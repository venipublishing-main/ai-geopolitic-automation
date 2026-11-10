"""Active v3.1 image-level Render Integrity Gate, separate from Manifest v2.

This checker decodes the actual exported PNG bytes, and cannot promote a
design PASS or successful render into an image PASS. Semantic, pixel identity,
typographic, Ep128-style and continuity judgements require recorded
per-image human inspection. No archive, publishing or provider actions exist.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Mapping

from PIL import Image, UnidentifiedImageError

REQUIRED_HUMAN_CHECKS = (
    "identity",
    "exact_copy",
    "furniture",
    "style_material_integration",
    "batch_continuity",
)
TARGETS = {"carousel": (1080, 1350, 10), "reel": (1080, 1920, 6)}
MAX_EXPORTED_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True)
class HumanRenderInspection:
    """Explicit per-export visual evidence, never inferred from a design gate.

    Each check must be an actual checked image-level judgement, not a prompt
    plan. The inspection references the SHA-256 of the *exported* PNG.
    """
    inspector: str
    inspected_png_sha256: str
    visual_evidence_ref: str
    checks: Mapping[str, bool]


def audit_exported_png(
    exported_png: bytes,
    *,
    kind: str,
    item_number: int,
    compositor_qc: Mapping | None = None,
    inspection: HumanRenderInspection | None = None,
) -> dict:
    """Return an external receipt, keeping Manifest JSON strictly unchanged.

    Machine checks: image format, dimensions, source/QC identity alignment.
    Human checks: actual visible copy, furniture, portrait identity,
    Ep128 + scoped Ep142 aesthetics and batch continuity.
    """
    if kind not in TARGETS:
        raise ValueError("Unsupported v3.1 image type.")
    width, height, total = TARGETS[kind]
    if type(item_number) is not int or not 1 <= item_number <= total:
        raise ValueError("Image number out of range.")
    number = f"{item_number:02d}/{total:02d}"
    issues = []
    digest = sha256(exported_png).hexdigest() if isinstance(exported_png, bytes) else None
    measured_size = None
    png_ok = False
    if not isinstance(exported_png, bytes) or not (0 < len(exported_png) <= MAX_EXPORTED_BYTES):
        issues.append("EXPORT_BYTES_INVALID")
    else:
        try:
            with Image.open(io.BytesIO(exported_png)) as image:
                measured_size = list(image.size)
                png_ok = image.format == "PNG"
                # Force a real data read, not just a file signature/header.
                image.load()
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
            issues.append("EXPORT_PNG_UNREADABLE")
    if not png_ok:
        if "EXPORT_PNG_UNREADABLE" not in issues:
            issues.append("EXPORT_NOT_PNG")
    if measured_size != [width, height]:
        issues.append("OUTPUT_DIMENSIONS_INVALID")

    # A synthesized receipt from a prompt, or from a different output file,
    # is not sufficient evidence of a correct composite.
    if not isinstance(compositor_qc, Mapping):
        issues.append("SOURCE_COMPOSITOR_RECEIPT_MISSING")
    else:
        if compositor_qc.get("output_png_sha256") != digest:
            issues.append("SOURCE_OUTPUT_HASH_MISMATCH")
        if compositor_qc.get("size") != [width, height]:
            issues.append("SOURCE_OUTPUT_DIMENSIONS_MISMATCH")
        if compositor_qc.get("slide_number") != item_number and kind == "carousel":
            issues.append("SOURCE_ITEM_NUMBER_MISMATCH")
        if compositor_qc.get("counter") != number:
            issues.append("SOURCE_COUNTER_MISMATCH")
        if kind == "carousel":
            if (compositor_qc.get("pagination_markers") != 10 or
                    compositor_qc.get("filled_marker_index") != item_number):
                issues.append("SOURCE_PAGINATION_MISMATCH")
        if (not compositor_qc.get("portrait_sha256") or
                compositor_qc.get("footer") !=
                "The event is factual. The interpretation ideological."):
            issues.append("SOURCE_IDENTITY_OR_FOOTER_UNVERIFIED")

    reviewed = False
    if inspection is not None:
        if (not isinstance(inspection, HumanRenderInspection) or
                not inspection.inspector.strip() or
                not inspection.visual_evidence_ref.strip() or
                inspection.inspected_png_sha256 != digest):
            issues.append("HUMAN_INSPECTION_EVIDENCE_INVALID")
        elif (set(inspection.checks) != set(REQUIRED_HUMAN_CHECKS) or
              any(type(v) is not bool for v in inspection.checks.values())):
            issues.append("HUMAN_INSPECTION_INCOMPLETE")
        elif not all(inspection.checks.values()):
            issues.append("HUMAN_INSPECTION_FAILED")
        else:
            reviewed = True

    status = ("RENDER_QC_FAIL" if issues else
              "RENDER_QC_PASS" if reviewed else "HUMAN_REVIEW_REQUIRED")
    return {
        "contract": "v3.1",
        "kind": kind,
        "item": number,
        "expected_dimensions": [width, height],
        "measured_dimensions": measured_size,
        "png_sha256": digest,
        "machine_png_decoded": png_ok,
        "human_inspection_attested": reviewed,
        "render_integrity_gate": status,
        "issues": issues,
        "inspector": inspection.inspector if reviewed else None,
        "visual_evidence_ref": inspection.visual_evidence_ref if reviewed else None,
        "publication_authorised": False,
        "manifest_schema_modified": False,
    }
