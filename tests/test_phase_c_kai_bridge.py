"""Offline, current-copy benchmark compatibility; never dispatch live inference."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

from PIL import Image, ImageChops
import pytest

from src import phase_c, phase_c_cloud, render_kai_layout_family
from src.providers.cloud import common
from src.providers.cloud.cloudflare_workers_ai import CloudflareWorkersAIProvider, CloudflareConfig
from src.contextual_illustrations import validate_context_art_spec
from test_phase_c_cloud import current_ready, horde, Wire, snapshot, REMOTE_ID


@pytest.fixture
def kai_ready(monkeypatch, tmp_path):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    monkeypatch.setattr(phase_c_cloud, "OUTPUT", tmp_path / "output/phase-c1")
    monkeypatch.delenv("AI_GEOPOLITIC_HORDE_API_KEY", raising=False)
    def no_network(*args, **kwargs):
        raise AssertionError("Bridge tests are offline")
    monkeypatch.setattr("urllib.request.OpenerDirector.open", no_network)
    readiness = current_ready(monkeypatch)
    slide = readiness.manifest["slides"][4]
    # Recorded Ep104 copy, not shorter copy that would conceal a layout failure.
    slide.update(panelists=["kai_patel"], accent_colours={"kai_patel": "#6540A4"},
        pairing_mode=None, central_relationship=None, shared_ground=None, why_dual=None, panelist_contributions=None,
        headline="“THE CLOUD” STILL NEEDS MEGAWATTS, PIPES AND LAND",
        subheadline="Remote computation does not make the physical hosting layer disappear.",
        main_visual_phrase="THE CLOUD HAS AN ADDRESS.",
        core_argument="AI services can be remote while hosting constraints remain geographically local.",
        hero_visual="User network flows into a cutaway campus showing fibre, transformers, cooling and water infrastructure.",
        essential_labels=["REMOTE USERS", "FIBRE", "COMPUTE", "COOLING", "POWER", "LAND"],
        takeaway_ideas=[{"idea": idea, "intended_visual_treatment": "paired labels"} for idea in
                       ["remote use, local footprint", "bottlenecks persist", "geography matters"]],
        preferred_visual_reasoning_family="network-to-physical transition",
        anti_cliche_guardrail="no literal fluffy cloud or cyberpunk glow.",
        factual_guardrails=["Cooling and water systems vary; do not imply one fixed footprint."])
    return readiness


def compile_kai(readiness, number=5):
    return phase_c.compile_context_slide(readiness, number, profile=phase_c.KAI_NETWORK_MESH)


def test_exact_mapping_and_live_prompt(kai_ready):
    spec, prompt = compile_kai(kai_ready)
    slide = kai_ready.manifest["slides"][4]
    assert spec == {"speaker": "kai_patel", "slide_number": 5, "total_slides": 20,
        "layout_family": "network_mesh", "headline": slide["headline"], "deck": slide["subheadline"],
        "quote": slide["main_visual_phrase"], "facts": [r["idea"] for r in slide["takeaway_ideas"]],
        "takeaway": slide["core_argument"]}
    assert slide["hero_visual"] in prompt and slide["factual_guardrails"][0] in prompt
    assert phase_c.LOCKED_ART in prompt and "No Kai likeness" in prompt
    assert phase_c_cloud.select_slide(kai_ready, 5) == (5, spec, prompt)


@pytest.mark.parametrize("number", [1, 20, 6])
def test_kai_only_slide05_interior(kai_ready, number):
    with pytest.raises(ValueError, match="KAI_.*REQUIRED"):
        compile_kai(kai_ready, number)


@pytest.mark.parametrize("change", [
    {"panelists": ["nora"]}, {"pairing_mode": "comparison"}, {"central_relationship": "shared system"},
    {"panelists": ["kai_patel", "thabo_mokoena"]},
])
def test_kai_dual_non_kai_and_changed_metadata_fail_closed(kai_ready, change):
    kai_ready.manifest["slides"][4].update(change)
    # Invalid v2 metadata is rejected even before the explicit profile gate.
    with pytest.raises(ValueError):
        compile_kai(kai_ready)


@pytest.mark.parametrize("change", [{"build": "BLOCKED"}, {"state": "BUILD_BLOCKED"},
                                  {"production_date_sast": "2026-10-02"}])
def test_kai_still_requires_live_readiness(kai_ready, change):
    with pytest.raises(ValueError, match="LIVE_BUILD_READY_REQUIRED"):
        compile_kai(replace(kai_ready, **change))


def test_old_thabo_and_unknown_profile(kai_ready):
    render, _ = phase_c.compile_context_slide(kai_ready, 7)
    assert render["speaker"] == "thabo_mokoena" and render["layout_family"] == "material_chain"
    with pytest.raises(ValueError, match="UNSUPPORTED_BENCHMARK_PROFILE"):
        phase_c.compile_context_slide(kai_ready, 5, profile="GENERAL_COMPILER")


def test_asset_hook_path_safe_box_and_number(kai_ready, tmp_path, monkeypatch):
    spec, _ = compile_kai(kai_ready)
    artifact = tmp_path / "art.png"
    Image.new("RGB", (1024, 1024), "black").save(artifact)
    captured = {}
    def render(source, destination):
        data = json.loads(source.read_text(encoding="utf-8"))
        captured.update(data)
        validate_context_art_spec(data["context_art"])
        staged = phase_c.ROOT / data["context_art"]["path"]
        assert staged.resolve().is_relative_to((phase_c.ROOT / "assets/_phase_c_runtime").resolve())
        assert staged.is_file()
        image = Image.new("RGB", (1080, 1080), "white")
        image.putpixel((0, 0), (0, 0, 0))
        image.save(destination)
    monkeypatch.setattr(render_kai_layout_family, "render", render)
    phase_c.compose(spec, artifact, tmp_path / "composite.png")
    assert captured["context_art"]["source"] == "asset"
    assert captured["context_art"]["box"] == [470, 545, 940, 875]
    assert captured["slide_number"] == 5
    assert not (phase_c.ROOT / captured["context_art"]["path"]).exists()


def test_current_copy_fits_real_renderer_and_foreground_is_preserved(kai_ready, tmp_path):
    spec, _ = compile_kai(kai_ready)
    source, baseline, composite = (tmp_path / name for name in ("baseline.json", "baseline.png", "composite.png"))
    source.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    render_kai_layout_family.render(source, baseline)
    artifact = tmp_path / "art.png"
    pixels = Image.new("RGB", (1024, 1024), "black")
    pixels.putpixel((1, 1), (255, 255, 255))
    pixels.save(artifact)
    phase_c.compose(spec, artifact, composite)
    with Image.open(baseline) as before, Image.open(composite) as after:
        assert after.size == (1080, 1080)
        for region in ((96, 145, 431, 505), (485, 108, 940, 530), (96, 555, 425, 870),
                       (0, 890, 1080, 1080), (0, 0, 1080, 76), (650, 675, 730, 725)):
            assert ImageChops.difference(before.crop(region), after.crop(region)).getbbox() is None
        # Ink/accent foreground pixels stay exact, including mesh links and labels;
        # only background paper between deterministic elements may change.
        from src.editorial_primitives import INK, hex_rgb
        for y in range(545, 875):
            for x in range(470, 940):
                if before.getpixel((x, y)) in (INK, hex_rgb("#6540A4")):
                    assert before.getpixel((x, y)) == after.getpixel((x, y))
        assert ImageChops.difference(before, after).getbbox() is not None


def test_kai_dry_run_zero_inference(kai_ready, tmp_path):
    provider, wire = horde(tmp_path)
    cf = CloudflareWorkersAIProvider(CloudflareConfig(), transport=Wire())
    try:
        report = phase_c_cloud.benchmark(kai_ready, (provider, cf),
            priority=(provider.provider_id, cf.provider_id), slide_number=5)
        assert report["state"] == "DRY_RUN_READY" and not report["blockers"]
        assert report["selected_bridge_profile"] == phase_c.KAI_NETWORK_MESH
        assert report["predicted_generation_count"] == 1 and report["generation_attempts_total"] == 0
        assert not any(row[0] == "POST" for row in wire.calls)
    finally:
        cf.close()


def test_no_supported_profile_still_blocks(kai_ready):
    manifest = deepcopy(kai_ready.manifest)
    for slide in manifest["slides"]:
        slide.update(panelists=["nora"], accent_colours={"nora": "#1769AA"}, pairing_mode=None,
                     central_relationship=None, shared_ground=None, why_dual=None, panelist_contributions=None)
    assert not phase_c.validate_manifest_v2(manifest, phase_c.load_canonical_characters())
    with pytest.raises(ValueError, match="SUPPORTED_CURRENT_CONTEXT_ART_SLIDE_MISSING"):
        phase_c_cloud.select_slide(replace(kai_ready, manifest=manifest))


def test_valid_dual_and_valid_non_kai_rejected_by_profile(kai_ready):
    slide = kai_ready.manifest["slides"][4]
    slide.update(panelists=["kai_patel", "thabo_mokoena"],
        accent_colours={"kai_patel": "#6540A4", "thabo_mokoena": "#A73528"},
        pairing_mode="QUALIFIED_TENSION", central_relationship="partially_overlap",
        shared_ground="Hosting needs infrastructure.", why_dual="Two distinct perspectives.",
        panelist_contributions={"kai_patel": "Network layer", "thabo_mokoena": "Physical layer"})
    assert not phase_c.validate_manifest_v2(kai_ready.manifest, phase_c.load_canonical_characters())
    with pytest.raises(ValueError, match="SINGLE_KAI_SLIDE_REQUIRED"):
        compile_kai(kai_ready)
    slide.update(panelists=["nora"], accent_colours={"nora": "#1769AA"}, pairing_mode=None,
                 central_relationship=None, shared_ground=None, why_dual=None, panelist_contributions=None)
    assert not phase_c.validate_manifest_v2(kai_ready.manifest, phase_c.load_canonical_characters())
    with pytest.raises(ValueError, match="SINGLE_KAI_SLIDE_REQUIRED"):
        compile_kai(kai_ready)


def test_deferred_composition_and_sanitized_real_shaped_lifecycle(kai_ready, tmp_path, monkeypatch):
    provider, wire = horde(tmp_path)
    wire.state = snapshot("success")
    wire.generation.update(worker_id="worker-fixture", worker_name="offline-fixture")
    cf = CloudflareWorkersAIProvider(CloudflareConfig(), transport=Wire())
    monkeypatch.setattr(phase_c, "compose", lambda *args: pytest.fail("Must inspect artifact before composing"))
    try:
        report = phase_c_cloud.benchmark(kai_ready, (provider, cf), priority=(provider.provider_id, cf.provider_id),
            slide_number=5, execute=True, defer_composition=True)
        assert report["state"] == "ARTIFACT_REVIEW_REQUIRED" and not report["blockers"]
        result = report["results"][0]
        assert result["worker_job_id"] == REMOTE_ID and "composition_output" not in result
        assert result["provider_lifecycle"]["returned_generations"][0]["seed"] == "104"
        metadata = json.loads((Path(result["artifact_path"]).parent / "generation-metadata.json").read_text())
        assert metadata["provider_lifecycle"]["horde_job_id"] == REMOTE_ID
        assert "img" not in json.dumps(metadata) and "apikey" not in json.dumps(metadata)
        assert sum(row[0] == "POST" for row in wire.calls) == 1
        assert provider.http is wire
        assert phase_c_cloud.benchmark(kai_ready, (provider, cf), priority=(provider.provider_id, cf.provider_id),
            slide_number=5, execute=True)["state"] == "BLOCKED"
        assert sum(row[0] == "POST" for row in wire.calls) == 1
    finally:
        cf.close()
