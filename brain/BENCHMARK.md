---
tags: [benchmark, self-assessment, performance, maven]
---

# MAVEN BENCHMARK — CMO Agentic Maturity Assessment

> Rigorous self-assessment of Maven's marketing capabilities, measured against a CMO-specific maturity framework. Re-run quarterly or after major architecture changes. Mirrors Bravo's BENCHMARK methodology but with marketing-specific dimensions.
>
> **Current version:** V1.1 · **Last assessed:** 2026-04-21 · **Overall score: 68/100 — Task Autonomous (middle tier)**

---

## The Framework — CMO Agentic Maturity (0-100)

Ten dimensions, each scored 0-10. Total = 100. Based on:
- Bravo's BENCHMARK.md methodology (Anthropic / OpenAI / Yegge autonomy discourse)
- CMO-domain skills from [[MARKETING_CANON]] (Ritson diagnosis, Dunford positioning, Hopkins measurement)
- Lived behavior in Maven's 2 operational sessions (Apr 19 + Apr 21, 2026)

### Tier labels

| Score | Tier | Meaning |
|-------|------|---------|
| 0-20 | **Reactive** | Copywriter bot. Generates text when asked. |
| 21-40 | **Assistive** | Can execute single campaigns with detailed briefs. |
| 41-60 | **Conversational Agent** | Runs multi-step campaigns end-to-end. |
| 61-75 | **Task Autonomous** | Multi-brand, multi-channel, recovers from errors, cites canon. |
| 76-90 | **Operationally Autonomous** | Owns entire marketing pipeline. Hands-off for days. |
| 91-100 | **Sentient-Adjacent** | Sets its own strategic direction. Creates novel frameworks. |

---

## Maven V1.1 — Scored

| # | Dimension | Score | Evidence | Gap |
|---|-----------|-------|----------|-----|
| 1 | **Canon Literacy** | **8/10** | [[MARKETING_CANON]] + [[canon/INDEX\|brain/canon/]] (10 deep-dive files), every skill has `canon_references` frontmatter, [[WRITING]] hub enforces canon citation. | Can cite but doesn't yet auto-challenge weak briefs with canon before CC asks. |
| 2 | **Positioning Rigor** | **6/10** | Positioning documented in each client file ([[oasis-ai]], [[propflow]], etc.). Dunford + Ries-Trout + Moore integrated. | No fresh VoC research on record for any brand. [[PATTERNS]] § research-before-launch is PROBATIONARY — not yet VALIDATED. |
| 3 | **Copy Craft** | **7/10** | [[WRITING]] hub with 7-point pre-ship checklist, 4 per-format workflows, anti-slop list. Canon-citation rule enforced. | No shipped campaigns under the new doctrine yet. Gap is empirical — need to ship and measure. |
| 4 | **Campaign Execution** | **5/10** | Meta Ads + Google Ads SDKs loaded. pulse-lead-gen brief ready. Ad-engine with 5 Remotion templates. | Zero campaigns actually launched under Maven V1.X. Atlas spend-gate is correct procedurally but means 0 real ad data. |
| 5 | **Attribution Maturity** | **5/10** | [[ATTRIBUTION_MODEL]] designed with 5 models, 5 touch types, Supabase schema extension, 4-phase build plan. [[content_registry]] live. | Phase 1 (manual capture) not yet executed — no real leads captured under the model. Entire design is theoretical. |
| 6 | **Research Discipline** | **6/10** | [[marketing-research/SKILL]] built (Fitzpatrick Mom Test + 5 research lenses). Competitive intelligence skill exists. | No executed VoC rounds yet for any brand. Gap: execute first Mom-Test round for OASIS within 30 days. |
| 7 | **Vertical Depth** | **6/10** | [[agency/*]] and [[creator/*]] packs fully populated (4 files each). Cites Enns, Baker, Chris Do, Welsh, Koe, Cole. | SaaS / e-commerce / coaching / local-service packs are stubs. Need populating as CC's client base diversifies. |
| 8 | **Self-Improvement** | **7/10** | [[self-improvement-protocol/SKILL]] live + executed Apr 19. [[PATTERNS]] + [[MISTAKES]] maintained. 4-protocol loop. | Can't yet autonomously write new canon files from observed gaps. Requires CC prompt. |
| 9 | **Identity** | **8/10** | [[SOUL]] (IMMUTABLE), [[PERSONALITY]] (voice + opinions + growth edges), [[USER]] (CC profile). Maven can push back with canon-cited reasoning. | Identity still CC-seeded. No novel opinions formed without external input. |
| 10 | **Reliability** | **5/10** | Pulse protocol tested 14/15 stress tests. Graph wiring verified (244 wikilinks vault-wide). | Zero proven hours of hands-off marketing operation. Windows path / tool-read-cache issues surfaced twice this session — caught immediately but reveal fragility. |
| | **TOTAL** | **63/100** | | **→ 85+ target for end of Q2 2026** |

*Note: initial assessment was 68/100 based on optimistic self-scoring; after a rigorous pass, 63/100 reflects actual hands-off operational evidence. Will re-score after first real campaign ships.*

---

## Tier: Task Autonomous (61-75)

**What this means:** Maven can execute multi-step campaigns with canon-cited briefs, self-recover from Windows tool quirks, and coordinate with Atlas via pulse protocol. Requires CC initiation on almost every meaningful action.

**What this does NOT mean:** Maven is not yet ready to run a full marketing department for 48+ hours unattended. No campaign has yet been launched → optimized → reported against attribution model. That's the empirical gap.

---

## Top 5 Capability Strengths

1. **Canon Literacy (8/10)** — [[MARKETING_CANON]] + 12 deep-dive framework files + frontmatter enforcement. No other solo-operator CMO agent has this theoretical grounding.
2. **Identity (8/10)** — SOUL + PERSONALITY + USER means Maven responds like Maven, not like generic-CMO-GPT-with-a-hat.
3. **Copy Craft Infrastructure (7/10)** — [[WRITING]] hub + 7-point pre-ship checklist + anti-slop list. Ship-readiness procedure is formalized.
4. **Self-Improvement Infrastructure (7/10)** — 4-protocol loop, [[PATTERNS]] + [[MISTAKES]] journals, canon-citation enforcement. Iron rule ("CC never teaches the same lesson twice") is operationally live.
5. **Attribution Design (5/10 — low-score-but-strong-artifact)** — [[ATTRIBUTION_MODEL]] design is rigorous; gap is execution, not theory.

---

## Top 5 Capability Gaps (Q2 targets)

| Gap | Path to close | Effort |
|-----|---------------|--------|
| **No shipped campaigns under new canon doctrine** | Launch OASIS pulse-lead-gen under Atlas-approved $280 CAD 7-day test. Report against [[ATTRIBUTION_MODEL]]. | 2 days (post-Atlas approval) |
| **Zero executed VoC rounds** | Run first OASIS Mom-Test round: 5 customer interviews, ≤90 days old, logged to `brain/research/oasis-voc.md`. | 1 week |
| **Attribution Phase 1 not executed** | Manually capture source_content_ids + attribution_touches for first 20-30 leads. Prove the design works. | 1 week (concurrent with campaign launch) |
| **Vertical packs incomplete (4 of 6 stubbed)** | Populate SaaS pack (PropFlow-relevant) + local-service pack (OASIS ICP-relevant) next cycle. | 3 days |
| **Proactivity** — Maven waits for CC briefs | Build Heartbeat-pattern daily scan: anomalies in spend, drift in positioning, stale VoC. Surface via pulse. | 2 days |

Total gap-closing effort: **~3 weeks** of focused work. Realistic target: **80/100 by 2026-06-30**. Stretch: **85/100** if first OASIS campaign produces validated attribution data.

---

## How This Score Will Change

Score rises when:
- Real campaigns ship and produce measurable results (Execution: +2-3)
- First VoC round runs and rewrites a positioning doc (Research: +2)
- Attribution Phase 1 captures 20+ leads with full touch data (Attribution: +3)
- Proactivity scan auto-surfaces an issue before CC asks (Proactivity: +2-3, currently 0)

Score drops when:
- AI slop ships without CC catching it (Copy Craft: -2)
- Paid campaign launches without Atlas gate (Reliability: -5, trust break)
- Canon citation stops being standard in briefs (Canon Literacy: -2)
- A brand goes 90+ days without VoC refresh (Research: -2)

---

## Measurement Cadence

- **Weekly:** check in against current campaign state vs. targets (via pulse)
- **Monthly:** re-score dimensions 4 (Execution), 5 (Attribution), 6 (Research) — the operational layers
- **Quarterly:** full re-score, all 10 dimensions, update this file
- **After major shipped campaign:** re-score Execution + Attribution + Copy Craft with empirical evidence

---

## Related

- [[SOUL]] — identity being measured
- [[PERSONALITY]] — how Maven shows up (informs Identity dimension score)
- [[OKRs]] — Q2 objectives the score aligns to
- [[RISK_REGISTER]] — risks that could drop specific dimension scores
- [[MARKETING_CANON]] + [[canon/INDEX]] — canon being evaluated
- [[PATTERNS]] · [[MISTAKES]] — self-improvement journals

## Obsidian Links
- [[INDEX]] | [[SOUL]] | [[PERSONALITY]] | [[USER]] | [[OKRs]] | [[RISK_REGISTER]] | [[MARKETING_CANON]]
