import json
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.editorial_primitives import LayoutError
from src.render_diane_layout_family import FAMILIES, render


SAMPLES = {
    "market_grid": "diane-market-grid.json",
    "transmission_chain": "diane-transmission-chain.json",
    "fiscal_flow": "diane-fiscal-flow.json",
    "portfolio_pipeline": "diane-portfolio-pipeline.json",
    "regional_economy": "diane-regional-economy.json",
}


def test_diane_family_matches_approved_presets():
    presets = json.loads((ROOT / "config/layout_presets.json").read_text(encoding="utf-8"))
    assert set(presets["diane_sterling"]["approved_families"]) == FAMILIES


def test_all_five_diane_families_render(tmp_path):
    for family, filename in SAMPLES.items():
        out = tmp_path / f"{family}.png"
        render(ROOT / "inputs" / filename, out)
        with Image.open(out) as im:
            assert im.size == (1080, 1080)
            assert im.mode == "RGB"


def test_diane_renderer_rejects_wrong_speaker(tmp_path):
    data = json.loads((ROOT / "inputs/diane-transmission-chain.json").read_text(encoding="utf-8"))
    data["speaker"] = "nora"
    path = tmp_path / "wrong-speaker.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad.png")


def test_diane_renderer_rejects_unknown_family(tmp_path):
    data = json.loads((ROOT / "inputs/diane-fiscal-flow.json").read_text(encoding="utf-8"))
    data["layout_family"] = "generic_social_card"
    path = tmp_path / "wrong-family.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad.png")


def test_diane_family_rejects_episode_opener_or_closer_roles(tmp_path):
    data = json.loads((ROOT / "inputs/diane-market-grid.json").read_text(encoding="utf-8"))
    data["slide_number"] = 1
    path = tmp_path / "wrong-role.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad.png")

    data["slide_number"] = 20
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(path, tmp_path / "bad2.png")


def test_diane_specialised_layouts_validate_required_structures(tmp_path):
    flow = json.loads((ROOT / "inputs/diane-fiscal-flow.json").read_text(encoding="utf-8"))
    flow["flows"] = flow["flows"][:3]
    bad_flow = tmp_path / "bad-flow.json"
    bad_flow.write_text(json.dumps(flow), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_flow, tmp_path / "bad-flow.png")

    portfolio = json.loads((ROOT / "inputs/diane-portfolio-pipeline.json").read_text(encoding="utf-8"))
    portfolio["portfolio"] = portfolio["portfolio"][:3]
    bad_portfolio = tmp_path / "bad-portfolio.json"
    bad_portfolio.write_text(json.dumps(portfolio), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_portfolio, tmp_path / "bad-portfolio.png")

    regions = json.loads((ROOT / "inputs/diane-regional-economy.json").read_text(encoding="utf-8"))
    regions["regions"] = regions["regions"][:3]
    bad_regions = tmp_path / "bad-regions.json"
    bad_regions.write_text(json.dumps(regions), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(bad_regions, tmp_path / "bad-regions.png")


def test_diane_contact_sheet_utility(tmp_path):
    from src.make_contact_sheet import make_contact_sheet

    rendered = []
    for filename in ("diane-transmission-chain.json", "diane-regional-economy.json"):
        out = tmp_path / filename.replace(".json", ".png")
        render(ROOT / "inputs" / filename, out)
        rendered.append(out)

    sheet = tmp_path / "contact.png"
    make_contact_sheet(rendered, sheet, cols=2, thumb=220)
    with Image.open(sheet) as im:
        assert im.width > 400
        assert im.height > 240
