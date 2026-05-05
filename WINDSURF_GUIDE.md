# YouTube Automation Pipeline — Deployment Guide

## Overview

This pipeline watches a directory for video files, uploads them to YouTube via the YouTube Data API v3, and archives processed files. It runs as a scheduled background worker on Render.

## Step 1: Google Cloud Setup

1. Go to https://console.cloud.google.com
2. Create a new project or select existing
3. Enable the **YouTube Data API v3**:
   - Left sidebar → APIs & Services → Library
   - Search "YouTube Data API v3" → Enable
4. Create OAuth credentials:
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: **Desktop app**
   - Name: "YouTube Automation"
   - Click Create
   - Download the JSON file → rename to `client_secrets.json`

## Step 2: Local OAuth Setup (One-Time)

Run this on YOUR computer (not Render):

```bash
pip install -r requirements.txt
python youtube_uploader.py
```

A browser opens. Log in with the YouTube channel you want to upload to. This creates `token.pickle` — save this file, you'll need it for Render.

## Step 3: Prepare a Test Video

1. Create folder `videos/`
2. Put a test `.mp4` file inside
3. Create `metadata/your-video-name.json`:

```json
{
  "title": "My First Automated Video",
  "description": "Uploaded by the automation pipeline.",
  "tags": ["automation", "test"],
  "privacy": "private",
  "category": "22"
}
```

## Step 4: Deploy to Render

1. Go to https://dashboard.render.com → New → **Background Worker**
2. Connect your GitHub/GitLab repo
3. Configure:
   - **Name**: youtube-automation
   - **Runtime**: Docker
   - **Region**: Oregon (or closest)
4. Add **Secret Files** (Settings → Secret Files):
   - Filename: `client_secrets.json` → paste the JSON content
   - Filename: `token.pickle` → upload the file from Step 2
5. Add **Environment Variables**:
   - `VIDEOS_DIR` = `videos`
   - `UPLOADED_DIR` = `uploaded`
   - `DEFAULT_PRIVACY` = `private`
6. Set **Cron Schedule** (optional, for recurring runs):
   - In Render dashboard → Cron Jobs → `0 */6 * * *` (every 6 hours)
7. Click **Create Worker**

## Step 5: Add Videos

Upload video files to your `videos/` directory (via Git push or Render shell). Each run processes all pending videos and moves them to `uploaded/`.

## File Structure

```
youtube-automation/
├── main.py              # Orchestrator
├── youtube_uploader.py  # OAuth + upload logic
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container config
├── .env.example         # Environment template
├── WINDSURF_GUIDE.md    # This file
├── client_secrets.json  # Google OAuth (secret)
├── token.pickle         # OAuth token (secret)
├── videos/              # Drop videos here
├── metadata/            # JSON metadata per video
└── uploaded/            # Archive after upload
```
