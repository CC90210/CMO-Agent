# SKILL: Reporting & Analytics

> Cross-platform performance reporting and data analysis.

---

## Report Types

### 1. Daily Snapshot
Quick overview of today's performance across all platforms.
```
=== Daily Snapshot: YYYY-MM-DD ===

GOOGLE ADS: $X spend | X clicks | X leads | $X CPL
META ADS:   $X spend | X clicks | X leads | $X CPL
COMBINED:   $X spend | X leads | $X CPL

Alerts: [any issues]
```

### 2. Weekly Performance Report
Detailed analysis with trends and recommendations.
```
=== Weekly Report: [Date Range] ===

GOOGLE ADS SUMMARY
| Campaign | Spend | Impressions | Clicks | CTR | CPC | Leads | CPL | vs Last Week |
|----------|-------|-------------|--------|-----|-----|-------|-----|-------------|

META ADS SUMMARY
| Campaign | Spend | Impressions | Clicks | CTR | CPC | Leads | CPL | vs Last Week |
|----------|-------|-------------|--------|-----|-----|-------|-----|-------------|

TOP PERFORMING ADS
1. [ad name] — CTR X.X%, CPL $X.XX
2. [ad name] — CTR X.X%, CPL $X.XX

BOTTOM PERFORMING ADS
1. [ad name] — CTR X.X%, CPL $X.XX (recommendation)
2. [ad name] — CTR X.X%, CPL $X.XX (recommendation)

KEY INSIGHTS
1. [insight + data]
2. [insight + data]

RECOMMENDED ACTIONS
1. [specific action]
2. [specific action]
```

### 3. Monthly Executive Summary
High-level overview for client/stakeholders.
```
=== Monthly Report: [Month Year] ===

HEADLINES
- Total spend: $X,XXX
- Total leads: XX
- Blended CPL: $XX.XX
- Best platform: [Google/Meta]
- Month-over-month change: +/-X%

BUDGET UTILIZATION: X% of allocated budget spent
ROI ESTIMATE: X leads × estimated lead value = $X potential revenue
```

## Data Sources

### Google Ads (via GAQL)
```sql
-- Weekly campaign performance
SELECT campaign.name, metrics.impressions, metrics.clicks, metrics.ctr,
       metrics.average_cpc, metrics.conversions, metrics.cost_micros
FROM campaign
WHERE segments.date DURING LAST_7_DAYS
ORDER BY metrics.cost_micros DESC

-- Daily breakdown
SELECT segments.date, metrics.impressions, metrics.clicks,
       metrics.conversions, metrics.cost_micros
FROM campaign
WHERE campaign.id = {id}
  AND segments.date DURING LAST_30_DAYS
ORDER BY segments.date DESC
```

### Meta Ads (via Insights API)
```python
insights = Campaign(id).get_insights(
    fields=['impressions', 'clicks', 'ctr', 'cpc', 'spend',
            'actions', 'cost_per_action_type'],
    params={
        'date_preset': 'last_7d',
        'breakdowns': ['age', 'gender', 'placement'],
        'time_increment': 1,  # daily granularity
    }
)
```

## Key Metrics Glossary
| Metric | Formula | Good for Lending |
|--------|---------|-----------------|
| CPL | Spend / Leads | < $50 (varies by market) |
| CTR | Clicks / Impressions | > 2% (Search), > 1% (Meta) |
| CPC | Spend / Clicks | < $3 (varies) |
| CVR | Leads / Clicks | > 5% |
| ROAS | Revenue / Spend | > 3x |
| CPM | (Spend / Impressions) × 1000 | < $30 |
| Frequency | Impressions / Reach | < 3 (Meta) |

## Reporting Cadence
- **Daily:** Quick spend/lead check (automated via n8n if set up)
- **Weekly:** Full performance review with recommendations
- **Monthly:** Executive summary for client
- **Quarterly:** Strategy review and planning
