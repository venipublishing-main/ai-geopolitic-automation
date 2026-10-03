"""Local raster/geometry regressions, not beauty or provider-inference tests."""
from dataclasses import asdict, replace
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from PIL import Image, ImageChops
import pytest

from src import premium_compositor as premium
from src.daily_readiness import DailyBuildReadinessResult
from test_phase_c_kai_bridge import kai_ready

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def local_proof(kai_ready, monkeypatch, tmp_path):
    monkeypatch.setattr(premium, "ROOT", tmp_path)
    monkeypatch.setattr(premium, "current_production_date", lambda: date(2026, 10, 3))
    monkeypatch.setattr("urllib.request.OpenerDirector.open", lambda *a, **k: pytest.fail("No network in local composition"))
    # Synthetic gradient and acceptance record confined to tests. The production
    # digest remains pinned to the already accepted Albedo asset, not this fixture.
    source = tmp_path / "output/phase-c1/context-art.png"
    source.parent.mkdir(parents=True)
    gradient = Image.linear_gradient("L").rotate(90).resize((1024, 1024))
    gradient.convert("RGB").save(source)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setattr(premium, "ACCEPTED_SHA256", digest)
    metadata = source.parent / "generation-metadata.json"
    metadata.write_text(json.dumps({
        "state": "SUCCEEDED", "episode_id": "Ep104", "slide_number": 5,
        "model_profile": {"model_id": "AlbedoBase XL 3.1"},
        "agent_visual_screen": {"performed": True, "approved_for_composition": True, "artifact_sha256": digest},
        "licence_audit": {"creator": "albedobond", "attribution_text": "TEST ONLY recorded credit",
            "publication_attribution_required": True, "permission_source": "https://example.test/evidence",
            "use": {"context": "INTERNAL_BENCHMARK"}},
        "publication_handoff": {"state": "BLOCKED", "publication_attribution_required": True,
            "creator": "albedobond", "required_attribution_text": "TEST ONLY recorded credit",
            "source": "https://example.test/evidence"}
    }), encoding="utf-8")
    portrait = tmp_path / "assets/characters/kai_patel.png"
    portrait.parent.mkdir(parents=True)
    shutil.copyfile(REPO / "assets/characters/kai_patel.png", portrait)
    destination = tmp_path / premium.PACKAGE / "premium/slide05-premium.png"
    return kai_ready, source, metadata, destination


def compose(local_proof):
    return premium.compose_premium(*local_proof)


def test_exact_manifest_mapping(local_proof):
    readiness, _, _, _ = local_proof
    spec = asdict(premium.compile_slide(readiness))
    slide = readiness.manifest["slides"][4]
    for field in ("headline", "subheadline", "main_visual_phrase", "core_argument"):
        assert spec[field] == slide[field]
    assert spec["essential_labels"] == tuple(slide["essential_labels"])
    assert spec["takeaway_ideas"] == tuple(row["idea"] for row in slide["takeaway_ideas"])
    assert spec["panelist"] == "kai_patel" and spec["accent"] == "#6540A4"
    assert spec["portrait"] == "assets/characters/kai_patel.png"
    assert spec["episode_id"] == "Ep104" and spec["production_date_sast"] == "2026-10-03"


def test_primary_hero_and_premium_geometry(local_proof):
    report = compose(local_proof)
    geometry = report["geometry"]
    assert geometry["hero_area"] > 2 * geometry["old_plate_area"]
    assert geometry["portrait_area"] > 1.4 * geometry["old_portrait_area"]
    assert 0.55 <= geometry["hero_visual_field_fraction"] <= 0.65
    assert geometry["hero_centre_alpha"] == 255
    assert geometry["hero"] != [470, 545, 940, 875]
    assert geometry["headline"][1] < 150 and geometry["headline"][3] <= 310
    assert geometry["main_phrase"][0] < 100 and geometry["main_phrase"][2] - geometry["main_phrase"][0] >= 400
    columns = geometry["takeaway_columns"]
    assert len(columns) == 3 and all(box[1] >= 910 for box in columns)
    assert columns[0][2] < columns[1][0] < columns[1][2] < columns[2][0]
    assert not geometry["opaque_generic_diagram"]
    # Pixel evidence that scene detail survives, instead of an opaque generic mesh.
    with Image.open(report["output"]) as output:
        hero_pixels = list(output.crop((500, 570, 850, 670)).getdata())
        assert sum(p[0] < 150 for p in hero_pixels) / len(hero_pixels) > 0.2


def test_exact_type_labels_counter_footer_and_collision_bounds(local_proof):
    report = compose(local_proof)
    rows = report["geometry"]["protected_text"]
    text = {r["name"]: r["text"] for r in rows}
    source = local_proof[0].manifest["slides"][4]
    assert text["headline_black"] + " " + text["headline_accent"] == source["headline"]
    assert text["subheadline"] == source["subheadline"]
    assert text["phrase_first"] + " " + text["phrase_second"] == source["main_visual_phrase"]
    assert text["footer"] == premium.MOTTO and text["counter"] == "05/20"
    assert text["date"] == "SATURDAY, 3 OCTOBER 2026"
    assert [text[f"label_{i}"] for i in range(6)] == list(premium.LABELS)
    assert [text[f"takeaway_idea_{i}"] for i in range(1, 4)] == [r["idea"] for r in source["takeaway_ideas"]]
    assert [text[f"takeaway_number_{i}"] for i in range(1, 4)] == ["01", "02", "03"]
    assert len(report["geometry"]["callout_anchors"]) == 6
    for i, row in enumerate(rows):
        assert 36 <= row["bounds"][0] < row["bounds"][2] <= 1044
        assert 36 <= row["bounds"][1] < row["bounds"][3] <= 1050
        assert not any(premium._intersects(row["bounds"], other["bounds"]) for other in rows[i + 1:])


def test_canonical_identity_source_accent_and_valid_png(local_proof):
    report = compose(local_proof)
    assert report["canonical_portrait"].endswith("assets/characters/kai_patel.png") or report["canonical_portrait"].endswith("assets\\characters\\kai_patel.png")
    assert report["portrait_sha256"] == hashlib.sha256((REPO / "assets/characters/kai_patel.png").read_bytes()).hexdigest()
    with Image.open(report["output"]) as image:
        image.verify()
    with Image.open(report["output"]) as image:
        assert image.size == (1080, 1080) and image.format == "PNG"
        assert image.getpixel((24, 24)) == (101, 64, 164)
        assert image.getpixel((45, 751)) == (101, 64, 164)


def test_zero_generation_zero_network_and_no_legacy_paths(local_proof, monkeypatch):
    from src.providers.contracts import GenerationJob
    from src.providers.router import GenerationRouter
    from src.providers.cloud.ai_horde import AIHordeProvider
    from src.providers.cloud.cloudflare_workers_ai import CloudflareWorkersAIProvider
    from src.providers.local.wangp import WanGPProvider
    from src.providers.local.comfyui import ComfyUIProvider
    from src import contextual_illustrations, render_kai_layout_family, render_identity_slide
    def forbidden(*a, **kw):
        pytest.fail("Premium composition must not enter generation or legacy paths")
    for cls in (GenerationJob, GenerationRouter, AIHordeProvider, CloudflareWorkersAIProvider, WanGPProvider, ComfyUIProvider):
        monkeypatch.setattr(cls, "__init__", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(render_kai_layout_family, "render", forbidden)
    monkeypatch.setattr(render_kai_layout_family, "render_network_mesh", forbidden)
    monkeypatch.setattr(render_identity_slide, "render_kai", forbidden)
    monkeypatch.setattr(contextual_illustrations, "_asset_plate", forbidden)
    monkeypatch.setattr(contextual_illustrations, "apply_context_art", forbidden)
    report = compose(local_proof)
    assert report["provider_calls"] == report["new_generation_count"] == 0
    assert report["runtime_reference_dependency"] is False


def test_hero_opaque_tonal_detail_and_portrait_aspect_preserved(local_proof):
    _, source, _, _ = local_proof
    hero, mask = premium.prepare_hero_art(source, (658, 530))
    assert hero.size == mask.size == (658, 530)
    assert mask.getpixel((329, 265)) == 255 and mask.getpixel((0, 0)) == 0
    assert min(hero.convert("L").getdata()) < 35 and max(hero.convert("L").getdata()) > 235
    assert hero.mode == "RGB"
    # Source pixels are crop/cover transformed once, with no facial geometry warp.
    p = premium.ROOT / "assets/characters/kai_patel.png"
    crop = premium.compile_slide(local_proof[0]).crop_box
    portrait, _ = premium.prepare_portrait(p, crop, (367, 498))
    from PIL import ImageOps
    with Image.open(p) as original:
        used = (crop[0], max(crop[1], round(original.height * .03)), crop[2], crop[3])
        expected = ImageOps.fit(original.convert("RGB").crop(used), (367, 498), Image.Resampling.LANCZOS, centering=(.52, .48))
        assert ImageChops.difference(portrait, expected).getbbox() is None


@pytest.mark.parametrize("change", [{"build": "BLOCKED"}, {"state": "BUILD_BLOCKED"}, {"production_date_sast": "2026-10-02"}])
def test_readiness_fail_closed(local_proof, change):
    with pytest.raises(ValueError, match="LIVE_BUILD_READY_REQUIRED"):
        premium.compile_slide(replace(local_proof[0], **change))


@pytest.mark.parametrize("change", [
    {"panelists": ["nora"]}, {"accent_colours": {"kai_patel": "#ffffff"}},
    {"essential_labels": list(premium.LABELS[:5])}, {"slide_number": 6},
    {"takeaway_ideas": []}, {"pairing_mode": "SUPPORTIVE_CONVERGENT"},
])
def test_manifest_and_one_slide_scope_fail_closed(local_proof, change):
    local_proof[0].manifest["slides"][4].update(change)
    with pytest.raises(ValueError):
        premium.compile_slide(local_proof[0])


def test_missing_or_changed_accepted_art_fails_before_output(local_proof):
    readiness, source, metadata, destination = local_proof
    source.unlink()
    with pytest.raises(ValueError, match="REQUIRED_LOCAL_ASSET_MISSING"):
        compose(local_proof)
    assert not destination.exists()
    Image.new("RGB", (1024, 1024), "red").save(source)
    with pytest.raises(ValueError, match="ACCEPTED_ALBEDO_ART_REQUIRED"):
        compose(local_proof)


@pytest.mark.parametrize("change", [
    {"agent_visual_screen": {"approved_for_composition": False}}, {"state": "FAILED"},
    {"licence_audit": {}}, {"publication_handoff": {"state": "READY"}}, {"agent_visual_screen": None},
    {"publication_handoff": {"state": "BLOCKED", "publication_attribution_required": False}},
])
def test_acceptance_and_attribution_record_required(local_proof, change):
    data = json.loads(local_proof[2].read_text())
    data.update(change)
    local_proof[2].write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        compose(local_proof)
    assert not local_proof[3].exists()


def test_path_escape_for_source_portrait_and_output(local_proof, tmp_path):
    readiness, source, metadata, output = local_proof
    outside = tmp_path / "outside.png"
    shutil.copyfile(source, outside)
    with pytest.raises(ValueError, match="PATH_ESCAPE"):
        premium.compose_premium(readiness, outside, metadata, output)
    with pytest.raises(ValueError, match="PATH_ESCAPE"):
        premium.compose_premium(readiness, source, metadata, outside)


def test_long_copy_blocks_without_clipping_or_rewriting(local_proof):
    local_proof[0].manifest["slides"][4]["headline"] = "Excessive headline " * 80
    with pytest.raises(ValueError, match="DISPLAY_COPY_TOO_LONG"):
        compose(local_proof)
    assert not local_proof[3].exists()


def test_report_retains_credit_and_human_review_no_runtime_reference(local_proof):
    report = compose(local_proof)
    premium.write_report(report, premium.ROOT / premium.PACKAGE / "report")
    directory = premium.ROOT / premium.PACKAGE / "report"
    saved = json.loads((directory / "composition-report.json").read_text(encoding="utf-8"))
    assert saved["state"] == premium.REVIEW and saved["visual_parity"] == "NOT CLAIMED"
    assert saved["publication_handoff"]["state"] == "BLOCKED"
    assert "TEST ONLY recorded credit" in (directory / "composition-report.md").read_text()
    assert not (premium.ROOT / premium.PACKAGE / "reference").exists()


def test_reference_input_control_and_output_are_ignored():
    files = ["output/phase-c2/Ep104/slide-05/" + p for p in (
        "reference/Slide05of20-reference.png", "input/context-art.png",
        "control/slide05-phase-c1-control.png", "premium/slide05-premium.png")]
    result = subprocess.run(["git", "check-ignore", *files], cwd=REPO, text=True, capture_output=True)
    assert result.returncode == 0 and len(result.stdout.splitlines()) == 4


def test_actual_albedo_trust_anchor_matches_accepted_phase_c1_record():
    assert premium.ACCEPTED_SHA256 == "af911721d389f3b6a658d18e3e0ba30f93c48bb041be51a7060bf69255f2288b"
