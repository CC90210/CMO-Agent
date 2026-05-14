---
name: integrations-sync
description: Idempotent refresh patterns for Maven's external data sources — Late/Zernio, Meta Ads, Google Ads, Instagram, Supabase content tables. Codifies safe sync flow so agents stop reinventing dedupe/audit/dry-run logic per source.
tags: [skill, integrations, data, sync, idempotent]
triggers: ["sync integrations", "refresh late", "refresh meta ads", "refresh google ads", "pull latest stats", "integrations sync", "sync social"]
owner: maven
tier: T2
risk: medium
canonical_pattern: ../../Business-Empire-Agent/skills/integrations-sync/SKILL.md
---

# Integrations Sync — Maven Refresh Patterns

## Overview

Every external data source needs a refresh path. Without a codified pattern, each agent reinvents dedupe + audit + dry-run logic, and stale data quietly poisons `cmo_pulse.json` + downstream snapshots.

This skill is the canonical reference for "how do I safely refresh X" in Maven's domain. Always idempotent. Always logs. Always has a dry-run.

**When to invoke:**
- CC says "refresh Zernio" / "pull latest Meta Ads stats" / "sync the content calendar"
- A Prep Table snapshot has stale upstream data
- Before generating a content brief if `cmo_pulse.json` is > 24h old

**Trigger:** `sync integrations`, `/integrations-sync`, "refresh <source>"

## Core Principles

1. **Idempotent or dry-run.** Every sync command must support re-running without duplicating data OR have `--dry-run`.
2. **Audit log.** Every sync writes a one-line JSONL entry to `state/integrations_sync.log`.
3. **Pull only the delta.** Use `--since <iso>` or platform-equivalent. Full re-syncs are explicit (`--full`) and require CC confirmation.
4. **Downstream rebuild.** After syncing Pantry, rebuild the Prep Table snapshot that consumes it + emit a fresh `cmo_pulse.json`.

## Source-by-Source Playbook

### Late / Zernio → posts + accounts

```bash
python scripts/late_tool.py refresh --since "<iso>" --json
python scripts/late_tool.py posts list --status all --json
python scripts/late_tool.py accounts list --json
```

- Idempotent: uses Late post IDs as keys.
- Verify: `python scripts/late_tool.py posts list --status scheduled --json` shows current queue.
- Downstream: refresh `cmo_pulse.json` content section.

### Meta Ads → ad performance

```bash
python scripts/meta_ads_engine.py sync-insights --since "<iso>" --json
python scripts/meta_ads_engine.py campaigns list --status active --json
```

- Idempotent: writes to Supabase `ad_performance` with `(campaign_id, date)` upsert.
- Verify: `python scripts/meta_ads_engine.py campaigns summary --json` shows updated spend totals.
- Downstream: refresh `cmo_pulse.json` ad section, future `ad_performance_snapshot.py`.

### Google Ads → spend + conversions

```bash
python scripts/google_ads_engine.py sync --since "<iso>" --json
```

- Idempotent: Google Ads daily reports are deterministic for the same date range.
- Downstream: `cmo_pulse.json` + Google-specific reports.

### Instagram organic → insights

```bash
python scripts/instagram_engine.py sync --since "<iso>" --json
```

- Idempotent: Instagram Graph API returns same metrics per (media_id, metric).
- Rate-limit aware: respects 200/hour per token.

### Supabase content_calendar / content_pieces

```bash
python scripts/content_engine.py sync --since "<iso>" --json
```

- Idempotent: upsert on (id) primary key.

### Cross-agent pulse refresh

```bash
python scripts/pulse_publish.py emit --json
```

- After any Maven sync above, emit a fresh pulse so Bravo + Atlas see current ad state.

## Audit Log Format

`state/integrations_sync.log` JSONL:

```json
{"ts":"2026-05-14T22:00:00Z","source":"meta_ads","action":"sync","mode":"incremental","since":"2026-05-13T21:00:00Z","rows":47,"errors":0}
```

If `errors > 0`, also append to `state/integrations_sync.errors.log` with the stderr blob.

## Execution Protocol

1. **Identify the source** from CC's request.
2. **Dry-run first if mutating** (especially `meta_ads_engine.py create`, `google_ads_engine.py launch`). Never auto-launch paid spend.
3. **Sync the delta.** Pull `--since` last-success-ts. `--full` requires explicit CC approval.
4. **Verify** with the per-source verification command above.
5. **Rebuild downstream.** Affected snapshot + `cmo_pulse.json`.
6. **Log to audit.** JSONL entry.
7. **Confirm in chat:** source, mode, row delta, downstream rebuilt, audit log path.

## Anti-Patterns

- ❌ Launching Meta Ads / Google Ads campaigns silently. ALWAYS require CC approval for spend.
- ❌ Full re-sync as default. Always pull delta.
- ❌ Sync-ing without refreshing `cmo_pulse.json`. Bravo + Atlas now see stale Maven state.
- ❌ Burying errors. Always log; always surface.
- ❌ Skipping the audit log. Without JSONL trail, no way to debug "why does pulse say spend=X but Meta dashboard says spend=Y."

## Integration

- **brain/DATA_TAXONOMY.md** — the Pantry source registry
- **scripts/late_tool.py / meta_ads_engine.py / google_ads_engine.py / instagram_engine.py** — underlying CLI wrappers
- **scripts/pulse_publish.py** — emits cross-agent visibility
- **state/integrations_sync.log** — the audit trail

## Obsidian Links
- [[brain/DATA_TAXONOMY]] | [[brain/CAPABILITIES]] | [[brain/INTENTS]]
- [[skills/silver-platter/SKILL]] | [[skills/memory-journaling/SKILL]]
