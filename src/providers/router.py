"""Deterministic single-provider submission with immutable selection audits."""
from __future__ import annotations

from dataclasses import dataclass, replace

from .contracts import (DuplicateJob, GenerationError, GenerationJob, GenerationProvider,
                        GenerationResult, HealthReport, HealthState, JobState, JobStatus,
                        MonetaryCost, OutputArtifact, ProviderCapabilities, ResourceState,
                        ResultNotReady, UnknownJob, capability_rejections, require_text,
                        optional_int, resource_rejections)
from .model_registry import ModelRegistry


@dataclass(frozen=True)
class ZeroCostPolicy:
    """Local/unmetered describes money only; resources are evaluated separately."""

    def allows(self, cost: MonetaryCost) -> bool:
        return cost is MonetaryCost.ZERO_COST


@dataclass(frozen=True)
class RoutingPolicy:
    allow_synthetic: bool = False
    monetary: ZeroCostPolicy = ZeroCostPolicy()

    def __post_init__(self):
        if type(self.allow_synthetic) is not bool or type(self.monetary) is not ZeroCostPolicy:
            raise ValueError("Policy requires explicit booleans and the project zero-cost policy.")

    @classmethod
    def development(cls) -> RoutingPolicy:
        # Only synthetic providers may skip commercial-model permission checks.
        return cls(allow_synthetic=True)


@dataclass(frozen=True)
class ProviderDecision:
    provider_id: str
    eligible: bool
    reasons: tuple[str, ...]
    selected: bool = False


@dataclass(frozen=True)
class Submission:
    job: GenerationJob
    provider_id: str
    provider_job_id: str
    capabilities: ProviderCapabilities


class NoFreeGenerationProviderAvailable(GenerationError):
    def __init__(self, audit: tuple[ProviderDecision, ...]):
        self.audit = audit
        super().__init__("No eligible zero-cost generation provider is available.")


class SubmissionFailed(GenerationError):
    def __init__(self, audit: tuple[ProviderDecision, ...]):
        self.audit = audit
        super().__init__("Selected provider submission failed; no fallback was attempted.")


class InvalidProviderResponse(GenerationError):
    pass


class GenerationRouter:
    def __init__(self, providers: tuple[GenerationProvider, ...], *, priority: tuple[str, ...] | None = None,
                 policy: RoutingPolicy | None = None, models: ModelRegistry | None = None):
        self._providers: dict[str, GenerationProvider] = {}
        for provider in providers:
            require_text(provider.provider_id, "provider_id")
            if provider.provider_id in self._providers:
                raise ValueError("Provider IDs must be unique.")
            self._providers[provider.provider_id] = provider
        self._priority = tuple(self._providers) if priority is None else priority
        if (not isinstance(self._priority, tuple) or len(set(self._priority)) != len(self._priority) or
                set(self._priority) != set(self._providers)):
            raise ValueError("Priority must list every registered provider exactly once.")
        self._policy = RoutingPolicy() if policy is None else policy
        if type(self._policy) is not RoutingPolicy:
            raise ValueError("policy must be RoutingPolicy.")
        self._models = ModelRegistry() if models is None else models
        if not isinstance(self._models, ModelRegistry):
            raise ValueError("models must be ModelRegistry.")
        self._submissions: dict[str, Submission] = {}
        self._audits: dict[str, tuple[ProviderDecision, ...]] = {}
        self._attempted: set[str] = set()
        self._observed_states: dict[str, JobState] = {}

    def _model_rejections(self, provider_id: str, job: GenerationJob, caps: ProviderCapabilities,
                          resources: ResourceState) -> tuple[str, ...]:
        if caps.synthetic and self._policy.allow_synthetic:
            return ()
        model_id = job.model_preference or caps.default_model_id
        model = self._models.get(provider_id, model_id, job.modality) if model_id is not None else None
        reasons = []
        if model is None or model.commercial_output_allowed is not True or not model.licence:
            reasons.append("MODEL_COMMERCIAL_PERMISSION_UNPROVEN")
        elif model.attribution_required is None:
            reasons.append("MODEL_ATTRIBUTION_UNKNOWN")
        elif model.attribution_required and not job.output.attribution_allowed:
            reasons.append("MODEL_ATTRIBUTION_REQUIRED")
        if model is not None and model.known_restrictions:
            # Phase C must explicitly implement any restriction-specific handling.
            reasons.append("MODEL_RESTRICTIONS_UNHANDLED")
        if model is not None:
            if job.reference_assets and model.reference_image_support is not True:
                reasons.append("MODEL_REFERENCE_SUPPORT_UNPROVEN")
            if job.image_edit and model.image_edit_support is not True:
                reasons.append("MODEL_EDIT_SUPPORT_UNPROVEN")
            if model.min_vram_mb is not None and (not resources.gpu_identity or
                    resources.free_vram_mb is None or resources.free_vram_mb < model.min_vram_mb):
                reasons.append("MODEL_VRAM_INSUFFICIENT_OR_UNKNOWN")
        return tuple(reasons)

    def _inspect(self, provider_id: str, job: GenerationJob) -> tuple[ProviderDecision, ProviderCapabilities | None]:
        provider = self._providers[provider_id]
        reasons = []
        try:
            if provider.available() is not True:
                reasons.append("PROVIDER_UNAVAILABLE")
            health = provider.health()
            if not isinstance(health, HealthReport) or health.state is not HealthState.HEALTHY:
                reasons.append("PROVIDER_UNHEALTHY")
            caps = provider.capabilities()
            resources = provider.resource_state()
            if not isinstance(caps, ProviderCapabilities) or not isinstance(resources, ResourceState):
                raise ValueError("Invalid provider snapshot.")
            caps.validate()
            resources.validate()
            if not self._policy.monetary.allows(caps.monetary_cost):
                reasons.append("ZERO_COST_POLICY_REJECTED")
            if caps.synthetic and not self._policy.allow_synthetic:
                reasons.append("SYNTHETIC_PROVIDER_REJECTED")
            reasons.extend(capability_rejections(job, caps))
            reasons.extend(resource_rejections(job, resources, caps))
            reasons.extend(self._model_rejections(provider_id, job, caps, resources))
        except Exception:
            # Probe failures are rejection, never a reason to bypass a gate.
            return ProviderDecision(provider_id, False, tuple(reasons + ["PROVIDER_PROBE_FAILED"])), None
        return ProviderDecision(provider_id, not reasons, tuple(reasons) or ("ELIGIBLE",)), caps

    def submit(self, job: GenerationJob) -> str:
        if not isinstance(job, GenerationJob):
            raise ValueError("submit requires GenerationJob.")
        job.validate()
        if job.job_id in self._attempted:
            raise DuplicateJob("A submission has already been attempted for this job identity.")
        decisions = []
        selected_id = None
        selected_caps = None
        for provider_id in self._priority:
            decision, caps = self._inspect(provider_id, job)
            if decision.eligible and selected_id is None:
                selected_id, selected_caps = provider_id, caps
                decision = replace(decision, selected=True)
            decisions.append(decision)
        audit = tuple(decisions)
        self._audits[job.job_id] = audit
        if selected_id is None:
            raise NoFreeGenerationProviderAvailable(audit)
        # Reserve before dispatch: an exception may follow actual worker acceptance.
        self._attempted.add(job.job_id)
        try:
            provider_job_id = self._providers[selected_id].submit(job)
            require_text(provider_job_id, "provider_job_id")
        except Exception as exc:
            audit = tuple(replace(item, eligible=False, reasons=item.reasons + ("SUBMISSION_FAILED",))
                          if item.selected else item for item in audit)
            self._audits[job.job_id] = audit
            raise SubmissionFailed(audit) from exc
        self._submissions[job.job_id] = Submission(job, selected_id, provider_job_id, selected_caps)
        return job.job_id

    def submission(self, job_id: str) -> Submission:
        if job_id not in self._submissions:
            raise UnknownJob(job_id)
        return self._submissions[job_id]

    def audit(self, job_id: str) -> tuple[ProviderDecision, ...]:
        if job_id not in self._audits:
            raise UnknownJob(job_id)
        return self._audits[job_id]

    def _status_snapshot(self, submission: Submission, snapshot: JobStatus) -> JobStatus:
        try:
            if not isinstance(snapshot, JobStatus):
                raise ValueError("Invalid status snapshot.")
            snapshot.validate()
            if snapshot.job_id != submission.provider_job_id:
                raise ValueError("Status identity mismatch.")
            previous = self._observed_states.get(submission.job.job_id)
            terminals = (JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED)
            if ((previous in terminals and previous is not snapshot.state) or
                    (previous is JobState.RUNNING and snapshot.state is JobState.QUEUED)):
                raise ValueError("Worker status regressed.")
        except ValueError as exc:
            raise InvalidProviderResponse(str(exc)) from exc
        self._observed_states[submission.job.job_id] = snapshot.state
        return replace(snapshot, job_id=submission.job.job_id)

    def status(self, job_id: str) -> JobStatus:
        submission = self.submission(job_id)
        return self._status_snapshot(submission, self._providers[submission.provider_id].status(submission.provider_job_id))

    def cancel(self, job_id: str) -> JobStatus:
        submission = self.submission(job_id)
        if not submission.capabilities.cancellation:
            raise GenerationError("Provider does not support cancellation.")
        return self._status_snapshot(submission, self._providers[submission.provider_id].cancel(submission.provider_job_id))

    def result(self, job_id: str) -> GenerationResult:
        submission = self.submission(job_id)
        if self.status(job_id).state is not JobState.SUCCEEDED:
            raise ResultNotReady("A successful result requires an explicit SUCCEEDED status.")
        result = self._providers[submission.provider_id].result(submission.provider_job_id)
        if (not isinstance(result, GenerationResult) or result.job_id != submission.provider_job_id or
                result.provider_id != submission.provider_id or result.modality is not submission.job.modality or
                type(result.synthetic) is not bool or result.synthetic is not submission.capabilities.synthetic or
                not isinstance(result.artifacts, tuple) or not isinstance(result.data, tuple)):
            raise InvalidProviderResponse("Result identity/modality/type does not match the submitted job.")
        if result.synthetic and not self._policy.allow_synthetic:
            raise InvalidProviderResponse("Synthetic result is not permitted.")
        if not result.synthetic and not result.artifacts:
            raise InvalidProviderResponse("Real successful result must describe output artifacts.")
        if result.synthetic and not result.artifacts and not result.data:
            raise InvalidProviderResponse("Synthetic success must contain structured data or an artifact declaration.")
        keys = []
        for pair in result.data:
            if (not isinstance(pair, tuple) or len(pair) != 2 or not isinstance(pair[0], str) or
                    not pair[0].strip() or not isinstance(pair[1], str)):
                raise InvalidProviderResponse("Result data must contain text key/value pairs.")
            keys.append(pair[0])
        if len(set(keys)) != len(keys):
            raise InvalidProviderResponse("Result data keys must be unique.")
        for artifact in result.artifacts:
            if (not isinstance(artifact, OutputArtifact) or not isinstance(artifact.identifier, str) or
                    not artifact.identifier.strip() or artifact.format != submission.job.output.format or
                    artifact.width != submission.job.output.width or artifact.height != submission.job.output.height):
                raise InvalidProviderResponse("Result artifact does not satisfy requested output requirements.")
            try:
                optional_int(artifact.width, "artifact.width", 1)
                optional_int(artifact.height, "artifact.height", 1)
            except ValueError as exc:
                raise InvalidProviderResponse(str(exc)) from exc
        return replace(result, job_id=job_id)
