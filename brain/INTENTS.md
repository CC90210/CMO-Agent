---
name: INTENTS
description: Verb-by-verb playbook for Maven. For each kind of operator request, the exact sequence the agent should run.
mutability: SEMI-MUTABLE
tags: [brain, agent-only, playbook]
last_updated: 2026-05-14
canonical_pattern: ../../Business-Empire-Agent/brain/INTENTS.md (Bravo master — Maven adapts to CMO domain)
---

# INTENTS — Maven Verb-by-Verb Playbook

> Reached from `brain/AGENT_ROUTER.md` when an intent needs more than a one-line "read this file" answer. Mirrors Bravo's INTENTS pattern but scoped to Maven's CMO domain.

---

## "Generate a content brief / what should we post this week"

1. Read `data/pulse/cmo_pulse.json` for current ad performance + content velocity. If `ts` is < 24h old, use as-is.
2. If stale or empty: pull live via `python scripts/performance_reporter.py weekly --json` + `python scripts/late_tool.py upcoming --json`.
3. Cross-reference `brain/CONTENT_BIBLE.md` for the 3 daily pillars (Sobriety Log, Quote Drop, CEO Log) and pacing rules.
4. Draft 3–5 concrete content ideas with hook + angle + platform. Voice rules: `brain/SOUL.md` + `brain/CC_CREATIVE_IDENTITY.md`.
5. End with the #1 priority post for this week — make it concrete, schedulable.

---

## "Draft ad creative / build a Meta Ads campaign"

1. Read `brain/CONTENT_BIBLE.md` for brand voice + `data/research/` for any active competitor scans.
2. If targeting a specific funnel: query Supabase `funnels` table for the offer + audience.
3. Draft 3 ad variants per platform (Meta/Google/Instagram) with: hook, headline, body, CTA, visual brief.
4. For Meta Ads execution: `python scripts/meta_ads_engine.py create --campaign-name "..." --json`. ASK before launching paid spend.
5. For Google Ads: `python scripts/google_ads_engine.py create --json`. Same gate.
6. Confirm in chat: variant count, platform, draft state. Surface to CC for approval before any launch.

---

## "Score this content idea / is this on-brand"

1. Read `brain/CONTENT_BIBLE.md` + `brain/CC_CREATIVE_IDENTITY.md`.
2. Apply the 5-criteria rubric: voice fit (1-10), pillar match (Y/N), hook strength (1-10), platform suitability, novelty vs last 14 days.
3. If score ≥ 7/10 and pillar match: green-light, surface as candidate for `/content-brief`.
4. If score 4-6: surface as needs-revision with the specific weakness.
5. If score < 4: kill, log to `memory/MISTAKES.md` with tag `content-misfire` if it was a published idea.

---

## "Sync social platforms / refresh stats"

1. Read `skills/integrations-sync/SKILL.md` for canonical refresh patterns.
2. Zernio (Late): `python scripts/late_tool.py refresh --since <iso> --json` — pulls posts, accounts, status.
3. Meta Ads: `python scripts/meta_ads_engine.py sync-insights --since <iso> --json` — pulls daily spend + conversions.
4. Google Ads: `python scripts/google_ads_engine.py sync --json`.
5. Instagram organic: `python scripts/instagram_engine.py sync --json` (with rate-limit awareness).
6. After sync, refresh `data/pulse/cmo_pulse.json` via `python scripts/pulse_publish.py emit --json`.
7. Confirm in chat: rows synced, errors (if any), pulse refresh confirmed.

---

## "Schedule a post / publish to social"

1. Compose the post in chat first. Voice from `brain/SOUL.md` + `CONTENT_BIBLE.md`. Validate length per platform.
2. Pre-flight: `python scripts/late_tool.py validate --content "..." --platforms x,instagram,linkedin --json`.
3. ASK for CC confirmation before scheduling. ALWAYS — never silent-publish.
4. Schedule: `python scripts/late_publisher.py schedule --content "..." --platforms <list> --time <iso> --json`.
5. Confirm in chat: scheduled IDs per platform, scheduled time, dashboard URL if relevant.

---

## "Log a decision or pattern"

1. Decision (creative direction, campaign cut, brand voice ruling): append to `memory/DECISIONS.md`. Format: `## YYYY-MM-DD — <title>` + Context / Decision / Why / Alternatives.
2. Pattern (hook that worked, format that converted): append to `memory/PATTERNS.md` as `[P]`. Promote to `[V]` after 3 successful re-uses.
3. Mistake (post bombed, ad burned spend, audience misfire): write to `memory/MISTAKES.md` with Failure / Why / Prevention / Tag.
4. Cross-link: every entry MUST `[[wiki-link]]` to ≥ 2 related files.
5. The `skills/memory-journaling/SKILL.md` skill is the guided form for this.

---

## "Switch me to Bravo / Atlas / Hermes"

Maven's lane is brand, content, ads, funnels, growth. If CC asks for:
- Revenue / sales / client deals → route to Bravo (`C:\Users\User\Business-Empire-Agent`)
- Finance / tax / spend gate / runway → route to Atlas (`C:\Users\User\APPS\CFO-Agent`)
- POs / orders / invoices / commerce ops → route to Hermes (`C:\Users\User\APPS\hermes`)

Cross-agent delegation: `python scripts/agent_inbox.py post --to bravo --from maven --priority normal --subject "..." --body "..."`.

---

## How to extend this file

Add sections when intents recur. First-person playbooks, ≤ 15 lines each.

## Obsidian Links
- [[brain/AGENT_ROUTER]] | [[brain/AGENTIC_OS_REFERENCE]] | [[brain/DATA_TAXONOMY]]
- [[skills/silver-platter/SKILL]] | [[skills/integrations-sync/SKILL]] | [[skills/memory-journaling/SKILL]]
