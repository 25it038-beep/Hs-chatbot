from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont


def generate_universal_svg(title: str, svg_markup: str, output_path: str):
    """Generates authentic SVG vector file (§10, §11)."""
    if "<svg" not in svg_markup:
        svg_markup = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="800" height="600">
  <rect width="800" height="600" fill="#0f172a"/>
  <text x="400" y="300" font-family="system-ui, sans-serif" font-size="28" fill="#38bdf8" text-anchor="middle" font-weight="bold">{title}</text>
  <circle cx="400" cy="180" r="50" fill="#3b82f6" opacity="0.8"/>
</svg>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_markup.strip() + "\n")


def generate_universal_png(title: str, output_path: str, width: int = 800, height: int = 600):
    """Generates valid PNG image file (§11)."""
    img = Image.new("RGB", (width, height), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    # Draw simple gradient / banner
    draw.rectangle([0, 0, width, 12], fill=(59, 130, 246))
    draw.text((40, 50), title, fill=(255, 255, 255))
    img.save(output_path, format="PNG")
