"""
stages/voice_gen.py
يولّد صوت الراوي segment-by-segment عبر edge-tts (مع rate متغيّر لكل جزء)،
ويلزقهم مع فجوات صمت (pause_after_ms) عبر FFmpeg.
لو edge-tts فشل (خدمة غير رسمية، ممكن تنكسر)، يرجع تلقائياً لـ gTTS كـ fallback
(بدون تحكم بالسرعة/الوقفات الدقيقة، بس بيضمن استمرار الأتمتة).

المخرج: ملف صوت نهائي واحد (voice.mp3) + قائمة بمدة كل segment (لمزامنة الترجمة لاحقاً)
"""

import asyncio
import os
import subprocess
import tempfile
from gtts import gTTS

VOICE_NAME = "en-US-GuyNeural"  # جرّب أصوات تانية: en-US-JennyNeural, en-GB-RyanNeural ...


async def _edge_tts_segment(text: str, rate: str, out_path: str) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, VOICE_NAME, rate=rate)
    await communicate.save(out_path)


def _edge_tts_segment_sync(text: str, rate: str, out_path: str) -> None:
    asyncio.run(_edge_tts_segment(text, rate, out_path))


def _gtts_fallback_segment(text: str, out_path: str) -> None:
    """gTTS لا يدعم rate/pitch — يستخدم فقط لو edge-tts فشل بالكامل."""
    tts = gTTS(text=text, lang="en")
    tmp_mp3 = out_path.replace(".mp3", "_raw.mp3")
    tts.save(tmp_mp3)
    os.replace(tmp_mp3, out_path)


def _make_silence(duration_ms: int, out_path: str) -> None:
    if duration_ms <= 0:
        return
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"anullsrc=r=24000:cl=mono",
            "-t", str(duration_ms / 1000),
            "-q:a", "9", out_path,
        ],
        check=True, capture_output=True,
    )


def _get_duration_ms(path: str) -> int:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        check=True, capture_output=True, text=True,
    )
    return int(float(result.stdout.strip()) * 1000)


def generate_voice(segments: list[dict], workdir: str) -> tuple[str, list[int]]:
    """
    segments: [{"text": str, "rate": str, "pause_after_ms": int}, ...]
    Returns: (final_voice_path, [duration_ms_per_segment_including_pause, ...])
    """
    os.makedirs(workdir, exist_ok=True)
    part_files = []
    durations = []

    for i, seg in enumerate(segments):
        seg_path = os.path.join(workdir, f"seg_{i:02d}.mp3")
        try:
            _edge_tts_segment_sync(seg["text"], seg.get("rate", "+0%"), seg_path)
        except Exception as e:
            print(f"[voice_gen] edge-tts failed on segment {i} ({e}); falling back to gTTS")
            _gtts_fallback_segment(seg["text"], seg_path)

        seg_duration = _get_duration_ms(seg_path)
        part_files.append(seg_path)
        durations.append(seg_duration)

        pause_ms = seg.get("pause_after_ms", 0)
        if pause_ms > 0:
            silence_path = os.path.join(workdir, f"seg_{i:02d}_silence.mp3")
            _make_silence(pause_ms, silence_path)
            part_files.append(silence_path)
            durations[-1] += pause_ms

    concat_list_path = os.path.join(workdir, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for p in part_files:
            f.write(f"file '{os.path.abspath(p)}'\n")

    final_path = os.path.join(workdir, "voice.mp3")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path,
         "-c", "copy", final_path],
        check=True, capture_output=True,
    )

    return final_path, durations


if __name__ == "__main__":
    demo_segments = [
        {"text": "Ever replayed a conversation for hours after it happened?", "rate": "+0%", "pause_after_ms": 300},
        {"text": "Your brain isn't punishing you. It's trying to protect you.", "rate": "-10%", "pause_after_ms": 500},
    ]
    with tempfile.TemporaryDirectory() as td:
        path, durs = generate_voice(demo_segments, td)
        print(path, durs)
