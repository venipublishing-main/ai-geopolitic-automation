"""Neutral cloud image validation and output consumer; no worker/GPU assumptions."""
import base64
import binascii
import hashlib
import io
from pathlib import Path

from ..contracts import (GenerationResult, HealthState, Modality, OutputArtifact, UnsupportedJob,
                         capability_rejections, resource_rejections)
from .http import CloudError
from ..licence_policy import model_permission_rejections

ROOT = Path(__file__).resolve().parents[3]


def validate_cloud_job(provider, job):
    job.validate()
    caps, resources = provider.capabilities(), provider.resource_state()
    caps.validate()
    resources.validate()
    reasons = list(capability_rejections(job, caps) + resource_rejections(job, resources, caps))
    if provider.health().state is not HealthState.HEALTHY:
        reasons.append("PROVIDER_UNHEALTHY")
    from ..contracts import MonetaryCost
    if caps.monetary_cost is not MonetaryCost.ZERO_COST:
        reasons.append("ZERO_COST_UNPROVEN")
    metadata = provider.models.get(provider.provider_id, job.model_preference or caps.default_model_id, job.modality)
    permission_reasons = model_permission_rejections(metadata, job)
    if metadata is None or metadata.permission_state is None:
        # Retain the adapter's established legacy unknown-permission code.
        if any(r != "MODEL_ATTRIBUTION_REQUIRED" for r in permission_reasons):
            reasons.append("MODEL_PERMISSION_UNPROVEN")
        elif permission_reasons:
            reasons.extend(permission_reasons)
    else:
        reasons.extend(permission_reasons)
    if reasons:
        raise UnsupportedJob(tuple(reasons))


def image_bytes(value):
    if not isinstance(value, str) or not value or len(value) > 24 * 1024 * 1024:
        raise CloudError("INVALID_IMAGE_BASE64")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise CloudError("INVALID_IMAGE_BASE64") from None


def save_image(raw, root, job, provider_job_id, provider_id):
    """Lossless pixel conversion to PNG; never resize or fake requested dimensions."""
    from PIL import Image, ImageStat
    root = Path(root).resolve()
    approved = (ROOT / "output").resolve()
    if not root.is_relative_to(approved / "phase-c") and not root.is_relative_to(approved / "phase-c1"):
        raise CloudError("ARTIFACT_ROOT_REJECTED")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if (image.format not in {"PNG", "JPEG", "WEBP"} or image.size != (job.output.width, job.output.height) or
                    getattr(image, "n_frames", 1) != 1):
                raise CloudError("IMAGE_FORMAT_OR_DIMENSIONS_INVALID")
            image.load()
            pixels = image.convert("RGB")
            if max(ImageStat.Stat(pixels).var) <= 0:
                raise CloudError("EMPTY_IMAGE_CONTENT")
    except CloudError:
        raise
    except Exception:
        raise CloudError("IMAGE_DECODE_FAILED") from None
    root.mkdir(parents=True, exist_ok=True)
    path = root / (hashlib.sha256(provider_job_id.encode()).hexdigest() + ".png")
    if path.exists() or not path.resolve().is_relative_to(root):
        raise CloudError("ARTIFACT_OVERWRITE_REJECTED")
    pixels.save(path, "PNG")
    return GenerationResult(provider_job_id, provider_id, Modality.IMAGE,
                            (OutputArtifact(str(path), "png", job.output.width, job.output.height),))
