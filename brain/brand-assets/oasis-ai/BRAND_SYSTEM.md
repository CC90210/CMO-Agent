# OASIS AI — Brand System

> Canonical source of truth for every visual, video, copy, and ad I produce for OASIS AI.
> When in doubt, this file overrides anything else. Last updated: 2026-05-03.

---

## What OASIS AI is (in CC's words)

> "We build custom solutions to people's issues and problems. Not a one-size-fits-all mentality. We build partnerships and connections and give an ecosystem to friends, family, and clientele that prepares them and puts them ahead in this ever-changing world of AI, quantum computing, and all this tech that's changing the world. The customer is everyone — if you're a human, you're the customer. We target businesses specifically, especially entrepreneurs."

**One-liner (lifted from the website):**
*Custom AI systems built from scratch — tailored to your business, embedded with intelligent agents that never sleep. Your operations, automated into an asset.*

**Tagline (the poetic one):**
*Calm waters. Intelligent tides.*

**Internal tagline (from the YouTube outro):**
*Built for the ones who refuse to stay asleep.*

---

## Brand mood — what it should FEEL like

CC names three reference brands:

- **Anthropologie** — literary, considered, slightly mystical, generous with whitespace, never loud
- **Apple** — quiet confidence, restraint, every detail deliberate, premium without prestige theater
- **Louis Vuitton** — designer-tier finish, upper-echelon presence, but still warm and inviting

**The OASIS feeling = upper-echelon designer + accessible to everyone + future-aware-but-grounded.**

Things to do: serif headlines, considered animations, restrained particles, clean negative space, glow that whispers.

Things to never do: stock-photo collages, Comic Sans, drop shadows on everything, "AI hype" visual clichés (no fake holograms, no glitchy "matrix" rain, no robotic faces), hashtag walls, neon vomit.

---

## Color palette (canonical hex)

| Role | Hex | Where it goes |
|---|---|---|
| `BG_DEEP` | `#050B12` | Pure black-navy. Outer edges, vignette darkest point. |
| `BG_PRIMARY` | `#0A1525` | The main dark navy. Use for video backgrounds, social card backgrounds, email header bg. |
| `BG_ELEVATED` | `#11202F` | Slightly lifted surfaces (cards, buttons, panels). |
| `CYAN_PRIMARY` | `#1FE3F0` | The OASIS cyan. CTAs, accents, glow, brand wordmark. |
| `CYAN_SOFT` | `#7AE8F0` | Lighter cyan for italic emphasis (matches "Intelligent tides." website italic). |
| `CYAN_GLOW` | `#1FE3F0` at 25-40% opacity, with 30-60px blur radius | Used as `boxShadow` and `textShadow` for the signature glow effect. |
| `OFF_WHITE` | `#F0F4F8` | Headlines, "Calm waters." style serif text. |
| `BODY_GRAY` | `#A8B5C2` | Body copy, captions, secondary text. |
| `BODY_DIM` | `#5A6A7A` | Tertiary, deemphasized text, byline labels. |
| `STAR_DUST` | `#3A4A5C` | Background particles, star field, subtle texture dots. |

**The default video background should always be `BG_PRIMARY` (#0A1525), not pure black.** The website is dark navy, not black. This is a calibration that costs nothing and pays brand consistency.

---

## Typography

Three voices — each with a job:

### 1. Headline serif (the "Calm waters" voice)
**Font:** [Fraunces](https://fonts.google.com/specimen/Fraunces) — Google Font, available in Remotion.
**Why:** Closest free match to the Tide Recoleta / Canela vibe on the website. High contrast, gentle curves, italic that breathes.
**Use:**
- Video intro/outro headlines
- Quote-card pull quotes
- Email subject lines (when displayed visually)
- Hero text on landing pages
**Weights:** 300 (light), 400 (regular), 600 (semibold). Italic for emphasis (always italicize the *second* line in two-line headlines, like the website does with "*Intelligent tides.*").
**Color:** `OFF_WHITE` for primary line, `CYAN_SOFT` for the italic emphasis line.

### 2. The OASIS AI wordmark (brand mark only)
The actual logo lockup uses a custom italic geometric sans. Closest free Google Font match: **[Audiowide](https://fonts.google.com/specimen/Audiowide)** for that retro-futuristic italic feel, OR **[Iceberg](https://fonts.google.com/specimen/Iceberg)** for a slightly more modern read.
**Use only for the literal OASIS AI brand mention** in graphics where the logo PNG isn't appropriate. For most cases, USE THE LOGO IMAGE FILE directly: `/ad-engine/public/oasis-ai-logo.jpg`.
**Color:** `CYAN_PRIMARY` with strong glow.

### 3. Body / UI / caption sans
**Font:** [Inter](https://fonts.google.com/specimen/Inter) — Google Font, already used in our Remotion compositions.
**Why:** Neutral, clean, high legibility, pairs cleanly with Fraunces (serif + sans contrast = elegant).
**Use:**
- All body text in videos
- Social captions, hashtag rows
- UI labels, button text
- Small text overlays
**Weights:** 200 (ultralight, for atmospheric brand mark), 300 (light, captions), 400 (body), 500 (UI), 700 (bold emphasis).
**Color:** `BODY_GRAY` default, `OFF_WHITE` when emphasized.

### Pairing rule
Always use **Fraunces for "art" content** (philosophical, poetic, brand-led) and **Inter for "info" content** (descriptions, captions, CTAs, dates, byline). Mixing them in one frame is fine — the contrast is the point.

---

## Visual elements

### The signature: **subtle particle starfield**
Already implemented in `OasisIntroCard.tsx` and `OasisOutroCard.tsx`. Drifting white particles at 0.3-0.7 opacity, deterministic seed-based positioning, slight twinkle. Always present in any video card or motion graphic. Keep particle density at ~60-90 for 1920x1080 — never more (clutter).

### The signature: **breathing glow on text**
Headline text gets a slow oscillating `textShadow` of `0 0 30-50px rgba(31, 227, 240, 0.15-0.4)`. This is the "alive" feeling — the text isn't static, it's breathing. Already in the outro card. Apply to all branded headlines.

### The signature: **hard-cut composition with negative space**
Don't fill every pixel. Most OASIS frames should be 60-70% empty. Text on left, breathing room. Or text on bottom third, sky above. The website does this — match it.

### Animation language
- **Fade-ins via `spring`** with `damping: 16-20, stiffness: 80-120`. Never linear interpolation for entrance.
- **Character-by-character reveals** for headline serifs (already in intro card).
- **Word-by-word reveals** for sublines and body copy.
- **Slow continuous "breath" scale** at `1 + sin(frame*0.04)*0.012` on the entire composition.
- **No flashy transitions.** No spin, swoosh, or zoom-in. Always crossfade or hard cut.

### The logo — when and how
- **End of every video card** = full logo image with brand mark beneath it (use the JPG).
- **Top-left of social cards** = small logo + "OASIS AI" wordmark in Audiowide italic.
- **Watermark on long videos** = bottom-right corner at 25% opacity (don't compete with content).
- **NEVER stretch the logo.** It's square. If a layout demands horizontal, use just "OASIS AI" wordmark.

---

## Voice — how OASIS writes

CC's actual voice (transcribed from this conversation):
- "I run five businesses by myself with the help of four AI agents I built."
- "I've been quiet about what I've been seeing for too long."
- "AI is moving faster than people think."
- "Built for the ones who refuse to stay asleep."

**Voice rules:**
- **Lowercase opens** are okay (Twitter, Threads, Instagram captions). Match the medium.
- **Sentence fragments are powerful.** Don't fight them. *"Not a tutorial. A message."*
- **Em dash > comma** when the sentence is loaded with weight. *"It's not a tutorial — it's a message."*
- **Never use "unleash," "unlock," "harness," "elevate," "leverage."** Standard AI-marketing slop. CC's voice is literary, not corporate.
- **The word "calm" is on-brand.** So is "asleep," "awake," "asset," "tide," "ecosystem," "operation," "future," "intentional," "discipline," "patient."
- **Avoid hype words.** "Game-changing," "revolutionary," "disrupt," "10x," "next-gen" — all banned.
- **Singular voice.** OASIS speaks as one unified entity, not a "we" company. *"OASIS builds…"* / *"This is what we're building…"* — never *"Our team of experts…"*

---

## Captions on videos

CC's preference (stated 2026-05-03): **don't auto-add captions** to philosophical/atmospheric content. Keep frames clean. Captions break the cinematic feel.

**When TO use captions:**
- Reels/Shorts where viewers watch on mute by default
- Tutorial content
- Quote-card carousel posts (the caption IS the content)

**When NOT to use captions:**
- Cinematic intros/outros
- Long-form atmospheric YouTube videos like the May 3 launch video
- Anywhere the audio carries the meaning

---

## Templates currently built

| Template | Status | File | Notes |
|---|---|---|---|
| YouTube intro card (1920x1080, 5s) | ✅ v1 done | `ad-engine/src/compositions/OasisIntroCard.tsx` | Needs brand-color refresh |
| YouTube outro card (1920x1080, 8s) | ✅ v1 done | `ad-engine/src/compositions/OasisOutroCard.tsx` | Needs logo + brand-color refresh |
| Reels/Shorts vertical template (1080x1920) | ⏳ planned | — | Vertical, ≤90s, captions on |
| Static social card (1080x1080) | ⏳ planned | — | Quote-card style, IG feed compatible |
| Email header banner (1200x400) | ⏳ planned | — | For Gmail outreach signature |

---

## Canonical links (mirror — see `reference_oasis_canonical_links.md`)

- Website: `https://oasisai.work`
- Booking: `https://calendar.app.google/tpfvJYBGircnGu8G8`
- Email: `conaugh@oasisai.work`
- Brand: OASIS AI Solutions (NEVER `oasisai.solutions` — that's not a domain we own)

---

## How I use this file

Before generating ANY public-facing OASIS asset (video card, social post, ad creative, email graphic), I open this file and verify:
1. Color hex values match the palette above
2. Typography uses Fraunces (headlines) + Inter (body) with Audiowide for brand mark
3. Voice rules don't violate the banned-word list
4. The logo is used correctly (not stretched, end-card placement, watermark only at 25%)
5. The composition leaves 60-70% negative space
6. Particle starfield is present in motion content
7. Breathing glow is applied to brand-color text

If any of those checks fail, I rebuild before delivery. No exceptions.
