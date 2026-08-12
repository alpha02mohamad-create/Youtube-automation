"""
السكريبت الرئيسي: ينسّق كل المراحل لإنتاج ورفع فيديو واحد.
main.py --count 5   -> ينتج ويرفع 5 فيديوهات بجلسة واحدة
"""

import argparse
import os
import shutil
import traceback

from stages.trend_finder import get_trending_topic
from stages.script_writer import write_script
from stages.voice_gen import generate_voice, get_audio_duration
from stages.video_assembler import search_and_download_clips, build_srt, assemble_video
from stages.quality_check import check_script, check_audio_duration, save_to_history
from stages.youtube_uploader import upload_video

MAX_ATTEMPTS_PER_VIDEO = 3


def produce_one_video(work_dir: str) -> bool:
    os.makedirs(work_dir, exist_ok=True)

    for attempt in range(1, MAX_ATTEMPTS_PER_VIDEO + 1):
        topic = get_trending_topic()
        print(f"[main] topic: {topic} (attempt {attempt})")

        data = write_script(topic)
        script_text = data["script"]

        passed, reason = check_script(script_text)
        if not passed:
            print(f"[main] script rejected: {reason} -> retrying with new topic")
            continue

        voice_path = os.path.join(work_dir, "voice.mp3")
        generate_voice(script_text, voice_path)
        duration = get_audio_duration(voice_path)

        passed, reason = check_audio_duration(duration)
        if not passed:
            print(f"[main] audio rejected: {reason} -> retrying with new topic")
            continue

        clips_dir = os.path.join(work_dir, "clips")
        clip_paths = search_and_download_clips(topic, count=3, out_dir=clips_dir)

        srt_path = os.path.join(work_dir, "subtitles.srt")
        build_srt(script_text, duration, srt_path)

        final_path = os.path.join(work_dir, "final.mp4")
        assemble_video(
            clip_paths, voice_path, srt_path,
            intro_path="assets/intro.mp4", out_path=final_path,
        )

        video_id = upload_video(
            final_path, data["title"], data["script"], data["hashtags"]
        )
        print(f"[main] uploaded: https://youtube.com/shorts/{video_id}")

        save_to_history(script_text)
        return True

    print("[main] all attempts failed for this video slot, skipping")
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1)
    args = parser.parse_args()

    successes = 0
    for i in range(args.count):
        work_dir = f"work/video_{i}"
        try:
            if produce_one_video(work_dir):
                successes += 1
        except Exception:
            print(f"[main] unexpected error on video {i}:")
            traceback.print_exc()
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    print(f"[main] done: {successes}/{args.count} videos published")


if __name__ == "__main__":
    main()
