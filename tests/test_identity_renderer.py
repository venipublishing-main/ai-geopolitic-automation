import json
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.editorial_primitives import LayoutError
from src.render_identity_slide import render


IDENTITY_INPUTS = [
    "identity-nora.json",
    "identity-johan.json",
    "identity-diane.json",
    "identity-kai.json",
    "identity-thabo.json",
    "identity-amari.json",
]


def test_identity_proof_pack_renders_all_six(tmp_path):
    for name in IDENTITY_INPUTS:
        out = tmp_path / name.replace(".json", ".png")
        render(ROOT / "inputs" / name, out)
        with Image.open(out) as im:
            assert im.size == (1080, 1080)
            assert im.mode == "RGB"


def test_identity_presets_cover_all_characters():
    presets_path = ROOT / "config" / "layout_presets.json"
    if not presets_path.exists():
        pytest.skip("layout_presets.json is not present in this local fixture")
    presets = json.loads(presets_path.read_text(encoding="utf-8"))
    assert set(presets) == {
        "nora",
        "johan_vosloo",
        "diane_sterling",
        "kai_patel",
        "thabo_mokoena",
        "amari_ndlovu",
    }
    grammars = {v["identity_grammar"] for v in presets.values()}
    assert len(grammars) == 6


def test_all_portrait_crops_are_valid():
    characters = json.loads((ROOT / "config" / "characters.json").read_text(encoding="utf-8"))
    assert set(characters) == {
        "nora", "johan_vosloo", "diane_sterling", "kai_patel", "thabo_mokoena", "amari_ndlovu"
    }
    for key, character in characters.items():
        portrait_path = ROOT / character["portrait"]
        assert portrait_path.exists(), f"missing portrait for {key}"
        crop = character.get("crop_box")
        assert isinstance(crop, list) and len(crop) == 4, f"missing crop_box for {key}"
        with Image.open(portrait_path) as im:
            left, top, right, bottom = crop
            assert 0 <= left < right <= im.width
            assert 0 <= top < bottom <= im.height


def test_overlong_johan_deck_fails_instead_of_colliding(tmp_path):
    data = json.loads((ROOT / "inputs" / "identity-johan.json").read_text(encoding="utf-8"))
    data["deck"] = " ".join(["Institutional responsibility must remain visible and accountable."] * 18)
    bad_input = tmp_path / "johan-overflow.json"
    bad_input.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_input, tmp_path / "bad.png")


def test_overlong_thabo_facts_fail_instead_of_covering_portrait(tmp_path):
    data = json.loads((ROOT / "inputs" / "identity-thabo.json").read_text(encoding="utf-8"))
    data["facts"] = [
        "This deliberately overlong material burden statement should not be silently squeezed over the portrait or takeaway region."
    ] * 4
    bad_input = tmp_path / "thabo-overflow.json"
    bad_input.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_input, tmp_path / "bad-thabo.png")
