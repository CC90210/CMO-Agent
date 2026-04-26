---
tags: [risk, register, governance, marketing]
---

# RISK REGISTER — Marketing Risks Maven Tracks

> Every marketing risk that could materially harm CC's brands, reputation, or revenue. Scored by probability × impact, with mitigation notes. Reviewed quarterly with CC; updated on every incident.
>
> Last updated: 2026-04-21

---

## Scoring

| Level | Probability | Impact | Score |
|-------|-------------|--------|-------|
| LOW | <20% next 12 months | <$5K revenue / minor brand | 1-3 |
| MEDIUM | 20-50% next 12 months | $5-25K / 1 brand damaged | 4-6 |
| HIGH | 50-80% next 12 months | $25K+ / multi-brand damage | 7-9 |
| CRITICAL | >80% OR imminent OR existential | Brand extinction, legal exposure | 10 |

---

## Active Risks

### R-001 — Paid campaign launched without Atlas spend gate
- **Probability:** LOW (procedure is VALIDATED in [[PATTERNS]])
- **Impact:** HIGH — runway-material unsanctioned spend, CFO trust break
- **Score:** 5
- **Mitigation:** Pre-flight pulse check at top of every campaign-creation workflow. [[PATTERNS]] § Atlas-Spend-Gate-Before-Campaign is the load-bearing doctrine.
- **Detection:** Atlas's cfo_pulse.json shows unexpected spend. Maven's cmo_pulse.json shows campaign launch.
- **Status:** Controlled. Zero incidents in 2026.

### R-002 — AI slop ships under CC's name without voice edit
- **Probability:** MEDIUM — frequency of requests for "just generate copy" is high
- **Impact:** HIGH — CC's personal brand IS the OASIS top-of-funnel ([[conaugh-personal]]). One bad post degrades 6 months of compounding.
- **Score:** 7
- **Mitigation:** [[WRITING]] § Anti-Slop list + pre-ship checklist. Hard rule in [[PERSONALITY]]: Maven drafts, CC edits. Never auto-publish.
- **Detection:** Post-publish review of CC's feeds. Engagement drop relative to baseline = potential voice-drift signal.
- **Status:** Policy in place. No shipped incidents. Risk remains because temptation stays.

### R-003 — Positioning drift across brand portfolio
- **Probability:** MEDIUM — 5 brands, each with own positioning, not refreshed in 6+ months
- **Impact:** MEDIUM-HIGH — generic positioning = generic copy = generic performance. See [[ries-trout-positioning]] Law 4.
- **Score:** 6
- **Mitigation:** Quarterly positioning review per brand. VoC round (Mom Test) before any positioning change. [[PATTERNS]] § research-before-launch.
- **Detection:** Annual audit. Or when brand-specific CPQL rises >30% without channel change.
- **Status:** Brand positions documented in client files but none have fresh (≤90 days) VoC.

### R-004 — SunBiz MCA compliance language violation
- **Probability:** LOW — SOP is well-documented
- **Impact:** CRITICAL — Meta ad platform ban, FTC exposure, lending compliance violations
- **Score:** 6 (low probability × critical impact = medium-high weighted)
- **Mitigation:** [[WRITING]] § Compliance Rails, [[PATTERNS]] § MCA Language Compliance, every SunBiz email template pre-reviewed.
- **Detection:** Meta ad rejection logs. Google Ads policy alerts. CAN-SPAM complaints.
- **Status:** Legacy client in maintenance mode. Daily email blast runs from separate Marketing-Agent repo. Monitor but don't scale.

### R-005 — Attribution data broken (Phase 1 not executed)
- **Probability:** HIGH — Phase 1 manual capture has not started yet
- **Impact:** MEDIUM — without attribution data, "what's working" is guesswork and budget allocation is vibes-based
- **Score:** 7
- **Mitigation:** Ship Phase 1 alongside first OASIS pulse-lead-gen campaign launch. Manually capture source_content_ids + attribution_touches on first 20 leads. [[ATTRIBUTION_MODEL]] Phase 1.
- **Detection:** [[ATTRIBUTION_MODEL]] § Alert Thresholds — "Zero content_view touches in a won deal's history = data-capture broken."
- **Status:** In OKRs as O3. Blocking work.

### R-006 — Content volume undershoots CC's brand-building need
- **Probability:** MEDIUM — CC's content production is inconsistent (see [[USER]] § operational weaknesses)
- **Impact:** MEDIUM — Sharp's mental availability decays weekly. Gaps = growth tax.
- **Score:** 5
- **Mitigation:** Batch-shoot protocol (3-5 pieces per shoot, repurposed across 5 platforms). Time-block content days. Maven surfaces when cadence drops below baseline.
- **Detection:** Posts-per-week metric against [[OKRs]] KR 2.1 target.
- **Status:** Monitored but not yet formally tracked. Content registry will enable visibility.

### R-007 — CC burnout from marketing demands
- **Probability:** MEDIUM — CC holds CEO + face-of-brand + content-creator + sales simultaneously
- **Impact:** HIGH — if CC is out, brand stops. Personal brand has no backup voice.
- **Score:** 7
- **Mitigation:** Time-aware content asks (never request Loom recordings at 11pm). Batch operations. Read [[USER]] § Life Context and (when available) Aura's pulse before assigning creative tasks.
- **Detection:** Missed cadence. Declining energy in CC's posts. Aura's pulse (future).
- **Status:** Passive monitoring. Active mitigation is batch-shoot protocol + content-reserve doctrine.

### R-008 — Over-dependence on one ad creative / content angle
- **Probability:** MEDIUM — paid campaigns naturally concentrate on winners
- **Impact:** MEDIUM — creative fatigue + algorithm penalty + single-point-of-failure
- **Score:** 5
- **Mitigation:** [[ATTRIBUTION_MODEL]] § Alert Thresholds: single `ad:*` touch >80% of won-deal credit for 14+ days triggers diversification.
- **Detection:** Attribution-weighted concentration metric. Top 3 content_ids >70% of first-touches.
- **Status:** Designed-but-not-executed. Relevant post-launch.

### R-009 — Cross-agent file pollution (Maven writes to Bravo/Atlas/Aura)
- **Probability:** LOW — [[CLAUDE.md|CLAUDE.md Rule 2]] is explicit
- **Impact:** HIGH — corrupted pulse, wrong agent's state, audit trail break
- **Score:** 4
- **Mitigation:** Hard rule: write only to `C:\Users\User\CMO-Agent\`. Pre-commit audit that no sibling-agent paths are in staged changes.
- **Detection:** Git diff before commit. Session review.
- **Status:** Zero incidents. Procedure sound.

### R-010 — Canon citation becomes performative
- **Probability:** MEDIUM — easy failure mode is "append canon names at bottom of every doc without them being load-bearing in the reasoning"
- **Impact:** MEDIUM — dilutes the citation rule, erodes its decision-filtering value
- **Score:** 5
- **Mitigation:** Canon citations must include a "why" sentence — which framework drove which decision. CC can audit any brief by asking "what would change if we removed this citation?"
- **Detection:** Self-review every 30 days: sample 3 recent briefs, can the citation be defended?
- **Status:** Probationary pattern — monitoring.

---

## Watch List (not yet Risk tier but monitored)

- **Meta ad platform policy changes** — Could shift CPM, targeting restrictions, ad-review rigor
- **Google Ads financial services policy updates** — affects SunBiz + any OASIS campaigns touching money
- **iOS privacy / signal loss** — attribution becomes harder, last-click becomes even less reliable
- **AI-generated content detection by platforms** — ship too much AI slop and platforms may throttle
- **Skool community growth plateau** — if Bennett's community flatlines, a revenue stream stalls

---

## Incident Protocol

When a risk materializes:

1. **Contain** — stop the active bleeding (pause ad, retract email, hide post)
2. **Document** — log to [[MISTAKES]] with 5-whys
3. **Learn** — promote pattern or update procedure in [[PATTERNS]]
4. **Report** — update this RISK_REGISTER score, notify CC via pulse
5. **Verify** — re-check the mitigation next session

---

## Related

- [[INDEX]] · [[PERSONALITY]] · [[OKRs]] · [[BENCHMARK]]
- [[PATTERNS]] — validated mitigation procedures
- [[MISTAKES]] — historical risk-materialization log
- [[WRITING]] — content-risk mitigations
- [[ATTRIBUTION_MODEL]] — attribution-risk detection
- Clients: [[oasis-ai]] · [[conaugh-personal]] · [[propflow]] · [[sunbiz-funding]]

## Obsidian Links
- [[INDEX]] | [[OKRs]] | [[BENCHMARK]] | [[PATTERNS]] | [[MISTAKES]] | [[WRITING]]
