---
adr: 0001
title: CONTEXT.md as canonical Maven vocabulary
status: accepted
date: 2026-05-16
deciders: [maven, cc]
supersedes: null
superseded_by: null
parent: ~/Business-Empire-Agent/docs/adr/0002-context-md-canonical-vocabulary.md
---

# ADR-0001 — CONTEXT.md as canonical Maven vocabulary

## Context

V6.8 (2026-05-16) introduced [CONTEXT.md root glossaries](../../CONTEXT.md) across all C-suite agents (Bravo, Maven, Atlas). The empire-wide propagation contract is owned by [Bravo's ADR-0002](../../../Business-Empire-Agent/docs/adr/0002-context-md-canonical-vocabulary.md). This Maven-side ADR records adoption and the local scope rule.

Maven was previously re-deriving brand voice, content pillars, platform conventions, and NEPQ vocabulary every session. Token cost compounded; subtle drift leaked into commits (e.g., "Pulse" meant different things in Maven and Bravo without anyone noticing for a week).

## Decision

Maven adopts the V6.8 vocabulary layer:

1. **`/CONTEXT.md` at repo root** is the canonical Maven glossary. Scope:
   - Maven identity + C-suite relationships
   - Brands Maven serves
   - Content pillars + brand voice
   - Platforms (IG, TikTok, LinkedIn, YouTube, X, FB)
   - Tooling (Zernio/Late, Remotion, FFmpeg, Whisper, ElevenLabs)
   - Cold outreach (NEPQ, pattern interrupts)
   - Competitor reference (chase.h.ai)
   - Output quality bar
   - Maven-specific lifecycle terms (Brand asset, Pulse, Drop)
2. **Empire-wide terms** (CC, Bravo, Atlas, OASIS, PropFlow, Nostalgic Requests, North Star, $5K Net MRR by May 30, 2026) live in [Bravo's CONTEXT.md](../../../Business-Empire-Agent/CONTEXT.md), NOT this one. Maven references Bravo's glossary for those; no duplication.
3. **Sibling entry-point sync** — Maven's [CLAUDE.md](../../CLAUDE.md), [GEMINI.md](../../GEMINI.md), [ANTIGRAVITY.md](../../ANTIGRAVITY.md), [AGENTS.md](../../AGENTS.md), [OPENCODE.md](../../OPENCODE.md) reference `CONTEXT.md` on their first operational turn. Update batched separately to avoid churn during V6.8 cutover.
4. **Update protocol** — when a Maven-specific term enters the codebase, add to CONTEXT.md in the same PR. When meaning shifts, edit in place; don't shadow.

## Consequences

**Positive:**
- Eliminates per-session re-derivation of brand voice + platform conventions.
- Forces a single canonical definition for terms that span Maven's skills, agent files, and content output (e.g., what counts as "CEO Log" vs "Quote Drop" stays consistent).
- Onboarding cost drops when Maven spawns a new sub-agent (drip-orchestrator, ad-creative, brand-asset-manager) — they reference CONTEXT.md instead of re-explaining the empire.

**Negative:**
- One more file to keep current. Mitigated by the `last_updated:` frontmatter and the V6.8 staleness gate (see Bravo `brain/V68_AGENT_OS_PATTERNS.md`).
- Risk of CONTEXT.md drifting from Bravo's empire-wide terms. Mitigated by ADR rule #2 above (empire-wide terms live in Bravo only; Maven references them).

**Neutral:**
- Maven adopts the *pattern*. Bravo's frontmatter conventions (`disable_model_invocation`, `argument_hint`) and `skills/in-progress/` staging lane are NOT yet applied to Maven's skill set — those propagate as Maven's skills are audited (deferred).

## Enforcement

- This ADR's existence enforces the rule. New skills must consult CONTEXT.md before introducing domain terms (the same pattern Bravo's `skills/skill-creator/SKILL.md` documents).
- No automated check today. If Maven adopts a `capability_query.py` resolver in the future, the same `check-deps` proposal in [Bravo's ADR-0001](../../../Business-Empire-Agent/docs/adr/0001-skill-dependency-classification.md) applies.

## References

- Empire-wide canonical: [~/Business-Empire-Agent/docs/adr/0002-context-md-canonical-vocabulary.md](../../../Business-Empire-Agent/docs/adr/0002-context-md-canonical-vocabulary.md)
- V6.8 propagation contract: [~/Business-Empire-Agent/brain/V68_AGENT_OS_PATTERNS.md](../../../Business-Empire-Agent/brain/V68_AGENT_OS_PATTERNS.md)
- Source pattern: https://github.com/mattpocock/skills/blob/main/CONTEXT.md
