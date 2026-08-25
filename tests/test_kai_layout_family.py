import json
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.editorial_primitives import LayoutError
from src.render_kai_layout_family import FAMILIES, render


SAMPLES = {
    "network_mesh": "kai-network-mesh.json",
    "feedback_system": "kai-feedback-system.json",
    "monitoring_loop": "kai-monitoring-loop.json",
    "decentralised_pathway": "kai-decentralised-pathway.json",
    "repair_network": "kai-repair-network.json",
}


def test_kai_family_matches_approved_presets():
    presets = json.loads((ROOT / "config/layout_presets.json").read_text(encoding="utf-8"))
    assert set(presets["kai_patel"]["approved_families"]) == FAMILIES


def test_all_five_kai_families_render(tmp_path):
    for family, filename in SAMPLES.items():
        out = tmp_path / f"{family}.png"
        render(ROOT / "inputs" / filename, out)
        with Image.open(out) as im:
            assert im.size == (1080, 1080)
            assert im.mode == "RGB"


def test_kai_renderer_rejects_wrong_speaker(tmp_path):
    data = json.loads((ROOT / "inputs/kai-feedback-system.json").read_text(encoding="utf-8"))
    data["speaker"] = "nora"
    path = tmp_path / "wrong-speaker.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad.png")


def test_kai_renderer_rejects_unknown_family(tmp_path):
    data = json.loads((ROOT / "inputs/kai-monitoring-loop.json").read_text(encoding="utf-8"))
    data["layout_family"] = "generic_social_card"
    path = tmp_path / "wrong-family.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad.png")


def test_kai_family_rejects_episode_opener_or_closer_roles(tmp_path):
    data = json.loads((ROOT / "inputs/kai-network-mesh.json").read_text(encoding="utf-8"))
    data["slide_number"] = 1
    path = tmp_path / "wrong-role.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad.png")

    data["slide_number"] = 20
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad2.png")


def test_kai_specialised_layouts_validate_required_structures(tmp_path):
    feedback = json.loads((ROOT / "inputs/kai-feedback-system.json").read_text(encoding="utf-8"))
    feedback["mechanism"] = feedback["mechanism"][:3]
    bad_feedback = tmp_path / "bad-feedback.json"
    bad_feedback.write_text(json.dumps(feedback), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_feedback, tmp_path / "bad-feedback.png")

    monitoring = json.loads((ROOT / "inputs/kai-monitoring-loop.json").read_text(encoding="utf-8"))
    monitoring["monitors"] = monitoring["monitors"][:3]
    bad_monitoring = tmp_path / "bad-monitoring.json"
    bad_monitoring.write_text(json.dumps(monitoring), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_monitoring, tmp_path / "bad-monitoring.png")

    pathway = json.loads((ROOT / "inputs/kai-decentralised-pathway.json").read_text(encoding="utf-8"))
    pathway["routes"] = pathway["routes"][:4]
    bad_pathway = tmp_path / "bad-pathway.json"
    bad_pathway.write_text(json.dumps(pathway), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_pathway, tmp_path / "bad-pathway.png")

    repair = json.loads((ROOT / "inputs/kai-repair-network.json").read_text(encoding="utf-8"))
    repair["repair_steps"] = repair["repair_steps"][:4]
    bad_repair = tmp_path / "bad-repair.json"
    bad_repair.write_text(json.dumps(repair), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_repair, tmp_path / "bad-repair.png")


def test_kai_contact_sheet_utility(tmp_path):
    from src.make_contact_sheet import make_contact_sheet

    rendered = []
    for filename in ("kai-feedback-system.json", "kai-repair-network.json"):
        out = tmp_path / filename.replace(".json", ".png")
        render(ROOT / "inputs" / filename, out)
        rendered.append(out)

    sheet = tmp_path / "contact.png"
    make_contact_sheet(rendered, sheet, cols=2, thumb=220)
    with Image.open(sheet) as im:
        assert im.width > 400
        assert im.height > 240
