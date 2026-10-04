"""General D.1 premium INTERNAL preview. No generation or publication path.

Contract zones are planned geometry, not manually inspected image anchors.
Only neutral C.2 portrait preparation and C.3 ink preparation are reused;
their proof layouts/compilers/finishers are never called.
"""
from __future__ import annotations

import hashlib

from PIL import Image, ImageDraw

from .editorial_fusion import prepare_editorial_engraving
from .editorial_primitives import INK, PAPER, hex_rgb, paper_texture
from .premium_compositor import prepare_portrait
from .premium_hero_qa import HeroQA, inspect_hero
from .premium_scene_compiler import ROOT, compile_prompt, compile_scene
from .premium_typography import draw_text
from .scene_contract import SceneContract


def _point(point, box):
    return (round(box[0] + point[0] * (box[2] - box[0])),
            round(box[1] + point[1] * (box[3] - box[1])))


def _ink(image, origin, *, portrait=False):
    return prepare_editorial_engraving(image, contrast=1.06 if portrait else 1.26,
        gamma=1.04 if portrait else 1.12, edge_strength=.22 if portrait else .65, origin=origin)


def _route(draw, points, grammar, colour):
    if len(points) < 2:
        return
    if grammar == "rectilinear gates":
        routed = []
        for a, b in zip(points, points[1:]):
            routed.extend((a, (a[0], b[1]), b))
        draw.line(routed, fill=colour, width=2)
    elif grammar == "contour arcs":
        # Quadratic bend determined from endpoints, never an image inspection.
        for a, b in zip(points, points[1:]):
            control = ((a[0] + b[0]) / 2 + 12, (a[1] + b[1]) / 2 - 10)
            curve = []
            for i in range(13):
                t = i / 12
                curve.append(((1-t)**2*a[0] + 2*(1-t)*t*control[0] + t*t*b[0],
                              (1-t)**2*a[1] + 2*(1-t)*t*control[1] + t*t*b[1]))
            draw.line(curve, fill=colour, width=2)
    else:
        draw.line(points, fill=colour, width=3 if grammar == "asymmetric pressure" else 2)


def render_preview(contract: SceneContract, manifest, hero_path, qa: HeroQA, *, content_evidence=None):
    """Return an internal 1080-square PIL image and honest review metadata.

    The caller must supply the full Manifest again. Recompile prevents modified
    zones, copy, canonical assets or configuration bypassing the compiler.
    This API deliberately cannot issue a production-ready/publication result.
    """
    authoritative = compile_scene(manifest, contract.slide_number)
    if contract.sha256 != authoritative.sha256:
        raise ValueError("CONTRACT_AUTHORITY_MISMATCH")
    repeated = inspect_hero(contract, hero_path, compile_prompt(contract), source_kind=qa.source_kind,
                            content_evidence=content_evidence)
    if qa != repeated or not repeated.mechanical_passed:
        raise ValueError("HERO_QA_REQUIRED_OR_STALE")
    portrait_path = ROOT / contract.portrait.path
    if hashlib.sha256(portrait_path.read_bytes()).hexdigest() != contract.portrait.asset_sha256:
        raise ValueError("CANONICAL_PORTRAIT_CHANGED")
    img = Image.new("RGB", (1080, 1080), PAPER)
    paper_texture(img)
    hero_box = contract.hero_region.pixels()
    art_box = contract.art_region.pixels(hero_box)
    with Image.open(hero_path) as raw:
        # Both prompt conversion and annotation terminals account for this
        # square contain transform. Neither cropping nor stretching is needed.
        art = raw.convert("RGB").resize((art_box[2]-art_box[0], art_box[3]-art_box[1]), Image.Resampling.LANCZOS)
    img.paste(_ink(art, art_box[:2]), art_box[:2])
    pbox = contract.portrait.zone.pixels()
    portrait, mask = prepare_portrait(portrait_path, contract.portrait.crop,
        (pbox[2]-pbox[0], pbox[3]-pbox[1]))
    img.paste(_ink(portrait, pbox[:2], portrait=True), pbox[:2], mask)
    draw = ImageDraw.Draw(img)
    accent = hex_rgb(contract.accent)
    centres = [_point(o.zone.centre, hero_box) for o in contract.semantic_objects]
    if contract.route_grammar == "radial":
        for point in centres[1:]:
            _route(draw, (centres[0], point), contract.shape_language, accent)
    elif contract.route_grammar == "branch":
        for point in centres[1:]:
            _route(draw, (centres[0], point), "rectilinear gates", accent)
    elif contract.route_grammar != "parallel":
        _route(draw, centres + centres[:1] if contract.route_grammar == "closed_loop" else centres,
               contract.shape_language, accent)
    annotation_metadata = []
    for obj, centre in zip(contract.semantic_objects, centres):
        points = [_point(p, hero_box) for p in obj.leader]
        draw.line(points, fill=INK, width=1)
        draw.ellipse((centre[0]-3, centre[1]-3, centre[0]+3, centre[1]+3), fill=accent)
        # Glyph-local paper release keeps exact labels distinct from art.
        box = obj.annotation.zone.pixels(hero_box)
        draw.rectangle(box, fill=PAPER)
        draw_text(draw, obj.annotation, INK, parent=hero_box)
        annotation_metadata.append({"label": obj.label, "planned_terminal": centre,
                                    "object_placement_verified": False})
    # Small marks differ by identity grammar, derived from object terminals.
    for i, (x, y) in enumerate(centres):
        if contract.micro_detail in {"repair nodes", "continuity rings"}:
            draw.ellipse((x-8, y-8, x+8, y+8), outline=accent, width=1)
        elif contract.micro_detail == "ledger strikes":
            draw.line((x-8, y+5, x+8, y-5), fill=accent, width=2)
        else:
            draw.line((x-6, y+8, x+6, y+8), fill=accent, width=1)
    draw_text(draw, contract.headline, accent)
    draw_text(draw, contract.subheadline, INK)
    phrase_box = contract.phrase.zone.pixels()
    if contract.phrase.treatment == "accent_block":
        draw.rectangle(phrase_box, fill=accent)
    elif contract.phrase.treatment == "doctrine_strip":
        draw.line((phrase_box[0], phrase_box[1], phrase_box[2], phrase_box[1]), fill=accent, width=3)
        draw.line((phrase_box[0], phrase_box[3], phrase_box[2], phrase_box[3]), fill=accent, width=1)
    elif contract.phrase.treatment == "hero_integrated_callout":
        draw.rounded_rectangle(phrase_box, radius=10, outline=accent, width=2)
    else:
        draw.line((phrase_box[0], phrase_box[1], phrase_box[0], phrase_box[3]), fill=accent, width=4)
    draw_text(draw, contract.phrase, PAPER if contract.phrase.treatment == "accent_block" else accent)
    for i, takeaway in enumerate(contract.takeaways):
        box = takeaway.zone.pixels()
        if contract.takeaway_arrangement == "three_node_sequence":
            draw.ellipse((box[0], box[1]-13, box[0]+7, box[1]-6), fill=accent)
            if i < 2:
                draw.line((box[0]+10, box[1]-9, box[2]+15, box[1]-9), fill=accent, width=1)
        else:
            draw.line((box[0], box[1], box[2], box[1]), fill=accent, width=2)
        if contract.takeaway_arrangement == "numbered_vertical_rail":
            from .premium_typography import typeface
            draw.text((box[0]+6, box[1]-16), f"{i+1:02d}", font=typeface("label", 12), fill=accent)
        draw_text(draw, takeaway, INK)
    for furniture in contract.furniture:
        draw_text(draw, furniture, accent if furniture.text == contract.panelist_name else INK)
    draw.line((44, 1039, 1036, 1039), fill=accent, width=1)
    return img, {"state": "INTERNAL_PREVIEW_HUMAN_REVIEW_REQUIRED", "contract_sha256": contract.sha256,
        "hero_qa": qa.to_dict(), "annotations": annotation_metadata, "expected_generation_count": 0,
        "production_publication": "BLOCKED_D1", "portrait_source": contract.portrait.path,
        "canonical_portrait_sha256": contract.portrait.asset_sha256}
