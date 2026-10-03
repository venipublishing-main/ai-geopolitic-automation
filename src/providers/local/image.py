"""Narrow image-worker activation boundary; no shipped model approvals."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

from ..contracts import (ActivityState, DuplicateJob, GenerationJob, GenerationResult, HealthReport,
                         HealthState, Modality, MonetaryCost, OutputArtifact, ProviderCapabilities,
                         ProviderUnavailable, ResourceState, ResultNotReady, UnknownJob, UnsupportedJob,
                         WorkerLocation, capability_rejections, resource_rejections, require_text)
from ..model_registry import ModelMetadata
from .base import InactiveLocalProvider, LocalWorkerConfig
from .transport import MalformedResponse, localhost_url


@dataclass(frozen=True)
class ImageProfile:
    """Operator-reviewed binding from runtime discovery + authoritative evidence.

    This is adapter configuration, never a field in the neutral GenerationJob.
    No production instances/approval data are supplied by this repository.
    """
    model: ModelMetadata
    evidence_urls: tuple[str, ...]
    worker_revision: str
    width: int
    height: int
    seed_supported: bool = False
    cancellation_verified: bool = False
    local_execution_verified: bool = False
    required_model_files: tuple[str, ...] = ()

    def validate(self, provider_id: str):
        self.model.validate()
        if self.model.provider != provider_id or self.model.modality is not Modality.IMAGE:
            raise ValueError("Model/profile identity mismatch.")
        if (not isinstance(self.evidence_urls, tuple) or not self.evidence_urls or
                any(not isinstance(url, str) or not url.startswith("https://") for url in self.evidence_urls)):
            raise ValueError("Authoritative model/worker source URLs are required.")
        require_text(self.worker_revision, "verified worker revision")
        if (not isinstance(self.required_model_files, tuple) or not self.required_model_files or
                any(not isinstance(p, str) or not Path(p).is_absolute() for p in self.required_model_files)):
            raise ValueError("A reviewed, complete absolute model-file inventory is required.")
        if (type(self.width) is not int or type(self.height) is not int or self.width < 1 or self.height != self.width):
            raise ValueError("Benchmark profile requires known supported square dimensions.")
        for value in (self.seed_supported, self.cancellation_verified, self.local_execution_verified):
            if type(value) is not bool:
                raise ValueError("Profile verification flags must be boolean.")
        if (not self.local_execution_verified or self.model.commercial_output_allowed is not True or
                not self.model.licence or self.model.attribution_required is None or self.model.known_restrictions or
                self.model.min_vram_mb is None):
            raise ValueError("Local execution, licence/attribution and hardware requirements must be reviewed first.")


def nvidia_resources() -> ResourceState:
    """Read actual local measurements; never substitute expected/project hardware."""
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free",
                                 "--format=csv,noheader,nounits"], capture_output=True,
                                text=True, encoding="utf-8", timeout=5, check=True)
        rows = result.stdout.strip().splitlines()
        if len(rows) != 1:
            return ResourceState()  # Multi-device selection requires explicit later configuration.
        name, total, free = [part.strip() for part in rows[0].split(",")]
        snapshot = ResourceState(gpu_identity=name, total_vram_mb=int(total), free_vram_mb=int(free))
        snapshot.validate()
        return snapshot
    except (OSError, ValueError, subprocess.SubprocessError):
        return ResourceState()


def inspect_png(path: Path, width: int, height: int) -> dict:
    from PIL import Image, ImageStat

    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Missing/empty generated artifact.")
    with Image.open(path) as image:
        if image.format != "PNG" or image.size != (width, height) or getattr(image, "n_frames", 1) != 1:
            raise ValueError("Generated artifact format/dimensions are incorrect.")
        image.load()
        variance = ImageStat.Stat(image.convert("RGB")).var
        if max(variance) <= 0:
            raise ValueError("Generated artifact has no non-uniform image content.")
    return {"format": "PNG", "width": width, "height": height, "bytes": path.stat().st_size,
            "nonuniform_content": True, "human_review": "HUMAN REVIEW REQUIRED"}


class ImageWorker(InactiveLocalProvider):
    def __init__(self, provider_id: str, config: LocalWorkerConfig | None = None, *, profile=None, artifact_root=None):
        super().__init__(provider_id, config)
        self.profile = profile
        if profile is not None:
            profile.validate(provider_id)
            if self.config.endpoint is None:
                raise ValueError("Reviewed workers require an explicit localhost endpoint.")
            localhost_url(self.config.endpoint)
        self.artifact_root = Path(artifact_root).resolve() if artifact_root is not None else None
        self._jobs: dict[str, GenerationJob] = {}
        self._attempted: set[str] = set()

    def _configured(self):
        return self.profile is not None and self.artifact_root is not None and self._transport is not None

    def available(self):
        if not self._configured():
            return False
        try:
            self.verify_runtime()
            return True
        except (ProviderUnavailable, ValueError, KeyError, TypeError, AttributeError, OSError):
            return False

    def health(self):
        if not self._configured():
            return super().health()
        return HealthReport(HealthState.HEALTHY if self.available() else HealthState.UNHEALTHY)

    def capabilities(self):
        if not self.available():
            return super().capabilities()
        return ProviderCapabilities(modalities=(Modality.IMAGE,), output_formats=("png",), image_generation=True,
                                    max_width=self.profile.width, max_height=self.profile.height,
                                    model_ids=(self.profile.model.model_id,), default_model_id=self.profile.model.model_id,
                                    deterministic_seed=self.profile.seed_supported,
                                    cancellation=self.profile.cancellation_verified, location=WorkerLocation.LOCAL,
                                    monetary_cost=MonetaryCost.ZERO_COST)

    def submit(self, job: GenerationJob):
        job.validate()
        if not self.available():
            raise ProviderUnavailable("Verified local image worker/profile is unavailable.")
        if job.job_id in self._attempted:
            raise DuplicateJob(job.job_id)
        caps = self.capabilities()
        resources = self.resource_state()
        reasons = capability_rejections(job, caps) + resource_rejections(job, resources, caps)
        if not resources.gpu_identity or resources.free_vram_mb is None or resources.free_vram_mb < self.profile.model.min_vram_mb:
            reasons += ("MODEL_VRAM_INSUFFICIENT_OR_UNKNOWN",)
        if (job.output.width, job.output.height) != (self.profile.width, self.profile.height):
            reasons += ("EXACT_DIMENSIONS_UNPROVEN",)
        if job.model_preference != self.profile.model.model_id:
            reasons += ("EXPLICIT_MODEL_REQUIRED",)
        if self.profile.model.attribution_required and not job.output.attribution_allowed:
            reasons += ("MODEL_ATTRIBUTION_REQUIRED",)
        if reasons:
            raise UnsupportedJob(reasons)
        self._attempted.add(job.job_id)  # Reserve even if the worker acknowledgement is lost.
        worker_id = self._submit(job)
        require_text(worker_id, "real worker job ID")
        if worker_id in self._jobs:
            raise MalformedResponse("Worker reused an existing job ID.")
        self._jobs[worker_id] = job
        return worker_id

    def _job(self, job_id):
        if not self._configured():
            raise ProviderUnavailable("Verified local image worker/profile is unavailable.")
        if job_id not in self._jobs:
            raise UnknownJob(job_id)
        return self._jobs[job_id]

    def result(self, job_id):
        from ..contracts import JobState

        job = self._job(job_id)
        if self.status(job_id).state is not JobState.SUCCEEDED:
            raise ResultNotReady("Worker has not explicitly succeeded.")
        path = self._artifact(job_id)
        inspect_png(path, job.output.width, job.output.height)
        return GenerationResult(job_id, self.provider_id, Modality.IMAGE,
                                (OutputArtifact(str(path), "png", job.output.width, job.output.height),))

    def cancel(self, job_id):
        self._job(job_id)
        if not self.profile.cancellation_verified:
            raise UnsupportedJob(("CANCELLATION_UNPROVEN",))
        self._cancel(job_id)
        # A cancellation request/acknowledgement is not a CANCELLED result.
        return self.status(job_id)

    def verify_files(self):
        if any(not Path(p).is_file() or Path(p).stat().st_size == 0 for p in self.profile.required_model_files):
            raise ProviderUnavailable("Reviewed model files are missing; automatic downloading is forbidden.")
