"""R2.2 geometry-aware scene and engraved, exact-copy lettering primitives.

Material typography is composed over an explicitly reviewed, reserved low-detail
region of the provided bespoke hero. No opaque text backing card is generated.
This module neither generates hero art nor claims aesthetic approval.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import random
from typing import Callable, Sequence

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat


class AdaptiveLayoutError(ValueError):
    """Argument-specific layout or lettered surface is unsafe or cannot fit."""


ARRANGEMENTS = frozenset({
    "legacy", "portrait-left", "portrait-right", "central-portrait", "paired-dialogue"
})


@dataclass(frozen=True)
class LetteringSurface:
    """Approved physical lettering aperture in final-canvas pixel coordinates."""
    box: tuple[int, int, int, int]
    material: str = "engraved"  # 'engraved' | 'stamped', never a filled opaque card
    rotation_degrees: int = 0
    reserved_surface_reviewed: bool = False


def _intersects(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def validate_arrangement(
    arrangement: str,
    placements: Sequence,
    hero_box: tuple[int, int, int, int],
) -> None:
    """The active visual geometry is chosen per editorial argument, not per cast."""
    if arrangement not in ARRANGEMENTS:
        raise AdaptiveLayoutError("Unapproved argument-responsive composition geometry.")
    if arrangement == "legacy":
        return
    left, _, right, _ = hero_box
    span = right - left
    if arrangement == "paired-dialogue":
        if len(placements) != 2:
            raise AdaptiveLayoutError("Paired dialogue requires exactly two canonical panels.")
        centres = sorted((p.box[0] + p.box[2]) / 2 for p in placements)
        if not (centres[0] <= left + span * .46 and centres[1] >= left + span * .54):
            raise AdaptiveLayoutError("Two portraits must occupy distinct dialogue fields.")
        return
    if len(placements) != 1:
        raise AdaptiveLayoutError("Single-portrait geometry cannot be assigned to a dual cast.")
    p = placements[0]
    centre = (p.box[0] + p.box[2]) / 2
    if arrangement == "portrait-left" and centre > left + span * .43:
        raise AdaptiveLayoutError("Portrait-left geometry must reserve right-side scene space.")
    if arrangement == "portrait-right" and centre < left + span * .57:
        raise AdaptiveLayoutError("Portrait-right geometry must reserve left-side scene space.")
    if arrangement == "central-portrait" and not (
        left + span * .35 <= centre <= left + span * .65
    ):
        raise AdaptiveLayoutError("Central portrait must remain centred on analytical apparatus.")


def _wrap_exact(draw, copy: str, font, width: int) -> list[str]:
    if not isinstance(copy, str) or not copy.strip():
        raise AdaptiveLayoutError("Exact editorial material phrase is missing.")
    rows = []
    for part in copy.split("\n"):
        current = ""
        for word in part.split():
            if draw.textlength(word, font=font) > width:
                raise AdaptiveLayoutError("Exact lettering word cannot fit reserved surface.")
            candidate = (current + " " + word).strip()
            if current and draw.textlength(candidate, font=font) > width:
                rows.append(current)
                current = word
            else:
                current = candidate
        if current:
            rows.append(current)
    return rows


def compose_material_lettering(
    canvas: Image.Image,
    *,
    exact_phrase: str,
    surface: LetteringSurface,
    hero_box: tuple[int, int, int, int],
    raw_hero: Image.Image,
    portrait_boxes: Sequence[tuple[int, int, int, int]],
    portrait_occupancy: Image.Image,
    ink: tuple[int, int, int],
    accent: tuple[int, int, int],
    font_loader: Callable[[int, str], ImageFont.FreeTypeFont],
) -> dict:
    if canvas.mode != "RGBA" or portrait_occupancy.mode != "L":
        raise AdaptiveLayoutError("Lettering needs RGBA canvas and true alpha occupancy.")
    if surface.material not in ("engraved", "stamped"):
        raise AdaptiveLayoutError("Only physically interpreted engraved/stamped lettering is allowed.")
    if type(surface.rotation_degrees) is not int or abs(surface.rotation_degrees) > 5:
        raise AdaptiveLayoutError("Lettering rotation exceeds phone-safe angular limits.")
    if surface.reserved_surface_reviewed is not True:
        raise AdaptiveLayoutError("Lettering requires a human-reviewed reserved physical surface.")
    box = surface.box
    if not isinstance(box, tuple) or len(box) != 4 or any(type(v) is not int for v in box):
        raise AdaptiveLayoutError("Lettering surface needs four exact integer coordinates.")
    x0, y0, x1, y1 = box
    hx0, hy0, hx1, hy1 = hero_box
    if not (hx0 + 18 <= x0 < x1 <= hx1 - 18
            and hy0 + 18 <= y0 < y1 <= hy1 - 18
            and x1 - x0 >= 225 and y1 - y0 >= 95):
        raise AdaptiveLayoutError("Lettering surface crosses artwork, margin or size constraints.")
    if any(_intersects(box, other) for other in portrait_boxes):
        raise AdaptiveLayoutError("Material type cannot overlap a canonical portrait aperture.")
    # Quiet-zone validation uses the UNCOMPOSITED hero, not a region already
    # hidden by portraits. Busy illustration must be redesigned, not covered.
    rx0, ry0 = x0 - hx0, y0 - hy0
    patch = raw_hero.crop((rx0, ry0, x1 - hx0, y1 - hy0))
    if ImageStat.Stat(patch.convert("L")).stddev[0] > 34:
        raise AdaptiveLayoutError("Reserved lettered hero surface is too busy for legible type.")

    sw, sh = x1 - x0, y1 - y0
    mask = Image.new("L", (sw, sh), 0)
    painter = ImageDraw.Draw(mask)
    fitted = None
    for size in range(45, 19, -1):
        font = font_loader(size, "headline")
        lines = _wrap_exact(painter, exact_phrase, font, sw - 62)
        lineheight = round(size * 1.22)
        if len(lines) <= 3 and len(lines) * lineheight <= sh - 54:
            fitted = (font, lines, size, lineheight)
            break
    if fitted is None:
        raise AdaptiveLayoutError("Exact phrase cannot fit the approved physical surface.")
    font, lines, size, lineheight = fitted
    for index, line in enumerate(lines):
        painter.text((29, 22 + index * lineheight), line, font=font, fill=255)

    if surface.rotation_degrees:
        mask = mask.rotate(surface.rotation_degrees, resample=Image.Resampling.BICUBIC,
                           expand=False)
    # Simulate dry ink grain without creating an opaque card or replacing the
    # hero pixels outside the actual letter glyphs.
    seed = int(sha256((exact_phrase + str(box) + surface.material).encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    pixels = mask.load()
    for _ in range(min(2800, sw * sh // 8)):
        x, y = rng.randrange(sw), rng.randrange(sh)
        if pixels[x, y] > 0:
            pixels[x, y] = max(70, pixels[x, y] - rng.randrange(30, 110))
    target_ink = accent if surface.material == "stamped" else ink
    layer = Image.new("RGBA", (sw, sh), (*target_ink, 0))
    layer.putalpha(mask)
    # Source identity has already been protected by geometry; the mask below
    # is defence-in-depth for anti-aliased edges.
    protect = portrait_occupancy.crop(box).point(lambda value: 255 if value else 0)
    layer.putalpha(ImageChops.subtract(layer.getchannel("A"), protect))
    canvas.alpha_composite(layer, dest=(x0, y0))
    return {
        "surface_box": list(box),
        "material": surface.material,
        "rotation_degrees": surface.rotation_degrees,
        "font_size": size,
        "line_count": len(lines),
        "surface_reviewed": True,
        "copy_sha256": sha256(exact_phrase.encode("utf-8")).hexdigest(),
        "opaque_card_added": False,
    }
