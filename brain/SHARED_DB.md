---
tags: [infrastructure, shared, supabase, c-suite]
---

# Shared Supabase — 3-Agent Long-Term Memory

> **Single Supabase project used by all three C-Suite agents** (Bravo CEO, Atlas CFO, Maven CMO) for cross-agent durable state, analytics, and machine-readable memory.

## Project

| Field | Value |
|-------|-------|
| **Supabase project ref** | `phctllmtsogkovoilwos` |
| **Role** | Primary (originally Bravo's; now shared across C-Suite) |
| **Purpose** | Cross-agent traces, activation scoring, self-modification logs, performance metrics, long-term semantic memory |

## Separation of Concerns

| State Type | Storage | Why |
|-----------|---------|-----|
| **Real-time pulse** (runway, spend gate, current directive, MRR) | JSON files at `{agent-repo}/data/pulse/*.json` | Instant read, no network, survives DB outages |
| **Long-term memory** (traces, patterns, session logs, cross-agent analytics) | Supabase `phctllmtsogkovoilwos` | Queryable, indexable, RLS-protected, shared across agents |
| **App data** (threads, clients, deals) | Each app's own DB (Turso for PULSE, Supabase for PropFlow, etc.) | App sovereignty |

## Why One Shared DB

- **Single source of truth** for cross-agent observability — who did what, when, and why
- **Shared activation scoring** — all 3 agents contribute to the same pattern-validation pool
- **Zero sync overhead** — no bridging between separate DBs
- **Easier diagnostics** — one SQL connection to query the entire C-Suite state

## Schema (existing tables, all 3 agents can use)

- `agent_traces` — every material action logged (who, what, outcome)
- `self_modification_log` — file-level audit of agent-made changes
- `performance_metrics` — per-agent + per-skill KPIs
- `skill_activation` — which skills are firing + activation scores (recency × 0.3 + frequency × 0.4 + confidence × 0.3)
- `session_logs` — cross-agent session summaries
- `agent_state` — snapshot of each agent's declared state at session end
- (plus Bravo's app tables: leads, content_calendar, etc. that Maven and Atlas READ for context)

## Agent Conventions

Every row written by any agent MUST include an `agent` column valued one of:
- `bravo` — Bravo (CEO)
- `atlas` — Atlas (CFO)
- `maven` — Maven (CMO)

This enables filtering (`WHERE agent = 'maven'`) and audit (who touched what).

## RLS Policy

- Each agent has write access to rows where `agent = <its-name>`
- All agents have read access to all rows
- No agent can modify another agent's rows (enforced at Postgres level via RLS policy)

## How to Connect

Credentials live in each agent's `.env.agents` file under the shared keys:
```
SUPABASE_PROJECT_REF=phctllmtsogkovoilwos
SUPABASE_URL=https://phctllmtsogkovoilwos.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<shared>
SUPABASE_ANON_KEY=<shared>
```

Write:
```python
# Python (any agent)
from scripts.supabase_tool import log_trace
log_trace(agent="maven", action="campaign_launch", payload={"campaign_id": "abc"})
```

Read (cross-agent):
```python
# Maven reading Bravo's traces
from scripts.supabase_tool import query
rows = query("SELECT * FROM agent_traces WHERE agent = 'bravo' AND created_at > now() - interval '24 hours'")
```

## Relationship to Pulse Files

| Signal | Sources | Consumer |
|--------|---------|----------|
| "What's the current runway?" | `cfo_pulse.json` (fast) | Any agent on session start |
| "Did Maven launch that campaign 2 days ago?" | Supabase `agent_traces` (historical) | Bravo during briefing |
| "What skill is Maven firing most often?" | Supabase `skill_activation` (aggregated) | System diagnostics |

**Rule of thumb:** pulse = "now," Supabase = "over time."
