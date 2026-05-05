"""
YouTube Automation Pipeline — Main Orchestrator.

Watches a directory for new video files, uploads them to YouTube,
and moves processed files to an archive directory.

Designed to run as a scheduled background worker on Render.
Each run processes all pending videos in the VIDEOS_DIR.
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from youtube_uploader import upload_video

load_dotenv()

VIDEOS_DIR = Path(os.getenv("VIDEOS_DIR", "videos"))
UPLOADED_DIR = Path(os.getenv("UPLOADED_DIR", "uploaded"))
METADATA_DIR = Path("metadata")

DEFAULT_PRIVACY = os.getenv("DEFAULT_PRIVACY", "private")
DEFAULT_CATEGORY = os.getenv("DEFAULT_CATEGORY", "22")
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def ensure_directories() -> None:
    """Create required directories if they don't exist."""
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADED_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)


def load_metadata(video_path: Path) -> dict:
    """
    Load metadata for a video from a matching JSON file.
    Looks for {video_name}.json in the metadata directory.

    Expected JSON format:
    {
        "title": "My Video Title",
        "description": "Optional description",
        "tags": ["tag1", "tag2"],
        "privacy": "public",
        "category": "22"
    }
    """
    metadata_file = METADATA_DIR / f"{video_path.stem}.json"
    if metadata_file.exists():
        with open(metadata_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_video_files() -> list[Path]:
    """Return list of video files in the watch directory, sorted by creation time."""
    files: list[Path] = []
    for ext in VIDEO_EXTENSIONS:
        files.extend(VIDEOS_DIR.glob(f"*{ext}"))
        files.extend(VIDEOS_DIR.glob(f"*{ext.upper()}"))
    files.sort(key=lambda p: p.stat().st_ctime)
    return files


def process_video(video_path: Path) -> bool:
    """
    Process a single video: load metadata, upload, and archive.
    Returns True on success, False on failure.
    """
    metadata = load_metadata(video_path)

    title = metadata.get("title", video_path.stem)
    description = metadata.get("description", "")
    tags = metadata.get("tags", [])
    privacy = metadata.get("privacy", DEFAULT_PRIVACY)
    category = str(metadata.get("category", DEFAULT_CATEGORY))
    language = metadata.get("language", DEFAULT_LANGUAGE)

    print(f"\n{'='*60}")
    print(f"Processing: {video_path.name}")
    print(f"Title: {title}")
    print(f"Privacy: {privacy}")
    print(f"{'='*60}")

    try:
        upload_video(
            file_path=str(video_path),
            title=title,
            description=description,
            tags=tags,
            category_id=category,
            privacy_status=privacy,
            language=language,
        )

        # Move video to uploaded directory
        dest = UPLOADED_DIR / video_path.name
        shutil.move(str(video_path), str(dest))
        print(f"Moved to: {dest}")

        # Move metadata to uploaded directory
        metadata_file = METADATA_DIR / f"{video_path.stem}.json"
        if metadata_file.exists():
            shutil.move(str(metadata_file), str(UPLOADED_DIR / metadata_file.name))

        return True

    except Exception as e:
        print(f"FAILED: {e}")
        return False


def main() -> None:
    """Main entry point. Process all pending videos."""
    print(f"[{datetime.now().isoformat()}] Pipeline started")
    ensure_directories()

    video_files = get_video_files()

    if not video_files:
        print("No videos to process.")
        return

    print(f"Found {len(video_files)} video(s) to process.")

    success_count = 0
    fail_count = 0

    for video_path in video_files:
        if process_video(video_path):
            success_count += 1
        else:
            fail_count += 1

    print(f"\nPipeline complete: {success_count} uploaded, {fail_count} failed.")
    print(f"[{datetime.now().isoformat()}] Pipeline finished")


if __name__ == "__main__":
    main()
