---
title: Data Taxonomy — Maven (CMO domain) — Pantry / Prep Table / Plate
mutability: GOVERNED
purpose: Single source of truth for what data lives where in Maven's domain. Audit target for skills/silver-platter.
canonical_spec: brain/AGENTIC_OS_REFERENCE.md (§3) — the principle
related: ../../Business-Empire-Agent/brain/DATA_TAXONOMY.md (Bravo's parallel manifest)
---

# Maven Data Taxonomy

Three tiers, one rule per tier: **Pantry is raw. Prep Table is deterministic Python (no LLM). Plate is what agents consume.**

When in doubt: does it require an LLM call to produce? → not Prep Table. Is it raw API output? → Pantry. Is it the artifact an agent reads to answer CC? → Plate.

---

## Pantry — Raw Sources (Maven domain)

External integrations and on-disk raw data. Agents should NOT read these directly during a synthesis turn — read the matching Prep Table snapshot instead.

| Domain | Source | Access | Owner |
|--------|--------|--------|-------|
| Cross-platform scheduling | Late / Zernio (X, Instagram, LinkedIn, Threads, YouTube, Facebook) | `scripts/late_tool.py`, `scripts/late_publisher.py` | Maven |
| Meta Ads | Facebook Ads + Instagram Ads | `scripts/meta_ads_engine.py` | Maven |
| Google Ads | Search + Display + YouTube | `scripts/google_ads_engine.py` | Maven |
| Instagram organic | Instagram Graph API | `scripts/instagram_engine.py` | Maven |
| Content calendar | Supabase `content_calendar`, `content_pieces` | `scripts/content_engine.py` | Maven |
| Performance metrics | Supabase `ad_performance`, platform APIs | `scripts/performance_reporter.py` | Maven |
| Brand assets | `brand/`, `ad-engine/public/`, `data/templates/` | direct file read | Maven |
| Research | `data/research/` (competitor scans, audience insights, trending content) | direct file read + n8n research workflows | Maven |
| Pulse | `data/pulse/cmo_pulse.json` (cross-agent visibility) | direct file read | Maven |
| Cross-agent inbox | `tmp/agent_inbox/inbox/` (writes to/reads from sibling repos) | `scripts/agent_inbox.py` | Shared |
| A/B tests | Supabase `ab_tests`, `ab_variants` | `scripts/ab_testing_engine.py` | Maven |
| Funnels | Supabase `funnels`, `funnel_leads` (shared with Bravo) | `scripts/funnel_engine.py` if present, else direct supabase query | Shared with Bravo |

---

## Prep Table — Deterministic Pre-Aggregations (V6.7 — partial, expanding)

Python-only. No LLM. Runs on a schedule and writes a JSON artifact agents can read in O(1). The whole point: agents stop burning context on retrieval.

| Snapshot | Script (planned) | Schedule | Output | Read by |
|----------|------------------|----------|--------|---------|
| Daily ad performance | `scripts/snapshots/ad_performance_snapshot.py` (TBD) | `0 6 * * *` | `state/snapshots/latest_ad_performance.json` | CMO briefing skill |
| Weekly content velocity | `scripts/snapshots/content_velocity_snapshot.py` (TBD) | `0 8 * * MON` | `state/snapshots/latest_content_velocity.json` | weekly digest |
| Monthly ROAS digest | `scripts/snapshots/roas_snapshot.py` (TBD) | `0 9 1 * *` | `state/snapshots/latest_roas.json` | board-level summary |
| CMO pulse refresh | `scripts/pulse_publish.py` (existing — likely already runs but populates zeros) | event-driven | `data/pulse/cmo_pulse.json` | Bravo + Atlas cross-agent visibility |
| FTS5 + vector index | `scripts/memory_retriever.py update` (substrate-gap — script not yet present in Maven) | event-driven | `state/memory_index.db` | All hooks + agents |

**V6.7 status:** Prep Table snapshots are the next implementation push for Maven. Pattern lives in Bravo at `~/Business-Empire-Agent/scripts/snapshots/`. Adapting requires: (a) Maven's V6.0 substrate (state_manager, memory_retriever, guards), (b) snapshot scripts wrapped around `meta_ads_engine.py` / `late_tool.py` / `performance_reporter.py`, (c) cron_engine.py with adapted SEED_JOBS.

**Refresh cadence rule:** Read-path checks `ts` field. If > 24h old, fall back to live engines.

---

## Plate — Consumers

What CC and the agents read. Snapshot-first; live engines only as fallback.

| Consumer | Source | Delivery channel |
|----------|--------|------------------|
| `/content-brief` slash command | (planned) `latest_content_velocity.json` → `content_engine` live (fallback) | Terminal / Telegram |
| `chief-of-staff` agent | (planned) `latest_ad_performance.json`, `latest_roas.json` | Terminal digests |
| `cmo_pulse.json` cross-agent visibility | All Pantry sources aggregated | Bravo + Atlas read this |
| Command Center web | Supabase + state-api passthrough | `apps/command-center/` (Bravo-hosted) |
| `silver-platter` skill audit | This file + scans `state/snapshots/`, `scripts/snapshots/` | HTML at `tmp/silver-platter-maven-*.html` |
| Telegram digests | (planned) snapshot JSONs | Telegram chat |

---

## Add-a-Source Protocol (Maven)

1. **Pantry first:** wrap the new platform's API in `scripts/*_tool.py` (or extend an existing engine).
2. **Decide if it needs Prep Table.** If Maven reads it > 2×/day, build a snapshot.
3. **If Prep Table:** add a row above, register in `scripts/cron_engine.py` SEED_JOBS (when cron_engine lands), write `scripts/snapshots/<name>_snapshot.py`.
4. **Update consumers:** the skills/agents that read it should prefer snapshot, fall back to live.
5. **Index it:** `silver-platter` audit picks it up automatically from this file.

---

## Maven-Specific Anti-Patterns

- ❌ Pulling Meta Ads insights live on every `/content-brief` call. Pre-aggregate nightly.
- ❌ Hand-curated `data/pulse/cmo_pulse.json`. Must be auto-emitted by `pulse_publish.py`, never edited by hand.
- ❌ Writing ad-creative content to the snapshot JSON. Snapshot is metrics + counts; copy belongs in `content_calendar` (Pantry).
- ❌ Snapshot scripts that call an LLM (e.g., for "summarize this campaign"). That's a synthesis step belonging in a skill, not Prep Table.
- ❌ Reading raw Supabase from `apps/command-center/` Maven-area routes when a snapshot exists.
