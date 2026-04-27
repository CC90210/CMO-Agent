---
name: video-editing
description: Automated video editing pipeline for CC's personal brand content. Use whenever CC drops raw footage and needs it edited, captioned, graded, and sent for review. The primary tool is video_editor.py which handles the full 8-step pipeline.
triggers: [video, edit, raw footage, silence, filler, caption, grade, master, review, content day, batch]
tier: standard
dependencies: [content-engine, elite-video-production]
canon_references: [sutherland-signalling, dunford-positioning]
canon_source: brain/MARKETING_CANON.md
universal: true
---

# SKILL: Video Editing & Production

> **Primary tool:** `scripts/video_editor.py`  
> **Supports:** `scripts/content_pipeline.py` (captions, transcription)

---

## When to Activate

- CC says "edit this", "make this a post", or drops raw video files
- Content Day batch processing (7 videos at once)
- Any request involving silence removal, filler cutting, captioning, or color grading
- Platform-specific video export requests

## Primary Tool: `video_editor.py`

### 8-Step Pipeline (`edit` command)

```
Step 1: Silence detection     (FFmpeg silencedetect, threshold -30dB, min 0.4s)
Step 2: Filler word detection (Whisper word-level timestamps)
Step 3: Apply cuts            (FFmpeg concat demuxer, keep segments only)
Step 4: Audio mastering       (Gate→Highpass→Lowpass→Compand→Loudnorm -14 LUFS)
Step 5: Color grading         (Pillar-auto-mapped: teal_orange, editorial, warm, clean)
Step 6: Karaoke captions      (Word-by-word highlight via content_pipeline.py ASS format)
Step 7: Background music      (Auto-ducked, mood-matched to pillar from media/music/)
Step 8: Telegram review       (sendVideo to CC, awaits 'approve' or feedback)
```

### CLI Commands

```bash
# Full edit pipeline (raw → review-ready)
python scripts/video_editor.py edit media/raw/piece_1.mp4 --pillar ai_oracle

# Remove silence + fillers only (no captions, no music, no grading)
python scripts/video_editor.py clean media/raw/piece_1.mp4

# Preview what would be cut (non-destructive analysis)
python scripts/video_editor.py analyze media/raw/piece_1.mp4

# Export edited video to all platform formats
python scripts/video_editor.py export media/exports/piece_1_final.mp4

# Send edited video to Telegram for CC's review
python scripts/video_editor.py review media/exports/piece_1_final.mp4

# Content Day: batch edit all videos in a directory
python scripts/video_editor.py batch media/raw/ --manifest data/content_day/2026-04-27_template.json
```

### Skip Flags (for partial runs)

```bash
--skip-music      # No background music overlay
--skip-captions   # No karaoke captions
--skip-review     # No Telegram notification
--skip-grade      # No color grading
--skip-master     # No audio mastering
--grade warm      # Override auto-selected grade preset
```

## Color Grade Presets

| Preset | Pillar Default | Look |
|--------|---------------|------|
| `teal_orange` | AI Oracle | Cinematic teal shadows, warm skin tones |
| `editorial` | CEO Log | Desaturated, high contrast, professional |
| `warm` | The Becoming, The Journey | Warm orange tones, gentle vignette |
| `clean` | (manual) | Neutral with micro-contrast, minimal processing |

## Audio Mastering Chain

Applied automatically in step 4:
- **Gate** (threshold 0.01) — kills breath noise between words
- **Highpass** (100Hz) — removes rumble, HVAC, handling noise
- **Lowpass** (10kHz) — tames harshness
- **Compand** (3:1 ratio, -7dB ceiling) — consistent loudness
- **Loudnorm** (-14 LUFS, -1.0 dBTP) — platform standard

## Platform Export Specs

| Platform | Max Duration | Resolution |
|----------|-------------|------------|
| Instagram Reels | 90s | 1080x1920 |
| TikTok | 180s | 1080x1920 |
| YouTube Shorts | 60s | 1080x1920 |
| LinkedIn | 600s | 1080x1920 |
| Facebook | 240s | 1080x1920 |
| X/Twitter | 140s | 1080x1920 |

## File Structure

```
media/
  raw/                  # CC drops raw footage here
  exports/              # Edited videos output here
  music/
    intense/            # AI Oracle pillar tracks
    warm/               # The Becoming pillar tracks
    emotional/          # The Journey pillar tracks
    confident/          # CEO Log pillar tracks
```

## Dependencies

| Package | Purpose | Status |
|---------|---------|--------|
| `openai-whisper` | Transcription + filler detection | Installed |
| `auto-editor` | Silence removal (backup method) | Installed |
| `pydub` | Audio analysis | Installed |
| `ffmpeg` | All video/audio processing | Installed |

## Integration Points

- **content_pipeline.py** — Called internally for karaoke caption generation
- **batch_content_day.py** — Schedules edited videos via Zernio API
- **notify.py** — Telegram review notifications
- **elite-video-production SKILL** — Reference spec for advanced techniques (zoom punches, SFX, B-roll)

## Content Day Workflow (End-to-End)

```
1. CC films 7 pieces → drops into media/raw/
2. python scripts/video_editor.py batch media/raw/ --manifest data/content_day/YYYY-MM-DD_template.json
3. Each video: silence cut → filler cut → master → grade → caption → music → Telegram
4. CC reviews each on phone, replies 'approve' or feedback
5. python scripts/batch_content_day.py schedule --manifest data/content_day/YYYY-MM-DD_template.json
6. Videos go live across 8 platforms over the next 7 days
```

## Key GitHub Repos (Reference)

| Repo | Stars | What We Use From It |
|------|-------|-------------------|
| [WyattBlue/auto-editor](https://github.com/WyattBlue/auto-editor) | 4.2k | Silence removal architecture, margin/threshold approach |
| [SamurAIGPT/AI-Youtube-Shorts-Generator](https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator) | — | Viral highlight detection pattern |
| [MatteoFasulo/Whisper-TikTok](https://github.com/MatteoFasulo/Whisper-TikTok) | — | Caption burn-in workflow |
| [HubertKasperek/short-maker](https://github.com/HubertKasperek/short-maker) | — | Audio ducking + subtitle approach |

---

## Obsidian Links
- [[skills/elite-video-production/SKILL]] | [[skills/content-engine/SKILL]] | [[brain/CAPABILITIES]]
