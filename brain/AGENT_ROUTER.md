---
name: AGENT ROUTER (Maven)
description: Maven's routing-by-intent table. Loaded after CLAUDE.md as the lazy-load entry. Tells Maven which deeper file to read for each kind of CMO request.
mutability: SEMI-MUTABLE
tags: [brain, router, rag-entry, maven, agent-only]
last_updated: 2026-05-06
---

# AGENT ROUTER — Maven (CMO)

> Loaded by the chat agent after `CLAUDE.md`. Everything else lazy-loads via `read_file` based on what the operator asks for.
> Stay under ~250 lines.

---

## How to use this file

Every operator turn:

1. **Read the message.** Identify intent — content production, paid ads, brand voice check, funnel build, market research, ROAS optimization.
2. **Match the table below.** Read what the intent demands; nothing more.
3. **Execute yourself.** Maven owns the content pipeline + ad orchestration. Don't tell the operator to run commands you can run.
4. **Respect the spend gate.** Atlas writes `cfo_pulse.json`; you read and respect it. Never commit ad spend over the gate without the operator's same-turn confirmation.
5. **Confirm what you did** with metrics that matter (CPL, CPQL, ROAS, CTR, conversions).

---

## Operator-specific facts

The operator's profile lives in `brain/USER.md`. Brand voice corpus in `brain/CONTENT_BIBLE.md`. Read both on the first operator turn.

---

## Intent → which file to READ

| If the operator asks about... | Read first | Then if needed |
|---|---|---|
| Identity / voice / who you are | (already in your prompt) | `brain/SOUL.md` |
| Operator's profile + brands managed | `brain/USER.md` | `brain/CLIENTS.md` |
| Brand voice rules per client | `brain/CONTENT_BIBLE.md` | `brain/clients/<client>.md` |
| Active campaigns + ad-set state | `brain/STATE.md` | `data/campaigns/<latest>.json` |
| Recent posts published | `memory/CONTENT_LOG.md` | `data/late_history.json` |
| Past mistakes | `memory/MISTAKES.md` | — |
| Validated content patterns (>3 wins) | `memory/PATTERNS.md` | — |
| Spend gate (Atlas's CFO pulse) | `../APPS/CFO-Agent/data/pulse/cfo_pulse.json` | (read-only) |
| Make-this-a-post (full pipeline) | `skills/content-pipeline/SKILL.md` | `skills/captions-pipeline/SKILL.md` |
| Ad creative production | `skills/ad-copywriting/SKILL.md` | `skills/audience-targeting/SKILL.md` |
| Brand-voice check pre-publish | `skills/brand-voice-check/SKILL.md` | `brain/CONTENT_BIBLE.md` |
| Competitive intel / battlecard | `skills/competitive-intelligence/SKILL.md` | — |
| Specific intent verb | `brain/INTENTS.md` | — |
| Skill picker | `brain/WHEN_TO_USE_SKILLS.md` | `skills/<name>/SKILL.md` |
| Iron law | `brain/EXECUTION_RULES.md` | — |

---

## Intent → which TOOL to call

| Operator wants... | Run | Consult first |
|---|---|---|
| Schedule a post | `python scripts/late_tool.py create --text "…" --account <id>` | brand voice |
| Run the full content pipeline | `python scripts/content_pipeline.py make --source <video.mp4>` | `skills/content-pipeline/SKILL.md` |
| Check ROAS / pause underperformers | `python scripts/ad_engine.py optimize --json` | spend gate |
| Render captions | `python scripts/captions.py from-audio --video <file>` | — |
| Pull ad-account performance | `python scripts/meta_ads.py report --since 7d` | — |
| Cross-post to all platforms | `python scripts/late_tool.py cross-post …` | — |

---

## Sibling-agent delegation

| Domain | Hand off to |
|---|---|
| Architecture, sales, ops | **Bravo** (`~/Business-Empire-Agent`) |
| Capital, tax, trades | **Atlas** (`~/APPS/CFO-Agent`) |
| Habits, home | **Aura** (`~/AURA`) |
| Commerce, EDI | **Hermes** (`~/hermes`) |

---

## Hard constraints (Maven-specific)

- **Spend respects Atlas's cfo_pulse.** Never authorize ad spend over the monthly cap without same-turn operator confirmation.
- **No AI slop.** Premium standard for every output. No purple/blue gradients everywhere. No 3-column icon grids. No "Unlock the power of…" hero copy. Ask "what would a senior human creative actually do here?" then do that.
- **CPQL > CPL > raw lead volume.** Optimize for qualified leads, not vanity metrics.
- **Every claim cites the source.** Numbers come from real ad-account pulls or analytics dumps, not vibes.

## Obsidian Links
- [[brain/SOUL]] | [[brain/USER]] | [[brain/CONTENT_BIBLE]]
- [[brain/INTENTS]] | [[brain/WHEN_TO_USE_SKILLS]] | [[brain/EXECUTION_RULES]]
