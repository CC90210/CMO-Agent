# PIPELINE — Shopify Ad Engine Data Flow

> Three-step pipeline: Sync → Render → Post. Each step produces artifacts consumed by the next.

## Overview

```
Shopify Store (Storefront API)
  │
  ▼  Step 1: npm run shopify:sync
products.json            (project root)
public/products/*.jpg    (Remotion static assets)
  │
  ▼  Step 2: npm run render:all
exports/{handle}/{Template}-{format}.mp4
  │
  ▼  Step 3: python scripts/meta_ads_engine.py
Meta video creative ID → ad set → live campaign
```

---

## Step 1: Product Sync

**Script:** `scripts/shopify_sync.js`
**Trigger:** `npm run shopify:sync` or `node scripts/shopify_sync.js --limit 10`

### What it does

1. Reads `SHOPIFY_STORE` + `SHOPIFY_ACCESS_TOKEN` from `.env`
2. Paginates the Shopify Storefront GraphQL API (50 products/page)
3. For each product: extracts title, description, price, compareAtPrice, tags, images, variants
4. Downloads the first image per product to `public/products/{handle}.{ext}` (skips if cached)
5. Writes `products.json` to project root

### products.json shape (per product)

```json
{
  "id": "gid://shopify/Product/123",
  "handle": "premium-wireless-earbuds",
  "title": "Premium Wireless Earbuds",
  "description": "...",
  "price": "$79.99",
  "compareAtPrice": "$129.99",
  "discount": "38% OFF",
  "images": ["https://cdn.shopify.com/..."],
  "localImage": "products/premium-wireless-earbuds.jpg",
  "productType": "Electronics",
  "tags": ["brand-color:#FF6B35", "feature:ANC", "bestseller"],
  "variants": [...]
}
```

### Tag conventions (used by render_batch.js)

| Tag format | Effect |
|-----------|--------|
| `brand-color:#FF6B35` | Sets `brandColor` prop on all templates |
| `accent-color:#004E89` | Sets `accentColor` prop on templates that use it |
| `feature:ANC Pro` | Adds to features list (up to 3, for ProductShowcase) |
| `tagline:Sound Without Limits` | Sets tagline for CinematicReveal |
| `bestseller` | Added to feature fallbacks |

---

## Step 2: Ad Rendering

**Script:** `scripts/render_batch.js`
**Trigger:** `npm run render:all` or with flags for targeted renders

### What it does

1. Reads `products.json` (fails if not found — run sync first)
2. For each product × template combination: calls `buildProps()` to map product data to Remotion props
3. Serializes props to a temp JSON file (avoids Windows shell arg length limits)
4. Spawns `npx remotion render {compositionId} {outputFile} --props {propsFile}`
5. Cleans up temp file after render
6. Saves output to `exports/{handle}/{Template}-{format}.mp4`

### Output structure

```
exports/
  premium-wireless-earbuds/
    ProductShowcase-vertical.mp4
    UGCTestimonial-vertical.mp4
    CountdownSale-vertical.mp4
    ComparisonAd-vertical.mp4
    CinematicReveal-vertical.mp4
  another-product/
    ...
```

### Formats

| Flag | Dimensions | Use case |
|------|-----------|----------|
| `vertical` (default) | 1080×1920 | Instagram Reels, Stories, TikTok |
| `square` | 1080×1080 | Facebook Feed, Instagram Feed |
| `landscape` | 1920×1080 | YouTube pre-roll, Facebook video |

### Composition ID resolution

Only `ProductShowcase` has a registered square variant (`ProductShowcase-Square` in `Root.tsx`). All other templates use the base composition ID with `--width`/`--height` overrides.

---

## Step 3: Meta Posting

**Script:** `scripts/meta_ads_engine.py`
**Trigger:** `npm run meta:post` or direct Python invocation

### Authentication

Reads from `.env`: `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`, `META_PAGE_ID`.
Uses Graph API v20.0. Rate limiting: 2-second delay between calls.
Retry policy: 3 attempts, exponential backoff (5s, 10s, 20s) on transient errors.

### Workflow (run in order)

```bash
# 1. Upload video creative
python scripts/meta_ads_engine.py upload \
  --video exports/premium-wireless-earbuds/ProductShowcase-vertical.mp4 \
  --title "Premium Earbuds Ad"

# Returns: video_id and creative_id — save these for next steps

# 2. Create campaign + ad set
python scripts/meta_ads_engine.py create-campaign \
  --name "Earbuds Launch" \
  --budget 50 \
  --objective OUTCOME_SALES

# Returns: campaign_id and adset_id

# 3. Post (link creative to campaign, set live)
python scripts/meta_ads_engine.py post \
  --creative-id {creative_id} \
  --campaign-id {campaign_id}

# 4. Check status
python scripts/meta_ads_engine.py status
```

### Supported objectives

`OUTCOME_AWARENESS` | `OUTCOME_TRAFFIC` | `OUTCOME_ENGAGEMENT` | `OUTCOME_LEADS` | `OUTCOME_APP_PROMOTION` | `OUTCOME_SALES`

---

## File Paths Quick Reference

| File | Created by | Consumed by |
|------|-----------|-------------|
| `products.json` | shopify_sync.js | render_batch.js |
| `public/products/*.jpg` | shopify_sync.js | Remotion compositions (staticFile) |
| `exports/**/*.mp4` | render_batch.js | meta_ads_engine.py |
| `.env` | developer | all three scripts |
