"""Offline API-shaped fixtures; never evidence of real cloud generation/licensing."""
import base64
from dataclasses import asdict, replace
from datetime import date
import io
import json
from pathlib import Path
import threading
import time
from urllib.error import HTTPError, URLError

from PIL import Image
import pytest

from src import phase_c, phase_c_cloud
from src.control_documents import Blocker, extract_automation_manifest
from src.daily_readiness import DailyBuildReadinessResult
from src.providers.cloud import common
from src.providers.cloud.ai_horde import AIHordeProvider, ANONYMOUS_KEY, HORDE_CANDIDATE, horde_status
from src.providers.cloud.cloudflare_workers_ai import CloudflareConfig, CloudflareWorkersAIProvider
from src.providers.cloud.http import CloudError, CloudHTTP, NoRedirects
from src.providers.cloud.models import CF_MODEL, CF_MODEL_ID, CF_PROVIDER, HORDE_PROVIDER, cloud_registry
from src.providers.contracts import (DuplicateJob, HealthState, JobState, Modality, MonetaryCost,
                                    ResultNotReady, UnsupportedJob, UnknownJob)
from src.providers.model_registry import ModelMetadata, ModelRegistry
from src.providers.router import GenerationRouter, NoFreeGenerationProviderAvailable, SubmissionFailed

SECRET = "test-only-secret-canary"
REMOTE_ID = "00000000-0000-4000-8000-000000000104"


def image(size=1024, format="PNG", uniform=False):
    pixels = Image.new("RGB", (size, size), "white")
    if not uniform:
        pixels.putpixel((4, 4), (0, 0, 0))
    stream = io.BytesIO()
    pixels.save(stream, format)
    return stream.getvalue()


def snapshot(state="queued"):
    return {"done": state in {"success", "cancelled", "failed"}, "faulted": state == "failed",
            "finished": int(state == "success"), "processing": int(state == "running"),
            "waiting": int(state == "queued")}


class Wire:
    def __init__(self):
        self.calls = []
        self.cf_models = {"success": True, "result": [{"name": CF_MODEL_ID}]}
        self.active = [{"name": HORDE_CANDIDATE, "count": 4, "eta": 400, "queued": 100}]
        self.cf_response = ({"success": True, "result": {"image": base64.b64encode(image()).decode()}}, "application/json")
        self.state = snapshot()
        self.generation = {"model": HORDE_CANDIDATE, "censored": False, "state": "ok", "seed": "104",
                           "gen_metadata": [], "img": base64.b64encode(image(format="WEBP")).decode()}
        self.ack = {"id": REMOTE_ID}
        self.error = None
        self.pause = None
        self.on_delete = lambda: setattr(self, "state", snapshot("cancelled"))

    def json(self, method, path, payload=None, *, headers=None):
        self.calls.append((method, path, payload, headers))
        if self.error:
            raise self.error
        if "/models/search" in path:
            return self.cf_models
        if path == "/v2/status/models?type=image":
            return self.active
        if method == "POST":
            return self.ack
        if method == "DELETE":
            before = self.state
            self.on_delete()
            return before  # Official DELETE returns a pre-cancellation snapshot.
        if "/check/" in path:
            return self.state
        return {**self.state, "generations": [self.generation]}

    def request(self, method, path, payload=None, *, headers=None):
        self.calls.append((method, path, payload, headers))
        if self.pause:
            assert self.pause.wait(2), "Test coordinator was not released"
        if self.error:
            raise self.error
        value, kind = self.cf_response
        return (value if isinstance(value, bytes) else json.dumps(value).encode()), kind


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    monkeypatch.setattr(phase_c_cloud, "OUTPUT", tmp_path / "output/phase-c1")
    monkeypatch.delenv("AI_GEOPOLITIC_HORDE_API_KEY", raising=False)
    # Any accidentally unmocked HTTP operation fails this test rather than accessing the network.
    def network_forbidden(*args, **kwargs):
        raise AssertionError("Normal tests must not access the network")
    monkeypatch.setattr("urllib.request.OpenerDirector.open", network_forbidden)


@pytest.fixture
def cf(tmp_path):
    wire = Wire()
    provider = CloudflareWorkersAIProvider(CloudflareConfig("a" * 32, SECRET, True, True),
            artifact_root=tmp_path / "output/phase-c1/cf", transport=wire)
    yield provider, wire
    provider.close()


def horde(tmp_path, *, approved=True, key=None):
    # Explicitly synthetic permission used only to exercise the adapter. Not a shipped licence approval.
    metadata = ModelMetadata(HORDE_CANDIDATE, HORDE_PROVIDER, Modality.IMAGE,
                            licence="TEST FIXTURE ONLY", commercial_output_allowed=True, attribution_required=False)
    wire = Wire()
    provider = AIHordeProvider(api_key=key, artifact_root=tmp_path / "output/phase-c1/horde", transport=wire,
                              models=ModelRegistry((metadata,)) if approved else cloud_registry())
    return provider, wire


def job(provider, **changes):
    return replace(phase_c_cloud.cloud_job(provider, "Text-free engraved infrastructure.", "Ep104", 7), **changes)


def await_terminal(provider, identifier):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        state = provider.status(identifier)
        if state.state in {JobState.SUCCEEDED, JobState.FAILED}:
            return state
        time.sleep(.005)
    pytest.fail("Offline async fixture did not finish")


def current_ready(monkeypatch):
    monkeypatch.setattr(phase_c, "current_production_date", lambda: date(2026, 10, 3))
    monkeypatch.setattr(phase_c_cloud, "current_production_date", lambda: date(2026, 10, 3))
    text = (Path(__file__).parent / "fixtures/daily_readiness/slide_design_valid.txt").read_text(encoding="utf-8")
    manifest = extract_automation_manifest(text)
    manifest.update(episode_id="Ep104", production_date_sast="2026-10-03", source_rnd_date_sast="2026-10-03")
    slide = manifest["slides"][6]
    slide.update(panelists=["thabo_mokoena"], accent_colours={"thabo_mokoena": "#A73528"}, pairing_mode=None,
                 central_relationship=None, shared_ground=None, why_dual=None, panelist_contributions=None,
                 preferred_visual_reasoning_family="material_chain", essential_labels=["Power", "Cooling", "Racks", "Work", "Grid"])
    return DailyBuildReadinessResult("2026-10-03", "READY", "BUILD_READY", (), manifest)


def test_cf_absent_config_no_network():
    wire = Wire()
    provider = CloudflareWorkersAIProvider(CloudflareConfig(), transport=wire)
    try:
        assert provider.health().state is HealthState.NOT_CONFIGURED
        assert not provider.available() and not wire.calls
        assert provider.capabilities().monetary_cost is MonetaryCost.UNKNOWN
    finally:
        provider.close()


@pytest.mark.parametrize("verified,only", [(False, False), (False, True), (True, False)])
def test_working_token_never_implies_free(cf, verified, only):
    provider, wire = cf
    provider.config = CloudflareConfig("a" * 32, SECRET, verified, only)
    assert provider.available()
    assert provider.capabilities().monetary_cost is MonetaryCost.UNKNOWN
    with pytest.raises(UnsupportedJob, match="ZERO_COST"):
        provider.submit(job(provider))
    assert not any(method == "POST" for method, *_ in wire.calls)


@pytest.mark.parametrize("plan,only,expected", [("workers-free", "1", "ZERO_COST"), ("workers-paid", "1", "UNKNOWN"),
                                                ("workers-free", "true", "UNKNOWN"), ("", "", "UNKNOWN")])
def test_explicit_environment_free_gate(monkeypatch, plan, only, expected):
    monkeypatch.setenv("AI_GEOPOLITIC_CLOUDFLARE_PLAN", plan)
    monkeypatch.setenv("AI_GEOPOLITIC_CLOUDFLARE_FREE_ALLOCATION_ONLY", only)
    provider = CloudflareWorkersAIProvider(CloudflareConfig.from_environment(), transport=Wire())
    try:
        assert provider.capabilities().monetary_cost.value == expected
    finally:
        provider.close()


@pytest.mark.parametrize("cost", [MonetaryCost.PAID, MonetaryCost.UNKNOWN])
def test_router_rejects_nonzero_cost(cf, monkeypatch, cost):
    provider, wire = cf
    caps = provider.capabilities()
    monkeypatch.setattr(provider, "capabilities", lambda: replace(caps, monetary_cost=cost))
    with pytest.raises(NoFreeGenerationProviderAvailable):
        GenerationRouter((provider,), models=cloud_registry()).submit(job(provider))
    assert not any(method == "POST" for method, *_ in wire.calls)


def test_exact_approved_schnell_registry_no_horde_or_dev():
    registry = cloud_registry()
    assert registry.get(CF_PROVIDER, CF_MODEL_ID, Modality.IMAGE) == CF_MODEL
    assert CF_MODEL.licence == "Apache-2.0" and CF_MODEL.commercial_output_allowed is True
    assert registry.get(HORDE_PROVIDER, HORDE_CANDIDATE, Modality.IMAGE) is None
    assert registry.get(CF_PROVIDER, "@cf/black-forest-labs/flux-1-dev", Modality.IMAGE) is None


def test_cf_async_mapping_seed_and_truthful_cancel(cf):
    provider, wire = cf
    wire.pause = threading.Event()
    identifier = provider.submit(job(provider, seed=1047))
    try:
        assert provider.status(identifier).state in {JobState.QUEUED, JobState.RUNNING}
        with pytest.raises(ResultNotReady):
            provider.result(identifier)
        assert not provider.capabilities().cancellation
        with pytest.raises(UnsupportedJob, match="CANCELLATION"):
            provider.cancel(identifier)
    finally:
        wire.pause.set()
    assert await_terminal(provider, identifier).state is JobState.SUCCEEDED
    posts = [(path, payload) for method, path, payload, _ in wire.calls if method == "POST"]
    assert len(posts) == 1 and posts[0][0].endswith("/ai/run/" + CF_MODEL_ID)
    assert posts[0][1] == {"prompt": job(provider).prompt, "steps": 4, "width": 1024, "height": 1024, "seed": 1047}
    result = provider.result(identifier)
    assert result.job_id == identifier and not result.synthetic
    assert Path(result.artifacts[0].identifier).is_file()
    assert provider.observations()["free_allocation_available"] is None
    assert SECRET not in repr(provider.config) + json.dumps(provider.observations())


@pytest.mark.parametrize("format", ["PNG", "JPEG", "WEBP"])
def test_cf_binary_output_lossless_pixel_conversion(cf, format):
    provider, wire = cf
    raw = image(format=format)
    wire.cf_response = (raw, "image/" + ("jpeg" if format == "JPEG" else format.lower()))
    identifier = provider.submit(job(provider))
    assert await_terminal(provider, identifier).state is JobState.SUCCEEDED
    with Image.open(io.BytesIO(raw)) as before, Image.open(provider.result(identifier).artifacts[0].identifier) as after:
        assert after.format == "PNG" and after.size == before.size
        assert after.tobytes() == before.convert("RGB").tobytes()


@pytest.mark.parametrize("bad", [None, "", "https://attacker.invalid/image", "%%%", base64.b64encode(b"corrupt").decode()])
def test_cf_bad_image_fails_without_artifact(cf, bad):
    provider, wire = cf
    wire.cf_response = ({"success": True, "result": {"image": bad}}, "application/json")
    identifier = provider.submit(job(provider))
    status = await_terminal(provider, identifier)
    assert status.state is JobState.FAILED and status.failure
    with pytest.raises(ResultNotReady):
        provider.result(identifier)
    assert not provider.artifact_root.exists()


@pytest.mark.parametrize("kind", ["size", "uniform", "empty"])
def test_cf_dimensions_content_empty_fail(cf, kind):
    provider, wire = cf
    raw = b"" if kind == "empty" else image(size=64 if kind == "size" else 1024, uniform=kind == "uniform")
    wire.cf_response = (raw, "image/png")
    assert await_terminal(provider, provider.submit(job(provider))).state is JobState.FAILED
    assert not provider.artifact_root.exists()


@pytest.mark.parametrize("code", ["AUTHENTICATION_REJECTED", "ENTITLEMENT_REJECTED", "RATE_OR_QUOTA_LIMIT", "HTTP_TIMEOUT_OR_UNAVAILABLE"])
def test_cf_structured_terminal_failure_and_no_leak(cf, code):
    provider, wire = cf
    assert provider.available()
    wire.error = CloudError(code)
    identifier = provider.submit(job(provider))
    status = await_terminal(provider, identifier)
    assert status.state is JobState.FAILED and status.failure.code == code
    assert SECRET not in json.dumps(asdict(status)) + json.dumps(provider.observations())
    if code == "ENTITLEMENT_REJECTED":
        assert provider.capabilities().monetary_cost is MonetaryCost.UNKNOWN
    if code == "RATE_OR_QUOTA_LIMIT":
        assert provider.observations()["free_allocation_available"] is False
    if code == "HTTP_TIMEOUT_OR_UNAVAILABLE":
        assert not phase_c_cloud.terminal_failure_proven(status)


@pytest.mark.parametrize("message,code", [("Requires paid billing " + SECRET, "BILLING_OR_PLAN_REQUIRED"),
                                        ("Daily free neurons exhausted " + SECRET, "FREE_QUOTA_EXHAUSTED"),
                                        ("Rejected " + SECRET, "CLOUDFLARE_API_FAILED")])
def test_cf_api_rejections_never_echo_payload(cf, message, code):
    provider, wire = cf
    wire.cf_response = ({"success": False, "errors": [{"message": message}]}, "application/json")
    status = await_terminal(provider, provider.submit(job(provider)))
    assert status.failure.code == code and SECRET not in repr(status)
    if code != "CLOUDFLARE_API_FAILED":
        assert not provider.available()


def test_cf_unknown_model_no_substitution(cf):
    provider, wire = cf
    with pytest.raises(UnsupportedJob):
        provider.submit(job(provider, model_preference="@cf/black-forest-labs/flux-1-dev"))
    assert not any(method == "POST" for method, *_ in wire.calls)


@pytest.mark.parametrize("change", [{"prompt": "a" * 2049}, {"cancellation_required": True}])
def test_cf_limits_enforced_before_dispatch(cf, change):
    provider, wire = cf
    with pytest.raises(UnsupportedJob):
        provider.submit(job(provider, **change))
    assert not any(method == "POST" for method, *_ in wire.calls)


def test_cf_duplicate_identity(cf):
    provider, _ = cf
    await_terminal(provider, provider.submit(job(provider)))
    with pytest.raises(DuplicateJob):
        provider.submit(job(provider))


@pytest.mark.parametrize("key", [None, SECRET])
def test_horde_configuration_and_submit_mapping(tmp_path, key):
    provider, wire = horde(tmp_path, key=key)
    assert provider.capabilities().monetary_cost is MonetaryCost.ZERO_COST
    assert provider.observations()["anonymous"] is (key is None)
    assert provider.submit(job(provider)) == REMOTE_ID
    posts = [(payload, headers) for method, _, payload, headers in wire.calls if method == "POST"]
    assert len(posts) == 1
    payload, headers = posts[0]
    assert headers["apikey"] == (key or ANONYMOUS_KEY)
    assert payload["models"] == [HORDE_CANDIDATE] and payload["params"]["n"] == 1
    assert payload["params"]["steps"] == 4 and payload["params"]["sampler_name"] == "k_euler"
    assert payload["allow_downgrade"] is False and payload["r2"] is False
    assert SECRET not in json.dumps(provider.observations())


@pytest.mark.parametrize("state,expected", [("queued", JobState.QUEUED), ("running", JobState.RUNNING),
                                            ("success", JobState.SUCCEEDED), ("failed", JobState.FAILED)])
def test_horde_status_mapping(state, expected):
    assert horde_status(snapshot(state), REMOTE_ID).state is expected


def test_horde_completed_result_caching_and_metadata(tmp_path):
    provider, wire = horde(tmp_path)
    identifier = provider.submit(job(provider))
    with pytest.raises(ResultNotReady):
        provider.result(identifier)
    wire.state = snapshot("success")
    result = provider.result(identifier)
    assert result is provider.result(identifier)
    assert result.artifacts[0].format == "png" and Path(result.artifacts[0].identifier).is_file()
    assert len([path for _, path, *_ in wire.calls if "/generate/status/" in path]) == 1


@pytest.mark.parametrize("race", [False, True])
def test_horde_cancellation_requires_observed_terminal_no_work(tmp_path, race):
    provider, wire = horde(tmp_path)
    identifier = provider.submit(job(provider))
    wire.state = snapshot("running")
    wire.on_delete = lambda: setattr(wire, "state", snapshot("success" if race else "cancelled"))
    expected = JobState.SUCCEEDED if race else JobState.CANCELLED
    assert provider.cancel(identifier).state is expected
    assert provider.cancel(identifier).state is expected
    assert len([m for m, *_ in wire.calls if m == "DELETE"]) == 1


def test_horde_delete_ack_alone_is_not_cancelled(tmp_path):
    provider, wire = horde(tmp_path)
    identifier = provider.submit(job(provider))
    wire.state = snapshot("running")
    wire.on_delete = lambda: None
    assert provider.cancel(identifier).state is JobState.RUNNING
    assert provider.status(identifier).state is JobState.RUNNING


@pytest.mark.parametrize("approved,active", [(False, True), (True, False)])
def test_horde_unapproved_or_unavailable_blocks_before_post(tmp_path, approved, active):
    provider, wire = horde(tmp_path, approved=approved)
    if not active:
        wire.active = []
    with pytest.raises(UnsupportedJob):
        provider.submit(job(provider))
    assert not any(method == "POST" for method, *_ in wire.calls)


def test_horde_seed_not_overclaimed(tmp_path):
    provider, wire = horde(tmp_path)
    assert not provider.capabilities().deterministic_seed
    with pytest.raises(UnsupportedJob, match="SEED"):
        provider.submit(job(provider, seed=104))
    assert not any(method == "POST" for method, *_ in wire.calls)


@pytest.mark.parametrize("value", [{}, {"id": SECRET}, {"id": 7}, []])
def test_horde_malformed_ack_no_reuse_or_secret(tmp_path, value):
    provider, wire = horde(tmp_path, key=SECRET)
    wire.ack = value
    with pytest.raises(CloudError, match="ACK_INVALID") as caught:
        provider.submit(job(provider))
    assert SECRET not in str(caught.value)
    with pytest.raises(DuplicateJob):
        provider.submit(job(provider))


def test_horde_timeout_after_dispatch_blocks_duplicate_and_fallback(tmp_path):
    provider, wire = horde(tmp_path)
    assert provider.available()
    wire.error = CloudError("HTTP_TIMEOUT_OR_UNAVAILABLE")
    with pytest.raises(CloudError):
        provider.submit(job(provider))
    with pytest.raises(DuplicateJob):
        provider.submit(job(provider))
    assert len([m for m, *_ in wire.calls if m == "POST"]) == 1


@pytest.mark.parametrize("change", [{"model": "different-model"}, {"censored": True}, {"state": "faulted"},
                                    {"img": "https://untrusted.invalid/image"}, {"gen_metadata": None},
                                    {"gen_metadata": [SECRET]}, {"gen_metadata": [{"type": "censorship"}]}])
def test_horde_bad_result_never_written(tmp_path, change):
    provider, wire = horde(tmp_path)
    identifier = provider.submit(job(provider))
    wire.state = snapshot("success")
    wire.generation.update(change)
    with pytest.raises(CloudError) as caught:
        provider.result(identifier)
    assert SECRET not in str(caught.value) and not provider.artifact_root.exists()


@pytest.mark.parametrize("value", [{}, {"done": "true"}, {**snapshot(), "finished": True},
                                  {**snapshot(), "waiting": -1}, {**snapshot("success"), "processing": 1},
                                  snapshot("cancelled"), {**snapshot("success"), "finished": 2}])
def test_horde_malformed_status_fails_closed(value):
    with pytest.raises(CloudError):
        horde_status(value, REMOTE_ID)


def test_cloud_router_never_falls_back_after_lost_ack(cf, tmp_path):
    provider, wire = cf
    other, other_wire = horde(tmp_path)
    # Make Horde first, force a lost POST acknowledgement after a healthy probe.
    assert other.available()
    other_wire.error = CloudError("HTTP_TIMEOUT_OR_UNAVAILABLE")
    registry = ModelRegistry((CF_MODEL, other.models.get(HORDE_PROVIDER, HORDE_CANDIDATE, Modality.IMAGE)))
    router = GenerationRouter((other, provider), models=registry)
    neutral = job(other, model_preference=None)
    with pytest.raises(SubmissionFailed):
        router.submit(neutral)
    assert router.audit(neutral.job_id)[0].selected
    assert len([m for m, *_ in other_wire.calls if m == "POST"]) == 1
    assert not any(method == "POST" for method, *_ in wire.calls)


def test_cloud_current_bridge_uses_ep104_slide7_not_ep103(monkeypatch):
    readiness = current_ready(monkeypatch)
    number, spec, prompt = phase_c_cloud.select_slide(readiness)
    assert number == 7 and spec["slide_number"] == 7
    assert spec["headline"] == readiness.manifest["slides"][6]["headline"]
    assert phase_c.LOCKED_ART in prompt
    with pytest.raises(ValueError):
        phase_c.compile_slide(readiness)


@pytest.mark.parametrize("change", [{"build": "BLOCKED"}, {"production_date_sast": "2026-10-02"},
                                    {"manifest": None}, {"blockers": (Blocker("BLOCK", "stop", "source"),)}])
def test_cloud_readiness_guard_no_dispatch(cf, tmp_path, monkeypatch, change):
    provider, wire = cf
    other, other_wire = horde(tmp_path)
    readiness = replace(current_ready(monkeypatch), **change)
    report = phase_c_cloud.benchmark(readiness, [provider, other], execute=True, episode_hint="Ep104")
    assert report["state"] == "BLOCKED" and report["generation_attempts_total"] == 0
    assert not any(method == "POST" for method, *_ in wire.calls + other_wire.calls)


def test_cloud_dryrun_reports_gate_cost_priority_no_generation(cf, tmp_path, monkeypatch):
    provider, wire = cf
    other, other_wire = horde(tmp_path, approved=False)
    report = phase_c_cloud.benchmark(current_ready(monkeypatch), [other, provider])
    assert report["state"] == "DRY_RUN_READY" and report["selected_provider"] == CF_PROVIDER
    assert report["episode_id"] == "Ep104" and report["selected_slide"] == 7
    assert report["predicted_generation_count"] == 1 and report["generation_attempts_total"] == 0
    assert report["providers"][1]["eligible"] is False
    assert not any(method == "POST" for method, *_ in wire.calls + other_wire.calls)
    assert SECRET not in json.dumps(report)


def test_priority_configurable_and_duplicate_rejected(cf, tmp_path, monkeypatch):
    provider, _ = cf
    other, _ = horde(tmp_path)
    readiness = current_ready(monkeypatch)
    report = phase_c_cloud.benchmark(readiness, [provider, other], priority=(HORDE_PROVIDER, CF_PROVIDER))
    assert report["selected_provider"] == HORDE_PROVIDER
    with pytest.raises(ValueError):
        phase_c_cloud.benchmark(readiness, [provider, other], priority=(CF_PROVIDER, CF_PROVIDER))


def test_shared_cloud_artifact_consumer_one_provider_ceiling(cf, tmp_path, monkeypatch):
    provider, wire = cf
    other, other_wire = horde(tmp_path)
    readiness = current_ready(monkeypatch)
    # Composer is tested by the existing real renderer suite; this test isolates dispatch/handoff.
    def compose(spec, artifact, destination):
        assert spec["slide_number"] == 7 and Path(artifact).is_file()
        destination.write_bytes(image())
    monkeypatch.setattr(phase_c, "compose", compose)
    report = phase_c_cloud.benchmark(readiness, [provider, other], execute=True)
    assert report["state"] == "COMPLETED" and report["generation_attempts_total"] == 1
    assert report["results"][0]["episode_id"] == "Ep104" and report["results"][0]["composition_output"]
    assert len([m for m, *_ in wire.calls if m == "POST"]) == 1
    assert not any(method == "POST" for method, *_ in other_wire.calls)
    second = phase_c_cloud.benchmark(readiness, [provider, other], execute=True, diagnosis="a prettier image")
    assert second["state"] == "BLOCKED" and "GENERATION_BUDGET_BLOCKED" in second["blockers"]


def test_cloud_timeout_consumes_unresolved_budget(cf, tmp_path, monkeypatch):
    provider, wire = cf
    other, _ = horde(tmp_path)
    readiness = current_ready(monkeypatch)
    assert provider.available()
    wire.error = CloudError("HTTP_TIMEOUT_OR_UNAVAILABLE")
    report = phase_c_cloud.benchmark(readiness, [provider, other], execute=True)
    assert report["state"] == "BLOCKED" and report["generation_attempts_total"] == 1
    rows = json.loads((phase_c_cloud.OUTPUT / "attempt-ledger.json").read_text())
    assert rows[0]["outcome"] == "unresolved"
    later = phase_c_cloud.benchmark(readiness, [provider, other], execute=True, diagnosis="timeout")
    assert "GENERATION_BUDGET_BLOCKED" in later["blockers"]


def test_cloud_two_attempt_absolute_ceiling_and_no_comparison(tmp_path):
    ledger = phase_c.AttemptLedger(tmp_path / "ledger.json", providers=(CF_PROVIDER, HORDE_PROVIDER), maximum=2, single_provider=True)
    index, attempt = ledger.reserve(CF_PROVIDER)
    assert attempt == 1
    ledger.finish(index, "technical_failure")
    with pytest.raises(ValueError):
        ledger.reserve(HORDE_PROVIDER, "switch provider")
    with pytest.raises(ValueError):
        ledger.reserve(CF_PROVIDER)
    index, attempt = ledger.reserve(CF_PROVIDER, "decoded artifact had wrong dimensions")
    assert attempt == 2
    ledger.finish(index, "technical_failure")
    with pytest.raises(ValueError, match="CEILING"):
        ledger.reserve(CF_PROVIDER, "third image forbidden")


def test_artifact_path_restricted(cf, tmp_path):
    provider, _ = cf
    provider.artifact_root = tmp_path / "outside"
    assert await_terminal(provider, provider.submit(job(provider))).failure.code == "ARTIFACT_ROOT_REJECTED"
    assert not provider.artifact_root.exists()


@pytest.mark.parametrize("status,code", [(401, "AUTHENTICATION_REJECTED"), (403, "ENTITLEMENT_REJECTED"),
                                        (429, "RATE_OR_QUOTA_LIMIT"), (500, "HTTP_REJECTED")])
def test_http_status_sanitized(monkeypatch, status, code):
    http = CloudHTTP("https://aihorde.net/api")
    def fail(*args, **kwargs):
        raise HTTPError("https://" + SECRET, status, SECRET, {}, io.BytesIO(SECRET.encode()))
    monkeypatch.setattr(http.opener, "open", fail)
    with pytest.raises(CloudError) as caught:
        http.json("POST", "/v2/generate/async", headers={"apikey": SECRET})
    assert str(caught.value) == code and caught.value.status == status
    assert caught.value.__suppress_context__


@pytest.mark.parametrize("error", [TimeoutError(SECRET), URLError(SECRET), OSError(SECRET)])
def test_http_network_errors_sanitized(monkeypatch, error):
    http = CloudHTTP("https://aihorde.net/api")
    monkeypatch.setattr(http.opener, "open", lambda *a, **k: (_ for _ in ()).throw(error))
    with pytest.raises(CloudError, match="HTTP_TIMEOUT_OR_UNAVAILABLE") as caught:
        http.request("POST", "/v2/generate/async")
    assert SECRET not in str(caught.value)


def test_http_bounded_read_and_malformed_json(monkeypatch):
    http = CloudHTTP("https://aihorde.net/api")
    class Response(io.BytesIO):
        headers = {"Content-Type": "application/json"}
    monkeypatch.setattr(http.opener, "open", lambda *a, **k: Response(b"x" * 20))
    with pytest.raises(CloudError, match="TOO_LARGE"):
        http.request("GET", "/v2/status/models", limit=10)
    with pytest.raises(CloudError, match="MALFORMED_JSON"):
        http.json("GET", "/v2/status/models")


@pytest.mark.parametrize("origin,timeout", [("http://aihorde.net/api", 30), ("https://attacker.invalid", 30),
                                          ("https://aihorde.net/api", 0), ("https://aihorde.net/api", 61),
                                          ("https://aihorde.net/api", float("nan"))])
def test_http_origin_timeout_validation(origin, timeout):
    with pytest.raises(ValueError):
        CloudHTTP(origin, timeout)


def test_http_redirect_rejected_and_unknown_jobs(cf, tmp_path):
    with pytest.raises(CloudError, match="REDIRECT_REJECTED"):
        NoRedirects().redirect_request(None, None, None, None, None, None)
    provider, _ = cf
    other, _ = horde(tmp_path)
    for adapter in (provider, other):
        with pytest.raises(UnknownJob):
            adapter.status("not-owned")


def test_cli_defaults_to_dryrun_and_persists_no_secret_report(cf, tmp_path, monkeypatch, capsys):
    provider, wire = cf
    other, other_wire = horde(tmp_path)
    readiness = current_ready(monkeypatch)
    from src.production_inputs import DailyDocuments
    monkeypatch.setattr(phase_c_cloud.RcloneDriveInput, "from_environment", lambda: type("Source", (),
                        {"read": lambda self: DailyDocuments("test", "test")})())
    monkeypatch.setattr(phase_c_cloud.DailyBuildReadiness, "evaluate", lambda *a: readiness)
    monkeypatch.setattr(phase_c_cloud, "CloudflareWorkersAIProvider", lambda: provider)
    monkeypatch.setattr(phase_c_cloud, "AIHordeProvider", lambda: other)
    assert phase_c_cloud.main([]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["mode"] == "DRY_RUN" and report["generation_attempts_total"] == 0
    persisted = (phase_c_cloud.OUTPUT / "benchmark-report.json").read_text()
    assert SECRET not in persisted and json.loads(persisted) == report
    assert not any(m == "POST" for m, *_ in wire.calls + other_wire.calls)


def test_current_missing_manifest_remains_exact_blocker(cf, tmp_path, monkeypatch):
    provider, _ = cf
    other, _ = horde(tmp_path, approved=False)
    current_ready(monkeypatch)
    readiness = DailyBuildReadinessResult("2026-10-03", "BLOCKED", "BUILD_BLOCKED",
                         (Blocker("AUTOMATION_MANIFEST_MISSING", "missing", "manifest"),))
    report = phase_c_cloud.benchmark(readiness, [provider, other], episode_hint="Ep104", execute=True)
    assert report["episode_id"] == "Ep104" and report["episode_source"] == "human_metadata_only"
    assert report["selected_slide"] is None and report["predicted_generation_count"] == 0
    assert "AUTOMATION_MANIFEST_MISSING" in report["blockers"]


def test_live_scene_family_cannot_be_overridden(cf, monkeypatch):
    readiness = current_ready(monkeypatch)
    readiness.manifest["slides"][6]["preferred_visual_reasoning_family"] = "power_map"
    with pytest.raises(ValueError):
        phase_c_cloud.select_slide(readiness, 7)


def test_horde_delete_timeout_does_not_claim_cancelled(tmp_path):
    provider, wire = horde(tmp_path)
    identifier = provider.submit(job(provider))
    wire.state = snapshot("running")
    original = wire.json
    def fail_delete(method, *args, **kwargs):
        if method == "DELETE":
            raise CloudError("HTTP_TIMEOUT_OR_UNAVAILABLE")
        return original(method, *args, **kwargs)
    wire.json = fail_delete
    with pytest.raises(CloudError):
        provider.cancel(identifier)
    assert provider.status(identifier).state is JobState.RUNNING
    assert provider._jobs[identifier]["cancel_ack"] is False


@pytest.mark.parametrize("dimensions", [(63, 64), (100, 128), (3136, 3136)])
def test_horde_dimensions_block_before_submission(tmp_path, dimensions):
    from src.providers.contracts import OutputRequirements
    provider, wire = horde(tmp_path)
    with pytest.raises(UnsupportedJob):
        provider.submit(job(provider, output=OutputRequirements("png", *dimensions)))
    assert not any(m == "POST" for m, *_ in wire.calls)


@pytest.mark.parametrize("metadata", [{"commercial_output_allowed": False}, {"commercial_output_allowed": None},
                                     {"licence": None}, {"attribution_required": None},
                                     {"attribution_required": True}, {"known_restrictions": ("unhandled condition",)}])
def test_horde_licence_unknown_restrictions_attribution_fail_closed(tmp_path, metadata):
    provider, wire = horde(tmp_path)
    entry = provider.models.get(HORDE_PROVIDER, HORDE_CANDIDATE, Modality.IMAGE)
    provider.models = ModelRegistry((replace(entry, **metadata),))
    assert not provider.observations()["licence_approved"]
    with pytest.raises(UnsupportedJob):
        provider.submit(job(provider))
    assert not any(m == "POST" for m, *_ in wire.calls)


def test_http_unicode_header_error_sanitized(monkeypatch):
    http = CloudHTTP("https://aihorde.net/api")
    def fail(*args, **kwargs):
        raise UnicodeEncodeError("ascii", SECRET + "\N{SNOWMAN}", 0, 1, "bad header")
    monkeypatch.setattr(http.opener, "open", fail)
    with pytest.raises(CloudError, match="HTTP_REQUEST_REJECTED") as caught:
        http.request("POST", "/v2/generate/async", headers={"apikey": SECRET})
    assert SECRET not in str(caught.value)


@pytest.mark.parametrize("response", [b"invalid-json", {}, [], {"success": "true"}, {"success": None}, {"success": 0},
                                      {"success": True, "errors": [{"message": SECRET}]}])
def test_cf_malformed_success_ack_never_proves_retry_safe(cf, response):
    provider, wire = cf
    wire.cf_response = (response, "application/json")
    status = await_terminal(provider, provider.submit(job(provider)))
    assert status.state is JobState.FAILED and status.failure.code == "CLOUDFLARE_RESPONSE_MALFORMED"
    assert not phase_c_cloud.terminal_failure_proven(status)
    assert not provider.available() and provider.capabilities().monetary_cost is MonetaryCost.UNKNOWN
    assert SECRET not in repr(status) and not provider.artifact_root.exists()
