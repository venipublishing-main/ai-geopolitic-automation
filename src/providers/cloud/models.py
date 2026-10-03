"""Reviewed cloud permissions; active model discovery never grants a licence."""
from ..contracts import Modality
from ..model_registry import ModelMetadata, ModelRegistry, PermissionState
from ..licence_policy import RESTRICTIONS

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


ALBEDO_MODEL_ID = "AlbedoBase XL 3.1"
SDXL_MODEL_ID = "SDXL 1.0"
SDXL_LICENCE_SOURCE = "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/main/LICENSE.md"
ALBEDO_PERMISSION_SOURCE = "https://civitai.com/api/v1/models/140737"
ALBEDO_VERSION_SOURCE = "https://civitai.com/api/v1/model-versions/1041855"
ALBEDO_CHECKPOINT_SHA256 = "C379D154EB476B67B390E31463C41C79AC9E766466315408886EBB7FAA2EA098"
ALBEDO_MODEL = ModelMetadata(
    ALBEDO_MODEL_ID, HORDE_PROVIDER, Modality.IMAGE, licence="CreativeML Open RAIL++-M",
    commercial_output_allowed=True, attribution_required=True, creator="albedobond",
    attribution_text="Context illustration generated with AlbedoBase XL 3.1 by albedobond.",
    permission_state=PermissionState.ALLOWED_WITH_OBLIGATIONS,
    licence_source=SDXL_LICENCE_SOURCE, permission_source=ALBEDO_PERMISSION_SOURCE,
    known_restrictions=RESTRICTIONS, reference_image_support=False, image_edit_support=False)
SDXL_MODEL = ModelMetadata(
    SDXL_MODEL_ID, HORDE_PROVIDER, Modality.IMAGE, licence="CreativeML Open RAIL++-M",
    commercial_output_allowed=True, attribution_required=False, creator="Stability AI",
    permission_state=PermissionState.ALLOWED_WITH_OBLIGATIONS,
    licence_source=SDXL_LICENCE_SOURCE, permission_source=SDXL_LICENCE_SOURCE,
    known_restrictions=RESTRICTIONS, reference_image_support=False, image_edit_support=False)
MODEL_EVIDENCE = {
    ALBEDO_MODEL_ID: {
        "model_id": ALBEDO_MODEL_ID, "checkpoint_sha256": ALBEDO_CHECKPOINT_SHA256,
        "checkpoint_file": "albedobaseXL_V31Large.safetensors", "civitai_version_id": 1041855,
        "civitai_model_id": 140737, "creator": "albedobond", "reviewed_date": "2026-10-03",
        "sources": ["https://models.aihorde.net/api/model_references/v2/image_generation/model/AlbedoBase%20XL%203.1",
                    ALBEDO_VERSION_SOURCE, ALBEDO_PERMISSION_SOURCE, SDXL_LICENCE_SOURCE],
        "author_permissions": {"allowNoCredit": False, "allowCommercialUse": ["Image", "RentCivit", "Rent"],
                               "allowDerivatives": True, "allowDifferentLicense": False},
        "service_note": "Author permits Image and Rent generation uses. No sale or redistribution of weights; no alternate model licence inferred.",
        "credit_note": "Conservatively require creator credit for generated images; internal audit recording is allowed only for this unpublished benchmark. Future public credit is unresolved.",
        "licence_note": "Exact Civitai version SHA matches the exact Horde checkpoint; both author permissions and base Attachment A restrictions retained.",
    },
    SDXL_MODEL_ID: {
        "model_id": SDXL_MODEL_ID, "creator": "Stability AI", "reviewed_date": "2026-10-03",
        "checkpoint_sha256": "31e35c80fc4829d14f90153f4c74cd59c90b779f6afe05a74cd6120b893f7e5b",
        "sources": ["https://models.aihorde.net/api/model_references/v2/image_generation/model/SDXL%201.0", SDXL_LICENCE_SOURCE],
        "licence_note": "Licensor claims no rights in output; uses remain subject to Attachment A. Metadata-only fallback, never automatically dispatched.",
    },
}


def model_evidence(provider_id, model_id):
    return MODEL_EVIDENCE[model_id] if provider_id == HORDE_PROVIDER and model_id in MODEL_EVIDENCE else EVIDENCE[provider_id]


def cloud_registry():
    # Explicit reviewed entries only; dynamic discovery never grants permission.
    return ModelRegistry((CF_MODEL, HORDE_MODEL, ALBEDO_MODEL, SDXL_MODEL))
