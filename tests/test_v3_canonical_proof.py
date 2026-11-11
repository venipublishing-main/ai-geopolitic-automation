"""Offline R2.2c source-pixel invariance and synthesis-geometry checks."""
from __future__ import annotations

from dataclasses import replace

import pytest

from src.v3_adaptive_layout import AdaptiveLayoutError
from src.v3_compositor import PortraitPlacement, compose_r2_slide
from src.v3_render_qc import audit_exported_png
from test_v3_compositor import synthetic_inputs


def test_exact_exported_source_pixels_are_checked_for_single_panelist(monkeypatch):
    m, plan, hero, portraits, ref = synthetic_inputs(monkeypatch, 1)
    result = compose_r2_slide(m, plan, hero_png=hero, portrait_pngs=portraits,
                              ep128_reference_png=ref)
    assert result.qc["opaque_source_pixels_verified"] == {"nora": True}
    receipt = audit_exported_png(result.png_bytes, kind="carousel",
                                 item_number=1, compositor_qc=result.qc)
    assert receipt["render_integrity_gate"] == "HUMAN_REVIEW_REQUIRED"
    broken = {**result.qc, "opaque_source_pixels_verified": {"nora": False}}
    receipt = audit_exported_png(result.png_bytes, kind="carousel",
                                 item_number=1, compositor_qc=broken)
    assert "EXPORTED_CANONICAL_PIXEL_INTEGRITY_UNVERIFIED" in receipt["issues"]


def test_historical_two_panelist_synthesis_ensemble_remains_nonpublishable(monkeypatch):
    m, plan, hero, portraits, ref = synthetic_inputs(monkeypatch, 2)
    paired = replace(plan, arrangement="paired-synthesis",
                     placements=(
                         PortraitPlacement(plan.placements[0].slug, (52, 435, 373, 985)),
                         PortraitPlacement(plan.placements[1].slug, (378, 435, 691, 985)),
                     ))
    proof = compose_r2_slide(m, paired, hero_png=hero,
                             portrait_pngs=portraits, ep128_reference_png=ref)
    assert proof.qc["opaque_source_pixels_verified"] == {
        slug: True for slug in m["slides"][1]["panelists"]
    }
    assert proof.qc["arrangement"] == "paired-synthesis"
    assert proof.qc["publication_authorised"] is False


def test_paired_synthesis_rejects_inadequate_right_art_space(monkeypatch):
    m, plan, hero, portraits, ref = synthetic_inputs(monkeypatch, 2)
    invalid = replace(plan, arrangement="paired-synthesis",
                      placements=(
                          PortraitPlacement(plan.placements[0].slug, (52, 435, 440, 985)),
                          PortraitPlacement(plan.placements[1].slug, (560, 435, 1015, 985)),
                      ))
    with pytest.raises(AdaptiveLayoutError, match="apparatus"):
        compose_r2_slide(m, invalid, hero_png=hero,
                         portrait_pngs=portraits, ep128_reference_png=ref)


def test_wrong_historial_fixture_is_rejected():
    from src.v3_historical_proof import _manifest_from_archive
    with pytest.raises(ValueError, match="Manifest pair"):
        _manifest_from_archive("No actual archive document here.")


def test_real_proof_runner_has_no_publication_or_network_functions():
    from src import v3_historical_proof as proof
    assert hasattr(proof, "render_historical_proofs")
    assert not hasattr(proof, "publish")
    assert not hasattr(proof, "upload")
