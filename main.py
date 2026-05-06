#!/usr/bin/env python3
"""
YouTube Automation Pipeline
Generate → Render → Upload (fully autonomous)
"""

import os
import json
import time
import pickle
import random
import threading
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from generate_video import generate_daily_video_sync, ensure_dirs as ensure_gen_dirs

# ─── Config ───

VIDEOS_DIR = Path(os.getenv("VIDEOS_DIR", "/app/videos"))
METADATA_DIR = Path(os.getenv("METADATA_DIR", "/app/metadata"))
THUMBNAILS_DIR = Path(os.getenv("THUMBNAILS_DIR", "/app/thumbnails"))
UPLOADED_DIR = Path(os.getenv("UPLOADED_DIR", "/app/uploaded"))

YOUTUBE_CLIENT_SECRETS_FILE = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "/etc/secrets/client_secrets.json")
YOUTUBE_TOKEN_FILE = os.getenv("YOUTUBE_TOKEN_FILE", "/etc/secrets/token.json")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
UPLOAD_INTERVAL_SECONDS = int(os.getenv("UPLOAD_INTERVAL_SECONDS", "3600"))

# ─── Logging ───

def log(msg: str):
    print(f"[{datetime.now().isoformat()}] {msg}")

# ─── HTTP Health Server ───

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ["/", "/health"]:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "service": "youtube-automation",
                "time": datetime.now().isoformat()
            }).encode())
        elif self.path == "/trigger":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"triggered": True}).encode())
            global _trigger_flag
            _trigger_flag = True
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def start_http_server() -> None:
    port = int(os.getenv("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    log(f"HTTP server listening on 0.0.0.0:{port}")

# ─── YouTube Auth ───

def get_youtube_service():
    creds = None
    if os.path.exists(YOUTUBE_TOKEN_FILE):
        with open(YOUTUBE_TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            log("Token refreshed successfully")
        else:
            if not os.path.exists(YOUTUBE_CLIENT_SECRETS_FILE):
                raise FileNotFoundError(f"Missing {YOUTUBE_CLIENT_SECRETS_FILE}")
            log("Starting OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(YOUTUBE_CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(YOUTUBE_TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)
        log(f"Token saved to {YOUTUBE_TOKEN_FILE}")

    return build("youtube", "v3", credentials=creds)

# ─── Upload Logic ───

def upload_video(youtube, video_path: Path, metadata_path: Path) -> dict:
    with open(metadata_path, "r") as f:
        meta = json.load(f)

    log(f"Uploading: {meta['title'][:60]}...")

    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta.get("tags", []),
            "categoryId": meta.get("category", "22"),
            "defaultLanguage": meta.get("language", "en"),
            "defaultAudioLanguage": meta.get("language", "en"),
        },
        "status": {
            "privacyStatus": meta.get("privacy", "private"),
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()

    video_id = response.get("id")
    log(f"Upload complete! Video ID: {video_id}")

    thumb_path = Path(meta.get("thumbnail_file", ""))
    if thumb_path.exists():
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(thumb_path))).execute()
            log(f"Thumbnail uploaded for {video_id}")
        except HttpError as e:
            log(f"Thumbnail upload failed: {e}")

    return response

def get_video_files():
    videos = []
    for meta_file in sorted(METADATA_DIR.glob("*.json")):
        with open(meta_file, "r") as f:
            meta = json.load(f)
        video_path = Path(meta.get("video_file", VIDEOS_DIR / f"{meta['video_id']}.mp4"))
        if video_path.exists() and meta.get("status") == "ready_for_upload":
            videos.append((video_path, meta_file))
    return videos

def mark_uploaded(video_path: Path, metadata_path: Path, youtube_response: dict):
    UPLOADED_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(metadata_path, "r") as f:
        meta = json.load(f)
    
    meta["status"] = "uploaded"
    meta["uploaded_at"] = datetime.now().isoformat()
    meta["youtube_video_id"] = youtube_response.get("id")
    meta["youtube_url"] = f"https://youtube.com/watch?v={youtube_response.get('id')}"
    
    new_meta = UPLOADED_DIR / metadata_path.name
    with open(new_meta, "w") as f:
        json.dump(meta, f, indent=2)
    metadata_path.unlink()
    
    new_video = UPLOADED_DIR / video_path.name
    video_path.rename(new_video)
    
    log(f"Marked uploaded: {meta['youtube_video_id']}")

# ─── Main Loop ───

_trigger_flag = False

def run_once(youtube):
    log("Starting work cycle...")
    
    pending = get_video_files()
    if not pending:
        log("No pending videos. Generating new content...")
        try:
            meta = generate_daily_video_sync()
            log(f"Generated video: {meta['video_id']}")
            pending = get_video_files()
        except Exception as e:
            log(f"Generation failed: {e}")
            import traceback
            traceback.print_exc()
    
    if not pending:
        log("No videos to upload.")
        return
    
    log(f"Found {len(pending)} video(s) to upload")
    for video_path, meta_path in pending:
        try:
            response = upload_video(youtube, video_path, meta_path)
            mark_uploaded(video_path, meta_path, response)
            time.sleep(5)
        except HttpError as e:
            log(f"Upload error for {video_path.name}: {e}")
            if e.resp.status in [403, 401]:
                log("Auth error — token may need refresh")
        except Exception as e:
            log(f"Unexpected error for {video_path.name}: {e}")
            import traceback
            traceback.print_exc()

def main():
    log("=== YouTube Automation Pipeline Starting ===")
    
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADED_DIR.mkdir(parents=True, exist_ok=True)
    ensure_gen_dirs()
    
    start_http_server()
    
    try:
        youtube = get_youtube_service()
        log("YouTube API authenticated successfully")
    except Exception as e:
        log(f"YouTube auth failed: {e}")
        youtube = None
    
    log(f"Config: upload_interval={UPLOAD_INTERVAL_SECONDS}s")
    
    last_run = 0
    global _trigger_flag
    
    while True:
        now = time.time()
        
        if youtube and (now - last_run >= UPLOAD_INTERVAL_SECONDS or _trigger_flag):
            _trigger_flag = False
            last_run = now
            try:
                run_once(youtube)
            except Exception as e:
                log(f"Cycle error: {e}")
                import traceback
                traceback.print_exc()
        
        time.sleep(10)

if __name__ == "__main__":
    main()
