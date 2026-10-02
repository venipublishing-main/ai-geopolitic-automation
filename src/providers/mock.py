"""Manually advanced in-memory worker: no files, clocks, network or image calls."""
from __future__ import annotations

from dataclasses import replace

from .contracts import (ActivityState, DuplicateJob, FailureInfo, GenerationJob, GenerationResult,
                        HealthReport, HealthState, InvalidJobTransition, JobState, JobStatus,
                        Modality, MonetaryCost, ProviderCapabilities, ProviderUnavailable,
                        ResourceState, ResultNotReady, UnknownJob, UnsupportedJob,
                        WorkerLocation, capability_rejections, require_text, resource_rejections)


class MockProvider:
    def __init__(self, provider_id: str = "mock", *, fail_jobs: bool = False,
                 capabilities: ProviderCapabilities | None = None, resources: ResourceState | None = None,
                 available: bool = True, healthy: bool = True):
        require_text(provider_id, "provider_id")
        if any(type(value) is not bool for value in (fail_jobs, available, healthy)):
            raise ValueError("Mock controls must be boolean.")
        self._provider_id = provider_id
        self._fail_jobs = fail_jobs
        self._available = available
        self._healthy = healthy
        self._caps = capabilities if capabilities is not None else ProviderCapabilities(
            modalities=(Modality.IMAGE,), output_formats=("png",), image_generation=True,
            reference_images=True, image_editing=True, max_width=4096, max_height=4096,
            cancellation=True, deterministic_seed=True, location=WorkerLocation.LOCAL,
            monetary_cost=MonetaryCost.ZERO_COST, synthetic=True)
        self._caps.validate()
        if not self._caps.synthetic or self._caps.modalities != (Modality.IMAGE,):
            raise ValueError("Mock simulates IMAGE only and must advertise synthetic results.")
        self._resources = resources if resources is not None else ResourceState(
            online=True, activity=ActivityState.IDLE, worker_id=provider_id)
        self._resources.validate()
        self._jobs: dict[str, GenerationJob] = {}
        self._statuses: dict[str, JobStatus] = {}

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def available(self) -> bool:
        return self._available

    def health(self) -> HealthReport:
        return HealthReport(HealthState.HEALTHY if self._healthy else HealthState.UNHEALTHY)

    def capabilities(self) -> ProviderCapabilities:
        return self._caps

    def resource_state(self) -> ResourceState:
        active = next((key for key, value in self._statuses.items()
                       if value.state in (JobState.QUEUED, JobState.RUNNING)), None)
        return replace(self._resources, activity=ActivityState.BUSY, active_job_id=active) if active else self._resources

    def submit(self, job: GenerationJob) -> str:
        job.validate()
        provider_job_id = f"{self.provider_id}:{job.job_id}"
        if provider_job_id in self._jobs:
            raise DuplicateJob(job.job_id)
        if not self.available() or self.health().state is not HealthState.HEALTHY:
            raise ProviderUnavailable("Mock unavailable/unhealthy.")
        reasons = capability_rejections(job, self._caps) + resource_rejections(job, self.resource_state(), self._caps)
        if reasons:
            raise UnsupportedJob(reasons)
        self._jobs[provider_job_id] = job
        self._statuses[provider_job_id] = JobStatus(provider_job_id, JobState.QUEUED, 0)
        return provider_job_id

    def status(self, job_id: str) -> JobStatus:
        if job_id not in self._statuses:
            raise UnknownJob(job_id)
        return self._statuses[job_id]

    def advance(self, job_id: str) -> JobStatus:
        previous = self.status(job_id)
        if previous.state is JobState.QUEUED:
            snapshot = JobStatus(job_id, JobState.RUNNING, 0.5)
        elif previous.state is JobState.RUNNING:
            snapshot = (JobStatus(job_id, JobState.FAILED, failure=FailureInfo("MOCK_FAILURE", "Configured mock failure."))
                        if self._fail_jobs else JobStatus(job_id, JobState.SUCCEEDED, 1))
        else:
            raise InvalidJobTransition("Terminal jobs cannot advance.")
        self._statuses[job_id] = snapshot
        return snapshot

    def cancel(self, job_id: str) -> JobStatus:
        previous = self.status(job_id)
        if not self._caps.cancellation:
            raise UnsupportedJob(("CANCELLATION_UNSUPPORTED",))
        # Idempotent cancellation; completed/failed jobs retain their terminal state.
        if previous.state in (JobState.QUEUED, JobState.RUNNING):
            self._statuses[job_id] = JobStatus(job_id, JobState.CANCELLED)
        return self.status(job_id)

    def result(self, job_id: str) -> GenerationResult:
        if self.status(job_id).state is not JobState.SUCCEEDED:
            raise ResultNotReady("Mock result is available only after SUCCEEDED.")
        job = self._jobs[job_id]
        return GenerationResult(job_id, self.provider_id, job.modality, synthetic=True,
                                data=(("purpose", job.purpose), ("format", job.output.format),
                                      ("width", str(job.output.width)), ("height", str(job.output.height)),
                                      ("seed", str(job.seed))))
