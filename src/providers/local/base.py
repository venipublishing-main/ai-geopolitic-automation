"""Shared inactive adapter behaviour until verified transport integration exists."""
from __future__ import annotations

from dataclasses import dataclass

from ..contracts import (GenerationJob, GenerationResult, HealthReport, HealthState,
                         JobStatus, ProviderCapabilities, ProviderUnavailable, ResourceState,
                         WorkerLocation, require_text)


@dataclass(frozen=True)
class LocalWorkerConfig:
    endpoint: str | None = None
    runtime_path: str | None = None
    worker_id: str | None = None

    def __post_init__(self):
        for name in ("endpoint", "runtime_path", "worker_id"):
            if getattr(self, name) is not None:
                require_text(getattr(self, name), name)


class InactiveLocalProvider:
    """No transport/endpoint assumptions, dependency imports or worker execution."""
    def __init__(self, provider_id: str, config: LocalWorkerConfig | None = None):
        require_text(provider_id, "provider_id")
        self._provider_id = provider_id
        self.config = LocalWorkerConfig() if config is None else config
        if not isinstance(self.config, LocalWorkerConfig):
            raise ValueError("Local adapter requires LocalWorkerConfig.")

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def available(self) -> bool:
        return False

    def health(self) -> HealthReport:
        configured = self.config.endpoint is not None or self.config.runtime_path is not None
        return HealthReport(HealthState.INTEGRATION_PENDING if configured else HealthState.NOT_CONFIGURED,
                            "Phase B seam has no verified worker transport.")

    def capabilities(self) -> ProviderCapabilities:
        # Candidate roles are documentation, not evidence of live capabilities/cost.
        return ProviderCapabilities(location=WorkerLocation.LOCAL)

    def resource_state(self) -> ResourceState:
        return ResourceState(worker_id=self.config.worker_id)

    def submit(self, job: GenerationJob) -> str:
        job.validate()
        raise ProviderUnavailable(self.health().state.value)

    def status(self, job_id: str) -> JobStatus:
        raise ProviderUnavailable(self.health().state.value)

    def result(self, job_id: str) -> GenerationResult:
        raise ProviderUnavailable(self.health().state.value)

    def cancel(self, job_id: str) -> JobStatus:
        raise ProviderUnavailable(self.health().state.value)
