"""
YouTube Uploader — handles OAuth authentication and video uploads.
Run this file directly ONCE on your local machine to generate the OAuth token.
After that, the token is reused by main.py in production.
"""

import os
import pickle
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS_FILE = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")
TOKEN_FILE = "token.pickle"


def get_authenticated_service():
    """Authenticate and return a YouTube API service instance."""
    credentials: Credentials | None = None

    if Path(TOKEN_FILE).exists():
        with open(TOKEN_FILE, "rb") as token:
            credentials = pickle.load(token)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not Path(CLIENT_SECRETS_FILE).exists():
                raise FileNotFoundError(
                    f"Missing {CLIENT_SECRETS_FILE}. "
                    "Download it from Google Cloud Console → APIs & Services → Credentials."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES
            )
            credentials = flow.run_local_server(port=8080)

        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(credentials, token)

    return build("youtube", "v3", credentials=credentials)


def upload_video(
    file_path: str,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    category_id: str = "22",
    privacy_status: str = "private",
    language: str = "en",
) -> dict:
    """
    Upload a video to YouTube.

    Args:
        file_path: Path to the video file.
        title: Video title.
        description: Video description.
        tags: List of tags.
        category_id: YouTube category ID (22 = People & Blogs).
        privacy_status: "private", "unlisted", or "public".
        language: ISO 639-1 language code.

    Returns:
        API response dict with video ID and metadata.
    """
    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": category_id,
            "defaultLanguage": language,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        file_path,
        mimetype="video/*",
        resumable=True,
        chunksize=1024 * 1024 * 5,  # 5 MB chunks
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"Uploading: {pct}%")

    video_id = response["id"]
    print(f"Upload complete: https://youtube.com/watch?v={video_id}")
    return response


if __name__ == "__main__":
    print("Running one-time OAuth setup...")
    print("A browser window will open. Log in with your YouTube account.")
    service = get_authenticated_service()
    print(f"Token saved to {TOKEN_FILE}. You can now deploy main.py.")
