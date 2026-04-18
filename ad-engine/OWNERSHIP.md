# ad-engine — Maven's Video Ad + Ecommerce Connector Pipeline

This directory is a **clone** of the Shopify-Ad-Engine (`C:\Users\User\APPS\shopify-ad-engine`) brought into CMO-Agent so Maven owns the full Remotion + Meta Ads + Shopify rendering stack directly.

## What This Is

Maven's full marketing execution toolkit:

| Capability | File | What it does |
|-----------|------|--------------|
| **Remotion studio** | `src/`, `templates/` | 5 production video ad templates (cinematic-reveal, comparison, countdown-sale, product-showcase, ugc-testimonial) |
| **Meta Ads API** | `scripts/meta_ads_engine.py` | Post videos to Facebook / Instagram as ads via Meta Marketing API |
| **Shopify Storefront API** | `scripts/shopify_sync.js` | Pull products + images from any Shopify store → `products.json` for use in ad templates |
| **Batch render** | `scripts/render_batch.js` | Render multiple ads in parallel |

## Why Maven Has This (Scope)

Maven manages marketing for **multiple brands** in CC's portfolio:

- **OASIS AI** — CC's B2B AI agency (primary revenue)
- **CC personal brand (Conaugh McKenna)** — top-of-funnel content engine
- **PropFlow** — real estate SaaS (launch campaign pending)
- **Nostalgic Requests** — DJ/music SaaS
- **SunBiz Funding** — legacy client, compliance-sensitive

Any of these brands could run Shopify (Nostalgic already does; OASIS and PropFlow might add storefronts). **Maven needs direct Shopify + Meta connectivity** without having to reach across to another codebase.

The original Shopify-Ad-Engine (`APPS/shopify-ad-engine`) remains a standalone sandbox for Shopify-specific experiments. Maven's `ad-engine/` is the multi-brand production pipeline.

## Setup for First Use

```bash
cd ad-engine
npm install
```

Then add to `.env` (in the ad-engine directory, or use Maven's root `.env.agents`):

```
# Shopify (if using)
SHOPIFY_STORE=your-store-handle
SHOPIFY_ACCESS_TOKEN=your-storefront-api-token

# Meta Ads (if using)
META_APP_ID=...
META_ACCESS_TOKEN=...
META_AD_ACCOUNT_ID=...
```

## Running

```bash
# Preview + edit templates
npx remotion studio         # opens localhost:3000 in browser

# Pull Shopify products into products.json
npm run shopify:sync        # or: npm run shopify:sync -- --limit 10

# Render a single composition
npx remotion render <composition-id>

# Batch render all templates
npm run render:all

# Post a rendered video as a Meta ad
npm run meta:post
```

## Evolution Protocol

- **Maven owns this directly.** Evolve templates, tune rendering params, add new compositions as brands need.
- Shopify-Ad-Engine (`APPS/shopify-ad-engine`) remains a separate standalone app. If it adds a useful template, port it here via manual diff — no two-way sync.
- New ad templates should be added under `templates/{name}/`.

## Why the Clone (not a symlink or submodule)

- **Isolation**: template tweaks for OASIS don't risk breaking the standalone Shopify engine
- **Maven sovereignty**: CMO-Agent is self-contained; no external runtime dependency
- **Diff-friendly**: Maven's pipeline can diverge from the original over time
