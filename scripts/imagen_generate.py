"""
SunBiz Funding — Production-Grade AI Ad Creative Generator
===========================================================
Gemini Imagen (Nano Banana) + Pillow Logo Compositing

Generates agency-quality, psychology-based ad creatives with:
- Photorealistic AI-generated humans for trust & connection
- SunBiz Funding logo composited on every ad (Pillow overlay)
- Conversion psychology: visual hierarchy, color theory, urgency triggers
- MCA compliance baked into every prompt (no "loan" language)

Requirements:
    pip install google-genai Pillow python-dotenv

SDK: google-genai (NOT the deprecated google-generativeai)

Usage:
    from scripts.imagen_generate import generate_consolidation_ad, generate_growth_ad
    result = generate_consolidation_ad(style="hero_human")
"""

import os
import re
import base64
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

# Load credentials
load_dotenv(Path(__file__).parent.parent / ".env.agents")

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

# Model priority: best image gen first
MODELS = [
    "gemini-2.5-flash-image",      # Nano Banana — fast, production-ready
    "gemini-2.0-flash-exp",         # Legacy experimental fallback
]

PROJECT_ROOT = Path(__file__).parent.parent
REGISTRY_PATH = PROJECT_ROOT / "media" / "ASSET_REGISTRY.md"
LOGO_PATH = PROJECT_ROOT / "media" / "brand" / "sunbiz_logo.png"

# Matches a registry table row: | 001 | ... |
_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|")

# ---------------------------------------------------------------------------
# BRAND SYSTEM — Embedded in every prompt for consistency
# ---------------------------------------------------------------------------

BRAND = {
    "name": "SunBiz Funding",
    "tagline": "Your Partner in Financial Health",
    "colors": {
        "primary": "deep navy blue (#001F54)",
        "cta": "warm burnt orange (#FF6B35)",
        "success": "emerald green (#28A745)",
        "text_light": "crisp white (#FFFFFF)",
        "text_dark": "charcoal (#333333)",
        "gold_accent": "warm gold (#D4A843)",
    },
    "logo_description": (
        "The SunBiz Funding logo: a golden hand cradling a money bag with a dollar sign, "
        "with a green leaf accent beneath, surrounded by elegant radiating sunburst lines. "
        "Below reads 'SUNBIZ FUNDING' in clean dark serif lettering."
    ),
}

# ---------------------------------------------------------------------------
# PSYCHOLOGY-BASED PROMPT ENGINEERING SYSTEM
# ---------------------------------------------------------------------------

# Core visual psychology principles injected into every prompt
VISUAL_PSYCHOLOGY = """
VISUAL PSYCHOLOGY RULES (apply to entire composition):
- Visual hierarchy: Eye moves top-left → headline → center visual → bottom CTA (Z-pattern)
- Rule of thirds: Key focal point at intersection of thirds grid
- Color psychology: Navy blue = trust/stability, Orange = action/urgency, Green = growth/money
- Contrast ratio: Text must be highly readable against background (WCAG AAA level contrast)
- Negative space: At least 20% whitespace to convey professionalism and breathing room
- Focal anchoring: One dominant visual element draws the eye before any text
- Social proof cue: Human presence increases trust by 35% in financial advertising
"""

# Quality and rendering specifications for Gemini
RENDER_SPECS = """
RENDERING SPECIFICATIONS:
- Photorealistic quality, 4K ultra-sharp detail
- Professional studio lighting with soft rim highlights
- Shallow depth of field on background elements (bokeh)
- Color-graded with cinematic teal-and-orange palette
- Typography: Bold modern sans-serif (like Montserrat or Inter), clean kerning
- All text must be crisp, legible, and properly spelled
- No AI artifacts, no distorted hands, no warped text
- Magazine advertisement production quality
"""

# Logo placement instruction for every prompt
LOGO_INSTRUCTION = f"""
BRANDING (MANDATORY):
- {BRAND['logo_description']}
- Place the SunBiz Funding logo prominently in the top-right corner of the ad
- Logo size: approximately 12-15% of image width
- White glow or subtle shadow behind logo for visibility on any background
- "SunBiz Funding" text must appear clearly in the composition
"""

# MCA compliance rules
COMPLIANCE = """
COMPLIANCE (NON-NEGOTIABLE):
- NEVER use the word "loan" — these are "advances," "funding," or "capital"
- NEVER promise "guaranteed approval" — use "See if you qualify"
- Include small disclaimer text: "Merchant cash advance products. Terms vary by qualification."
- No misleading financial imagery or fake statistics
- No discriminatory imagery or messaging
"""


def _build_master_prompt(scene_prompt: str, size: str = "1080x1080") -> str:
    """
    Assemble the complete production prompt by combining:
    1. Scene-specific creative direction
    2. Brand identity system
    3. Visual psychology rules
    4. Rendering specifications
    5. Logo placement
    6. Compliance guardrails
    """
    return f"""{scene_prompt}

{LOGO_INSTRUCTION}

COLOR PALETTE:
- Primary background: {BRAND['colors']['primary']}
- CTA buttons/accents: {BRAND['colors']['cta']}
- Success/savings indicators: {BRAND['colors']['success']}
- Text on dark: {BRAND['colors']['text_light']}
- Gold accents: {BRAND['colors']['gold_accent']}

{VISUAL_PSYCHOLOGY}

{RENDER_SPECS}

{COMPLIANCE}

IMAGE FORMAT: {size} pixels, optimized for social media advertising.
"""


# ---------------------------------------------------------------------------
# ASSET REGISTRY
# ---------------------------------------------------------------------------

def register_asset(
    file_path: str,
    campaign_name: str,
    creative_type: str,
    angle: str,
    size: str,
    model: str,
) -> str:
    """Append a new DRAFT entry to media/ASSET_REGISTRY.md."""
    registry_text = REGISTRY_PATH.read_text(encoding="utf-8") if REGISTRY_PATH.exists() else ""

    existing_ids = [int(m.group(1)) for m in _ROW_RE.finditer(registry_text)]
    next_id = (max(existing_ids) + 1) if existing_ids else 1
    asset_id = str(next_id).zfill(3)

    try:
        relative_path = Path(file_path).resolve().relative_to(PROJECT_ROOT.resolve())
        display_path = str(relative_path).replace("\\", "/")
    except ValueError:
        display_path = str(file_path).replace("\\", "/")

    created = date.today().isoformat()
    new_row = (
        f"| {asset_id} | {display_path} | {campaign_name} | {creative_type} "
        f"| {angle} | {size} | {model} | DRAFT | {created} | — |"
    )

    legend_marker = "\n## Status Legend"
    if legend_marker in registry_text:
        updated_text = registry_text.replace(legend_marker, f"\n{new_row}{legend_marker}")
    else:
        updated_text = registry_text.rstrip("\n") + f"\n{new_row}\n"

    REGISTRY_PATH.write_text(updated_text, encoding="utf-8")
    return asset_id


# ---------------------------------------------------------------------------
# LOGO COMPOSITING (Pillow overlay)
# ---------------------------------------------------------------------------

def composite_logo(image_path: str, position: str = "top-right", scale: float = 0.13) -> str:
    """
    Overlay the SunBiz Funding logo onto a generated ad image.

    Args:
        image_path: Path to the generated ad image
        position: Logo placement — 'top-right', 'top-left', 'bottom-right', 'bottom-left'
        scale: Logo width as fraction of image width (default 13%)

    Returns:
        Path to the composited image (overwrites original)
    """
    if not LOGO_PATH.exists():
        return image_path  # Skip if no logo file available

    try:
        from PIL import Image

        ad = Image.open(image_path).convert("RGBA")
        logo = Image.open(str(LOGO_PATH)).convert("RGBA")

        # Scale logo proportionally
        logo_width = int(ad.width * scale)
        logo_height = int(logo.height * (logo_width / logo.width))
        logo = logo.resize((logo_width, logo_height), Image.LANCZOS)

        # Calculate position with padding
        pad = int(ad.width * 0.03)  # 3% padding from edge
        positions = {
            "top-right": (ad.width - logo_width - pad, pad),
            "top-left": (pad, pad),
            "bottom-right": (ad.width - logo_width - pad, ad.height - logo_height - pad),
            "bottom-left": (pad, ad.height - logo_height - pad),
        }
        pos = positions.get(position, positions["top-right"])

        # Composite with alpha
        ad.paste(logo, pos, logo)

        # Save back (as PNG to preserve quality)
        ad.save(image_path, "PNG")
        return image_path
    except Exception:
        return image_path  # Graceful fallback — ad still usable without logo


# ---------------------------------------------------------------------------
# GEMINI API CLIENT
# ---------------------------------------------------------------------------

def get_client():
    """Initialize Gemini API client using google-genai SDK."""
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found in .env.agents. "
            "Get one from https://aistudio.google.com/apikey"
        )
    return genai.Client(api_key=api_key)


def _size_to_aspect_ratio(size):
    """Convert pixel dimensions string to Gemini aspect ratio."""
    width, height = map(int, size.split("x"))
    ratio = width / height
    ratios = [
        (1.0, "1:1"), (1.778, "16:9"), (0.5625, "9:16"),
        (0.8, "4:5"), (1.25, "5:4"), (0.75, "3:4"),
        (1.333, "4:3"), (0.667, "2:3"), (1.5, "3:2"),
    ]
    return min(ratios, key=lambda r: abs(r[0] - ratio))[1]


def _size_to_resolution(size):
    """Pick appropriate resolution tier based on pixel dimensions."""
    max_dim = max(map(int, size.split("x")))
    if max_dim <= 512:
        return "0.5K"
    elif max_dim <= 1080:
        return "1K"
    elif max_dim <= 2048:
        return "2K"
    return "4K"


# ---------------------------------------------------------------------------
# CORE GENERATION ENGINE
# ---------------------------------------------------------------------------

def generate_ad_image(
    prompt,
    output_path,
    size="1080x1080",
    campaign_name: str = "",
    creative_type: str = "Static Image",
    angle: str = "",
    apply_logo: bool = True,
    logo_position: str = "top-right",
):
    """
    Generate a single ad image using Gemini native image generation.

    The prompt is automatically enhanced with brand identity, visual psychology,
    rendering specs, logo placement, and compliance rules via _build_master_prompt().

    Args:
        prompt: Scene-specific creative direction
        output_path: Where to save the generated image
        size: Image dimensions (1080x1080, 1080x1920, 1200x628)
        campaign_name: For asset registry tracking
        creative_type: Asset type label
        angle: Creative angle description
        apply_logo: Whether to composite the logo via Pillow (default True)
        logo_position: Where to place the logo overlay

    Returns:
        dict with path, size, model, status, and asset_id
    """
    from google.genai import types

    def _success(path: str, model: str) -> dict:
        result = {"path": path, "size": size, "model": model, "status": "SUCCESS"}
        if campaign_name:
            asset_id = register_asset(
                file_path=path,
                campaign_name=campaign_name,
                creative_type=creative_type,
                angle=angle or Path(path).stem,
                size=size,
                model=model,
            )
            result["asset_id"] = asset_id
        return result

    client = get_client()
    aspect_ratio = _size_to_aspect_ratio(size)
    resolution = _size_to_resolution(size)

    # Build the full production prompt
    master_prompt = _build_master_prompt(prompt, size)

    for model_name in MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=master_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size=resolution,
                    ),
                ),
            )

            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)

            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data is not None:
                    image_data = part.inline_data.data
                    if isinstance(image_data, str):
                        image_data = base64.b64decode(image_data)

                    with open(output_path, "wb") as f:
                        f.write(image_data)

                    # Composite logo overlay
                    if apply_logo:
                        composite_logo(str(output_path), position=logo_position)

                    return _success(str(output_path), model_name)

        except Exception:
            continue

    # Final fallback: Imagen standalone
    try:
        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=master_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
            ),
        )
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        response.generated_images[0].image.save(output_path)
        if apply_logo:
            composite_logo(str(output_path), position=logo_position)
        return _success(str(output_path), "imagen-3.0-generate-002")
    except Exception as e:
        return {"path": None, "error": f"All models failed. Last: {e}", "status": "FAILED"}


# ---------------------------------------------------------------------------
# AD VARIANT GENERATOR
# ---------------------------------------------------------------------------

def generate_ad_variants(base_prompt, campaign_name, variants=3, size="1080x1080"):
    """Generate multiple conceptually distinct ad variants for A/B testing."""
    results = []
    output_dir = PROJECT_ROOT / "media" / "exports" / campaign_name

    variant_angles = [
        "Focus on emotional relief — the feeling of financial weight being lifted. Warm, hopeful lighting.",
        "Focus on analytical credibility — data visualization, specific numbers, clean charts. Cool, professional.",
        "Focus on human connection — business owner looking confident, eye contact with viewer. Natural warmth.",
    ]

    for i in range(1, variants + 1):
        output_path = output_dir / f"ad_v{i}_{size.replace('x', '_')}.png"
        angle = variant_angles[i - 1] if i <= len(variant_angles) else f"Unique creative direction #{i}."

        variant_prompt = f"{base_prompt}\n\nCREATIVE DIRECTION FOR THIS VARIANT:\n{angle}"

        result = generate_ad_image(
            prompt=variant_prompt,
            output_path=str(output_path),
            size=size,
            campaign_name=campaign_name,
            angle=f"Variant {i}",
        )
        result["variant"] = i
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# CONSOLIDATION AD TEMPLATES (Psychology-Based, Agency-Quality)
# ---------------------------------------------------------------------------

CONSOLIDATION_PROMPTS = {
    "hero_human": """
SCENE: Cinematic advertisement photograph for a premium financial services company.

SUBJECT: A confident, professional business owner (age 35-50) in their real workspace —
a clean modern office, retail store, or small warehouse. They're looking directly at the
camera with a calm, relieved expression — the look of someone who just solved a major
financial problem. Natural, authentic body language — arms relaxed, slight genuine smile.
Professional but approachable attire (button-down shirt, no tie). Sharp focus on the person,
background elements slightly soft (f/2.8 depth of field).

OVERLAY TEXT (crisp, modern sans-serif typography):
- Top banner: "{headline}" in bold white, large font with subtle text shadow
- Middle floating card (semi-transparent navy panel with rounded corners):
  "BEFORE: {before_daily}" in red-tinted text
  "AFTER: {after_daily}" in green text
  "{savings}" in large bold gold (#D4A843) numbers
- Bottom: Warm orange (#FF6B35) CTA button with rounded corners: "{cta}"
- Small footer disclaimer in white 8pt text: "Merchant cash advance products. Terms vary."

LIGHTING: Golden hour warm side-lighting from the left, soft fill from right.
Professional editorial photography quality. Slight cinematic color grade —
lifted blacks, warm mid-tones, teal shadows.

MOOD: Relief, confidence, financial empowerment. This person has regained control.
""",

    "split_screen": """
SCENE: High-end split-screen comparison advertisement — magazine print quality.

LEFT HALF (labeled "BEFORE" at top in bold red):
- Moody, cool-toned color grade (desaturated, slightly blue/gray)
- A stressed business owner at a cluttered desk, head in hands or looking overwhelmed
- Multiple payment notification overlays floating around them (red warning indicators)
- Text overlay: "{before_daily}" in red
- Stack of 4 payment cards/bills scattered on desk
- Dramatic shadows, stressful atmosphere

RIGHT HALF (labeled "AFTER" at top in bold emerald green):
- Warm, golden-toned color grade (saturated, warm and inviting)
- SAME business owner now relaxed, leaning back in chair with a genuine smile
- Clean organized desk, single tablet showing a simple dashboard
- Text overlay: "{after_daily}" in green
- ONE clean payment card
- Bright, airy, hopeful atmosphere

CENTER DIVIDER: Bold diagonal line separating the two halves with "{savings}" in large
gold text on a navy pill/badge.

BOTTOM: Full-width navy bar with headline "{headline}" in white and orange CTA button "{cta}".

PRODUCTION: Ultra-high resolution, advertising agency quality. Perfect skin tones,
professional retouching. Think American Express or Chase ad quality.
""",

    "data_dashboard": """
SCENE: Premium financial data visualization advertisement — Bloomberg/fintech aesthetic.

BACKGROUND: Deep navy blue (#001F54) gradient, subtle geometric pattern overlay
(thin lines creating a grid/mesh effect at 10% opacity for depth and sophistication).

MAIN VISUAL: A photorealistic 3D-rendered glass dashboard panel floating at a slight angle,
showing a clean before/after payment comparison:
- LEFT column (red gradient glow): "4 Funders" with 4 bar chart elements, labeled "{before_daily}"
- RIGHT column (green gradient glow): "1 Funder" with 1 tall bar, labeled "{after_daily}"
- Animated-looking arrow pointing from left to right (transformation visual)
- Large glowing number in gold: "{savings}"

HUMAN ELEMENT: In the bottom-left quadrant, a professional business person (sharp suit,
confident posture) pointing toward or interacting with the data dashboard — like a financial
advisor presenting results. Viewed from a slight low angle for authority.

HEADLINE: "{headline}" in bold white at the top, with subtle glow effect.
CTA: Large warm orange button at bottom center: "{cta}" — 3D raised button effect.

MOOD: Sophisticated, data-driven, authoritative. Like a Bloomberg terminal meets
premium financial advisory firm. This company has the technology and expertise
to solve your problem.
""",

    "testimonial_style": """
SCENE: Social proof testimonial advertisement — editorial portrait style.

SUBJECT: A real-looking business owner (age 40-55, could be a restaurant owner, contractor,
or small manufacturer) photographed in a warm, natural environment — their actual business
setting. They're smiling genuinely, relaxed posture, looking slightly off-camera as if
telling their story to someone just out of frame. Candid editorial portrait feel.

BACKGROUND: Their actual business — visible signage, equipment, or products (blurred slightly).
Warm natural light streaming in from windows.

OVERLAY DESIGN:
- Large quotation marks (gold, stylized) framing the top
- Quote text in clean white serif font: "I went from {before_daily} to {after_daily}.
  SunBiz gave me my business back."
- Attribution line: "— Business Owner, [Industry]" in smaller italic white
- Below the quote: A semi-transparent navy panel showing:
  "{savings}" in large gold numerals
  "in daily payment reduction" in white below
- Bottom: Orange CTA button: "{cta}"

PHOTOGRAPHY STYLE: Natural light editorial portrait. Warm color temperature.
Shallow depth of field (f/2.0). Authentic, not staged. Think small business
documentary photography meets premium ad campaign.

MOOD: Trust, relatability, genuine success story. The viewer sees themselves in this person.
""",

    "urgency_relief": """
SCENE: Powerful emotional transformation advertisement — cinematic quality.

COMPOSITION: Dynamic single scene with strong visual metaphor.

MAIN IMAGE: A business owner standing at a crossroads — literally at a fork in a path
or hallway. Behind them (top of image): dark, stormy, chaotic — stacks of papers,
red payment alerts, multiple debt symbols swirling in dramatic clouds.
Ahead of them (bottom of image): clear path leading to a bright, golden horizon —
clean desk, single green checkmark, organized finances.

The person is mid-stride, walking toward the bright side. Camera angle: slightly
from behind and above, showing both the chaos they're leaving and the clarity ahead.

TEXT LAYOUT:
- Top (over the dark section): "{before_daily}" in stressed red text
- Center (at the turning point): "{headline}" in massive bold white with glow
- Bottom (over the bright section): "{after_daily}" in confident green
- Very bottom: Navy bar with gold text "{savings}" and orange CTA: "{cta}"

LIGHTING: Dramatic split lighting — cool blue/gray on the "before" side,
warm golden on the "after" side. Cinematic lens flare at the horizon point.

MOOD: Powerful transformation moment. This is the turning point. Take action NOW.
""",
}


GROWTH_PROMPTS = {
    "ceo_portrait": """
SCENE: Premium business funding advertisement — executive portrait style.

SUBJECT: A successful, polished business owner (age 30-45) in a modern, upscale workspace.
They're sitting at a clean glass desk or standing by a floor-to-ceiling window overlooking
a city. Confident posture, direct eye contact with camera, slight knowing smile — the look
of someone whose business is thriving. Professional attire — crisp blazer, modern cut.

SETTING: Bright, airy modern office. Natural light flooding in. Plants, clean lines,
minimalist decor. Conveys success without being ostentatious.

OVERLAY TEXT (clean, modern typography):
- Headline at top: "{headline}" in bold navy blue
- Three floating glass cards below the person (horizontal row):
  Card 1: "Funded in 24-48 Hours" (clock icon)
  Card 2: "No Equity Required" (shield icon)
  Card 3: "Revenue-Based" (chart-up icon)
- Each card has a subtle gold top border accent
- Subtext: "Revenue $40K+/month? You qualify for our best terms." in navy
- Bottom: Large orange CTA button: "{cta}"

PHOTOGRAPHY: Bright, aspirational, premium. Color grade: clean whites, navy blue
shadows, warm skin tones. Think Goldman Sachs or American Express business card ad.

MOOD: Ambition, growth, premium service. This is for winners who want the best terms.
""",

    "growth_chart": """
SCENE: Data-driven growth capital advertisement — fintech/startup aesthetic.

BACKGROUND: Clean white with subtle light gray geometric grid pattern.
Premium, minimalist, modern.

MAIN VISUAL: A large, beautiful 3D-rendered growth chart/graph taking up the center —
an upward-curving revenue line in emerald green with a glowing gold accent where
it reaches its peak. Below the chart, subtle data points and metrics that convey
sophistication. The chart line literally seems to be breaking through a glass ceiling
or barrier at the top — visual metaphor for breaking through to the next level.

HUMAN ELEMENT: A confident business professional (age 30-40) in the lower-left,
slightly overlapping the chart, looking upward toward the growth line with an
expression of ambitious determination. Professional casual attire.

TEXT:
- "{headline}" in bold navy blue at the top
- Key stats in floating navy pills: "24-48hr Funding" | "No Equity" | "Flexible Terms"
- Subtext: "Revenue $40K+/month? Let's grow together." in charcoal
- Orange CTA button: "{cta}"

MOOD: Ambition, momentum, upward trajectory. For businesses that are already succeeding
and want rocket fuel.
""",

    "lifestyle_success": """
SCENE: Aspirational business lifestyle advertisement — editorial magazine quality.

SUBJECT: A thriving business owner captured in action at their successful business —
a busy restaurant with customers, a warehouse with products being shipped, a tech
office with their team collaborating. The owner is in the foreground, reviewing
something on a tablet with a satisfied expression. Their business is humming
behind them — proof of success.

BACKGROUND: The actual thriving business environment, slightly blurred (bokeh),
with warm ambient lighting. Activity and energy without chaos.

OVERLAY (minimalist, premium):
- Semi-transparent white panel on the right third of the image
- Navy text: "{headline}"
- Three benefit lines with green checkmarks:
  ✓ "Fast decisions, not bank bureaucracy"
  ✓ "Capital that grows with your revenue"
  ✓ "One partner, transparent terms"
- Orange CTA button: "{cta}"
- Gold accent line separating headline from benefits

PHOTOGRAPHY: Bright, warm, editorial. Slightly warm color temperature.
Authentic business environment — not a studio set. Real business energy.

MOOD: "This could be you." Aspirational but believable. The funding made
this success possible — now it's your turn.
""",
}


# ---------------------------------------------------------------------------
# CONSOLIDATION AD GENERATOR
# ---------------------------------------------------------------------------

def generate_consolidation_ad(
    headline="STOP THE DAILY DRAIN",
    before_daily="$2,100/day across 4 funders",
    after_daily="$850/day — one partner",
    savings="Save $1,250/day",
    cta="See If You Qualify",
    size="1080x1080",
    campaign_name="consolidation",
    style="hero_human",
):
    """
    Generate a production-grade MCA consolidation ad for SunBiz Funding.

    Styles:
        hero_human      — Confident business owner with data overlay (highest trust)
        split_screen    — Before/after dramatic transformation
        data_dashboard  — Bloomberg-style data visualization
        testimonial_style — Social proof editorial portrait
        urgency_relief  — Emotional transformation metaphor
    """
    template = CONSOLIDATION_PROMPTS.get(style, CONSOLIDATION_PROMPTS["hero_human"])
    prompt = template.format(
        headline=headline,
        before_daily=before_daily,
        after_daily=after_daily,
        savings=savings,
        cta=cta,
    )

    output_dir = PROJECT_ROOT / "media" / "exports" / campaign_name
    output_path = output_dir / f"consolidation_{style}_{size.replace('x', '_')}.png"

    return generate_ad_image(
        prompt=prompt,
        output_path=str(output_path),
        size=size,
        campaign_name=campaign_name,
        creative_type="Static Image",
        angle=f"Consolidation - {style.replace('_', ' ').title()}",
    )


# ---------------------------------------------------------------------------
# GROWTH CAPITAL AD GENERATOR
# ---------------------------------------------------------------------------

def generate_growth_ad(
    headline="SMART CAPITAL FOR GROWING BUSINESSES",
    cta="See Your Options",
    size="1080x1080",
    campaign_name="growth_capital",
    style="ceo_portrait",
):
    """
    Generate a production-grade growth capital ad for SunBiz Funding.

    Styles:
        ceo_portrait       — Executive portrait in premium workspace
        growth_chart       — Fintech-style data visualization with growth curve
        lifestyle_success  — Business owner thriving in their environment
    """
    template = GROWTH_PROMPTS.get(style, GROWTH_PROMPTS["ceo_portrait"])
    prompt = template.format(headline=headline, cta=cta)

    output_dir = PROJECT_ROOT / "media" / "exports" / campaign_name
    output_path = output_dir / f"growth_{style}_{size.replace('x', '_')}.png"

    return generate_ad_image(
        prompt=prompt,
        output_path=str(output_path),
        size=size,
        campaign_name=campaign_name,
        creative_type="Static Image",
        angle=f"Growth - {style.replace('_', ' ').title()}",
    )


# ---------------------------------------------------------------------------
# STORIES / VERTICAL FORMAT GENERATOR
# ---------------------------------------------------------------------------

def generate_stories_ad(
    headline="DROWNING IN MCA PAYMENTS?",
    before_daily="$2,100/day across 4 funders",
    after_daily="$850/day — one partner",
    savings="Save $1,250/day",
    cta="SWIPE UP TO QUALIFY",
    campaign_name="stories",
    style="transformation",
):
    """
    Generate a vertical 9:16 Stories/Reels ad.

    Styles:
        transformation — Dramatic before/after with human
        quick_stat     — Fast-scrolling stat highlight
    """
    if style == "quick_stat":
        prompt = f"""
SCENE: Vertical 9:16 mobile-optimized financial services story ad.

BACKGROUND: Deep navy blue (#001F54) with subtle geometric pattern.
Designed for rapid scrolling — must stop the thumb in 0.3 seconds.

TOP THIRD: A close-up face shot of a concerned business owner looking directly
at camera — serious, questioning expression. Sharp focus, dramatic side lighting.
Overlaid text: "{headline}" in massive bold white, slight 3D shadow.

MIDDLE THIRD: Glowing gold number "{savings}" taking up the full width.
Below it: "EVERY. SINGLE. DAY." in white, spaced out for emphasis.
Subtle pulse/glow effect on the savings number.

BOTTOM THIRD:
- Small before/after: "{before_daily}" (red strikethrough) → "{after_daily}" (green)
- Large orange CTA button filling the width: "{cta}"
- SunBiz Funding logo centered below button

STYLE: Bold, high-contrast, mobile-first. Stop-the-scroll design.
Every element must be readable at phone screen size.
"""
    else:  # transformation
        prompt = f"""
SCENE: Vertical 9:16 cinematic transformation story ad.

TOP SECTION (top 40%):
- Dark, moody atmosphere — stressed business owner at desk, face lit by screen glow
- Papers, multiple payment notices visible
- Red-tinted overlay
- Text: "BEFORE: {before_daily}" in white on red banner

DRAMATIC TRANSITION (middle 20%):
- Visual divider — lightning bolt, dramatic line, or energy burst effect
- "{savings}" in massive glowing gold text
- "YOUR DAILY SAVINGS" in small white beneath

BOTTOM SECTION (bottom 40%):
- Bright, warm atmosphere — SAME person now relaxed, smiling, at a clean desk
- Green-tinted overlay, natural warm light
- Text: "AFTER: {after_daily}" in white on green banner
- Large orange CTA: "{cta}"
- SunBiz Funding logo bottom center

STYLE: Cinematic, dramatic, emotional. Mobile-optimized vertical format.
Maximum visual impact for Stories/Reels. Stop-the-scroll quality.
"""

    output_dir = PROJECT_ROOT / "media" / "exports" / campaign_name
    output_path = output_dir / f"story_{style}_1080_1920.png"

    return generate_ad_image(
        prompt=prompt,
        output_path=str(output_path),
        size="1080x1920",
        campaign_name=campaign_name,
        creative_type="Static Image (Stories)",
        angle=f"Stories - {style.replace('_', ' ').title()}",
    )


# ---------------------------------------------------------------------------
# MULTI-SIZE GENERATOR
# ---------------------------------------------------------------------------

def generate_all_sizes(prompt, campaign_name):
    """Generate an ad in all standard platform sizes."""
    sizes = {
        "meta_feed_square": "1080x1080",
        "meta_feed_portrait": "1080x1350",
        "meta_stories": "1080x1920",
        "google_display": "1200x628",
    }
    results = {}
    for name, size in sizes.items():
        output_dir = PROJECT_ROOT / "media" / "exports" / campaign_name
        output_path = output_dir / f"{name}.png"
        results[name] = generate_ad_image(
            prompt=prompt, output_path=str(output_path), size=size,
            campaign_name=campaign_name,
        )
    return results


# ---------------------------------------------------------------------------
# FULL CAMPAIGN CREATIVE SUITE
# ---------------------------------------------------------------------------

def generate_campaign_suite(campaign_name="sunbiz_campaign", audience="consolidation"):
    """
    Generate a complete creative suite for a campaign — all styles × key sizes.

    Args:
        campaign_name: Campaign identifier
        audience: 'consolidation' or 'growth'

    Returns:
        dict of all generated results
    """
    results = {}

    if audience == "consolidation":
        for style in CONSOLIDATION_PROMPTS:
            key = f"consolidation_{style}_feed"
            results[key] = generate_consolidation_ad(
                style=style, size="1080x1080", campaign_name=campaign_name,
            )
            # Also generate 4:5 portrait for optimal feed
            key_portrait = f"consolidation_{style}_portrait"
            results[key_portrait] = generate_consolidation_ad(
                style=style, size="1080x1350", campaign_name=campaign_name,
            )
        # Stories variants
        for s_style in ["transformation", "quick_stat"]:
            results[f"story_{s_style}"] = generate_stories_ad(
                style=s_style, campaign_name=campaign_name,
            )
    else:  # growth
        for style in GROWTH_PROMPTS:
            key = f"growth_{style}_feed"
            results[key] = generate_growth_ad(
                style=style, size="1080x1080", campaign_name=campaign_name,
            )
            key_portrait = f"growth_{style}_portrait"
            results[key_portrait] = generate_growth_ad(
                style=style, size="1080x1350", campaign_name=campaign_name,
            )

    return results


# ---------------------------------------------------------------------------
# CLI ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("SunBiz Funding — Production-Grade AI Ad Generator")
    print("=" * 55)
    print()
    print("SDK: google-genai | Model: gemini-2.5-flash-image")
    print("Features: Psychology-based prompts, AI humans, logo compositing")
    print()
    print("CONSOLIDATION AD STYLES:")
    for style in CONSOLIDATION_PROMPTS:
        print(f"  - {style}")
    print()
    print("GROWTH CAPITAL AD STYLES:")
    for style in GROWTH_PROMPTS:
        print(f"  - {style}")
    print()
    print("EXAMPLES:")
    print()
    print("  # Generate a hero ad with confident business owner")
    print('  from scripts.imagen_generate import generate_consolidation_ad')
    print('  result = generate_consolidation_ad(style="hero_human")')
    print()
    print("  # Generate split-screen before/after transformation")
    print('  result = generate_consolidation_ad(style="split_screen")')
    print()
    print("  # Generate Bloomberg-style data dashboard")
    print('  result = generate_consolidation_ad(style="data_dashboard")')
    print()
    print("  # Generate growth capital CEO portrait")
    print('  from scripts.imagen_generate import generate_growth_ad')
    print('  result = generate_growth_ad(style="ceo_portrait")')
    print()
    print("  # Generate full campaign creative suite (all styles)")
    print('  from scripts.imagen_generate import generate_campaign_suite')
    print('  results = generate_campaign_suite("q2_consolidation", "consolidation")')
    print()
    print("  # Generate Stories/Reels vertical ad")
    print('  from scripts.imagen_generate import generate_stories_ad')
    print('  result = generate_stories_ad(style="transformation")')
