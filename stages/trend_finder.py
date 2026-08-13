"""
stages/trend_finder.py
يجيب موضوع رائج ضمن نيتش "قصص نفسية/سلوكية" عبر pytrends (مكتبة غير رسمية).
لو فشل (pytrends معرضة للانكسار لأنها reverse-engineered)، يرجع لقائمة مواضيع
احتياطية ثابتة تغطي نفس النيتش.
"""

import random

FALLBACK_TOPICS = [
    "why we overthink small conversations",
    "the psychology behind procrastination",
    "why embarrassing memories feel so vivid",
    "why we remember insults more than compliments",
    "the reason silence feels uncomfortable",
    "why we compare ourselves to strangers online",
    "the psychology of holding grudges",
    "why deadlines make us more creative",
    "the reason we re-read old texts",
    "why criticism hurts more from people we admire",
]

SEED_KEYWORDS = ["overthinking", "psychology facts", "attachment style", "self sabotage", "cognitive bias"]


def get_trending_topic() -> str:
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="en-US", tz=0)
        pytrends.build_payload(SEED_KEYWORDS, timeframe="now 7-d")
        related = pytrends.related_queries()
        for kw in SEED_KEYWORDS:
            rising = related.get(kw, {}).get("rising")
            if rising is not None and not rising.empty:
                return str(rising.iloc[0]["query"])
    except Exception as e:
        print(f"[trend_finder] pytrends failed ({e}); using fallback topic list")

    return random.choice(FALLBACK_TOPICS)
