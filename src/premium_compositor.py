"""Phase C.2: one local Ep104/05 hero composition, without any generation provider."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps, ImageStat

from .daily_readiness import DailyBuildReadinessResult, current_production_date
from .episode_manifest_v2 import load_canonical_characters, validate_manifest_v2
from .editorial_primitives import PAPER, INK, LayoutError, font, paper_texture, distressed_text, fit_wrapped

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = Path("output/phase-c2/Ep104/slide-05")
ACCEPTED_ART = Path("output/phase-c1/Ep104/slide-5/albedo-sdxl/ai_horde/context-art.png")
ACCEPTED_SHA256 = "af911721d389f3b6a658d18e3e0ba30f93c48bb041be51a7060bf69255f2288b"
ACCENT = (101, 64, 164)
LABELS = ("REMOTE USERS", "FIBRE", "COMPUTE", "COOLING", "POWER", "LAND")
MOTTO = "The event is factual. The interpretation ideological."
REVIEW = "PHASE C.2 PREMIUM COMPOSITION PROOF READY FOR HUMAN REVIEW"
HERO = (380, 360, 1038, 890)
PORTRAIT = (42, 354, 409, 852)
HEADLINE = (42, 116, 1038, 301)
PHRASE = (42, 747, 455, 885)
TAKEAWAYS = ((42, 916, 350, 997), (385, 916, 688, 997), (723, 916, 1038, 997))
# Label position and endpoint on the physical scene. No generic network overlay.
CALLOUTS = (
    ((531, 365, 782, 397), (487, 459)),
    ((430, 469, 544, 501), (584, 566)),
    ((703, 415, 859, 447), (759, 545)),
    ((871, 529, 1033, 561), (834, 610)),
    ((472, 693, 588, 725), (650, 691)),
    ((879, 805, 984, 837), (1003, 865)),
)


@dataclass(frozen=True)
class PremiumSlide:
    episode_id: str
    production_date_sast: str
    slide_number: int
    total_slides: int
    headline: str
    subheadline: str
    main_visual_phrase: str
    essential_labels: tuple[str, ...]
    takeaway_ideas: tuple[str, ...]
    core_argument: str
    panelist: str
    accent: str
    portrait: str
    crop_box: tuple[int, ...]


def compile_slide(readiness: DailyBuildReadinessResult) -> PremiumSlide:
    today = current_production_date().isoformat()
    if (not isinstance(readiness, DailyBuildReadinessResult) or readiness.build != "READY" or
            readiness.state != "BUILD_READY" or readiness.blockers or readiness.production_date_sast != today):
        raise ValueError("LIVE_BUILD_READY_REQUIRED")
    characters = load_canonical_characters()
    manifest = readiness.manifest
    if validate_manifest_v2(manifest, characters):
        raise ValueError("VALIDATED_MANIFEST_REQUIRED")
    if (manifest["episode_id"] != "Ep104" or manifest["production_date_sast"] != "2026-10-03" or
            manifest["production_date_sast"] != today or manifest["source_rnd_date_sast"] != today):
        raise ValueError("EP104_CURRENT_PRODUCTION_DATE_REQUIRED")
    slide = manifest["slides"][4]
    if (slide["slide_number"] != 5 or slide["panelists"] != ["kai_patel"] or
            slide["pairing_mode"] is not None or slide["central_relationship"] is not None):
        raise ValueError("SINGLE_KAI_SLIDE05_REQUIRED")
    if tuple(slide["essential_labels"]) != LABELS:
        raise ValueError("SIX_INFRASTRUCTURE_LABELS_REQUIRED")
    kai = characters["kai_patel"]
    if kai["accent"] != "#6540A4" or kai["portrait"] != "assets/characters/kai_patel.png":
        raise ValueError("CANONICAL_KAI_CONFIGURATION_REQUIRED")
    return PremiumSlide(manifest["episode_id"], manifest["production_date_sast"], 5, 20,
        slide["headline"], slide["subheadline"], slide["main_visual_phrase"], tuple(slide["essential_labels"]),
        tuple(i["idea"] for i in slide["takeaway_ideas"]), slide["core_argument"], "kai_patel", kai["accent"],
        kai["portrait"], tuple(kai["crop_box"]))


def _confined(path, directory, *, exists=True):
    path = Path(path).resolve()
    if not path.is_relative_to((ROOT / directory).resolve()):
        raise ValueError("ASSET_OR_OUTPUT_PATH_ESCAPE")
    if exists and not path.is_file():
        raise ValueError("REQUIRED_LOCAL_ASSET_MISSING")
    return path


def accepted_asset(path, metadata_path):
    path = _confined(path, "output")
    metadata_path = _confined(metadata_path, "output")
    if metadata_path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("ACCEPTANCE_METADATA_INVALID")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("ACCEPTANCE_METADATA_INVALID")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    screen = metadata.get("agent_visual_screen", {})
    if not isinstance(screen, dict) or not isinstance(metadata.get("model_profile"), dict):
        raise ValueError("ACCEPTANCE_METADATA_INVALID")
    if (digest != ACCEPTED_SHA256 or screen.get("artifact_sha256") != digest or
            screen.get("performed") is not True or screen.get("approved_for_composition") is not True or
            metadata.get("state") != "SUCCEEDED" or metadata.get("episode_id") != "Ep104" or
            metadata.get("slide_number") != 5 or metadata.get("model_profile", {}).get("model_id") != "AlbedoBase XL 3.1"):
        raise ValueError("ACCEPTED_ALBEDO_ART_REQUIRED")
    audit, handoff = metadata.get("licence_audit", {}), metadata.get("publication_handoff", {})
    if not isinstance(audit, dict) or not isinstance(handoff, dict) or not isinstance(audit.get("use"), dict):
        raise ValueError("ATTRIBUTION_AUDIT_REQUIRED")
    if (audit.get("publication_attribution_required") is not True or not audit.get("attribution_text") or
            audit.get("creator") != "albedobond" or not audit.get("permission_source") or
            audit.get("use", {}).get("context") != "INTERNAL_BENCHMARK" or
            handoff.get("state") != "BLOCKED" or handoff.get("publication_attribution_required") is not True or
            handoff.get("creator") != audit["creator"] or
            handoff.get("required_attribution_text") != audit["attribution_text"] or
            handoff.get("source") != audit["permission_source"]):
        raise ValueError("ATTRIBUTION_AUDIT_REQUIRED")
    with Image.open(path) as image:
        if image.format != "PNG" or image.size != (1024, 1024) or getattr(image, "n_frames", 1) != 1:
            raise ValueError("ACCEPTED_IMAGE_QA_FAILED")
        image.load()
        if max(ImageStat.Stat(image.convert("RGB")).var) <= 0:
            raise ValueError("ACCEPTED_IMAGE_QA_FAILED")
    return path, digest, audit, handoff


def _edge_mask(size, *, left=0, top=0, right=0, bottom=0):
    w, h = size
    # Only selected perimeter pixels feather; the centre retains full strength.
    xs = [min(1, x / max(1, left), (w - 1 - x) / max(1, right)) if left and right else
          min(1, x / left) if left else min(1, (w - 1 - x) / right) if right else 1 for x in range(w)]
    ys = [min(1, y / max(1, top), (h - 1 - y) / max(1, bottom)) if top and bottom else
          min(1, y / top) if top else min(1, (h - 1 - y) / bottom) if bottom else 1 for y in range(h)]
    mask = Image.new("L", size)
    mask.putdata([round(255 * min(x, y)) for y in ys for x in xs])
    return mask


def prepare_hero_art(path, size):
    """Aspect-preserving cover, opaque ink/paper tones, perimeter feather only."""
    with Image.open(path) as source:
        covered = ImageOps.fit(source.convert("RGB"), size, Image.Resampling.LANCZOS)
    tones = ImageOps.autocontrast(ImageOps.grayscale(covered), cutoff=0.4)
    tones = ImageEnhance.Contrast(tones).enhance(1.18)
    return ImageOps.colorize(tones, black=INK, white=PAPER), _edge_mask(size, left=24, top=20, right=10, bottom=28)


def prepare_portrait(path, crop, size):
    with Image.open(path) as source:
        if not (0 <= crop[0] < crop[2] <= source.width and 0 <= crop[1] < crop[3] <= source.height):
            raise ValueError("CANONICAL_PORTRAIT_CROP_INVALID")
        # The canonical PNG contains a printed perimeter. Crop its top border,
        # rather than introducing a portrait card into the continuous hero field.
        crop = (crop[0], max(crop[1], round(source.height * 0.03)), crop[2], crop[3])
        # Crop/cover preserves facial proportions; no synthesis or geometry warp.
        portrait = ImageOps.fit(source.convert("RGB").crop(crop), size, Image.Resampling.LANCZOS,
                               centering=(0.52, 0.48))
    edges = _edge_mask(size, left=8, top=6, right=30, bottom=70)
    # Release near-paper areas so the portrait shares the hero's paper field.
    ink_mask = ImageOps.grayscale(portrait).point(lambda value: min(255, max(0, (245 - value) * 4)))
    from PIL import ImageChops
    return portrait, ImageChops.multiply(edges, ink_mask)


def _intersects(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def _record(records, name, text, box):
    if not (36 <= box[0] < box[2] <= 1044 and 36 <= box[1] < box[3] <= 1050):
        raise ValueError("TEXT_CLIPPING_OR_SAFE_MARGIN_VIOLATION: " + name)
    if any(_intersects(box, row["bounds"]) for row in records):
        raise ValueError("PROTECTED_TEXT_COLLISION: " + name)
    records.append({"name": name, "text": text, "bounds": list(box)})


def _type(img, records, name, text, box, *, colour=INK, size=24, minimum=18, lines=1, serif=False, bold=False):
    draw = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    fnt, wrapped = fit_wrapped(draw, text, x1 - x0, lines, size, minimum,
        max_height=y1 - y0, spacing=3, label=name, serif=serif, bold=bold, condensed=not serif)
    line = "\n".join(wrapped)
    measured = draw.multiline_textbbox((0, 0), line, font=fnt, spacing=3)
    xy = (x0 - measured[0], y0 - measured[1])
    actual = draw.multiline_textbbox(xy, line, font=fnt, spacing=3)
    if actual[2] > x1 or actual[3] > y1:
        raise ValueError("TEXT_CLIPPING: " + name)
    _record(records, name, text, actual)
    draw.multiline_text(xy, line, font=fnt, spacing=3, fill=colour)


def _display_type(img, records, name, text, box, colour, seed, *, font_size=130):
    """Condensed distressed display typography; transformation applies to glyphs only."""
    fnt = font(font_size, bold=True, condensed=True)
    measured = ImageDraw.Draw(img).textbbox((0, 0), text, font=fnt)
    width, height = measured[2] - measured[0], measured[3] - measured[1]
    target_w, target_h = box[2] - box[0], box[3] - box[1]
    if width <= 0 or target_w / width < 0.32:
        raise ValueError("DISPLAY_COPY_TOO_LONG: " + name)
    scratch = Image.new("RGBA", (width + 8, height + 8))
    distressed_text(scratch, (4 - measured[0], 4 - measured[1]), text, fnt, colour, seed=seed)
    ink = scratch.crop(scratch.getbbox()).resize((target_w, target_h), Image.Resampling.LANCZOS)
    _record(records, name, text, box)
    img.paste(ink, box[:2], ink)


def compose_premium(readiness, asset_path, metadata_path, destination):
    slide = compile_slide(readiness)
    asset, digest, audit, handoff = accepted_asset(asset_path, metadata_path)
    portrait_path = _confined(ROOT / slide.portrait, "assets/characters")
    destination = _confined(destination, PACKAGE / "premium", exists=False)
    if destination.suffix.lower() != ".png":
        raise ValueError("PNG_OUTPUT_REQUIRED")
    image = Image.new("RGB", (1080, 1080), PAPER)
    paper_texture(image)
    grid = Image.new("RGBA", image.size)
    gd = ImageDraw.Draw(grid)
    for x in range(42, 1040, 48):
        gd.line((x, 346, x, 901), fill=(*ACCENT, 12))
    for y in range(346, 902, 48):
        gd.line((42, y, 1038, y), fill=(*ACCENT, 12))
    image.paste(grid, (0, 0), grid)
    hero, hero_mask = prepare_hero_art(asset, (HERO[2] - HERO[0], HERO[3] - HERO[1]))
    image.paste(hero, HERO[:2], hero_mask)
    portrait, portrait_mask = prepare_portrait(portrait_path, slide.crop_box,
                                              (PORTRAIT[2] - PORTRAIT[0], PORTRAIT[3] - PORTRAIT[1]))
    image.paste(portrait, PORTRAIT[:2], portrait_mask)
    records = []
    draw = ImageDraw.Draw(image)
    draw.rectangle((24, 24, 1056, 1056), outline=ACCENT, width=2)
    draw.rectangle((42, 40, 92, 87), outline=ACCENT, width=2)
    _type(image, records, "masthead_badge", "AI", (49, 46, 89, 80), colour=ACCENT, size=33, bold=True)
    _type(image, records, "masthead_brand", "GEOPOLITIC", (104, 49, 350, 82), colour=ACCENT, size=33, bold=True)
    _type(image, records, "episode", slide.episode_id, (379, 56, 467, 82), colour=ACCENT, size=19, bold=True)
    day = date.fromisoformat(slide.production_date_sast)
    full_date = f"{day.strftime('%A').upper()}, {day.day} {day.strftime('%B').upper()} {day.year}"
    _type(image, records, "date", full_date, (493, 56, 909, 83), colour=ACCENT, size=18, minimum=16)
    _type(image, records, "counter", f"{slide.slide_number:02d}/{slide.total_slides}",
          (941, 45, 1038, 84), colour=ACCENT, size=34, minimum=28, bold=True)
    draw.line((42, 99, 1038, 99), fill=ACCENT, width=2)
    for x in (364, 926):
        draw.line((x, 42, x, 87), fill=ACCENT, width=1)
    words = slide.headline.split()
    split = next((i for i, word in enumerate(words) if "," in word), len(words) // 2)
    if split < 1 or split >= len(words):
        raise ValueError("HEADLINE_HIERARCHY_UNAVAILABLE")
    _display_type(image, records, "headline_black", " ".join(words[:split]), (42, 116, 1038, 200), INK, 104)
    _display_type(image, records, "headline_accent", " ".join(words[split:]), (42, 210, 1038, 301), ACCENT, 105)
    _type(image, records, "subheadline", slide.subheadline, (42, 313, 1038, 344), serif=True, size=23, minimum=19)
    draw = ImageDraw.Draw(image)
    anchors = []
    for index, (label, (box, endpoint)) in enumerate(zip(slide.essential_labels, CALLOUTS)):
        # Local paper-backed captions protect type, leaving nearly all hero detail visible.
        draw.rectangle(box, fill=PAPER)
        _type(image, records, "label_" + str(index), label, (box[0] + 6, box[1] + 6, box[2] - 6, box[3] - 4),
              colour=ACCENT, size=24, minimum=18, bold=True)
        start = ((box[0] + box[2]) // 2, box[3] + 2 if endpoint[1] > box[3] else box[1] - 2)
        elbow = (start[0], endpoint[1])
        draw.line((start, elbow, endpoint), fill=ACCENT, width=2)
        draw.ellipse((endpoint[0] - 3, endpoint[1] - 3, endpoint[0] + 3, endpoint[1] + 3), fill=ACCENT)
        anchors.append({"label": label, "caption_bounds": list(box), "start": list(start), "endpoint": list(endpoint)})
    draw.rectangle(PHRASE, fill=ACCENT)
    phrase_words = slide.main_visual_phrase.split()
    cut = len(phrase_words) // 2
    if cut < 1:
        raise ValueError("MAIN_PHRASE_HIERARCHY_UNAVAILABLE")
    _display_type(image, records, "phrase_first", " ".join(phrase_words[:cut]), (55, 761, 440, 811), PAPER, 106, font_size=110)
    _display_type(image, records, "phrase_second", " ".join(phrase_words[cut:]), (55, 819, 440, 872), PAPER, 107, font_size=110)
    draw.line((42, 904, 1038, 904), fill=ACCENT, width=2)
    for index, (idea, box) in enumerate(zip(slide.takeaway_ideas, TAKEAWAYS), 1):
        _type(image, records, f"takeaway_number_{index}", f"{index:02d}", (box[0], 921, box[0] + 96, 984),
              colour=ACCENT, size=72, minimum=60, bold=True)
        _type(image, records, f"takeaway_idea_{index}", idea, (box[0] + 104, 928, box[2], 992),
              size=25, minimum=21, lines=2, bold=True)
        draw.line((box[0] + 104, 994, box[0] + 143, 994), fill=ACCENT, width=3)
    for x in (366, 706):
        draw.line((x, 919, x, 996), fill=ACCENT, width=1)
    _type(image, records, "core_argument", slide.core_argument, (42, 1009, 1038, 1029),
          serif=True, size=16, minimum=14)
    _type(image, records, "footer", MOTTO, (363, 1036, 1038, 1050), serif=True, size=12, minimum=11)
    draw.line((42, 1043, 338, 1043), fill=ACCENT, width=1)
    geometry = {
        "hero": list(HERO), "portrait": list(PORTRAIT), "headline": list(HEADLINE),
        "main_phrase": list(PHRASE), "takeaway_columns": [list(b) for b in TAKEAWAYS],
        "hero_area": (HERO[2] - HERO[0]) * (HERO[3] - HERO[1]),
        "old_plate_area": 470 * 330, "portrait_area": (PORTRAIT[2] - PORTRAIT[0]) * (PORTRAIT[3] - PORTRAIT[1]),
        "old_portrait_area": 335 * 360,
        "hero_visual_field_fraction": ((HERO[2] - HERO[0]) * (HERO[3] - HERO[1])) / (996 * 555),
        "hero_centre_alpha": hero_mask.getpixel((hero.width // 2, hero.height // 2)),
        "callout_anchors": anchors, "protected_text": records,
        "protected_text_collisions": [], "opaque_generic_diagram": False,
        "legacy_network_mesh_invoked": False, "legacy_asset_plate_invoked": False,
    }
    for anchor in anchors:
        start, end = anchor["start"], anchor["endpoint"]
        elbow = (start[0], end[1])
        for a, b in ((start, elbow), (elbow, end)):
            line_box = (min(a[0], b[0]) - 1, min(a[1], b[1]) - 1,
                        max(a[0], b[0]) + 2, max(a[1], b[1]) + 2)
            if any(_intersects(line_box, r["bounds"]) for r in records):
                raise ValueError("CALLOUT_CROSSES_PROTECTED_TEXT")
    if geometry["hero_area"] < 2 * geometry["old_plate_area"] or geometry["portrait_area"] < 1.4 * geometry["old_portrait_area"]:
        raise ValueError("PREMIUM_VISUAL_HIERARCHY_UNMET")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, "PNG")
    with Image.open(destination) as result:
        result.verify()
    return {"state": REVIEW, "slide": asdict(slide), "geometry": geometry,
        "output": str(destination), "output_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "dimensions": [1080, 1080], "format": "PNG", "new_generation_count": 0,
        "provider_calls": 0, "runtime_reference_dependency": False,
        "source_asset": str(asset), "source_asset_sha256": digest,
        "canonical_portrait": str(portrait_path), "portrait_sha256": hashlib.sha256(portrait_path.read_bytes()).hexdigest(),
        "licence_audit": audit, "publication_handoff": handoff,
        "production_publication_allowed": False, "visual_parity": "NOT CLAIMED"}


def write_report(report, directory):
    directory = _confined(Path(directory) / "composition-report.json", PACKAGE / "report", exists=False).parent
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "composition-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    body = (f"# Phase C.2 premium composition proof\n\n{report['state']}\n\n"
        f"Output: {report['output']}\n\nSource: {report['source_asset']}\n\n"
        f"ZERO new generations; provider calls: {report['provider_calls']}. Reference is development-only.\n\n"
        "Hero art is opaque ink/paper imagery with perimeter feathering. Canonical Kai uses aspect-preserving crop/scale, "
        "paper release and edge feathering. Code owns all type, six scene callouts, three editorial columns and furniture.\n\n"
        f"Geometry and measured text bounds: see JSON. Hero area: {report['geometry']['hero_area']}px²; "
        f"old plate: {report['geometry']['old_plate_area']}px². No legacy renderer or faint plate path.\n\n"
        f"Credit retained: {report['licence_audit']['attribution_text']}\n\n"
        f"Evidence: {report['licence_audit']['permission_source']}\n\n"
        "Public attribution delivery remains BLOCKED. Human quality review required; visual parity is not claimed.\n")
    (directory / "composition-report.md").write_text(body, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readiness", required=True, type=Path, help="Current validated local readiness JSON; no provider access.")
    parser.add_argument("--asset", type=Path, default=ROOT / ACCEPTED_ART)
    parser.add_argument("--acceptance-metadata", type=Path, default=ROOT / ACCEPTED_ART.parent / "generation-metadata.json")
    args = parser.parse_args(argv)
    try:
        raw = json.loads(_confined(args.readiness, "output").read_text(encoding="utf-8-sig"))
        if raw.get("blockers") != []:
            raise ValueError("LIVE_BUILD_READY_REQUIRED")
        readiness = DailyBuildReadinessResult(raw["production_date_sast"], raw["build"], raw["state"], (), raw["manifest"])
        report = compose_premium(readiness, args.asset, args.acceptance_metadata, ROOT / PACKAGE / "premium/slide05-premium.png")
        write_report(report, ROOT / PACKAGE / "report")
        print(json.dumps({k: report[k] for k in ("state", "output", "new_generation_count", "provider_calls")}))
        return 0
    except (ValueError, OSError, KeyError, TypeError, LayoutError) as exc:
        print(json.dumps({"state": "BLOCKED", "error_type": type(exc).__name__, "blocker": str(exc), "new_generation_count": 0}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
