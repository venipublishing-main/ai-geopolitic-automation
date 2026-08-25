import json
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.editorial_primitives import LayoutError
from src.render_thabo_layout_family import FAMILIES, render


SAMPLES = {
    "burden_ledger": "thabo-burden-ledger.json",
    "material_chain": "thabo-material-chain.json",
    "structural_gap": "thabo-structural-gap.json",
    "continuity_pressure": "thabo-continuity-pressure.json",
}


def test_thabo_family_matches_approved_presets():
    presets = json.loads((ROOT / "config/layout_presets.json").read_text(encoding="utf-8"))
    assert set(presets["thabo_mokoena"]["approved_families"]) == FAMILIES


def test_all_four_thabo_families_render(tmp_path):
    for family, filename in SAMPLES.items():
        out = tmp_path / f"{family}.png"
        render(ROOT / "inputs" / filename, out)
        with Image.open(out) as im:
            assert im.size == (1080, 1080)
            assert im.mode == "RGB"


def test_thabo_renderer_rejects_wrong_speaker(tmp_path):
    data = json.loads((ROOT / "inputs/thabo-material-chain.json").read_text(encoding="utf-8"))
    data["speaker"] = "nora"
    path = tmp_path / "wrong-speaker.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad.png")


def test_thabo_renderer_rejects_unknown_family(tmp_path):
    data = json.loads((ROOT / "inputs/thabo-structural-gap.json").read_text(encoding="utf-8"))
    data["layout_family"] = "generic_social_card"
    path = tmp_path / "wrong-family.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad.png")


def test_thabo_family_rejects_episode_opener_or_closer_roles(tmp_path):
    data = json.loads((ROOT / "inputs/thabo-burden-ledger.json").read_text(encoding="utf-8"))
    data["slide_number"] = 1
    path = tmp_path / "wrong-role.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad.png")

    data["slide_number"] = 20
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad2.png")


def test_thabo_specialised_layouts_validate_required_structures(tmp_path):
    chain = json.loads((ROOT / "inputs/thabo-material-chain.json").read_text(encoding="utf-8"))
    chain["chain"] = chain["chain"][:4]
    bad_chain = tmp_path / "bad-chain.json"
    bad_chain.write_text(json.dumps(chain), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_chain, tmp_path / "bad-chain.png")

    gaps = json.loads((ROOT / "inputs/thabo-structural-gap.json").read_text(encoding="utf-8"))
    gaps["gaps"] = gaps["gaps"][:2]
    bad_gaps = tmp_path / "bad-gaps.json"
    bad_gaps.write_text(json.dumps(gaps), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_gaps, tmp_path / "bad-gaps.png")

    pressure = json.loads((ROOT / "inputs/thabo-continuity-pressure.json").read_text(encoding="utf-8"))
    pressure["pressure_steps"] = pressure["pressure_steps"][:3]
    bad_pressure = tmp_path / "bad-pressure.json"
    bad_pressure.write_text(json.dumps(pressure), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_pressure, tmp_path / "bad-pressure.png")


def test_thabo_contact_sheet_utility(tmp_path):
    from src.make_contact_sheet import make_contact_sheet

    rendered = []
    for filename in ("thabo-material-chain.json", "thabo-structural-gap.json"):
        out = tmp_path / filename.replace(".json", ".png")
        render(ROOT / "inputs" / filename, out)
        rendered.append(out)

    sheet = tmp_path / "contact.png"
    make_contact_sheet(rendered, sheet, cols=2, thumb=220)
    with Image.open(sheet) as im:
        assert im.width > 400
        assert im.height > 240
