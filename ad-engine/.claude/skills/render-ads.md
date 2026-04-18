---
description: "Render Shopify product ads using Remotion. Use when CC wants to create ad videos, preview templates, or batch render products."
---
# Ad Rendering Pipeline

## Preview
```bash
npm run studio    # Opens Remotion studio at localhost:3000
```

## Batch Render
```bash
npm run render:all                              # All products × all templates
node scripts/render_batch.js --template ProductShowcase  # Single template
node scripts/render_batch.js --format square --limit 5   # Square format, 5 products
```

## Templates (5 compositions)
- **ProductShowcase** — Hero product with feature callouts
- **UGCTestimonial** — User-generated content style
- **CountdownSale** — Urgency-driven with countdown timer
- **ComparisonAd** — Before/after or vs. competitor
- **CinematicReveal** — Premium reveal with 3D effects

## Output Formats
- Portrait (1080x1920) — Instagram Stories/Reels, TikTok
- Square (1080x1080) — Instagram Feed, Facebook
- Landscape (1920x1080) — YouTube, LinkedIn

Check brain/TEMPLATES.md for full composition schemas.