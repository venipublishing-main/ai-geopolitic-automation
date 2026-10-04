"""Offline D.1 architecture tests, no real generation or semantic QA claim."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import date
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import urllib.request

from PIL import Image, ImageDraw
import pytest

from src import premium_scene_compiler as compiler
from src import premium_compositor, editorial_fusion
from src.episode_manifest_v2 import load_canonical_characters
from src.premium_hero_qa import inspect_hero
from src.premium_slide_renderer import render_preview
from src.scene_contract import SceneContract, Zone

BASE = Path(__file__).parent / "fixtures/premium_scenes"
CASES = json.loads((BASE / "single_cases.json").read_text(encoding="utf-8"))
CHARACTERS = load_canonical_characters()


@pytest.fixture(autouse=True)
def prohibit_execution(monkeypatch):
    """Patch constructors themselves, not just transports or submit methods."""
    from src.providers import contracts, router
    from src.providers.cloud import ai_horde, cloudflare_workers_ai
    from src.providers.local import wangp, comfyui

    def forbidden(*args, **kwargs):
        pytest.fail("D.1 attempted a provider/job, network, subprocess or legacy render")

    for cls in (contracts.GenerationJob, router.GenerationRouter, ai_horde.AIHordeProvider,
                cloudflare_workers_ai.CloudflareWorkersAIProvider, wangp.WanGPProvider, comfyui.ComfyUIProvider):
        monkeypatch.setattr(cls, "__init__", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    from src import render_identity_slide as renderer
    from src import render_kai_layout_family as kai_layouts
    monkeypatch.setattr(renderer, "render", forbidden)
    monkeypatch.setattr(kai_layouts, "render", forbidden)
    monkeypatch.setattr(premium_compositor, "compose_premium", forbidden)
    monkeypatch.setattr(editorial_fusion, "compose_fusion", forbidden)


@pytest.fixture
def manifest():
    return json.loads((BASE / "ep104_manifest.json").read_text(encoding="utf-8"))


def case_manifest(manifest, case):
    result = deepcopy(manifest)
    slide = deepcopy(result["slides"][case["source_slide"]-1])
    slide.update(slide_number=1, panelists=[case["panelist"]], accent_colours={case["panelist"]: CHARACTERS[case["panelist"]]["accent"]},
                 preferred_visual_reasoning_family=case["family"])
    result["slides"][0] = slide
    return result


@pytest.fixture
def raster(tmp_path):
    path = tmp_path / "synthetic.png"
    image = Image.new("RGB", (512, 512), (245, 241, 231))
    draw = ImageDraw.Draw(image)
    # Clearly synthetic nonuniform scene; no claim of object/zone compliance.
    draw.rectangle((100, 100, 400, 380), fill=(90, 100, 110))
    draw.ellipse((200, 180, 350, 330), fill=(200, 190, 170))
    image.save(path)
    return path


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["panelist"])
def test_six_grammars_exact_copy_and_repeatability(manifest, case):
    manifest = case_manifest(manifest, case)
    contract = compiler.compile_scene(manifest, 1)
    assert contract == compiler.compile_scene(deepcopy(manifest), 1)
    assert contract == SceneContract.from_dict(json.loads(json.dumps(contract.to_dict())))
    assert contract.slide == manifest["slides"][0]
    assert contract.headline.text == contract.slide["headline"]
    assert contract.subheadline.text == contract.slide["subheadline"]
    assert contract.phrase.text == contract.slide["main_visual_phrase"]
    assert [t.text for t in contract.takeaways] == [t["idea"] for t in contract.slide["takeaway_ideas"]]
    assert [o.label for o in contract.semantic_objects] == contract.slide["essential_labels"]
    assert contract.panelist_grammar == compiler.GRAMMARS[case["panelist"]][0]
    assert contract.portrait.path == CHARACTERS[case["panelist"]]["portrait"]
    assert contract.portrait.crop == tuple(CHARACTERS[case["panelist"]]["crop_box"])
    assert contract.accent == CHARACTERS[case["panelist"]]["accent"]
    assert .18 <= contract.portrait.scale <= .26
    with pytest.raises(FrozenInstanceError):
        contract.panelist = "other"
    with pytest.raises(FrozenInstanceError):
        contract.semantic_objects[0].label = "other"


def test_diversity_is_geometry_not_only_accent(manifest):
    contracts = [compiler.compile_scene(case_manifest(manifest, c), 1) for c in CASES]
    assert len({c.hero_region for c in contracts}) >= 4
    assert len({c.portrait.side for c in contracts}) == 2
    assert len({c.phrase.treatment for c in contracts}) >= 3
    assert len({c.takeaway_arrangement for c in contracts}) == 3
    assert len({c.micro_detail for c in contracts}) == 6
    assert len({tuple(o.zone for o in c.semantic_objects) for c in contracts}) >= 4


@pytest.mark.parametrize("panelist,families", [
    ("kai_patel", ("physical dependency stack", "monitoring feedback loop")),
    ("diane_sterling", ("cost allocation flow", "investment opportunity comparison")),
])
def test_same_panelist_different_argument_geometry(manifest, panelist, families):
    plans = []
    for family in families:
        plans.append(compiler.compile_scene(case_manifest(manifest,
            {"panelist": panelist, "source_slide": 12, "family": family}), 1))
    a, b = plans
    assert a.panelist_grammar == b.panelist_grammar
    assert a.portrait.side != b.portrait.side
    assert a.hero_region != b.hero_region
    assert a.route_grammar != b.route_grammar
    assert a.takeaway_arrangement != b.takeaway_arrangement


@pytest.mark.parametrize("mutation,code", [
    (lambda m: m["slides"][0].update(preferred_visual_reasoning_family="unreviewed metaphor + special effect"), "UNSUPPORTED_REASONING_FAMILY"),
    (lambda m: m["slides"][0].update(essential_labels=[str(n) for n in range(9)]), "LABEL_CAPACITY_EXCEEDED"),
    (lambda m: m["slides"][0].update(essential_labels=["DUPLICATE"]*2), "LABEL_CAPACITY_EXCEEDED"),
    (lambda m: m["slides"][0].update(headline="W"*800), "COPY_OVERFLOW"),
    (lambda m: m["slides"][0].update(essential_labels=["W"*200]), "LABEL_OVERFLOW"),
    (lambda m: m["slides"][0].update(main_visual_phrase="word "*200), "COPY_OVERFLOW"),
    (lambda m: m["slides"][0]["takeaway_ideas"][0].update(idea="word "*200), "COPY_OVERFLOW"),
    (lambda m: m["slides"][0].update(portrait_scale_intention="giant portrait"), "PORTRAIT_SCALE_UNSUPPORTED"),
    (lambda m: m["slides"][0].update(portrait_scale_intention="90%"), "PORTRAIT_SCALE_UNSUPPORTED"),
    (lambda m: m["slides"][0].update(hero_visual="Render the headline into the illustration"), "ART_REQUIREMENT_NOT_REPRESENTABLE"),
    (lambda m: m["slides"][0].update(panelists=["unknown"]), "MANIFEST_INVALID"),
    (lambda m: m["slides"][0].update(accent_colours={"nora": "#000000"}), "MANIFEST_INVALID"),
    (lambda m: m["slides"][0].update(takeaway_ideas=[]), "MANIFEST_INVALID"),
    (lambda m: m["slides"].pop(), "MANIFEST_INVALID"),
])
def test_fail_closed_mutations(manifest, mutation, code):
    mutation(manifest)
    with pytest.raises(ValueError, match=code):
        compiler.compile_scene(manifest, 1)
    report = compiler.compile_episode(manifest)
    assert report["expected_generation_count"] == 0
    assert report["blockers"] or report["slides"][0]["blockers"]


@pytest.mark.parametrize("field,value", [("crop_box", [-1, 0, 1, 1]), ("crop_box", [0, 0, 99999, 99999]),
    ("portrait", "../outside.png"), ("portrait", "assets/characters/missing.png")])
def test_invalid_canonical_config_blocked(manifest, field, value):
    characters = deepcopy(CHARACTERS)
    characters["nora"][field] = value
    with pytest.raises(compiler.SceneCompileError, match="PORTRAIT_CONFIGURATION_INVALID"):
        compiler.compile_scene(manifest, 1, characters=characters)


@pytest.mark.parametrize("coords", [(-.1, 0, 1, 1), (0, 0, 0, 1), (0, 0, float("nan"), 1), (0, 0, 1, 2)])
def test_invalid_normalised_zones(coords):
    with pytest.raises(ValueError, match="INVALID_NORMALISED_ZONE"):
        Zone(*coords)


def test_ep104_all_slides_zero_calls_and_structured_dual_blockers(manifest):
    report = compiler.compile_episode(manifest)
    compiled = [s["slide_number"] for s in report["slides"] if not s["blockers"]]
    assert compiled == [1, 2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 16, 20]
    blocked = [s for s in report["slides"] if s["blockers"]]
    assert [s["slide_number"] for s in blocked] == [4, 7, 10, 13, 17, 18, 19]
    assert all(s["blockers"][0]["code"] == "DUAL_PANELIST_NOT_SUPPORTED_D1" for s in blocked)
    assert report["provider_submissions"] == report["expected_generation_count"] == 0
    assert report["production_publication"] == "BLOCKED"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["panelist"])
def test_prompt_and_render_share_zones_and_exact_copy(manifest, case, raster):
    manifest = case_manifest(manifest, case)
    contract = compiler.compile_scene(manifest, 1)
    prompt = compiler.compile_prompt(contract)
    assert "No text, letters" in prompt and "canonical portrait" in prompt
    for obj in contract.semantic_objects:
        assert obj.label in prompt
        assert obj.leader[-1] == obj.zone.centre
        assert obj.annotation_side in {"left", "right"}
        assert .0 < obj.importance <= 1
    qa = inspect_hero(contract, raster, prompt, source_kind="synthetic_fixture")
    assert qa.mechanical_passed and qa.content_guard == "NOT_INSPECTED_NO_DETECTOR"
    image, report = render_preview(contract, manifest, raster, qa)
    assert image.size == (1080, 1080)
    assert report["production_publication"] == "BLOCKED_D1"
    assert report["hero_qa"]["human_visual_qa"] == "REQUIRED_NOT_PERFORMED"
    assert report["hero_qa"]["semantic_placement"] == "PLANNED_NOT_VERIFIED"
    assert [r["label"] for r in report["annotations"]] == contract.slide["essential_labels"]
    assert not any(r["object_placement_verified"] for r in report["annotations"])
    # Repeatability includes raster output and local print texture.
    again, _ = render_preview(contract, manifest, raster, qa)
    assert image.tobytes() == again.tobytes()


def test_renderer_rejects_tampered_contract_or_stale_qa(manifest, raster):
    contract = compiler.compile_scene(manifest, 1)
    qa = inspect_hero(contract, raster, compiler.compile_prompt(contract), source_kind="synthetic_fixture")
    with pytest.raises(ValueError, match="CONTRACT_AUTHORITY_MISMATCH"):
        render_preview(replace(contract, accent="#000000"), manifest, raster, qa)
    with pytest.raises(ValueError, match="HERO_QA_REQUIRED_OR_STALE"):
        render_preview(contract, manifest, raster, replace(qa, contract_sha256="invalid"))
    with pytest.raises(ValueError, match="HERO_QA_REQUIRED_OR_STALE"):
        render_preview(contract, manifest, raster, replace(qa, human_visual_qa="PASSED"))
    Image.new("RGB", (512, 512), "white").save(raster)
    with pytest.raises(ValueError, match="HERO_QA_REQUIRED_OR_STALE"):
        render_preview(contract, manifest, raster, qa)


@pytest.mark.parametrize("case", ["uniform", "invalid", "small", "wrong_prompt", "source"])
def test_mechanical_qa_failure(manifest, raster, case):
    contract = compiler.compile_scene(manifest, 1)
    prompt = compiler.compile_prompt(contract)
    source = "synthetic_fixture"
    if case == "uniform":
        Image.new("RGB", (512, 512), "white").save(raster)
    if case == "invalid":
        raster.write_text("not a raster")
    if case == "small":
        Image.new("RGB", (64, 64)).save(raster)
    if case == "wrong_prompt":
        prompt += " changed"
    if case == "source":
        source = "new_generation"
    qa = inspect_hero(contract, raster, prompt, source_kind=source)
    assert not qa.mechanical_passed and qa.blockers


def test_existing_content_evidence_bound_and_no_semantic_claim(manifest, raster):
    contract = compiler.compile_scene(manifest, 1)
    prompt = compiler.compile_prompt(contract)
    evidence = dict(artifact_sha256=hashlib.sha256(raster.read_bytes()).hexdigest(), performed=True,
        approved_for_composition=True, text_or_pseudotext_detected=False, watermark_or_signature_detected=False,
        logo_detected=False, panelist_identity_detected=False, literal_fluffy_cloud_or_icon_detected=False,
        neon_cyberpunk_detected=False, poster_or_contact_sheet_detected=False)
    qa = inspect_hero(contract, raster, prompt, source_kind="existing_accepted_asset", content_evidence=evidence)
    assert qa.mechanical_passed and qa.semantic_placement == "PLANNED_NOT_VERIFIED"
    evidence["text_or_pseudotext_detected"] = True
    assert "CONTENT_GUARD_REJECTED" in inspect_hero(contract, raster, prompt, source_kind="existing_accepted_asset", content_evidence=evidence).blockers
    evidence["artifact_sha256"] = "mismatch"
    assert "CONTENT_GUARD_EVIDENCE_INVALID" in inspect_hero(contract, raster, prompt, source_kind="existing_accepted_asset", content_evidence=evidence).blockers


def test_historical_cli_does_not_claim_current_ready(manifest, tmp_path, capsys):
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps(dict(build="READY", state="BUILD_READY", blockers=[],
        production_date_sast=manifest["production_date_sast"], manifest=manifest)), encoding="utf-8")
    assert compiler.main(["--accepted-snapshot", str(snapshot), "--dry-run"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["input_mode"] == "ACCEPTED_SNAPSHOT_HISTORICAL_REPLAY"
    assert result["current_build_readiness"] == "NOT_ASSERTED"
    assert result["expected_generation_count"] == 0
    assert len(result["slides"]) == 20


def test_live_cli_retains_stale_date_gate(monkeypatch, capsys):
    from src import daily_readiness
    monkeypatch.setattr(daily_readiness, "current_production_date", lambda: date(2026, 10, 4))
    base = Path(__file__).parent / "fixtures/daily_readiness"
    assert compiler.main(["--source", "local", "--rnd-file", str(base/"daily_rnd.txt"),
        "--slide-design-file", str(base/"slide_design_valid.txt"), "--dry-run"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["state"] == "BUILD_BLOCKED" and result["slides"] == []
    assert result["expected_generation_count"] == 0


def test_cli_requires_dry_run_and_no_execute_or_date_option():
    for flags in (["--source", "drive"], ["--source", "drive", "--dry-run", "--execute"],
                  ["--source", "drive", "--dry-run", "--date", "2026-10-03"]):
        with pytest.raises(SystemExit) as error:
            compiler.main(flags)
        assert error.value.code == 2


def test_all_ep104_copy_bounds_and_portrait_protection(manifest):
    from src.premium_typography import typeface
    draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    for slide in manifest["slides"]:
        if len(slide["panelists"]) != 1:
            continue
        contract = compiler.compile_scene(manifest, slide["slide_number"])
        plans = [(p, (0, 0, 1080, 1080)) for p in
                 (contract.headline, contract.subheadline, contract.phrase, *contract.takeaways, *contract.furniture)]
        plans += [(o.annotation, contract.hero_region.pixels()) for o in contract.semantic_objects]
        boxes = []
        for plan, parent in plans:
            box = plan.zone.pixels(parent)
            face = typeface(plan.font_kind, plan.font_size)
            for i, line in enumerate(plan.lines):
                b = draw.textbbox((0, 0), line, font=face)
                assert b[2]-b[0] + 12 <= box[2]-box[0]
                assert i*plan.line_step + b[3]-b[1] + 8 <= box[3]-box[1]
            assert 36 <= box[0] < box[2] <= 1044
            assert 36 <= box[1] < box[3] <= 1079
            boxes.append(box)
        face_box = contract.portrait.protected_face.pixels()
        assert not any(premium_compositor._intersects(face_box, box) for box in boxes)
        for i, box in enumerate(boxes):
            assert not any(premium_compositor._intersects(box, b) for b in boxes[i+1:])
        # Contain transform is square within one rounding pixel, no art crop.
        art_box = contract.art_region.pixels(contract.hero_region.pixels())
        assert abs((art_box[2]-art_box[0]) - (art_box[3]-art_box[1])) <= 1
        object_boxes = [o.zone.pixels((0, 0, 10000, 10000)) for o in contract.semantic_objects]
        for i, box in enumerate(object_boxes):
            assert not any(premium_compositor._intersects(box, b) for b in object_boxes[i+1:])


@pytest.mark.parametrize("change", ["blocked", "metadata", "malformed", "source_date", "null_manifest", "nonobject"])
def test_snapshot_cannot_claim_invalid_acceptance(manifest, tmp_path, capsys, change):
    snapshot = dict(build="READY", state="BUILD_READY", blockers=[],
        production_date_sast=manifest["production_date_sast"], manifest=manifest)
    if change == "blocked":
        snapshot["blockers"] = [{"code": "FAILED"}]
    if change == "metadata":
        snapshot["production_date_sast"] = "2026-10-04"
    if change == "source_date":
        snapshot["manifest"]["source_rnd_date_sast"] = "2026-10-01"
    if change == "malformed":
        snapshot["manifest"]["slides"] = []
    if change == "null_manifest":
        snapshot["manifest"] = None
    if change == "nonobject":
        snapshot = []
    path = tmp_path/"snapshot.json"
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    assert compiler.main(["--accepted-snapshot", str(path), "--dry-run"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["slides"] == [] and result["blockers"]
