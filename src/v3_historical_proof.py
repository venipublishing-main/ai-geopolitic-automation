"""R2.2c read-only HISTORICAL Ep136 identity proof (not an editorial generator).

Renders two locally staged, NONPUBLISHABLE test sheets from the original
canonical transparent portrait PNGs and accepted Ep128 source references.
The hero artwork is newly authored deterministic schematic art, not an
AI-generated person or a replacement for the accepted Ep136 images.

Example:
python -m src.v3_historical_proof --design-text path/to/ep136-design.txt \
  --asset-dir path/to/approved-pngs --output-dir path/to/isolated-proofs

The script performs zero network requests, Drive writes, provider calls or
publishing actions. It never bundles source portraits or references in GitHub.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import random
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .episode_manifest_v2 import validate_manifest_v2
from .v3_canon_assets import PORTRAIT_CANON, verify_reference_bytes
from .v3_compositor import (
    HERO_BOX, PortraitPlacement, R2SlidePlan, compose_r2_slide
)
from .v3_adaptive_layout import LetteringSurface
from .v3_readiness import V3_MANIFEST_BEGIN, V3_MANIFEST_END, v3_characters
from .v3_render_qc import audit_exported_png

NAVY = (30, 61, 93)
BLUE = (47, 108, 158)
GOLD = (150, 108, 42)
INK = (31, 32, 31)
PAPER = (246, 241, 231)
HERO_SIZE = (HERO_BOX[2] - HERO_BOX[0], HERO_BOX[3] - HERO_BOX[1])


def _font(size: int, bold: bool = False):
    candidates = ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                  "C:/Windows/Fonts/georgiab.ttf", "DejaVuSerif-Bold.ttf") if bold else (
                  "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
                  "C:/Windows/Fonts/arial.ttf", "DejaVuSansCondensed.ttf")
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    raise RuntimeError("No suitable system font for local engineering proof.")


def _seal(d: ImageDraw.ImageDraw, x: int, y: int, label: str,
          colour=NAVY, size=18):
    d.ellipse((x - 15, y - 15, x + 15, y + 15), outline=colour, width=3)
    d.text((x + 23, y - size // 2 - 2), label, font=_font(size), fill=colour)


def _base(seed: int) -> Image.Image:
    rng = random.Random(seed)
    im = Image.new("RGB", HERO_SIZE, PAPER)
    d = ImageDraw.Draw(im)
    for y in range(26, HERO_SIZE[1] - 25, 26):
        d.line((12, y, HERO_SIZE[0] - 12, y), fill=(224, 219, 208), width=1)
    for x in range(32, HERO_SIZE[0], 33):
        d.line((x, 12, x, HERO_SIZE[1] - 15), fill=(235, 229, 220), width=1)
    for _ in range(4500):
        x, y = rng.randrange(HERO_SIZE[0]), rng.randrange(HERO_SIZE[1])
        if rng.random() < .42:
            colour = (219, 214, 205)
            d.point((x, y), fill=colour)
    return im


def _map_hero() -> Image.Image:
    im = _base(13601)
    d = ImageDraw.Draw(im)
    # Greenland-shaped relief: a schematic silhouette, not a geographic
    # boundary dataset and never a source for precise legal geography.
    shape = [
        (708, 36), (759, 43), (799, 72), (826, 104), (846, 126),
        (835, 162), (861, 193), (852, 226), (825, 238), (820, 278),
        (788, 297), (752, 285), (736, 310), (698, 295), (681, 266),
        (663, 241), (630, 213), (632, 175), (650, 145), (649, 110),
        (670, 88), (675, 58),
    ]
    # Two offset access layers show formal title versus operating permissions.
    for dy, fill, line in [(28, (73, 115, 153), (31, 68, 112)),
                           (13, (151, 192, 210), (41, 98, 148)),
                           (0, (236, 236, 225), NAVY)]:
        polygon = [(x, y + dy) for x, y in shape]
        d.polygon(polygon, fill=fill)
        d.line(polygon + [polygon[0]], fill=line, width=4)
    for yy in range(96, 264, 19):
        d.arc((645, yy - 48, 850, yy + 120), 205, 327, fill=(105, 134, 151), width=1)
    d.text((620, 15), "GREENLAND / TWO CONTROL LAYERS",
           font=_font(19, bold=True), fill=NAVY)
    _seal(d, 577, 143, "01  LEGAL SOVEREIGNTY", NAVY, 18)
    _seal(d, 563, 237, "02  SECURITY ACCESS", BLUE, 18)
    d.line((560, 159, 635, 170), fill=NAVY, width=3)
    d.line((560, 248, 666, 252), fill=BLUE, width=3)
    for i in range(18):
        x = 500 + i * 27
        d.line((x, 322, x + 18, 307), fill=(190, 198, 191), width=1)
    d.line((536, 328, 961, 328), fill=NAVY, width=3)
    d.text((564, 345), "THE CENTRAL DISTINCTION", font=_font(16), fill=NAVY)
    return im


def _wheel_hero() -> Image.Image:
    im = _base(13609)
    d = ImageDraw.Draw(im)
    cx, cy = 810, 210
    for radius, col in [(151, NAVY), (128, GOLD), (106, NAVY),
                        (83, GOLD), (60, NAVY)]:
        d.ellipse((cx-radius, cy-radius, cx+radius, cy+radius),
                  outline=col, width=4)
    for idx in range(20):
        a = math.tau * idx / 20
        x1 = cx + 156 * math.cos(a)
        y1 = cy + 156 * math.sin(a)
        x2 = cx + 167 * math.cos(a)
        y2 = cy + 167 * math.sin(a)
        d.line((x1, y1, x2, y2), fill=GOLD if idx % 2 else NAVY, width=2)
    for i, word in enumerate(("LEGAL", "ACCESS", "SCREENING", "VALUE", "FUTURE CHOICE")):
        x, y = 652, 23 + i * 34
        d.text((x, y), f"{i+1:02d}  {word}", font=_font(16), fill=GOLD if i % 2 else NAVY)
    d.arc((676, 80, 946, 351), 205, 315, fill=GOLD, width=9)
    d.ellipse((cx-14, cy-14, cx+14, cy+14), fill=NAVY, outline=GOLD, width=3)
    d.text((709, 340), "ONE SOVEREIGNTY SYSTEM", font=_font(17, bold=True), fill=NAVY)
    d.line((661, 361, 960, 361), fill=GOLD, width=3)
    return im


def _foreground(number: int) -> bytes:
    overlay = Image.new("RGBA", HERO_SIZE, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    y0 = 292 if number == 1 else 302
    for i in range(7):
        y = y0 + i * 7
        points = [(x, y + round(math.sin(x / 47 + i) * 9))
                  for x in range(0, HERO_SIZE[0], 13)]
        d.line(points, fill=(*NAVY, max(30, 110 - i * 11)), width=2)
    buf = io.BytesIO()
    overlay.save(buf, format="PNG")
    return buf.getvalue()


def _png(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _manifest_from_archive(text: str) -> dict:
    # Older Ep136 archive includes a standing instruction with sample marker
    # strings: the live JSON is the final pair in the document's daily payload.
    start = text.rfind(V3_MANIFEST_BEGIN)
    end = text.rfind(V3_MANIFEST_END)
    if start < 0 or end <= start:
        raise ValueError("Accepted Ep136 Manifest pair not found.")
    obj = json.loads(text[start + len(V3_MANIFEST_BEGIN):end].strip())
    if (obj.get("episode_id") != "Ep136" or
            obj.get("production_date_sast") != "2026-11-04"):
        raise ValueError("This historical fixture accepts only archival Ep136/2026-11-04.")
    errors = validate_manifest_v2(obj, v3_characters(), expected_count=10)
    if errors:
        raise ValueError("Archived v3 Manifest is not a valid ten-slide contract.")
    return obj


def render_historical_proofs(design_text: str, asset_dir: Path, output_dir: Path) -> list[dict]:
    manifest = _manifest_from_archive(design_text)
    if output_dir.exists() and list(output_dir.glob("*")):
        raise ValueError("Proof output directory must be empty; never overwrite accepted files.")
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    plans = {
        1: (
            "portrait-left",
            (PortraitPlacement("nora", (63, 421, 504, 983)),),
            LetteringSurface((606, 755, 1006, 969), "engraved", 0, True),
            "1u6Fux5vvIJHRzgnnZ_Yrr-TabpZlvQeY",
            _map_hero,
        ),
        9: (
            "paired-synthesis",
            (PortraitPlacement("nora", (52, 435, 373, 985)),
             PortraitPlacement("amari_ndlovu", (378, 435, 691, 985))),
            LetteringSurface((704, 790, 1009, 972), "stamped", 0, True),
            "1paH71uL8n5R9r8e-s4LtWtwa0Txrzo62",
            _wheel_hero,
        ),
    }
    for number, (arrangement, placements, surface, reference_id, artist) in plans.items():
        slide = manifest["slides"][number - 1]
        source_files = {}
        for slug in slide["panelists"]:
            filename = PORTRAIT_CANON[slug][0]
            source_files[slug] = (asset_dir / filename).read_bytes()
        ref_name = "Ep128_Slide01of10.png" if number == 1 else "Ep128_Slide09of10.png"
        reference_data = (asset_dir / ref_name).read_bytes()
        verify_reference_bytes(reference_id, reference_data)
        plan = R2SlidePlan(
            slide_number=number,
            visual_id=f"EP136-HISTORICAL-READONLY-HANDDRAWN-{number:02d}",
            hero_family=slide["preferred_visual_reasoning_family"],
            placements=placements,
            ep128_reference_id=reference_id,
            background_human_free_reviewed=True,  # algorithm draws NO people
            arrangement=arrangement,
            material_surface=surface,
        )
        proof = compose_r2_slide(
            manifest, plan, hero_png=_png(artist()),
            portrait_pngs=source_files,
            ep128_reference_png=reference_data,
            foreground_layer_png=_foreground(number),
            foreground_reviewed=True,
        )
        receipt = audit_exported_png(proof.png_bytes, kind="carousel",
                                     item_number=number, compositor_qc=proof.qc)
        if receipt["render_integrity_gate"] != "HUMAN_REVIEW_REQUIRED":
            raise ValueError("Historical engineering preview must never automatically pass QC.")
        name = f"NONPUBLISHABLE_Ep136_CanonProof{number:02d}_4x5.png"
        (output_dir / name).write_bytes(proof.png_bytes)
        (output_dir / name.replace(".png", ".qc.json")).write_text(
            json.dumps({"compositor": proof.qc, "render": receipt}, indent=2),
            encoding="utf-8",
        )
        results.append({"slide": number, "file": name, "qc": receipt})
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design-text", type=Path, required=True)
    parser.add_argument("--asset-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    results = render_historical_proofs(
        args.design_text.read_text(encoding="utf-8-sig"),
        args.asset_dir, args.output_dir,
    )
    print(json.dumps({"proofs": results,
                      "draft_only": True,
                      "generation_performed": False,
                      "publishing_performed": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
