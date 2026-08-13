"""
stages/quality_check.py
بوابة الفحص قبل النشر:
- مقارنة الهوك/السكريبت الجديد مع آخر 30 سكريبت منشور (history/) لتجنب التكرار
- التأكد من مدة الفيديو أقل من 60 ثانية
- التأكد من عدد كلمات معقول
"""

import difflib
import json
import os

HISTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "history")
HISTORY_FILE = os.path.join(HISTORY_DIR, "published_scripts.json")
MAX_HISTORY = 30
SIMILARITY_THRESHOLD = 0.72  # فوق هالنسبة => يعتبر متشابه/مكرر
MAX_VIDEO_SECONDS = 59


def _load_history() -> list[dict]:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_history(entries: list[dict]) -> None:
    os.makedirs(HISTORY_DIR, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(entries[-MAX_HISTORY:], f, ensure_ascii=False, indent=2)


def _hook_text(script: dict) -> str:
    return script["segments"][0]["text"] if script.get("segments") else ""


def is_duplicate(script: dict) -> bool:
    hook = _hook_text(script)
    title = script.get("title", "")
    for entry in _load_history():
        hook_sim = difflib.SequenceMatcher(None, hook.lower(), entry.get("hook", "").lower()).ratio()
        title_sim = difflib.SequenceMatcher(None, title.lower(), entry.get("title", "").lower()).ratio()
        if hook_sim >= SIMILARITY_THRESHOLD or title_sim >= SIMILARITY_THRESHOLD:
            return True
    return False


def check_duration(video_path: str) -> bool:
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        check=True, capture_output=True, text=True,
    )
    duration = float(result.stdout.strip())
    return duration <= MAX_VIDEO_SECONDS


def run_quality_checks(script: dict, video_path: str) -> tuple[bool, str]:
    if is_duplicate(script):
        return False, "duplicate_hook_or_title"
    if not check_duration(video_path):
        return False, "video_too_long"
    word_count = sum(len(seg["text"].split()) for seg in script.get("segments", []))
    if word_count < 60 or word_count > 170:
        return False, f"word_count_out_of_range:{word_count}"
    return True, "ok"


def record_published(script: dict) -> None:
    history = _load_history()
    history.append({"title": script.get("title", ""), "hook": _hook_text(script)})
    _save_history(history)
