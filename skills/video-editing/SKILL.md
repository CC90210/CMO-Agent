# SKILL: Video Editing & Production

> Video processing pipeline for ad creative — trimming, captioning, formatting, and platform optimization.

---

## Overview
This skill covers the video production pipeline for creating ad-ready video content from raw footage. Uses FFmpeg for processing, Whisper for auto-captioning, and platform APIs for uploading.

## Tools Required
- **FFmpeg** — Video processing, trimming, resizing, compression, caption burning
- **Whisper** — AI speech-to-text for auto-captioning
- **Playwright** — Screenshot thumbnails, preview verification
- **Platform APIs** — Upload via Google Ads AssetService or Meta AdVideo endpoint

## Platform Video Specifications

### Google Ads (YouTube)
| Ad Type | Ratio | Duration | Notes |
|---------|-------|----------|-------|
| In-Stream (skippable) | 16:9 | 12s - 3min | Skip after 5s. Hook must be in first 5s. |
| In-Stream (non-skip) | 16:9 | 15 or 20s | Full attention. Every second counts. |
| Bumper | 16:9 | 6s max | Ultra-short brand awareness |
| Shorts | 9:16 | Up to 60s | Vertical, mobile-first |

### Meta Ads
| Placement | Ratio | Duration | Resolution | Max Size |
|-----------|-------|----------|------------|----------|
| Feed | 1:1 or 4:5 | 15-30s | 1080x1080 / 1080x1350 | 4GB |
| Stories/Reels | 9:16 | 15s | 1080x1920 | 4GB |
| In-Stream | 16:9 | 5-15s | 1920x1080 | 4GB |

## Video Production Pipeline

### Phase 1: Ingest & Analyze
```bash
# Get video info
ffprobe -v quiet -print_format json -show_format -show_streams input.mp4
```
- Check: duration, resolution, aspect ratio, audio codec, file size
- Store raw in `media/raw/`

### Phase 2: Trim
```bash
# Trim to 30 seconds starting at 5s
ffmpeg -i input.mp4 -ss 00:00:05 -t 00:00:30 -c copy trimmed.mp4

# Trim with re-encoding (more precise cut points)
ffmpeg -i input.mp4 -ss 00:00:05 -t 00:00:30 -c:v libx264 -c:a aac trimmed.mp4
```

### Phase 3: Resize for Platforms
```bash
# Square (1:1) for Meta Feed
ffmpeg -i input.mp4 -vf "scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2:black" feed_square.mp4

# Vertical (9:16) for Stories/Reels
ffmpeg -i input.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black" stories_vertical.mp4

# Landscape (16:9) for YouTube
ffmpeg -i input.mp4 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black" youtube_landscape.mp4

# Portrait (4:5) for Meta Feed optimal
ffmpeg -i input.mp4 -vf "scale=1080:1350:force_original_aspect_ratio=decrease,pad=1080:1350:(ow-iw)/2:(oh-ih)/2:black" feed_portrait.mp4
```

### Phase 4: Auto-Caption
```bash
# Generate captions with Whisper
whisper input.mp4 --model medium --language en --output_format srt --output_dir ./captions/

# Burn captions into video (white text, black outline)
ffmpeg -i input.mp4 -vf "subtitles=captions/input.srt:force_style='FontName=Arial,FontSize=28,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2,Shadow=1,MarginV=40'" captioned.mp4
```

### Phase 5: Compress
```bash
# Standard compression (good quality, smaller file)
ffmpeg -i input.mp4 -c:v libx264 -crf 23 -preset medium -c:a aac -b:a 128k compressed.mp4

# Aggressive compression (for file size limits)
ffmpeg -i input.mp4 -c:v libx264 -crf 28 -preset slow -c:a aac -b:a 96k small.mp4
```

### Phase 6: Thumbnail
```bash
# Extract frame at 3 seconds as thumbnail
ffmpeg -i input.mp4 -ss 00:00:03 -frames:v 1 thumbnail.jpg

# Extract best frame (highest quality)
ffmpeg -i input.mp4 -vf "select=eq(pict_type\,I)" -frames:v 1 thumbnail_best.jpg
```

### Phase 7: Export & Organize
- Store all variants in `media/exports/[campaign_name]/`
- Name convention: `[campaign]_[placement]_[variant].mp4`
- Generate manifest listing all files with specs

## Video Ad Creative Best Practices (Lending)

### Structure (30-second template)
```
0-3s:  HOOK — Problem statement ("Need funds fast?")
3-10s: AGITATE — Empathize ("We know applying for loans is stressful")
10-20s: SOLUTION — Your offer ("Simple application, quick decisions")
20-25s: PROOF — Trust signal ("Trusted by 10,000+ borrowers")
25-30s: CTA — Clear action ("Apply now at [URL]")
```

### Must-Haves
1. **Captions** — 85% of social video watched on mute
2. **Brand logo** — Visible throughout or at end card
3. **CTA overlay** — "Apply Now" button graphic in last 5 seconds
4. **Professional tone** — Trustworthy, not flashy/scammy
5. **Real people** — Testimonials outperform stock footage

### Don'ts
1. No fake check images or cash stacks
2. No "guaranteed approval" text overlays
3. No misleading before/after financial situations
4. No tiny/unreadable disclaimer text
5. No copyrighted music (use royalty-free)

## A/B Testing Video Variants
Create these variants from single source footage:
1. **Duration test:** 15s vs. 30s
2. **Hook test:** Different opening 3 seconds
3. **CTA test:** "Apply Now" vs. "Check Your Rate"
4. **Format test:** With captions vs. without
5. **Aspect test:** Feed (1:1) vs. Stories (9:16) performance
