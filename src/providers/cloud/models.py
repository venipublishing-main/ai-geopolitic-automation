"""Reviewed cloud permissions; active model discovery never grants a licence."""
from ..contracts import Modality
from ..model_registry import ModelMetadata, ModelRegistry

CF_MODEL_ID = "@cf/black-forest-labs/flux-1-schnell"
CF_PROVIDER = "cloudflare_workers_ai"
HORDE_PROVIDER = "ai_horde"
CF_MODEL = ModelMetadata(CF_MODEL_ID, CF_PROVIDER, Modality.IMAGE, licence="Apache-2.0",
                         commercial_output_allowed=True, attribution_required=False,
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
        "model_id": None, "commercial_output_allowed": None,
        "note": "Active Flux.1-Schnell fp8 (Compact) discovered. Exact compact derivative publisher licence/terms not verified; no approved entry.",
        "sources": ["https://aihorde.net/api/v2/status/models?type=image",
                    "https://github.com/Haidra-Org/AI-Horde-image-model-reference/blob/main/stable_diffusion.json"],
    },
}


def cloud_registry():
    # No speculative Horde entry; external callers can supply a separately reviewed registry.
    return ModelRegistry((CF_MODEL,))
