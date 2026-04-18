"""Generate Facebook page profile picture and cover photo using Gemini."""
import requests
import json
import base64
import os
from pathlib import Path

# Load API key
env_path = Path(__file__).parent.parent / ".env.agents"
GEMINI_KEY = None
for line in env_path.read_text().splitlines():
    if line.startswith("GEMINI_API_KEY="):
        GEMINI_KEY = line.split("=", 1)[1].strip()
        break

if not GEMINI_KEY:
    print("ERROR: GEMINI_API_KEY not found in .env.agents")
    exit(1)

URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={GEMINI_KEY}"
HEADERS = {"Content-Type": "application/json"}
OUT_DIR = Path(__file__).parent.parent / "docs" / "ads"


def generate_image(prompt: str, filename: str) -> bool:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    print(f"Generating {filename}...")
    try:
        resp = requests.post(URL, headers=HEADERS, json=payload, timeout=120)
        result = resp.json()
        for part in result.get("candidates", [{}])[0].get("content", {}).get("parts", []):
            if "inlineData" in part:
                img_data = base64.b64decode(part["inlineData"]["data"])
                out_path = OUT_DIR / filename
                out_path.write_bytes(img_data)
                print(f"  Saved: {out_path} ({len(img_data):,} bytes)")
                return True
        print(f"  No image returned. Response: {json.dumps(result, indent=2)[:300]}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


# --- Profile Picture (square, 1080x1080) ---
profile_prompt = """Generate a professional, premium square profile picture for a business funding company.

Requirements:
- Square image, 1080x1080 pixels
- Solid deep navy blue background (hex #001F54)
- Large, elegant gold/amber colored (hex #D4A843) monogram letters "SB" centered
- The letters should be in a modern, premium sans-serif typeface with slight metallic sheen
- Below the monogram, "FUNDING" in small, clean white uppercase text with wide letter spacing
- Extremely minimal and clean - no icons, no graphics, no borders
- Premium financial services aesthetic (think Goldman Sachs, JP Morgan)
- Must look crisp and readable even as a tiny Facebook profile thumbnail
- Professional, trustworthy, authoritative"""

# --- Cover Photo (landscape, 1640x856 for Facebook) ---
cover_prompt = """Generate a professional Facebook cover photo for SunBiz Funding, a business capital company.

Requirements:
- Wide landscape format, 1640x856 pixels (Facebook cover photo dimensions)
- Left side: deep navy blue (#001F54) gradient fading to slightly lighter navy on right
- Large bold white text on left reading "Business Funding" on one line, "Simplified." on the next line in gold (#D4A843)
- Below that in smaller white text: "$5K - $250K | No Credit Pull | Weekly Payments"
- Right side: subtle abstract geometric pattern or financial graph lines in gold (#D4A843) at low opacity
- A thin gold (#D4A843) horizontal accent line separating the headline from the subtitle
- Clean, modern, premium financial services aesthetic
- No photos, no people, no stock imagery - purely typographic and geometric
- Professional, authoritative, trustworthy"""


if __name__ == "__main__":
    print("=" * 50)
    print("SunBiz Funding — Page Asset Generator")
    print("=" * 50)

    success = 0
    success += generate_image(profile_prompt, "sunbiz_profile_picture.png")
    success += generate_image(cover_prompt, "sunbiz_cover_photo.png")

    print(f"\nDone: {success}/2 images generated")
    if success > 0:
        print(f"Files in: {OUT_DIR}")
