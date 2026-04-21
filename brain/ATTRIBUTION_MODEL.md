---
tags: [attribution, analytics, schema, canon]
version: 1.0.0
canon_references: [ritson-diagnosis, sharp-how-brands-grow, hormozi-lead-flows]
---

# ATTRIBUTION MODEL — Content → Lead → Deal

> Every dollar of ad spend and every hour of content creation needs a line back to revenue, or it's craft. This model is how Maven proves (or disproves) that line.

## Why this exists

Single-touch attribution (last-click) lies. Byron Sharp's research + Les Binet & Peter Field's long/short-term evidence show that brand-building content compounds over 6-24 months before it closes a deal. A last-click model gives 100% credit to the final ad and 0% to the Reel that planted the problem-awareness 8 months earlier. That's how marketing budgets get cut.

Multi-touch attribution acknowledges reality: a buyer touched your brand N times across M channels over T months before they converted. Each touch gets partial credit based on a defensible rule.

## Scope

This model covers:
- Content → Lead (first-touch + influence touches)
- Lead → Deal (last-qualifying-touch + close assists)
- Cross-brand (when CC's personal content drives an OASIS lead, track both)

This model does NOT cover:
- Brand-lift measurement (requires geo-holdouts + surveys — separate doc)
- MMM (marketing mix modeling — only valuable >$100K/month ad spend)

---

## The 5 Touchpoint Types

Every touch is tagged with one of these types. Aggregated over a lead's lifetime, they tell the attribution story.

| Type | Description | How captured |
|------|-------------|--------------|
| `content_view` | Passive exposure (video watched, post seen, page viewed) | Meta Pixel, GA4 events, Substack opens |
| `content_engage` | Active engagement (comment, reply, share, bookmark) | Platform APIs, CRM capture |
| `direct_inbound` | They reached out first (DM, email, form) | PULSE capture, form webhook, email inbox |
| `ad_click` | Paid click leading to a tracked landing page | UTM + Pixel + GCLID |
| `sales_touch` | 1:1 human contact (call, meeting, custom reply) | Manual log or call-transcription hook |

---

## Schema (Supabase extension on `leads`)

### Existing `leads` table (abbreviated)
```sql
-- existing fields we rely on
id uuid PRIMARY KEY
agent text                       -- 'maven', 'bravo', etc.
brand text                       -- 'oasis', 'propflow', 'nostalgic', 'cc-personal', 'sunbiz'
captured_at timestamptz
source text                       -- channel
status text                       -- 'new' | 'mql' | 'sql' | 'won' | 'lost' | 'stalled'
```

### NEW columns (migration proposal)

```sql
ALTER TABLE leads
  ADD COLUMN source_content_ids JSONB DEFAULT '[]',
  ADD COLUMN attribution_touches JSONB DEFAULT '[]',
  ADD COLUMN first_touch_at timestamptz,
  ADD COLUMN last_qualifying_touch_at timestamptz,
  ADD COLUMN attribution_model_version text DEFAULT 'v1';

CREATE INDEX idx_leads_first_touch ON leads (first_touch_at);
CREATE INDEX idx_leads_source_content ON leads USING gin (source_content_ids);
```

### `source_content_ids` shape
Array of canonical content identifiers that appeared in this lead's journey.
```json
[
  "reel:oasis:2026-04-02:pulse-hook-v2",
  "post:cc-personal:2026-04-05:build-in-public-week-14",
  "email:oasis:pulse-teaser:v3",
  "ad:meta:cmp-12345:adset-67890:ad-abc"
]
```

Convention: `<type>:<brand>:<date>:<slug>` or `ad:<platform>:<cmp>:<adset>:<ad>`.

### `attribution_touches` shape
Full touch log. Most recent first.
```json
[
  {
    "at": "2026-04-18T14:22:31Z",
    "type": "sales_touch",
    "channel": "call",
    "content_id": null,
    "source_medium": "discovery-call",
    "notes": "30-min call with CC. Said yes to proposal.",
    "touch_weight": 1.0
  },
  {
    "at": "2026-04-14T09:10:00Z",
    "type": "ad_click",
    "channel": "meta",
    "content_id": "ad:meta:cmp-12345:adset-67890:ad-abc",
    "source_medium": "cpc",
    "utm_campaign": "pulse-lead-gen",
    "touch_weight": 0.4
  },
  {
    "at": "2026-04-02T11:05:00Z",
    "type": "content_view",
    "channel": "instagram",
    "content_id": "reel:oasis:2026-04-02:pulse-hook-v2",
    "source_medium": "organic-reel",
    "touch_weight": 0.2
  }
]
```

---

## Attribution Models (pick one per brand per query)

### Model 1 — First Touch
100% credit to `first_touch_at` content_id. Use for: which content builds awareness?

### Model 2 — Last Qualifying Touch
100% credit to the touch that pushed lead from MQL → SQL. Use for: which channel closes?

### Model 3 — Linear
Equal credit to every touch in `attribution_touches`. Use for: honest + boring baseline.

### Model 4 — Time Decay
Exponential decay — most recent touch gets most credit. Half-life = 14 days. Use for: most operationally useful; balances awareness and close.

### Model 5 — Position-Based (U-shape)
40% first touch, 40% last qualifying, 20% split across middle touches. Use for: brand-builders who also close fast.

### Maven's default: **Time Decay (14-day half-life)** for operational dashboards + **First Touch** for content ROI dashboards + **Last Qualifying** for sales-channel ROI dashboards. Always name the model when citing a number.

---

## Queries Maven Runs

### Which content drives the most MQLs (first-touch model, 30d)?
```sql
SELECT
  jsonb_array_elements(source_content_ids) ->> 0 AS content_id,
  COUNT(*) AS mqls,
  COUNT(*) FILTER (WHERE status IN ('sql', 'won')) AS progressed,
  ROUND(100.0 * COUNT(*) FILTER (WHERE status IN ('sql', 'won')) / COUNT(*), 1) AS progress_rate_pct
FROM leads
WHERE agent = 'maven'
  AND brand = 'oasis'
  AND first_touch_at > now() - interval '30 days'
GROUP BY 1
ORDER BY mqls DESC
LIMIT 20;
```

### Ad spend vs. revenue, time-decay attribution (30d)?
```sql
WITH decayed AS (
  SELECT
    id,
    brand,
    jsonb_array_elements(attribution_touches) AS touch,
    ROW_NUMBER() OVER (PARTITION BY id ORDER BY (jsonb_array_elements(attribution_touches) ->> 'at') DESC) AS rn
  FROM leads
  WHERE status = 'won' AND won_at > now() - interval '30 days'
)
SELECT
  brand,
  touch ->> 'channel' AS channel,
  SUM(
    (touch ->> 'touch_weight')::numeric
    * EXP(-0.0495 * EXTRACT(EPOCH FROM (now() - (touch ->> 'at')::timestamptz)) / 86400)
  ) AS decayed_credit
FROM decayed
GROUP BY brand, channel
ORDER BY decayed_credit DESC;
```
(0.0495 ≈ ln(2)/14 for a 14-day half-life)

### Cross-brand assist — CC personal content driving OASIS deals?
```sql
SELECT
  l.id,
  l.brand AS lead_brand,
  jsonb_array_elements_text(l.source_content_ids) AS content,
  l.status
FROM leads l
WHERE l.brand = 'oasis'
  AND l.source_content_ids::text LIKE '%cc-personal%'
  AND l.captured_at > now() - interval '90 days';
```

---

## Content ID registry (`brain/research/content_registry.md`)

Every published piece of content gets registered:
```markdown
## reel:oasis:2026-04-02:pulse-hook-v2
- Published: 2026-04-02
- Platform: instagram + tiktok
- Brand: OASIS
- Campaign: pulse-lead-gen
- Hook: "I automated my DMs and 40% of my leads started closing themselves"
- CTA: bio link → calendly
- Assets: `ad-engine/exports/pulse-hook-v2.mp4`
```

This registry is the human-readable index. Supabase is the machine-readable join table.

---

## Capture Implementation (build order)

### Phase 1 — Week 1 (MANUAL)
- Every new lead gets a manual `source_content_ids` entry populated by Maven at capture time
- Manual attribution_touches for the first 20-30 leads
- Goal: prove the model works before automating

### Phase 2 — Week 2-3 (AUTOMATED)
- Meta Pixel + GA4 event capture → `scripts/attribution_capture.py` writes to `leads.attribution_touches`
- Cron: every hour, pull new events, merge by email/phone hash

### Phase 3 — Month 2 (MULTI-BRAND)
- Cross-brand identity resolution (same phone/email → same person across brands)
- Content registry fully populated for CC personal + OASIS + PropFlow
- Attribution dashboards in Supabase materialized views

### Phase 4 — Month 3+ (PRODUCTION)
- Auto-expire stale touches (>365 days) to keep JSONB small
- Attribution confidence score per lead (low = we only have 1 touch, high = we have 5+)
- Incrementality tests (geo-holdouts for paid) — requires $30K+ monthly spend to be statistically meaningful

---

## Canon Grounding

- **Ritson — diagnosis before prescription**: this model IS the diagnosis. Spending money without attribution data = prescribing without diagnosing.
- **Sharp — reach over frequency**: first-touch model helps identify the content that delivers MENTAL AVAILABILITY to new buyers. Never cut first-touch-winners because their last-click rate looks bad.
- **Hormozi — 4 lead flows**: each of the 4 (warm, content, paid, cold) gets attributed separately. A given lead's attribution_touches array shows which flows are doing the heavy lifting.
- **Binet & Field — 60:40 brand:activation**: content with high content_view counts but low direct last-click is the 60% brand-builder. Do not kill it based on last-click alone.

---

## Anti-Patterns to Reject

1. **Only last-click attribution** → kills brand-building content at month 3. Use time-decay minimum.
2. **Trusting the default platform attribution** → Meta and Google each claim the same conversion. Run your own model.
3. **Building attribution before product-market fit** → premature. Below ~$5K MRR, the right metric is "did we get any sign of intent?" not "which of these 7 touches deserves credit?"
4. **Reporting attribution without naming the model** → "content drove 40% of leads" is meaningless without "under the time-decay 14-day model, first-touch weighted."
5. **Over-weighting brand lift without numbers** → Sharp is right that brand matters, but you still need evidence. Don't hide behind "brand" when activation numbers are bad.

---

## Alert Thresholds

- A single `ad:*` touch > 80% of all won-deal credit for 14+ days → over-dependence on one ad, creative fatigue incoming, diversify
- First-touch content concentration: if top 3 content_ids account for >70% of first-touches, content engine is too narrow
- Zero `content_view` touches in a won deal's history → data-capture broken for that brand
- Median touches-per-won-deal trending down → funnel getting shorter (good) OR tracking broken (bad — verify before celebrating)

---

## Related

- [[INDEX]] — vault home
- [[MARKETING_CANON]] — framework library this model rests on
- [[SHARED_DB]] — Supabase schema context
- [[content_registry]] — canonical content IDs this model consumes
- [[WRITING]] — the copy pipeline that terminates in registration + attribution
- [[lead-management/SKILL]] — lead lifecycle this model augments
- [[funnel-management/SKILL]] — funnel metrics this model powers
- [[reporting-analytics/SKILL]] — dashboards that consume this model

## Obsidian Links
- [[INDEX]] | [[MARKETING_CANON]] | [[content_registry]] | [[SHARED_DB]] | [[WRITING]]
