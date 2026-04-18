# AdForge — Shopify Ad Engine

**Turn any Shopify product catalog into high-converting Meta ads. Automatically.**

AdForge pulls your products from Shopify, renders professional video ads using Remotion, and posts directly to Meta — no design tool, no agency, no manual work.

---

## What This Does

```
Shopify Store
     |
     v
[1] SYNC PRODUCTS
     Storefront API → products.json
     (titles, prices, images, variants)
     |
     v
[2] RENDER ADS
     Remotion + 5 templates → MP4 files
     (vertical, square, landscape formats)
     |
     v
[3] POST TO META
     Marketing API → live campaigns
     (targeting, budgets, scheduling)
```

One command to run all three steps. One config file to control everything.

---

## Ad Templates

### ProductShowcase
Highlights your product's key features with a problem-to-solution narrative. Best for products that need explanation. Runs 15 seconds.

### UGCTestimonial
Simulates an authentic customer review with AI voiceover (ElevenLabs) and product imagery. Builds social proof without sourcing real UGC. Runs 15 seconds.

### CountdownSale
Urgency-first format with animated countdown timer, discount callout, and hard deadline. Built for BFCM, flash sales, and limited-time offers. Runs 15 seconds.

### ComparisonAd
Side-by-side feature comparison against the generic alternative. Data-driven proof format. Works best for products with a clear competitive edge. Runs 15 seconds.

### CinematicReveal
Premium mystery-to-reveal format. Soft film grain, dramatic pacing, product reveal on the final third. For luxury or high-ticket items. Runs 10 seconds.

---

## Quick Start

**Prerequisites:** Node.js 18+, ffmpeg, a Shopify store, a Meta Business account.

```bash
# 1. Clone the repo
git clone https://github.com/CC90210/shopify-ad-engine.git
cd shopify-ad-engine

# 2. Install dependencies
npm install

# 3. Configure environment
cp .env.example .env
# Fill in your Shopify, Meta, and ElevenLabs credentials

# 4. Sync products from Shopify
npm run sync

# 5. Render ads for all synced products
npm run render

# 6. Post to Meta
npm run post
```

---

## Usage

### Sync Products

Pulls all active products from your Shopify Storefront API and writes them to `public/products/`.

```bash
npm run sync
# Fetches: title, handle, description, price, compare_at_price, images, variants
# Output: public/products/{handle}.json
```

### Render Ads

Renders video ads for every product in `public/products/`. Defaults to all 5 templates in vertical (9:16) format.

```bash
# Render all products, all templates, vertical format
npm run render

# Render one product
npm run render -- --product=your-product-handle

# Render specific template only
npm run render -- --template=CountdownSale

# Render in square format (1:1)
npm run render -- --format=square
```

Output files are written to `exports/{product-handle}/{template}/{format}.mp4`.

### Post to Meta

Creates ad creatives and campaigns in your Meta Ad Account using the Marketing API.

```bash
# Post all rendered ads
npm run post

# Dry run — validate without posting
npm run post -- --dry-run

# Post specific product
npm run post -- --product=your-product-handle
```

### Generate AI Voiceover

Generates ElevenLabs TTS audio for UGCTestimonial ads before rendering.

```bash
npm run voiceover -- --product=your-product-handle
# Output: public/audio/{product-handle}-voiceover.mp3
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Video rendering | Remotion 4.x | Programmatic video composition in React/TypeScript |
| Language | TypeScript | End-to-end type safety across all pipeline scripts |
| Store data | Shopify Storefront API | Product sync (titles, prices, images) |
| Ad distribution | Meta Marketing API | Campaign creation and creative upload |
| AI voiceover | ElevenLabs TTS | Synthetic UGC audio for testimonial ads |
| Video processing | ffmpeg | Format conversion, compression, watermarking |

---

## Architecture

```
shopify-ad-engine/
├── brain/              # Agent identity and configuration
├── compositions/       # Remotion composition definitions (5 templates)
├── exports/            # Rendered video output (gitignored)
├── public/
│   ├── products/       # Synced product JSON files
│   ├── audio/          # Generated voiceover files
│   ├── avatars/        # UGC avatar images for testimonial template
│   └── fonts/          # Brand fonts
├── scripts/
│   ├── sync.ts         # Shopify product sync
│   ├── render.ts       # Remotion batch renderer
│   ├── post.ts         # Meta Marketing API uploader
│   └── voiceover.ts    # ElevenLabs TTS generator
├── src/
│   ├── types/          # TypeScript interfaces (Product, AdConfig, etc.)
│   ├── utils/          # Shared helpers (shopify, meta, formatting)
│   └── templates/      # Per-template React components
├── templates/          # Ad copy templates (JSON)
├── .env.example        # Environment variable reference
└── package.json
```

Data flow:

```
Shopify API → scripts/sync.ts → public/products/*.json
                                        |
                                        v
                              scripts/render.ts
                                        |
                              compositions/*.tsx (Remotion)
                                        |
                                        v
                              exports/{handle}/{template}.mp4
                                        |
                                        v
                              scripts/post.ts → Meta Marketing API
```

---

## Configuration

Copy `.env.example` to `.env` and fill in each variable.

```bash
# Shopify Storefront API
SHOPIFY_STORE=your-store-name          # e.g. my-brand (without .myshopify.com)
SHOPIFY_ACCESS_TOKEN=                  # Storefront API public access token

# Meta Marketing API
META_ACCESS_TOKEN=                     # Long-lived user or system user token
META_AD_ACCOUNT_ID=act_123456789       # Found in Business Manager
META_PAGE_ID=                          # Facebook Page ID

# ElevenLabs (for AI voiceover on UGCTestimonial)
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=                   # Voice ID from ElevenLabs dashboard

# Rendering
RENDER_CONCURRENCY=2                   # Parallel render threads (raise for faster machines)
DEFAULT_FORMAT=vertical                # vertical | square | landscape
```

**Getting credentials:**
- Shopify token: Admin > Apps > Develop apps > Storefront API
- Meta token: developers.facebook.com > Tools > Graph API Explorer
- ElevenLabs voice ID: elevenlabs.io > Voices > copy ID from any voice

---

## Roadmap

- [ ] Webhook-triggered rendering (new Shopify product → auto-render)
- [ ] A/B testing: auto-generate 3 hook variants per product, rotate in campaigns
- [ ] Dynamic discount overlays tied to Shopify sale events
- [ ] TikTok Ads API integration
- [ ] Client dashboard: white-label portal for OASIS AI clients to review and approve ads
- [ ] Auto-pause underperforming ads based on Meta ROAS threshold

---

## Built by

**OASIS AI Solutions** — AI automation for e-commerce and service businesses.

[oasisai.ca](https://oasisai.ca) | Built by Conaugh McKenna
