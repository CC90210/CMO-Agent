# SOP LIBRARY — Standard Operating Procedures

---

## SOP-001: Create a Google Ads Campaign

### Prerequisites
- Google Ads API credentials configured in `.env.agents`
- Google Ads MCP server or Python SDK available
- Client's Google Ads customer ID

### Steps
1. **Define campaign objective** (Search, Display, Video, Performance Max)
2. **Create campaign budget** — `CampaignBudgetService.mutate()` with daily amount in micros
3. **Create campaign** — Set name, type, status (PAUSED initially), network settings, bidding strategy
4. **Create ad group(s)** — Set name, bid amount, targeting type
5. **Add keywords** (for Search) — `AdGroupCriterionService.mutate()` with match type
6. **Create ad(s)** — Responsive Search Ad (headlines + descriptions) or Display Ad (images + copy)
7. **Review & verify** — Read back campaign via API to confirm structure
8. **Enable campaign** — Set status to ACTIVE (after user approval)
9. **Log to CAMPAIGN_TRACKER.md**

---

## SOP-002: Create a Meta Ads Campaign (MCA)

### Prerequisites
- Meta Marketing API credentials configured in `.env.agents`
- Meta Ads MCP server or Python SDK available
- Client's ad account ID (act_XXXXXXXXX)

### Steps
1. **Define campaign objective** (OUTCOME_LEADS for MCA)
2. **Create campaign** — Include `special_ad_categories: ['CREDIT']` (MANDATORY)
3. **Create ad set** — Set budget, schedule, targeting (remember: no age/gender/zip for credit)
4. **Upload creative assets** — Images via `adimages` endpoint, videos via `advideos` endpoint
5. **Create ad creative** — Link assets with copy (headline, body, CTA)
6. **Create ad** — Link creative to ad set
7. **Review & verify** — Read back via API
8. **Enable** — Set status to ACTIVE (after user approval)
9. **Log to CAMPAIGN_TRACKER.md**

---

## SOP-003: Pull Performance Report

### Steps
1. **Identify scope** — Which campaigns/platforms? What date range?
2. **Google Ads** — Execute GAQL query via SearchStream
3. **Meta Ads** — Call Insights API with fields and breakdowns
4. **Compile metrics** — Impressions, clicks, CTR, CPC, conversions, CPL, spend, ROAS
5. **Compare to targets** — CPL vs. target, CTR benchmarks, budget pacing
6. **Generate summary** — Human-readable report with recommendations
7. **Log to SESSION_LOG.md**

---

## SOP-004: Optimize Underperforming Campaign

### Steps
1. **Pull performance data** (SOP-003)
2. **Identify issues:**
   - High CPL → Check targeting, ad relevance, landing page
   - Low CTR → Check ad copy, creative, audience match
   - Low impressions → Check budget, bid, targeting too narrow
   - High CPC → Check competition, quality score, bid strategy
3. **Generate 2-3 optimization hypotheses** (BRAIN_LOOP Step 4)
4. **Implement top hypothesis** — Adjust targeting, copy, bid, or budget
5. **Set review checkpoint** — Check results after 3-7 days
6. **Log changes to CAMPAIGN_TRACKER.md**

---

## SOP-005: API Health Check

### Steps
1. **Google Ads:** Attempt to list campaigns → Verify auth works
2. **Meta Ads:** Attempt to read ad account → Verify token valid
3. **Check token expiry dates**
4. **Verify MCP servers responding**
5. **Report health status** (format in HEARTBEAT.md)
