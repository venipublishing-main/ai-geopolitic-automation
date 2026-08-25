from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(ROOT / "src"))

from editorial_primitives import LayoutError
from route_episode import load_json, render_episode, select_layout, validate_routing_config


def configs():
    routing = load_json(ROOT / "config/layout_routing.json")
    presets = load_json(ROOT / "config/layout_presets.json")
    return routing, presets


def test_routing_config_only_uses_approved_families():
    routing, presets = configs()
    validate_routing_config(routing, presets)


def test_content_type_rule_selects_character_specific_family():
    routing, presets = configs()
    family, source = select_layout(
        {"speaker": "johan_vosloo", "content_type": "governance_handoff"},
        routing,
        presets,
    )
    assert family == "containment_chain"
    assert source == "content_type_rule"


def test_valid_explicit_override_wins():
    routing, presets = configs()
    family, source = select_layout(
        {
            "speaker": "diane_sterling",
            "content_type": "economic_transmission",
            "layout_override": "fiscal_flow",
        },
        routing,
        presets,
    )
    assert family == "fiscal_flow"
    assert source == "explicit_override"


def test_unapproved_override_fails_closed():
    routing, presets = configs()
    with pytest.raises(LayoutError):
        select_layout(
            {"speaker": "kai_patel", "layout_override": "market_grid"},
            routing,
            presets,
        )


def test_unknown_content_type_fails_closed():
    routing, presets = configs()
    with pytest.raises(LayoutError):
        select_layout(
            {"speaker": "amari_ndlovu", "content_type": "unknown_mode"},
            routing,
            presets,
        )


def test_routing_proof_manifest_matches_expected_layouts():
    routing, presets = configs()
    manifest = load_json(ROOT / "inputs/routing-proof-episode.json")
    assert len(manifest["slides"]) == 14
    for item in manifest["slides"]:
        selected, _ = select_layout(item, routing, presets)
        assert selected == item["expected_layout"]


def test_full_routing_proof_renders_and_reports(tmp_path: Path):
    output = tmp_path / "routing-proof"
    report = render_episode(ROOT / "inputs/routing-proof-episode.json", output)

    assert report["total_slides"] == 14
    assert len(report["slides"]) == 14
    assert report["slides"][0]["selected_layout"] == "episode_opener"
    assert report["slides"][-1]["selected_layout"] == "episode_closer"

    for index in range(1, 15):
        path = output / f"slide_{index:02d}.png"
        assert path.exists()
        with Image.open(path) as image:
            assert image.size == (1080, 1080)

    assert (output / "routing-contact-sheet.png").exists()
    assert (output / "routing-report.json").exists()
    assert (output / "routing-report.md").exists()
    assert len(list((output / "resolved-inputs").glob("slide_*.json"))) == 14

    on_disk = json.loads((output / "routing-report.json").read_text(encoding="utf-8"))
    assert on_disk["routing_policy"] == "deterministic_content_type_with_explicit_override"
    assert set(on_disk["speaker_counts"]) == {
        "nora", "johan_vosloo", "diane_sterling", "kai_patel", "thabo_mokoena", "amari_ndlovu"
    }
