#!/usr/bin/env python3
"""
Add a /status endpoint to show detailed runtime information
"""

import os
import json
from pathlib import Path

VIDEOS_DIR = Path(os.getenv("VIDEOS_DIR", "/app/videos"))
METADATA_DIR = Path(os.getenv("METADATA_DIR", "/app/metadata"))
THUMBNAILS_DIR = Path(os.getenv("THUMBNAILS_DIR", "/app/thumbnails"))
UPLOADED_DIR = Path(os.getenv("UPLOADED_DIR", "/app/uploaded"))

def get_status():
    """Get detailed status of the automation pipeline"""
    
    # Count files in each directory
    video_files = list(VIDEOS_DIR.glob("*.mp4"))
    metadata_files = list(METADATA_DIR.glob("*.json"))
    thumbnail_files = list(THUMBNAILS_DIR.glob("*.jpg"))
    uploaded_files = list(UPLOADED_DIR.glob("*.json"))
    
    # Get ready-to-upload videos
    ready_videos = []
    for meta_file in metadata_files:
        try:
            with open(meta_file, "r") as f:
                meta = json.load(f)
            if meta.get("status") == "ready_for_upload":
                video_path = Path(meta.get("video_file", ""))
                if video_path.exists():
                    ready_videos.append({
                        "video_id": meta.get("video_id"),
                        "title": meta.get("title", "")[:50],
                        "created_at": meta.get("created_at"),
                        "video_file": str(video_path.name),
                        "thumbnail_file": str(Path(meta.get("thumbnail_file", "")).name)
                    })
        except:
            pass
    
    return {
        "service": "youtube-automation",
        "status": "running",
        "directories": {
            "videos": {
                "count": len(video_files),
                "files": [f.name for f in video_files[:5]]  # Show first 5
            },
            "metadata": {
                "count": len(metadata_files),
                "files": [f.name for f in metadata_files[:5]]
            },
            "thumbnails": {
                "count": len(thumbnail_files),
                "files": [f.name for f in thumbnail_files[:5]]
            },
            "uploaded": {
                "count": len(uploaded_files),
                "files": [f.name for f in uploaded_files[:5]]
            }
        },
        "ready_to_upload": ready_videos,
        "last_check": "2026-05-07T15:25:45Z"
    }

if __name__ == "__main__":
    print(json.dumps(get_status(), indent=2))
