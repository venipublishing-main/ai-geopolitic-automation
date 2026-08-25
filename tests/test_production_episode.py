from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(ROOT / "src"))

from editorial_primitives import LayoutError
from render_production_episode import (
    compile_slide,
    render_production_episode,
    validate_production_manifest,
)
from route_episode import load_json, validate_routing_config


def configs():
    routing = load_json(ROOT / "config/layout_routing.json")
    presets = load_json(ROOT / "config/layout_presets.json")
    validate_routing_config(routing, presets)
    return routing, presets


def proof_manifest():
    return load_json(ROOT / "inputs/production-schema-proof.json")


def test_production_schema_proof_is_exactly_twenty_slides():
    routing, presets = configs()
    manifest = proof_manifest()
    slides = validate_production_manifest(manifest, routing, presets)
    assert len(slides) == 20


def test_production_schema_rejects_non_twenty_slide_episode():
    routing, presets = configs()
    manifest = proof_manifest()
    manifest["slides"] = manifest["slides"][:-1]
    with pytest.raises(LayoutError):
        validate_production_manifest(manifest, routing, presets)


def test_production_schema_rejects_compiler_owned_fields():
    routing, presets = configs()
    manifest = proof_manifest()
    manifest["slides"][3]["slide_number"] = 4
    with pytest.raises(LayoutError):
        validate_production_manifest(manifest, routing, presets)


def test_production_schema_rejects_reserved_visual_collision():
    routing, presets = configs()
    manifest = proof_manifest()
    manifest["slides"][8].setdefault("visual", {})["headline"] = "illegal"
    with pytest.raises(LayoutError):
        validate_production_manifest(manifest, routing, presets)


def test_production_schema_enforces_nora_opener_and_closer():
    routing, presets = configs()
    manifest = proof_manifest()
    manifest["slides"][0] = copy.deepcopy(manifest["slides"][1])
    with pytest.raises(LayoutError):
        validate_production_manifest(manifest, routing, presets)


def test_compile_slide_injects_numbering_and_selected_layout():
    routing, presets = configs()
    manifest = proof_manifest()
    spec, audit = compile_slide(manifest, manifest["slides"][9], 10, routing, presets)
    assert spec["slide_number"] == 10
    assert spec["total_slides"] == 20
    assert spec["layout_family"] == "monitoring_loop"
    assert "monitors" in spec
    assert audit["selection_source"] == "content_type_rule"


def test_full_production_schema_proof_renders_twenty_and_reports(tmp_path: Path):
    output = tmp_path / "production-proof"
    report = render_production_episode(ROOT / "inputs/production-schema-proof.json", output)
    assert report["total_slides"] == 20
    assert len(report["slides"]) == 20
    assert report["slides"][0]["selected_layout"] == "episode_opener"
    assert report["slides"][-1]["selected_layout"] == "episode_closer"

    for index in range(1, 21):
        path = output / f"slide_{index:02d}.png"
        assert path.exists()
        with Image.open(path) as image:
            assert image.size == (1080, 1080)

    assert (output / "episode-contact-sheet.png").exists()
    assert (output / "production-report.json").exists()
    assert (output / "production-report.md").exists()
    assert (output / "resolved-episode.json").exists()
    assert len(list((output / "resolved-inputs").glob("slide_*.json"))) == 20
