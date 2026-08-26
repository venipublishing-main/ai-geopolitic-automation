from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from contextual_illustrations import (
    ALLOWED_PROCEDURAL_KINDS,
    apply_context_art,
    validate_context_art_spec,
)
from editorial_primitives import LayoutError, PAPER
from render_production_episode import render_production_episode, validate_production_manifest
from route_episode import load_json, validate_routing_config

MANIFEST = ROOT / "inputs/episode-029-context-art-5.2.json"


def digest(image: Image.Image) -> str:
    return hashlib.sha256(image.tobytes()).hexdigest()


def test_procedural_context_art_is_deterministic():
    spec = {
        "source": "procedural",
        "kind": "water_infrastructure",
        "box": [120, 180, 900, 820],
        "opacity": 0.55,
        "layer": "background",
        "paper_wash": False,
    }
    a = Image.new("RGB", (1080, 1080), PAPER)
    b = Image.new("RGB", (1080, 1080), PAPER)
    apply_context_art(a, (23, 60, 104), spec, seed=5)
    apply_context_art(b, (23, 60, 104), spec, seed=5)
    assert digest(a) == digest(b)
    assert digest(a) != digest(Image.new("RGB", (1080, 1080), PAPER))


def test_all_six_procedural_context_kinds_are_distinct():
    hashes = set()
    for idx, kind in enumerate(sorted(ALLOWED_PROCEDURAL_KINDS), start=1):
        image = Image.new("RGB", (1080, 1080), PAPER)
        spec = {
            "source": "procedural",
            "kind": kind,
            "box": [120, 180, 900, 820],
            "opacity": 0.58,
            "layer": "background",
            "paper_wash": False,
        }
        apply_context_art(image, (70, 70, 70), spec, seed=idx)
        hashes.add(digest(image))
    assert len(hashes) == len(ALLOWED_PROCEDURAL_KINDS) == 6


def test_context_art_validation_fails_closed():
    with pytest.raises(LayoutError):
        validate_context_art_spec({
            "source": "procedural",
            "kind": "mystery_scene",
            "box": [120, 180, 900, 820],
        })
    with pytest.raises(LayoutError):
        validate_context_art_spec({
            "source": "asset",
            "path": "../portrait.png",
            "box": [120, 180, 900, 820],
        })
    with pytest.raises(LayoutError):
        validate_context_art_spec({
            "source": "procedural",
            "kind": "river_monitoring",
            "box": [40, 80, 900, 820],
        })


def test_foreground_exclusions_protect_exact_layout_regions():
    base_spec = {
        "source": "procedural",
        "kind": "casefile_system",
        "box": [120, 180, 900, 820],
        "opacity": 0.72,
        "layer": "foreground",
        "paper_wash": False,
    }
    unprotected = Image.new("RGB", (1080, 1080), PAPER)
    apply_context_art(unprotected, (23, 105, 170), base_spec, seed=2, stage="foreground")

    protected_spec = dict(base_spec)
    protected_spec["exclusions"] = [[250, 250, 650, 520]]
    protected = Image.new("RGB", (1080, 1080), PAPER)
    apply_context_art(protected, (23, 105, 170), protected_spec, seed=2, stage="foreground")

    protected_crop = protected.crop((250, 250, 650, 520))
    blank_crop = Image.new("RGB", protected_crop.size, PAPER)
    assert digest(protected_crop) == digest(blank_crop)
    assert digest(unprotected.crop((250, 250, 650, 520))) != digest(blank_crop)


def test_ep029_context_art_manifest_has_one_proof_for_each_presenter():
    manifest = load_json(MANIFEST)
    routing = load_json(ROOT / "config/layout_routing.json")
    presets = load_json(ROOT / "config/layout_presets.json")
    validate_routing_config(routing, presets)
    validate_production_manifest(manifest, routing, presets)

    illustrated = []
    for index, slide in enumerate(manifest["slides"], start=1):
        context = (slide.get("visual") or {}).get("context_art")
        if context:
            illustrated.append((index, slide["speaker"], context["kind"], context["layer"]))
    assert len(illustrated) == 6
    assert {speaker for _, speaker, _, _ in illustrated} == {
        "nora",
        "johan_vosloo",
        "diane_sterling",
        "kai_patel",
        "thabo_mokoena",
        "amari_ndlovu",
    }
    assert all(layer == "foreground" for _, _, _, layer in illustrated)


def test_full_context_art_benchmark_renders_and_audits_six_illustrations(tmp_path: Path):
    output = tmp_path / "contextual"
    report = render_production_episode(MANIFEST, output)
    assert report["total_slides"] == 20
    assert report["context_art_count"] == 6
    assert report["context_art_source_counts"] == {"procedural": 6}
    assert len(report["context_art_kind_counts"]) == 6
    assert (output / "episode-contact-sheet.png").exists()
    for index in range(1, 21):
        with Image.open(output / f"slide_{index:02d}.png") as image:
            assert image.size == (1080, 1080)

    on_disk = json.loads((output / "production-report.json").read_text(encoding="utf-8"))
    assert on_disk["context_art_count"] == 6
