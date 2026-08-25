from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from render_production_episode import render_production_episode, validate_production_manifest
from route_episode import load_json, select_layout, validate_routing_config

MANIFEST_PATH = ROOT / "inputs/episode-029-20july2026.json"

EXPECTED_SPEAKERS = [
    "nora",
    "nora",
    "johan_vosloo",
    "kai_patel",
    "johan_vosloo",
    "johan_vosloo",
    "thabo_mokoena",
    "amari_ndlovu",
    "johan_vosloo",
    "nora",
    "thabo_mokoena",
    "kai_patel",
    "kai_patel",
    "diane_sterling",
    "nora",
    "diane_sterling",
    "diane_sterling",
    "amari_ndlovu",
    "kai_patel",
    "nora",
]

EXPECTED_LAYOUTS = [
    "episode_opener",
    "system_axis",
    "oversight_gate",
    "monitoring_loop",
    "order_corridor",
    "containment_chain",
    "material_chain",
    "dignity_pathway",
    "principle_test",
    "feedback_loop",
    "burden_ledger",
    "decentralised_pathway",
    "network_mesh",
    "market_grid",
    "feedback_loop",
    "transmission_chain",
    "transmission_chain",
    "humanitarian_map",
    "repair_network",
    "episode_closer",
]


def configs():
    routing = load_json(ROOT / "config/layout_routing.json")
    presets = load_json(ROOT / "config/layout_presets.json")
    validate_routing_config(routing, presets)
    return routing, presets


def test_ep029_benchmark_is_a_real_20_slide_production_manifest():
    manifest = load_json(MANIFEST_PATH)
    routing, presets = configs()
    slides = validate_production_manifest(manifest, routing, presets)
    assert manifest["episode_id"] == "ep029-20july2026-follow-through"
    assert manifest["episode_date"] == "20 JULY 2026"
    assert len(slides) == 20


def test_ep029_preserves_original_presenter_sequence():
    manifest = load_json(MANIFEST_PATH)
    assert [slide["speaker"] for slide in manifest["slides"]] == EXPECTED_SPEAKERS
    assert set(EXPECTED_SPEAKERS) == {
        "nora",
        "johan_vosloo",
        "diane_sterling",
        "kai_patel",
        "thabo_mokoena",
        "amari_ndlovu",
    }


def test_ep029_routes_to_expected_character_specific_layouts():
    manifest = load_json(MANIFEST_PATH)
    routing, presets = configs()
    selected = [select_layout(slide, routing, presets)[0] for slide in manifest["slides"]]
    assert selected == EXPECTED_LAYOUTS
    assert len(set(selected)) >= 12


def test_ep029_contains_no_manual_layout_overrides():
    manifest = load_json(MANIFEST_PATH)
    assert all(not slide.get("layout_override") for slide in manifest["slides"])


def test_ep029_full_benchmark_renders_20_standalone_slides(tmp_path: Path):
    output = tmp_path / "ep029"
    report = render_production_episode(MANIFEST_PATH, output)
    assert report["total_slides"] == 20
    assert report["override_count"] == 0
    assert len(report["slides"]) == 20
    assert report["slides"][0]["selected_layout"] == "episode_opener"
    assert report["slides"][-1]["selected_layout"] == "episode_closer"

    for index in range(1, 21):
        path = output / f"slide_{index:02d}.png"
        assert path.exists()
        with Image.open(path) as image:
            assert image.size == (1080, 1080)

    assert (output / "episode-contact-sheet.png").exists()
    assert (output / "resolved-episode.json").exists()
    assert (output / "production-report.json").exists()
    assert (output / "production-report.md").exists()
    assert len(list((output / "resolved-inputs").glob("slide_*.json"))) == 20

    on_disk = json.loads((output / "production-report.json").read_text(encoding="utf-8"))
    assert set(on_disk["speaker_counts"]) == set(EXPECTED_SPEAKERS)
