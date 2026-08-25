import json
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.editorial_primitives import LayoutError
from src.render_amari_layout_family import FAMILIES, render


SAMPLES = {
    "regional_memory": "amari-regional-memory.json",
    "dignity_pathway": "amari-dignity-pathway.json",
    "humanitarian_map": "amari-humanitarian-map.json",
    "cross_border_bridge": "amari-cross-border-bridge.json",
    "cultural_landscape": "amari-cultural-landscape.json",
}


def test_amari_family_matches_approved_presets():
    presets = json.loads((ROOT / "config/layout_presets.json").read_text(encoding="utf-8"))
    assert set(presets["amari_ndlovu"]["approved_families"]) == FAMILIES


def test_all_five_amari_families_render(tmp_path):
    for family, filename in SAMPLES.items():
        out = tmp_path / f"{family}.png"
        render(ROOT / "inputs" / filename, out)
        with Image.open(out) as im:
            assert im.size == (1080, 1080)
            assert im.mode == "RGB"


def test_amari_renderer_rejects_wrong_speaker(tmp_path):
    data = json.loads((ROOT / "inputs/amari-dignity-pathway.json").read_text(encoding="utf-8"))
    data["speaker"] = "nora"
    path = tmp_path / "wrong-speaker.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad.png")


def test_amari_renderer_rejects_unknown_family(tmp_path):
    data = json.loads((ROOT / "inputs/amari-humanitarian-map.json").read_text(encoding="utf-8"))
    data["layout_family"] = "generic_social_card"
    path = tmp_path / "wrong-family.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad.png")


def test_amari_family_rejects_episode_opener_or_closer_roles(tmp_path):
    data = json.loads((ROOT / "inputs/amari-regional-memory.json").read_text(encoding="utf-8"))
    data["slide_number"] = 1
    path = tmp_path / "wrong-role.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad.png")

    data["slide_number"] = 20
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad2.png")


def test_amari_specialised_layouts_validate_required_structures(tmp_path):
    pathway = json.loads((ROOT / "inputs/amari-dignity-pathway.json").read_text(encoding="utf-8"))
    pathway["mechanism"] = pathway["mechanism"][:3]
    bad_pathway = tmp_path / "bad-pathway.json"
    bad_pathway.write_text(json.dumps(pathway), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_pathway, tmp_path / "bad-pathway.png")

    amap = json.loads((ROOT / "inputs/amari-humanitarian-map.json").read_text(encoding="utf-8"))
    amap["map_nodes"] = amap["map_nodes"][:3]
    bad_map = tmp_path / "bad-map.json"
    bad_map.write_text(json.dumps(amap), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_map, tmp_path / "bad-map.png")

    bridge = json.loads((ROOT / "inputs/amari-cross-border-bridge.json").read_text(encoding="utf-8"))
    bridge["bridge"] = bridge["bridge"][:3]
    bad_bridge = tmp_path / "bad-bridge.json"
    bad_bridge.write_text(json.dumps(bridge), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_bridge, tmp_path / "bad-bridge.png")

    landscape = json.loads((ROOT / "inputs/amari-cultural-landscape.json").read_text(encoding="utf-8"))
    landscape["landscape"] = landscape["landscape"][:3]
    bad_landscape = tmp_path / "bad-landscape.json"
    bad_landscape.write_text(json.dumps(landscape), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_landscape, tmp_path / "bad-landscape.png")


def test_amari_contact_sheet_utility(tmp_path):
    from src.make_contact_sheet import make_contact_sheet

    rendered = []
    for filename in ("amari-dignity-pathway.json", "amari-humanitarian-map.json"):
        out = tmp_path / filename.replace(".json", ".png")
        render(ROOT / "inputs" / filename, out)
        rendered.append(out)

    sheet = tmp_path / "contact.png"
    make_contact_sheet(rendered, sheet, cols=2, thumb=220)
    with Image.open(sheet) as im:
        assert im.width > 400
        assert im.height > 240
