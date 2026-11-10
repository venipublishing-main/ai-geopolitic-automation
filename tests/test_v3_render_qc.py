"""No-network v3.1 real-PNG QC contract: mandatory human review is external."""
from __future__ import annotations

import io
from hashlib import sha256

import pytest
from PIL import Image

from src.v3_render_qc import (
    HumanRenderInspection, REQUIRED_HUMAN_CHECKS, audit_exported_png,
)
from test_v3_compositor import synthetic_inputs, render


def test_valid_4x5_export_is_pending_visual_review(monkeypatch):
    proof = render(synthetic_inputs(monkeypatch))
    receipt = audit_exported_png(
        proof.png_bytes, kind="carousel", item_number=1, compositor_qc=proof.qc
    )
    assert receipt["expected_dimensions"] == [1080, 1350]
    assert receipt["measured_dimensions"] == [1080, 1350]
    assert receipt["render_integrity_gate"] == "HUMAN_REVIEW_REQUIRED"
    assert receipt["issues"] == []
    assert receipt["publication_authorised"] is False
    assert receipt["manifest_schema_modified"] is False


def test_only_actual_attested_image_can_pass(monkeypatch):
    proof = render(synthetic_inputs(monkeypatch))
    evidence = HumanRenderInspection(
        inspector="synthetic-fixture-review",
        inspected_png_sha256=sha256(proof.png_bytes).hexdigest(),
        visual_evidence_ref="local-test://rendered-image-opened",
        checks={k: True for k in REQUIRED_HUMAN_CHECKS},
    )
    receipt = audit_exported_png(
        proof.png_bytes, kind="carousel", item_number=1,
        compositor_qc=proof.qc, inspection=evidence,
    )
    assert receipt["render_integrity_gate"] == "RENDER_QC_PASS"
    assert receipt["publication_authorised"] is False


def test_attestation_cannot_apply_to_different_image(monkeypatch):
    proof = render(synthetic_inputs(monkeypatch))
    evidence = HumanRenderInspection(
        inspector="fixture",
        inspected_png_sha256="0" * 64,
        visual_evidence_ref="test://opened-image",
        checks={k: True for k in REQUIRED_HUMAN_CHECKS},
    )
    receipt = audit_exported_png(
        proof.png_bytes, kind="carousel", item_number=1,
        compositor_qc=proof.qc, inspection=evidence,
    )
    assert "HUMAN_INSPECTION_EVIDENCE_INVALID" in receipt["issues"]
    assert receipt["render_integrity_gate"] == "RENDER_QC_FAIL"


def test_missing_or_rejected_human_review_never_passes(monkeypatch):
    proof = render(synthetic_inputs(monkeypatch))
    for checks in (
        {"identity": True},
        {**{k: True for k in REQUIRED_HUMAN_CHECKS}, "exact_copy": False},
    ):
        receipt = audit_exported_png(
            proof.png_bytes, kind="carousel", item_number=1, compositor_qc=proof.qc,
            inspection=HumanRenderInspection(
                "reviewer", sha256(proof.png_bytes).hexdigest(), "test://opened", checks
            ),
        )
        assert receipt["render_integrity_gate"] == "RENDER_QC_FAIL"


def test_unrelated_compositor_receipt_is_not_proof(monkeypatch):
    proof = render(synthetic_inputs(monkeypatch))
    result = audit_exported_png(
        proof.png_bytes, kind="carousel", item_number=1,
        compositor_qc={**proof.qc, "output_png_sha256": "1" * 64},
    )
    assert "SOURCE_OUTPUT_HASH_MISMATCH" in result["issues"]
    assert result["render_integrity_gate"] == "RENDER_QC_FAIL"


def test_old_3x4_is_rejected_not_stretched(monkeypatch):
    proof = render(synthetic_inputs(monkeypatch))
    img = Image.new("RGB", (1080, 1440), (240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = audit_exported_png(
        buf.getvalue(), kind="carousel", item_number=1, compositor_qc=proof.qc
    )
    assert "OUTPUT_DIMENSIONS_INVALID" in result["issues"]
    assert result["render_integrity_gate"] == "RENDER_QC_FAIL"


@pytest.mark.parametrize("kind,number", [
    ("carousel", 0), ("carousel", 11), ("reel", 0), ("reel", 7),
])
def test_illegal_item_number_is_a_hard_error(kind, number):
    with pytest.raises(ValueError, match="number"):
        audit_exported_png(b"not a png", kind=kind, item_number=number)


def test_reel_requires_exact_9x16_source_and_proof():
    frame = Image.new("RGB", (1080, 1920), (250, 245, 235))
    buf = io.BytesIO()
    frame.save(buf, format="PNG")
    result = audit_exported_png(buf.getvalue(), kind="reel", item_number=1)
    assert result["expected_dimensions"] == [1080, 1920]
    assert result["measured_dimensions"] == [1080, 1920]
    assert result["render_integrity_gate"] == "RENDER_QC_FAIL"
    assert "SOURCE_COMPOSITOR_RECEIPT_MISSING" in result["issues"]


@pytest.mark.parametrize("bad", [b"", b"this-is-not-png", "not bytes"])
def test_invalid_bytes_never_get_image_approval(bad):
    receipt = audit_exported_png(bad, kind="carousel", item_number=1)
    assert receipt["render_integrity_gate"] == "RENDER_QC_FAIL"
    assert receipt["publication_authorised"] is False
