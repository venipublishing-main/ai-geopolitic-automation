"""D.1 mechanical raster/handshake QA, explicitly separate from visual review.

No OCR, object recognition or face recognition. Existing inspected content-guard
evidence may be carried forward only when its raster SHA matches. It cannot
verify a new contract's semantic placement. Publication remains blocked in D.1.
"""
from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path

from PIL import Image, ImageStat

from .premium_scene_compiler import compile_prompt
from .scene_contract import SceneContract, digest


@dataclass(frozen=True)
class HeroQA:
    contract_sha256: str
    prompt_sha256: str
    raster_sha256: str
    dimensions: tuple[int, int]
    source_kind: str
    mechanical_passed: bool
    blockers: tuple[str, ...]
    content_guard: str
    human_visual_qa: str = "REQUIRED_NOT_PERFORMED"
    semantic_placement: str = "PLANNED_NOT_VERIFIED"
    production_publication: str = "BLOCKED_D1"

    def to_dict(self):
        return asdict(self)


def inspect_hero(contract: SceneContract, path, prompt, *, source_kind, content_evidence=None, generation_receipt=None) -> HeroQA:
    blockers = []
    d2 = source_kind == "d2_generated_benchmark"
    if source_kind not in {"synthetic_fixture", "existing_accepted_asset", "d2_generated_benchmark"}:
        blockers.append("D1_ASSET_SOURCE_UNSUPPORTED")
    if d2:
        from .premium_sdxl_prompt import compile_sdxl_prompt
        expected_prompt = compile_sdxl_prompt(contract)
    else:
        expected_prompt = compile_prompt(contract)
    if prompt != expected_prompt:
        blockers.append("CONTRACT_PROMPT_MISMATCH")
    dimensions, raster_hash = (0, 0), ""
    try:
        raw = Path(path).read_bytes()
        raster_hash = hashlib.sha256(raw).hexdigest()
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
            dimensions = image.size
            if image.format != "PNG" or min(dimensions) < 512 or max(dimensions) > 4096 or dimensions[0] != dimensions[1]:
                blockers.append("HERO_DIMENSIONS_OR_FORMAT_INVALID")
            if max(ImageStat.Stat(image.convert("RGB")).stddev) < 3:
                blockers.append("HERO_UNIFORM_OR_EMPTY")
    except (OSError, ValueError, Image.DecompressionBombError):
        blockers.append("HERO_RASTER_INVALID")
    if d2:
        receipt = generation_receipt if isinstance(generation_receipt, dict) else {}
        audit = receipt.get("licence_audit", {})
        if (receipt.get("state") != "GENERATED_AWAITING_VISUAL_REVIEW" or
                receipt.get("contract_sha256") != contract.sha256 or receipt.get("prompt_sha256") != digest(prompt) or
                receipt.get("raster_sha256") != raster_hash or dimensions != (1024, 1024) or
                receipt.get("provider") != "ai_horde" or receipt.get("model") != "AlbedoBase XL 3.1" or
                receipt.get("slide_number") != contract.slide_number or receipt.get("attempt") != 1 or
                not receipt.get("provider_job_id") or receipt.get("CURRENT_READINESS") != "NOT_ASSERTED" or
                receipt.get("SOURCE") != "ACCEPTED_EP104_HISTORICAL_SNAPSHOT" or
                receipt.get("publication_allowed") is not False or receipt.get("reference_assets") != [] or
                audit.get("creator") != "albedobond" or audit.get("publication_attribution_required") is not True or
                audit.get("permission_state") != "ALLOWED_WITH_OBLIGATIONS" or
                audit.get("use", {}).get("context") != "INTERNAL_BENCHMARK"):
            blockers.append("D2_GENERATION_RECEIPT_INVALID")
    guard = "NOT_INSPECTED_NO_DETECTOR"
    if content_evidence is not None:
        # Same field names as the existing agent_visual_screen evidence gate.
        required = ("text_or_pseudotext_detected", "watermark_or_signature_detected", "logo_detected",
                    "panelist_identity_detected", "literal_fluffy_cloud_or_icon_detected",
                    "neon_cyberpunk_detected", "poster_or_contact_sheet_detected")
        if (not isinstance(content_evidence, dict) or content_evidence.get("artifact_sha256") != raster_hash or
                content_evidence.get("performed") is not True or
                any(type(content_evidence.get(k)) is not bool for k in required)):
            blockers.append("CONTENT_GUARD_EVIDENCE_INVALID")
        elif any(content_evidence[k] for k in required) or content_evidence.get("approved_for_composition") is not True:
            blockers.append("CONTENT_GUARD_REJECTED")
            guard = "REJECTED_INSPECTED_EVIDENCE"
        else:
            guard = "PASSED_INSPECTED_EVIDENCE_NOT_AUTOMATIC_DETECTION"
    return HeroQA(contract.sha256, digest(prompt), raster_hash, dimensions, source_kind,
                  not blockers, tuple(blockers), guard,
                  production_publication="BLOCKED_PUBLIC_ATTRIBUTION_AND_HUMAN_REVIEW" if d2 else "BLOCKED_D1")
