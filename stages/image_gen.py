"""
stages/image_gen.py
يولّد صورة واحدة لكل segment عبر Cloudflare Workers AI / FLUX.1 [schnell].
عند فشل Cloudflare أو عدم وجود المفاتيح، يستخدم صورة احتياطية عامة
من assets/fallback_images/ بدل إيقاف الـ pipeline بالكامل.
"""

import base64
import os
import random
from io import BytesIO

import requests
from PIL import Image, ImageOps


CLOUDFLARE_API_TOKEN = os.getenv("FLUX_API_KEY")
CLOUDFLARE_ACCOUNT_ID = os.getenv("FLUX_API_ID")

MODEL = "@cf/black-forest-labs/flux-1-schnell"

CLOUDFLARE_URL = (
    "https://api.cloudflare.com/client/v4/accounts/"
    f"{CLOUDFLARE_ACCOUNT_ID}/ai/run/{MODEL}"
    if CLOUDFLARE_ACCOUNT_ID
    else None
)

IMG_WIDTH = 1080
IMG_HEIGHT = 1920
TIMEOUT_SECONDS = 120

FALLBACK_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "assets",
    "fallback_images",
)


def _fallback_image() -> str:
    candidates = [
        f
        for f in os.listdir(FALLBACK_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    if not candidates:
        raise RuntimeError(
            "No fallback images found in assets/fallback_images/"
        )

    return os.path.join(FALLBACK_DIR, random.choice(candidates))


def _copy_fallback(out_path: str) -> str:
    fallback_path = _fallback_image()

    with open(fallback_path, "rb") as src, open(out_path, "wb") as dst:
        dst.write(src.read())

    return out_path


def _save_cloudflare_image(image_b64: str, out_path: str) -> str:
    raw = base64.b64decode(image_b64)

    image = Image.open(BytesIO(raw)).convert("RGB")

    # تحويل الصورة إلى 1080x1920 لتناسب فيديوهات Shorts
    image = ImageOps.fit(
        image,
        (IMG_WIDTH, IMG_HEIGHT),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )

    image.save(
        out_path,
        format="JPEG",
        quality=95,
        optimize=True,
    )

    return out_path


def generate_image(
    visual_prompt: str,
    out_path: str,
    seed: int | None = None,
) -> str:

    full_prompt = (
        f"{visual_prompt}, "
        "vertical portrait photography, "
        "cinematic lighting, "
        "high quality, "
        "detailed, "
        "no text, "
        "no watermark"
    )

    # إذا لم تكن مفاتيح Cloudflare موجودة، استخدم الصورة الاحتياطية
    if (
        not CLOUDFLARE_API_TOKEN
        or not CLOUDFLARE_ACCOUNT_ID
        or not CLOUDFLARE_URL
    ):
        print(
            "[image_gen] Cloudflare credentials missing; "
            "using fallback image"
        )
        return _copy_fallback(out_path)

    payload = {
        "prompt": full_prompt,
        "steps": 4,
    }

    if seed is not None:
        payload["seed"] = int(seed)

    try:
        response = requests.post(
            CLOUDFLARE_URL,
            headers={
                "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )

        response.raise_for_status()

        data = response.json()

        result = data.get("result") or {}
        image_b64 = result.get("image")

        if not image_b64:
            raise ValueError(
                "Cloudflare response did not contain result.image"
            )

        _save_cloudflare_image(image_b64, out_path)

        print("[image_gen] Cloudflare FLUX image generated successfully")

        return out_path

    except Exception as e:
        print(
            f"[image_gen] Cloudflare FLUX failed ({e}); "
            "using fallback image"
        )

        return _copy_fallback(out_path)


def generate_images_for_segments(
    segments: list[dict],
    workdir: str,
) -> list[str]:

    os.makedirs(workdir, exist_ok=True)

    paths = []

    for i, seg in enumerate(segments):

        out_path = os.path.join(
            workdir,
            f"img_{i:02d}.jpg",
        )

        generate_image(
            seg["visual_prompt"],
            out_path,
            seed=i + 1,
        )

        paths.append(out_path)

    return paths


if __name__ == "__main__":
    print(
        generate_image(
            "a futuristic city at night, cinematic",
            "/tmp/test_img.jpg",
            seed=42,
        )
    )
