"""Auditable fail-closed routing against in-memory contract doubles only."""
from dataclasses import replace
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.providers.contracts import (ActivityState, DuplicateJob, GenerationJob, GenerationResult,
                                    HealthReport, HealthState, InvalidGenerationJob, JobState, JobStatus,
                                    Modality, MonetaryCost, OutputArtifact, OutputRequirements,
                                    ProviderCapabilities, ResourceRequirements, ResourceState,
                                    ResultNotReady, TraceMetadata, UnknownJob, WorkerLocation)
from src.providers.mock import MockProvider
from src.providers.model_registry import ModelMetadata, ModelRegistry
from src.providers.router import (GenerationRouter, InvalidProviderResponse, NoFreeGenerationProviderAvailable,
                                 RoutingPolicy, SubmissionFailed, ZeroCostPolicy)


def job(**changes):
    return replace(GenerationJob("job-1", Modality.IMAGE, "test-purpose", "Contract fixture brief",
                                 OutputRequirements("png", 1080, 1080),
                                 trace=TraceMetadata("fixture-episode", 2, 1)), **changes)


class RecordedProvider:
    """Contract double for policy/response tests, not a real generation implementation."""
    def __init__(self, provider_id="recorded"):
        self.provider_id = provider_id
        self.is_available = True
        self.health_state = HealthState.HEALTHY
        self.caps = ProviderCapabilities(
            modalities=(Modality.IMAGE,), output_formats=("png",), image_generation=True,
            reference_images=True, image_editing=True, max_width=4096, max_height=4096,
            model_ids=("fixture-model",), default_model_id="fixture-model", cancellation=True,
            deterministic_seed=True, location=WorkerLocation.LOCAL, monetary_cost=MonetaryCost.ZERO_COST)
        self.resources = ResourceState(online=True, activity=ActivityState.IDLE,
                                       available_model_ids=("fixture-model",))
        self.calls = []
        self.submitted = None
        self.worker_job_id = "worker-job-1"
        self.state = JobState.QUEUED

    def available(self):
        self.calls.append("available")
        return self.is_available

    def health(self):
        self.calls.append("health")
        return HealthReport(self.health_state)

    def capabilities(self):
        self.calls.append("capabilities")
        return self.caps

    def resource_state(self):
        self.calls.append("resource_state")
        return self.resources

    def submit(self, submitted):
        self.calls.append("submit")
        self.submitted = submitted
        return self.worker_job_id

    def status(self, worker_job_id):
        assert worker_job_id == self.worker_job_id
        self.calls.append("status")
        return JobStatus(worker_job_id, self.state)

    def result(self, worker_job_id):
        assert worker_job_id == self.worker_job_id
        self.calls.append("result")
        output = self.submitted.output
        return GenerationResult(worker_job_id, self.provider_id, self.submitted.modality,
                                (OutputArtifact("nonexistent-test-output", output.format, output.width, output.height),))

    def cancel(self, worker_job_id):
        self.calls.append("cancel")
        if self.state in (JobState.QUEUED, JobState.RUNNING):
            self.state = JobState.CANCELLED
        return self.status(worker_job_id)


def registry(*providers, **model_changes):
    # Fabricated metadata is confined to tests; the production registry ships empty.
    return ModelRegistry(tuple(replace(ModelMetadata(
        "fixture-model", provider.provider_id, Modality.IMAGE,
        reference_image_support=True, image_edit_support=True,
        licence="TEST-ONLY invented permission", commercial_output_allowed=True,
        attribution_required=False), **model_changes) for provider in providers))


def reasons(router, requested):
    with pytest.raises(NoFreeGenerationProviderAvailable) as caught:
        router.submit(requested)
    assert caught.value.audit == router.audit(requested.job_id)
    return set(caught.value.audit[0].reasons)


@pytest.mark.parametrize("priority", [("a", "b"), ("b", "a")])
def test_configured_priority_selects_exactly_one_provider_without_job_changes(priority):
    a, b = RecordedProvider("a"), RecordedProvider("b")
    router = GenerationRouter((a, b), priority=priority, models=registry(a, b))
    requested = job(seed=123, reference_assets=("test-reference",), image_edit=True)
    assert router.submit(requested) == requested.job_id
    selected = a if priority[0] == "a" else b
    other = b if selected is a else a
    assert selected.submitted is requested and other.submitted is None
    assert selected.calls.count("submit") == 1
    assert router.submission(requested.job_id).provider_job_id == "worker-job-1"
    audit = router.audit(requested.job_id)
    assert [item.provider_id for item in audit] == list(priority)
    assert all(item.eligible and item.reasons == ("ELIGIBLE",) for item in audit)
    assert [item.provider_id for item in audit if item.selected] == [priority[0]]


def test_registration_order_is_default_priority():
    b, a = RecordedProvider("b"), RecordedProvider("a")
    router = GenerationRouter((b, a), models=registry(b, a))
    router.submit(job())
    assert router.submission("job-1").provider_id == "b"


@pytest.mark.parametrize("priority", [("a",), ("a", "a"), ("a", "unknown"), ["a", "b"]])
def test_invalid_priority_is_configuration_error(priority):
    with pytest.raises(ValueError):
        GenerationRouter((RecordedProvider("a"), RecordedProvider("b")), priority=priority)


def test_duplicate_provider_ids_are_rejected():
    with pytest.raises(ValueError):
        GenerationRouter((RecordedProvider(), RecordedProvider()))


def test_invalid_job_is_rejected_before_any_provider_probe():
    provider = RecordedProvider()
    router = GenerationRouter((provider,), models=registry(provider))
    with pytest.raises(InvalidGenerationJob):
        router.submit(job(prompt=""))
    assert provider.calls == []


@pytest.mark.parametrize("field,value", [("is_available", False), ("is_available", "true"),
                                        ("health_state", HealthState.UNHEALTHY), ("health_state", "HEALTHY")])
def test_offline_or_unhealthy_provider_is_skipped(field, value):
    first, second = RecordedProvider("first"), RecordedProvider("second")
    setattr(first, field, value)
    router = GenerationRouter((first, second), models=registry(first, second))
    router.submit(job())
    assert first.submitted is None and second.submitted is not None
    assert not router.audit("job-1")[0].eligible


@pytest.mark.parametrize("caps_change,job_change,code", [
    ({"modalities": ()}, {}, "MODALITY_UNSUPPORTED"),
    ({"image_generation": False}, {}, "MODALITY_UNSUPPORTED"),
    ({"reference_images": False}, {"reference_assets": ("ref",)}, "REFERENCE_IMAGES_UNSUPPORTED"),
    ({"image_editing": False}, {"reference_assets": ("ref",), "image_edit": True}, "IMAGE_EDIT_UNSUPPORTED"),
    ({"cancellation": False}, {"cancellation_required": True}, "CANCELLATION_UNSUPPORTED"),
    ({"deterministic_seed": False}, {"seed": 123}, "DETERMINISTIC_SEED_UNSUPPORTED"),
    ({"output_formats": ()}, {}, "OUTPUT_FORMAT_UNSUPPORTED"),
    ({"max_width": 1000}, {}, "DIMENSIONS_UNSUPPORTED"),
    ({"max_height": 1000}, {}, "DIMENSIONS_UNSUPPORTED"),
    ({"max_width": None}, {}, "DIMENSION_LIMIT_UNKNOWN"),
    ({}, {"model_preference": "unknown"}, "MODEL_UNSUPPORTED"),
])
def test_capability_requirements_cannot_be_dropped(caps_change, job_change, code):
    provider = RecordedProvider()
    provider.caps = replace(provider.caps, **caps_change)
    router = GenerationRouter((provider,), models=registry(provider))
    assert code in reasons(router, job(**job_change))
    assert "submit" not in provider.calls


@pytest.mark.parametrize("resource_change,requirements,code", [
    ({"online": False}, ResourceRequirements(), "RESOURCE_OFFLINE_OR_UNKNOWN"),
    ({"online": None}, ResourceRequirements(), "RESOURCE_OFFLINE_OR_UNKNOWN"),
    ({"activity": ActivityState.UNKNOWN}, ResourceRequirements(), "RESOURCE_ACTIVITY_UNKNOWN"),
    ({"activity": ActivityState.BUSY}, ResourceRequirements(), "RESOURCE_BUSY"),
    ({}, ResourceRequirements(require_gpu=True), "GPU_UNAVAILABLE_OR_UNKNOWN"),
    ({}, ResourceRequirements(min_free_vram_mb=8192), "VRAM_INSUFFICIENT_OR_UNKNOWN"),
    ({"gpu_identity": "fixture-gpu", "free_vram_mb": 4096}, ResourceRequirements(min_free_vram_mb=8192),
     "VRAM_INSUFFICIENT_OR_UNKNOWN"),
    ({}, ResourceRequirements(min_free_ram_mb=8192), "RAM_INSUFFICIENT_OR_UNKNOWN"),
    ({"free_ram_mb": 4096}, ResourceRequirements(min_free_ram_mb=8192), "RAM_INSUFFICIENT_OR_UNKNOWN"),
    ({"available_model_ids": None}, ResourceRequirements(), "MODEL_UNAVAILABLE_OR_UNKNOWN"),
    ({"available_model_ids": ()}, ResourceRequirements(), "MODEL_UNAVAILABLE_OR_UNKNOWN"),
])
def test_resource_requirements_are_independent_from_free_money(resource_change, requirements, code):
    provider = RecordedProvider()
    provider.resources = replace(provider.resources, **resource_change)
    router = GenerationRouter((provider,), models=registry(provider))
    assert provider.caps.monetary_cost is MonetaryCost.ZERO_COST
    assert code in reasons(router, job(resources=requirements))


def test_known_sufficient_resources_and_queue_capacity_can_be_selected():
    provider = RecordedProvider()
    provider.caps = replace(provider.caps, queue_while_busy=True)
    provider.resources = replace(provider.resources, activity=ActivityState.BUSY, gpu_identity="fixture-gpu",
                                 total_vram_mb=16384, free_vram_mb=8192, total_ram_mb=32768, free_ram_mb=16384)
    router = GenerationRouter((provider,), models=registry(provider, min_vram_mb=8192))
    assert router.submit(job(resources=ResourceRequirements(True, 8192, 16384))) == "job-1"


@pytest.mark.parametrize("cost", [MonetaryCost.PAID, MonetaryCost.UNKNOWN])
@pytest.mark.parametrize("job_requires_free", [True, False])
@pytest.mark.parametrize("policy", [RoutingPolicy(), RoutingPolicy.development()])
def test_paid_and_unknown_cost_are_rejected_even_when_job_opts_out(cost, job_requires_free, policy):
    provider = RecordedProvider()
    provider.caps = replace(provider.caps, monetary_cost=cost)
    router = GenerationRouter((provider,), policy=policy, models=registry(provider))
    assert "ZERO_COST_POLICY_REJECTED" in reasons(router, job(zero_cost_required=job_requires_free))
    assert provider.submitted is None


def test_policy_rejects_provider_supplied_override():
    class SpendingPolicy(ZeroCostPolicy):
        def allows(self, cost):
            return True

    with pytest.raises(ValueError):
        RoutingPolicy(monetary=SpendingPolicy())
    assert ZeroCostPolicy().allows(MonetaryCost.ZERO_COST)
    assert not ZeroCostPolicy().allows("ZERO_COST")


def test_no_provider_fails_with_dedicated_error_and_empty_audit():
    router = GenerationRouter(())
    with pytest.raises(NoFreeGenerationProviderAvailable) as caught:
        router.submit(job())
    assert caught.value.audit == ()


def test_multiple_rejection_reasons_are_retained_in_priority_order():
    provider = RecordedProvider()
    provider.is_available = False
    provider.health_state = HealthState.UNHEALTHY
    provider.caps = replace(provider.caps, monetary_cost=MonetaryCost.PAID, reference_images=False)
    provider.resources = replace(provider.resources, online=False)
    router = GenerationRouter((provider,), models=registry(provider))
    codes = reasons(router, job(reference_assets=("ref",)))
    assert {"PROVIDER_UNAVAILABLE", "PROVIDER_UNHEALTHY", "ZERO_COST_POLICY_REJECTED",
            "REFERENCE_IMAGES_UNSUPPORTED", "RESOURCE_OFFLINE_OR_UNKNOWN"} <= codes


def test_mock_requires_explicit_development_policy_but_money_policy_stays_strict():
    mock = MockProvider()
    production = GenerationRouter((mock,))
    assert "SYNTHETIC_PROVIDER_REJECTED" in reasons(production, job())
    development = GenerationRouter((mock,), policy=RoutingPolicy.development())
    app_id = development.submit(job())
    worker_id = development.submission(app_id).provider_job_id
    assert development.status(app_id).state is JobState.QUEUED
    with pytest.raises(ResultNotReady):
        development.result(app_id)
    mock.advance(worker_id)
    assert development.status(app_id).state is JobState.RUNNING
    mock.advance(worker_id)
    result = development.result(app_id)
    assert result.job_id == app_id and result.synthetic and result.artifacts == ()
    assert development.cancel(app_id).state is JobState.SUCCEEDED


def test_router_cancellation_and_failure_information_are_delegated():
    mock = MockProvider(fail_jobs=True)
    router = GenerationRouter((mock,), policy=RoutingPolicy.development())
    first = router.submit(job())
    assert router.cancel(first).state is JobState.CANCELLED
    second = router.submit(job(job_id="second"))
    worker_id = router.submission(second).provider_job_id
    mock.advance(worker_id)
    mock.advance(worker_id)
    assert router.status(second).failure.code == "MOCK_FAILURE"
    with pytest.raises(ResultNotReady):
        router.result(second)


@pytest.mark.parametrize("metadata,code", [
    ({"commercial_output_allowed": None}, "MODEL_COMMERCIAL_PERMISSION_UNPROVEN"),
    ({"commercial_output_allowed": False}, "MODEL_COMMERCIAL_PERMISSION_UNPROVEN"),
    ({"licence": None}, "MODEL_COMMERCIAL_PERMISSION_UNPROVEN"),
    ({"attribution_required": None}, "MODEL_ATTRIBUTION_UNKNOWN"),
    ({"attribution_required": True}, "MODEL_ATTRIBUTION_REQUIRED"),
    ({"known_restrictions": ("unimplemented restriction",)}, "MODEL_RESTRICTIONS_UNHANDLED"),
])
def test_model_permission_metadata_is_enforced_for_production_and_development(metadata, code):
    provider = RecordedProvider()
    for policy in (RoutingPolicy(), RoutingPolicy.development()):
        router = GenerationRouter((provider,), policy=policy, models=registry(provider, **metadata))
        assert code in reasons(router, job())


def test_absent_registry_and_model_reference_support_fail_closed():
    provider = RecordedProvider()
    assert "MODEL_COMMERCIAL_PERMISSION_UNPROVEN" in reasons(GenerationRouter((provider,)), job())
    router = GenerationRouter((provider,), models=registry(provider, reference_image_support=None))
    assert "MODEL_REFERENCE_SUPPORT_UNPROVEN" in reasons(router, job(reference_assets=("ref",)))
    router = GenerationRouter((provider,), models=registry(provider, image_edit_support=False))
    assert "MODEL_EDIT_SUPPORT_UNPROVEN" in reasons(router, job(reference_assets=("ref",), image_edit=True))


def test_attribution_can_be_explicitly_allowed_by_job():
    provider = RecordedProvider()
    router = GenerationRouter((provider,), models=registry(provider, attribution_required=True))
    assert router.submit(job(output=OutputRequirements("png", 1080, 1080, attribution_allowed=True)))


def test_model_minimum_vram_is_enforced_even_without_job_requirement():
    provider = RecordedProvider()
    router = GenerationRouter((provider,), models=registry(provider, min_vram_mb=8192))
    assert "MODEL_VRAM_INSUFFICIENT_OR_UNKNOWN" in reasons(router, job())


@pytest.mark.parametrize("bad_snapshot", [
    {"monetary_cost": "ZERO_COST"}, {"reference_images": "yes"}, {"max_width": -1},
    {"modalities": ("IMAGE",)}, {"model_ids": ["fixture-model"]},
])
def test_malformed_capability_snapshot_is_rejected(bad_snapshot):
    provider = RecordedProvider()
    provider.caps = replace(provider.caps, **bad_snapshot)
    router = GenerationRouter((provider,), models=registry(provider))
    assert "PROVIDER_PROBE_FAILED" in reasons(router, job())


@pytest.mark.parametrize("bad_snapshot", [{"online": "yes"}, {"activity": "IDLE"},
                                         {"total_vram_mb": 10, "free_vram_mb": 20}])
def test_malformed_resource_snapshot_is_rejected(bad_snapshot):
    provider = RecordedProvider()
    provider.resources = replace(provider.resources, **bad_snapshot)
    router = GenerationRouter((provider,), models=registry(provider))
    assert "PROVIDER_PROBE_FAILED" in reasons(router, job())


def test_probe_exception_is_audited_and_lower_priority_provider_can_be_selected():
    class BrokenProbe(RecordedProvider):
        def health(self):
            raise RuntimeError("Probe unavailable")

    broken, good = BrokenProbe("broken"), RecordedProvider("good")
    router = GenerationRouter((broken, good), models=registry(broken, good))
    router.submit(job())
    assert router.audit("job-1")[0].reasons == ("PROVIDER_PROBE_FAILED",)
    assert good.submitted is not None


def test_submit_failure_never_dispatches_fallback_or_retries_same_identity():
    class BrokenSubmit(RecordedProvider):
        def submit(self, submitted):
            self.submitted = submitted  # Worker may have accepted before response failed.
            raise RuntimeError("Lost submission acknowledgement")

    broken, fallback = BrokenSubmit("broken"), RecordedProvider("fallback")
    router = GenerationRouter((broken, fallback), models=registry(broken, fallback))
    with pytest.raises(SubmissionFailed) as caught:
        router.submit(job())
    assert fallback.submitted is None
    assert caught.value.audit[0].selected
    assert "SUBMISSION_FAILED" in router.audit("job-1")[0].reasons
    with pytest.raises(DuplicateJob):
        router.submit(job())


def test_existing_artifact_does_not_make_queued_job_succeed(tmp_path):
    artifact = tmp_path / "existing.png"
    artifact.write_text("Not an image; orchestration must not inspect existence.")

    class ExistingArtifactProvider(RecordedProvider):
        def result(self, worker_job_id):
            return replace(super().result(worker_job_id), artifacts=(OutputArtifact(str(artifact), "png", 1080, 1080),))

    provider = ExistingArtifactProvider()
    router = GenerationRouter((provider,), models=registry(provider))
    router.submit(job())
    with pytest.raises(ResultNotReady):
        router.result("job-1")
    assert "result" not in provider.calls
    provider.state = JobState.SUCCEEDED
    assert router.result("job-1").artifacts[0].identifier == str(artifact)
    # File decoding/visual QA belong to a future artifact consumer, not routing.


@pytest.mark.parametrize("result_change", [
    {"job_id": "other"}, {"provider_id": "other"}, {"modality": Modality.VIDEO},
    {"synthetic": True}, {"artifacts": ()},
    {"artifacts": (OutputArtifact("output", "png", 512, 512),)},
    {"artifacts": (OutputArtifact("output", "webp", 1080, 1080),)},
    {"data": (("key", "a"), ("key", "b"))},
    {"data": (("key", 1),)},
])
def test_successful_result_must_match_original_job(result_change):
    class BadResult(RecordedProvider):
        def result(self, worker_job_id):
            return replace(super().result(worker_job_id), **result_change)

    provider = BadResult()
    router = GenerationRouter((provider,), models=registry(provider))
    router.submit(job())
    provider.state = JobState.SUCCEEDED
    with pytest.raises(InvalidProviderResponse):
        router.result("job-1")


@pytest.mark.parametrize("state", [JobState.RUNNING, JobState.SUCCEEDED, JobState.CANCELLED])
def test_observed_lifecycle_cannot_regress(state):
    provider = RecordedProvider()
    router = GenerationRouter((provider,), models=registry(provider))
    router.submit(job())
    provider.state = state
    router.status("job-1")
    provider.state = JobState.QUEUED
    with pytest.raises(InvalidProviderResponse):
        router.status("job-1")


@pytest.mark.parametrize("snapshot", [JobStatus("wrong", JobState.QUEUED),
                                     JobStatus("worker-job-1", "SUCCEEDED"),
                                     JobStatus("worker-job-1", JobState.FAILED),
                                     JobStatus("worker-job-1", JobState.RUNNING, float("nan"))])
def test_invalid_worker_status_is_rejected(snapshot):
    class BadStatus(RecordedProvider):
        def status(self, worker_job_id):
            return snapshot

    provider = BadStatus()
    router = GenerationRouter((provider,), models=registry(provider))
    router.submit(job())
    with pytest.raises(InvalidProviderResponse):
        router.status("job-1")


@pytest.mark.parametrize("operation", ["status", "result", "cancel", "audit", "submission"])
def test_router_does_not_invent_unknown_jobs(operation):
    with pytest.raises(UnknownJob):
        getattr(GenerationRouter(()), operation)("missing")


def test_malformed_submission_acknowledgement_does_not_trigger_fallback():
    provider, fallback = RecordedProvider("bad"), RecordedProvider("fallback")
    provider.worker_job_id = ""
    router = GenerationRouter((provider, fallback), models=registry(provider, fallback))
    with pytest.raises(SubmissionFailed):
        router.submit(job())
    assert fallback.submitted is None


def test_no_dispatch_rejection_can_be_retried_when_resources_recover():
    provider = RecordedProvider()
    provider.resources = replace(provider.resources, activity=ActivityState.BUSY)
    router = GenerationRouter((provider,), models=registry(provider))
    assert "RESOURCE_BUSY" in reasons(router, job())
    provider.resources = replace(provider.resources, activity=ActivityState.IDLE)
    assert router.submit(job()) == "job-1"
    with pytest.raises(DuplicateJob):
        router.submit(job())


def test_router_rejects_empty_synthetic_success():
    class EmptyMock(MockProvider):
        def result(self, worker_job_id):
            return replace(super().result(worker_job_id), data=())

    mock = EmptyMock()
    router = GenerationRouter((mock,), policy=RoutingPolicy.development())
    app_id = router.submit(job())
    worker_id = router.submission(app_id).provider_job_id
    mock.advance(worker_id)
    mock.advance(worker_id)
    with pytest.raises(InvalidProviderResponse):
        router.result(app_id)
