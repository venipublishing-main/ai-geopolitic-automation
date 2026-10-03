"""Reviewed cloud permissions; active model discovery never grants a licence."""
from ..contracts import Modality
from ..model_registry import ModelMetadata, ModelRegistry

CF_MODEL_ID = "@cf/black-forest-labs/flux-1-schnell"
CF_PROVIDER = "cloudflare_workers_ai"
HORDE_PROVIDER = "ai_horde"
HORDE_MODEL_ID = "Flux.1-Schnell fp8 (Compact)"
HORDE_CHECKPOINT_SHA256 = "5C2C590E92ED47500092EF8E1A00FD1F8E61009DA93B89130A80940F5257DF17"
CF_MODEL = ModelMetadata(CF_MODEL_ID, CF_PROVIDER, Modality.IMAGE, licence="Apache-2.0",
                         commercial_output_allowed=True, attribution_required=False,
                         reference_image_support=False, image_edit_support=False)
HORDE_MODEL = ModelMetadata(HORDE_MODEL_ID, HORDE_PROVIDER, Modality.IMAGE, licence="Apache-2.0",
                            commercial_output_allowed=True, attribution_required=False, quantization="fp8",
                            reference_image_support=False, image_edit_support=False)
EVIDENCE = {
    CF_PROVIDER: {
        "model_id": CF_MODEL_ID,
        "licence": "Apache-2.0",
        "commercial_output_allowed": True,
        "attribution_note": "No generated-output attribution condition in Apache-2.0; distributing weights/code has separate notice obligations.",
        "sources": ["https://huggingface.co/black-forest-labs/FLUX.1-schnell",
                    "https://github.com/black-forest-labs/flux/blob/main/README.md",
                    "https://www.apache.org/licenses/LICENSE-2.0",
                    "https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/"],
        "reviewed_date": "2026-10-03",
        "note": "Image-only underlying Schnell, not dev; model-card limitations and service terms still apply. No copyright/accuracy guarantee.",
    },
    HORDE_PROVIDER: {
        "model_id": HORDE_MODEL_ID, "licence": "Apache-2.0", "commercial_output_allowed": True,
        "checkpoint_sha256": HORDE_CHECKPOINT_SHA256, "reviewed_date": "2026-10-03",
        "reference_reviewed_by": "horde-model-reference-license-backfill",
        "reference_reviewed_at": "2026-08-26",
        "sources": ["https://models.aihorde.net/api/model_references/v2/image_generation/model/Flux.1-Schnell%20fp8%20%28Compact%29",
                    "https://models.aihorde.net/api/model_references/v2/licensing/licenses/Apache-2.0",
                    "https://huggingface.co/black-forest-labs/FLUX.1-schnell",
                    "https://www.apache.org/licenses/LICENSE-2.0"],
        "note": "Exact official v2 record binds this checkpoint to Apache-2.0 and explicitly allows commercial use; no family-based approval.",
        "attribution_note": "include_license applies to redistribution of model/code, not generated contextual images; no output-attribution requirement identified.",
        "restriction_note": "Official licence definition lists no restrictions. BFL out-of-scope guidance was reviewed for non-deceptive text-free infrastructure illustration; no model redistribution, factual image claims or identity generation.",
        "availability_note": "Exact active model cross-matched with official v2 search/popular records; worker count/ETA is transient, not an execution guarantee.",
    },
}


def cloud_registry():
    # Explicit reviewed entries only; dynamic discovery never grants permission.
    return ModelRegistry((CF_MODEL, HORDE_MODEL))
