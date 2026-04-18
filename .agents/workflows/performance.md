---
description: Pull cross-platform ad performance metrics with insights and actionable recommendations.
---

// turbo-all

# /performance — Cross-Platform Performance Metrics

## When to Use
Use `/performance` when checking how ads are doing, pulling metrics, or reviewing campaign health.

## Steps

1. **Determine Scope** — All campaigns or specific? Date range (default: last 7 days)? Both platforms?

2. **Pull Google Ads Data** — Via MCP or SDK:
   ```sql
   SELECT campaign.name, campaign.status,
          metrics.impressions, metrics.clicks, metrics.ctr,
          metrics.average_cpc, metrics.conversions, metrics.cost_micros
   FROM campaign WHERE segments.date DURING LAST_7_DAYS
   ```

3. **Pull Meta Ads Data** — Via MCP or SDK:
   ```python
   account.get_insights(fields=['campaign_name','impressions','clicks','ctr','cpc','spend','actions'], params={'date_preset':'last_7d','level':'campaign'})
   ```

4. **Compile Cross-Platform Report:**
   ```
   === Performance: [Date Range] ===
   GOOGLE ADS | Campaign | Spend | Clicks | CTR | CPC | Leads | CPL |
   META ADS   | Campaign | Spend | Clicks | CTR | CPC | Leads | CPL |
   COMBINED: $X spent | X leads | $X.XX blended CPL
   TOP: [name] — $X.XX CPL | NEEDS ATTENTION: [name] — $X.XX CPL
   RECOMMENDATIONS: 1. [action] 2. [action]
   ```

5. **Log** — Update `memory/AD_PERFORMANCE.md`, append to `memory/SESSION_LOG.md`.

## Example Usage
**User:** `/performance`
**Agent:** Shows formatted report with metrics, insights, and recommendations.
