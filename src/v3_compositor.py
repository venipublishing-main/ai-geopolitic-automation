"""R2 deterministic, draft-only active 4:5 compositor. Zero generation / publishing.

The R2 stage only COMPOSITES separately supplied bespoke hero artwork and exact
hash-pinned original transparent panelist PNGs. It never invents artwork or
claims to have visually approved a complete slide. The old 1080-square
renderer remains frozen and unused.
"""
from __future__ import annotations

import io
import json
import random
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Mapping

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

from .episode_manifest_v2 import validate_manifest_v2
from .v3_canon_assets import verify_portrait_bytes, verify_reference_bytes
from .v3_readiness import V3_PORTRAIT_IDS, v3_characters

WIDTH, HEIGHT = 1080, 1350
HERO_BOX = (48, 399, 1032, 998)
PAPER = (245, 242, 234)
INK = (20, 21, 20)
MUTED = (78, 72, 65)
GOLD = (143, 102, 26)
FOOTER = "The event is factual. The interpretation ideological."
RAIL_CENTRES = tuple((76 + 43 * i, 1292) for i in range(10))


class R2CompositionError(ValueError):
    """A deterministic output would violate a layout or identity gate."""


@dataclass(frozen=True)
class PortraitPlacement:
    slug: str
    box: tuple[int, int, int, int]
    mirror: bool = False


@dataclass(frozen=True)
class R2SlidePlan:
    slide_number: int
    visual_id: str
    hero_family: str
    placements: tuple[PortraitPlacement, ...]
    ep128_reference_id: str
    background_human_free_reviewed: bool = False


@dataclass(frozen=True)
class R2Composite:
    png_bytes: bytes
    qc: dict


def _hex(value: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or len(value) != 7 or value[0] != "#":
        raise R2CompositionError("Invalid canonical accent colour.")
    try:
        return tuple(int(value[n:n + 2], 16) for n in (1, 3, 5))
    except ValueError as exc:
        raise R2CompositionError("Invalid canonical accent colour.") from exc


def _font(size: int, role: str):
    if role == "headline":
        candidates = [
            "C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/timesbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerifCondensed-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "DejaVuSerif-Bold.ttf",
        ]
    elif role == "sans":
        candidates = [
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
            "DejaVuSansCondensed-Bold.ttf", "DejaVuSans-Bold.ttf",
        ]
    else:
        candidates = [
            "C:/Windows/Fonts/georgia.ttf", "C:/Windows/Fonts/times.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "DejaVuSerif.ttf",
        ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    raise R2CompositionError("Suitable platform font unavailable; no low-quality fallback permitted.")


def _width(draw, text: str, font) -> float:
    return draw.textlength(text, font=font)


def _wrap(draw, text: str, font, max_width: int) -> list[str]:
    if not isinstance(text, str) or not text.strip():
        raise R2CompositionError("Missing mandatory editorial copy.")
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split():
            if _width(draw, word, font) > max_width:
                raise R2CompositionError("An editorial word cannot fit within the safe region.")
            candidate = (current + " " + word).strip()
            if current and _width(draw, candidate, font) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
    return lines


def _fitted(draw, text: str, max_width: int, max_height: int, max_lines: int,
            start: int, minimum: int, role: str):
    for size in range(start, minimum - 1, -1):
        font = _font(size, role)
        lines = _wrap(draw, text, font, max_width)
        line_height = int(size * 1.20)
        if len(lines) <= max_lines and len(lines) * line_height <= max_height:
            return font, lines, line_height
    raise R2CompositionError("Editorial copy overflows its reserved safe region; do not truncate.")


def _draw_copy(draw, text: str, *, x: int, y: int, width: int, height: int,
               lines: int, start: int, minimum: int, role: str, colour):
    font, wrapped, line_height = _fitted(draw, text, width, height, lines, start, minimum, role)
    for i, line in enumerate(wrapped):
        draw.text((x, y + i * line_height), line, font=font, fill=colour)
    return len(wrapped)


def _background_image(png: bytes) -> Image.Image:
    if not isinstance(png, bytes) or len(png) > 16 * 1024 * 1024:
        raise R2CompositionError("Missing or oversized bespoke background-only hero PNG.")
    try:
        with Image.open(io.BytesIO(png)) as im:
            if im.format != "PNG" or im.width < 480 or im.height < 480:
                raise R2CompositionError("Hero must be an approved nontrivial PNG.")
            # Cropping is proportional, never stretched. Reject severe aspect mismatch.
            source_ratio = im.width / im.height
            target_ratio = (HERO_BOX[2] - HERO_BOX[0]) / (HERO_BOX[3] - HERO_BOX[1])
            coverage = min(source_ratio / target_ratio, target_ratio / source_ratio)
            if coverage < 0.69:
                raise R2CompositionError("Hero aspect mismatch would crop away excessive artwork.")
            return ImageOps.fit(im.convert("RGB"),
                                (HERO_BOX[2] - HERO_BOX[0], HERO_BOX[3] - HERO_BOX[1]),
                                method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise R2CompositionError("Background cannot be decoded as PNG.") from exc


def _portrait_image(png: bytes) -> Image.Image:
    try:
        with Image.open(io.BytesIO(png)) as im:
            if im.format != "PNG" or im.mode not in ("RGBA", "LA", "P"):
                raise R2CompositionError("Canonical portrait must have a genuine alpha-capable PNG mode.")
            rgba = im.convert("RGBA")
            if rgba.getchannel("A").getextrema() != (0, 255):
                raise R2CompositionError("Canonical PNG must preserve a transparent cutout and opaque interior.")
            return rgba
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise R2CompositionError("Canonical portrait PNG cannot be decoded.") from exc


def _validate_plan(slide: dict, plan: R2SlidePlan) -> None:
    if plan.slide_number != slide["slide_number"]:
        raise R2CompositionError("Plan and Manifest slide numbers disagree.")
    if (not isinstance(plan.hero_family, str)
            or plan.hero_family != slide["preferred_visual_reasoning_family"]
            or not isinstance(plan.visual_id, str) or not plan.visual_id.strip()):
        raise R2CompositionError("Argument-specific hero family or bespoke design ID absent/mismatched.")
    if not plan.background_human_free_reviewed:
        raise R2CompositionError("Background-only human-free scene must be reviewed before portrait insertion.")
    expected = set(slide["panelists"])
    actual = [p.slug for p in plan.placements]
    if len(actual) != len(expected) or set(actual) != expected:
        raise R2CompositionError("Exactly the Manifest's one or two canonical portraits are required.")
    boxes = []
    for p in plan.placements:
        if len(p.box) != 4 or any(type(i) is not int for i in p.box):
            raise R2CompositionError("Portrait aperture must be four integer pixels.")
        x0, y0, x1, y1 = p.box
        if not (HERO_BOX[0] <= x0 < x1 <= HERO_BOX[2]
                and HERO_BOX[1] <= y0 < y1 <= HERO_BOX[3]):
            raise R2CompositionError("Portrait aperture intersects editorial text/footer safe areas.")
        if x1 - x0 < 180 or y1 - y0 < 280:
            raise R2CompositionError("Portrait aperture is too small for identity visibility.")
        for prev in boxes:
            if (max(x0, prev[0]) < min(x1, prev[2])
                    and max(y0, prev[1]) < min(y1, prev[3])):
                raise R2CompositionError("Assigned portrait apertures overlap.")
        boxes.append(p.box)


def _date_label(value: str) -> str:
    try:
        return date.fromisoformat(value).strftime("%A %d %B %Y").upper()
    except (TypeError, ValueError) as exc:
        raise R2CompositionError("Invalid production date.") from exc


def _paper_grain(canvas: Image.Image, seed: int) -> None:
    rng = random.Random(seed)
    px = canvas.load()
    for _ in range(20000):
        x = rng.randrange(WIDTH)
        y = rng.randrange(HEIGHT)
        r, g, b = px[x, y]
        delta = rng.choice((-3, -2, -1, 1, 2, 3))
        px[x, y] = (max(0, min(255, r + delta)),
                    max(0, min(255, g + delta)),
                    max(0, min(255, b + delta)))


def compose_r2_slide(manifest: dict, plan: R2SlidePlan, *, hero_png: bytes,
                     portrait_pngs: Mapping[str, bytes], ep128_reference_png: bytes) -> R2Composite:
    """Compose one non-publishable 1080x1440 draft; never calls an image provider.

    The exact canonical input hashes and one hydrated Ep128 reference are
    mandatory. Background humans cannot be reliably detected programmatically;
    background_human_free_reviewed is a separate human-authored precondition,
    not machine-verifiable provenance. Every draft still requires human review.
    """
    errors = validate_manifest_v2(manifest, v3_characters(), expected_count=10)
    if errors:
        raise R2CompositionError("Strict current ten-slide Manifest v2 validation failed.")
    if not isinstance(plan, R2SlidePlan) or not 1 <= plan.slide_number <= 10:
        raise R2CompositionError("Exactly one active carousel slide must be specified.")
    slide = manifest["slides"][plan.slide_number - 1]
    _validate_plan(slide, plan)
    verified_ref = verify_reference_bytes(plan.ep128_reference_id, ep128_reference_png)
    if set(portrait_pngs.keys()) != set(slide["panelists"]):
        raise R2CompositionError("Unassigned or missing portrait bytes.")
    portraits = {}
    hashes = {}
    for p in plan.placements:
        data = portrait_pngs[p.slug]
        hashes[p.slug] = verify_portrait_bytes(p.slug, V3_PORTRAIT_IDS[p.slug], data)
        portraits[p.slug] = _portrait_image(data)

    hero = _background_image(hero_png)
    canvas = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    _paper_grain(canvas, int(sha256(
        (manifest["episode_id"] + "|" + str(plan.slide_number)).encode("utf-8")
    ).hexdigest()[:8], 16))
    canvas.paste(hero, (HERO_BOX[0], HERO_BOX[1]))
    canvas = canvas.convert("RGBA")
    for placement in plan.placements:
        portrait = portraits[placement.slug]
        x0, y0, x1, y1 = placement.box
        scale = min((x1 - x0) / portrait.width, (y1 - y0) / portrait.height)
        size = (max(1, round(portrait.width * scale)),
                max(1, round(portrait.height * scale)))
        portrait = portrait.resize(size, Image.Resampling.LANCZOS)
        if placement.mirror:
            portrait = ImageOps.mirror(portrait)
        left = x0 + ((x1 - x0) - size[0]) // 2
        top = y1 - size[1]
        canvas.alpha_composite(portrait, dest=(left, top))

    accent = _hex(slide["accent_colours"][slide["panelists"][0]])
    draw = ImageDraw.Draw(canvas)
    # Fixed publication furniture, separate from bespoke background hero artwork.
    draw.rectangle((46, 28, 135, 118), fill=(*GOLD, 255), outline=(*INK, 255), width=2)
    draw.text((59, 37), "AI", font=_font(54, "headline"), fill=PAPER)
    draw.text((155, 32), "AI GEOPOLITIC", font=_font(51, "headline"), fill=INK)
    draw.text((158, 92), "ANALYSIS. DIALOGUE. CIVILIZATION.",
              font=_font(17, "sans"), fill=MUTED)
    dateline = f"{manifest['episode_id'].upper()}  |  {_date_label(manifest['production_date_sast'])}"
    dateline_font, _, _ = _fitted(draw, dateline, 500, 27, 1, 17, 13, "sans")
    draw.text((1032 - int(_width(draw, dateline, dateline_font)), 111),
              dateline, font=dateline_font, fill=INK)
    draw.line((48, 145, 1032, 145), fill=INK, width=2)

    _draw_copy(draw, slide["headline"], x=52, y=167, width=976, height=204,
               lines=3, start=78, minimum=42, role="headline", colour=INK)
    draw.line((52, 387, 1028, 387), fill=(*accent, 255), width=4)
    draw.line((48, 999, 1032, 999), fill=INK, width=2)

    _draw_copy(draw, slide["main_visual_phrase"], x=52, y=1017,
               width=975, height=54, lines=1, start=35, minimum=22,
               role="headline", colour=(*accent, 255))
    _draw_copy(draw, slide["subheadline"], x=52, y=1081,
               width=975, height=72, lines=2, start=27, minimum=19,
               role="serif", colour=INK)
    labels = "  •  ".join(slide["essential_labels"])
    _draw_copy(draw, labels, x=52, y=1168, width=975, height=57,
               lines=2, start=20, minimum=15, role="sans", colour=MUTED)

    # Exactly ten identical rail circles; the XX/10 text counter appears once,
    # separate from the progress dots (v3.1 publication-furniture contract).
    draw.line((48, 1248, 1032, 1248), fill=INK, width=2)
    for idx, (x, y) in enumerate(RAIL_CENTRES):
        r = 9
        if idx == plan.slide_number - 1:
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(*accent, 255),
                         outline=(*INK, 255), width=1)
        else:
            draw.ellipse((x - r, y - r, x + r, y + r), outline=(*INK, 255), width=2)
    draw.text((521, 1271), f"{plan.slide_number:02d}/10",
              font=_font(31, "sans"), fill=INK)
    draw.line((671, 1266, 671, 1320), fill=INK, width=1)
    draw.text((694, 1267), "The event is factual.",
              font=_font(22, "serif"), fill=INK)
    draw.text((694, 1296), "The interpretation ideological.",
              font=_font(18, "serif"), fill=INK)

    out = io.BytesIO()
    canvas.convert("RGB").save(out, format="PNG", optimize=False, compress_level=9)
    data = out.getvalue()
    with Image.open(io.BytesIO(data)) as check:
        if check.size != (WIDTH, HEIGHT) or check.format != "PNG":
            raise R2CompositionError("Exact final 1080x1350 PNG readback failed.")
    qc = {
        "episode_id": manifest["episode_id"],
        "slide_number": plan.slide_number,
        "counter": f"{plan.slide_number:02d}/10",
        "size": [WIDTH, HEIGHT],
        "pagination_markers": len(RAIL_CENTRES),
        "filled_marker_index": plan.slide_number,
        "footer": FOOTER,
        "hero_visual_id": plan.visual_id,
        "hero_family": plan.hero_family,
        "portrait_sha256": hashes,
        "portrait_apertures": {p.slug: list(p.box) for p in plan.placements},
        "ep128_reference_id": plan.ep128_reference_id,
        "ep128_reference_sha256": verified_ref,
        "hero_png_sha256": sha256(hero_png).hexdigest(),
        "output_png_sha256": sha256(data).hexdigest(),
        "visual_review": "REQUIRED",
        "editorial_approval": "NOT_GRANTED",
        "render_integrity_status": "RENDER_QC_PENDING",
        "publication_authorised": False,
        "image_generation_performed": False,
    }
    return R2Composite(data, qc)
