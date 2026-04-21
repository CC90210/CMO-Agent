# PATTERNS — Validated Approaches

> Tag new patterns as `[PROBATIONARY]`. Promote to `[VALIDATED]` after 3+ successful uses.
> Protocol 4 of `skills/self-improvement-protocol/SKILL.md` writes here.

---

## [VALIDATED] Atlas-Spend-Gate-Before-Campaign
- **Pattern:** Read `data/pulse/cfo_pulse.json` BEFORE any Meta/Google Ads API call that costs money. If `spend_approved_by_atlas: false` OR daily spend would exceed Atlas's ceiling, STOP and surface a spend_request to CC.
- **Why:** Without the gate, a CMO-side agent can trigger runway-material spend while the CFO is blind to it. Single source of truth for "are we allowed to spend today" is Atlas's pulse.
- **Situation:** Every campaign launch, every budget increase, every ad-set resume after pause.
- **Approach:** Pre-flight check at the top of `skills/campaign-creation/SKILL.md`, `skills/meta-ads-management/SKILL.md`, `skills/google-ads-management/SKILL.md` workflows.
- **Outcome:** Zero runway surprises; Atlas retains veto authority; CC gets a structured spend_request to approve/deny rather than an after-the-fact bill.
- **Why it worked:** Aligns with RULE 2 in CLAUDE.md (4-Way Pulse Protocol). Promotes finance sovereignty across agents.
- **When to apply:** Always. No campaign launch is exempt. Even $5/day test campaigns go through the gate.
- **Counter-indications:** None. Gate is non-negotiable.
- **Canon:** Hormozi (spend math), Ritson (diagnose-before-prescribe applies to budget as well as strategy).
- **Status:** [VALIDATED] 2026-04-19 — promoted from [PROBATIONARY] after formal adoption in CLAUDE.md Rule 2.

## [PROBATIONARY] Canon-Citation-Per-Recommendation
- **Pattern:** Every Maven recommendation (campaign brief, offer design, content angle, pricing move, objection handler) must cite at least 1 framework from `brain/MARKETING_CANON.md`. If a recommendation has no canonical citation, it's a draft opinion — not yet a Maven recommendation.
- **Why:** Separates strategy from "craft" (Ritson's distinction). Forces diagnosis before prescription. Prevents AI-slop recommendations that sound confident but have no foundation.
- **Situation:** Any deliverable — sales page draft, ad creative brief, content-calendar proposal, pricing tier design.
- **Approach:** In the draft, inline the citation: "Per Dunford's positioning framework, the current OASIS positioning is [X]..." or append at bottom "Canon: [Hormozi Value Equation, Sharp mental availability]."
- **Outcome:** TBD — patternisnew as of 2026-04-19.
- **When to apply:** Every deliverable. If Maven can't cite, Maven should research before recommending (see `skills/marketing-research/SKILL.md`).
- **Promote to VALIDATED after:** 3 campaigns where canon-citation demonstrably caught a flaw early (e.g., positioning mismatch, wrong buyer-pyramid target, effort-side value-equation blindspot).
- **Status:** [PROBATIONARY] 2026-04-19.

## [PROBATIONARY] Research-Before-Launch (Diagnosis gate)
- **Pattern:** Before any campaign launch for a brand, check that `brain/research/<brand>-voc.md` exists AND is <90 days old AND has ≥5 interviews logged. If not, block the launch pending a Mom-Test round.
- **Why:** Ritson's diagnosis-before-prescription. Most "our copy isn't converting" problems are positioning problems, which are research problems. Launching without fresh VoC = paying to discover you should have interviewed first.
- **Situation:** New campaign briefs, repositioning work, new offer design.
- **Counter-indications:** Platform-urgent maintenance (token refresh, compliance fix) — doesn't need research.
- **Promote to VALIDATED after:** 3 instances where running the research round caught an issue that would have killed the campaign.
- **Canon:** Ritson + Fitzpatrick (Mom Test) + Dunford (positioning research).
- **Status:** [PROBATIONARY] 2026-04-19.

---

## [PROBATIONARY] Meta MCA Ad Category
- **Pattern:** ALL MCA/funding ads on Meta MUST include `special_ad_categories: ['CREDIT']`
- **Why:** Meta requires this for any ad related to credit, funding, or financial services (expanded Jan 2025)
- **Impact:** Ads without this will be rejected. Targeting is restricted (no age, gender, zip, lookalike)
- **Source:** Meta Advertising Standards, research 2026-03-10

## [PROBATIONARY] MCA Language Compliance
- **Pattern:** NEVER use "loan," "lender," "lending," "borrower," "interest rate" in any MCA ad copy
- **Why:** MCA is a purchase of future receivables, NOT a loan. Legal/compliance distinction.
- **Use instead:** "advance," "funding," "capital," "funder," "merchant," "factor rate"
- **Source:** SunBiz Funding SOP, FTC enforcement actions

## [PROBATIONARY] Google Ads MCA Disclosure
- **Pattern:** Google MCA ads must include disclaimers and clear identification as funder or lead generator
- **Why:** Google Ads policy for financial services requires transparent disclosures
- **Impact:** Ads may be disapproved without proper disclosures
- **Source:** Google Ads Financial Services policy, research 2026-03-10

## [PROBATIONARY] Windows MCP Env Variable Fix
- **Pattern:** Use `.cmd` wrapper scripts to inject environment variables for MCP servers on Windows
- **Why:** JSON `env` blocks in MCP configs don't reliably pass vars to subprocesses on Windows
- **How:** Create `scripts/xxx-mcp-wrapper.cmd` that sets vars then launches the server
- **Source:** Inherited from Business Empire Agent (VALIDATED there)

## [PROBATIONARY] SDK Fallback When MCP Fails
- **Pattern:** If MCP server fails, fall back to direct Python SDK calls
- **Why:** MCP servers can have bugs or connectivity issues
- **How:** Use `google-ads` Python library or `facebook-business` Python SDK directly
- **Rule:** Report MCP error first, then fall back. Don't create workaround scripts.
- **Source:** Inherited from Business Empire Agent

## [PROBATIONARY] Campaign Structure Top-Down
- **Pattern:** Always create campaigns top-down: Campaign → Ad Group/Ad Set → Ad
- **Why:** Child objects reference parent IDs. Cannot create ads without a campaign.
- **Both platforms:** Google (Campaign → Ad Group → Ad) and Meta (Campaign → Ad Set → Ad)
- **Source:** API documentation, research 2026-03-10

## [PROBATIONARY] Multi-Hypothesis Approach
- **Pattern:** For moderate+ tasks, generate 2-3 candidate approaches, rank, execute best
- **Why:** Prevents getting stuck on one bad approach
- **Max attempts:** 3 total across all approaches, then escalate
- **Source:** Inherited from Business Empire Agent (VALIDATED there)


---

## Related

- [[INDEX]] · [[self-improvement-protocol/SKILL]] (writes this file) · [[MISTAKES]] · [[MARKETING_CANON]]
- [[STATE]] · [[ACTIVE_TASKS]] · [[SESSION_LOG]]

## Obsidian Links
- [[INDEX]] | [[MISTAKES]] | [[self-improvement-protocol/SKILL]] | [[MARKETING_CANON]]
