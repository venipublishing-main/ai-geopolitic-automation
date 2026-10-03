"""Local fusion regressions: source/geometry/integration, never a beauty score."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess

from PIL import Image, ImageChops, ImageDraw, ImageOps
import pytest

from src import editorial_fusion as fusion, premium_compositor as control
from test_premium_compositor import local_proof
from test_phase_c_kai_bridge import kai_ready

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def fusion_proof(local_proof, monkeypatch, tmp_path):
    monkeypatch.setattr(fusion, "ROOT", tmp_path)
    ready, source, metadata, _ = local_proof
    return ready, source, metadata, tmp_path / fusion.PACKAGE / "phase3/slide05-phase3.png"


def compose(proof):
    return fusion.compose_fusion(*proof)


def test_exact_copy_identity_scope_and_png(fusion_proof):
    report = compose(fusion_proof)
    source = fusion_proof[0].manifest["slides"][4]
    spec = report["slide"]
    assert (spec["episode_id"], spec["slide_number"], spec["total_slides"], spec["production_date_sast"]) == ("Ep104", 5, 20, "2026-10-03")
    assert spec["panelist"] == "kai_patel" and report["accent_hex"] == "#6540A4"
    assert report["portrait_sha256"] == hashlib.sha256((REPO / "assets/characters/kai_patel.png").read_bytes()).hexdigest()
    text = {r["name"]: r["text"] for r in report["geometry"]["protected_text"]}
    assert text["headline_black"] + " " + text["headline_accent"] == source["headline"]
    assert text["subheadline"] == source["subheadline"]
    assert text["phrase_first"] + " " + text["phrase_second"] == source["main_visual_phrase"]
    assert text["core_argument"] == source["core_argument"]
    assert [text[f"label_{i}"] for i in range(6)] == source["essential_labels"]
    assert [text[f"takeaway_idea_{i}"] for i in range(1, 4)] == [r["idea"] for r in source["takeaway_ideas"]]
    assert [text[f"takeaway_number_{i}"] for i in range(1, 4)] == ["01", "02", "03"]
    assert (text["footer"], text["counter"], text["episode"], text["date"]) == (fusion.MOTTO, "05/20", "Ep104", "SATURDAY, 3 OCTOBER 2026")
    with Image.open(report["output"]) as image:
        assert image.format == "PNG" and image.size == (1080, 1080)
        image.verify()


def test_native_display_type_no_clipping_or_collision(fusion_proof):
    report = compose(fusion_proof)
    rows = report["geometry"]["protected_text"]
    for i, row in enumerate(rows):
        x0, y0, x1, y1 = row["bounds"]
        assert 36 <= x0 < x1 <= 1044 and 36 <= y0 < y1 <= 1050
        assert not any(control._intersects(row["bounds"], other["bounds"]) for other in rows[i + 1:])
    for row in report["typography"].values():
        assert row["raster_glyph_resize"] is False
    assert report["typography"]["headline_black"]["font"] == "Anton"
    assert report["typography"]["headline_black"]["size"] >= 90


def test_common_ink_path_opaque_hero_and_unwarped_portrait(fusion_proof, monkeypatch):
    calls = []
    original = fusion.prepare_editorial_engraving
    def capture(source, **kwargs):
        calls.append((source.copy(), kwargs))
        return original(source, **kwargs)
    monkeypatch.setattr(fusion, "prepare_editorial_engraving", capture)
    report = compose(fusion_proof)
    assert [c[1]["origin"] for c in calls] == [fusion.HERO[:2], fusion.PORTRAIT[:2]]
    assert report["geometry"]["hero_centre_alpha"] == 255
    portrait = fusion.ROOT / "assets/characters/kai_patel.png"
    crop = control.compile_slide(fusion_proof[0]).crop_box
    with Image.open(portrait) as source:
        used = (crop[0], max(crop[1], round(source.height * .03)), crop[2], crop[3])
        expected = ImageOps.fit(source.convert("RGB").crop(used), calls[1][0].size, Image.Resampling.LANCZOS, centering=(.52, .48))
    assert ImageChops.difference(calls[1][0], expected).getbbox() is None
    # A strong neutral tonal range survives the shared process, including detail.
    ink = original(calls[0][0], **calls[0][1]).convert("L")
    assert len(set(ink.getdata())) > 100
    assert min(ink.getdata()) < 35 and max(ink.getdata()) > 230


def test_semantic_routes_glyph_knockouts_and_protected_regions(fusion_proof):
    report = compose(fusion_proof)
    geometry = report["geometry"]
    assert set(geometry["callout_anchors"]) == set(fusion.LABELS)
    assert {(r["from"], r["to"]) for r in geometry["routes"]} == {
        ("REMOTE USERS", "FIBRE"), ("FIBRE", "COMPUTE"),
        ("COMPUTE", "POWER"), ("COMPUTE", "COOLING"), ("COMPUTE", "LAND")}
    mask = fusion.route_mask()
    for route in fusion.ROUTES:
        assert route["points"][0] == fusion.ANCHORS[route["from"]]["point"]
        assert route["points"][-1] == fusion.ANCHORS[route["to"]]["point"]
    fusion.validate_route_mask(mask, geometry["protected_text"])
    assert mask.crop(fusion.FACE).getbbox() is None
    assert geometry["opaque_label_cards"] == 0
    assert geometry["label_knockout"] == "glyph strokes + 1px"
    # The glyph knockout is sparse, not its entire bounding rectangle.
    image = Image.new("RGB", (1080, 1080), fusion.INK)
    fusion._type(image, [], {}, "label", "COOLING", (500, 400, 700, 440),
                 colour=fusion.ACCENT, size=25, display=True, knockout=True)
    region = list(image.crop((500, 400, 700, 440)).getdata())
    assert sum(p == fusion.INK for p in region) > len(region) * .6


@pytest.mark.parametrize("region", [fusion.FACE, (470, 440, 510, 470)])
def test_actual_route_pixel_collision_blocks(region):
    mask = Image.new("L", (1080, 1080))
    ImageDraw.Draw(mask).point((region[0] + 3, region[1] + 3), fill=255)
    rows = [] if region == fusion.FACE else [{"name": "copy", "bounds": region}]
    with pytest.raises(ValueError, match="ROUTE_CROSSES_PROTECTED_REGION"):
        fusion.validate_route_mask(mask, rows)


def test_microdetail_is_graphical_face_safe_and_changes_pixels(fusion_proof, monkeypatch):
    layer = fusion.micro_detail_layer()
    assert layer.getbbox() and layer.crop(fusion.FACE).getbbox() is None
    def no_text(*a, **kw):
        pytest.fail("Micro-detail may not generate prose/data")
    with monkeypatch.context() as scoped:
        scoped.setattr(ImageDraw.ImageDraw, "text", no_text)
        scoped.setattr(ImageDraw.ImageDraw, "multiline_text", no_text)
        assert fusion.micro_detail_layer().tobytes() == layer.tobytes()
    first = compose(fusion_proof)
    with Image.open(first["output"]) as image:
        with_detail = image.copy()
    monkeypatch.setattr(fusion, "micro_detail_layer", lambda: Image.new("RGBA", (1080, 1080)))
    compose(fusion_proof)
    with Image.open(first["output"]) as image:
        diff = ImageChops.difference(with_detail, image)
        assert diff.crop((460, 890, 1036, 903)).getbbox() is not None
        assert diff.crop((380, 650, 460, 744)).getbbox() is not None
    assert first["micro_detail"]["semantic_text"] == []


def test_c2_reproducible_and_fusion_materially_changes_regions(fusion_proof, local_proof):
    c2 = control.compose_premium(*local_proof)
    original = Path(c2["output"]).read_bytes()
    c3 = compose(fusion_proof)
    assert Path(c2["output"]).read_bytes() == original
    again = control.compose_premium(*local_proof)
    assert Path(again["output"]).read_bytes() == original
    with Image.open(c2["output"]) as prior, Image.open(c3["output"]) as new:
        for box, minimum in (((500, 570, 850, 670), .05), ((360, 480, 455, 745), .05),
                             ((430, 365, 1033, 561), .05), ((460, 891, 1036, 903), .02)):
            diff = ImageChops.difference(prior.crop(box), new.crop(box))
            changed = sum(max(p) > 6 for p in diff.getdata())
            # Sparse construction ticks deliberately occupy less than the scene.
            assert changed > diff.width * diff.height * minimum
    # Repeating fusion is byte-identical with the same input, not a beauty test.
    digest = c3["output_sha256"]
    assert compose(fusion_proof)["output_sha256"] == digest


def test_black_structure_dominates_restrained_accent(fusion_proof):
    report = compose(fusion_proof)
    with Image.open(report["output"]) as image:
        pixels = list(image.crop(fusion.HERO).getdata())
    purple = sum(b > r + 25 and r > g + 15 for r, g, b in pixels)
    dark = sum(max(p) < 130 and max(p) - min(p) < 20 for p in pixels)
    assert purple < len(pixels) * .08 and dark > purple * 2


def test_no_generation_no_network_no_legacy_no_runtime_references(fusion_proof, monkeypatch):
    from src.providers.contracts import GenerationJob
    from src.providers.router import GenerationRouter
    from src.providers.cloud.ai_horde import AIHordeProvider
    from src.providers.cloud.cloudflare_workers_ai import CloudflareWorkersAIProvider
    from src.providers.local.wangp import WanGPProvider
    from src.providers.local.comfyui import ComfyUIProvider
    from src import contextual_illustrations, render_kai_layout_family, render_identity_slide
    def forbidden(*a, **kw):
        pytest.fail("C.3 may only compose local accepted art")
    for cls in (GenerationJob, GenerationRouter, AIHordeProvider, CloudflareWorkersAIProvider, WanGPProvider, ComfyUIProvider):
        monkeypatch.setattr(cls, "__init__", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(render_kai_layout_family, "render_network_mesh", forbidden)
    monkeypatch.setattr(render_kai_layout_family, "render", forbidden)
    monkeypatch.setattr(render_identity_slide, "render_kai", forbidden)
    monkeypatch.setattr(contextual_illustrations, "_asset_plate", forbidden)
    monkeypatch.setattr(contextual_illustrations, "apply_context_art", forbidden)
    monkeypatch.setattr(control, "compose_premium", forbidden)
    opened = []
    original_open = Image.open
    def local_only(path, *a, **kw):
        opened.append(str(path))
        assert "reference" not in str(path)
        return original_open(path, *a, **kw)
    monkeypatch.setattr(Image, "open", local_only)
    report = compose(fusion_proof)
    assert report["provider_calls"] == report["new_generation_count"] == 0
    assert report["runtime_reference_dependency"] is False
    assert not report["legacy_network_mesh_invoked"] and not report["legacy_asset_plate_invoked"]
    assert not (fusion.ROOT / fusion.PACKAGE / "reference").exists()
    assert len(opened) >= 4


@pytest.mark.parametrize("change", [{"build": "BLOCKED"}, {"state": "BUILD_BLOCKED"},
                                    {"production_date_sast": "2026-10-02"}])
def test_readiness_fail_closed(fusion_proof, change):
    ready, art, metadata, output = fusion_proof
    with pytest.raises(ValueError, match="LIVE_BUILD_READY_REQUIRED"):
        fusion.compose_fusion(replace(ready, **change), art, metadata, output)
    assert not output.exists()


@pytest.mark.parametrize("change", [{"slide_number": 6}, {"panelists": ["nora"]},
    {"pairing_mode": "SUPPORTIVE_CONVERGENT"}, {"accent_colours": {"kai_patel": "#FFFFFF"}},
    {"essential_labels": ["FIBRE"]}, {"takeaway_ideas": []}])
def test_one_slide_manifest_fail_closed(fusion_proof, change):
    fusion_proof[0].manifest["slides"][4].update(change)
    with pytest.raises(ValueError):
        compose(fusion_proof)
    assert not fusion_proof[3].exists()


def test_changed_art_and_missing_metadata_block_before_output(fusion_proof):
    art = fusion_proof[1]
    original = art.read_bytes()
    Image.new("RGB", (1024, 1024), "red").save(art)
    with pytest.raises(ValueError, match="ACCEPTED_ALBEDO_ART_REQUIRED"):
        compose(fusion_proof)
    art.write_bytes(original)
    fusion_proof[2].unlink()
    with pytest.raises(ValueError, match="REQUIRED_LOCAL_ASSET_MISSING"):
        compose(fusion_proof)
    assert not fusion_proof[3].exists()


@pytest.mark.parametrize("handoff", [{"state": "READY"}, {"publication_attribution_required": False},
                                    {"required_attribution_text": ""}])
def test_public_attribution_fail_closed(fusion_proof, handoff):
    data = json.loads(fusion_proof[2].read_text())
    data["publication_handoff"].update(handoff)
    fusion_proof[2].write_text(json.dumps(data))
    with pytest.raises(ValueError, match="ATTRIBUTION_AUDIT_REQUIRED"):
        compose(fusion_proof)
    assert not fusion_proof[3].exists()


def test_source_output_portrait_and_report_escape(fusion_proof):
    ready, art, metadata, output = fusion_proof
    outside = fusion.ROOT / "outside.png"
    shutil.copyfile(art, outside)
    with pytest.raises(ValueError, match="PATH_ESCAPE"):
        fusion.compose_fusion(ready, outside, metadata, output)
    with pytest.raises(ValueError, match="PATH_ESCAPE"):
        fusion.compose_fusion(ready, art, metadata, outside)
    with pytest.raises(ValueError, match="PATH_ESCAPE"):
        fusion._confined(outside, "assets/characters")
    with pytest.raises(ValueError, match="PATH_ESCAPE"):
        fusion.write_report({}, fusion.ROOT / "outside")


def test_output_cannot_replace_accepted_source(fusion_proof):
    ready, art, metadata, output = fusion_proof
    output.parent.mkdir(parents=True)
    shutil.copyfile(art, output)
    original = output.read_bytes()
    with pytest.raises(ValueError, match="OUTPUT_SOURCE_COLLISION"):
        fusion.compose_fusion(ready, output, metadata, output)
    assert output.read_bytes() == original


def test_oversized_copy_blocks_without_rewriting(fusion_proof):
    fusion_proof[0].manifest["slides"][4]["headline"] = "Excessive headline " * 80 + "MEGAWATTS, PIPES AND LAND"
    with pytest.raises(ValueError, match="DISPLAY_COPY_TOO_LONG"):
        compose(fusion_proof)
    assert not fusion_proof[3].exists()


def test_report_provenance_credit_and_human_review(fusion_proof):
    report = compose(fusion_proof)
    directory = fusion.ROOT / fusion.PACKAGE / "report"
    fusion.write_report(report, directory)
    saved = json.loads((directory / "fusion-report.json").read_text(encoding="utf-8"))
    assert saved["state"] == fusion.REVIEW and saved["visual_parity"] == "NOT CLAIMED"
    assert saved["publication_handoff"]["state"] == "BLOCKED" and not saved["production_publication_allowed"]
    assert saved["source_asset_sha256"] == hashlib.sha256(fusion_proof[1].read_bytes()).hexdigest()
    assert "TEST ONLY recorded credit" in (directory / "fusion-report.md").read_text()
    assert [r["drive_id"] for r in saved["development_references"]] == [
        "1jLaocNFP31PQvXmOAZNDSyjzmkbjaQO4", "1mRRuboHP9VVcftljZ9X7lJ1oPhAsbpS9"]


@pytest.mark.parametrize("raw", [None, [], {"blockers": ["blocked"]}, {"blockers": [], "build": "READY"}])
def test_cli_malformed_snapshot_exit_one(fusion_proof, raw, capsys):
    path = fusion.ROOT / "output/readiness.json"
    path.write_text(json.dumps(raw))
    assert fusion.main(["--readiness", str(path)]) == 1
    assert json.loads(capsys.readouterr().out)["state"] == "BLOCKED"


def test_cli_success_is_local_proof_and_report(fusion_proof, capsys):
    ready, art, metadata, output = fusion_proof
    path = fusion.ROOT / "output/readiness.json"
    path.write_text(json.dumps(asdict(ready)))
    assert fusion.main(["--readiness", str(path), "--asset", str(art), "--acceptance-metadata", str(metadata)]) == 0
    assert json.loads(capsys.readouterr().out)["state"] == fusion.REVIEW
    assert output.is_file()
    assert (fusion.ROOT / fusion.PACKAGE / "report/fusion-report.json").is_file()


def test_accepted_source_pin_and_vendored_font_license():
    assert control.ACCEPTED_SHA256 == "af911721d389f3b6a658d18e3e0ba30f93c48bb041be51a7060bf69255f2288b"
    assert hashlib.sha256(fusion.DISPLAY_FONT.read_bytes()).hexdigest() == "a4ba3a92350ebb031da0cb47630ac49eb265082ca1bc0450442f4a83ab947cab"
    assert "SIL OPEN FONT LICENSE Version 1.1" in fusion.DISPLAY_FONT.with_name("OFL.txt").read_text()


def test_package_rasters_are_ignored():
    paths = [str(fusion.PACKAGE / suffix) for suffix in (
        "reference/Slide05of20-current-final.png", "reference/kai-historical-exemplar.png",
        "control/slide05-phase-c2-control.png", "input/context-art.png", "phase3/slide05-phase3.png")]
    result = subprocess.run(["git", "check-ignore", *paths], cwd=REPO, capture_output=True, text=True)
    assert result.returncode == 0 and len(result.stdout.splitlines()) == 5
