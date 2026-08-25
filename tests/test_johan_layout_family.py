import json
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.editorial_primitives import LayoutError
from src.render_johan_layout_family import FAMILIES, render


SAMPLES = {
    "institutional_spine": "johan-institutional-spine.json",
    "containment_chain": "johan-containment-chain.json",
    "oversight_gate": "johan-oversight-gate.json",
    "order_corridor": "johan-order-corridor.json",
    "principle_test": "johan-principle-test.json",
}


def test_johan_family_matches_approved_presets():
    presets = json.loads((ROOT / "config/layout_presets.json").read_text(encoding="utf-8"))
    assert set(presets["johan_vosloo"]["approved_families"]) == FAMILIES


def test_all_five_johan_families_render(tmp_path):
    for family, filename in SAMPLES.items():
        out = tmp_path / f"{family}.png"
        render(ROOT / "inputs" / filename, out)
        with Image.open(out) as im:
            assert im.size == (1080, 1080)
            assert im.mode == "RGB"


def test_johan_renderer_rejects_wrong_speaker(tmp_path):
    data = json.loads((ROOT / "inputs/johan-containment-chain.json").read_text(encoding="utf-8"))
    data["speaker"] = "nora"
    path = tmp_path / "wrong-speaker.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad.png")


def test_johan_renderer_rejects_unknown_family(tmp_path):
    data = json.loads((ROOT / "inputs/johan-order-corridor.json").read_text(encoding="utf-8"))
    data["layout_family"] = "generic_social_card"
    path = tmp_path / "wrong-family.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad.png")


def test_johan_family_rejects_episode_opener_or_closer_roles(tmp_path):
    data = json.loads((ROOT / "inputs/johan-institutional-spine.json").read_text(encoding="utf-8"))
    data["slide_number"] = 1
    path = tmp_path / "wrong-role.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad.png")

    data["slide_number"] = 20
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad2.png")


def test_johan_specialised_layouts_validate_required_structures(tmp_path):
    principle = json.loads((ROOT / "inputs/johan-principle-test.json").read_text(encoding="utf-8"))
    principle["tests"] = principle["tests"][:3]
    bad_principle = tmp_path / "bad-principle.json"
    bad_principle.write_text(json.dumps(principle), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_principle, tmp_path / "bad-principle.png")

    chain = json.loads((ROOT / "inputs/johan-containment-chain.json").read_text(encoding="utf-8"))
    chain["mechanism"] = ["MANDATE", "AUTHORITY"]
    bad_chain = tmp_path / "bad-chain.json"
    bad_chain.write_text(json.dumps(chain), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_chain, tmp_path / "bad-chain.png")


def test_johan_contact_sheet_utility(tmp_path):
    from src.make_contact_sheet import make_contact_sheet

    rendered = []
    for filename in ("johan-containment-chain.json", "johan-principle-test.json"):
        out = tmp_path / filename.replace(".json", ".png")
        render(ROOT / "inputs" / filename, out)
        rendered.append(out)

    sheet = tmp_path / "contact.png"
    make_contact_sheet(rendered, sheet, cols=2, thumb=220)
    with Image.open(sheet) as im:
        assert im.width > 400
        assert im.height > 240
