"""
stages/video_assembler.py
يركّب الفيديو النهائي:
- صورة لكل segment + حركة Ken Burns (zoom/pan تدريجي) بمدة توازي مدة الصوت لنفس الـ segment
- whoosh.mp3 عند كل انتقال بين صورتين
- pop.mp3 خفيف عند بداية الفيديو (لحظة الهوك)
- موسيقى خلفية ثابتة طول الفيديو بمستوى صوت منخفض تحت الراوي
- ترجمة نصية (subtitles) مبنية على توقيت segments الفعلي
- إخراج عمودي 1080x1920، أقل من 60 ثانية
"""

import glob
import os
import random
import subprocess

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
SFX_DIR = os.path.join(ASSETS_DIR, "sfx")
MUSIC_DIR = os.path.join(ASSETS_DIR, "music")

WIDTH, HEIGHT = 1080, 1920
MUSIC_VOLUME_DB = -22  # منخفض جداً تحت صوت الراوي
SFX_VOLUME_DB = -8


def _pick_random(directory: str, exts=(".mp3", ".wav")) -> str | None:
    files = [f for f in glob.glob(os.path.join(directory, "*")) if f.lower().endswith(exts)]
    return random.choice(files) if files else None


def _make_ken_burns_clip(image_path: str, duration_ms: int, out_path: str, zoom_in: bool = True) -> None:
    """صورة ثابتة + zoom/pan تدريجي بمدة duration_ms، مُخرج عمودي."""
    duration_s = max(duration_ms / 1000, 0.5)
    fps = 30
    total_frames = int(duration_s * fps)
    zoom_expr = (
        f"zoom+0.0015" if zoom_in else f"zoom-0.0015"
    )
    filter_complex = (
        f"scale={WIDTH*2}:{HEIGHT*2},"
        f"zoompan=z='{zoom_expr}':d={total_frames}:s={WIDTH}x{HEIGHT}:fps={fps}"
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-loop", "1", "-i", image_path,
            "-vf", filter_complex, "-t", str(duration_s),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path,
        ],
        check=True, capture_output=True,
    )


def _concat_video_clips(clip_paths: list[str], out_path: str) -> None:
    list_path = out_path + "_list.txt"
    with open(list_path, "w") as f:
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
         "-c", "copy", out_path],
        check=True, capture_output=True,
    )
    os.remove(list_path)


def _build_srt(segments: list[dict], durations_ms: list[int], out_path: str) -> None:
    def fmt(ms: int) -> str:
        h, ms_rem = divmod(ms, 3600000)
        m, ms_rem = divmod(ms_rem, 60000)
        s, ms_rem = divmod(ms_rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms_rem:03d}"

    lines = []
    cursor = 0
    for i, (seg, dur) in enumerate(zip(segments, durations_ms), start=1):
        start = cursor
        end = cursor + dur
        lines.append(str(i))
        lines.append(f"{fmt(start)} --> {fmt(end)}")
        lines.append(seg["text"])
        lines.append("")
        cursor = end

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def assemble_video(
    image_paths: list[str],
    segment_durations_ms: list[int],
    segments: list[dict],
    voice_path: str,
    workdir: str,
) -> str:
    os.makedirs(workdir, exist_ok=True)

    # 1) صورة متحركة لكل segment
    clip_paths = []
    for i, (img, dur) in enumerate(zip(image_paths, segment_durations_ms)):
        clip_path = os.path.join(workdir, f"clip_{i:02d}.mp4")
        _make_ken_burns_clip(img, dur, clip_path, zoom_in=(i % 2 == 0))
        clip_paths.append(clip_path)

    silent_video_path = os.path.join(workdir, "silent_video.mp4")
    _concat_video_clips(clip_paths, silent_video_path)

    # 2) ترجمة
    srt_path = os.path.join(workdir, "subtitles.srt")
    _build_srt(segments, segment_durations_ms, srt_path)

    # 3) الصوت: راوي + موسيقى خلفية + SFX (whoosh عند كل انتقال، pop بالبداية)
    music_path = _pick_random(MUSIC_DIR)
    pop_path = os.path.join(SFX_DIR, "pop.mp3")
    whoosh_path = os.path.join(SFX_DIR, "whoosh.mp3")

    audio_inputs = ["-i", voice_path]
    filter_parts = ["[0:a]volume=1.0[voice]"]
    mix_inputs = ["[voice]"]
    input_idx = 1

    if music_path and os.path.exists(music_path):
        audio_inputs += ["-i", music_path]
        filter_parts.append(f"[{input_idx}:a]aloop=loop=-1:size=2e9,volume={MUSIC_VOLUME_DB}dB[music]")
        mix_inputs.append("[music]")
        input_idx += 1

    if os.path.exists(pop_path):
        audio_inputs += ["-i", pop_path]
        filter_parts.append(f"[{input_idx}:a]volume={SFX_VOLUME_DB}dB,adelay=0|0[pop]")
        mix_inputs.append("[pop]")
        input_idx += 1

    if os.path.exists(whoosh_path):
        cursor = 0
        for dur in segment_durations_ms[:-1]:
            cursor += dur
            audio_inputs += ["-i", whoosh_path]
            delay_ms = max(cursor - 150, 0)
            filter_parts.append(
                f"[{input_idx}:a]volume={SFX_VOLUME_DB}dB,adelay={delay_ms}|{delay_ms}[whoosh{input_idx}]"
            )
            mix_inputs.append(f"[whoosh{input_idx}]")
            input_idx += 1

    filter_complex = ";".join(filter_parts) + ";" + "".join(mix_inputs) + \
        f"amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=0[aout]"

    mixed_audio_path = os.path.join(workdir, "mixed_audio.mp3")
    subprocess.run(
        ["ffmpeg", "-y", *audio_inputs, "-filter_complex", filter_complex,
         "-map", "[aout]", mixed_audio_path],
        check=True, capture_output=True,
    )

    # 4) دمج الفيديو + الصوت + حرق الترجمة
    final_path = os.path.join(workdir, "final_video.mp4")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", silent_video_path, "-i", mixed_audio_path,
            "-vf", f"subtitles={srt_path}:force_style='FontSize=18,PrimaryColour=&HFFFFFF&,Outline=2,Alignment=2'",
            "-c:v", "libx264", "-c:a", "aac", "-shortest", final_path,
        ],
        check=True, capture_output=True,
    )

    return final_path
