#!/usr/bin/env python3
"""
YouTube Video Generator
Creates faceless YouTube videos using:
  - AI-generated scripts from trending topics
  - Free TTS (edge-tts) for voiceover
  - ffmpeg for video assembly with text overlays
  - Auto-generated thumbnails
"""

import os
import json
import random
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

# Config paths
VIDEOS_DIR = Path(os.getenv("VIDEOS_DIR", "/app/videos"))
METADATA_DIR = Path(os.getenv("METADATA_DIR", "/app/metadata"))
THUMBNAILS_DIR = Path(os.getenv("THUMBNAILS_DIR", "/app/thumbnails"))
TEMP_DIR = Path("/tmp/youtube_gen")

# Try to find a usable system font for ffmpeg drawtext
COMMON_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/arial.ttf",
]

def get_font_path() -> str:
    for f in COMMON_FONTS:
        if os.path.exists(f):
            return f
    subprocess.run(["apt-get", "update", "-qq"], capture_output=True)
    subprocess.run(["apt-get", "install", "-y", "-qq", "fonts-dejavu"], capture_output=True)
    for f in COMMON_FONTS:
        if os.path.exists(f):
            return f
    return ""

FONT_PATH = get_font_path()
FONT_ARG = f":fontfile={FONT_PATH}" if FONT_PATH else ""

def ensure_dirs():
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

# ─── 1. Trending Topics & Script Generation ───

TRENDING_TOPICS = [
    "AI tools that will blow your mind in 2026",
    "How to make $1000 online this month with zero skills",
    "3 habits that changed my life forever",
    "The truth about passive income nobody tells you",
    "Why most beginner programmers fail (avoid this)",
    "Hidden ChatGPT features that save hours every day",
    "The fastest way to learn any skill in 30 days",
    "Money mistakes to avoid in your 20s",
    "How I built a $5K/month side hustle from my phone",
    "Signs you are smarter than you think",
    "The 5-minute morning routine millionaires use",
    "Free websites that feel illegal to know",
    "How to negotiate a salary raise (scripts included)",
    "The real reason you are procrastinating",
    "Apps that pay you real money in 2026",
]

HOOKS = [
    "You won't believe what I discovered about {topic}",
    "Stop scrolling. This changes everything about {topic}",
    "I tried {topic} for 30 days — here's what happened",
    "Nobody is talking about this {topic} secret",
    "If you care about {topic}, watch this before tomorrow",
    "This {topic} hack saved me 10 hours last week",
]

BULLETS_POOL = [
    "First, most people completely misunderstand this.",
    "The mainstream advice is actually backwards.",
    "Here's what the top 1% do differently.",
    "I wish I knew this 5 years ago.",
    "This one shift changes everything.",
    "The data on this is shocking.",
    "Stop doing this one thing immediately.",
]

CTAS = [
    "Subscribe + follow for part 2 tomorrow.",
    "Comment 'YES' if this hit home.",
    "Save this before it gets buried.",
    "Drop a follow if you want full blueprint.",
    "Which point hit hardest? Comment below.",
]

def generate_script(topic: Optional[str] = None) -> dict:
    if topic is None:
        topic = random.choice(TRENDING_TOPICS)
    
    hook = random.choice(HOOKS).format(topic=topic)
    bullets = random.sample(BULLETS_POOL, k=3)
    cta = random.choice(CTAS)
    
    narration = f"{hook}\n\n"
    for i, b in enumerate(bullets, 1):
        narration += f"Point number {i}: {b}\n\n"
    narration += f"{cta}"
    
    title = hook.replace("You won't believe what I discovered about ", "")
    title = title.replace("Stop scrolling. This changes everything about ", "")
    title = title.replace("I tried ", "I Tried ")
    title = title[:95]
    
    return {
        "video_id": f"vid_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000,9999)}",
        "topic": topic,
        "title": title,
        "hook": hook,
        "bullets": bullets,
        "cta": cta,
        "narration": narration,
        "description": f"{hook}\n\n" + "\n".join(f"• {b}" for b in bullets) + f"\n\n{cta}\n\n#shorts #viral #trending",
        "tags": topic.lower().split() + ["shorts", "viral", "trending"],
        "duration_estimate": 45,
    }

# ─── 2. TTS Voiceover ───

async def generate_voiceover(script: dict, output_path: Path) -> Path:
    try:
        import edge_tts
    except ImportError:
        subprocess.run(["pip", "install", "edge-tts", "-q"], check=True)
        import edge_tts
    
    voice = "en-US-GuyNeural"
    communicate = edge_tts.Communicate(script["narration"], voice)
    await communicate.save(str(output_path))
    return output_path

def get_audio_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())

# ─── 3. Video Rendering ───

def create_background_video(duration: float, output_path: Path, width: int = 1080, height: int = 1920):
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x121212:s={width}x{height}:d={duration}",
        "-f", "lavfi",
        "-i", f"gradients=s={width}x{height}:r=30:d={duration}:speed=0.05:type=radial:seed=42",
        "-filter_complex",
        "[1:v]format=yuv420p,fade=t=out:st=0:d=0.01:alpha=1[grad];[0:v][grad]blend=all_mode='overlay':all_opacity=0.15[out]",
        "-map", "[out]",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-r", "30",
        "-t", str(duration),
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=0x1a1a2e:s={width}x{height}:d={duration}",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-r", "30",
            "-t", str(duration),
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True, check=True)
    return output_path

def add_text_overlays(video_path: Path, script: dict, output_path: Path):
    duration = get_audio_duration(TEMP_DIR / f"{script['video_id']}.mp3")
    
    segments = [
        (0, 5, script["hook"], "hook"),
        (8, 15, script["bullets"][0], "bullet1"),
        (18, 25, script["bullets"][1], "bullet2"),
        (28, 35, script["bullets"][2], "bullet3"),
        (max(0, duration - 8), duration, script["cta"], "cta"),
    ]
    
    filters = []
    for start, end, text, label in segments:
        escaped = text.replace("'", "\\'").replace(",", "\\,")
        if label == "hook":
            fontsize, fontcolor, bordercolor, y_pos = 64, "white", "black", "h*0.15"
        elif label == "cta":
            fontsize, fontcolor, bordercolor, y_pos = 56, "yellow", "black", "h*0.75"
        else:
            fontsize, fontcolor, bordercolor, y_pos = 52, "white", "black", "h*0.45"
        
        filters.append(
            f"drawtext=text='{escaped}'{FONT_ARG}:"
            f"fontsize={fontsize}:fontcolor={fontcolor}:borderw=4:bordercolor={bordercolor}:"
            f"x=(w-text_w)/2:y={y_pos}:"
            f"enable='between(t\\,{start}\\,{end})':"
            f"alpha='if(lt(t,{start}+0.5),(t-{start})/0.5,if(lt(t,{end}-0.5),1,({end}-t)/0.5))'"
        )
    
    filters.append(
        f"drawtext=text='Subscribe for daily tips'{FONT_ARG}:"
        f"fontsize=24:fontcolor=white:borderw=2:bordercolor=black:"
        f"x=(w-text_w)/2:y=h*0.92:"
        f"enable='between(t\\,0\\,{duration})'"
    )
    
    filter_str = ",".join(filters)
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", filter_str,
        "-an",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-r", "30",
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path

def combine_video_audio(video_path: Path, audio_path: Path, output_path: Path):
    duration = get_audio_duration(audio_path)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        "-t", str(duration),
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path

# ─── 4. Thumbnail Generator ───

def generate_thumbnail(script: dict, output_path: Path):
    width, height = 1280, 720
    bg_path = TEMP_DIR / f"{script['video_id']}_thumb_bg.png"
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"gradient=s={width}x{height}:c0=0x1a1a2e:c1=0x16213e",
        "-frames:v", "1",
        str(bg_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    
    title = script["title"][:50] + "..." if len(script["title"]) > 50 else script["title"]
    words = title.split()
    lines = []
    current = ""
    for w in words:
        if len(current) + len(w) < 20:
            current += " " + w if current else w
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    
    display_text = "\\n".join(lines).replace("'", "\\'")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(bg_path),
        "-vf",
        f"drawtext=text='{display_text}'{FONT_ARG}:"
        f"fontsize=72:fontcolor=yellow:borderw=6:bordercolor=black:"
        f"x=(w-text_w)/2:y=(h-text_h)/2",
        "-frames:v", "1",
        "-update", "1",
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path

# ─── 5. Main Pipeline ───

async def generate_video_package(topic: Optional[str] = None) -> dict:
    ensure_dirs()
    script = generate_script(topic)
    vid = script["video_id"]
    print(f"[GEN] Starting generation for: {script['title'][:60]}...")
    
    audio_path = TEMP_DIR / f"{vid}.mp3"
    print(f"[GEN] Generating voiceover...")
    await generate_voiceover(script, audio_path)
    duration = get_audio_duration(audio_path)
    print(f"[GEN] Audio duration: {duration:.1f}s")
    
    bg_path = TEMP_DIR / f"{vid}_bg.mp4"
    print(f"[GEN] Rendering background...")
    create_background_video(duration, bg_path, width=1080, height=1920)
    
    overlay_path = TEMP_DIR / f"{vid}_overlay.mp4"
    print(f"[GEN] Adding text overlays...")
    add_text_overlays(bg_path, script, overlay_path)
    
    final_video = VIDEOS_DIR / f"{vid}.mp4"
    print(f"[GEN] Muxing audio + video...")
    combine_video_audio(overlay_path, audio_path, final_video)
    
    thumb_path = THUMBNAILS_DIR / f"{vid}.jpg"
    print(f"[GEN] Creating thumbnail...")
    generate_thumbnail(script, thumb_path)
    
    metadata = {
        "video_id": vid,
        "title": script["title"],
        "description": script["description"],
        "tags": script["tags"],
        "category": os.getenv("DEFAULT_CATEGORY", "22"),
        "privacy": os.getenv("DEFAULT_PRIVACY", "private"),
        "language": os.getenv("DEFAULT_LANGUAGE", "en"),
        "video_file": str(final_video),
        "thumbnail_file": str(thumb_path),
        "script": script,
        "duration": duration,
        "created_at": datetime.now().isoformat(),
        "status": "ready_for_upload",
    }
    meta_path = METADATA_DIR / f"{vid}.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    for f in [audio_path, bg_path, overlay_path, TEMP_DIR / f"{vid}_thumb_bg.png"]:
        if f.exists():
            f.unlink()
    
    print(f"[GEN] Done! Video: {final_video.name} | Thumbnail: {thumb_path.name}")
    return metadata

def generate_daily_video_sync(topic: Optional[str] = None) -> dict:
    return asyncio.run(generate_video_package(topic))

if __name__ == "__main__":
    meta = generate_daily_video_sync()
    print("\nGenerated metadata preview:")
    print(json.dumps(meta, indent=2))
