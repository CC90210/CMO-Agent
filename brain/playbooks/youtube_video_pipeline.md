# YouTube Video Pipeline — End-to-End Runbook

> **Trigger:** CC asks for a YouTube video, says "post this video," "make a video," "upload to YouTube," or hands me raw footage to publish.
> **Outcome:** A fully branded, captioned-correctly, properly-thumbnailed YouTube video live on `@ccmusicc03`, with cross-posts to LinkedIn / Twitter / Threads.
> **Time to ship:** 30-90 minutes from raw footage to live URL.
> **Last reviewed:** 2026-05-03 (after first end-to-end execution).

---

## 0. Before you do anything — load context

**Read in this order. Skipping = mistakes.**

1. `brain/brand-assets/oasis-ai/BRAND_SYSTEM.md` — colors, fonts, voice, banned words. The 7-point verification checklist at the bottom of that file is your contract before any frame ships.
2. `memory/reference_oasis_canonical_links.md` — domain (`oasisai.work`, NOT `.solutions`), booking link, email.
3. `memory/reference_late_api_large_uploads.md` — Late API has a 4.5 MB serverless function limit; large videos go through the R2 presign flow.
4. `memory/feedback_late_account_verify.md` — verify the connected account by `displayName + username + profileUrl` BEFORE posting. The Late account `_id` stays stable across reconnects, so it's not a safety check.
5. `memory/feedback_just_post_dont_handoff.md` — when CC says "post," I post. Don't generate a copy-paste handoff package.

If any of these files don't load or look stale, STOP and tell CC before proceeding.

---

## 1. Pre-flight checks

```bash
# Confirm Late API key is loaded
grep -E "^LATE_API_KEY=" /c/Users/User/CMO-Agent/.env.agents

# Confirm ffmpeg is on PATH
ffmpeg -version | head -1

# Confirm the OASIS logo is in the Remotion public folder (Remotion needs it via staticFile())
test -f /c/Users/User/CMO-Agent/ad-engine/public/oasis-ai-logo.jpg && echo "logo OK" || echo "MISSING — copy from brand-assets/oasis-ai/logos/"

# Confirm Remotion compositions are registered
grep -c "OasisIntroCard\|OasisOutroCard" /c/Users/User/CMO-Agent/ad-engine/src/Root.tsx  # expect ≥4
```

If any check fails, fix it before touching the video.

---

## 2. Verify the Late YouTube account

```bash
export LATE_API_KEY=$(grep ^LATE_API_KEY= /c/Users/User/CMO-Agent/.env.agents | cut -d= -f2-)
curl -sS -H "Authorization: Bearer $LATE_API_KEY" "https://getlate.dev/api/v1/accounts" \
  | python -c "import sys,json; [print(f\"{a['platform']:12} | {a.get('displayName','?'):25} | {a.get('username','?'):20} | {a.get('profileUrl','?')}\") for a in json.load(sys.stdin)['accounts'] if a['platform']=='youtube']"
```

**Expected:** `youtube | CC | ccmusicc03 | https://youtube.com/@ccmusicc03`

If it shows ANYTHING ELSE (especially Adon's gaming channel — happened once on May 2), STOP and tell CC to reconnect Late → YouTube. Don't post.

---

## 3. Preprocess raw footage

### 3a. Detect leading silence (the "I waited to talk" gap)

```bash
ffmpeg -hide_banner -i RAW.mp4 -t 30 -af "silencedetect=noise=-30dB:duration=0.5" -f null - 2>&1 | grep "silence_(start|end)"
```

Look for a long initial silence that ends near the first real word. That's the cut point.

### 3b. Trim + color grade + film grain (single ffmpeg pass)

```bash
ffmpeg -y -ss <START_SEC> -to <END_SEC> -i RAW.mp4 \
  -vf "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,
       eq=contrast=1.08:saturation=0.78:gamma=0.95,
       vignette=PI/4.5,
       noise=alls=8:allf=t" \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 192k -ar 48000 \
  main_graded.mp4
```

Notes:
- The color grade values above are the OASIS cinematic look (cool desat + warmth on skin + vignette + light grain).
- `END_SEC` cuts off any fumble at the end. Watch the raw and pick a clean stopping point.
- Output is large (~5 GB for 6 min) because grain is high-entropy. That's fine — re-encode for upload happens later.

---

## 4. Render branded intro/outro cards

The Remotion compositions are already brand-aligned. Just adjust the props.

```bash
cd /c/Users/User/CMO-Agent/ad-engine

# Intro — Fraunces serif headline, 5s
./node_modules/.bin/remotion render OasisIntroCard \
  /tmp/intro.mp4 --codec=h264 --crf=18 \
  --props='{"line1":"<line one>","line2":"<line two>"}'

# Outro — logo + tagline + CTA, 8s
./node_modules/.bin/remotion render OasisOutroCard \
  /tmp/outro.mp4 --codec=h264 --crf=18 \
  --props='{"tagline":"<tagline>","cta":"Book a 30-min strategy call","bookingUrl":"calendar.app.google/tpfvJYBGircnGu8G8"}'
```

**Don't render intro and outro in parallel.** They share Remotion's font cache; parallel renders cause `Z_BUF_ERROR`. Render serially.

If the line1/line2 props match the website hero (`Calm waters.` / `Intelligent tides.`) or the video's opening note, leave them as-is. Otherwise customize.

---

## 5. Concat with crossfades (intro + main + outro)

The xfade filter requires matching pixel format, fps, and timebase across all inputs. Remotion outputs use `yuvj420p` and timebase `1/15360`; ffmpeg-graded video uses `yuv420p` and `1/15360` too — but normalize anyway.

```bash
INTRO_LEN=5.0   # 150 frames at 30fps
MAIN_LEN=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 main_graded.mp4 | awk '{printf "%.1f", $1}')
OUTRO_LEN=8.0   # 240 frames at 30fps

# Crossfade offsets: intro→main at INTRO_LEN-0.6, then [v01]→outro at INTRO_LEN+MAIN_LEN-0.6-1.0
XF1_OFFSET=$(echo "$INTRO_LEN - 0.6" | bc)
XF2_OFFSET=$(echo "$INTRO_LEN + $MAIN_LEN - 1.6" | bc)

ffmpeg -y -hide_banner -loglevel error \
  -i /tmp/intro.mp4 -i main_graded.mp4 -i /tmp/outro.mp4 \
  -filter_complex "
    [0:v]trim=duration=$INTRO_LEN,setpts=PTS-STARTPTS,fps=30,format=yuv420p,setsar=1,settb=AVTB[v0];
    [1:v]trim=duration=$MAIN_LEN,setpts=PTS-STARTPTS,fps=30,format=yuv420p,setsar=1,settb=AVTB[v1];
    [2:v]trim=duration=$OUTRO_LEN,setpts=PTS-STARTPTS,fps=30,format=yuv420p,setsar=1,settb=AVTB[v2];
    [0:a]atrim=duration=$INTRO_LEN,asetpts=PTS-STARTPTS,aresample=48000[a0];
    [1:a]atrim=duration=$MAIN_LEN,asetpts=PTS-STARTPTS,aresample=48000[a1];
    [2:a]atrim=duration=$OUTRO_LEN,asetpts=PTS-STARTPTS,aresample=48000[a2];
    [v0][v1]xfade=transition=fade:duration=0.6:offset=$XF1_OFFSET[vx1];
    [vx1][v2]xfade=transition=fade:duration=1.0:offset=$XF2_OFFSET[vout];
    [a0][a1]acrossfade=d=0.6[ax1];
    [ax1][a2]acrossfade=d=1.0[aout]
  " \
  -map "[vout]" -map "[aout]" \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
  final_master.mp4
```

**Common failure: `First input link main timebase ... do not match`** — this is why `settb=AVTB` is on every video stream. Don't remove it.

---

## 6. Upload via Late R2 presign (NOT direct multipart)

Direct upload (`POST /v1/media/upload`) is hard-capped at ~4.5 MB by Late's Vercel deployment. For ANY video over 4.5 MB, use the presign flow.

```bash
SIZE=$(stat -c %s final_master.mp4)
PRESIGN=$(curl -sS -X POST -H "Authorization: Bearer $LATE_API_KEY" -H "Content-Type: application/json" \
  -d "{\"filename\":\"video.mp4\",\"contentType\":\"video/mp4\",\"size\":$SIZE}" \
  "https://zernio.com/api/v1/media/presign")

UPLOAD_URL=$(echo "$PRESIGN" | python -c "import sys,json; print(json.load(sys.stdin)['uploadUrl'])")
PUBLIC_URL=$(echo "$PRESIGN" | python -c "import sys,json; print(json.load(sys.stdin)['publicUrl'])")

curl -sS -X PUT -H "Content-Type: video/mp4" --data-binary @final_master.mp4 "$UPLOAD_URL" \
  -w "PUT HTTP %{http_code}\n"
```

Expect HTTP 200 and ~25-60 seconds for a 500 MB file (depends on uplink). The `$PUBLIC_URL` is what you reference in `mediaItems` next.

---

## 7. Create the YouTube post via Late

```json
{
  "content": "<full YouTube description with chapters, hashtags, oasisai.work + booking link>",
  "mediaItems": [{ "type": "video", "url": "<PUBLIC_URL from step 6>" }],
  "platforms": [{
    "platform": "youtube",
    "accountId": "<youtube account id from step 2>",
    "platformSpecificData": {
      "title": "<title, max 100 chars>",
      "visibility": "public",
      "madeForKids": false,
      "containsSyntheticMedia": false,
      "categoryId": "28"
    }
  }],
  "publishNow": true,
  "tags": [<14-20 keyword tags, each ≤100 chars, combined ≤500 chars>]
}
```

POST to `https://getlate.dev/api/v1/posts`. Capture the `post._id` from the response.

**Description must include** (mirror the May 3 launch video):
- Hook paragraph
- The note / message body
- "— Conaugh" sign-off
- `📍 Want to talk about what AI can do for your business?\nBook a 30-min call → https://calendar.app.google/tpfvJYBGircnGu8G8`
- `🌐 OASIS AI Solutions → https://oasisai.work`
- `📧 conaugh@oasisai.work`
- Tagline block: `OASIS AI` / `Built for the ones who refuse to stay asleep.`
- Chapters (e.g. `00:00 — Intro`)
- Hashtag row

**Description must NEVER** contain `oasisai.solutions` (wrong domain — burned once already).

---

## 8. Poll for live URL

```bash
POST_ID=<from step 7>
for i in {1..20}; do
  STATUS=$(curl -sS -H "Authorization: Bearer $LATE_API_KEY" "https://getlate.dev/api/v1/posts/$POST_ID" \
    | python -c "import sys,json; p=json.load(sys.stdin)['post']; pl=p['platforms'][0]; print(f\"{pl['status']}|{pl.get('platformPostUrl','(pending)')}\")")
  echo "$i: $STATUS"
  [[ "$STATUS" == published* ]] && break
  sleep 30
done
```

YouTube ingestion takes 2-5 minutes for ~500 MB videos.

---

## 9. Build and apply custom thumbnail

YouTube auto-grabs a random face frame. Override it.

```bash
# 9a. Pick a face frame from main_graded.mp4 — sample a few timestamps
for t in 30 70 120 200 260; do
  ffmpeg -y -ss $t -i main_graded.mp4 -frames:v 1 frame_${t}s.jpg
done
# Inspect them, pick the strongest.

# 9b. Composite branded thumbnail (1280x720, hard-cut left half black, headline + face)
ffmpeg -y -i frame_70s.jpg -vf "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,
  eq=contrast=1.18:saturation=0.65:gamma=0.92,vignette=PI/4,
  geq=r='if(lt(X,540),0,if(lt(X,720),r(X,Y)*((X-540)/180),r(X,Y)))':
       g='if(lt(X,540),0,if(lt(X,720),g(X,Y)*((X-540)/180),g(X,Y)))':
       b='if(lt(X,540),0,if(lt(X,720),b(X,Y)*((X-540)/180),b(X,Y)))',
  drawtext=text='<3-WORD HEADLINE>':fontsize=130:fontcolor=white:x=50:y=265,
  drawtext=text='OASIS AI':fontsize=22:fontcolor=white@0.6:x=50:y=h-50" \
  -q:v 2 thumbnail.jpg

# 9c. Upload + apply
SIZE=$(stat -c %s thumbnail.jpg)
PRESIGN=$(curl -sS -X POST -H "Authorization: Bearer $LATE_API_KEY" -H "Content-Type: application/json" \
  -d "{\"filename\":\"thumb.jpg\",\"contentType\":\"image/jpeg\",\"size\":$SIZE}" "https://zernio.com/api/v1/media/presign")
UPLOAD_URL=$(echo "$PRESIGN" | python -c "import sys,json; print(json.load(sys.stdin)['uploadUrl'])")
PUBLIC_URL=$(echo "$PRESIGN" | python -c "import sys,json; print(json.load(sys.stdin)['publicUrl'])")
curl -sS -X PUT -H "Content-Type: image/jpeg" --data-binary @thumbnail.jpg "$UPLOAD_URL"

curl -sS -X POST -H "Authorization: Bearer $LATE_API_KEY" -H "Content-Type: application/json" \
  -d "{\"platform\":\"youtube\",\"thumbnailUrl\":\"$PUBLIC_URL\"}" \
  "https://getlate.dev/api/v1/posts/$POST_ID/update-metadata"
```

Thumbnail headline must be **3 words max** (longer doesn't read at 1280×720). Match the video's emotional core. Stay on brand: white sans on dark, no rainbow text, no cartoon arrows.

---

## 10. Cross-post (LinkedIn native, Twitter, Threads)

Don't try IG until CC reconnects (token expired May 3, never refreshed).

LinkedIn (native video upload — uses same `PUBLIC_URL` from step 6):
```json
{
  "content": "<long-form LinkedIn caption with YouTube link>",
  "mediaItems": [{ "type": "video", "url": "<PUBLIC_URL>" }],
  "platforms": [{ "platform": "linkedin", "accountId": "<linkedin account id>" }],
  "publishNow": true
}
```

Twitter (text + YouTube link, ≤280 chars):
```json
{
  "content": "<short hook>\n\nwatch it → https://www.youtube.com/watch?v=<videoId>",
  "platforms": [{ "platform": "twitter", "accountId": "<twitter account id>" }],
  "publishNow": true
}
```

Threads (text + link, ~500 chars):
```json
{
  "content": "<short philosophical hook>\n\n▶ https://www.youtube.com/watch?v=<videoId>",
  "platforms": [{ "platform": "threads", "accountId": "<threads account id>" }],
  "publishNow": true
}
```

POST each separately. Check responses for `"error":"This exact content is already scheduled, publishing, or was posted to this account within the last 24 hours."` — that's Late's deduplication; not a real failure if the existingPostId is processing.

---

## Failure modes I've already hit (don't repeat)

| Symptom | Cause | Fix |
|---|---|---|
| `FUNCTION_PAYLOAD_TOO_LARGE` on `/v1/media/upload` | Vercel function body cap ~4.5 MB | Use `/v1/media/presign` → R2 PUT (step 6) |
| Title card text rendered with literal `—` | drawtext doesn't support unicode escapes | Use the actual UTF-8 character or rewrite without dashes |
| `Z_BUF_ERROR` from Remotion render | Font cache contention from parallel renders | Render compositions serially, not in parallel |
| `First input link main timebase do not match` | xfade requires matching timebases | Add `settb=AVTB` to every video stream filter chain |
| Late posts to wrong YouTube channel | Account `_id` stable across reconnects but channel changed | Always run step 2 verification BEFORE posting |
| Instagram post fails with `auth_expired` | OAuth token expired | Tell CC to reconnect IG in Late dashboard, then retry |
| YouTube description shows wrong domain | Improvised `oasisai.solutions` from brand display name | The domain is `oasisai.work`. Always pull from `reference_oasis_canonical_links.md` |

---

## What gets saved where

```
brain/brand-assets/oasis-ai/
  ├── BRAND_SYSTEM.md                   # Source of truth for brand
  ├── logos/oasis-ai-primary-square.jpg # Logo file
  └── templates/
      ├── oasis-intro-card-v2.mp4       # Pre-rendered branded intro
      ├── oasis-outro-card-v2.mp4       # Pre-rendered branded outro
      ├── preview-intro-v2.png
      └── preview-outro-v2.png

ad-engine/
  ├── public/oasis-ai-logo.jpg          # Logo accessible to Remotion
  └── src/compositions/
      ├── OasisIntroCard.tsx            # Brand-aligned, edit ONLY with BRAND_SYSTEM.md open
      └── OasisOutroCard.tsx            # Brand-aligned, edit ONLY with BRAND_SYSTEM.md open

media/videos/youtube/<video-slug>/
  ├── working/                          # Intermediate files, deletable after publish
  └── final/
      ├── <slug>-MASTER.mp4             # Full quality, archive
      ├── <slug>-UPLOAD.mp4             # Compressed for upload, also kept for re-uploads
      └── thumbnail.jpg                 # Final thumbnail
```

---

## Step 11 (optional but recommended) — claude-video QA pass before publish

Before pushing the final to YouTube via Late, run claude-video on the rendered file as a QA gate:

```bash
python3 /c/Users/User/CMO-Agent/vendor/claude-video/scripts/watch.py \
  /c/Users/User/CMO-Agent/media/videos/youtube/<slug>/final/<slug>-MASTER.mp4 \
  --max-frames 60
```

Then read the JPEG paths the script prints, scanning for:
- Text bleeding off-frame or clipping
- Brand color drift (anything that's NOT `#0A1525` bg or `#1FE3F0` cyan in branded sections)
- Logo rendering issues on the outro
- Audio/video desync indicators (lip-sync glitches if the topic is on-camera)
- Any frames that look "AI-generated cliché" the brand voice rule disallows

If any issue is found → fix in Remotion or the ffmpeg pipeline → re-render → re-QA → THEN upload via Late.

This is a one-shot, takes ~30 seconds for a 6-min video. See `brain/integrations/claude-video.md` for full flag reference.

---

## Last sanity check before declaring done

- [ ] Live YouTube URL captured and shared with CC
- [ ] Custom thumbnail visible (not the auto-grab face frame)
- [ ] Description has correct domain (`oasisai.work`), booking link, chapters, hashtags
- [ ] Cross-posts confirmed live on LinkedIn / Twitter / Threads
- [ ] Working files cleaned up; final files in `media/videos/youtube/<slug>/final/`
- [ ] Anything new learned this session is captured in MEMORY.md
