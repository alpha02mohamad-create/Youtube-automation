"""
stages/image_gen.py
يولّد صورة واحدة لكل segment عبر Pollinations.ai (مجاني، بدون بطاقة أو تسجيل).
لو فشل الطلب (خدمة صغيرة، غير مضمونة الاستقرار)، يستخدم صورة احتياطية عامة
من assets/fallback_images/ بدل ما يوقف الـ pipeline بالكامل.
"""

import os
import random
import urllib.parse
import requests

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt/"
IMG_WIDTH = 1080
IMG_HEIGHT = 1920  # عمودي 9:16
TIMEOUT_SECONDS = 30

FALLBACK_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fallback_images")


def _fallback_image() -> str:
    candidates = [f for f in os.listdir(FALLBACK_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    if not candidates:
        raise RuntimeError("No fallback images found in assets/fallback_images/")
    return os.path.join(FALLBACK_DIR, random.choice(candidates))


def generate_image(visual_prompt: str, out_path: str, seed: int | None = None) -> str:
    """
    يحاول توليد صورة عبر Pollinations.ai. عند أي فشل (timeout، خطأ سيرفر، محتوى فاضي)،
    يرجع مسار صورة احتياطية بدل ما يرمي استثناء يوقف باقي الفيديو.
    """
    full_prompt = f"{visual_prompt}, vertical portrait photography, cinematic lighting, no text, no watermark"
    encoded = urllib.parse.quote(full_prompt)
    seed_val = seed if seed is not None else random.randint(1, 999999)
    url = f"{POLLINATIONS_BASE}{encoded}?width={IMG_WIDTH}&height={IMG_HEIGHT}&seed={seed_val}&nologo=true"

    try:
        resp = requests.get(url, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        if len(resp.content) < 5000:  # رد صغير جداً = غالباً فشل صامت
            raise ValueError("Response too small, likely a failed generation")
        with open(out_path, "wb") as f:
            f.write(resp.content)
        return out_path
    except Exception as e:
        print(f"[image_gen] Pollinations.ai failed ({e}); using fallback image")
        fallback_path = _fallback_image()
        with open(fallback_path, "rb") as src, open(out_path, "wb") as dst:
            dst.write(src.read())
        return out_path


def generate_images_for_segments(segments: list[dict], workdir: str) -> list[str]:
    os.makedirs(workdir, exist_ok=True)
    paths = []
    for i, seg in enumerate(segments):
        out_path = os.path.join(workdir, f"img_{i:02d}.jpg")
        generate_image(seg["visual_prompt"], out_path)
        paths.append(out_path)
    return paths


if __name__ == "__main__":
    print(generate_image("a person staring at their phone late at night, anxious", "/tmp/test_img.jpg"))
