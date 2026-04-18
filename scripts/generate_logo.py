"""
Generate a clean SunBiz Funding logo with transparent background using Gemini.

This creates media/brand/sunbiz_logo.png — the logo used for compositing
onto every generated ad via imagen_generate.py.

Usage:
    python scripts/generate_logo.py

Requirements:
    pip install google-genai Pillow python-dotenv
"""

import os
import base64
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env.agents")

LOGO_DEST = PROJECT_ROOT / "media" / "brand" / "sunbiz_logo.png"


def generate_logo():
    """Generate the SunBiz Funding logo using Gemini image generation."""
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in .env.agents")
        return

    client = genai.Client(api_key=api_key)

    prompt = """Generate a professional business logo on a pure white background.

EXACT LOGO DESIGN:
- A golden/amber colored hand (open palm, facing upward) cradling a money bag with a dollar sign ($)
- The money bag is golden/amber colored with a dark green dollar sign
- Below the hand is a single curved green leaf accent (emerald green)
- Surrounding the hand+moneybag is an elegant sunburst pattern — thin dark lines radiating outward in a full circle, like rays of sunshine
- Below the entire icon, centered text reads "SUNBIZ FUNDING" in clean, professional dark serif/sans-serif lettering
- The text should be in dark green or black

COLORS:
- Golden amber (#D4A843) for the hand and money bag
- Emerald green (#10b981) for the leaf and dollar sign
- Dark charcoal/black for the radiating lines and text

STYLE: Clean, professional corporate logo. Flat design with minimal shading.
Simple enough to be recognizable at small sizes. White background.
High resolution, crisp edges, vector-quality rendering.

The logo should be centered in the image with generous padding around it.
NO additional text, NO taglines, NO background graphics. Just the logo icon and "SUNBIZ FUNDING" text."""

    LOGO_DEST.parent.mkdir(parents=True, exist_ok=True)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio="1:1",
                ),
            ),
        )

        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data is not None:
                image_data = part.inline_data.data
                if isinstance(image_data, str):
                    image_data = base64.b64decode(image_data)

                # Save raw first
                raw_path = LOGO_DEST.parent / "sunbiz_logo_raw.png"
                with open(str(raw_path), "wb") as f:
                    f.write(image_data)
                print(f"Raw logo saved: {raw_path}")

                # Now remove white background
                import sys
                sys.path.insert(0, str(PROJECT_ROOT))
                from scripts.save_logo import remove_white_background
                from PIL import Image

                img = Image.open(str(raw_path))
                img_transparent = remove_white_background(img)
                img_transparent.save(str(LOGO_DEST), "PNG", optimize=True)

                print(f"Transparent logo saved: {LOGO_DEST}")
                print(f"Size: {LOGO_DEST.stat().st_size:,} bytes")
                print("Logo compositing is now active for all generated ads.")
                return str(LOGO_DEST)

        print("ERROR: No image generated in response")
        return None

    except Exception as e:
        print(f"ERROR generating logo: {e}")
        return None


if __name__ == "__main__":
    print("SunBiz Funding — Logo Generator")
    print("=" * 40)
    generate_logo()
