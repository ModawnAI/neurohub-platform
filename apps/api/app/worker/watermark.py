"""Image watermark utility using Pillow."""

import io
import math

from PIL import Image, ImageDraw, ImageFont


def apply_watermark(
    image_bytes: bytes,
    text: str,
    opacity: float = 0.3,
    font_size: int = 36,
) -> bytes:
    """Apply diagonal repeating watermark text to an image.

    Args:
        image_bytes: Input JPEG/PNG bytes
        text: Watermark text to embed
        opacity: Text opacity (0.0 - 1.0)
        font_size: Font size in pixels

    Returns:
        Watermarked JPEG bytes
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    width, height = img.size

    # Create transparent overlay
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Load font (fallback to default)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

    # Calculate text dimensions
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Grid spacing
    spacing_x = text_width + 80
    spacing_y = text_height + 100

    # Create a larger canvas for rotation (diagonal requires more space)
    diagonal = int(math.sqrt(width**2 + height**2))
    text_layer = Image.new("RGBA", (diagonal * 2, diagonal * 2), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)

    alpha = int(255 * opacity)
    fill_color = (128, 128, 128, alpha)

    # Draw watermark text in grid
    for y in range(0, diagonal * 2, spacing_y):
        for x in range(0, diagonal * 2, spacing_x):
            text_draw.text((x, y), text, font=font, fill=fill_color)

    # Rotate 30 degrees
    text_layer = text_layer.rotate(30, expand=False, resample=Image.BICUBIC)

    # Crop to original size (center crop)
    cx, cy = text_layer.size[0] // 2, text_layer.size[1] // 2
    crop_box = (cx - width // 2, cy - height // 2, cx + width // 2, cy + height // 2)
    text_layer = text_layer.crop(crop_box)

    # Composite
    result = Image.alpha_composite(img, text_layer)
    result = result.convert("RGB")

    output = io.BytesIO()
    result.save(output, format="JPEG", quality=90)
    return output.getvalue()
