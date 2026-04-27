"""
Video Editor -- Automated editing pipeline for CC's Content Day system.

Takes raw footage and produces review-ready content:
  1. Detect and remove silence/dead space
  2. Detect and cut filler words (um, uh, hmm)
  3. Apply karaoke captions via content_pipeline
  4. Overlay background music with auto-ducking
  5. Export per-platform formats
  6. Send to Telegram for CC's review

Usage:
    python scripts/video_editor.py edit media/raw/piece_1.mp4 --pillar ai_oracle
    python scripts/video_editor.py clean media/raw/piece_1.mp4
    python scripts/video_editor.py analyze media/raw/piece_1.mp4
    python scripts/video_editor.py review media/exports/piece_1_final.mp4
    python scripts/video_editor.py batch media/raw/ --manifest data/content_day/2026-04-27_template.json

Dependencies: auto-editor, openai-whisper, pydub, ffmpeg
"""

import argparse
import json
import os
import subprocess
import sys
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
EXPORT_DIR = PROJECT_ROOT / "media" / "exports"
MUSIC_DIR = PROJECT_ROOT / "media" / "music"
RAW_DIR = PROJECT_ROOT / "media" / "raw"

# FFmpeg paths
FFMPEG_DIR = os.path.expandvars(
    r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin"
)
FFMPEG = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
FFPROBE = os.path.join(FFMPEG_DIR, "ffprobe.exe")
if not os.path.exists(FFMPEG):
    FFMPEG, FFPROBE = "ffmpeg", "ffprobe"

# Editing defaults
SILENCE_THRESHOLD_DB = -30
SILENCE_MIN_DURATION = 0.4
SILENCE_MARGIN = 0.15
FILLER_WORDS = {
    "um", "uh", "uhh", "umm", "hmm", "hm", "erm", "ah", "ahh",
    "like", "you know", "so", "basically", "literally",
}
WHISPER_MODEL = "small"
MUSIC_VOLUME_DB = -18

# Audio mastering chain (from elite-video-production skill Section 6)
AUDIO_MASTER_FILTER = (
    "agate=threshold=0.01:attack=80:release=840:makeup=1:ratio=3:knee=8,"
    "highpass=f=100:width_type=q:width=0.5,"
    "lowpass=f=10000,"
    "compand=attacks=0:points=-80/-900|-45/-15|-27/-9|0/-7|20/-7:gain=5,"
    "loudnorm=I=-14:TP=-1.0:LRA=11"
)

# Color grade presets (from elite-video-production skill Section 5)
COLOR_GRADES = {
    "teal_orange": (
        "curves=r='0/0 0.25/0.30 0.75/0.82 1/0.95':"
        "g='0/0 0.5/0.50 1/1':"
        "b='0/0.18 0.25/0.35 0.75/0.60 1/0.75',"
        "eq=saturation=0.85:contrast=1.08,vignette=PI/4"
    ),
    "editorial": "eq=saturation=0.6:contrast=1.2,vignette=PI/4",
    "warm": (
        "curves=r='0/0 0.5/0.56 1/0.95':"
        "g='0/0 0.5/0.48 1/1':"
        "b='0/0.22 0.5/0.44 1/0.80',"
        "eq=saturation=0.80:contrast=1.05,vignette=PI/4"
    ),
    "clean": "vignette=PI/4,unsharp=5:5:0.5:3:3:0",
}

# Platform export specifications (from elite-video-production Section 14)
PLATFORM_SPECS = {
    "instagram_reels": {"max_dur": 90, "aspect": "9:16", "res": "1080x1920"},
    "tiktok":          {"max_dur": 180, "aspect": "9:16", "res": "1080x1920"},
    "youtube_shorts":  {"max_dur": 60, "aspect": "9:16", "res": "1080x1920"},
    "linkedin":        {"max_dur": 600, "aspect": "9:16", "res": "1080x1920"},
    "facebook":        {"max_dur": 240, "aspect": "9:16", "res": "1080x1920"},
    "x":               {"max_dur": 140, "aspect": "9:16", "res": "1080x1920"},
}

# Pillar-to-music mood mapping
PILLAR_MUSIC_MOOD = {
    "ai_oracle": "intense",
    "the_becoming": "warm",
    "the_journey": "emotional",
    "ceo_log": "confident",
}


def load_env():
    """Load .env.agents."""
    env_path = PROJECT_ROOT / ".env.agents"
    env_vars = {}
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env_vars[key.strip()] = value.strip()
    return env_vars


# ============================================================================
# STEP 1: SILENCE DETECTION
# ============================================================================

def detect_silence(input_path):
    """Detect silent segments using FFmpeg silencedetect filter."""
    cmd = [
        FFPROBE, "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", input_path,
    ]
    probe = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    duration = 0
    if probe.returncode == 0:
        info = json.loads(probe.stdout)
        duration = float(info.get("format", {}).get("duration", 0))

    cmd = [
        FFMPEG, "-i", input_path, "-af",
        f"silencedetect=noise={SILENCE_THRESHOLD_DB}dB:d={SILENCE_MIN_DURATION}",
        "-f", "null", "-",
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        creationflags=0x08000000 if sys.platform == "win32" else 0,
    )

    silences = []
    current_start = None
    for line in result.stderr.split("\n"):
        if "silence_start:" in line:
            try:
                current_start = float(line.split("silence_start:")[1].strip().split()[0])
            except (ValueError, IndexError):
                pass
        elif "silence_end:" in line and current_start is not None:
            try:
                parts = line.split("silence_end:")[1].strip().split()
                end = float(parts[0])
                dur = end - current_start
                if dur >= SILENCE_MIN_DURATION:
                    silences.append({
                        "start": round(current_start, 3),
                        "end": round(end, 3),
                        "duration": round(dur, 3),
                        "type": "silence",
                    })
                current_start = None
            except (ValueError, IndexError):
                pass

    print(f"  [Silence] Found {len(silences)} silent segments "
          f"(>{SILENCE_MIN_DURATION}s, <{SILENCE_THRESHOLD_DB}dB)")
    return silences, duration


# ============================================================================
# STEP 2: FILLER WORD DETECTION
# ============================================================================

def detect_filler_words(input_path, model_name=WHISPER_MODEL):
    """Detect filler words using Whisper word-level timestamps."""
    try:
        import whisper
    except ImportError:
        print("  [Filler] Whisper not installed, skipping filler detection")
        return [], []

    print(f"  [Filler] Transcribing with Whisper ({model_name})...")
    model = whisper.load_model(model_name)
    result = model.transcribe(input_path, word_timestamps=True)

    all_words = []
    fillers = []
    for seg in result.get("segments", []):
        for w in seg.get("words", []):
            word_text = w["word"].strip().lower().rstrip(".,!?;:")
            word_data = {
                "word": w["word"].strip(),
                "start": round(w["start"], 3),
                "end": round(w["end"], 3),
            }
            all_words.append(word_data)
            if word_text in FILLER_WORDS:
                word_data["type"] = "filler"
                fillers.append(word_data)

    print(f"  [Filler] {len(all_words)} words transcribed, "
          f"{len(fillers)} filler words detected")
    if fillers:
        filler_list = ", ".join(f"'{f['word']}' @ {f['start']:.1f}s" for f in fillers[:5])
        if len(fillers) > 5:
            filler_list += f" ... (+{len(fillers) - 5} more)"
        print(f"  [Filler] Examples: {filler_list}")

    return fillers, all_words


# ============================================================================
# STEP 3: GENERATE CUT LIST
# ============================================================================

def generate_cut_list(silences, fillers, total_duration):
    """Merge silence and filler cuts into a unified cut list."""
    cuts = []

    for s in silences:
        cuts.append({
            "start": max(0, s["start"] + SILENCE_MARGIN),
            "end": max(0, s["end"] - SILENCE_MARGIN),
            "type": "silence",
            "reason": f"Silent for {s['duration']:.1f}s",
        })

    for f in fillers:
        margin = 0.05
        cuts.append({
            "start": max(0, f["start"] - margin),
            "end": f["end"] + margin,
            "type": "filler",
            "reason": f"Filler word: '{f['word']}'",
        })

    cuts.sort(key=lambda x: x["start"])

    # Merge overlapping cuts
    merged = []
    for cut in cuts:
        if cut["end"] <= cut["start"] + 0.05:
            continue
        if merged and cut["start"] <= merged[-1]["end"] + 0.1:
            merged[-1]["end"] = max(merged[-1]["end"], cut["end"])
            merged[-1]["reason"] += f" + {cut['reason']}"
        else:
            merged.append(dict(cut))

    # Build keep segments (inverse of cuts)
    keeps = []
    pos = 0
    for cut in merged:
        if cut["start"] > pos + 0.05:
            keeps.append({"start": pos, "end": cut["start"]})
        pos = cut["end"]
    if pos < total_duration - 0.05:
        keeps.append({"start": pos, "end": total_duration})

    time_removed = sum(c["end"] - c["start"] for c in merged)
    print(f"  [Cuts] {len(merged)} cuts, {time_removed:.1f}s removed "
          f"({total_duration:.1f}s -> {total_duration - time_removed:.1f}s)")

    return {
        "cuts": merged,
        "keeps": keeps,
        "total_duration": total_duration,
        "edited_duration": total_duration - time_removed,
        "time_removed": round(time_removed, 2),
    }


# ============================================================================
# STEP 4: APPLY CUTS
# ============================================================================

def apply_cuts(input_path, cut_list, output_path):
    """Apply cuts using FFmpeg concat demuxer."""
    keeps = cut_list.get("keeps", [])
    if not keeps:
        print("  [Edit] No segments to keep!")
        return None

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_dir = EXPORT_DIR / "_tmp_cuts"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Cut each keep segment.
    #
    # CRITICAL: we re-encode each segment instead of stream-copying. With
    # `-ss BEFORE -i` and `-c copy`, FFmpeg snaps to the nearest preceding
    # keyframe, producing a frozen frame at the start of every segment until
    # the next keyframe. Voice content with karaoke captions cannot tolerate
    # that — across 30+ cuts on a 5-min video the output looks visibly broken.
    # Transcoding to libx264/aac at frame-accurate boundaries is slower but
    # correct. Using `-ss` AFTER `-i` (slow seek) gets us frame-accurate input.
    segment_files = []
    for i, seg in enumerate(keeps):
        seg_path = str(tmp_dir / f"seg_{i:04d}.mp4")
        duration = seg["end"] - seg["start"]
        cmd = [
            FFMPEG, "-y",
            "-i", input_path,
            "-ss", str(seg["start"]), "-t", str(duration),
            "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-avoid_negative_ts", "make_zero",
            "-pix_fmt", "yuv420p",
            seg_path,
        ]
        r = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            creationflags=0x08000000 if sys.platform == "win32" else 0,
        )
        if r.returncode == 0 and os.path.exists(seg_path):
            segment_files.append(seg_path)
        else:
            err_tail = (r.stderr or "")[-200:]
            print(f"  [Edit] Segment {i} failed: {err_tail}")

    if not segment_files:
        print("  [Edit] No segments produced!")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None

    # Concat all segments (now safe to stream-copy because all segments share
    # codec parameters from the transcode step above).
    concat_list = str(tmp_dir / "concat.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for sf in segment_files:
            safe = sf.replace("\\", "/")
            f.write(f"file '{safe}'\n")

    cmd = [
        FFMPEG, "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list, "-c", "copy", output_path,
    ]
    r = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        creationflags=0x08000000 if sys.platform == "win32" else 0,
    )

    # Cleanup
    shutil.rmtree(tmp_dir, ignore_errors=True)

    if r.returncode == 0 and os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  [Edit] Output: {os.path.basename(output_path)} ({size_mb:.1f} MB)")
        return output_path
    else:
        print(f"  [Edit] Concat failed: {(r.stderr or '')[:200]}")
        return None


# ============================================================================
# STEP 5: ADD CAPTIONS (via content_pipeline)
# ============================================================================

def add_captions(input_path, output_path):
    """Run content_pipeline's transcribe + karaoke caption on the edited video."""
    pipeline_script = str(SCRIPTS_DIR / "content_pipeline.py")
    if not os.path.exists(pipeline_script):
        print("  [Captions] content_pipeline.py not found, skipping")
        return input_path

    # Import and use directly
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        import content_pipeline as cp

        transcription = cp.transcribe(input_path)
        if not transcription:
            print("  [Captions] Transcription failed, using uncaptioned video")
            return input_path

        ass_path = os.path.splitext(input_path)[0] + ".karaoke.ass"
        cp.generate_karaoke_ass(transcription["words"], ass_path)

        result = cp.process_video(input_path, output_path, ass_path)
        if result:
            return output_path
        return input_path
    except Exception as e:
        print(f"  [Captions] Error: {e}")
        return input_path

# ============================================================================
# STEP 5b: AUDIO MASTERING
# ============================================================================

def master_audio(input_path, output_path):
    """Apply broadcast-standard audio mastering chain.
    Gate -> Highpass -> Lowpass -> Compand -> Loudnorm to -14 LUFS.
    """
    cmd = [
        FFMPEG, "-y", "-i", input_path,
        "-af", AUDIO_MASTER_FILTER,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        output_path,
    ]
    r = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        creationflags=0x08000000 if sys.platform == "win32" else 0,
    )
    if r.returncode == 0:
        print(f"  [Audio] Mastered to -14 LUFS")
        return output_path
    else:
        print(f"  [Audio] Mastering failed: {(r.stderr or '')[:200]}")
        return input_path


# ============================================================================
# STEP 5c: COLOR GRADING
# ============================================================================

def color_grade(input_path, output_path, preset="warm"):
    """Apply color grade preset via FFmpeg curves and EQ."""
    grade_filter = COLOR_GRADES.get(preset)
    if not grade_filter:
        print(f"  [Grade] Unknown preset '{preset}', skipping")
        return input_path

    cmd = [
        FFMPEG, "-y", "-i", input_path,
        "-vf", grade_filter,
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "copy",
        output_path,
    ]
    r = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        creationflags=0x08000000 if sys.platform == "win32" else 0,
    )
    if r.returncode == 0:
        print(f"  [Grade] Applied '{preset}' color grade")
        return output_path
    else:
        print(f"  [Grade] Grading failed: {(r.stderr or '')[:200]}")
        return input_path


# ============================================================================
# STEP 8: MULTI-PLATFORM EXPORT
# ============================================================================

def export_platforms(input_path, platforms=None):
    """Export video in platform-specific formats."""
    if platforms is None:
        platforms = list(PLATFORM_SPECS.keys())

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    base = os.path.splitext(os.path.basename(input_path))[0]
    exports = {}

    for plat in platforms:
        spec = PLATFORM_SPECS.get(plat)
        if not spec:
            print(f"  [Export] Unknown platform '{plat}', skipping")
            continue

        out_path = str(EXPORT_DIR / f"{base}_{plat}.mp4")
        w, h = spec["res"].split("x")

        cmd = [
            FFMPEG, "-y", "-i", input_path,
            "-t", str(spec["max_dur"]),
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                   f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black",
            "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            out_path,
        ]
        r = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            creationflags=0x08000000 if sys.platform == "win32" else 0,
        )
        if r.returncode == 0:
            size_mb = os.path.getsize(out_path) / (1024 * 1024)
            exports[plat] = out_path
            print(f"  [Export] {plat}: {os.path.basename(out_path)} ({size_mb:.1f} MB)")
        else:
            print(f"  [Export] {plat}: FAILED")

    print(f"  [Export] {len(exports)}/{len(platforms)} platforms exported")
    return exports


# ============================================================================
# STEP 6: BACKGROUND MUSIC
# ============================================================================

def add_music(input_path, output_path, pillar="ceo_log"):
    """Overlay background music with REAL auto-ducking under speech.

    Earlier versions of this function only applied a static volume cut,
    which is not ducking — the music sat at -18dB the whole time, drowning
    quiet speech segments and competing with loud ones. Real ducking uses
    `sidechaincompress` keyed off the speech track: when speech is present,
    the compressor pulls music volume down dynamically; when speech is
    quiet/silent, music swells back up.

    Chain:
      [0:a]                                 -> speech (sidechain key)
      [1:a] aloop -> volume preset          -> music (signal)
      [music][speech] sidechaincompress     -> ducked music
      [speech][ducked] amix                 -> final mix
    """
    mood = PILLAR_MUSIC_MOOD.get(pillar, "confident")
    music_file = find_music_track(mood)
    if not music_file:
        print(f"  [Music] No tracks found for mood '{mood}' in media/music/")
        print(f"  [Music] Add .mp3 files to media/music/{mood}/ to enable")
        shutil.copy2(input_path, output_path)
        return output_path

    # `-stream_loop -1` on the music input is cleaner than `aloop` (no in-
    # memory ringbuffer; FFmpeg loops the demuxer indefinitely). `-shortest`
    # then trims the loop to the video's audio duration.
    filter_complex = (
        # Music: lower base volume + ensure stereo + 48kHz to match speech
        "[1:a]volume=0.6,aresample=48000,aformat=channel_layouts=stereo[music_pre];"
        # Speech: split — one branch feeds amix, one feeds sidechain key
        "[0:a]asplit=2[speech][skey];"
        # Sidechain compressor: when speech is present, music gets ducked.
        # threshold=0.05 fires on speech levels; ratio=8 is aggressive duck;
        # attack=5ms is fast enough to catch syllables; release=300ms lets
        # music swell back up between phrases.
        "[music_pre][skey]sidechaincompress=threshold=0.05:ratio=8:"
        "attack=5:release=300:makeup=1[music_ducked];"
        # Final mix: speech full, ducked music underneath.
        "[speech][music_ducked]amix=inputs=2:duration=first:"
        "dropout_transition=2:weights=1.0 0.7[aout]"
    )

    cmd = [
        FFMPEG, "-y",
        "-i", input_path,
        "-stream_loop", "-1", "-i", music_file,
        "-filter_complex", filter_complex,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", output_path,
    ]

    r = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        creationflags=0x08000000 if sys.platform == "win32" else 0,
    )
    if r.returncode == 0:
        print(f"  [Music] Added '{os.path.basename(music_file)}' (mood: {mood}, ducked)")
        return output_path
    else:
        err_tail = (r.stderr or "")[-300:]
        print(f"  [Music] Sidechain mix failed, falling back to static -18dB mix")
        print(f"  [Music] Error tail: {err_tail}")
        # Fallback: static mix (the original behavior). Better to ship music
        # at a fixed level than ship none at all.
        fallback_filter = (
            f"[1:a]volume={MUSIC_VOLUME_DB}dB,aresample=48000,"
            f"aformat=channel_layouts=stereo[music];"
            f"[0:a][music]amix=inputs=2:duration=first:"
            f"dropout_transition=2[aout]"
        )
        fallback_cmd = [
            FFMPEG, "-y",
            "-i", input_path,
            "-stream_loop", "-1", "-i", music_file,
            "-filter_complex", fallback_filter,
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", output_path,
        ]
        r2 = subprocess.run(
            fallback_cmd, capture_output=True, text=True, encoding="utf-8",
            creationflags=0x08000000 if sys.platform == "win32" else 0,
        )
        if r2.returncode == 0:
            print(f"  [Music] Static-mix fallback succeeded")
            return output_path
        print(f"  [Music] Fallback also failed, using original audio")
        shutil.copy2(input_path, output_path)
        return output_path


def find_music_track(mood):
    """Find a music track matching the mood."""
    mood_dir = MUSIC_DIR / mood
    if mood_dir.exists():
        tracks = list(mood_dir.glob("*.mp3")) + list(mood_dir.glob("*.wav"))
        if tracks:
            import random
            return str(random.choice(tracks))

    # Fall back to any track in the music dir
    if MUSIC_DIR.exists():
        tracks = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.wav"))
        if tracks:
            import random
            return str(random.choice(tracks))

    return None


# ============================================================================
# STEP 7: TELEGRAM REVIEW
# ============================================================================

def send_for_review(video_path, piece_info=None):
    """Send edited video to CC's Telegram for review."""
    env = load_env()
    token = (
        env.get("MAVEN_TELEGRAM_BOT_TOKEN")
        or env.get("BRAVO_TELEGRAM_BOT_TOKEN")
        or env.get("TELEGRAM_BOT_TOKEN")
    )
    chat_ids_raw = (
        env.get("MAVEN_TELEGRAM_ALLOWED_USERS")
        or env.get("TELEGRAM_ALLOWED_USERS")
        or ""
    )
    chat_ids = [c.strip() for c in chat_ids_raw.split(",") if c.strip()]

    if not token or not chat_ids:
        print("  [Review] Telegram not configured, skipping review notification")
        # Still send a text notification via notify.py
        try:
            from notify import notify
            notify(
                f"Video ready for review: {os.path.basename(video_path)}",
                category="content-published",
            )
        except Exception:
            pass
        return False

    # Get video info
    file_size = os.path.getsize(video_path) / (1024 * 1024)
    duration_str = "unknown"
    try:
        cmd = [FFPROBE, "-v", "quiet", "-print_format", "json", "-show_format", video_path]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if r.returncode == 0:
            info = json.loads(r.stdout)
            dur = float(info.get("format", {}).get("duration", 0))
            duration_str = f"{int(dur)}s"
    except Exception:
        pass

    # Build caption
    pillar = piece_info.get("pillar", "unknown") if piece_info else "unknown"
    piece_num = piece_info.get("piece_number", "?") if piece_info else "?"
    hook = piece_info.get("hook", "") if piece_info else ""

    caption = (
        f"Content Review: Piece #{piece_num} - {pillar}\n"
        f"Hook: {hook[:80]}\n"
        f"Duration: {duration_str} | Size: {file_size:.1f} MB\n\n"
        f"Reply 'approve' to schedule\n"
        f"Reply with feedback to re-edit"
    )

    try:
        import requests
    except ImportError:
        print("  [Review] requests not installed")
        return False

    # Telegram bot API hard limit for sendVideo is 50 MB. Modern 1080p clips
    # at CRF 18 routinely blow past that on 30-90s content, so the original
    # "send a text-only notification and bail" path silently broke the
    # review UX. The turnkey behavior: shrink the video to fit, ship the
    # video, fall back to text only if even the shrunk version is too big.
    TELEGRAM_LIMIT_MB = 50
    review_video_path = video_path

    def _safe_json(resp):
        """Telegram normally returns JSON, but proxies/timeouts can return
        empty bodies or HTML error pages. Don't crash on those."""
        try:
            return resp.json() or {}
        except Exception:
            return {}

    if file_size > TELEGRAM_LIMIT_MB:
        # Auto-shrink: re-encode at a higher CRF + cap height. CRF 28 on 720p
        # is plenty for phone-screen review, and lands a typical 90s clip
        # well under 50 MB.
        shrunk = os.path.splitext(video_path)[0] + ".review.mp4"
        target_height = 720 if file_size < 200 else 540
        shrink_cmd = [
            FFMPEG, "-y", "-i", video_path,
            "-vf", f"scale=-2:{target_height}",
            "-c:v", "libx264", "-crf", "28", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            shrunk,
        ]
        print(f"  [Review] Video {file_size:.0f}MB > {TELEGRAM_LIMIT_MB}MB, "
              f"auto-shrinking to {target_height}p for Telegram preview...")
        sr = subprocess.run(
            shrink_cmd, capture_output=True, text=True, encoding="utf-8",
            creationflags=0x08000000 if sys.platform == "win32" else 0,
        )
        if sr.returncode == 0 and os.path.exists(shrunk):
            shrunk_size_mb = os.path.getsize(shrunk) / (1024 * 1024)
            if shrunk_size_mb <= TELEGRAM_LIMIT_MB:
                print(f"  [Review] Shrunk to {shrunk_size_mb:.1f}MB")
                review_video_path = shrunk
                # Annotate the caption so CC knows the phone preview is a
                # smaller transcode and the full version is still on disk.
                caption += f"\n\n(Preview shrunk to {target_height}p; full version: {os.path.basename(video_path)})"
            else:
                print(f"  [Review] Shrunk to {shrunk_size_mb:.1f}MB — still over limit; sending text only")
                # Clean up the failed shrink
                try: os.remove(shrunk)
                except Exception: pass
                review_video_path = None
        else:
            err_tail = (sr.stderr or "")[-200:]
            print(f"  [Review] Shrink failed: {err_tail}")
            review_video_path = None

        if review_video_path is None:
            # Last-resort text-only fallback
            for chat_id in chat_ids:
                try:
                    requests.post(
                        f"https://api.telegram.org/bot{token}/sendMessage",
                        json={"chat_id": chat_id,
                              "text": caption + f"\n\n(File too large for Telegram even after shrink)"},
                        timeout=10,
                    )
                except Exception:
                    pass
            return True

    ok = False
    for chat_id in chat_ids:
        try:
            with open(review_video_path, "rb") as vf:
                resp = requests.post(
                    f"https://api.telegram.org/bot{token}/sendVideo",
                    data={"chat_id": chat_id, "caption": caption},
                    files={"video": (os.path.basename(review_video_path), vf, "video/mp4")},
                    timeout=120,
                )
                payload = _safe_json(resp)
                if payload.get("ok"):
                    ok = True
                    print(f"  [Review] Sent to Telegram for review")
                else:
                    err = payload.get("description") or f"HTTP {resp.status_code}"
                    print(f"  [Review] Telegram error: {err}")
        except Exception as e:
            print(f"  [Review] Send failed: {e}")

    # Clean up the shrunken preview if we made one
    if review_video_path != video_path and review_video_path and os.path.exists(review_video_path):
        try: os.remove(review_video_path)
        except Exception: pass

    return ok


# ============================================================================
# MAIN COMMANDS
# ============================================================================

def cmd_analyze(input_path):
    """Analyze video and output cut list without editing."""
    print(f"\n{'='*60}")
    print(f"  Video Analysis: {os.path.basename(input_path)}")
    print(f"{'='*60}\n")

    silences, duration = detect_silence(input_path)
    fillers, all_words = detect_filler_words(input_path)
    cut_list = generate_cut_list(silences, fillers, duration)

    # Save cut list
    out_path = os.path.splitext(input_path)[0] + ".cuts.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cut_list, f, indent=2)

    print(f"\n  Cut list saved: {out_path}")
    print(f"  Total: {len(cut_list['cuts'])} cuts, "
          f"{cut_list['time_removed']}s removed")
    return cut_list


def cmd_clean(input_path, output_path=None):
    """Remove silence and fillers only (no captions, no music)."""
    if not output_path:
        base = os.path.splitext(os.path.basename(input_path))[0]
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(EXPORT_DIR / f"{base}_clean_{ts}.mp4")

    print(f"\n{'='*60}")
    print(f"  Clean Edit: {os.path.basename(input_path)}")
    print(f"{'='*60}\n")

    silences, duration = detect_silence(input_path)
    fillers, _ = detect_filler_words(input_path)
    cut_list = generate_cut_list(silences, fillers, duration)

    if not cut_list["cuts"]:
        print("  No cuts needed -- video is clean")
        shutil.copy2(input_path, output_path)
        return output_path

    return apply_cuts(input_path, cut_list, output_path)


def cmd_edit(input_path, pillar="ceo_log", skip_music=False,
             skip_captions=False, skip_review=False, skip_grade=False,
             skip_master=False, grade_preset=None, piece_info=None):
    """Full edit pipeline: clean -> master audio -> grade -> captions -> music -> review."""
    base = os.path.splitext(os.path.basename(input_path))[0]
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    intermediates = []  # track files to clean up

    # Map pillar to default grade preset
    pillar_grades = {
        "ai_oracle": "teal_orange",
        "the_becoming": "warm",
        "the_journey": "warm",
        "ceo_log": "editorial",
    }
    if grade_preset is None:
        grade_preset = pillar_grades.get(pillar, "warm")

    print(f"\n{'='*60}")
    print(f"  Full Edit Pipeline")
    print(f"  Input: {os.path.basename(input_path)}")
    print(f"  Pillar: {pillar} | Grade: {grade_preset}")
    print(f"{'='*60}\n")

    # Step 1-3: Detect and cut
    print("[1/8] Detecting silence...")
    silences, duration = detect_silence(input_path)

    print("[2/8] Detecting filler words...")
    fillers, all_words = detect_filler_words(input_path)

    print("[3/8] Applying cuts...")
    cut_list = generate_cut_list(silences, fillers, duration)

    if cut_list["cuts"]:
        cleaned_path = str(EXPORT_DIR / f"{base}_cleaned_{ts}.mp4")
        cleaned = apply_cuts(input_path, cut_list, cleaned_path)
        if not cleaned:
            print("  Cut application failed, using original")
            cleaned = input_path
        else:
            intermediates.append(cleaned_path)
    else:
        print("  No cuts needed")
        cleaned = input_path

    # Step 4: Audio mastering
    current = cleaned
    if not skip_master:
        print("[4/8] Mastering audio (-14 LUFS)...")
        mastered_path = str(EXPORT_DIR / f"{base}_mastered_{ts}.mp4")
        current = master_audio(current, mastered_path)
        if current == mastered_path:
            intermediates.append(mastered_path)
    else:
        print("[4/8] Audio mastering skipped")

    # Step 5: Color grading
    if not skip_grade:
        print(f"[5/8] Color grading ({grade_preset})...")
        graded_path = str(EXPORT_DIR / f"{base}_graded_{ts}.mp4")
        current = color_grade(current, graded_path, grade_preset)
        if current == graded_path:
            intermediates.append(graded_path)
    else:
        print("[5/8] Color grading skipped")

    # Step 6: Captions
    if not skip_captions:
        print("[6/8] Adding karaoke captions...")
        captioned_path = str(EXPORT_DIR / f"{base}_captioned_{ts}.mp4")
        current = add_captions(current, captioned_path)
        if current == captioned_path:
            intermediates.append(captioned_path)
    else:
        print("[6/8] Captions skipped")

    # Step 7: Music
    if not skip_music:
        print("[7/8] Adding background music...")
        final_path = str(EXPORT_DIR / f"{base}_final_{ts}.mp4")
        current = add_music(current, final_path, pillar)
    else:
        print("[7/8] Music skipped")

    # Step 8: Telegram review
    if not skip_review:
        print("[8/8] Sending for review...")
        send_for_review(current, piece_info)
    else:
        print("[8/8] Review skipped")

    # Cleanup intermediates (keep final only)
    for tmp in intermediates:
        if tmp and tmp != current and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass

    # Save cut list alongside output for reference
    cuts_path = os.path.splitext(current)[0] + ".cuts.json"
    with open(cuts_path, "w", encoding="utf-8") as f:
        json.dump(cut_list, f, indent=2)

    # Format-safe summary: edited_duration / total_duration may be missing
    # when no cuts were applied (cut_list comes from a pristine no-op input).
    def _fmt_secs(v):
        if v is None: return "?"
        try: return f"{float(v):.1f}s"
        except (TypeError, ValueError): return str(v)

    print(f"\n{'='*60}")
    print(f"  Edit Complete")
    print(f"  Output: {current}")
    print(f"  Duration: {_fmt_secs(cut_list.get('edited_duration'))} "
          f"(was {_fmt_secs(cut_list.get('total_duration'))})")
    print(f"  Cuts: {len(cut_list.get('cuts', []))} | "
          f"Removed: {_fmt_secs(cut_list.get('time_removed'))}")
    print(f"{'='*60}\n")

    return current


def cmd_batch(raw_dir, manifest_path=None):
    """Edit all videos in a directory, optionally using manifest for metadata."""
    manifest = None
    if manifest_path:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    raw = Path(raw_dir)
    videos = sorted(raw.glob("*.mp4")) + sorted(raw.glob("*.mov")) + sorted(raw.glob("*.mkv"))

    if not videos:
        print(f"No video files found in {raw_dir}")
        return

    print(f"\n{'='*60}")
    print(f"  Batch Edit: {len(videos)} videos")
    print(f"{'='*60}\n")

    results = []
    pieces = manifest.get("pieces", []) if manifest else []

    for i, video in enumerate(videos):
        piece_info = pieces[i] if i < len(pieces) else None
        pillar = piece_info.get("pillar", "ceo_log") if piece_info else "ceo_log"

        print(f"\n--- Video {i+1}/{len(videos)}: {video.name} ---\n")
        result = cmd_edit(str(video), pillar=pillar, piece_info=piece_info)
        results.append({"input": str(video), "output": result})

    print(f"\n{'='*60}")
    print(f"  Batch Complete: {len(results)} videos edited")
    print(f"{'='*60}")
    return results


def cmd_review(video_path):
    """Send an already-edited video to Telegram for review."""
    print(f"Sending {os.path.basename(video_path)} for review...")
    send_for_review(video_path)


def cmd_export(input_path, platforms=None):
    """Export video in platform-specific formats."""
    print(f"\n{'='*60}")
    print(f"  Multi-Platform Export: {os.path.basename(input_path)}")
    print(f"{'='*60}\n")
    return export_platforms(input_path, platforms)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        prog="video_editor.py",
        description="CC's Automated Video Editor -- raw footage to review-ready content",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # Edit
    edit_p = sub.add_parser("edit", help="Full edit pipeline (8 steps)")
    edit_p.add_argument("input", help="Path to raw video")
    edit_p.add_argument("--pillar", default="ceo_log",
                        choices=["ai_oracle", "the_becoming", "the_journey", "ceo_log"])
    edit_p.add_argument("--grade", default=None,
                        choices=["teal_orange", "editorial", "warm", "clean"],
                        help="Color grade preset (auto-selected from pillar if omitted)")
    edit_p.add_argument("--skip-music", action="store_true")
    edit_p.add_argument("--skip-captions", action="store_true")
    edit_p.add_argument("--skip-review", action="store_true")
    edit_p.add_argument("--skip-grade", action="store_true")
    edit_p.add_argument("--skip-master", action="store_true")

    # Clean
    clean_p = sub.add_parser("clean", help="Remove silence + fillers only")
    clean_p.add_argument("input", help="Path to raw video")
    clean_p.add_argument("--output", help="Output path")

    # Analyze
    analyze_p = sub.add_parser("analyze", help="Generate cut list without editing")
    analyze_p.add_argument("input", help="Path to raw video")

    # Review
    review_p = sub.add_parser("review", help="Send video to Telegram for review")
    review_p.add_argument("input", help="Path to edited video")

    # Export
    export_p = sub.add_parser("export", help="Export to platform-specific formats")
    export_p.add_argument("input", help="Path to edited video")
    export_p.add_argument("--platforms", nargs="+", default=None,
                          help="Platforms to export for (default: all)")

    # Batch
    batch_p = sub.add_parser("batch", help="Edit all videos in a directory")
    batch_p.add_argument("dir", help="Directory with raw videos")
    batch_p.add_argument("--manifest", help="Content day manifest JSON")

    args = parser.parse_args()

    if args.command == "edit":
        cmd_edit(args.input, args.pillar, args.skip_music,
                 args.skip_captions, args.skip_review,
                 args.skip_grade, args.skip_master, args.grade)
    elif args.command == "clean":
        cmd_clean(args.input, args.output)
    elif args.command == "analyze":
        cmd_analyze(args.input)
    elif args.command == "review":
        cmd_review(args.input)
    elif args.command == "export":
        cmd_export(args.input, args.platforms)
    elif args.command == "batch":
        cmd_batch(args.dir, args.manifest)


if __name__ == "__main__":
    main()
