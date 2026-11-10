"""R2 isolated synthetic compositor regressions; no Drive, providers or publishing.

These tests use fake PNG bytes with temporarily patched test-only SHA expected
values. Production always uses the pinned original Drive SHA-256 assets.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
from hashlib import sha256

import pytest
from PIL import Image, ImageDraw

from src import v3_canon_assets
from src.v3_canon_assets import CanonMismatch
from src.v3_compositor import (
    HERO_BOX, RAIL_CENTRES, R2CompositionError, R2SlidePlan, PortraitPlacement,
    compose_r2_slide,
)
from src.v3_readiness import V3_MANIFEST_BEGIN, V3_MANIFEST_END
from test_v3_readiness import v3_fixture


def png_of(image):
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def fake_portrait(rgb=(30, 80, 120), *, opaque=False):
    im = Image.new("RGBA", (600, 600), (0, 0, 0, 0 if not opaque else 255))
    d = ImageDraw.Draw(im)
    d.ellipse((70, 15, 530, 520), fill=(*rgb, 255))
    d.rectangle((185, 430, 440, 590), fill=(*rgb, 255))
    return png_of(im)


def fake_hero(*, size=(1400, 980)):
    im = Image.new("RGB", size, (242, 237, 225))
    d = ImageDraw.Draw(im)
    for i in range(20):
        yy = 60 + i * 34
        d.line((60, yy, size[0] - 50, yy - 25), fill=(75, 65, 50), width=2)
    d.ellipse((size[0] // 2, 100, size[0] - 100, size[1] - 100),
              outline=(120, 90, 55), width=10)
    return png_of(im)


def fixture_manifest():
    text = v3_fixture().slide_design
    data = json.loads(text.split(V3_MANIFEST_BEGIN, 1)[1].split(V3_MANIFEST_END, 1)[0])
    # Short, synthetic editorial copy to qualify raster geometry. No factual claims.
    for item in data["slides"]:
        item["headline"] = "WHO WRITES THE RULES?"
        item["subheadline"] = "The terms of the agreement determine future choices."
        item["main_visual_phrase"] = "RIGHTS AND PRACTICE"
        item["essential_labels"] = ["LEGAL STATUS", "ACCESS", "ACCOUNTABILITY"]
    return data


def synthetic_inputs(monkeypatch, slide_number=1):
    manifest = fixture_manifest()
    slide = manifest["slides"][slide_number-1]
    portraits = {}
    for i, slug in enumerate(slide["panelists"]):
        portrait = fake_portrait(rgb=(60 + i * 60, 30 + i * 70, 135))
        portraits[slug] = portrait
        fname = v3_canon_assets.PORTRAIT_CANON[slug][0]
        monkeypatch.setitem(v3_canon_assets.PORTRAIT_CANON, slug,
                            (fname, sha256(portrait).hexdigest()))
    ref = fake_hero(size=(1254, 1254))
    refid = "1u6Fux5vvIJHRzgnnZ_Yrr-TabpZlvQeY"
    monkeypatch.setitem(v3_canon_assets.EP128_VERIFIED_REFERENCES,
                        refid, sha256(ref).hexdigest())
    if len(slide["panelists"]) == 1:
        boxes = [(72, 438, 605, 963)]
    else:
        boxes = [(55, 425, 500, 972), (554, 425, 1000, 972)]
    plan = R2SlidePlan(
        slide_number=slide_number,
        visual_id=f"SYNTHETIC-R2-{slide_number:02d}",
        hero_family=slide["preferred_visual_reasoning_family"],
        placements=tuple(
            PortraitPlacement(slug=slug, box=boxes[i])
            for i, slug in enumerate(slide["panelists"])
        ),
        ep128_reference_id=refid,
        background_human_free_reviewed=True,
    )
    return manifest, plan, fake_hero(), portraits, ref


def render(inputs):
    m, plan, hero, portraits, reference = inputs
    return compose_r2_slide(
        m, plan, hero_png=hero, portrait_pngs=portraits,
        ep128_reference_png=reference,
    )


def test_single_slide_is_exact_3_by_4_with_ten_markers_and_footer(monkeypatch):
    inputs = synthetic_inputs(monkeypatch)
    result = render(inputs)
    with Image.open(io.BytesIO(result.png_bytes)) as img:
        assert img.format == "PNG"
        assert img.mode == "RGB"
        assert img.size == (1080, 1350)
        assert img.getpixel(RAIL_CENTRES[0]) == (51, 107, 163)  # Nora canon accent
        assert img.getpixel(RAIL_CENTRES[1]) != (51, 107, 163)
    preview = os.environ.get("R2_SYNTHETIC_QA_PREVIEW")
    if preview:
        target = Path(preview)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(result.png_bytes)
    qc = result.qc
    assert qc["counter"] == "01/10"
    assert qc["pagination_markers"] == 10
    assert qc["render_integrity_status"] == "RENDER_QC_PENDING"
    assert qc["filled_marker_index"] == 1
    assert qc["footer"] == "The event is factual. The interpretation ideological."
    assert qc["visual_review"] == "REQUIRED"
    assert qc["publication_authorised"] is False
    assert qc["image_generation_performed"] is False
    assert len(qc["portrait_sha256"]) == 1



@pytest.mark.parametrize("slide_number", range(1, 11))
def test_all_ten_slide_roles_and_pagination_positions(monkeypatch, slide_number):
    result = render(synthetic_inputs(monkeypatch, slide_number))
    assert result.qc["slide_number"] == slide_number
    assert result.qc["counter"] == f"{slide_number:02d}/10"
    assert result.qc["filled_marker_index"] == slide_number
    assert result.qc["pagination_markers"] == 10
    assert result.qc["size"] == [1080, 1350]


def test_repeat_execution_is_byte_deterministic(monkeypatch):
    inputs = synthetic_inputs(monkeypatch)
    a = render(inputs)
    b = render(inputs)
    assert a.png_bytes == b.png_bytes
    assert a.qc["output_png_sha256"] == b.qc["output_png_sha256"]


def test_dual_assignments_require_exactly_two_sources(monkeypatch):
    inputs = synthetic_inputs(monkeypatch, slide_number=2)
    m, plan, hero, portraits, ref = inputs
    assert len(plan.placements) == 2
    result = render(inputs)
    assert result.qc["counter"] == "02/10"
    assert len(result.qc["portrait_sha256"]) == 2
    with pytest.raises(R2CompositionError, match="Unassigned or missing"):
        compose_r2_slide(m, plan, hero_png=hero,
                         portrait_pngs={next(iter(portraits)): next(iter(portraits.values()))},
                         ep128_reference_png=ref)


def test_portrait_bytes_must_match_pinned_original_sha(monkeypatch):
    m, plan, hero, portraits, ref = synthetic_inputs(monkeypatch)
    corrupted = dict(portraits)
    corrupted["nora"] = fake_portrait((230, 0, 0))
    with pytest.raises(CanonMismatch, match="Canonical bytes"):
        compose_r2_slide(m, plan, hero_png=hero,
                         portrait_pngs=corrupted, ep128_reference_png=ref)


def test_ep128_requires_exact_hydrated_reference_pixels(monkeypatch):
    m, plan, hero, portraits, ref = synthetic_inputs(monkeypatch)
    with pytest.raises(CanonMismatch, match="does not match"):
        compose_r2_slide(m, plan, hero_png=hero, portrait_pngs=portraits,
                         ep128_reference_png=ref + b"wrong")
    invalid = R2SlidePlan(plan.slide_number, plan.visual_id, plan.hero_family,
                          plan.placements, "not-approved", True)
    with pytest.raises(CanonMismatch, match="not been hydrated"):
        compose_r2_slide(m, invalid, hero_png=hero, portrait_pngs=portraits,
                         ep128_reference_png=ref)


def test_opaque_source_is_rejected_even_if_test_hash_is_modified(monkeypatch):
    m, plan, hero, portraits, ref = synthetic_inputs(monkeypatch)
    opaque = fake_portrait(opaque=True)
    fname = v3_canon_assets.PORTRAIT_CANON["nora"][0]
    monkeypatch.setitem(v3_canon_assets.PORTRAIT_CANON, "nora",
                        (fname, sha256(opaque).hexdigest()))
    with pytest.raises(R2CompositionError, match="transparent cutout"):
        compose_r2_slide(m, plan, hero_png=hero,
                         portrait_pngs={"nora": opaque}, ep128_reference_png=ref)


def test_no_unreviewed_or_generic_background_allowed(monkeypatch):
    m, plan, hero, portraits, ref = synthetic_inputs(monkeypatch)
    not_reviewed = R2SlidePlan(plan.slide_number, plan.visual_id, plan.hero_family,
                               plan.placements, plan.ep128_reference_id, False)
    with pytest.raises(R2CompositionError, match="reviewed"):
        compose_r2_slide(m, not_reviewed, hero_png=hero,
                         portrait_pngs=portraits, ep128_reference_png=ref)
    missing_art = R2SlidePlan(plan.slide_number, "", plan.hero_family,
                              plan.placements, plan.ep128_reference_id, True)
    with pytest.raises(R2CompositionError, match="bespoke"):
        compose_r2_slide(m, missing_art, hero_png=hero,
                         portrait_pngs=portraits, ep128_reference_png=ref)


@pytest.mark.parametrize("box", [
    (0, 438, 605, 950), (72, 438, 1050, 950),
    (72, 180, 605, 950), (72, 438, 605, 1200), (72, 438, 160, 660),
])
def test_portrait_never_crosses_text_safe_zones(monkeypatch, box):
    m, plan, hero, portraits, ref = synthetic_inputs(monkeypatch)
    invalid = R2SlidePlan(plan.slide_number, plan.visual_id, plan.hero_family,
                          (PortraitPlacement("nora", box),),
                          plan.ep128_reference_id, True)
    with pytest.raises(R2CompositionError, match="aperture"):
        compose_r2_slide(m, invalid, hero_png=hero,
                         portrait_pngs=portraits, ep128_reference_png=ref)


def test_hero_wide_aspect_crop_blocks_without_stretch(monkeypatch):
    m, plan, _, portraits, ref = synthetic_inputs(monkeypatch)
    invalid = fake_hero(size=(500, 3000))
    with pytest.raises(R2CompositionError, match="aspect mismatch"):
        compose_r2_slide(m, plan, hero_png=invalid,
                         portrait_pngs=portraits, ep128_reference_png=ref)


def test_no_truncation_of_unfit_editorial_words(monkeypatch):
    m, plan, hero, portraits, ref = synthetic_inputs(monkeypatch)
    m["slides"][0]["headline"] = "X" * 300
    with pytest.raises(R2CompositionError, match="cannot fit"):
        compose_r2_slide(m, plan, hero_png=hero,
                         portrait_pngs=portraits, ep128_reference_png=ref)


def test_exact_manifest_validation_before_composition(monkeypatch):
    m, plan, hero, portraits, ref = synthetic_inputs(monkeypatch)
    m["slides"].pop()
    with pytest.raises(R2CompositionError, match="Manifest"):
        compose_r2_slide(m, plan, hero_png=hero,
                         portrait_pngs=portraits, ep128_reference_png=ref)

def test_foreground_engraving_preserves_canonical_silhouette_pixels(monkeypatch):
    manifest, plan, hero, portraits, reference = synthetic_inputs(monkeypatch)
    base = compose_r2_slide(
        manifest, plan, hero_png=hero, portrait_pngs=portraits,
        ep128_reference_png=reference,
    )
    layer = Image.new("RGBA", (HERO_BOX[2] - HERO_BOX[0], HERO_BOX[3] - HERO_BOX[1]),
                      (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # Cross both the source portrait silhouette and the background.
    d.rectangle((0, 210, layer.width - 1, 280), fill=(190, 15, 20, 230))
    foreground = png_of(layer)
    composed = compose_r2_slide(
        manifest, plan, hero_png=hero, portrait_pngs=portraits,
        ep128_reference_png=reference,
        foreground_layer_png=foreground, foreground_reviewed=True,
    )
    with Image.open(io.BytesIO(base.png_bytes)) as original, \
         Image.open(io.BytesIO(composed.png_bytes)) as layered:
        # Inside synthetic silhouette = unchanged source appearance.
        assert original.getpixel((350, 650)) == layered.getpixel((350, 650))
        # Elsewhere the analytical foreground is deliberately visible.
        assert original.getpixel((900, 650)) != layered.getpixel((900, 650))
    assert composed.qc["foreground_png_sha256"] == sha256(foreground).hexdigest()
    assert composed.qc["foreground_protected_portrait_pixels"] > 0
    assert composed.qc["publication_authorised"] is False


def test_unreviewed_foreground_cannot_be_composited(monkeypatch):
    manifest, plan, hero, portraits, reference = synthetic_inputs(monkeypatch)
    layer = Image.new("RGBA", (984, 599), (0, 0, 0, 0))
    ImageDraw.Draw(layer).line((0, 80, 983, 80), fill=(50, 40, 40, 200), width=3)
    with pytest.raises(R2CompositionError, match="foreground|Foreground"):
        compose_r2_slide(
            manifest, plan, hero_png=hero, portrait_pngs=portraits,
            ep128_reference_png=reference, foreground_layer_png=png_of(layer),
            foreground_reviewed=False,
        )


def test_foreground_stretching_is_forbidden(monkeypatch):
    manifest, plan, hero, portraits, reference = synthetic_inputs(monkeypatch)
    wrong = Image.new("RGBA", (980, 603), (0, 0, 0, 0))
    ImageDraw.Draw(wrong).line((0, 20, 979, 20), fill=(50, 40, 40, 200), width=3)
    with pytest.raises(ValueError, match="exactly match"):
        compose_r2_slide(
            manifest, plan, hero_png=hero, portrait_pngs=portraits,
            ep128_reference_png=reference, foreground_layer_png=png_of(wrong),
            foreground_reviewed=True,
        )
