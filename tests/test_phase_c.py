"""Offline engineering fixtures, not claims of a real GPU/model benchmark."""
from dataclasses import replace
from datetime import date
import hashlib
import io
import json
from pathlib import Path

from PIL import Image
import pytest

from src import phase_c
from src.control_documents import Blocker, extract_automation_manifest
from src.daily_readiness import DailyBuildReadinessResult
from src.providers.contracts import (ActivityState, DuplicateJob, JobState, Modality, ProviderUnavailable,
                                    ResourceState, ResultNotReady, UnsupportedJob)
from src.providers.local.base import LocalWorkerConfig
from src.providers.local.comfyui import ComfyUIProvider, comfy_status, local_workflow
from src.providers.local.image import ImageProfile, inspect_png
from src.providers.local.transport import LocalHTTP, MCPClient, MalformedResponse, TransportError, localhost_url
from src.providers.local.wangp import WanGPProvider, wangp_status
from src.providers.model_registry import ModelMetadata

FIXTURES = Path(__file__).parent / "fixtures/daily_readiness"


def ready(monkeypatch):
    monkeypatch.setattr(phase_c, "current_production_date", lambda: date(2026, 10, 1))
    manifest = extract_automation_manifest((FIXTURES / "slide_design_valid.txt").read_text(encoding="utf-8"))
    # Deliberately synthetic benchmark identity/copy, only within this test.
    manifest["episode_id"] = "Ep103"
    slide = manifest["slides"][11]
    slide.update(panelists=["thabo_mokoena"], accent_colours={"thabo_mokoena": "#A73528"}, pairing_mode=None,
                 central_relationship=None, shared_ground=None, why_dual=None, panelist_contributions=None,
                 essential_labels=["Power", "Cooling", "Racks", "Workers", "Grid"])
    return DailyBuildReadinessResult("2026-10-01", "READY", "BUILD_READY", (), manifest)


def png(path=None):
    image = Image.new("RGB", (64, 64), "white")
    image.putpixel((5, 5), (0, 0, 0))
    stream = io.BytesIO()
    image.save(stream, "PNG")
    if path:
        path.write_bytes(stream.getvalue())
    return stream.getvalue()


def profile(tmp_path, provider):
    model = tmp_path / "test-only-weights.bin"
    model.write_bytes(b"fixture; not model weights")
    revision = "test-version"
    if provider == "wangp":
        (tmp_path / "shared").mkdir(exist_ok=True)
        source = tmp_path / "shared/mcp_v2.py"
        source.write_bytes(b"test-only revision fixture")
        revision = hashlib.sha256(source.read_bytes()).hexdigest()
    return ImageProfile(ModelMetadata("fixture-model", provider, Modality.IMAGE, min_vram_mb=1,
                                      licence="fixture-only licence", commercial_output_allowed=True, attribution_required=False),
                        ("https://example.org/test-fixture-not-model-evidence",), revision, 64, 64,
                        seed_supported=True, cancellation_verified=True, local_execution_verified=True,
                        required_model_files=(str(model),))


def w_snapshot(done=False, success=False, cancelled=False):
    return {"job_id": "00000000-0000-4000-8000-000000000012", "done": done, "cancel_requested": False,
            "result": {"success": success, "cancelled": cancelled, "generated_files": []} if done else None}


class FakeMCP:
    def __init__(self):
        self.calls = []
        self.snapshot = w_snapshot()

    def list_tools(self):
        return [{"name": name, "inputSchema": {"properties": {"wait": {"type": "boolean"}}}}
                for name in ("wangp_models", "wangp_model", "wangp_generate", "wangp_session")]

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "wangp_models":
            return {"models": [{"model_type": "fixture-model"}], "has_more": False}
        if name == "wangp_model":
            return {"capabilities": {"metadata": {"main_output": ["image"]}},
                    "defaults": {"resolution": "64x64", "seed": 0}, "definition": {}}[arguments["action"]]
        if name == "wangp_generate":
            return self.snapshot
        if "arguments" not in arguments:
            return {"action": {"parameters": {"properties": {"job_id": {"type": "string"}}}}}
        if arguments["action"] == "list_queue":
            return {"queued_count": 0, "running_count": 0}
        return self.snapshot


class FakeHTTP:
    def __init__(self):
        self.calls = []
        self.snapshot = {"id": "00000000-0000-4000-8000-000000000012", "status": "in_progress"}
        numeric = lambda lo, hi, step=1: ["INT", {"min": lo, "max": hi, "step": step}]
        self.nodes = {name: {"python_module": "nodes"} for name in
                      ("CheckpointLoaderSimple", "CLIPTextEncode", "EmptyLatentImage", "KSampler", "VAEDecode", "SaveImage")}
        self.nodes["CheckpointLoaderSimple"]["input"] = {"required": {"ckpt_name": [["fixture-model"]]}}
        self.nodes["EmptyLatentImage"]["input"] = {"required": {"width": numeric(8, 4096, 8), "height": numeric(8, 4096, 8)}}
        self.nodes["KSampler"]["input"] = {"required": {"seed": numeric(0, 2**64-1), "steps": numeric(1, 100),
                                                        "cfg": ["FLOAT", {"min": 0, "max": 100, "step": 0.1}],
                                                        "sampler_name": [["euler"]], "scheduler": [["normal"]]}}

    def json(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if path == "/system_stats":
            return {"system": {"comfyui_version": "test-version", "ram_total": 1024**3, "ram_free": 1024**3},
                    "devices": [{"name": "fixture GPU", "type": "cuda", "vram_total": 1024**3, "vram_free": 1024**3}]}
        if path == "/object_info":
            return self.nodes
        if path.startswith("/api/jobs?"):
            return {"jobs": []}
        if path == "/queue":
            return {"queue_running": [], "queue_pending": []}
        if path == "/prompt":
            return {"prompt_id": "00000000-0000-4000-8000-000000000012", "node_errors": {}}
        if path.endswith("/cancel"):
            return {"cancelled": True}
        return self.snapshot

    def request(self, method, path, **kwargs):
        self.calls.append((method, path, None))
        return png(), {}


def worker(tmp_path, name):
    p = profile(tmp_path, name)
    if name == "wangp":
        transport = FakeMCP()
        adapter = WanGPProvider(LocalWorkerConfig(endpoint="http://127.0.0.1:7866/mcp", runtime_path=str(tmp_path)),
                                profile=p, artifact_root=tmp_path, transport=transport,
                                resource_reader=lambda: ResourceState(gpu_identity="fixture GPU", total_vram_mb=1024, free_vram_mb=1024))
    else:
        transport = FakeHTTP()
        adapter = ComfyUIProvider(LocalWorkerConfig(endpoint="http://127.0.0.1:8188"), profile=p,
                                  artifact_root=tmp_path, transport=transport)
    return adapter, transport


@pytest.mark.parametrize("done,success,cancelled,state", [(False, False, False, JobState.RUNNING),
    (True, True, False, JobState.SUCCEEDED), (True, False, True, JobState.CANCELLED), (True, False, False, JobState.FAILED)])
def test_wangp_mapping(done, success, cancelled, state):
    assert wangp_status(w_snapshot(done, success, cancelled), "00000000-0000-4000-8000-000000000012").state is state


@pytest.mark.parametrize("change", [{"job_id": "wrong"}, {"done": 1}, {"cancel_requested": None},
                                   {"done": True, "result": None}, {"done": True, "result": {"success": True, "cancelled": True}}])
def test_wangp_malformed(change):
    with pytest.raises(MalformedResponse):
        wangp_status({**w_snapshot(), **change}, "00000000-0000-4000-8000-000000000012")


@pytest.mark.parametrize("state", ["pending", "in_progress", "completed", "failed", "cancelled"])
def test_comfy_mapping(state):
    snapshot = {"id": "00000000-0000-4000-8000-000000000012", "status": state, "execution_status": {"status_str": "success", "completed": True}}
    comfy_status(snapshot, "00000000-0000-4000-8000-000000000012").validate()


@pytest.mark.parametrize("snapshot", [{}, {"id": "wrong", "status": "pending"}, {"id": "00000000-0000-4000-8000-000000000012", "status": "completed"},
                                      {"id": "00000000-0000-4000-8000-000000000012", "status": "completed", "execution_status": {"status_str": "error", "completed": True}}])
def test_comfy_malformed(snapshot):
    with pytest.raises(MalformedResponse):
        comfy_status(snapshot, "00000000-0000-4000-8000-000000000012")


@pytest.mark.parametrize("name", ["wangp", "comfyui"])
def test_real_adapter_lifecycle_with_offline_fixture(tmp_path, name):
    adapter, transport = worker(tmp_path, name)
    assert adapter.available()
    job = phase_c.generation_job(adapter, "test fixture prompt", seed=123)
    identifier = adapter.submit(job)
    assert identifier == "00000000-0000-4000-8000-000000000012"
    assert adapter.status(identifier).state is JobState.RUNNING
    with pytest.raises(ResultNotReady):
        adapter.result(identifier)
    assert adapter.cancel(identifier).state is JobState.RUNNING  # ACK does not imply terminal cancellation.
    with pytest.raises(DuplicateJob):
        adapter.submit(job)
    if name == "wangp":
        artifact = tmp_path / "result.png"
        png(artifact)
        transport.snapshot = w_snapshot(True, True)
        transport.snapshot["result"]["generated_files"] = [str(artifact)]
    else:
        transport.snapshot = {"id": identifier, "status": "completed", "execution_status": {"status_str": "success", "completed": True},
                              "outputs": {"7": {"images": [{"filename": "test.png", "subfolder": "", "type": "output"}]}}}
    result = adapter.result(identifier)
    assert result.provider_id == name and len(result.artifacts) == 1
    assert Path(result.artifacts[0].identifier).is_file()
    assert adapter.result(identifier) == result  # Result retrieval is repeatable.


@pytest.mark.parametrize("name", ["wangp", "comfyui"])
def test_missing_model_files_fail_closed(tmp_path, name):
    adapter, _ = worker(tmp_path, name)
    Path(adapter.profile.required_model_files[0]).unlink()
    assert not adapter.available()
    with pytest.raises(ProviderUnavailable):
        adapter.submit(phase_c.generation_job(adapter, "fixture"))


@pytest.mark.parametrize("change", [{"commercial_output_allowed": None}, {"commercial_output_allowed": False},
                                    {"licence": None}, {"attribution_required": None}, {"min_vram_mb": None},
                                    {"known_restrictions": ("unhandled",)}])
def test_unproven_model_profiles_rejected(tmp_path, change):
    p = profile(tmp_path, "wangp")
    with pytest.raises(ValueError):
        replace(p, model=replace(p.model, **change)).validate("wangp")


@pytest.mark.parametrize("endpoint", ["https://localhost:8188", "http://example.org", "http://127.0.0.1@external.example",
                                     "http://localhost:8188/?token=secret", "http://127.0.0.1:8188/#secret", "http://192.168.1.2:8188"])
def test_localhost_boundary(endpoint):
    with pytest.raises(ValueError):
        localhost_url(endpoint)


def test_transport_unavailable(monkeypatch):
    client = LocalHTTP("http://127.0.0.1:8188")
    monkeypatch.setattr(client._opener, "open", lambda *a, **k: (_ for _ in ()).throw(OSError("fixture unreachable")))
    with pytest.raises(TransportError):
        client.json("GET", "/system_stats")


def test_mcp_handshake_and_tool_json():
    class Wire:
        def request(self, method, path="", payload=None, **kwargs):
            result = {"protocolVersion": "2025-06-18"} if payload["method"] == "initialize" else {"content": [{"type": "text", "text": '{"job_id":"real-shaped-fixture"}'}]}
            return json.dumps({"jsonrpc": "2.0", "id": payload.get("id"), "result": result}).encode(), {"Mcp-Session-Id": "private-test-session"}
    client = MCPClient("http://127.0.0.1:7866/mcp", http=Wire())
    assert client.call_tool("test", {}) == {"job_id": "real-shaped-fixture"}


def test_compiler_exact_copy_and_prompt(monkeypatch):
    readiness = ready(monkeypatch)
    spec, prompt = phase_c.compile_slide(readiness)
    slide = readiness.manifest["slides"][11]
    assert spec["headline"] == slide["headline"] and spec["quote"] == slide["main_visual_phrase"]
    assert spec["deck"] == slide["subheadline"] and spec["takeaway"] == slide["core_argument"]
    assert spec["facts"] == [v["idea"] for v in slide["takeaway_ideas"]]
    assert spec["slide_number"] == 12 and spec["total_slides"] == 20
    assert phase_c.compile_slide(readiness) == (spec, prompt)
    assert slide["hero_visual"] in prompt and phase_c.LOCKED_ART in prompt
    assert "TEXT-FREE" in prompt and "no panelist portrait" in prompt.lower()


@pytest.mark.parametrize("change", [{"build": "BLOCKED"}, {"state": "BUILD_BLOCKED"}, {"production_date_sast": "2026-09-30"},
                                   {"blockers": (Blocker("TEST", "blocked", "test"),)}, {"manifest": None}])
def test_compiler_readiness_cannot_bypass(monkeypatch, change):
    with pytest.raises(ValueError):
        phase_c.compile_slide(replace(ready(monkeypatch), **change))


@pytest.mark.parametrize("change", [{"episode_id": "Ep104"}, {"production_date_sast": "2026-09-30"}, {"slides": []}])
def test_compiler_revalidates(monkeypatch, change):
    r = ready(monkeypatch)
    r.manifest.update(change)
    with pytest.raises(ValueError):
        phase_c.compile_slide(r)


def test_no_invented_chain_labels(monkeypatch):
    r = ready(monkeypatch)
    r.manifest["slides"][11]["essential_labels"] = ["Only one explicit label"]
    with pytest.raises(ValueError, match="FIVE_EXPLICIT_LABELS"):
        phase_c.compile_slide(r)


def test_fixed_workflow_is_local_single_image(tmp_path):
    adapter, _ = worker(tmp_path, "comfyui")
    graph = local_workflow(phase_c.generation_job(adapter, "fixture", seed=33))
    assert graph["4"]["inputs"]["batch_size"] == 1
    assert graph["5"]["inputs"]["seed"] == 33
    assert {n["class_type"] for n in graph.values()} == {"CheckpointLoaderSimple", "CLIPTextEncode", "EmptyLatentImage", "KSampler", "VAEDecode", "SaveImage"}


def test_partner_node_rejected(tmp_path):
    adapter, wire = worker(tmp_path, "comfyui")
    wire.nodes["KSampler"]["python_module"] = "paid_partner"
    assert not adapter.available()


@pytest.mark.parametrize("cost", ["PAID", "UNKNOWN"])
def test_phase_c_router_rejects_nonzero_cost_before_dispatch(tmp_path, monkeypatch, cost):
    from src.providers.contracts import MonetaryCost
    from src.providers.model_registry import ModelRegistry
    from src.providers.router import GenerationRouter, NoFreeGenerationProviderAvailable
    adapter, wire = worker(tmp_path, "comfyui")
    caps = adapter.capabilities()
    monkeypatch.setattr(adapter, "capabilities", lambda: replace(caps, monetary_cost=MonetaryCost(cost)))
    router = GenerationRouter((adapter,), models=ModelRegistry((adapter.profile.model,)))
    with pytest.raises(NoFreeGenerationProviderAvailable):
        router.submit(phase_c.generation_job(adapter, "fixture"))
    assert not any(path == "/prompt" for _, path, _ in wire.calls)


def test_unknown_vram_rejected_at_adapter_boundary(tmp_path):
    adapter, _ = worker(tmp_path, "wangp")
    adapter._resource_reader = lambda: ResourceState()
    with pytest.raises(UnsupportedJob):
        adapter.submit(phase_c.generation_job(adapter, "fixture"))


def test_wangp_default_dimension_gate(tmp_path):
    adapter, _ = worker(tmp_path, "wangp")
    adapter.profile = replace(adapter.profile, width=128, height=128)
    assert not adapter.available()


@pytest.mark.parametrize("kind", ["empty", "uniform", "wrong_size", "corrupt"])
def test_technical_artifact_qa(tmp_path, kind):
    artifact = tmp_path / "bad.png"
    if kind in ("empty", "corrupt"):
        artifact.write_bytes(b"" if kind == "empty" else b"corrupt PNG")
    else:
        Image.new("RGB", (32, 32) if kind == "wrong_size" else (64, 64), "black").save(artifact)
    with pytest.raises((ValueError, OSError)):
        inspect_png(artifact, 64, 64)


def test_attempt_budget_and_technical_retry(tmp_path):
    ledger = phase_c.AttemptLedger(tmp_path / "ledger.json")
    index, attempt = ledger.reserve("wangp")
    assert attempt == 1
    with pytest.raises(ValueError):
        ledger.reserve("wangp", "lost response; job may still run")
    ledger.finish(index, "technical_failure")
    with pytest.raises(ValueError):
        ledger.reserve("wangp")
    assert ledger.reserve("wangp", "terminal worker failure diagnosed")[1] == 2
    index, _ = ledger.reserve("comfyui")
    ledger.finish(index, "technical_failure")
    ledger.reserve("comfyui", "corrupt completed output diagnosed")
    with pytest.raises(ValueError, match="CEILING"):
        ledger.reserve("comfyui", "extra forbidden attempt")
    assert len(ledger.read()) == 4


def test_dry_run_never_submits(tmp_path, monkeypatch):
    adapter, wire = worker(tmp_path, "comfyui")
    monkeypatch.setattr(phase_c, "OUTPUT", tmp_path / "output")
    report = phase_c.benchmark(ready(monkeypatch), [adapter], {"suitable_gpu_verified": True})
    assert report["state"] == "DRY_RUN_READY" and report["generation_attempts_total"] == 0
    assert not any(path == "/prompt" for _, path, _ in wire.calls)


def test_execute_blocked_before_dispatch(tmp_path, monkeypatch):
    adapter, wire = worker(tmp_path, "comfyui")
    monkeypatch.setattr(phase_c, "OUTPUT", tmp_path / "output")
    report = phase_c.benchmark(ready(monkeypatch), [adapter], {"suitable_gpu_verified": False}, execute=True)
    assert report["state"] == "BLOCKED" and report["results"] == [] and report["generation_attempts_total"] == 0
    assert not any(path == "/prompt" for _, path, _ in wire.calls)


def test_asset_escape_rejected(tmp_path):
    adapter, wire = worker(tmp_path, "comfyui")
    job_id = adapter.submit(phase_c.generation_job(adapter, "fixture"))
    wire.snapshot = {"id": job_id, "status": "completed", "execution_status": {"status_str": "success", "completed": True},
                     "outputs": {"7": {"images": [{"filename": "../unsafe.png", "type": "output"}]}}}
    with pytest.raises(MalformedResponse):
        adapter.result(job_id)


def test_wangp_artifact_escape_rejected(tmp_path):
    adapter, wire = worker(tmp_path, "wangp")
    identifier = adapter.submit(phase_c.generation_job(adapter, "fixture"))
    wire.snapshot = w_snapshot(True, True)
    wire.snapshot["result"]["generated_files"] = [str(tmp_path.parent / "outside.png")]
    with pytest.raises(MalformedResponse):
        adapter.result(identifier)


def test_offline_execution_records_actual_fixture_job_and_composition_failure(tmp_path, monkeypatch):
    adapter, wire = worker(tmp_path, "comfyui")
    monkeypatch.setattr(phase_c, "OUTPUT", tmp_path / "output")
    phase_c.OUTPUT.mkdir()
    wire.snapshot = {"id": "00000000-0000-4000-8000-000000000012", "status": "completed", "execution_status": {"status_str": "success", "completed": True},
                     "outputs": {"7": {"images": [{"filename": "fixture.png", "subfolder": "", "type": "output"}]}}}
    monkeypatch.setattr(phase_c, "compose", lambda *args: (_ for _ in ()).throw(ValueError("copy does not fit")))
    render, prompt = phase_c.compile_slide(ready(monkeypatch))
    ledger = phase_c.AttemptLedger(phase_c.OUTPUT / "ledger.json")
    record = phase_c.execute_candidate(adapter, render, prompt, ledger)
    assert record["worker_job_id"] == "00000000-0000-4000-8000-000000000012"
    assert record["lifecycle"][-1]["state"] == "SUCCEEDED"
    assert record["composition_blocker"] == "ValueError"
    assert ledger.read()[0]["outcome"] == "success"
    with pytest.raises(ValueError):
        ledger.reserve("comfyui", "a nicer-looking variation is forbidden")


def test_compositor_uses_asset_hook_and_cleans_staging(tmp_path, monkeypatch):
    from src import render_thabo_layout_family
    spec, _ = phase_c.compile_slide(ready(monkeypatch))
    artifact = tmp_path / "art.png"
    png(artifact)
    captured = {}
    def render(source, destination):
        data = json.loads(source.read_text(encoding="utf-8"))
        captured.update(data)
        assert (phase_c.ROOT / data["context_art"]["path"]).is_file()
        image = Image.new("RGB", (1080, 1080), "white")
        image.putpixel((0, 0), (0, 0, 0))
        image.save(destination)
    monkeypatch.setattr(render_thabo_layout_family, "render", render)
    phase_c.compose(spec, artifact, tmp_path / "composite.png")
    assert captured["context_art"]["source"] == "asset"
    assert captured["headline"] == spec["headline"]
    assert not (phase_c.ROOT / captured["context_art"]["path"]).exists()


def test_existing_renderer_asset_path_preserves_portrait_footer_counter(tmp_path):
    from PIL import ImageChops
    from src.render_thabo_layout_family import render
    # Short engineering copy tests the handoff; live editorial copy fit remains unproven.
    spec = {"slide_number": 12, "total_slides": 20, "speaker": "thabo_mokoena", "layout_family": "material_chain",
            "content_type": "material_handoff", "headline": "MATERIAL SYSTEMS", "deck": "A fixture for asset integration.",
            "quote": "Material work matters.", "facts": ["Power", "Cooling", "Workers"], "takeaway": "Infrastructure needs work.",
            "chain": [{"label": label, "note": ""} for label in ("Power", "Cooling", "Racks", "Workers", "Grid")]}
    source = tmp_path / "baseline.json"
    source.write_text(json.dumps(spec), encoding="utf-8")
    baseline = tmp_path / "baseline.png"
    render(source, baseline)
    artifact = tmp_path / "fixture-art.png"
    image = Image.new("RGB", (64, 64), "black")
    image.putpixel((0, 0), (255, 255, 255))
    image.save(artifact)
    composite = tmp_path / "composite.png"
    phase_c.compose(spec, artifact, composite)
    with Image.open(baseline) as before, Image.open(composite) as after:
        assert after.size == (1080, 1080)
        assert ImageChops.difference(before, after).getbbox() is not None
        for region in ((675, 126, 940, 418), (0, 894, 1080, 1080), (0, 0, 1080, 76)):
            assert ImageChops.difference(before.crop(region), after.crop(region)).getbbox() is None
