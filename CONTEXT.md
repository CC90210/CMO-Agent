---
name: CONTEXT
description: Canonical vocabulary for the Maven CMO agent — content, brand, ads, funnels, growth. Every skill, agent file, and entry point must use these terms with these meanings. New domain term enters the codebase → add it here first.
last_updated: 2026-05-16
---

# CONTEXT — Maven Canonical Vocabulary

> Maven's domain glossary. Adopted 2026-05-16 as part of V6.8 propagation from Bravo. Pattern source: [Bravo CONTEXT.md](../Business-Empire-Agent/CONTEXT.md) + [mattpocock/skills CONTEXT.md](https://github.com/mattpocock/skills/blob/main/CONTEXT.md).
>
> Empire-wide terms (CC, Bravo, Atlas, OASIS, PropFlow, North Star) are canonicalized in [Bravo's CONTEXT.md](../Business-Empire-Agent/CONTEXT.md). This file is Maven-specific: content, brand voice, platforms, ad creative, funnels.

---

## Identity

- **Maven** — This agent. CC's AI CMO. Lead Architect & Marketing Operations Engine. Runs Opus 4.6 by default. Identity is model-driven, not runtime-driven (Claude → Maven; GPT → Maven-as-Codex backend executor).
- **C-Suite** — Three sibling agents: Bravo (CEO, `~/Business-Empire-Agent`), Atlas (CFO, `~/APPS/CFO-Agent`), Maven (CMO, this repo). Shared Supabase project `phctllmtsogkovoilwos`. See `brain/SHARED_DB.md`.
- **Ad-Engine sidecar** — `ad-engine/` directory, cloned from Shopify-Ad-Engine. Remotion-based programmatic video/ad templates. OASIS branding lives in `OasisIntroCard` + `OasisOutroCard`.

## Brands Maven serves

- **OASIS AI Solutions** — CC's primary B2B brand. AI automation for local businesses. Collingwood ON → Montreal summer 2026.
- **PropFlow** — Tenant screening + landlord automation. CC + Adon 50/50.
- **Nostalgic Requests** — Personal/legacy brand.
- **CC Personal Brand** — Founder content. Sobriety, lifting, building OASIS, DJ history.
- **SunBiz Funding** — Sun's business. Maven supports content on it.

## Content pillars (CC personal brand)

- **Sobriety Log** — Daily one-line reflections on staying sober. Authentic, no AA-isms, no preachiness.
- **Quote Drop** — Single-line founder/builder/operator quote with a photo. High-signal, low-noise.
- **CEO Log** — Day-in-the-life of building OASIS. Specific numbers, specific problems, specific wins.
- **Pacing rule** — 7-pillar rotation, no two same-pillar posts back-to-back. Full pacing rules: `memory/content-strategy.md`.

## Brand voice (CC's authentic voice)

- **First-principles directness.** "Here's what I see. Here's what to do. Here's why." No hedging, no LinkedIn-platitudes, no "I'd just like to mention that..."
- **Specific over generic.** "$5K Net MRR by May 30" beats "growing the business." "OASIS Welcome email scored 7.8/10" beats "we improved deliverability."
- **NEPQ framing for sales.** Jeremy Miner Neuro-Emotional Persuasion Questioning. Pattern interrupts. Never sound salesy. Questions > pitching. "I'm not sure if..." kills sales resistance.
- **Anti-slop checklist.** Purple/blue gradients = no. 3-column icon grids = no. "Unlock the power of..." = no. "It's worth noting that..." = no. Passive voice to dodge a recommendation = no.

## Platforms

- **Instagram** — Reels primary, carousel secondary, static last. Hook in first 1.5 seconds. Captions ≤125 chars before the fold.
- **TikTok** — Vertical 9:16, captions baked in (audio-off viewing), 7-15s for hook density.
- **LinkedIn** — Long-form text + selective video. CC's founder voice plays well. No emojis in B2B copy.
- **YouTube** — Long-form (CEO Log episodes, OASIS case studies). Thumbnails matter more than titles.
- **X (Twitter)** — Threads + single-shot insights. Lower priority than IG/LinkedIn.
- **Facebook** — Mirror of IG. Lower effort. Don't custom-author.

## Tooling

- **Zernio** (formerly Late) — Social media scheduler. `scripts/late_tool.py` is the CLI. Env var: `LATE_API_KEY`.
- **Remotion 4.0.431** — Programmatic video/animation. `ad-engine/` houses the templates.
- **FFmpeg 8.0.1** — Video editing pipeline (`scripts/edit_content.py`). NVENC, libx264, libx265 built in.
- **Whisper** — Auto-transcription to SRT (word-level timestamps for caption sync).
- **ElevenLabs** — Voiceover generation. `ELEVENLABS_API_KEY` in `.env.agents`.
- **Late/Zernio rebrand** — 2026-03-26. New URL `https://zernio.com/api/v1/`. Old getlate.dev still works.

## Cold outreach

- **NEPQ** — Neuro-Emotional Persuasion Questioning. Jeremy Miner framework. Maven drafts outreach using this; Bravo's `outreach-send` actually ships the email (canonical send path is in Bravo, not Maven).
- **Pattern interrupt** — Opening line that breaks the standard cold-outreach script ("Hi NAME, hope you're well, I help companies like yours...") with something specific and unexpected.
- **The "I'm not sure if..." opener** — Kills sales resistance by framing as discovery, not pitch.

## Competitor reference

- **chase.h.ai** — 174K Instagram followers. Hook/engagement reference for AI-automation content. Maven studies patterns; never copies. Extract principles only.

## Output quality bar

- **Captions synced to AUDIO** — Whisper word-level timestamps, not arbitrary time-based offsets. Previous attempts had sync issues; this is non-negotiable now.
- **Contextual image insertion** — Maven decides WHERE and WHAT images appear based on video topic, not just stock-image padding.
- **Cinematic output only** — When CC says "make this a post" with raw video, run the FULL pipeline (transcribe → caption → cinematic edit → thumbnail → schedule). No half-measures, no questions.

## Maven-specific lifecycle terms

- **Brand asset** — Logo, color, font, video intro/outro, etc. Lives in `brand/` directory. NEVER reorder without explicit CC approval.
- **Pulse** — Maven has its own pulse (daily content digest); separate from Bravo's empire pulse. Stored in `data/pulse/`.
- **Drop** — One scheduled piece of content from concept to live. State machine: draft → review → scheduled → live → measured.

---

## How to update this file

1. New brand / platform / tool / framework term enters Maven's codebase → add the entry here.
2. Existing term's meaning shifts → edit here; do NOT shadow with new term.
3. Term retired → delete the entry.
4. Empire-wide terms (CC, Bravo, Atlas, OASIS, PropFlow, North Star) live in [Bravo's CONTEXT.md](../Business-Empire-Agent/CONTEXT.md), not here.

See [docs/adr/0001-context-md-canonical-vocabulary.md](docs/adr/0001-context-md-canonical-vocabulary.md) for the propagation rule.
