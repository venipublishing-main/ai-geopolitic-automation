"""Phase C.4: local finish of the accepted Ep104/05 C.3 proof, never live build.

This explicitly dated artifact replay leaves daily readiness and C.3 unchanged.
It accepts only the pinned C.3 raster/core, full manifest, art and Kai identity.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from . import editorial_fusion as fusion, premium_compositor as control
from .editorial_primitives import INK, PAPER, paper_texture
from .episode_manifest_v2 import load_canonical_characters, validate_manifest_v2

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = Path("output/phase-c4/Ep104/slide-05")
C3_ART = fusion.PACKAGE / "phase3/slide05-phase3.png"
C3_REPORT = fusion.PACKAGE / "report/fusion-report.json"
CONTROL_SHA256 = "530787d58f9dfd1074ccf89858e610567f01c6d4bf9e73d372b8faf3c0a76672"
CORE_SHA256 = "2f4aadf41cfb4151923a10303191a671b801e2a3a58e7daee8742a1966a73692"
MANIFEST_SHA256 = "955c5aad9d28e044f7454032cd811f39bc7eb5fa55798d87e5384b6a6f2e405d"
PORTRAIT_SHA256 = "bea8bcaf13c94316852b8ee8989540d31e65822d12d83b33465aa01c035ccc48"
CORE_FIELDS = ("state", "slide", "output_sha256", "source_asset_sha256", "portrait_sha256", "accent_hex", "geometry", "typography")
REVIEW = "PHASE C.4 FINAL FIDELITY PROOF READY FOR HUMAN REVIEW"
ACCENT = fusion.ACCENT
ROUTE_STYLE = {"trunk_width": 2, "branch_width": 1, "leader_width": 1,
               "arrow_length": 7, "terminal_radius": 4, "halo_expansion": 1, "halo_release": .70}
# Inspected physical surfaces on this fixed campus, not an object detector.
# Local directions/densities reflect different forms rather than a global filter.
ZONES = (
    {"name": "front_facade", "polygon": ((399, 635), (777, 769), (777, 851), (401, 685)),
     "tint_alpha": 100, "edge_gain": .42, "pitch": 6, "slope": 0, "hatch_alpha": 38, "stipple_pitch": 13},
    {"name": "compute", "polygon": ((744, 552), (830, 575), (875, 633), (824, 663), (746, 613)),
     "tint_alpha": 116, "edge_gain": .30, "pitch": 5, "slope": 1, "hatch_alpha": 33, "stipple_pitch": 11},
    {"name": "cooling", "polygon": ((571, 497), (618, 483), (665, 508), (668, 552), (620, 566), (577, 539)),
     "tint_alpha": 120, "edge_gain": .34, "pitch": 5, "slope": -1, "hatch_alpha": 31, "stipple_pitch": 13},
    {"name": "power", "polygon": ((918, 388), (983, 386), (1023, 410), (1002, 443), (947, 427)),
     "tint_alpha": 110, "edge_gain": .40, "pitch": 4, "slope": 2, "hatch_alpha": 36, "stipple_pitch": 9},
    {"name": "land", "polygon": ((796, 848), (915, 767), (945, 791), (869, 874)),
     "tint_alpha": 36, "edge_gain": .10, "pitch": 10, "slope": -2, "hatch_alpha": 19, "stipple_pitch": 17},
)
PIPES = (((453, 608), (562, 568), (655, 535)),)
DELTA_REGIONS = {"hero_surface": (500, 570, 850, 735), "accent_systems": (570, 495, 880, 660),
                 "portrait_hero_transition": (380, 650, 459, 743), "technical_microdetail": (460, 890, 1036, 903)}


def json_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _confined(path, directory, *, exists=True):
    path = Path(path).resolve()
    if not path.is_relative_to((ROOT / directory).resolve()):
        raise ValueError("ASSET_OR_OUTPUT_PATH_ESCAPE")
    if exists and not path.is_file():
        raise ValueError("REQUIRED_LOCAL_ASSET_MISSING")
    return path


def read_json(path):
    path = _confined(path, "output")
    if path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("PROOF_METADATA_TOO_LARGE")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("PROOF_METADATA_INVALID")
    return data


def validate_baseline(snapshot_path, baseline_path, report_path, asset_path, metadata_path):
    """Validate an accepted dated artifact; never assert today's BUILD_READY."""
    snapshot, report = read_json(snapshot_path), read_json(report_path)
    if snapshot.get("blockers") != [] or snapshot.get("build") != "READY" or snapshot.get("state") != "BUILD_READY":
        raise ValueError("ACCEPTED_EP104_SNAPSHOT_REQUIRED")
    characters = load_canonical_characters()
    manifest = snapshot.get("manifest")
    if validate_manifest_v2(manifest, characters):
        raise ValueError("VALIDATED_MANIFEST_REQUIRED")
    if (json_digest(manifest) != MANIFEST_SHA256 or manifest["episode_id"] != "Ep104" or
            manifest["production_date_sast"] != "2026-10-03" or manifest["source_rnd_date_sast"] != "2026-10-03" or
            snapshot.get("production_date_sast") != "2026-10-03"):
        raise ValueError("ACCEPTED_EP104_MANIFEST_REQUIRED")
    if json_digest({k: report.get(k) for k in CORE_FIELDS}) != CORE_SHA256:
        raise ValueError("ACCEPTED_C3_CORE_REQUIRED")
    baseline = _confined(baseline_path, "output")
    if hashlib.sha256(baseline.read_bytes()).hexdigest() != CONTROL_SHA256 or report.get("output_sha256") != CONTROL_SHA256:
        raise ValueError("ACCEPTED_C3_RASTER_REQUIRED")
    asset, digest, audit, handoff = control.accepted_asset(asset_path, metadata_path)
    portrait = _confined(ROOT / "assets/characters/kai_patel.png", "assets/characters")
    if hashlib.sha256(portrait.read_bytes()).hexdigest() != PORTRAIT_SHA256:
        raise ValueError("CANONICAL_KAI_SOURCE_REQUIRED")
    slide, kai = manifest["slides"][4], characters["kai_patel"]
    spec = report["slide"]
    if (report["state"] != fusion.REVIEW or report["source_asset_sha256"] != digest or
            report["portrait_sha256"] != PORTRAIT_SHA256 or report["accent_hex"] != "#6540A4" or
            slide["panelists"] != ["kai_patel"] or slide["pairing_mode"] is not None or
            tuple(slide["essential_labels"]) != fusion.LABELS or kai["accent"] != "#6540A4" or
            kai["portrait"] != "assets/characters/kai_patel.png" or tuple(spec["crop_box"]) != tuple(kai["crop_box"])):
        raise ValueError("ACCEPTED_KAI_SLIDE05_REQUIRED")
    for key in ("headline", "subheadline", "main_visual_phrase", "core_argument", "essential_labels"):
        if spec[key] != slide[key]:
            raise ValueError("C3_MANIFEST_COPY_MISMATCH")
    if spec["takeaway_ideas"] != [r["idea"] for r in slide["takeaway_ideas"]]:
        raise ValueError("C3_MANIFEST_COPY_MISMATCH")
    with Image.open(baseline) as image:
        if image.format != "PNG" or image.size != (1080, 1080) or getattr(image, "n_frames", 1) != 1:
            raise ValueError("C3_IMAGE_QA_FAILED")
        image.verify()
    fusion.validate_route_mask(fusion.route_mask(), report["geometry"]["protected_text"])
    return baseline, asset, portrait, report, audit, handoff


def allowed_finish_mask(records):
    mask = Image.new("L", (1080, 1080))
    draw = ImageDraw.Draw(mask)
    draw.rectangle((36, 103, 1044, 1003), fill=255)
    for box in [fusion.FACE] + [r["bounds"] for r in records]:
        draw.rectangle((box[0] - 2, box[1] - 2, box[2] + 2, box[3] + 2), fill=0)
    return mask


def scene_under_routes(asset, portrait, crop):
    """Rebuild only C.3's pre-route scene from its unchanged pure helpers."""
    scene = Image.new("RGB", (1080, 1080), PAPER)
    paper_texture(scene)
    micro = fusion.micro_detail_layer()
    scene.paste(micro, (0, 0), micro)
    hero, hero_mask, kai, kai_mask = fusion.prepare_sources(asset, portrait, crop)
    scene.paste(hero, fusion.HERO[:2], hero_mask)
    scene.paste(kai, fusion.PORTRAIT[:2], kai_mask)
    scene.paste(micro, (0, 0), micro)
    return scene


def local_surface_finish(image, allowed):
    """Local form-specific engraving and muted print separation, no global wash."""
    gray = ImageOps.grayscale(image)
    edges = ImageChops.subtract(gray.filter(ImageFilter.GaussianBlur(.85)), gray)
    gpx, epx, pixels = gray.load(), edges.load(), image.load()
    for zone in ZONES:
        mask = Image.new("L", image.size)
        ImageDraw.Draw(mask).polygon(zone["polygon"], fill=255)
        mask = ImageChops.multiply(mask, allowed)
        bounds = mask.getbbox()
        if not bounds:
            continue
        active = mask.load()
        for y in range(bounds[1], bounds[3]):
            for x in range(bounds[0], bounds[2]):
                if not active[x, y]:
                    continue
                value = gpx[x, y]
                pixel = list(pixels[x, y])
                edge = min(26, round(epx[x, y] * zone["edge_gain"]))
                pixel = [max(INK[i], c - edge) for i, c in enumerate(pixel)]
                # Preserve dark structure and paper highlights; only midtone
                # object surfaces receive an accent-derived print separation.
                if 78 < value < 220:
                    alpha = zone["tint_alpha"] + ((x * 13 + y * 7) % 9 - 4)
                    pixel = [round((c * (255 - alpha) + ACCENT[i] * alpha) / 255) for i, c in enumerate(pixel)]
                    if (x + zone["slope"] * y) % zone["pitch"] == 0:
                        pixel = [round((c * (255 - zone["hatch_alpha"]) + INK[i] * zone["hatch_alpha"]) / 255) for i, c in enumerate(pixel)]
                if 110 < value < 227 and x % zone["stipple_pitch"] == 0 and (y + x // zone["stipple_pitch"]) % zone["stipple_pitch"] == 0:
                    pixel = [max(INK[i], c - 13) for i, c in enumerate(pixel)]
                pixels[x, y] = tuple(pixel)
    # Far background only: a quiet paper release, without photographic blur.
    release = Image.new("L", image.size)
    ImageDraw.Draw(release).polygon(((770, 360), (860, 360), (912, 413), (855, 436), (776, 411)), fill=12)
    image.paste(PAPER, (0, 0), ImageChops.multiply(release, allowed))


def recover_canonical_pigment(image, portrait_path, crop, allowed):
    """Recover only existing canonical purple pixels outside face and copy."""
    original, alpha = control.prepare_portrait(portrait_path, crop, (367, 498))
    pigment = Image.new("L", image.size)
    px, local_alpha, pp = original.load(), alpha.load(), pigment.load()
    for y in range(original.height):
        for x in range(original.width):
            r, g, b = px[x, y]
            if b > r + 22 and r > g + 18:
                pp[x + fusion.PORTRAIT[0], y + fusion.PORTRAIT[1]] = round(local_alpha[x, y] * .68)
    pigment = ImageChops.multiply(pigment, allowed)
    image.paste(ACCENT, (0, 0), pigment)


def refined_route_mask():
    mask = Image.new("L", (1080, 1080))
    draw = ImageDraw.Draw(mask)
    for index, route in enumerate(fusion.ROUTES):
        points = route["points"]
        width = ROUTE_STYLE["trunk_width"] if index < 2 else ROUTE_STYLE["branch_width"]
        draw.line(points, fill=255, width=width, joint="curve")
        a, b = points[-2:]
        angle = math.atan2(b[1] - a[1], b[0] - a[0])
        wings = [(round(b[0] - ROUTE_STYLE["arrow_length"] * math.cos(angle + offset)),
                  round(b[1] - ROUTE_STYLE["arrow_length"] * math.sin(angle + offset))) for offset in (-.42, .42)]
        draw.line((wings[0], b, wings[1]), fill=255, width=1)
    for anchor in fusion.ANCHORS.values():
        draw.line(anchor["leader"], fill=255, width=ROUTE_STYLE["leader_width"])
        x, y = anchor["point"]
        radius = ROUTE_STYLE["terminal_radius"]
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=255, width=1)
        draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=255)
    return mask


def micro_finish_layer():
    """Graphical finish only. No generated text, measured values or fake facts."""
    layer = Image.new("RGBA", (1080, 1080))
    draw = ImageDraw.Draw(layer)
    for x in range(465, 1037, 12):
        draw.line((x, 897, x, 890 if x % 36 == 0 else 894), fill=(*ACCENT, 68))
    for y in range(356, 899, 24):
        draw.line((1034, y, 1038, y), fill=(*ACCENT, 42))
    for inset in (0, 7, 15):
        draw.arc((792 - inset, 756 - inset, 958 + inset, 873 + inset), 35, 112, fill=(*ACCENT, 50))
    for label in ("COMPUTE", "COOLING", "POWER"):
        x, y = fusion.ANCHORS[label]["point"]
        draw.line((x - 9, y - 7, x - 9, y - 11, x + 4, y - 11), fill=(*ACCENT, 160), width=1)
    for y in range(660, 741, 5):
        draw.line((383, y, 449, y - 27), fill=(*ACCENT, 63))
    draw.line((385, 687, 385, 728, 396, 728), fill=(*ACCENT, 130), width=1)
    for x, y in ((408, 348), (798, 348), (1036, 744)):
        draw.line((x - 5, y, x + 5, y), fill=(*ACCENT, 92))
        draw.line((x, y - 4, x, y + 4), fill=(*ACCENT, 92))
    # Thin registration fragments align headline, phrase and rail; no new copy.
    draw.line((952, 203, 1032, 203), fill=(*ACCENT, 44), width=1)
    for x in (52, 395, 733):
        for offset in range(0, 35, 7):
            draw.line((x + offset, 992, x + offset + 8, 996), fill=(*ACCENT, 42))
    for x in range(56, 442, 3):
        draw.point((x, 750 + x % 3), fill=(*PAPER, 65))
        draw.point((x, 881 - x % 2), fill=(*PAPER, 62))
    return layer


def coverage(image):
    pixels = image.crop(fusion.HERO).getdata()
    accent = black = 0
    for r, g, b in pixels:
        accent += b > r + 25 and r > g + 15
        black += max(r, g, b) < 130 and max(r, g, b) - min(r, g, b) < 20
    return {"accent_pixels": accent, "neutral_dark_pixels": black,
            "region": list(fusion.HERO), "purpose": "mark-language sanity check, not beauty"}


def finish_proof(snapshot_path, baseline_path, report_path, asset_path, metadata_path, destination):
    baseline, asset, portrait, c3, audit, handoff = validate_baseline(snapshot_path, baseline_path, report_path, asset_path, metadata_path)
    destination = _confined(destination, PACKAGE / "phase4", exists=False)
    if destination in {baseline, asset, portrait, Path(snapshot_path).resolve(), Path(report_path).resolve(), Path(metadata_path).resolve()}:
        raise ValueError("OUTPUT_SOURCE_COLLISION")
    if destination.suffix.lower() != ".png":
        raise ValueError("PNG_OUTPUT_REQUIRED")
    with Image.open(baseline) as source:
        original = source.convert("RGB")
    image = original.copy()
    records = c3["geometry"]["protected_text"]
    allowed = allowed_finish_mask(records)
    scene = scene_under_routes(asset, portrait, c3["slide"]["crop_box"])
    restore = ImageChops.multiply(fusion.route_mask().filter(ImageFilter.MaxFilter(3)), allowed)
    image.paste(scene, (0, 0), restore)
    local_surface_finish(image, allowed)
    recover_canonical_pigment(image, portrait, c3["slide"]["crop_box"], allowed)
    micro = micro_finish_layer()
    image.paste(micro.convert("RGB"), (0, 0), ImageChops.multiply(micro.getchannel("A"), allowed))
    pipes = Image.new("L", image.size)
    for points in PIPES:
        ImageDraw.Draw(pipes).line(points, fill=190, width=2)
    fusion.validate_route_mask(pipes, records)
    image.paste(ACCENT, (0, 0), pipes)
    routes = refined_route_mask()
    fusion.validate_route_mask(routes, records)
    # Pale local release gives thin drafting lines visibility without C.3's
    # larger white fringe. Main trunk stays stronger than physical branches.
    halo = routes.filter(ImageFilter.MaxFilter(3)).point(lambda v: round(v * ROUTE_STYLE["halo_release"]))
    image.paste(PAPER, (0, 0), halo)
    image.paste(ACCENT, (0, 0), routes)
    difference = ImageChops.difference(original, image)
    for box in [fusion.FACE] + [r["bounds"] for r in records]:
        if difference.crop(box).getbbox():
            raise ValueError("FINISH_MODIFIED_PROTECTED_REGION")
    before, after = coverage(original), coverage(image)
    if after["accent_pixels"] <= before["accent_pixels"] or after["neutral_dark_pixels"] <= after["accent_pixels"]:
        raise ValueError("MARK_LANGUAGE_SANITY_CHECK_FAILED")
    deltas = {}
    for name, box in DELTA_REGIONS.items():
        delta = difference.crop(box)
        count = sum(max(p) > 6 for p in delta.getdata())
        if count <= delta.width * delta.height * .02:
            raise ValueError("FINISH_REGION_UNCHANGED: " + name)
        deltas[name] = {"bounds": box, "changed_pixels_over_6_levels": count, "region_pixels": delta.width * delta.height}
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, "PNG")
    with Image.open(destination) as result:
        result.verify()
    return {"state": REVIEW, "mode": "ACCEPTED_EP104_ARTIFACT_REPLAY", "live_daily_readiness_claimed": False,
        "slide": deepcopy(c3["slide"]), "dimensions": [1080, 1080], "format": "PNG",
        "output": str(destination), "output_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "c3_control": str(baseline), "c3_control_sha256": CONTROL_SHA256, "c3_core_sha256": CORE_SHA256,
        "manifest_sha256": MANIFEST_SHA256, "source_asset": str(asset), "source_asset_sha256": c3["source_asset_sha256"],
        "canonical_portrait": str(portrait), "portrait_sha256": PORTRAIT_SHA256,
        "new_generation_count": 0, "provider_calls": 0, "runtime_reference_dependency": False,
        "accent_hex": "#6540A4", "geometry": deepcopy(c3["geometry"]), "typography": deepcopy(c3["typography"]),
        "engraving": {"inherited": c3["engraving"], "edge_blur_radius": .85, "max_extra_edge_darkening": 26,
                      "midtone_tint_range": [78, 220], "far_background_paper_release": 12},
        "accent_treatments": {"zones": ZONES, "pipe_traces": PIPES, "pipe_opacity": 190,
                              "canonical_pigment_recovery": .68, "face_skin_colour_change": False},
        "screen": {"inherited": c3["screen"], "local_hatch_and_stipple": ZONES, "midtone_only": True},
        "route_style": ROUTE_STYLE, "protected_face_and_copy_pixels": "UNCHANGED",
        "micro_detail": {"semantic_text": [], "primitives": ["ticks", "registration crosses", "terrain arcs", "object brackets", "shoulder hatch", "rail hatch", "phrase ink loss"],
                         "bridge_bounds": [383, 633, 450, 741], "max_registration_drift_px": 2},
        "raster_delta": deltas, "mark_coverage": {"c3": before, "c4": after},
        "development_references": deepcopy(c3["development_references"]),
        "licence_audit": audit, "publication_handoff": handoff,
        "production_publication_allowed": False, "visual_parity": "NOT CLAIMED"}


def write_report(report, directory):
    directory = _confined(Path(directory) / "fidelity-report.json", PACKAGE / "report", exists=False).parent
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "fidelity-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    text = (f"# Phase C.4 final fidelity proof\n\n{report['state']}\n\n"
        f"Output: {report['output']}\n\nC.3 control SHA: {report['c3_control_sha256']}\n\n"
        "ZERO generations and ZERO provider calls. Local accepted Ep104 artifact replay; no claim of today's BUILD_READY.\n\n"
        "C.3 is unchanged. C.4 adds inspected local print separations, directional hatch/stipple, edge reinforcement, "
        "thinner branch drafting, canonical clothing-pigment recovery and graphical microdetail. Face and all measured copy pixels remain unchanged. "
        "JSON records exact surfaces, styles, anchors, masks, hashes and real raster deltas; no beauty score.\n\n"
        f"Credit retained: {report['licence_audit']['attribution_text']}\n\n"
        "Public attribution delivery remains BLOCKED. Visual parity NOT CLAIMED. Human visual review pending. "
        "This is the final automatic Slide05 optimisation pass. No other panelist, carousel or generalisation run.\n")
    (directory / "fidelity-report.md").write_text(text, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accepted-snapshot", required=True, type=Path)
    parser.add_argument("--control", type=Path, default=ROOT / C3_ART)
    parser.add_argument("--control-report", type=Path, default=ROOT / C3_REPORT)
    parser.add_argument("--asset", type=Path, default=ROOT / control.ACCEPTED_ART)
    parser.add_argument("--acceptance-metadata", type=Path, default=ROOT / control.ACCEPTED_ART.parent / "generation-metadata.json")
    args = parser.parse_args(argv)
    try:
        report = finish_proof(args.accepted_snapshot, args.control, args.control_report, args.asset,
                              args.acceptance_metadata, ROOT / PACKAGE / "phase4/slide05-phase4.png")
        write_report(report, ROOT / PACKAGE / "report")
        print(json.dumps({k: report[k] for k in ("state", "output", "new_generation_count", "provider_calls")}))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "error_type": type(exc).__name__, "blocker": str(exc), "new_generation_count": 0}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
