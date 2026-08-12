"""
المرحلة 2: كتابة السكريبت + العنوان + الهاشتاغات عبر Gemini API
"""

import os
import re
import json

PROMPT_TEMPLATE = """You are a professional short-form scriptwriter specializing in
viral psychology/human-behavior story content for YouTube Shorts.

Write a video script about: {topic}

Requirements:
- HOOK (first line, first 2-3 seconds): must create an instant curiosity
  gap or pattern-interrupt. Use proven hook structures such as:
  "The real reason [common behavior] happens isn't what you think..."
  "Psychologists noticed something strange about people who..."
  "If you do this, here's what it actually says about you..."
  (Do NOT use fake/misleading claims - the hook must be true to the content)
- Do NOT make absolute scientific claims ("this proves scientifically that...").
  Keep it framed as behavioral observation, not medical/clinical fact.
- Include natural high-search keywords relevant to the topic within the
  script and title (e.g. "overthinking", "attachment style", "body language")
- Structure: Hook -> relatable mini-scenario -> the psychological insight
  -> a concrete, practical takeaway
- Conversational tone, short punchy sentences, no filler intros
- No fixed length requirement, but the total spoken script must stay under
  60 seconds when read aloud at a natural pace (roughly 90-150 words)
- End with a re-watchable or shareable closing line

Return ONLY valid JSON with this exact shape, nothing else:
{{
  "title": "...",
  "script": "...",
  "hashtags": ["...", "...", "...", "...", "..."]
}}
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```json\s*|\s*```$", "", text.strip())
    return json.loads(text)


def write_script(topic: str) -> dict:
    """يرجع dict فيه title, script, hashtags"""
    import google.generativeai as genai

    api_key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = PROMPT_TEMPLATE.format(topic=topic)
    response = model.generate_content(prompt)
    data = _extract_json(response.text)

    # فحص أساسي: تأكد من وجود كل الحقول
    assert "title" in data and "script" in data and "hashtags" in data
    return data


if __name__ == "__main__":
    from trend_finder import get_trending_topic

    topic = get_trending_topic()
    result = write_script(topic)
    print(json.dumps(result, indent=2, ensure_ascii=False))
