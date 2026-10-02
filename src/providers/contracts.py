"""Nonblocking worker operations and immutable, provider-neutral job snapshots."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class Modality(str, Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"


class JobState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class MonetaryCost(str, Enum):
    ZERO_COST = "ZERO_COST"
    PAID = "PAID"
    UNKNOWN = "UNKNOWN"


class WorkerLocation(str, Enum):
    LOCAL = "LOCAL"
    REMOTE = "REMOTE"
    UNKNOWN = "UNKNOWN"


class HealthState(str, Enum):
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    INTEGRATION_PENDING = "INTEGRATION_PENDING"


class ActivityState(str, Enum):
    IDLE = "IDLE"
    BUSY = "BUSY"
    UNKNOWN = "UNKNOWN"


class GenerationError(ValueError):
    pass


class InvalidGenerationJob(GenerationError):
    pass


class UnknownJob(GenerationError):
    pass


class DuplicateJob(GenerationError):
    pass


class UnsupportedJob(GenerationError):
    def __init__(self, reasons: tuple[str, ...]):
        self.reasons = reasons
        super().__init__(", ".join(reasons))


class ResultNotReady(GenerationError):
    pass


class ProviderUnavailable(GenerationError):
    pass


class InvalidJobTransition(GenerationError):
    pass


def require_text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonblank text.")


def optional_int(value: object, name: str, minimum: int = 0) -> None:
    if value is not None and (type(value) is not int or value < minimum):
        raise ValueError(f"{name} must be an integer >= {minimum}, or None.")


def text_tuple(value: object, name: str) -> None:
    if not isinstance(value, tuple):
        raise ValueError(f"{name} must be a tuple.")
    for item in value:
        require_text(item, name)
    if len(set(value)) != len(value):
        raise ValueError(f"{name} must not contain duplicates.")


@dataclass(frozen=True)
class OutputRequirements:
    format: str
    width: int | None = None
    height: int | None = None
    attribution_allowed: bool = False


@dataclass(frozen=True)
class ResourceRequirements:
    require_gpu: bool = False
    min_free_vram_mb: int | None = None
    min_free_ram_mb: int | None = None


@dataclass(frozen=True)
class TraceMetadata:
    episode_id: str | None = None
    slide_number: int | None = None
    attempt: int = 1
    # Immutable extra trace fields; never passed as provider-specific options.
    tags: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class GenerationJob:
    job_id: str
    modality: Modality
    purpose: str
    prompt: str
    output: OutputRequirements
    reference_assets: tuple[str, ...] = ()
    image_edit: bool = False
    cancellation_required: bool = False
    model_preference: str | None = None
    seed: int | None = None
    trace: TraceMetadata = field(default_factory=TraceMetadata)
    resources: ResourceRequirements = field(default_factory=ResourceRequirements)
    zero_cost_required: bool = True

    def validate(self) -> None:
        """Validate before probing any provider; no path/network/model I/O."""
        try:
            for name in ("job_id", "purpose", "prompt"):
                require_text(getattr(self, name), name)
            if not isinstance(self.modality, Modality):
                raise ValueError("modality must be a Modality enum.")
            if not isinstance(self.output, OutputRequirements):
                raise ValueError("output must be OutputRequirements.")
            require_text(self.output.format, "output.format")
            optional_int(self.output.width, "width", 1)
            optional_int(self.output.height, "height", 1)
            if (self.output.width is None) != (self.output.height is None):
                raise ValueError("width and height must be supplied together.")
            if self.modality in (Modality.IMAGE, Modality.VIDEO) and self.output.width is None:
                raise ValueError("IMAGE/VIDEO jobs require width and height.")
            if self.modality is Modality.AUDIO and self.output.width is not None:
                raise ValueError("AUDIO jobs do not use image dimensions.")
            for name, value in (("image_edit", self.image_edit), ("cancellation_required", self.cancellation_required),
                                ("zero_cost_required", self.zero_cost_required),
                                ("attribution_allowed", self.output.attribution_allowed)):
                if type(value) is not bool:
                    raise ValueError(f"{name} must be boolean.")
            text_tuple(self.reference_assets, "reference_assets")
            if self.image_edit and (self.modality is not Modality.IMAGE or not self.reference_assets):
                raise ValueError("image_edit requires an IMAGE job and reference assets.")
            if self.model_preference is not None:
                require_text(self.model_preference, "model_preference")
            optional_int(self.seed, "seed")
            if not isinstance(self.trace, TraceMetadata) or not isinstance(self.resources, ResourceRequirements):
                raise ValueError("trace/resources must use their neutral contracts.")
            if self.trace.episode_id is not None:
                require_text(self.trace.episode_id, "episode_id")
            optional_int(self.trace.slide_number, "slide_number", 1)
            optional_int(self.trace.attempt, "attempt", 1)
            if self.trace.attempt is None:
                raise ValueError("attempt is required.")
            if not isinstance(self.trace.tags, tuple):
                raise ValueError("trace.tags must be a tuple.")
            tag_keys = []
            for pair in self.trace.tags:
                if not isinstance(pair, tuple) or len(pair) != 2:
                    raise ValueError("trace tags must be text pairs.")
                require_text(pair[0], "tag key")
                require_text(pair[1], "tag value")
                tag_keys.append(pair[0])
            if len(set(tag_keys)) != len(tag_keys):
                raise ValueError("trace tag keys must be unique.")
            if type(self.resources.require_gpu) is not bool:
                raise ValueError("require_gpu must be boolean.")
            optional_int(self.resources.min_free_vram_mb, "min_free_vram_mb", 1)
            optional_int(self.resources.min_free_ram_mb, "min_free_ram_mb", 1)
        except ValueError as exc:
            raise InvalidGenerationJob(str(exc)) from exc


@dataclass(frozen=True)
class HealthReport:
    state: HealthState
    detail: str = ""


@dataclass(frozen=True)
class ProviderCapabilities:
    # Empty/unknown defaults never imply support.
    modalities: tuple[Modality, ...] = ()
    output_formats: tuple[str, ...] = ()
    image_generation: bool = False
    reference_images: bool = False
    image_editing: bool = False
    max_width: int | None = None
    max_height: int | None = None
    model_ids: tuple[str, ...] = ()
    default_model_id: str | None = None
    cancellation: bool = False
    deterministic_seed: bool = False
    queue_while_busy: bool = False
    location: WorkerLocation = WorkerLocation.UNKNOWN
    monetary_cost: MonetaryCost = MonetaryCost.UNKNOWN
    synthetic: bool = False

    def validate(self) -> None:
        if not isinstance(self.modalities, tuple) or any(not isinstance(item, Modality) for item in self.modalities):
            raise ValueError("modalities must be a tuple of Modality values.")
        if len(set(self.modalities)) != len(self.modalities):
            raise ValueError("Duplicate modalities.")
        text_tuple(self.output_formats, "output_formats")
        text_tuple(self.model_ids, "model_ids")
        for name in ("image_generation", "reference_images", "image_editing", "cancellation",
                     "deterministic_seed", "queue_while_busy", "synthetic"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean.")
        if not isinstance(self.location, WorkerLocation) or not isinstance(self.monetary_cost, MonetaryCost):
            raise ValueError("location/cost must use explicit enums.")
        optional_int(self.max_width, "max_width", 1)
        optional_int(self.max_height, "max_height", 1)
        if self.default_model_id is not None and self.default_model_id not in self.model_ids:
            raise ValueError("Default model must be advertised explicitly.")


@dataclass(frozen=True)
class ResourceState:
    online: bool | None = None
    activity: ActivityState = ActivityState.UNKNOWN
    worker_id: str | None = None
    gpu_identity: str | None = None
    total_vram_mb: int | None = None
    free_vram_mb: int | None = None
    total_ram_mb: int | None = None
    free_ram_mb: int | None = None
    active_job_id: str | None = None
    loaded_model_id: str | None = None
    available_model_ids: tuple[str, ...] | None = None

    def validate(self) -> None:
        if self.online is not None and type(self.online) is not bool:
            raise ValueError("online must be boolean or None.")
        if not isinstance(self.activity, ActivityState):
            raise ValueError("activity must be an ActivityState enum.")
        for name in ("total_vram_mb", "free_vram_mb", "total_ram_mb", "free_ram_mb"):
            optional_int(getattr(self, name), name)
        for total, free in ((self.total_vram_mb, self.free_vram_mb), (self.total_ram_mb, self.free_ram_mb)):
            if total is not None and free is not None and free > total:
                raise ValueError("Free memory cannot exceed total memory.")
        for name in ("worker_id", "gpu_identity", "active_job_id", "loaded_model_id"):
            if getattr(self, name) is not None:
                require_text(getattr(self, name), name)
        if self.available_model_ids is not None:
            text_tuple(self.available_model_ids, "available_model_ids")


@dataclass(frozen=True)
class FailureInfo:
    code: str
    message: str


@dataclass(frozen=True)
class JobStatus:
    job_id: str
    state: JobState
    progress: float | None = None
    failure: FailureInfo | None = None

    def validate(self) -> None:
        require_text(self.job_id, "job_id")
        if not isinstance(self.state, JobState):
            raise ValueError("state must be a JobState enum.")
        if self.progress is not None and (type(self.progress) not in (int, float) or
                                         not math.isfinite(self.progress) or not 0 <= self.progress <= 1):
            raise ValueError("progress must be finite and between zero and one.")
        if self.state is JobState.FAILED:
            if not isinstance(self.failure, FailureInfo):
                raise ValueError("Failed status requires failure information.")
            require_text(self.failure.code, "failure.code")
            require_text(self.failure.message, "failure.message")
        elif self.failure is not None:
            raise ValueError("Only failed status may carry failure information.")


@dataclass(frozen=True)
class OutputArtifact:
    # Paths/identifiers are declarations, never proof of successful generation.
    identifier: str
    format: str
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True)
class GenerationResult:
    job_id: str
    provider_id: str
    modality: Modality
    artifacts: tuple[OutputArtifact, ...] = ()
    data: tuple[tuple[str, str], ...] = ()
    synthetic: bool = False


class GenerationProvider(Protocol):
    @property
    def provider_id(self) -> str: ...

    def available(self) -> bool: ...
    def health(self) -> HealthReport: ...
    def capabilities(self) -> ProviderCapabilities: ...
    def resource_state(self) -> ResourceState: ...
    def submit(self, job: GenerationJob) -> str: ...
    def status(self, job_id: str) -> JobStatus: ...
    def result(self, job_id: str) -> GenerationResult: ...
    def cancel(self, job_id: str) -> JobStatus: ...


def capability_rejections(job: GenerationJob, caps: ProviderCapabilities) -> tuple[str, ...]:
    reasons = []
    if job.modality not in caps.modalities or (job.modality is Modality.IMAGE and not caps.image_generation):
        reasons.append("MODALITY_UNSUPPORTED")
    if job.output.format not in caps.output_formats:
        reasons.append("OUTPUT_FORMAT_UNSUPPORTED")
    if job.reference_assets and not caps.reference_images:
        reasons.append("REFERENCE_IMAGES_UNSUPPORTED")
    if job.image_edit and not caps.image_editing:
        reasons.append("IMAGE_EDIT_UNSUPPORTED")
    if job.seed is not None and not caps.deterministic_seed:
        reasons.append("DETERMINISTIC_SEED_UNSUPPORTED")
    if job.cancellation_required and not caps.cancellation:
        reasons.append("CANCELLATION_UNSUPPORTED")
    if job.model_preference is not None and job.model_preference not in caps.model_ids:
        reasons.append("MODEL_UNSUPPORTED")
    if ((caps.max_width is not None and job.output.width is not None and job.output.width > caps.max_width) or
            (caps.max_height is not None and job.output.height is not None and job.output.height > caps.max_height)):
        reasons.append("DIMENSIONS_UNSUPPORTED")
    if job.output.width is not None and (caps.max_width is None or caps.max_height is None):
        reasons.append("DIMENSION_LIMIT_UNKNOWN")
    return tuple(reasons)


def resource_rejections(job: GenerationJob, state: ResourceState, caps: ProviderCapabilities) -> tuple[str, ...]:
    reasons = []
    if state.online is not True:
        reasons.append("RESOURCE_OFFLINE_OR_UNKNOWN")
    if state.activity is ActivityState.UNKNOWN:
        reasons.append("RESOURCE_ACTIVITY_UNKNOWN")
    if state.activity is ActivityState.BUSY and not caps.queue_while_busy:
        reasons.append("RESOURCE_BUSY")
    if (job.resources.require_gpu or job.resources.min_free_vram_mb is not None) and not state.gpu_identity:
        reasons.append("GPU_UNAVAILABLE_OR_UNKNOWN")
    for minimum, available, code in ((job.resources.min_free_vram_mb, state.free_vram_mb, "VRAM_INSUFFICIENT_OR_UNKNOWN"),
                                      (job.resources.min_free_ram_mb, state.free_ram_mb, "RAM_INSUFFICIENT_OR_UNKNOWN")):
        if minimum is not None and (available is None or available < minimum):
            reasons.append(code)
    model = job.model_preference or caps.default_model_id
    if model is not None and (state.available_model_ids is None or model not in state.available_model_ids):
        reasons.append("MODEL_UNAVAILABLE_OR_UNKNOWN")
    return tuple(reasons)
