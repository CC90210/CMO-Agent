# PATTERNS — Validated Approaches

> Tag new patterns as `[PROBATIONARY]`. Promote to `[VALIDATED]` after 3+ successful uses.

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
