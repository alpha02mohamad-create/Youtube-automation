"""
stages/script_writer.py
يكتب السكريبت الكامل عبر Gemini API:
- هوك متنوع الأنماط
- segments (نص + rate + pause_after) لصوت طبيعي غير مسطح
- visual_prompt لكل segment (لتوليد صورة تطابق المضمون لاحقاً)
- عنوان + وصف + وسوم ليوتيوب

يرجع dict جاهز يُستهلك من voice_gen.py و image_gen.py و youtube_uploader.py
"""

import os
import json
import re
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-1.5-flash"

HOOK_TYPES = [
    "direct_question",      # سؤال مباشر يلمس تجربة شخصية
    "surprising_claim",     # ادعاء مفاجئ يكسر توقع
    "mid_scene",            # بداية قصة مقتطعة بمنتصف الحدث
]

SYSTEM_PROMPT = """You are a scriptwriter for short-form psychology/behavior videos (under 60 seconds, English only).

Write ONE short story-driven script that blends a real psychological fact with a small, relatable narrative.

STRICT RULES:
- Hook (first line) MUST use the hook_type given to you. Never use cliché openers like "You won't believe", "This will change your life", "Did you know".
- Keep sentences short and simple (TTS-friendly, no complex nested clauses).
- Total spoken duration should be 45-58 seconds at normal pace (~140-150 words total).
- Break the script into 4-7 "segments". Each segment is one short beat (one or two sentences).
- For each segment, decide:
  - "rate": a relative speech-rate offset for edge-tts, one of "-20%", "-10%", "+0%", "+10%", "+15%" (slower for tense/reflective beats, faster for energetic beats)
  - "pause_after_ms": silence to insert after this segment (0 to 700ms; use longer pauses before a twist or the final insight)
  - "visual_prompt": a short, concrete English image-generation prompt describing exactly what should be shown on screen for this segment (a real, specific scene — not an abstract concept). Vertical framing, photographic style, no text overlays in the image itself.
- End with a one-sentence takeaway / psychological insight, delivered slightly slower.
- Output natural keywords related to psychology topics inside the script content itself (not forced).

Return ONLY valid JSON, no markdown fences, no preamble, matching exactly this schema:

{
  "title": "string, <=100 chars, curiosity-driven, no clickbait cliches",
  "hook_type": "string, one of the provided hook types",
  "segments": [
    {"text": "string", "rate": "string", "pause_after_ms": 0, "visual_prompt": "string"}
  ],
  "description": "string, 2-3 sentences for YouTube description",
  "tags": ["string", "..."]
}
"""


def _build_user_prompt(topic: str, hook_type: str, recent_hooks: list[str]) -> str:
    avoid_block = ""
    if recent_hooks:
        avoid_block = (
            "Avoid repeating the style, wording, or structure of these recent hooks:\n"
            + "\n".join(f"- {h}" for h in recent_hooks[-30:])
        )
    return f"""Topic to base the story on: {topic}
Required hook_type for this script: {hook_type}

{avoid_block}

Write the script now and return the JSON described in the system instructions.
"""


def _extract_json(raw_text: str) -> dict:
    """Gemini sometimes wraps JSON in ```json fences despite instructions — strip them."""
    cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def generate_script(topic: str, recent_hooks: list[str] | None = None, attempt: int = 0) -> dict:
    """
    Calls Gemini and returns a validated script dict.
    Retries with a different hook_type if called again after a quality-check rejection.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(MODEL_NAME, system_instruction=SYSTEM_PROMPT)

    hook_type = HOOK_TYPES[attempt % len(HOOK_TYPES)]
    user_prompt = _build_user_prompt(topic, hook_type, recent_hooks or [])

    response = model.generate_content(
        user_prompt,
        generation_config={"temperature": 0.9, "max_output_tokens": 1024},
    )

    data = _extract_json(response.text)
    _validate_script(data)
    return data


def _validate_script(data: dict) -> None:
    required_keys = {"title", "hook_type", "segments", "description", "tags"}
    missing = required_keys - data.keys()
    if missing:
        raise ValueError(f"Script JSON missing keys: {missing}")
    if not data["segments"]:
        raise ValueError("Script has no segments")
    for seg in data["segments"]:
        for key in ("text", "rate", "pause_after_ms", "visual_prompt"):
            if key not in seg:
                raise ValueError(f"Segment missing key: {key}")


if __name__ == "__main__":
    result = generate_script("why we overthink small conversations")
    print(json.dumps(result, indent=2, ensure_ascii=False))
