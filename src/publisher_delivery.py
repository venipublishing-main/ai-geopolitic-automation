"""Loss-minimising delivery JPEGs and unmistakable 10-image QA carousel fixtures.

Never modifies the archived PNGs. No publishing or network access.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

from .publisher_archive import PublisherBlocked

JPEG_SIZE = (1080, 1350)
MAX_SOURCE_BYTES = 40 * 1024 * 1024
MAX_JPEG_BYTES = 8 * 1024 * 1024
PAPER = (247, 244, 235)


def to_api_jpeg(source_png: bytes, *, source_sha256: str,
                expected_dimensions: list[int]) -> bytes:
    """Create white/off-white-padded 4:5 delivery JPEG; no crop/stretch/upscale."""
    if not isinstance(source_png, bytes) or not (0 < len(source_png) <= MAX_SOURCE_BYTES):
        raise PublisherBlocked("Original carousel PNG has invalid byte length.")
    if hashlib.sha256(source_png).hexdigest() != source_sha256:
        raise PublisherBlocked("Original slide checksum differs from the archive QC record.")
    if expected_dimensions not in ([1080, 1350], [1080, 1440]):
        raise PublisherBlocked("Unexpected source dimensions in the archive QC record.")
    try:
        with Image.open(io.BytesIO(source_png)) as image:
            if image.format != "PNG" or list(image.size) != expected_dimensions:
                raise PublisherBlocked("Source file does not match its approved PNG dimensions.")
            if "A" in image.getbands() or "transparency" in image.info:
                flattened = Image.new("RGBA", image.size, PAPER + (255,))
                flattened.alpha_composite(image.convert("RGBA"))
                original = flattened.convert("RGB")
            else:
                original = image.convert("RGB")
            if original.size == JPEG_SIZE:
                delivery = original
            else:
                # 3:4 is accepted by Instagram's app, but not reliably by
                # the publishing API. Fit the *entire* artwork to a 4:5
                # off-white canvas; never lose the editorial perimeter.
                thumbnail = ImageOps.contain(original, JPEG_SIZE, Image.Resampling.LANCZOS)
                delivery = Image.new("RGB", JPEG_SIZE, PAPER)
                delivery.paste(thumbnail, ((JPEG_SIZE[0] - thumbnail.width) // 2,
                                            (JPEG_SIZE[1] - thumbnail.height) // 2))
            target = io.BytesIO()
            delivery.save(target, format="JPEG", quality=94, subsampling=0,
                          optimize=True, progressive=True)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise PublisherBlocked("Invalid PNG image; delivery conversion blocked.") from exc
    contents = target.getvalue()
    if len(contents) > MAX_JPEG_BYTES:
        raise PublisherBlocked("API JPEG exceeds maximum delivery size.")
    return contents


def _font(size: int, *, bold: bool = False):
    options = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for option in options:
        if Path(option).is_file():
            return ImageFont.truetype(option, size)
    return ImageFont.load_default()


def test_image(index: int) -> bytes:
    """Exactly one of ten clearly fake pages, safely distinct from editorials."""
    if not 1 <= index <= 10:
        raise PublisherBlocked("QA image index must be between 1 and 10.")
    image = Image.new("RGB", JPEG_SIZE, PAPER)
    d = ImageDraw.Draw(image)
    x0, x1 = 95, 985
    d.rectangle((x0, 96, x1, 124), fill=(35, 49, 65))
    d.text((x0, 155), "AI GEOPOLITIC — PUBLISHING QA",
           fill=(35, 49, 65), font=_font(37, bold=True))
    d.rounded_rectangle((95, 375, 985, 862), radius=35,
                        fill=(240, 234, 224), outline=(155, 60, 48), width=8)
    d.text((153, 449), "TEST ONLY", fill=(145, 46, 36), font=_font(106, bold=True))
    d.text((153, 607), f"{index:02d} / 10", fill=(35, 49, 65),
           font=_font(115, bold=True))
    d.text((98, 914), "NOT NEWS • NOT A PRODUCTION EPISODE",
           fill=(125, 58, 47), font=_font(30, bold=True))
    d.text((98, 980), "Instagram carousel connection verification",
           fill=(55, 60, 68), font=_font(29))
    d.line((95, 1100, 985, 1100), fill=(35, 49, 65), width=3)
    for i in range(10):
        left = 260 + i * 57
        d.ellipse((left, 1155, left + 19, 1174),
                  fill=(145, 46, 36) if i == index - 1 else (184, 180, 172))
    d.text((96, 1250), "ONE TEST CAROUSEL • DELETE FROM INSTAGRAM APP",
           fill=(105, 74, 70), font=_font(23, bold=True))
    target = io.BytesIO()
    image.save(target, format="JPEG", quality=92, subsampling=0, optimize=True)
    return target.getvalue()


def create_test_deck(folder: Path) -> dict:
    """Generate ten local .jpg QA assets. Never write into the Drive archive."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    assets = []
    for index in range(1, 11):
        name = f"TEST_Slide{index:02d}of10.jpg"
        path = folder / name
        data = test_image(index)
        path.write_bytes(data)
        assets.append({"filename": name, "sha256": hashlib.sha256(data).hexdigest(),
                       "bytes": len(data)})
    return {"test": True, "carousel_count": 10, "images": assets,
            "caption": "TEST ONLY — AI Geopolitic publisher verification. "
                       "Not a news briefing. This test carousel will be deleted manually."}
