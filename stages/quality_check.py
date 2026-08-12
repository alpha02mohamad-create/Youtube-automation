"""
المرحلة 5: بوابة فحص الجودة الآلية (بدل المراجعة اليدوية)
"""

import os
import json
import difflib

HISTORY_PATH = "history/published_scripts.json"
MAX_SIMILARITY = 0.75
MAX_DURATION_SECONDS = 59
MIN_WORDS = 40
MAX_WORDS = 200


def load_history() -> list:
    if not os.path.exists(HISTORY_PATH):
        return []
    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_to_history(script_text: str, limit: int = 30):
    history = load_history()
    history.append(script_text)
    history = history[-limit:]
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def is_too_similar(script_text: str, history: list) -> bool:
    for old in history:
        ratio = difflib.SequenceMatcher(None, script_text, old).ratio()
        if ratio >= MAX_SIMILARITY:
            return True
    return False


def check_script(script_text: str) -> tuple:
    """يرجع (passed: bool, reason: str)"""
    word_count = len(script_text.split())
    if not (MIN_WORDS <= word_count <= MAX_WORDS):
        return False, f"word count out of range: {word_count}"

    history = load_history()
    if is_too_similar(script_text, history):
        return False, "too similar to a recently published script"

    first_sentence = script_text.strip().split(".")[0].lower()
    weak_openings = ["in this video", "today we will", "welcome to"]
    if any(w in first_sentence for w in weak_openings):
        return False, "weak/generic opening line"

    return True, "ok"


def check_audio_duration(duration_seconds: float) -> tuple:
    if duration_seconds > MAX_DURATION_SECONDS:
        return False, f"audio too long: {duration_seconds:.1f}s"
    return True, "ok"
