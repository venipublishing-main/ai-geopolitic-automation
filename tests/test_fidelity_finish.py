"""Accepted-artifact finish tests, without network/inference or beauty scores."""
from dataclasses import asdict
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess

from PIL import Image, ImageChops, ImageDraw
import pytest

from src import fidelity_finish as finish, editorial_fusion as fusion, premium_compositor as control
from test_editorial_fusion import fusion_proof
from test_premium_compositor import local_proof
from test_phase_c_kai_bridge import kai_ready

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def finish_proof(fusion_proof, monkeypatch, tmp_path):
    # Synthetic source/acceptance and digest overrides are confined to fixtures.
    # Actual production pins are asserted separately, never weakened in code.
    monkeypatch.setattr(finish, "ROOT", tmp_path)
    c3 = fusion.compose_fusion(*fusion_proof)
    report_path = tmp_path / fusion.PACKAGE / "report/fusion-report.json"
    fusion.write_report(c3, report_path.parent)
    snapshot = tmp_path / finish.PACKAGE / "input/readiness.json"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text(json.dumps(asdict(fusion_proof[0])), encoding="utf-8")
    raw = json.loads(snapshot.read_text(encoding="utf-8"))
    core = json.loads(report_path.read_text(encoding="utf-8"))
    monkeypatch.setattr(finish, "CONTROL_SHA256", c3["output_sha256"])
    monkeypatch.setattr(finish, "CORE_SHA256", finish.json_digest({k: core[k] for k in finish.CORE_FIELDS}))
    monkeypatch.setattr(finish, "MANIFEST_SHA256", finish.json_digest(raw["manifest"]))
    return (snapshot, fusion_proof[3], report_path, fusion_proof[1], fusion_proof[2],
            tmp_path / finish.PACKAGE / "phase4/slide05-phase4.png")


def compose(proof):
    return finish.finish_proof(*proof)


def test_exact_copy_canonical_source_macro_geometry_and_png(finish_proof):
    report = compose(finish_proof)
    c3 = json.loads(finish_proof[2].read_text(encoding="utf-8"))
    source = json.loads(finish_proof[0].read_text(encoding="utf-8"))["manifest"]["slides"][4]
    assert report["slide"] == c3["slide"]
    assert report["geometry"] == c3["geometry"]
    assert report["typography"] == c3["typography"]
    assert report["source_asset_sha256"] == hashlib.sha256(finish_proof[3].read_bytes()).hexdigest()
    assert report["portrait_sha256"] == hashlib.sha256((REPO / "assets/characters/kai_patel.png").read_bytes()).hexdigest()
    assert report["accent_hex"] == "#6540A4"
    assert (report["slide"]["episode_id"], report["slide"]["slide_number"], report["slide"]["total_slides"]) == ("Ep104", 5, 20)
    text = {r["name"]: r["text"] for r in report["geometry"]["protected_text"]}
    assert text["headline_black"] + " " + text["headline_accent"] == source["headline"]
    assert text["subheadline"] == source["subheadline"]
    assert text["phrase_first"] + " " + text["phrase_second"] == source["main_visual_phrase"]
    assert [text[f"label_{i}"] for i in range(6)] == source["essential_labels"]
    assert [text[f"takeaway_idea_{i}"] for i in range(1, 4)] == [t["idea"] for t in source["takeaway_ideas"]]
    assert text["counter"] == "05/20" and text["footer"] == fusion.MOTTO
    assert report["geometry"]["opaque_label_cards"] == 0
    with Image.open(report["output"]) as image:
        assert image.size == (1080, 1080) and image.format == "PNG"
        image.verify()


def test_face_copy_and_furniture_pixels_identical_no_clipping(finish_proof):
    report = compose(finish_proof)
    with Image.open(finish_proof[1]) as baseline, Image.open(report["output"]) as result:
        diff = ImageChops.difference(baseline, result)
    rows = report["geometry"]["protected_text"]
    for box in [fusion.FACE, (0, 0, 1080, 103), (0, 1004, 1080, 1080)] + [r["bounds"] for r in rows]:
        assert diff.crop(box).getbbox() is None
    for i, row in enumerate(rows):
        x0, y0, x1, y1 = row["bounds"]
        assert 36 <= x0 < x1 <= 1044 and 36 <= y0 < y1 <= 1050
        assert not any(control._intersects(row["bounds"], other["bounds"]) for other in rows[i + 1:])


def test_more_accent_black_dominant_and_all_finish_regions_change(finish_proof):
    report = compose(finish_proof)
    c3, c4 = report["mark_coverage"]["c3"], report["mark_coverage"]["c4"]
    assert c4["accent_pixels"] > c3["accent_pixels"]
    assert c4["neutral_dark_pixels"] > c4["accent_pixels"] * 2
    assert set(report["raster_delta"]) == set(finish.DELTA_REGIONS)
    for delta in report["raster_delta"].values():
        assert delta["changed_pixels_over_6_levels"] > delta["region_pixels"] * .02
    with Image.open(report["output"]) as image:
        assert len(set(image.crop((500, 570, 850, 735)).convert("L").getdata())) > 100


def test_local_detail_nonuniform_negative_space_quiet():
    image = Image.new("RGB", (1080, 1080), (160, 160, 160))
    original = image.copy()
    finish.local_surface_finish(image, Image.new("L", image.size, 255))
    assert image.getpixel((550, 690)) != original.getpixel((550, 690))
    assert image.getpixel((650, 355)) == original.getpixel((650, 355))
    assert len({z["pitch"] for z in finish.ZONES}) > 2
    assert len({z["slope"] for z in finish.ZONES}) > 2
    assert len({z["tint_alpha"] for z in finish.ZONES}) > 2


def test_routes_remain_anchored_and_face_copy_safe(finish_proof):
    report = compose(finish_proof)
    mask = finish.refined_route_mask()
    fusion.validate_route_mask(mask, report["geometry"]["protected_text"])
    assert mask.crop(fusion.FACE).getbbox() is None
    assert report["geometry"]["routes"] == json.loads(finish_proof[2].read_text(encoding="utf-8"))["geometry"]["routes"]
    for route in fusion.ROUTES:
        for end in ("from", "to"):
            x, y = fusion.ANCHORS[route[end]]["point"]
            assert mask.getpixel((x, y)) == 255
    assert finish.ROUTE_STYLE["trunk_width"] > finish.ROUTE_STYLE["branch_width"]
    assert finish.ROUTE_STYLE["terminal_radius"] < 5
    assert finish.ROUTE_STYLE["arrow_length"] < 10


def test_refined_route_collision_fails_before_output(finish_proof, monkeypatch):
    invalid = finish.refined_route_mask()
    ImageDraw.Draw(invalid).line((100, 500, 180, 500), fill=255)
    monkeypatch.setattr(finish, "refined_route_mask", lambda: invalid)
    with pytest.raises(ValueError, match="ROUTE_CROSSES_PROTECTED_REGION"):
        compose(finish_proof)
    assert not finish_proof[-1].exists()


def test_microdetail_is_graphical_and_guarded(finish_proof, monkeypatch):
    def forbidden(*a, **k):
        pytest.fail("C.4 microdetail cannot generate text or invented data")
    monkeypatch.setattr(ImageDraw.ImageDraw, "text", forbidden)
    monkeypatch.setattr(ImageDraw.ImageDraw, "multiline_text", forbidden)
    layer = finish.micro_finish_layer()
    c3 = json.loads(finish_proof[2].read_text(encoding="utf-8"))
    allowed = finish.allowed_finish_mask(c3["geometry"]["protected_text"])
    alpha = ImageChops.multiply(layer.getchannel("A"), allowed)
    assert alpha.crop(fusion.FACE).getbbox() is None
    assert alpha.crop(finish.DELTA_REGIONS["technical_microdetail"]).getbbox() is not None
    for row in c3["geometry"]["protected_text"]:
        assert alpha.crop(row["bounds"]).getbbox() is None


def test_c3_reproducible_finish_deterministic_and_sources_preserved(finish_proof, fusion_proof):
    paths = finish_proof[:-1]
    prior = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    first = compose(finish_proof)
    c3 = fusion.compose_fusion(*fusion_proof)
    assert c3["output_sha256"] == prior[finish_proof[1]]
    second = compose(finish_proof)
    assert second["output_sha256"] == first["output_sha256"]
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in prior.items())


def test_explicit_dated_replay_does_not_bypass_live_gate(finish_proof, fusion_proof, monkeypatch):
    monkeypatch.setattr(control, "current_production_date", lambda: date(2026, 10, 4))
    with pytest.raises(ValueError, match="LIVE_BUILD_READY_REQUIRED"):
        control.compile_slide(fusion_proof[0])
    report = compose(finish_proof)
    assert report["mode"] == "ACCEPTED_EP104_ARTIFACT_REPLAY"
    assert report["live_daily_readiness_claimed"] is False
    assert report["slide"]["production_date_sast"] == "2026-10-03"


def test_no_jobs_providers_network_legacy_or_reference_reads(finish_proof, monkeypatch):
    from src.providers.contracts import GenerationJob
    from src.providers.router import GenerationRouter
    from src.providers.cloud.ai_horde import AIHordeProvider
    from src.providers.cloud.cloudflare_workers_ai import CloudflareWorkersAIProvider
    from src.providers.local.wangp import WanGPProvider
    from src.providers.local.comfyui import ComfyUIProvider
    from src import contextual_illustrations, render_kai_layout_family, render_identity_slide
    def forbidden(*a, **kw):
        pytest.fail("Finish must stay local and preserve C.3 behaviour")
    for cls in (GenerationJob, GenerationRouter, AIHordeProvider, CloudflareWorkersAIProvider, WanGPProvider, ComfyUIProvider):
        monkeypatch.setattr(cls, "__init__", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden)
    monkeypatch.setattr(fusion, "compose_fusion", forbidden)
    monkeypatch.setattr(control, "compose_premium", forbidden)
    monkeypatch.setattr(control, "compile_slide", forbidden)
    monkeypatch.setattr(contextual_illustrations, "_asset_plate", forbidden)
    monkeypatch.setattr(contextual_illustrations, "apply_context_art", forbidden)
    monkeypatch.setattr(render_kai_layout_family, "render_network_mesh", forbidden)
    monkeypatch.setattr(render_identity_slide, "render_kai", forbidden)
    original_open = Image.open
    def no_reference(path, *a, **kw):
        assert "reference" not in str(path)
        return original_open(path, *a, **kw)
    monkeypatch.setattr(Image, "open", no_reference)
    assert not (finish.ROOT / finish.PACKAGE / "reference").exists()
    report = compose(finish_proof)
    assert report["new_generation_count"] == report["provider_calls"] == 0
    assert report["runtime_reference_dependency"] is False


@pytest.mark.parametrize("change", [{"state": "BUILD_BLOCKED"}, {"build": "BLOCKED"}, {"blockers": ["problem"]},
                                    {"production_date_sast": "2026-10-04"}])
def test_snapshot_fail_closed(finish_proof, change):
    path = finish_proof[0]
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw.update(change)
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        compose(finish_proof)
    assert not finish_proof[-1].exists()


@pytest.mark.parametrize("field", ["headline", "accent_colours", "takeaway_ideas", "panelists", "slide_number"])
def test_changed_or_malformed_manifest_cannot_replay(finish_proof, field):
    raw = json.loads(finish_proof[0].read_text(encoding="utf-8"))
    raw["manifest"]["slides"][4][field] = None
    finish_proof[0].write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="VALIDATED_MANIFEST_REQUIRED"):
        compose(finish_proof)


def test_valid_but_changed_other_slide_is_not_same_manifest(finish_proof):
    raw = json.loads(finish_proof[0].read_text(encoding="utf-8"))
    raw["manifest"]["slides"][0]["headline"] = "Different valid headline"
    finish_proof[0].write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="ACCEPTED_EP104_MANIFEST_REQUIRED"):
        compose(finish_proof)


@pytest.mark.parametrize("field", ["slide", "geometry", "output_sha256", "portrait_sha256", "typography"])
def test_changed_c3_core_fail_closed(finish_proof, field):
    raw = json.loads(finish_proof[2].read_text(encoding="utf-8"))
    raw[field] = None
    finish_proof[2].write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="ACCEPTED_C3_CORE_REQUIRED"):
        compose(finish_proof)


def test_changed_control_source_and_canonical_portrait_fail(finish_proof):
    paths_and_errors = ((finish_proof[1], "ACCEPTED_C3_RASTER_REQUIRED"),
                        (finish_proof[3], "ACCEPTED_ALBEDO_ART_REQUIRED"),
                        (finish.ROOT / "assets/characters/kai_patel.png", "CANONICAL_KAI_SOURCE_REQUIRED"))
    for path, error in paths_and_errors:
        original = path.read_bytes()
        Image.new("RGB", (1080, 1080), "red").save(path)
        with pytest.raises(ValueError, match=error):
            compose(finish_proof)
        path.write_bytes(original)
    assert not finish_proof[-1].exists()


def test_public_attribution_gate_retained(finish_proof):
    report = compose(finish_proof)
    assert report["publication_handoff"]["state"] == "BLOCKED"
    assert not report["production_publication_allowed"] and report["visual_parity"] == "NOT CLAIMED"
    raw = json.loads(finish_proof[4].read_text(encoding="utf-8"))
    raw["publication_handoff"]["state"] = "READY"
    finish_proof[4].write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="ATTRIBUTION_AUDIT_REQUIRED"):
        compose(finish_proof)


def test_path_escape_and_alias_protect_evidence(finish_proof):
    outside = finish.ROOT / "outside.png"
    shutil.copyfile(finish_proof[1], outside)
    args = list(finish_proof)
    args[1] = outside
    with pytest.raises(ValueError, match="PATH_ESCAPE"):
        finish.finish_proof(*args)
    args = list(finish_proof)
    args[-1] = outside
    with pytest.raises(ValueError, match="PATH_ESCAPE"):
        finish.finish_proof(*args)
    alias = finish_proof[-1]
    alias.parent.mkdir(parents=True)
    shutil.copyfile(finish_proof[1], alias)
    args = list(finish_proof)
    args[1] = alias
    with pytest.raises(ValueError, match="OUTPUT_SOURCE_COLLISION"):
        finish.finish_proof(*args)
    assert alias.read_bytes() == finish_proof[1].read_bytes()
    with pytest.raises(ValueError, match="PATH_ESCAPE"):
        finish.write_report({}, finish.ROOT / "outside")


@pytest.mark.parametrize("raw", [None, [], {}, {"blockers": []}])
def test_cli_malformed_snapshot_blocks(finish_proof, raw, capsys):
    finish_proof[0].write_text(json.dumps(raw))
    assert finish.main(["--accepted-snapshot", str(finish_proof[0])]) == 1
    assert json.loads(capsys.readouterr().out)["state"] == "BLOCKED"


def test_cli_success_and_complete_report(finish_proof, capsys):
    snapshot, baseline, report, asset, metadata, output = finish_proof
    assert finish.main(["--accepted-snapshot", str(snapshot), "--control", str(baseline),
                        "--control-report", str(report), "--asset", str(asset), "--acceptance-metadata", str(metadata)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["state"] == finish.REVIEW and result["provider_calls"] == result["new_generation_count"] == 0
    path = finish.ROOT / finish.PACKAGE / "report/fidelity-report.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["c3_control_sha256"] == hashlib.sha256(baseline.read_bytes()).hexdigest()
    assert saved["protected_face_and_copy_pixels"] == "UNCHANGED"
    assert saved["micro_detail"]["semantic_text"] == []
    assert "TEST ONLY recorded credit" in path.with_suffix(".md").read_text(encoding="utf-8")


def test_production_pins_and_ignored_package():
    assert finish.CONTROL_SHA256 == "530787d58f9dfd1074ccf89858e610567f01c6d4bf9e73d372b8faf3c0a76672"
    assert finish.MANIFEST_SHA256 == "955c5aad9d28e044f7454032cd811f39bc7eb5fa55798d87e5384b6a6f2e405d"
    assert finish.CORE_SHA256 == "2f4aadf41cfb4151923a10303191a671b801e2a3a58e7daee8742a1966a73692"
    assert hashlib.sha256((REPO / "assets/characters/kai_patel.png").read_bytes()).hexdigest() == finish.PORTRAIT_SHA256
    paths = [str(finish.PACKAGE / p) for p in ("reference/Slide05of20-current-final.png",
        "reference/kai-historical-exemplar.png", "control/slide05-phase-c3-control.png",
        "input/context-art.png", "phase4/slide05-phase4.png")]
    result = subprocess.run(["git", "check-ignore", *paths], cwd=REPO, text=True, capture_output=True)
    assert result.returncode == 0 and len(result.stdout.splitlines()) == 5
