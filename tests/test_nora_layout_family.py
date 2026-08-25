import json
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.editorial_primitives import LayoutError
from src.render_nora_layout_family import FAMILIES, render


SAMPLES = {
    "system_axis": "nora-system-axis.json",
    "feedback_loop": "nora-feedback-loop.json",
    "diagnostic_matrix": "nora-diagnostic-matrix.json",
    "episode_opener": "nora-episode-opener.json",
    "episode_closer": "nora-episode-closer.json",
}


def test_nora_family_matches_approved_presets():
    presets = json.loads((ROOT / "config/layout_presets.json").read_text(encoding="utf-8"))
    assert set(presets["nora"]["approved_families"]) == FAMILIES


def test_all_five_nora_families_render(tmp_path):
    for family, filename in SAMPLES.items():
        out = tmp_path / f"{family}.png"
        render(ROOT / "inputs" / filename, out)
        with Image.open(out) as im:
            assert im.size == (1080, 1080)
            assert im.mode == "RGB"


def test_nora_renderer_rejects_wrong_speaker(tmp_path):
    data = json.loads((ROOT / "inputs/nora-feedback-loop.json").read_text(encoding="utf-8"))
    data["speaker"] = "johan_vosloo"
    path = tmp_path / "wrong-speaker.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad.png")


def test_nora_renderer_rejects_unknown_family(tmp_path):
    data = json.loads((ROOT / "inputs/nora-feedback-loop.json").read_text(encoding="utf-8"))
    data["layout_family"] = "generic_social_card"
    path = tmp_path / "wrong-family.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad.png")


def test_opener_and_closer_enforce_slide_roles(tmp_path):
    opener = json.loads((ROOT / "inputs/nora-episode-opener.json").read_text(encoding="utf-8"))
    opener["slide_number"] = 2
    opener_path = tmp_path / "bad-opener.json"
    opener_path.write_text(json.dumps(opener), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(opener_path, tmp_path / "bad-opener.png")

    closer = json.loads((ROOT / "inputs/nora-episode-closer.json").read_text(encoding="utf-8"))
    closer["slide_number"] = 19
    closer_path = tmp_path / "bad-closer.json"
    closer_path.write_text(json.dumps(closer), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(closer_path, tmp_path / "bad-closer.png")


def test_contact_sheet_utility(tmp_path):
    from src.make_contact_sheet import make_contact_sheet
    rendered = []
    for filename in ("nora-feedback-loop.json", "nora-diagnostic-matrix.json"):
        out = tmp_path / filename.replace(".json", ".png")
        render(ROOT / "inputs" / filename, out)
        rendered.append(out)
    sheet = tmp_path / "contact.png"
    make_contact_sheet(rendered, sheet, cols=2, thumb=220)
    with Image.open(sheet) as im:
        assert im.width > 400
        assert im.height > 240
