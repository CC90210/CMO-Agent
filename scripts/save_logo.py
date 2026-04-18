"""
Save the SunBiz Funding logo to media/brand/sunbiz_logo.png

Features:
    - Copies logo to the expected brand directory
    - Removes white/light background and makes it transparent (Pillow)
    - Validates minimum resolution
    - Creates brand directory if needed

Usage:
    python scripts/save_logo.py <path_to_logo.png>

The logo compositing system in imagen_generate.py expects:
    media/brand/sunbiz_logo.png (PNG with transparency)

Requirements:
    pip install Pillow
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
LOGO_DEST = PROJECT_ROOT / "media" / "brand" / "sunbiz_logo.png"


def remove_white_background(image):
    """
    Remove white/near-white background from an image and make it transparent.
    Uses per-pixel alpha based on distance from white.
    """
    from PIL import Image

    img = image.convert("RGBA")
    data = img.getdata()

    new_data = []
    # Threshold: pixels with R,G,B all above this value are considered "white"
    threshold = 225
    # Soft edge: pixels between (threshold - margin) and threshold get partial alpha
    margin = 30

    for item in data:
        r, g, b, a = item
        # Calculate "whiteness" — how close to pure white
        min_channel = min(r, g, b)

        if min_channel > threshold:
            # Fully transparent (white background)
            new_data.append((r, g, b, 0))
        elif min_channel > (threshold - margin):
            # Partial transparency for soft edges (anti-aliasing)
            alpha = int(255 * (1 - (min_channel - (threshold - margin)) / margin))
            new_data.append((r, g, b, alpha))
        else:
            # Keep original pixel fully opaque
            new_data.append((r, g, b, a))

    img.putdata(new_data)
    return img


def save_logo(source_path: str, remove_bg: bool = True):
    """
    Process and save logo to the expected brand directory.

    Args:
        source_path: Path to source logo image
        remove_bg: Whether to remove white background (default True)
    """
    from PIL import Image

    source = Path(source_path)
    if not source.exists():
        print(f"ERROR: Source file not found: {source}")
        sys.exit(1)

    LOGO_DEST.parent.mkdir(parents=True, exist_ok=True)

    # Open and process
    img = Image.open(str(source))
    original_size = img.size
    print(f"Source: {source}")
    print(f"Original size: {original_size[0]}x{original_size[1]}")
    print(f"Original mode: {img.mode}")

    if original_size[0] < 200 or original_size[1] < 200:
        print("WARNING: Logo resolution is low. Recommend 500x500px minimum.")

    if remove_bg:
        print("Removing white background...")
        img = remove_white_background(img)
        print("Background removed — transparent PNG created.")
    else:
        img = img.convert("RGBA")

    # Save as PNG with transparency
    img.save(str(LOGO_DEST), "PNG", optimize=True)
    print(f"Logo saved to: {LOGO_DEST}")
    print(f"Size: {LOGO_DEST.stat().st_size:,} bytes")
    print(f"Mode: {img.mode} (with alpha channel)")
    print("Logo compositing is now active for all generated ads.")


def create_from_url(url: str):
    """Download logo from URL and save with transparent background."""
    import urllib.request
    import tempfile

    tmp = Path(tempfile.mktemp(suffix=".png"))
    print(f"Downloading logo from: {url}")
    urllib.request.urlretrieve(url, str(tmp))
    save_logo(str(tmp))
    tmp.unlink()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/save_logo.py <path_to_logo.png>")
        print("       python scripts/save_logo.py --no-bg-remove <path_to_logo.png>")
        print()
        print(f"Destination: {LOGO_DEST}")
    elif sys.argv[1] == "--no-bg-remove":
        if len(sys.argv) < 3:
            print("ERROR: Provide path after --no-bg-remove")
            sys.exit(1)
        save_logo(sys.argv[2], remove_bg=False)
    else:
        save_logo(sys.argv[1])
