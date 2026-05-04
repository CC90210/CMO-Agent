# Integration: claude-video

> **Repo:** https://github.com/bradautomates/claude-video (MIT, by Bradley Bonanno)
> **Local clone:** `vendor/claude-video/`
> **Stack:** Pure Python 3 stdlib + `yt-dlp`, `ffmpeg`, `ffprobe`. Optional Whisper API (Groq preferred, OpenAI fallback).
> **Install size:** ~235 KB.

## What it actually is — and what it isn't

**It is:** a read-only "video → understanding" pipe. You hand it a video URL or local file. It downloads, samples JPEG frames at adaptive FPS, pulls a timestamped transcript (native VTT first, Whisper API fallback), and prints a markdown report with frame paths and timestamps so Claude can `Read()` each JPEG and "watch" the video.

**It is NOT:**
- A Remotion replacement (it doesn't generate video).
- A video editor or chopper (it never modifies the source).
- An EDL / clip extractor (no scene detection, no auto-cuts).
- A compositor (no compositing, no overlays).

CC's earlier framing — "instead of Remotion, to chop up the video" — is a misread. Remotion stays for compositing. This is a *new layer*, slotted upstream.

## Where it fits in Maven's pipeline

**Slot it before `ad-engine/` runs, never inside or after.** Three concrete use cases:

### 1. Pre-publish QA on Remotion ad creative
After `ad-engine/scripts/render_batch.js` produces an ad MP4, run `/watch <output.mp4> "any frame where text gets clipped, brand color drifts off the OASIS cyan, or the logo rendering looks wrong?"` This catches QA issues without recording a Loom for human review. Use as automated gate before Late upload.

### 2. Competitive teardown / hook research
Before drafting an OASIS ad concept or YouTube hook, paste a viral reference video (TikTok, IG Reel, YouTube Short) and ask:
- "What's the hook structure in the first 3 seconds?"
- "What's on-screen text vs spoken word balance?"
- "How many cuts in the first 15 seconds?"

Output feeds `agents/ad-strategist` brief.

### 3. Bug-repro from CC's screen recordings
CC drops a `.mov`. Maven runs `/watch screen.mov "what happened around 0:45 — error message visible?"` Faster than CC describing the bug.

### 4. Long-form repurposing seed
Run on a 30-min Loom or podcast → identify clip-worthy moments by question — *"which moments would make the strongest 60-second Reel?"* Output is descriptive (timestamps + summary), then a real cutter (FFmpeg + auto-editor) does the actual chopping.

## Install

Two options.

### Option A — Claude Code plugin (recommended for daily use)
```bash
# In any Claude Code session
/plugin marketplace add bradautomates/claude-video
/plugin install watch@claude-video
# Then: /watch <url-or-path> [optional question]
```

### Option B — Standalone CLI (already cloned to `vendor/claude-video/`)
```bash
cd /c/Users/User/CMO-Agent/vendor/claude-video
python3 scripts/setup.py            # checks/installs ffmpeg + yt-dlp
# Optional: configure Whisper API key
mkdir -p ~/.config/watch && echo 'GROQ_API_KEY=...' >> ~/.config/watch/.env

# Use it:
python3 scripts/watch.py "https://youtu.be/<id>" --start 0:30 --end 0:45
python3 scripts/watch.py /path/to/local.mp4 --max-frames 30
```

## Public API (CLI flags)

```
python3 scripts/watch.py <source> [options]

  --start / --end SS|MM:SS|HH:MM:SS   Focused mode (denser fps, transcript filtered)
  --max-frames N                       Cap frames (max 100, default duration-aware)
  --resolution W                       Frame width (default 512px, 1024 for text)
  --fps F                              Sampling fps (clamp 2.0)
  --whisper groq|openai                Override transcription provider
  --no-whisper                         Skip transcription, frames only
  --out-dir DIR                        Override work directory
```

**Source types accepted:** any yt-dlp-supported URL (YouTube, Loom, TikTok, X, Vimeo, Instagram public posts) OR local `.mp4 / .mov / .mkv / .webm / .m4v / .avi / .flv / .wmv`.

**Frame budgets (auto-adaptive in `scripts/frames.py`):**
- ≤30 sec → ~30 frames
- 30 sec – 3 min → ~60 frames
- 3 – 10 min → ~80 frames
- 10 min+ → 100 frames sparse + warning to use `--start/--end`

**Whisper fallback:** only kicks in if the source has no native VTT subs. 25 MB audio cap (~50 min). Public URLs only — no private-platform auth.

## Caveats

- **No scene detection** — if you need actual auto-cuts of a long video into clips, this isn't the tool. Use `PySceneDetect` + word-timestamped Whisper + your own logic from `brain/VIDEO_PRODUCTION_BIBLE.md`.
- **No object/face tracking** — frames are raw JPEGs; Claude does the reading.
- **Not a renderer** — never produces an output video. Read-only.
- **Cost discipline** — Whisper API calls aren't free. For repeat analyses of the same video, cache the transcript yourself.

## Trigger phrases (what CC says → run this)

| Trigger | Action |
|---|---|
| "Watch this video" / "tell me what's in this clip" | `python3 vendor/claude-video/scripts/watch.py <url>` then read frames |
| "QA this ad before we ship" | run after `ad-engine/render_batch.js`, before R2 upload |
| "What's the hook on this viral [TikTok/Reel/Short]?" | competitive teardown mode, focus on `--start 0:00 --end 0:15` |
| "Can you check this Loom recording?" | bug-repro / CC briefing mode |

## Update protocol

If the upstream repo ships a breaking change to `scripts/watch.py` flags or the SKILL.md contract:
1. Pull updates: `cd vendor/claude-video && git pull`
2. Re-run `python3 scripts/setup.py --check`
3. Update this doc + any references in `brain/playbooks/youtube_video_pipeline.md`
