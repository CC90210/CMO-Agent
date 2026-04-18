# SKILL: AI Image Generation (Production-Grade)

> Generate agency-quality, psychology-based ad creatives with AI-generated humans, logo compositing, and conversion science for SunBiz Funding MCA campaigns.

---

## Overview
Production-grade ad creative generation using Google Gemini's native image generation + Pillow logo compositing. Every ad includes photorealistic AI-generated humans for trust, SunBiz Funding logo overlay, conversion psychology principles, and MCA compliance guardrails.

## Setup
```bash
pip install google-genai Pillow python-dotenv
```
Add to `.env.agents`:
```
GEMINI_API_KEY=your_api_key_here
```
Place logo at: `media/brand/sunbiz_logo.png`

## Models
| Model | Capability | Use |
|-------|-----------|-----|
| `gemini-2.5-flash-image` | Nano Banana — fast, production-ready | Primary |
| `gemini-2.0-flash-exp` | Legacy experimental | Fallback |
| `imagen-3.0-generate-002` | Standalone Imagen API | Final fallback |

**SDK:** `google-genai` (NOT the deprecated `google-generativeai`)

## Architecture

### Master Prompt System
Every prompt is assembled from 6 layers via `_build_master_prompt()`:

1. **Scene Prompt** — The specific creative direction (human, setting, composition)
2. **Logo Instruction** — SunBiz logo description + placement rules
3. **Color Palette** — Brand colors with hex codes
4. **Visual Psychology** — Z-pattern hierarchy, rule of thirds, contrast, negative space
5. **Render Specs** — 4K quality, studio lighting, depth of field, typography
6. **Compliance** — No "loan" language, no guaranteed approvals, disclaimer text

### Logo Compositing Pipeline
After Gemini generates the image, Pillow overlays the actual SunBiz logo:
```
Gemini generates image → save to disk → Pillow opens image + logo →
scale logo to 13% of image width → paste at top-right with alpha →
save final composited image
```
This ensures pixel-perfect logo placement regardless of what Gemini renders.

## Creative Styles

### Consolidation Ads (5 styles)

| Style | Description | Psychology Trigger |
|-------|-------------|-------------------|
| `hero_human` | Confident business owner with data overlay | Trust + Social Proof |
| `split_screen` | Before/after dramatic transformation | Loss Aversion + Relief |
| `data_dashboard` | Bloomberg-style financial data viz | Authority + Credibility |
| `testimonial_style` | Editorial portrait with quote | Social Proof + Relatability |
| `urgency_relief` | Emotional crossroads metaphor | Urgency + Transformation |

### Growth Capital Ads (3 styles)

| Style | Description | Psychology Trigger |
|-------|-------------|-------------------|
| `ceo_portrait` | Executive in premium workspace | Aspiration + Authority |
| `growth_chart` | 3D growth curve breaking through ceiling | Momentum + Ambition |
| `lifestyle_success` | Owner thriving at their business | Aspirational Social Proof |

### Stories/Reels Vertical (2 styles)

| Style | Description | Psychology Trigger |
|-------|-------------|-------------------|
| `transformation` | Cinematic before/after vertical split | Dramatic Transformation |
| `quick_stat` | Bold stat with human face close-up | Stop-the-Scroll + Shock Value |

## Usage

### Single Ad
```python
from scripts.imagen_generate import generate_consolidation_ad

result = generate_consolidation_ad(
    headline="STOP THE DAILY DRAIN",
    before_daily="$2,100/day across 4 funders",
    after_daily="$850/day — one partner",
    savings="Save $1,250/day",
    cta="See If You Qualify",
    size="1080x1080",
    campaign_name="consolidation_q2",
    style="hero_human",
)
```

### Growth Capital Ad
```python
from scripts.imagen_generate import generate_growth_ad

result = generate_growth_ad(
    headline="SMART CAPITAL FOR GROWING BUSINESSES",
    cta="See Your Options",
    size="1080x1080",
    campaign_name="growth_q2",
    style="ceo_portrait",
)
```

### Stories/Reels Vertical
```python
from scripts.imagen_generate import generate_stories_ad

result = generate_stories_ad(
    headline="DROWNING IN MCA PAYMENTS?",
    style="transformation",
    campaign_name="stories_q2",
)
```

### Full Campaign Suite (All Styles)
```python
from scripts.imagen_generate import generate_campaign_suite

# Generates ALL consolidation styles in feed + portrait sizes, plus Stories
results = generate_campaign_suite("q2_consolidation", "consolidation")

# Generates ALL growth styles in feed + portrait sizes
results = generate_campaign_suite("q2_growth", "growth")
```

### A/B Test Variants
```python
from scripts.imagen_generate import generate_ad_variants

results = generate_ad_variants(
    base_prompt="Your detailed MCA ad prompt...",
    campaign_name="consolidation_test",
    variants=3,  # Generates 3 conceptually distinct variants
    size="1080x1080",
)
```

## Visual Psychology System

### Color Psychology
| Color | Hex | Psychological Effect | Use In Ads |
|-------|-----|---------------------|------------|
| Navy Blue | #001F54 | Trust, stability, authority | Primary backgrounds |
| Burnt Orange | #FF6B35 | Action, urgency, warmth | CTA buttons |
| Emerald Green | #28A745 | Growth, money, success | Savings/approval indicators |
| Gold | #D4A843 | Premium, value, prosperity | Savings numbers, accents |
| White | #FFFFFF | Clarity, transparency | Text on dark backgrounds |

### Human Psychology Triggers
- **Hero Human Presence**: Increases trust 35% in financial ads — always include people
- **Direct Eye Contact**: Builds connection and authority with the viewer
- **Before/After**: Loss aversion (losing $1,250/day) more powerful than gain framing
- **Specific Numbers**: "$1,250/day saved" converts 3x vs "save money"
- **Authority Positioning**: Low camera angle, confident posture, professional setting
- **Social Proof**: Testimonial format with real-looking business owners
- **Urgency**: Speed messaging ("24-48 hours") with genuine not false scarcity

### Visual Composition Rules
- **Z-Pattern**: Eye flow top-left → headline → center visual → bottom CTA
- **Rule of Thirds**: Key focal point at grid intersections
- **20% Negative Space**: Professional breathing room, not cluttered
- **F/2.8 Depth of Field**: Sharp subject, soft background = premium feel
- **Cinematic Color Grade**: Lifted blacks, warm mids, teal shadows

## Prompt Engineering Best Practices

### DO:
- Describe the scene cinematically (lighting, mood, atmosphere)
- Specify exact camera angles and depth of field
- Include specific color hex codes
- Describe human subjects in detail (age, expression, attire, posture)
- Specify text placement, typography style, and hierarchy
- Include lighting direction and quality
- Reference real-world quality benchmarks ("Think American Express ad quality")

### DON'T:
- Use vague prompts ("make a nice ad")
- Skip the human element
- Forget brand colors or logo placement
- Use "loan" language anywhere
- Promise guaranteed approval
- Use red as primary color (signals danger)
- Generate cluttered compositions (>30% text coverage)

## Quality Checklist
- [ ] Human subject looks realistic and professional (no AI artifacts)
- [ ] SunBiz Funding logo visible and properly placed
- [ ] Brand colors match (Navy #001F54, Orange #FF6B35, Green #28A745)
- [ ] All text readable at mobile size (400px width test)
- [ ] Before/after numbers realistic and specific
- [ ] MCA disclaimer included
- [ ] No "loan" language anywhere
- [ ] CTA button prominent and orange
- [ ] Visual hierarchy follows Z-pattern
- [ ] Image meets platform size requirements
- [ ] Emotional tone matches target audience (stress relief for consolidation, ambition for growth)

## Platform Sizes
| Platform | Size | Ratio | Use |
|----------|------|-------|-----|
| Meta Feed | 1080x1080 | 1:1 | Primary placement |
| Meta Feed | 1080x1350 | 4:5 | Optimal feed real estate |
| Meta Stories/Reels | 1080x1920 | 9:16 | Stories and Reels |
| Google Display | 1200x628 | 1.91:1 | Display network |

## Iteration Process
1. Generate all styles for target audience (5 consolidation or 3 growth)
2. Review — pick top 3 performers by visual quality
3. Regenerate winners with prompt refinements
4. Generate all platform sizes from winning prompts
5. Composite logos via Pillow (automatic)
6. Upload to platforms via media-manager agent
7. Launch as A/B test — after 500+ impressions, measure CPQL
8. Scale winners, iterate losers, maintain 10-15 distinct creatives per campaign
