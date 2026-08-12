"""
المرحلة 6: رفع الفيديو على يوتيوب عبر YouTube Data API v3
"""

import os
import json
import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def _get_credentials():
    """يقرأ بيانات OAuth المخزنة بمتغير بيئة YOUTUBE_CREDENTIALS (JSON)"""
    creds_json = json.loads(os.environ["YOUTUBE_CREDENTIALS"])
    return google.oauth2.credentials.Credentials(**creds_json)


def upload_video(
    video_path: str,
    title: str,
    description: str,
    hashtags: list,
    max_retries: int = 3,
):
    creds = _get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    tags = [h.lstrip("#") for h in hashtags]
    body = {
        "snippet": {
            "title": title[:100],
            "description": f"{description}\n\n" + " ".join(hashtags),
            "tags": tags,
            "categoryId": "27",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,
        },
    }

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=MediaFileUpload(video_path, resumable=True),
            )
            response = request.execute()
            return response["id"]
        except Exception as e:
            last_error = e
            print(f"[youtube_uploader] attempt {attempt} failed: {e}")

    raise RuntimeError(f"upload failed after {max_retries} attempts: {last_error}")
