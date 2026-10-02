"""Offline Phase B contracts/lifecycle checks; no synthetic visual files."""
from dataclasses import replace
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.providers.contracts import (ActivityState, DuplicateJob, GenerationJob, HealthState,
                                    InvalidGenerationJob, InvalidJobTransition, JobState, Modality,
                                    MonetaryCost, OutputRequirements, ProviderUnavailable,
                                    ResourceRequirements, ResourceState, ResultNotReady, TraceMetadata,
                                    UnknownJob, UnsupportedJob)
from src.providers.local.base import LocalWorkerConfig
from src.providers.local.comfyui import ComfyUIProvider
from src.providers.local.wangp import WanGPProvider
from src.providers.mock import MockProvider
from src.providers.model_registry import ModelMetadata, ModelRegistry


def job(**changes):
    return replace(GenerationJob("episode-slide-attempt-1", Modality.IMAGE, "context illustration",
                                 "Engineering contract test brief", OutputRequirements("png", 1080, 1080),
                                 trace=TraceMetadata("test-episode", 2, 1)), **changes)


@pytest.mark.parametrize("changes", [
    {"job_id": ""}, {"job_id": 1}, {"purpose": " "}, {"prompt": None},
    {"modality": "IMAGE"}, {"modality": "TEXT"}, {"output": {}},
    {"output": OutputRequirements("", 100, 100)},
    {"output": OutputRequirements("png", 0, 100)},
    {"output": OutputRequirements("png", True, 100)},
    {"output": OutputRequirements("png", 100, None)},
    {"output": OutputRequirements("png")},
    {"output": OutputRequirements("png", 100, 100, attribution_allowed="yes")},
    {"seed": -1}, {"seed": True}, {"seed": 1.5},
    {"model_preference": ""}, {"reference_assets": ["asset-id"]},
    {"reference_assets": ("",)}, {"reference_assets": ("asset", "asset")},
    {"image_edit": True}, {"image_edit": "yes"}, {"zero_cost_required": 0},
    {"cancellation_required": 1}, {"trace": {}},
    {"trace": TraceMetadata(slide_number=0)}, {"trace": TraceMetadata(attempt=None)},
    {"trace": TraceMetadata(tags=(("key", "a"), ("key", "b")))},
    {"trace": TraceMetadata(tags=(("key",),))},
    {"trace": TraceMetadata(tags=(("key", ""),))},
    {"resources": {}}, {"resources": ResourceRequirements(require_gpu=1)},
    {"resources": ResourceRequirements(min_free_vram_mb=-1)},
    {"resources": ResourceRequirements(min_free_ram_mb=True)},
])
def test_invalid_jobs_are_rejected(changes):
    with pytest.raises(InvalidGenerationJob):
        job(**changes).validate()


@pytest.mark.parametrize("modality,output", [
    (Modality.IMAGE, OutputRequirements("png", 1080, 1080)),
    (Modality.VIDEO, OutputRequirements("mp4", 1080, 1920)),
    (Modality.AUDIO, OutputRequirements("wav")),
])
def test_neutral_contract_accepts_future_modality_vocabulary(modality, output):
    job(modality=modality, output=output).validate()


def test_audio_rejects_image_dimensions_and_editing():
    with pytest.raises(InvalidGenerationJob):
        job(modality=Modality.AUDIO).validate()
    with pytest.raises(InvalidGenerationJob):
        job(modality=Modality.AUDIO, output=OutputRequirements("wav"),
            image_edit=True, reference_assets=("reference",)).validate()


def test_mock_lifecycle_is_explicit_and_creates_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    worker = MockProvider()
    original = job(seed=42, reference_assets=("unresolved-test-reference",))
    worker_id = worker.submit(original)
    assert worker_id == "mock:episode-slide-attempt-1"
    assert worker.status(worker_id).state is JobState.QUEUED
    assert worker.status(worker_id).state is JobState.QUEUED  # Polling does not advance.
    assert worker.resource_state().activity is ActivityState.BUSY
    with pytest.raises(ResultNotReady):
        worker.result(worker_id)
    assert worker.advance(worker_id).state is JobState.RUNNING
    with pytest.raises(ResultNotReady):
        worker.result(worker_id)
    assert worker.advance(worker_id).state is JobState.SUCCEEDED
    result = worker.result(worker_id)
    assert result.synthetic and result.artifacts == ()
    assert dict(result.data)["seed"] == "42"
    assert worker.result(worker_id) == result
    assert worker.resource_state().activity is ActivityState.IDLE
    assert list(tmp_path.iterdir()) == []
    with pytest.raises(InvalidJobTransition):
        worker.advance(worker_id)
    with pytest.raises(DuplicateJob):
        worker.submit(original)


def test_mock_is_reproducible_across_independent_workers():
    workers = (MockProvider(), MockProvider())
    results = []
    for worker in workers:
        worker_id = worker.submit(job(seed=123))
        worker.advance(worker_id)
        worker.advance(worker_id)
        results.append(worker.result(worker_id))
    assert results[0] == results[1]


def test_failed_job_retains_failure_without_successful_result():
    worker = MockProvider(fail_jobs=True)
    worker_id = worker.submit(job())
    worker.advance(worker_id)
    failed = worker.advance(worker_id)
    assert failed.state is JobState.FAILED
    assert failed.failure.code == "MOCK_FAILURE"
    assert failed.failure.message == "Configured mock failure."
    assert worker.cancel(worker_id) == failed
    with pytest.raises(ResultNotReady):
        worker.result(worker_id)
    with pytest.raises(InvalidJobTransition):
        worker.advance(worker_id)


@pytest.mark.parametrize("advance_count,expected", [(0, JobState.CANCELLED), (1, JobState.CANCELLED),
                                                   (2, JobState.SUCCEEDED)])
def test_cancellation_and_completed_job_behaviour(advance_count, expected):
    worker = MockProvider()
    worker_id = worker.submit(job())
    for _ in range(advance_count):
        worker.advance(worker_id)
    snapshot = worker.cancel(worker_id)
    assert snapshot.state is expected
    assert worker.cancel(worker_id) == snapshot
    if expected is JobState.CANCELLED:
        with pytest.raises(ResultNotReady):
            worker.result(worker_id)


@pytest.mark.parametrize("operation", ["status", "advance", "result", "cancel"])
def test_unknown_mock_job_is_not_invented(operation):
    with pytest.raises(UnknownJob):
        getattr(MockProvider(), operation)("missing")


@pytest.mark.parametrize("modality,output", [(Modality.VIDEO, OutputRequirements("mp4", 100, 100)),
                                           (Modality.AUDIO, OutputRequirements("wav"))])
def test_mock_only_simulates_image_jobs(modality, output):
    with pytest.raises(UnsupportedJob) as caught:
        MockProvider().submit(job(modality=modality, output=output))
    assert "MODALITY_UNSUPPORTED" in caught.value.reasons


@pytest.mark.parametrize("caps_change,job_change,code", [
    ({"reference_images": False}, {"reference_assets": ("ref",)}, "REFERENCE_IMAGES_UNSUPPORTED"),
    ({"image_editing": False}, {"reference_assets": ("ref",), "image_edit": True}, "IMAGE_EDIT_UNSUPPORTED"),
    ({"deterministic_seed": False}, {"seed": 42}, "DETERMINISTIC_SEED_UNSUPPORTED"),
    ({"cancellation": False}, {"cancellation_required": True}, "CANCELLATION_UNSUPPORTED"),
    ({"max_width": 100}, {}, "DIMENSIONS_UNSUPPORTED"),
    ({"max_height": None}, {}, "DIMENSION_LIMIT_UNKNOWN"),
    ({"output_formats": ("webp",)}, {}, "OUTPUT_FORMAT_UNSUPPORTED"),
    ({}, {"model_preference": "unknown"}, "MODEL_UNSUPPORTED"),
])
def test_mock_rejects_unsupported_requirements(caps_change, job_change, code):
    caps = replace(MockProvider().capabilities(), **caps_change)
    worker = MockProvider(capabilities=caps)
    with pytest.raises(UnsupportedJob) as caught:
        worker.submit(job(**job_change))
    assert code in caught.value.reasons


def test_zero_marginal_cost_does_not_fabricate_compute_resources():
    worker = MockProvider()
    assert worker.capabilities().monetary_cost is MonetaryCost.ZERO_COST
    resources = worker.resource_state()
    assert resources.gpu_identity is resources.total_vram_mb is resources.free_vram_mb is None
    with pytest.raises(UnsupportedJob) as caught:
        worker.submit(job(resources=ResourceRequirements(require_gpu=True, min_free_vram_mb=8192)))
    assert "GPU_UNAVAILABLE_OR_UNKNOWN" in caught.value.reasons
    assert "VRAM_INSUFFICIENT_OR_UNKNOWN" in caught.value.reasons


def test_mock_has_finite_capacity_and_explicit_queue_support():
    worker = MockProvider()
    first = worker.submit(job())
    with pytest.raises(UnsupportedJob) as caught:
        worker.submit(job(job_id="second"))
    assert "RESOURCE_BUSY" in caught.value.reasons
    worker.cancel(first)
    assert worker.submit(job(job_id="second"))
    queue_worker = MockProvider(capabilities=replace(worker.capabilities(), queue_while_busy=True))
    queue_worker.submit(job())
    assert queue_worker.submit(job(job_id="second"))


@pytest.mark.parametrize("controls", [{"available": False}, {"healthy": False}])
def test_direct_mock_submission_checks_availability(controls):
    with pytest.raises(ProviderUnavailable):
        MockProvider(**controls).submit(job())


def test_mock_cancellation_requires_advertised_support():
    worker = MockProvider(capabilities=replace(MockProvider().capabilities(), cancellation=False))
    worker_id = worker.submit(job())
    with pytest.raises(UnsupportedJob):
        worker.cancel(worker_id)
    assert worker.status(worker_id).state is JobState.QUEUED


@pytest.mark.parametrize("provider_class", [WanGPProvider, ComfyUIProvider])
@pytest.mark.parametrize("configured", [False, True])
def test_local_seams_are_inert_even_with_config(provider_class, configured, monkeypatch):
    import socket
    import subprocess

    def forbidden(*args, **kwargs):
        raise AssertionError("No network or process may run in a Phase B seam.")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    config = LocalWorkerConfig(endpoint="http://uncontacted.invalid", runtime_path="not-installed",
                               worker_id="household-pc") if configured else None
    provider = provider_class(config)
    assert provider.available() is False
    assert provider.health().state is (HealthState.INTEGRATION_PENDING if configured else HealthState.NOT_CONFIGURED)
    assert provider.capabilities().modalities == ()
    assert provider.capabilities().monetary_cost is MonetaryCost.UNKNOWN
    assert provider.resource_state().online is None
    for operation in (lambda: provider.submit(job()), lambda: provider.status("job"),
                      lambda: provider.result("job"), lambda: provider.cancel("job")):
        with pytest.raises(ProviderUnavailable):
            operation()


def test_registry_is_empty_and_provider_scoped():
    empty = ModelRegistry()
    assert empty.get("test-provider", "test-model", Modality.IMAGE) is None
    entry = ModelMetadata("test-model", "test-provider", Modality.IMAGE)
    registry = ModelRegistry((entry,))
    assert registry.get("test-provider", "test-model", Modality.IMAGE) == entry
    assert registry.get("other", "test-model", Modality.IMAGE) is None
    assert registry.get("test-provider", "test-model", Modality.VIDEO) is None
    with pytest.raises(ValueError):
        ModelRegistry((entry, entry))


@pytest.mark.parametrize("changes", [
    {"model_id": ""}, {"provider": ""}, {"modality": "IMAGE"},
    {"min_vram_mb": -1}, {"min_vram_mb": 8, "preferred_vram_mb": 4},
    {"commercial_output_allowed": "yes"}, {"attribution_required": 0},
    {"benchmark_score": float("nan")}, {"benchmark_score": -1},
    {"known_restrictions": ["unreviewed"]}, {"licence": ""},
])
def test_invalid_model_metadata_is_rejected(changes):
    with pytest.raises(ValueError):
        ModelRegistry((replace(ModelMetadata("test-model", "test-provider", Modality.IMAGE), **changes),))
