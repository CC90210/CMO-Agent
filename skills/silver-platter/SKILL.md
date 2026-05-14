---
name: silver-platter
description: Per-agent data-readiness audit for Maven. Produces an HTML report mapping Pantry (raw sources), Prep Table (deterministic snapshots), and Plate (consumers) with a Mermaid data-flow diagram and ranked quick-win list. V6.7 deliverable.
tags: [skill, audit, data, agentic-os, foundation]
triggers: ["silver platter", "data audit", "data readiness audit", "audit my data", "pantry prep table plate", "where does my data live"]
owner: maven
tier: T2
risk: low
canonical_pattern: ../../Business-Empire-Agent/skills/silver-platter/SKILL.md
---

# Silver Platter — Maven Data-Readiness Audit

## Overview

"Put the core data on a silver platter so agents spend their session analyzing, not retrieving." (brain/AGENTIC_OS_REFERENCE.md §3)

For Maven specifically: this skill audits the ad-creative + content + funnel data layer, identifying where Maven's content/ad agents are still pulling raw Meta Ads / Late / Google Ads / Instagram APIs per-call instead of reading pre-aggregated snapshots.

**When to invoke:**
- Quarterly content/ads review
- After adding a major platform integration
- When CC asks "where does my marketing data live"
- New client agent provisioning (Maven sub-brand)

**Trigger:** `silver platter`, `data audit`, `/silver-platter`

## What the audit produces

Single-page HTML at `tmp/silver-platter-maven-YYYY-MM-DD.html` with:

1. **Pantry** — Late/Zernio, Meta Ads, Google Ads, Instagram, Supabase content_calendar, `data/research/`. Status active/dead/stale.
2. **Prep Table** — Daily ad performance, weekly content velocity, monthly ROAS, `cmo_pulse.json` refresh. Each row shows refresh cadence + last-refresh timestamp + staleness flag.
3. **Plate** — `/content-brief` slash command, chief-of-staff agent, cmo_pulse cross-agent visibility, Command Center dashboard.
4. **Data flow** — Mermaid diagram. Flag any direct Pantry → Plate paths (anti-pattern — Maven should pull from Prep Table).
5. **Quick-wins** — Ranked list. Highest-value Prep Table additions for Maven (typically: nightly ROAS snapshot, weekly content-velocity rollup).

## Execution Protocol

1. **Read inputs:** `brain/DATA_TAXONOMY.md`, `ls scripts/snapshots/` (if exists), `grep snapshot scripts/cron_engine.py` (if exists), `brain/CAPABILITY_GRAPH.json`.
2. **For each Plate consumer**, trace back through the chain. Flag any consumer reading a Pantry source directly without Prep Table in between.
3. **Score quick-wins:** `score = (session_savings_sec / bravo_build_minutes) * agents_affected`. Sort descending.
4. **Render:** single-file HTML, no external deps. Mermaid via CDN. Match the visual aesthetic of Bravo's report for cross-agent consistency.
5. **Confirm in chat:** one line — `silver-platter audit for Maven: N pantry sources, M prep tables (K stale), P plate consumers, Q quick-wins. Report at tmp/silver-platter-maven-<date>.html`.

## Anti-Patterns (Maven-specific)

- ❌ Running this audit against the wrong repo (e.g., from Bravo's CLAUDE.md context with Maven paths). Confirm repo in step 1.
- ❌ Treating `cmo_pulse.json` as both Pantry AND Plate. It's Plate (consumer-facing summary) emitted by Pantry sources via the pulse refresh.
- ❌ Producing the audit without the quick-wins ranking. The prioritized action list is the whole point.

## Integration

- **brain/AGENTIC_OS_REFERENCE.md** — the principle this skill operationalizes
- **brain/DATA_TAXONOMY.md** — the manifest this skill reads
- **scripts/snapshots/** (planned) — the Prep Table implementations
- **state/snapshots/** (planned) — where outputs live
- **brain/CAPABILITY_GRAPH.json** — for skill/script enumeration

## Cross-Agent Consistency

Bravo's `~/Business-Empire-Agent/skills/silver-platter/SKILL.md` is the master. Maven's adaptation here changes only domain references (Stripe/leads/clients → Late/ads/funnels). When Bravo's master updates, mirror here.

## Obsidian Links
- [[brain/AGENTIC_OS_REFERENCE]] | [[brain/DATA_TAXONOMY]] | [[brain/CAPABILITIES]]
- [[skills/integrations-sync/SKILL]] | [[skills/memory-journaling/SKILL]]
