---
description: Analyze underperforming campaigns and apply data-driven optimizations to creative, audience, budget, and bidding.
---

// turbo-all

# /optimize — Campaign Optimization Engine

## When to Use
Use `/optimize` when campaigns underperform, CPL is too high, or you want to improve results.

## Steps

1. **Pull Current Performance** — Run `/performance` workflow first.

2. **Identify Issues:**
   - CPL above target? CTR below 1%? Audience underperforming?
   - Budget pacing off? Ads stuck in Learning Limited?

3. **Diagnose Root Causes:**
   ```
   CPL too high → CTR low? → Creative problem → New ads
                → CVR low? → Landing page problem
                → CPC high? → Refine targeting
   ```

4. **Generate Optimization Plan** — Multi-hypothesis:
   ```
   Issue: [what]
   Hypothesis A: [cause] → Action: [change] → Expected: [impact]
   Hypothesis B: [cause] → Action: [change] → Expected: [impact]
   Recommended: [A/B] — because [data reason]
   ```

5. **Present to User** — Current vs. target, issues, recommended changes.

6. **Implement (with approval)** — Apply via API, log to tracker, set review checkpoint (3-7 days).

## Example Usage
**User:** `/optimize`
**Agent:** "Found 2 issues: Ad Set B at 0.4% CTR, Campaign X 40% over target CPL. Recommending: [changes]. Approve?"
