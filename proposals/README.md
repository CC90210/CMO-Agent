---
tags: [proposals, governance, change-management]
---

# PROPOSALS — Maven's Change Proposal Directory

> Non-trivial changes Maven wants to make go through here for CC review. Individual markdown files, one per proposal. CC approves, denies, or requests revision before Maven executes.
>
> Pattern replicated from Bravo's `proposals/` structure.

---

## When to File a Proposal

File a proposal in this directory (instead of just executing) when:

- Changing semi-mutable brain files ([[BRAIN_LOOP]], [[INTERACTION_PROTOCOL]])
- Proposing a new skill with material scope
- Proposing a new canon file or canon restructure
- Making a change that affects Bravo / Atlas / Aura coordination (even if Maven only writes to its own repo)
- Any structural change touching [[MARKETING_CANON]] pillar list
- Proposing to deprecate or retire an existing skill/file
- Recommending a campaign structural change (new funnel type, new vertical activation)

Don't file proposals for:
- Copy edits
- Skill execution
- Pattern/mistake journal entries (that's [[PATTERNS]]/[[MISTAKES]] directly)
- Campaign briefs under existing doctrine (that's [[_templates/campaign-brief]])

---

## Proposal Format

File naming: `YYYY-MM-DD-<short-slug>.md`

Structure:

```markdown
---
status: DRAFT | PROPOSED | APPROVED | DENIED | EXECUTED
proposed_by: Maven
proposed_date: YYYY-MM-DD
decided_by: CC
decided_date: <when-CC-responds>
tags: [proposal]
---

# Proposal: <one-line title>

## Summary
<1-2 sentences>

## Context
<Why this matters — link to [[MARKETING_CANON]], [[PATTERNS]], [[MISTAKES]] as relevant>

## Proposal
<Specific change being proposed>

## Rationale
<Why this over alternatives>

## Canon Grounding
<[[MARKETING_CANON]] pillars this rests on>

## Impact
- What changes if approved
- What changes if denied
- Reversibility

## Risk
<Any [[RISK_REGISTER]] entries that could trigger>

## Implementation
<If approved, specific steps + timeline>

## CC Decision
<To be filled by CC>

## Obsidian Links
- [[INDEX]] | [[proposals/README]]
```

---

## Process

1. Maven drafts proposal → status DRAFT
2. Maven elevates to PROPOSED when ready → flags in session_note of cmo_pulse.json
3. CC reviews → marks APPROVED / DENIED / or requests revision
4. If APPROVED: Maven executes → status EXECUTED
5. If DENIED: Maven archives with `.archived` suffix, logs reasoning to [[DECISIONS]]

---

## Current Proposals

_(None pending as of 2026-04-21)_

---

## Related

- [[INDEX]] — vault home
- [[DECISIONS]] — where approved/denied proposals' reasoning lives
- [[INTERACTION_PROTOCOL]] — governance protocol
- [[self-improvement-protocol/SKILL]] — the protocol that often generates proposals

## Obsidian Links
- [[INDEX]] | [[DECISIONS]] | [[INTERACTION_PROTOCOL]]
