---
description: Generate comprehensive performance reports — daily snapshots, weekly analysis, or monthly executive summaries.
---

// turbo-all

# /report — Performance Report Generator

## When to Use
Use `/report` for formal performance reports with trends, insights, and recommendations.

## Steps

1. **Determine Type** — Daily snapshot? Weekly analysis? Monthly executive summary?

2. **Pull All Data** — Both platforms with breakdowns (device, placement, time, audience).

3. **Compile Report:**
   ```
   === [Type] Report: [Date Range] ===
   GOOGLE ADS | Campaign | Spend | Impressions | Clicks | CTR | CPC | Leads | CPL | vs Prior |
   META ADS   | Campaign | Spend | Impressions | Clicks | CTR | CPC | Leads | CPL | vs Prior |
   BUDGET: $X spent / $X allocated (X%)
   TOP 3 ADS by CPL | BOTTOM 3 ADS by CPL
   KEY INSIGHTS: [trend + data]
   RECOMMENDED ACTIONS: [specific changes]
   ```

4. **Save** — Update `memory/AD_PERFORMANCE.md`, present to user.

## Example Usage
**User:** `/report`
**Agent:** "Daily, weekly, or monthly?" → Generates formatted report.
