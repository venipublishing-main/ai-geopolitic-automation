import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.render_identity_slide import render


def test_identity_proof_pack_renders_all_six(tmp_path):
    inputs = [
        "identity-nora.json",
        "identity-johan.json",
        "identity-diane.json",
        "identity-kai.json",
        "identity-thabo.json",
        "identity-amari.json",
    ]
    for name in inputs:
        out = tmp_path / name.replace(".json", ".png")
        render(ROOT / "inputs" / name, out)
        with Image.open(out) as im:
            assert im.size == (1080, 1080)
            assert im.mode == "RGB"


def test_identity_presets_cover_all_characters():
    presets = json.loads((ROOT / "config" / "layout_presets.json").read_text(encoding="utf-8"))
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
