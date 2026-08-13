"""
main.py
المنسّق الرئيسي: يشغّل كل المراحل بالترتيب لإنتاج ونشر فيديو واحد.
عند فشل فحص الجودة، يعيد كتابة السكريبت بنمط هوك مختلف (حد أقصى 3 محاولات).
"""

import os
import shutil
import tempfile

from stages.trend_finder import get_trending_topic
from stages.script_writer import generate_script
from stages.voice_gen import generate_voice
from stages.image_gen import generate_images_for_segments
from stages.video_assembler import assemble_video
from stages.quality_check import run_quality_checks, record_published, _load_history
from stages.youtube_uploader import upload_video

MAX_ATTEMPTS = 3


def run_once() -> None:
    topic = get_trending_topic()
    print(f"[main] Topic: {topic}")

    recent_hooks = [e.get("hook", "") for e in _load_history()]

    with tempfile.TemporaryDirectory() as workdir:
        final_video_path = None
        script = None

        for attempt in range(MAX_ATTEMPTS):
            script = generate_script(topic, recent_hooks=recent_hooks, attempt=attempt)
            print(f"[main] Attempt {attempt+1}: title='{script['title']}' hook_type={script['hook_type']}")

            voice_path, durations_ms = generate_voice(script["segments"], os.path.join(workdir, "voice"))
            image_paths = generate_images_for_segments(script["segments"], os.path.join(workdir, "images"))

            video_path = assemble_video(
                image_paths, durations_ms, script["segments"], voice_path,
                os.path.join(workdir, "video"),
            )

            ok, reason = run_quality_checks(script, video_path)
            if ok:
                final_video_path = video_path
                break
            print(f"[main] Quality check failed: {reason}. Retrying with a different hook style...")

        if final_video_path is None:
            print("[main] All attempts failed quality checks. Skipping this run.")
            return

        video_id = upload_video(
            final_video_path,
            title=script["title"],
            description=script["description"],
            tags=script["tags"],
        )
        print(f"[main] Uploaded: https://youtube.com/watch?v={video_id}")

        record_published(script)


if __name__ == "__main__":
    run_once()
