# ad-engine — Maven's Video Ad Pipeline

This directory is a **clone** of the Shopify-Ad-Engine (`C:\Users\User\APPS\shopify-ad-engine`) brought into CMO-Agent so Maven owns the full Remotion + Meta Ads rendering stack directly.

## What This Is
- **Remotion 4.0+** video ad templates (cinematic reveals, UGC, comparisons, countdown sales, product showcases)
- **Meta Ads posting engine** (`scripts/meta_ads_engine.py`)
- **Rendering batch runner** (`scripts/render_batch.js`)
- **5 production templates** in `templates/` — reusable across ANY brand Maven manages (OASIS, PropFlow, Nostalgic, SunBiz, CC personal brand)

## Relationship to Shopify-Ad-Engine
The original Shopify-Ad-Engine (`APPS/shopify-ad-engine`) remains a standalone Shopify-integration app with `shopify_sync.js` tying into the Shopify Storefront/Admin APIs. That's a product specific to Shopify workflows.

Maven's `ad-engine/` is the **multi-brand rendering pipeline** — same Remotion foundation, no Shopify dependency. When Maven needs to render an ad for OASIS AI, PropFlow, etc., it runs from here.

## Evolution Protocol
- **Maven owns this directly.** Evolve templates, add new compositions, tune rendering params as brand needs dictate.
- If Shopify-Ad-Engine adds a useful template, port it here via manual diff (don't two-way-sync — they're divergent products by design).
- `shopify_sync.js` is deliberately excluded — no Shopify dependency in Maven's ad-engine.

## Setup for First Use
```bash
cd ad-engine
npm install
npx remotion studio   # opens Remotion editor on localhost:3000
```

## Why the Clone (not a symlink or submodule)
- **Isolation**: template changes for OASIS shouldn't risk breaking Shopify integrations
- **Maven sovereignty**: CMO-Agent repo is self-contained; no external runtime dependency
- **Diff-friendly**: we can see clearly when Maven's pipeline diverges from Shopify's
