"""Offline R2.2 adaptive-layout and exact-copy material lettering acceptance tests.

Synthetic assets only. Tests never read Drive or generate/publicise art.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import io
import os
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from src.v3_adaptive_layout import AdaptiveLayoutError, LetteringSurface
from src.v3_compositor import PortraitPlacement, R2SlidePlan, R2CompositionError, compose_r2_slide
from test_v3_compositor import synthetic_inputs, png_of


def compose(inputs, plan, **overrides):
    manifest, _, hero, portraits, reference = inputs
    return compose_r2_slide(
        manifest, plan, hero_png=hero, portrait_pngs=portraits,
        ep128_reference_png=reference, **overrides,
    )


def test_left_layout_material_phrase_is_engraved_without_a_card(monkeypatch):
    inputs = synthetic_inputs(monkeypatch, 1)
    default_plan = inputs[1]
    reviewed_surface = LetteringSurface(
        (642, 515, 997, 772),
        material="engraved",
        rotation_degrees=-2,
        reserved_surface_reviewed=True,
    )
    plan = replace(default_plan, arrangement="portrait-left", material_surface=reviewed_surface)
    plain = compose(inputs, replace(plan, material_surface=None))
    composed = compose(inputs, plan)
    assert len(composed.png_bytes) > 0
    assert composed.qc["arrangement"] == "portrait-left"
    assert composed.qc["material_lettering"]["copy_sha256"] == sha256(
        inputs[0]["slides"][0]["main_visual_phrase"].encode("utf-8")
    ).hexdigest()
    assert composed.qc["material_lettering"]["opaque_card_added"] is False
    assert composed.qc["render_integrity_status"] == "RENDER_QC_PENDING"
    assert composed.qc["publication_authorised"] is False
    with Image.open(io.BytesIO(composed.png_bytes)) as final, \
         Image.open(io.BytesIO(plain.png_bytes)) as baseline:
        assert final.size == (1080, 1350)
        # No lettering is allowed to alter the original canonical silhouette.
        assert final.getpixel((345, 615)) == baseline.getpixel((345, 615))
        assert list(final.crop(reviewed_surface.box).getdata()) != list(
            baseline.crop(reviewed_surface.box).getdata())
    target = os.environ.get("R2_ADAPTIVE_PROOF")
    if target:
        filename = Path(target)
        filename.parent.mkdir(parents=True, exist_ok=True)
        filename.write_bytes(composed.png_bytes)


def test_right_layout_validates_lateral_structure_and_integration(monkeypatch):
    inputs = synthetic_inputs(monkeypatch, 1)
    p = inputs[1]
    plan = replace(
        p,
        arrangement="portrait-right",
        placements=(PortraitPlacement("nora", (594, 430, 1008, 978)),),
        material_surface=LetteringSurface(
            (82, 528, 485, 813), material="stamped", rotation_degrees=2,
            reserved_surface_reviewed=True
        ),
    )
    result = compose(inputs, plan)
    assert result.qc["arrangement"] == "portrait-right"
    assert result.qc["material_lettering"]["material"] == "stamped"
    assert result.qc["material_lettering"]["line_count"] >= 1


def test_central_and_dual_layout_modes_are_argument_driven(monkeypatch):
    single = synthetic_inputs(monkeypatch, 1)
    central = replace(
        single[1], arrangement="central-portrait",
        placements=(PortraitPlacement("nora", (290, 437, 790, 978)),),
    )
    assert compose(single, central).qc["arrangement"] == "central-portrait"
    dual = synthetic_inputs(monkeypatch, 2)
    paired = replace(dual[1], arrangement="paired-dialogue")
    result = compose(dual, paired)
    assert result.qc["arrangement"] == "paired-dialogue"
    assert len(result.qc["portrait_sha256"]) == 2


def test_geometry_rejects_cast_mismatch_and_wrong_side(monkeypatch):
    inputs = synthetic_inputs(monkeypatch, 1)
    with pytest.raises(AdaptiveLayoutError, match="right-side"):
        compose(inputs, replace(inputs[1], arrangement="portrait-left",
                                placements=(PortraitPlacement("nora", (610, 440, 1000, 973)),)))
    with pytest.raises(AdaptiveLayoutError, match="two"):
        compose(inputs, replace(inputs[1], arrangement="paired-dialogue"))
    with pytest.raises(AdaptiveLayoutError, match="Unapproved"):
        compose(inputs, replace(inputs[1], arrangement="generic_dashboard"))


def test_material_type_cannot_cross_portrait_or_unreviewed_area(monkeypatch):
    inputs = synthetic_inputs(monkeypatch, 1)
    plan = replace(inputs[1], arrangement="portrait-left")
    with pytest.raises(AdaptiveLayoutError, match="overlap"):
        compose(inputs, replace(plan, material_surface=LetteringSurface(
            (260, 570, 640, 795), reserved_surface_reviewed=True
        )))
    with pytest.raises(AdaptiveLayoutError, match="reviewed"):
        compose(inputs, replace(plan, material_surface=LetteringSurface(
            (642, 515, 997, 772)
        )))
    with pytest.raises(AdaptiveLayoutError, match="crosses"):
        compose(inputs, replace(plan, material_surface=LetteringSurface(
            (6, 510, 997, 777), reserved_surface_reviewed=True
        )))


@pytest.mark.parametrize("angle", [-7, 6])
def test_material_type_excessive_perspective_is_blocked(monkeypatch, angle):
    inputs = synthetic_inputs(monkeypatch, 1)
    plan = replace(inputs[1], arrangement="portrait-left",
                   material_surface=LetteringSurface(
                       (642, 515, 997, 772), rotation_degrees=angle,
                       reserved_surface_reviewed=True
                   ))
    with pytest.raises(AdaptiveLayoutError, match="rotation"):
        compose(inputs, plan)


def test_material_copy_overflow_fails_not_ellipsized(monkeypatch):
    inputs = synthetic_inputs(monkeypatch, 1)
    m, plan, _, _, _ = inputs
    m["slides"][0]["main_visual_phrase"] = "SUPERCALIFRAGILISTICEXPIALIDOCIOUS" * 15
    revised = replace(plan, arrangement="portrait-left",
                      material_surface=LetteringSurface(
                          (642, 515, 997, 772), reserved_surface_reviewed=True
                      ))
    with pytest.raises(AdaptiveLayoutError, match="fit"):
        compose(inputs, revised)


def test_legacy_plan_does_not_gain_material_status_by_accident(monkeypatch):
    inputs = synthetic_inputs(monkeypatch, 1)
    surface = LetteringSurface((642, 515, 997, 772), reserved_surface_reviewed=True)
    with pytest.raises(R2CompositionError, match="explicit"):
        compose(inputs, replace(inputs[1], material_surface=surface))


def test_adaptive_compositor_is_byte_identical_on_repeat(monkeypatch):
    inputs = synthetic_inputs(monkeypatch, 1)
    plan = replace(inputs[1], arrangement="portrait-left",
                   material_surface=LetteringSurface((642, 515, 997, 772),
                                                      reserved_surface_reviewed=True))
    a = compose(inputs, plan)
    b = compose(inputs, plan)
    assert a.png_bytes == b.png_bytes
    assert a.qc["output_png_sha256"] == b.qc["output_png_sha256"]


def test_busy_art_surface_blocks_opaque_plate_workaround(monkeypatch):
    inputs = synthetic_inputs(monkeypatch, 1)
    portrait_plan = replace(
        inputs[1], arrangement="portrait-left",
        material_surface=LetteringSurface((642, 515, 997, 772),
                                           reserved_surface_reviewed=True),
    )
    crowded = Image.new("RGB", (1400, 980), (240, 240, 240))
    d = ImageDraw.Draw(crowded)
    for x in range(0, 1400, 25):
        for y in range(0, 980, 25):
            if ((x // 25) + (y // 25)) % 2 == 0:
                d.rectangle((x, y, x + 24, y + 24), fill=(20, 20, 20))
    manifest, _, _, portraits, reference = inputs
    with pytest.raises(AdaptiveLayoutError, match="too busy"):
        compose_r2_slide(
            manifest, portrait_plan, hero_png=png_of(crowded),
            portrait_pngs=portraits, ep128_reference_png=reference,
        )
