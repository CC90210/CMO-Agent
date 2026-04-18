---
description: Load full agent context — brain, memory, state, and quick health check for session start.
---

// turbo-all

# /prime — Load Full Context

## When to Use
Use `/prime` at the start of every session to load context and get situational awareness.

## Steps

1. **Load Brain (silently):**
   - `brain/SOUL.md` — Identity and values
   - `brain/STATE.md` — Current status
   - `brain/CLIENT.md` — Client context
   - `brain/AGENTS.md` — Available agents
   - `brain/CAPABILITIES.md` — Tool inventory

2. **Load Memory (silently):**
   - `memory/ACTIVE_TASKS.md` — Pending work
   - `memory/PATTERNS.md` — Known approaches
   - `memory/CAMPAIGN_TRACKER.md` — Current campaigns
   - `memory/MISTAKES.md` — What to avoid

3. **Quick Health Check** — APIs connected? Active campaigns? Urgent issues?

4. **Report:**
   ```
   AdVantage online. V1.0 loaded.
   Status: [INITIALIZING/OPERATIONAL/DEGRADED]
   APIs: Google [OK/PENDING] | Meta [OK/PENDING]
   Campaigns: X active | $X/day total budget
   Pending Tasks: [count]
   Ready for instructions.
   ```

## Example Usage
**User:** `/prime`
**Agent:** "AdVantage online. OPERATIONAL. 3 active campaigns, $150/day. No issues. Ready."
