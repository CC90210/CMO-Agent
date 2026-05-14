---
title: Agentic OS — Canonical Cross-Reference (V6.7 anchor for Maven)
source: YouTube video "Build your agentic OS better than 99% of people" (https://www.youtube.com/watch?v=-WCNwxz3uoM)
canonical_copy: ../Business-Empire-Agent/brain/AGENTIC_OS_REFERENCE.md (Bravo holds the master; this is the Maven mirror)
transcript: ../Business-Empire-Agent/docs/references/agentic-os-99pct-transcript.txt
captured: 2026-05-14
version: V6.7 (slots into V6.0/Phase-2 → V6.5 → V6.6 → V6.7 lineage; Bravo CLAUDE.md "Agentic OS Orchestration (V6.7)")
mutability: GOVERNED
purpose: Logic spec Maven must be mappable to. Bravo holds the master; Maven adapts implementation, never the logic.
applies_to: CMO-Agent (Maven). Companion mirrors at ~/Business-Empire-Agent (Bravo), ~/APPS/CFO-Agent (Atlas), ~/APPS/hermes (Hermes).
---

# Agentic OS Reference — Maven Mirror

This is the **logic spec for Maven** — the same 5-layer cross-section and Pantry/Prep Table/Plate taxonomy that governs Bravo, Atlas, and Hermes. Implementation differs per agent; the mental model is invariant.

> **"Sparkly slop on top of a foundation of slop is compounded slop."** Most agentic-OS builds fail because the dashboards/agents/personalities are built on unprepared data. Fix the foundation first.

---

## 1. The Cross-Section (5 layers, top-to-bottom)

| # | Layer | Maven equivalent | Status |
|---|-------|------------------|--------|
| 1 | **Agents / UI** | Maven persona, ad-engine Remotion studio, Command Center web | ✓ shipped |
| 2 | **CLAUDE.md** | `CLAUDE.md` + siblings `GEMINI.md`/`ANTIGRAVITY.md`/`AGENTS.md`/`OPENCODE.md` | ✓ |
| 3 | **Hooks** | `.claude/settings.local.json` (permissions only — V6.7 hooks pending substrate) | ⚠ substrate-blocked |
| 4 | **Skills** | `skills/` (55 skills as of audit) — content-engine, lead-management, growth-engine, meta-ads-management, etc. | ✓ rich |
| 5 | **Data / Integrations** | `late_tool.py` / Zernio, Meta Ads, Google Ads, Instagram, Supabase (shared `phctllmtsogkovoilwos`), `data/pulse/cmo_pulse.json` | ✓ |

**Where Maven is ahead of the video:** chief-of-staff orchestrator pattern (already canonical), cross-agent inbox (shared `agent_inbox.py`), shared Supabase substrate with Bravo + Atlas.

---

## 2. The Four-Layer Maturity Ladder

1. **Identity** — `brain/SOUL.md` (Maven persona), `CLAUDE.md` rules.
2. **Knowledge** — `memory/` (curated), `brain/CONTENT_BIBLE.md`, `data/research/`, `late_tool.py` for live platform data.
3. **Workers** — `agents/*.md` materialized specialists, chief-of-staff orchestrator.
4. **Automations** — V6.7 hooks (pending substrate), n8n cron for content scheduling.

Don't ascend until the layer below is solid. For Maven specifically: layer 3 (substrate) needs guards installed before layer 4 hooks can fully land — see `brain/V67_SUBSTRATE_GAP.md` (if created) for the remediation path.

---

## 3. The Silver Platter Principle (THE central insight)

> "Put the core data on a silver platter so agents spend their session analyzing, not retrieving."

**Failure mode for Maven:** content/ad agents pull live Meta Ads API + Late/Zernio APIs + Instagram + Google Ads stats on every briefing call. 80% of context window goes to retrieval; 20% to actual creative decisioning.

**Fix:** Pre-aggregate deterministically into **Prep Table** snapshots. Agent reads the JSON, spends 100% of its session on synthesis.

### Three-tier data taxonomy

| Tier | Meaning | Maven scope |
|------|---------|-------------|
| **Pantry** | Raw integrations — Late/Zernio, Meta Ads, Google Ads, Instagram Graph API, Supabase content_calendar, `data/research/` | See `brain/DATA_TAXONOMY.md` |
| **Prep Table** | Daily ad performance summary, weekly content velocity rollup, monthly ROAS digest. Python-only, no LLM. | TBD — partial (`cmo_pulse.json` exists but all-zeros, no refresh) |
| **Plate** | CMO briefing skill, ad-creative drafts, `/content-brief` slash command output | `skills/ceo-briefing/` analog needed |

---

## 4. Critical Paths (SOPs for Maven)

Every recurring task gets an explicit SOP. Maven's high-frequency intents:

- "Generate content brief" / "what should we post this week"
- "Draft ad creative" / "build a Meta Ads campaign"
- "Score this content idea" / "is this on-brand"
- "Sync social platforms" / "pull latest Zernio + Meta stats"
- "Schedule post"
- "Log a decision or pattern"

Each lives as a section in `brain/INTENTS.md` (V6.7 addition). Skill SKILL.md files implement the steps.

---

## 5. Cross-Reference — Maven Coverage vs. Spec

| Concept | Maven artifact | Status |
|---------|----------------|--------|
| CLAUDE.md as air-traffic-control | ✓ canonical |
| Empire of CLAUDE.mds (sibling runtimes) | `CLAUDE.md`, `GEMINI.md`, `ANTIGRAVITY.md`, `AGENTS.md`, `OPENCODE.md` | ✓ |
| Skills | 55 skill dirs | ✓ |
| Orchestrator pattern | chief-of-staff equivalent | ✓ |
| **Pantry/Prep Table/Plate taxonomy** | `brain/DATA_TAXONOMY.md` (V6.7) | ✅ NEW |
| **Silver-platter audit skill** | `skills/silver-platter/SKILL.md` (V6.7) | ✅ NEW |
| **Integrations-sync skill** | `skills/integrations-sync/SKILL.md` (V6.7) | ✅ NEW |
| **Memory-journaling skill** | `skills/memory-journaling/SKILL.md` (V6.7) | ✅ NEW |
| **6 INTENTS playbooks** | `brain/INTENTS.md` (V6.7) | ✅ NEW |
| V6.0 substrate (`state_manager.py`, `memory_retriever.py`, guards) | partial — see substrate-gap note | ⚠ open |
| Snapshot scripts (Maven domain) | TBD — adapt Bravo's pattern to `late_tool` / Meta Ads / Google Ads | ⚠ open |

**Open work tracked at:** `memory/ACTIVE_TASKS.md` under "V6.7 substrate completion." Bravo's `brain/AGENTIC_OS_REFERENCE.md` §10 is the master gap audit; this section is Maven's local cut.

---

## 6. Cross-Agent Propagation

Maven receives V6.7 essentials (this file, `DATA_TAXONOMY.md`, `INTENTS.md`, 3 new skills) in the same push that lands them in Bravo. Hooks + snapshot scripts depend on V6.0 substrate scripts that Maven is missing (`state_manager.py`, `memory_retriever.py`, guards). Those land in a follow-up substrate-parity push.

The contract: every sibling agent maps to this logic spec. Implementation is local. Bravo's `brain/AGENTIC_OS_REFERENCE.md` is the canonical master — when it changes, the sibling mirrors update.

## References

- Bravo master: `~/Business-Empire-Agent/brain/AGENTIC_OS_REFERENCE.md`
- Bravo CLAUDE.md V6.7 anchor: search for "Agentic OS Orchestration (V6.7)"
- Source video: https://www.youtube.com/watch?v=-WCNwxz3uoM
- Transcript: `~/Business-Empire-Agent/docs/references/agentic-os-99pct-transcript.txt`
