"""Phase C.3: deterministic, local Ep104/05 editorial fusion proof.

The inspected campus anchors are a one-slide mapping, not object recognition.
References inform development only; composition cannot fetch them or generate art.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from . import premium_compositor as control
from .daily_readiness import DailyBuildReadinessResult
from .editorial_primitives import INK, PAPER, LayoutError, paper_texture, fit_wrapped

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = Path("output/phase-c3/Ep104/slide-05")
DISPLAY_FONT = Path(__file__).resolve().parents[1] / "assets/fonts/anton/Anton-Regular.ttf"
REVIEW = "PHASE C.3 EDITORIAL FUSION PROOF READY FOR HUMAN REVIEW"
HERO, PORTRAIT = control.HERO, control.PORTRAIT
HEADLINE, PHRASE, TAKEAWAYS = control.HEADLINE, control.PHRASE, control.TAKEAWAYS
ACCENT, LABELS, MOTTO = control.ACCENT, control.LABELS, control.MOTTO
FACE = (90, 365, 378, 743)
ENGRAVING = {
    "hero": {"contrast": 1.26, "gamma": 1.12, "edge_strength": .65},
    "portrait": {"contrast": 1.06, "gamma": 1.04, "edge_strength": .22},
}
SCREEN = {"dot_pitch": 5, "hatch_pitch": 11, "dot_darkening": 16,
          "hatch_darkening": 10, "midtone_range": [58, 214], "grain_amplitude": 3}
INK_PROCESS = {"autocontrast_cutoff": .4, "unsharp_radius": 1.1, "unsharp_percent": 80,
               "unsharp_threshold": 3, "dark_edge_blur_radius": 1.2,
               "highlight_mapping": list(PAPER), "black_mapping": list(INK)}
# Source coordinates are on the accepted 1024 square raster. Cover crop is
# x=0..1024, y=99.57..924.43. These are visual proof anchors, not factual specs.
ANCHORS = {
    "REMOTE USERS": {"point": (492, 453), "source_point": (175, 245),
                     "object": "off-site road / incoming connection margin", "label": (465, 383, 750, 411),
                     "leader": ((492, 416), (492, 453))},
    "FIBRE": {"point": (576, 599), "source_point": (305, 472),
              "object": "incoming horizontal conduit at campus edge", "label": (415, 622, 565, 650),
              "leader": ((481, 637), (514, 628), (576, 599))},
    "COMPUTE": {"point": (852, 622), "source_point": (735, 507),
                "object": "central service / equipment building zone", "label": (772, 526, 960, 554),
                "leader": ((809, 558), (809, 591), (852, 622))},
    "COOLING": {"point": (625, 538), "source_point": (381, 377),
                "object": "vertical cylinders and connected pipe plant", "label": (576, 467, 728, 495),
                "leader": ((625, 499), (625, 538))},
    "POWER": {"point": (962, 401), "source_point": (906, 164),
              "object": "rear electrical switchyard / busbar zone", "label": (862, 365, 1029, 393),
              "leader": ((962, 397), (962, 401))},
    "LAND": {"point": (920, 802), "source_point": (840, 787),
             "object": "site ground outside building footprint", "label": (872, 823, 941, 851),
             "leader": ((946, 835), (951, 812), (920, 802))},
}
ROUTES = (
    {"from": "REMOTE USERS", "to": "FIBRE", "points": ((492, 453), (401, 490), (401, 569), (576, 599))},
    {"from": "FIBRE", "to": "COMPUTE", "points": ((576, 599), (697, 633), (852, 622))},
    {"from": "COMPUTE", "to": "COOLING", "points": ((852, 622), (772, 582), (700, 553), (625, 538))},
    {"from": "COMPUTE", "to": "POWER", "points": ((852, 622), (891, 584), (997, 503), (997, 431), (962, 401))},
    {"from": "COMPUTE", "to": "LAND", "points": ((852, 622), (894, 697), (930, 755), (920, 802))},
)
REFERENCES = (
    {"file": "reference/Slide05of20-current-final.png", "drive_id": "1jLaocNFP31PQvXmOAZNDSyjzmkbjaQO4"},
    {"file": "reference/kai-historical-exemplar.png", "drive_id": "1mRRuboHP9VVcftljZ9X7lJ1oPhAsbpS9"},
)


def _confined(path, directory, *, exists=True):
    path = Path(path).resolve()
    if not path.is_relative_to((ROOT / directory).resolve()):
        raise ValueError("ASSET_OR_OUTPUT_PATH_ESCAPE")
    if exists and not path.is_file():
        raise ValueError("REQUIRED_LOCAL_ASSET_MISSING")
    return path


def prepare_editorial_engraving(source, *, contrast, gamma, edge_strength, origin):
    """Shared ink process, with no change to the source's geometry.

    Retain continuous tones and dark lines; faint dot/hatch deposition applies
    only to midtones. Screen phase follows page coordinates across both rasters.
    """
    tones = ImageOps.autocontrast(ImageOps.grayscale(source), cutoff=INK_PROCESS["autocontrast_cutoff"])
    tones = ImageEnhance.Contrast(tones).enhance(contrast)
    tones = tones.filter(ImageFilter.UnsharpMask(radius=INK_PROCESS["unsharp_radius"],
                       percent=INK_PROCESS["unsharp_percent"], threshold=INK_PROCESS["unsharp_threshold"]))
    tones = tones.point(lambda v: round(255 * (v / 255) ** gamma))
    dark_edges = ImageChops.subtract(tones.filter(ImageFilter.GaussianBlur(INK_PROCESS["dark_edge_blur_radius"])), tones)
    tones = ImageChops.subtract(tones, dark_edges.point(lambda v: round(v * edge_strength)))
    pixels = tones.load()
    for y in range(tones.height):
        for x in range(tones.width):
            value = pixels[x, y]
            gx, gy = x + origin[0], y + origin[1]
            if SCREEN["midtone_range"][0] < value < SCREEN["midtone_range"][1]:
                value -= SCREEN["dot_darkening"] if gx % SCREEN["dot_pitch"] == gy % SCREEN["dot_pitch"] == 0 else 0
                value -= SCREEN["hatch_darkening"] if (gx + 2 * gy) % SCREEN["hatch_pitch"] == 0 else 0
            # Fixed, low amplitude grain, without modifying global random state.
            grain = ((gx * 17 + gy * 31 + gx * gy) % 7) - SCREEN["grain_amplitude"]
            pixels[x, y] = max(0, min(255, value + grain))
    return ImageOps.colorize(tones, black=INK, white=PAPER)


def prepare_sources(asset, portrait_path, crop):
    with Image.open(asset) as source:
        hero = ImageOps.fit(source.convert("RGB"), (HERO[2] - HERO[0], HERO[3] - HERO[1]), Image.Resampling.LANCZOS)
    portrait, portrait_mask = control.prepare_portrait(portrait_path, crop, (PORTRAIT[2] - PORTRAIT[0], PORTRAIT[3] - PORTRAIT[1]))
    return (prepare_editorial_engraving(hero, **ENGRAVING["hero"], origin=HERO[:2]),
            control._edge_mask(hero.size, left=30, top=20, right=10, bottom=28),
            prepare_editorial_engraving(portrait, **ENGRAVING["portrait"], origin=PORTRAIT[:2]), portrait_mask)


def micro_detail_layer():
    """Graphical construction marks only: no text, data, icons or telemetry."""
    layer = Image.new("RGBA", (1080, 1080))
    draw = ImageDraw.Draw(layer)
    faint = (*ACCENT, 19)
    for x in range(42, 1039, 48):
        draw.line((x, 349, x, 899), fill=(*ACCENT, 9))
    for y in range(349, 900, 48):
        draw.line((42, y, 1038, y), fill=(*ACCENT, 9))
    for x in range(430, 1020, 16):
        draw.line((x, 899, x, 896 if x % 48 else 892), fill=faint)
    for x, y in ((409, 350), (798, 350), (1036, 745), (459, 899)):
        draw.line((x - 4, y, x + 4, y), fill=(*ACCENT, 55))
        draw.line((x, y - 4, x, y + 4), fill=(*ACCENT, 55))
    # Site construction contours, not a geographic map or measured coordinates.
    for inset in (0, 10, 20):
        draw.arc((750 - inset, 710 - inset, 1021 + inset // 2, 884 + inset // 2), 20, 105, fill=faint)
    for y in range(670, 737, 8):
        draw.line((369, y, 445, y - 18), fill=(*INK, 13))
    draw.rectangle(FACE, fill=(0, 0, 0, 0))
    return layer


def route_mask():
    """Mask includes all semantic lines, direction arrows, nodes and leaders."""
    mask = Image.new("L", (1080, 1080))
    draw = ImageDraw.Draw(mask)
    for route in ROUTES:
        points = route["points"]
        draw.line(points, fill=255, width=2, joint="curve")
        a, b = points[-2:]
        angle = math.atan2(b[1] - a[1], b[0] - a[0])
        wings = [(round(b[0] - 10 * math.cos(angle + offset)), round(b[1] - 10 * math.sin(angle + offset)))
                 for offset in (-.45, .45)]
        draw.line((wings[0], b, wings[1]), fill=255, width=2)
    for anchor in ANCHORS.values():
        draw.line(anchor["leader"], fill=255, width=1)
        x, y = anchor["point"]
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), outline=255, width=2)
        draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=255)
    return mask


def validate_route_mask(mask, records):
    # Pixel inspection includes diagonal segments / arrow wings, unlike AABB
    # tests of entire diagonal segments which overestimate their coverage.
    for name, box in [("face", FACE)] + [(r["name"], r["bounds"]) for r in records]:
        padded = (box[0] - 2, box[1] - 2, box[2] + 2, box[3] + 2)
        if mask.crop(padded).getbbox():
            raise ValueError("ROUTE_CROSSES_PROTECTED_REGION: " + name)


def _type(image, records, sizes, name, text, box, *, colour=INK, size=24, minimum=18,
          lines=1, serif=False, bold=False, display=False, knockout=False):
    draw = ImageDraw.Draw(image)
    if display:
        for actual_size in range(size, minimum - 1, -1):
            fnt = ImageFont.truetype(str(DISPLAY_FONT), actual_size)
            bounds = draw.textbbox((0, 0), text, font=fnt)
            if bounds[2] - bounds[0] <= box[2] - box[0] and bounds[3] - bounds[1] <= box[3] - box[1]:
                break
        else:
            raise ValueError("DISPLAY_COPY_TOO_LONG: " + name)
        rendered = text
    else:
        fnt, wrapped = fit_wrapped(draw, text, box[2] - box[0], lines, size, minimum,
                                  max_height=box[3] - box[1], spacing=3, label=name,
                                  serif=serif, bold=bold, condensed=not serif)
        rendered = "\n".join(wrapped)
        bounds = draw.multiline_textbbox((0, 0), rendered, font=fnt, spacing=3)
    xy = (box[0] - bounds[0], box[1] - bounds[1])
    actual = draw.multiline_textbbox(xy, rendered, font=fnt, spacing=3)
    if actual[2] > box[2] or actual[3] > box[3]:
        raise ValueError("TEXT_CLIPPING: " + name)
    control._record(records, name, text, actual)
    sizes[name] = {"size": fnt.size, "font": "Anton" if display else "DejaVu Serif" if serif else "DejaVu Sans Condensed",
                   "raster_glyph_resize": False}
    mask = Image.new("L", image.size)
    ImageDraw.Draw(mask).multiline_text(xy, rendered, font=fnt, spacing=3, fill=255)
    if knockout:
        # One pixel around actual glyph strokes, never an opaque label card.
        image.paste(PAPER, (0, 0), mask.filter(ImageFilter.MaxFilter(3)))
    if display:
        # Fine deterministic ink pinholes; preserve the native font proportions.
        pix = mask.load()
        for y in range(int(actual[1]), int(actual[3])):
            for x in range(int(actual[0]), int(actual[2])):
                if (x * 37 + y * 61 + x * y) % 311 == 0:
                    pix[x, y] = max(0, pix[x, y] - 125)
    image.paste(colour, (0, 0), mask)


def phrase_field(image):
    mask = Image.new("L", image.size)
    draw = ImageDraw.Draw(mask)
    for y in range(PHRASE[1], PHRASE[3]):
        draw.line((PHRASE[0] + y % 3, y, PHRASE[2] - (y * 7) % 3, y), fill=255)
    image.paste(ACCENT, (0, 0), mask)
    pixels = image.load()
    for y in range(PHRASE[1], PHRASE[3]):
        for x in range(PHRASE[0] + 3, PHRASE[2] - 3):
            # Same page-phased deposition as the shared source ink; subtle tone.
            variation = ((x * 17 + y * 31 + x * y) % 7) - 3
            pixels[x, y] = tuple(c + variation for c in ACCENT)
    # Recessed engraved edges join the surrounding construction rules.
    draw = ImageDraw.Draw(image)
    for y in (PHRASE[1] - 5, PHRASE[3] + 5):
        draw.line((55, y, 455, y), fill=ACCENT, width=1)


def compose_fusion(readiness, asset_path, metadata_path, destination):
    slide = control.compile_slide(readiness)
    asset, digest, audit, handoff = control.accepted_asset(asset_path, metadata_path)
    portrait_path = _confined(ROOT / slide.portrait, "assets/characters")
    destination = _confined(destination, PACKAGE / "phase3", exists=False)
    if destination in (asset, Path(metadata_path).resolve(), portrait_path):
        raise ValueError("OUTPUT_SOURCE_COLLISION")
    if destination.suffix.lower() != ".png":
        raise ValueError("PNG_OUTPUT_REQUIRED")
    image = Image.new("RGB", (1080, 1080), PAPER)
    paper_texture(image)  # L0
    micro = micro_detail_layer()
    image.paste(micro, (0, 0), micro)
    hero, hero_mask, portrait, portrait_mask = prepare_sources(asset, portrait_path, slide.crop_box)
    image.paste(hero, HERO[:2], hero_mask)  # L1
    image.paste(portrait, PORTRAIT[:2], portrait_mask)  # L2
    # Fine construction remains visible around the released shoulder boundary.
    image.paste(micro, (0, 0), micro)
    routes = route_mask()  # L3, with a narrow paper release under strokes only.
    image.paste(PAPER, (0, 0), routes.filter(ImageFilter.MaxFilter(3)))
    image.paste(ACCENT, (0, 0), routes)
    records, sizes = [], {}
    for i, label in enumerate(slide.essential_labels):  # L4
        _type(image, records, sizes, f"label_{i}", label, ANCHORS[label]["label"],
              colour=ACCENT, size=25, minimum=22, display=True, knockout=True)
    split = next((i for i, word in enumerate(slide.headline.split()) if "," in word), 0)
    if not split:
        raise ValueError("HEADLINE_TWO_TIER_REQUIRED")
    words = slide.headline.split()
    _type(image, records, sizes, "headline_black", " ".join(words[:split]), (42, 116, 1038, 200),
          display=True, size=110, minimum=72)
    _type(image, records, sizes, "headline_accent", " ".join(words[split:]), (42, 210, 1038, 301),
          display=True, colour=ACCENT, size=110, minimum=72)
    _type(image, records, sizes, "subheadline", slide.subheadline, (42, 313, 1038, 344), serif=True, size=23, minimum=19)
    phrase_field(image)
    phrase_words = slide.main_visual_phrase.split()
    cut = len(phrase_words) // 2
    _type(image, records, sizes, "phrase_first", " ".join(phrase_words[:cut]), (55, 761, 440, 811),
          display=True, size=72, minimum=40, colour=PAPER)
    _type(image, records, sizes, "phrase_second", " ".join(phrase_words[cut:]), (55, 819, 440, 872),
          display=True, size=72, minimum=40, colour=PAPER)
    draw = ImageDraw.Draw(image)
    draw.line((42, 906, 1038, 906), fill=ACCENT, width=1)
    for i, (idea, box) in enumerate(zip(slide.takeaway_ideas, TAKEAWAYS), 1):
        _type(image, records, sizes, f"takeaway_number_{i}", f"{i:02d}", (box[0], 920, box[0] + 87, 988),
              display=True, colour=ACCENT, size=88, minimum=70)
        _type(image, records, sizes, f"takeaway_idea_{i}", idea, (box[0] + 104, 928, box[2], 992),
              size=25, minimum=21, lines=2, bold=True)
        draw.line((box[0] + 104, 996, box[0] + 145, 996), fill=ACCENT, width=2)
        draw.line((box[0], 910, box[0], 913), fill=ACCENT, width=1)
    for x in (366, 706):
        draw.line((x, 924, x, 991), fill=ACCENT, width=1)
    _type(image, records, sizes, "core_argument", slide.core_argument, (42, 1009, 1038, 1029), serif=True, size=16, minimum=14)
    # L6 compact publishing furniture, unchanged copy.
    draw.rectangle((24, 24, 1056, 1056), outline=ACCENT, width=2)
    draw.rectangle((42, 40, 92, 87), outline=ACCENT, width=1)
    _type(image, records, sizes, "badge", "AI", (49, 46, 89, 80), colour=ACCENT, size=33, minimum=28, bold=True)
    _type(image, records, sizes, "brand", "GEOPOLITIC", (104, 49, 350, 82), colour=ACCENT, size=33, minimum=28, bold=True)
    _type(image, records, sizes, "episode", slide.episode_id, (379, 56, 467, 82), colour=ACCENT, size=19, minimum=16, bold=True)
    _type(image, records, sizes, "date", "SATURDAY, 3 OCTOBER 2026", (493, 56, 909, 83), colour=ACCENT, size=18, minimum=16)
    _type(image, records, sizes, "counter", "05/20", (941, 45, 1038, 84), colour=ACCENT, size=34, minimum=28, bold=True)
    draw.line((42, 99, 1038, 99), fill=ACCENT, width=1)
    _type(image, records, sizes, "footer", MOTTO, (363, 1036, 1038, 1050), serif=True, size=12, minimum=11)
    draw.line((42, 1043, 338, 1043), fill=ACCENT, width=1)
    validate_route_mask(routes, records)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, "PNG")
    with Image.open(destination) as result:
        result.verify()
    return {"state": REVIEW, "slide": asdict(slide), "dimensions": [1080, 1080], "format": "PNG",
        "output": str(destination), "output_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "source_asset": str(asset), "source_asset_sha256": digest,
        "canonical_portrait": str(portrait_path), "portrait_sha256": hashlib.sha256(portrait_path.read_bytes()).hexdigest(),
        "provider_calls": 0, "new_generation_count": 0, "runtime_reference_dependency": False,
        "development_references": REFERENCES, "accent_hex": slide.accent,
        "geometry": {"hero": HERO, "portrait": PORTRAIT, "headline": HEADLINE, "main_phrase": PHRASE,
                     "takeaway_columns": TAKEAWAYS, "protected_face": FACE, "protected_text": records,
                     "hero_centre_alpha": hero_mask.getpixel((hero.width // 2, hero.height // 2)),
                     "callout_anchors": ANCHORS, "routes": ROUTES, "label_knockout": "glyph strokes + 1px",
                     "opaque_label_cards": 0, "protected_region_collisions": []},
        "typography": sizes, "engraving": ENGRAVING, "ink_process": INK_PROCESS, "screen": SCREEN,
        "print_finish": {"display_pinholes_modulus": 311, "display_pinhole_attenuation": 125,
                         "phrase_edge_variation_px": 2, "phrase_deposition_amplitude": 3},
        "micro_detail": {"semantic_text": [], "layers": ["grid", "ticks", "crosses", "site arcs", "shoulder hatch"]},
        "layer_order": ["paper/grid", "hero engraving", "portrait engraving", "semantic routes", "labels", "headline/phrase/rail", "furniture"],
        "legacy_network_mesh_invoked": False, "legacy_asset_plate_invoked": False,
        "licence_audit": audit, "publication_handoff": handoff,
        "production_publication_allowed": False, "visual_parity": "NOT CLAIMED"}


def write_report(report, directory):
    directory = _confined(Path(directory) / "fusion-report.json", PACKAGE / "report", exists=False).parent
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "fusion-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    body = (f"# Phase C.3 editorial fusion proof\n\n{report['state']}\n\n"
        f"Output: {report['output']}\n\nAccepted art SHA: {report['source_asset_sha256']}\n\n"
        "ZERO new generations and ZERO provider calls. Composition is local and references are development-only.\n\n"
        "Both rasters share grayscale, controlled contrast, dark-edge preservation, paper mapping and a page-phased fine screen. "
        "Portrait geometry uses canonical aspect-preserving crop/scale only. Six glyph-local labels attach to inspected objects; "
        "REMOTE USERS → FIBRE → COMPUTE branches to COOLING, POWER and LAND. These anchors apply to this one raster only.\n\n"
        "JSON records exact anchors, paths, face/copy protection, font sizes, ink parameters and source provenance. "
        "Native Anton glyph sizing replaces stretched display rasters; C.2 remains unchanged.\n\n"
        f"Required credit retained: {report['licence_audit']['attribution_text']}\n\n"
        "Public attribution delivery remains BLOCKED. No claim of visual parity or production acceptance.\n")
    (directory / "fusion-report.md").write_text(body, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readiness", required=True, type=Path)
    parser.add_argument("--asset", type=Path, default=ROOT / control.ACCEPTED_ART)
    parser.add_argument("--acceptance-metadata", type=Path, default=ROOT / control.ACCEPTED_ART.parent / "generation-metadata.json")
    args = parser.parse_args(argv)
    try:
        raw = json.loads(_confined(args.readiness, "output").read_text(encoding="utf-8-sig"))
        if not isinstance(raw, dict) or raw.get("blockers") != []:
            raise ValueError("LIVE_BUILD_READY_REQUIRED")
        readiness = DailyBuildReadinessResult(raw["production_date_sast"], raw["build"], raw["state"], (), raw["manifest"])
        report = compose_fusion(readiness, args.asset, args.acceptance_metadata, ROOT / PACKAGE / "phase3/slide05-phase3.png")
        write_report(report, ROOT / PACKAGE / "report")
        print(json.dumps({k: report[k] for k in ("state", "output", "provider_calls", "new_generation_count")}))
        return 0
    except (ValueError, OSError, KeyError, TypeError, LayoutError) as exc:
        print(json.dumps({"state": "BLOCKED", "error_type": type(exc).__name__, "blocker": str(exc), "new_generation_count": 0}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
