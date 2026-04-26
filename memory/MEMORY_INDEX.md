---
tags: [memory, index, hub]
---

# MEMORY — Maven's Episodic Journal

> The `memory/` directory holds Maven's episodic memory: what happened, what we learned, what's in flight, what we've decided. Distinct from `brain/` (instructions, identity, canon) and the shared Supabase (long-term analytics).

---

## How Memory Is Organized

| File | Purpose | When it grows |
|------|---------|---------------|
| [[ACTIVE_TASKS]] | Current P0/P1/P2/P3 tasks | Every session (reconciled) |
| [[SESSION_LOG]] | Append-only activity log | Every session |
| [[PATTERNS]] | Validated approaches (PROBATIONARY → VALIDATED) | Protocol 4 of [[self-improvement-protocol/SKILL]] |
| [[MISTAKES]] | Errors + root cause + prevention | When something fails |
| [[DECISIONS]] | Load-bearing decisions made | When a decision has multi-session impact |
| [[LONG_TERM]] | Long-horizon tracking | Quarterly |
| [[CAMPAIGN_TRACKER]] | Active + historical campaigns | Per campaign lifecycle event |
| [[AD_PERFORMANCE]] | Ad-level performance logs | Per campaign day (when live) |
| [[SOP_LIBRARY]] | Standard operating procedures | When a process earns durable doc |
| [[SELF_REFLECTIONS]] | Quarterly retrospectives | End of quarter |
| [[PROPOSED_CHANGES]] | Proposals needing CC sign-off | When Maven wants to change semi-mutable state |
| [[daily-notes\|daily/]] | Per-day notes (created from [[_templates/daily-note]]) | Optional — when deep-dive day warrants |
| ARCHIVES | Older content | Age-out of primary files |

---

## Read Order (at session start)

1. [[ACTIVE_TASKS]] — what's in flight
2. [[SESSION_LOG]] last entry — what happened most recently
3. [[PATTERNS]] + [[MISTAKES]] if a new campaign type is beginning

---

## Write Cadence

- **Every session:** [[SESSION_LOG]] entry, [[ACTIVE_TASKS]] reconcile
- **When fails:** [[MISTAKES]] entry with 5-whys (see [[_templates/mistake-entry]])
- **When succeeds non-obviously:** [[PATTERNS]] entry PROBATIONARY (see [[_templates/pattern-entry]])
- **When decides:** [[DECISIONS]] entry (see [[_templates/decision-entry]])
- **Quarterly:** [[SELF_REFLECTIONS]] retrospective

---

## Memory vs. Brain vs. Supabase

| | Memory | Brain | Supabase |
|---|--------|-------|----------|
| **Scope** | Episodic (what happened) | Instructions (what to do) | Analytical (what patterns emerge) |
| **Editable by Maven** | Yes | Semi (some immutable) | Yes (via agent='maven') |
| **Read at session start** | Last entries | Every session | When patterns need validation |
| **Grows over time** | Fast | Slow (deliberate) | Fast (automatic) |

Memory is what Maven lived through. Brain is who Maven is. Supabase is what Maven has measured.

---

## Maintenance

- **Prune quarterly:** move entries >180 days to ARCHIVES/ if no longer relevant
- **Canonicalize patterns:** PROBATIONARY patterns validated 3+ times → promote to VALIDATED
- **Deprecate mistakes:** when prevention has held for 180 days, note in entry

---

## Related

- [[INDEX]] — vault home
- [[BRAIN_LOOP]] — the reasoning cycle memory feeds
- [[self-improvement-protocol/SKILL]] — writes to PATTERNS + MISTAKES
- [[SHARED_DB]] — long-term analytics counterpart
- [[_templates/INDEX]] — entry templates

## Obsidian Links
- [[INDEX]] | [[ACTIVE_TASKS]] | [[SESSION_LOG]] | [[PATTERNS]] | [[MISTAKES]] | [[DECISIONS]]
