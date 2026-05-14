---
name: memory-journaling
description: Structured decision and pattern logging for Maven. Guides the agent through writing high-quality entries to memory/DECISIONS.md, memory/PATTERNS.md, or memory/MISTAKES.md with proper frontmatter, cross-links, and version tags.
tags: [skill, memory, journaling, decisions, patterns]
triggers: ["log a decision", "journal this", "memory journal", "log this pattern", "record this", "save this learning", "memory-journaling"]
owner: maven
tier: T1
risk: low
canonical_pattern: ../../Business-Empire-Agent/skills/memory-journaling/SKILL.md
---

# Memory Journaling — Maven Structured Logging

## Overview

Memory drifts when entries are written ad-hoc — bullet here, paragraph there, no cross-links, no `last_updated` field, dates omitted. This skill enforces structure: every journal entry has a category, a date, a body shape per category, wiki-links to related files, and a freshness tag.

**Maven-specific:** content + ad decisions are high-velocity and high-cost — a logged "this hook bombed" or "this audience converted" saves months of re-learning. Discipline here pays compounding returns.

**When to invoke:**
- CC says "log this" / "journal that" / "save this learning"
- After a non-obvious creative or campaign decision (kill a campaign, pivot brand voice, retire a content pillar)
- After a pattern proves itself (hook that converted, ad creative that landed, audience that engaged)
- After a mistake (post bombed, ad burned spend, audience misfire)

**Trigger:** `/journal <category>`, "log a decision", "save this pattern"

## Category Routing

| Category | File | Use for |
|----------|------|---------|
| **Decision** | `memory/DECISIONS.md` | Creative direction, campaign cuts, brand voice rulings, platform additions/removals |
| **Pattern** | `memory/PATTERNS.md` | Validated hooks, formats, audience segments, posting cadences |
| **Mistake** | `memory/MISTAKES.md` | Failed posts, burned ad spend, audience misfires, voice slip-ups |
| **Reflection** | `memory/SELF_REFLECTIONS.md` | Maven introspection, growth observations |
| **Anti-pattern** | `memory/ANTI_PATTERNS.json` (when present) | Regex-detectable bad patterns (e.g., a hook phrase that always underperforms) |

## Entry Shapes

### Decision entry

```markdown
## YYYY-MM-DD — <one-line title>

**Context:** What was the situation? Constraints?

**Decision:** What we chose. Be specific — campaign names, budget, dates.

**Why:** The reasoning. Tradeoffs accepted.

**Alternatives rejected:** What else was on the table + why we passed.

**Related:** [[brain/X]] | [[skills/Y/SKILL]] | (campaign ID if applicable)
```

### Pattern entry

```markdown
## [P] / [V] — <pattern name>

**Pattern:** One sentence — what the pattern is (e.g., "Hook framing: 'I don't know if X but...' kills sales resistance").

**When:** Trigger condition (e.g., cold outreach, top-of-funnel hooks).

**How:** Step-by-step.

**Why it works:** Mechanism.

**Uses:** N (increment per re-use; promote [P] → [V] at 3)

**First seen:** YYYY-MM-DD | **Last validated:** YYYY-MM-DD

**Related:** [[brain/CONTENT_BIBLE]] | [[brain/CC_CREATIVE_IDENTITY]]
```

### Mistake entry

- **Failure** (1-2 sentences observable)
- **Why it slipped** (root cause)
- **Prevention** (concrete rules)
- **Tag** (e.g., `content-misfire`, `ad-spend-burn`, `voice-slip`)

## Execution Protocol

1. **Classify.** Decision / Pattern / Mistake / Reflection / Anti-pattern. Ask CC if ambiguous.
2. **Compose the entry** per the matching shape. Always compute today's date (never quote from context).
3. **Cross-link.** Every entry MUST link to ≥ 2 related files via `[[wiki-link]]`.
4. **Append, don't overwrite.** Insert at TOP of target file (newest first).
5. **Update frontmatter** `last_updated:` on target file.
6. **Update MEMORY.md index** if high-leverage.
7. **Confirm in chat.** "Logged <category> to memory/<file>.md: '<title>'. <N> wiki-links."

## Anti-Patterns

- ❌ Quoting today's date from system context. Always compute.
- ❌ One-line entries with no Why.
- ❌ Zero wiki-links. Decays into orphan trivia.
- ❌ Writing a mistake without a prevention.
- ❌ Editing old entries to update facts. Append superseding entries; keep originals for audit.

## When NOT to Journal

- Trivial fixes (typo, post timing tweak)
- Anything the code/calendar already documents in itself
- Ephemeral session context

## Integration

- **memory/DECISIONS.md / PATTERNS.md / MISTAKES.md** — target files
- **memory/MEMORY.md** — index pointing to high-leverage entries (if present)
- **brain/INTENTS.md** — "Log a decision or pattern" playbook routes here

## Obsidian Links
- [[memory/DECISIONS]] | [[memory/PATTERNS]] | [[memory/MISTAKES]]
- [[brain/INTENTS]] | [[skills/silver-platter/SKILL]] | [[skills/integrations-sync/SKILL]]
