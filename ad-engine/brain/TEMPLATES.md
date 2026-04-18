# TEMPLATES — Ad Composition Reference

> All 5 templates live in `src/compositions/`. Each exports a Zod schema and a React component.
> Timing: 450 frames @ 30fps = 15 seconds. CinematicReveal is 300 frames = 10 seconds.

---

## 1. ProductShowcase

**File:** `src/compositions/ProductShowcase.tsx`
**Font:** Inter (loadFont from @remotion/google-fonts/Inter)
**Sizes:** 1080×1920 (vertical) + 1080×1080 (square — registered as `ProductShowcase-Square`)
**Duration:** 450 frames (15s)
**When to use:** Feature-heavy products with a clear discount. Best for DTC e-commerce.

### Zod Schema

```typescript
z.object({
  productName: z.string(),
  productImage: z.string(),      // path relative to public/ — use staticFile()
  price: z.string(),             // e.g. "$79.99"
  originalPrice: z.string(),     // e.g. "$129.99"
  discount: z.string(),          // e.g. "38% OFF"
  features: z.array(z.string()), // up to 3 items recommended
  ctaText: z.string(),           // e.g. "Shop Now"
  brandColor: z.string(),        // hex — used for glow, badges, CTA gradient
  accentColor: z.string(),       // hex — CTA gradient second color
})
```

### Scene Breakdown

| Scene | Frames | Content | Key Animations |
|-------|--------|---------|----------------|
| Hook | 0–110 | "Still Overpaying?" / "You're Missing Out" | `spring` scale-in, `interpolate` fade |
| Product Hero | 70–230 | Product image + product name + feature badges | `spring` scale from 0, staggered badge slides |
| Price Reveal | 190–370 | Original price → animated strikethrough → sale price → discount badge | `interpolate` strikeWidth 0→100%, `spring` scale for price + badge |
| CTA | 330–450 | Urgency text + arrow bounce + CTA button + social proof | `spring` slide-in, `frame % 20` arrow bounce |

### Key Techniques

- `AnimatedBackground`: dark gradient + brand color layer (fades in at Scene 3) + film grain via `backgroundPosition: ${frame * 7 % 200}px`
- `Particles`: 40 deterministic particles using `Math.sin(seed)` — positioned from `frame` directly, no CSS
- Scene cross-dissolves: `<Sequence>` wrappers with `interpolate(frame, [fadeOut, fadeOut+30], [1, 0])` on the wrapper div
- Square variant: same component, 1080×1080 registered separately — `isVertical` flag adjusts font sizes

---

## 2. UGCTestimonial

**File:** `src/compositions/UGCTestimonial.tsx`
**Font:** Space Grotesk (weights 400, 600, 700 — within 300–700 limit)
**Size:** 1080×1920 only
**Duration:** 450 frames (15s)
**When to use:** Trust-building ads. Best for products with social proof or skeptical audiences.

### Zod Schema

```typescript
z.object({
  hookText: z.string(),               // opening line, e.g. "I was skeptical at first..."
  testimonialLines: z.array(z.string()), // 2–4 lines, each ~60 chars max for readability
  productName: z.string(),
  productImage: z.string(),
  rating: z.number(),                 // 1–5 stars
  reviewerName: z.string(),           // e.g. "Sarah M." or "Verified Buyer"
  ctaText: z.string(),
  brandColor: z.string(),
})
```

### Scene Breakdown

| Scene | Frames | Content | Key Animations |
|-------|--------|---------|----------------|
| Hook | 0–90 | `hookText` word-by-word entrance, "verified purchase" badge | `spring` per word with `staggerDelay = i * 7` |
| Testimonial | 70–220 | Lines appear sequentially, product thumbnail floating top-right | Each line: `spring` at `frame - (i * LINE_DURATION)`, fade-out previous |
| Product + Rating | 220–330 | Large product image center, product name, star rating staggered | `spring` scale from 0.5, each star: `Easing.out(Easing.back(2))` pop |
| CTA | 330–450 | "Don't sleep on this", CTA button, swipe-up arrow | `spring` entrance, `Math.sin(sceneFrame * 0.15)` arrow pulse |

### Key Techniques

- `GrainLayer`: 80 SVG circles per frame, positions computed from `(frame * 137 + i * 1009) % 10000` — changes every frame for film grain feel
- Background color: interpolates from `rgb(14,14,14)` → warm `rgb(26,18,8)` at Scene 3 via per-channel `interpolate`
- Testimonial fade: active line = full opacity, previous lines fade to 0.45
- `Easing.back(2)` on star entrance: slight overshoot gives a satisfying "pop"

---

## 3. CountdownSale

**File:** `src/compositions/CountdownSale.tsx`
**Font:** Inter (weights 400, 700)
**Size:** 1080×1920 only
**Duration:** 450 frames (15s)
**When to use:** Flash sales, BFCM, limited-time offers. Urgency-driven audiences.

### Zod Schema

```typescript
z.object({
  productName: z.string(),
  productImage: z.string(),
  originalPrice: z.string(),
  salePrice: z.string(),
  discount: z.string(),             // e.g. "38% OFF"
  urgencyText: z.string(),          // e.g. "FLASH SALE ENDS IN"
  hoursLeft: z.number(),            // timer start hours
  minutesLeft: z.number(),          // timer start minutes
  ctaText: z.string(),
  brandColor: z.string(),           // dominant — used for timer border glow, CTA
  accentColor: z.string(),          // discount badge color (high contrast — yellows work well)
})
```

### Scene Breakdown

| Scene | Frames | Content | Key Animations |
|-------|--------|---------|----------------|
| Flash burst | 0–76 | Radial burst (`#fff → brandColor → #000`) + "⚡ FLASH SALE ⚡" slam-in | `spring` scale from 3.5→1, `interpolate` scale + opacity on burst |
| Price drop | 60–200 | Product image slides up, original price + animated strikethrough, sale price slams in, discount badge rotates | `spring` from 400px below, `spring` rotate -90→-12deg for badge |
| Countdown timer | 180–350 | Product thumbnail, urgency text, live HH:MM:SS timer with pulsing border | `frame / fps` elapsed math, blink colon at `Math.floor(frame / (fps/2)) % 2`, `Math.sin` border pulse |
| Final CTA | 330–450 | "Don't Wait." (flashing), product name, CTA button, "7 left in stock" | `spring` entrance, `Math.sin((relativeFrame / fps) * Math.PI * 4)` flash |

### Key Techniques

- **Live countdown**: `remaining = totalSecondsAtStart - Math.floor(frame / fps)`. Renders actual counting clock in the video.
- **`TimerDigit` pop**: `spring` on `frame % fps < 3 ? frame % fps : 3` — creates a brief scale pop on each second tick
- `Sequence` for scene isolation — Flash burst and Price drop share frames 60–76 intentionally for continuity

---

## 4. ComparisonAd

**File:** `src/compositions/ComparisonAd.tsx`
**Font:** Inter (loadFont default weights)
**Size:** 1080×1920 only
**Duration:** 450 frames (15s)
**When to use:** Competitive markets where your product wins on specs or price.

### Zod Schema

```typescript
z.object({
  headline: z.string(),             // e.g. "Why Customers Switch"
  ourProduct: z.string(),           // column header left
  competitor: z.string(),           // column header right (can be generic "Brand X")
  ourPrice: z.string(),
  competitorPrice: z.string(),
  comparisons: z.array(z.object({
    feature: z.string(),            // row label
    ours: z.string(),               // our value (green column)
    theirs: z.string(),             // competitor value (red/gray column)
  })),                              // 3–5 rows recommended (more = crowded)
  ctaText: z.string(),
  brandColor: z.string(),           // CTA button + save badge color
})
```

### Scene Breakdown

| Scene | Frames | Content | Key Animations |
|-------|--------|---------|----------------|
| Setup | 0–90 | Headline fades in, vertical divider grows from center down, column labels fade in | `interpolate` dividerHeight 0→height*0.72 over frames 20–70 |
| Feature rows | 70–(70 + rows*45) | Each row slides in from opposite sides | Each row at `enterFrame = 70 + i * 45`, left col slides from -80px, right from +80px |
| Price comparison | rows done → +60 | Price row + "Save $X" badge bounces in | `spring` rotate for save badge, `isPrice` flag enlarges font |
| Verdict + CTA | 360–450 | "The choice is clear." + CTA button overlaid on dimmed content | `bgDim` interpolate 1→0.35, CTA renders in separate `AbsoluteFill` at full opacity |

### Key Techniques

- Color palette constants at top of file: `OUR_COLOR = "#2ECC71"`, `THEIR_COLOR = "#E74C3C"` — do not change these per-instance, they are semantic
- `bgDim`: content layer opacity drops to 0.35 in Scene 4 so CTA reads clearly — CTA is a separate `AbsoluteFill` unaffected by this
- Row count is dynamic — `priceEnterFrame = 70 + comparisons.length * 45` ensures price row always follows feature rows

---

## 5. CinematicReveal

**File:** `src/compositions/CinematicReveal.tsx`
**Font:** Space Grotesk (weight 300, 600, 700 — within 300–700 limit)
**Size:** 1080×1920 only
**Duration:** 300 frames (10s — shorter by design)
**When to use:** Premium or luxury products. Builds desire rather than urgency. Dark aesthetic.

### Zod Schema

```typescript
z.object({
  productName: z.string(),
  productImage: z.string(),
  tagline: z.string(),              // e.g. "Sound Without Limits" — kept short
  price: z.string(),
  brandColor: z.string(),           // very dark works best — e.g. "#1a1a2e"
  accentColor: z.string(),          // glow + sweep color — saturated works well — e.g. "#e94560"
})
```

### Scene Breakdown

| Scene | Frames | Content | Key Animations |
|-------|--------|---------|----------------|
| Sweep | 0–60 | Horizontal sweep line + trailing glow orb crosses left to right | `interpolate` orbX = progress * width, line fades out at frame 60 |
| Product reveal | 45–150 | Product fades + scales from 0.8→1.0, radial glow behind it, 8 light rays rotate | `spring(damping:200, stiffness:80)` — deliberately smooth (no bounce), `frame / (fps * 10) * 360` rotation |
| Text | 130–220 | Product name typewriter char by char, tagline slides up | `Math.floor(interpolate(frame, [TEXT_START, TEXT_START + name.length * 2], [0, name.length]))` |
| Price | 200–300 | Price fades in + translates up, accent underline expands | `interpolate` underlineProgress 0→1 on `UNDERLINE_MAX_WIDTH` |

### Key Techniques

- **Typewriter**: `charsToShow = Math.floor(interpolate(..., [0, name.length]))` — integer floor gives sharp character reveal
- **Cursor blink**: `Math.floor(frame / 15) % 2 === 0 ? 1 : 0` while typing; fades out after typing completes
- **Bokeh particles**: `Math.sin(i * 73.19)` and `Math.cos(i * 47.31)` for deterministic positions, vertical travel wraps via `%`
- **Breathing glow**: `0.18 + Math.sin(frame / 35) * 0.05` — subtle oscillation on product glow after reveal
- Layer architecture: `AbsoluteFill` per layer (background → particles → sweep → product → text → price) — no `<Sequence>`, all layers always rendered, visibility via opacity

---

## Template Selection Guide

| Signal | Recommended Template |
|--------|---------------------|
| Product has 30%+ discount | ProductShowcase or CountdownSale |
| BFCM / flash sale event | CountdownSale |
| Product has strong reviews | UGCTestimonial |
| Competitor comparison angle | ComparisonAd |
| Premium price point ($100+) | CinematicReveal |
| Feature-heavy tech product | ProductShowcase or ComparisonAd |
| Impulse buy / low AOV | CountdownSale |
| Trust deficit / skeptical audience | UGCTestimonial |
