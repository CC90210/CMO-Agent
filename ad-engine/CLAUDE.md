# CLAUDE.md — Shopify Ad Engine

> AdForge V1.0 — AI-powered Shopify ad creation. Three steps: sync → render → post.

## Project Identity

- **Name:** Shopify Ad Engine (AdForge)
- **Owner:** CC (Conaugh McKenna), OASIS AI Solutions
- **Purpose:** Turn any Shopify product catalog into live Meta ad campaigns, fully automated
- **Platform:** Windows 11, bash shell

## Stack

| Layer | Technology |
|-------|-----------|
| Video rendering | Remotion 4.0.436, React 19 |
| Language | TypeScript 5.9, strict mode |
| 3D effects | Three.js + @react-three/fiber |
| Validation | Zod 4 (co-located schemas) |
| Meta posting | Python 3, requests (Graph API v20.0) |
| Product sync | Node.js, Shopify Storefront API (GraphQL) |

## Commands

```bash
npm run studio          # Preview compositions at localhost:3000
npm run build           # TypeScript check — run before every commit
npm run render:all      # Batch render all products × all templates
npm run shopify:sync    # Fetch products from Shopify → products.json + public/products/
npm run meta:post       # Post to Meta (upload | create-campaign | post | status)

# Targeted renders
node scripts/render_batch.js --template ProductShowcase
node scripts/render_batch.js --format square --limit 5 --parallel 2

# Meta workflow
python scripts/meta_ads_engine.py upload --video exports/product/ad.mp4
python scripts/meta_ads_engine.py create-campaign --name "Launch" --budget 50
python scripts/meta_ads_engine.py post --creative-id 123 --campaign-id 456
python scripts/meta_ads_engine.py status
```

## Pipeline

```
Shopify Storefront API
        ↓  npm run shopify:sync
  products.json + public/products/*.{jpg,png}
        ↓  npm run render:all
  exports/{product-handle}/{Template}-{format}.mp4
        ↓  python scripts/meta_ads_engine.py
  Live Meta ad campaign
```

See `brain/PIPELINE.md` for full data flow details.

## Composition Architecture

Every composition lives in `src/compositions/` and follows this structure:

1. **Font loading at module scope** — `loadFont()` called outside any component
2. **Zod schema exported** — e.g. `export const ProductShowcaseSchema = z.object({...})`
3. **Type derived from schema** — `type Props = z.infer<typeof Schema>`
4. **4-scene structure** — Hook → Product → Value prop → CTA, using `<Sequence>` for timing
5. **Registered in Root.tsx** — `<Composition id="..." component={...} schema={...} />`
6. **Added to render_batch.js** — `buildProps()` switch case + `ALL_TEMPLATES` array

See `brain/TEMPLATES.md` for schema fields and scene breakdowns per template.

## Remotion Rules (Critical)

**NEVER violate these — they cause silent rendering failures or black frames.**

- ALL animations via `useCurrentFrame()` + `spring()` + `interpolate()` only
- NO CSS `transition`, `animation`, `@keyframes`, or `setTimeout`
- `loadFont()` MUST be called at module scope, never inside components
- Space Grotesk supports weights 300–700 only (not 800/900) — use Inter for heavy weights
- `staticFile()` for any asset in `public/` — never raw relative paths
- `<Img>` from remotion, not HTML `<img>`, for assets in compositions
- Particle positions must use deterministic seeded math — no `Math.random()` in render
- Inter supports 100–900; Space Grotesk supports 300–700

See `brain/REMOTION_RULES.md` for the full rules reference.

## File Conventions

```
src/compositions/    # One file per template — schema + component co-located
src/Root.tsx         # Register compositions here — no logic, only <Composition> tags
public/products/     # Downloaded Shopify images (auto-populated by sync script)
exports/             # Rendered MP4s — gitignored, auto-created by render_batch.js
products.json        # Synced Shopify catalog — gitignored
scripts/             # shopify_sync.js, render_batch.js, meta_ads_engine.py
brain/               # Architecture docs for this AI session
```

## Credentials

All credentials in `.env` (copy from `.env.example`). Never hardcode.

```
SHOPIFY_STORE          — store subdomain (e.g. "mystore" not "mystore.myshopify.com")
SHOPIFY_ACCESS_TOKEN   — Storefront API public access token
META_ACCESS_TOKEN      — Meta Marketing API user/system token
META_AD_ACCOUNT_ID     — act_XXXXXXXXX format
META_PAGE_ID           — Facebook Page linked to the ad account
ELEVENLABS_API_KEY     — for UGC voiceover (optional)
ELEVENLABS_VOICE_ID    — ElevenLabs voice for testimonials (optional)
RENDER_CONCURRENCY     — parallel Remotion renders (default: 2)
```

## Adding a New Template

1. Create `src/compositions/MyTemplate.tsx` with schema + component
2. Export `MyTemplateSchema` and `MyTemplate` from that file
3. Import both in `src/Root.tsx`, add `<Composition id="MyTemplate" ... />`
4. Add `"MyTemplate"` to `ALL_TEMPLATES` in `scripts/render_batch.js`
5. Add a `case "MyTemplate":` block in `buildProps()` in `render_batch.js`
6. Run `npm run build` to verify zero TypeScript errors
7. Test in studio: `npm run studio`
