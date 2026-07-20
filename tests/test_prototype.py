from pathlib import Path
import json
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from render_prototype_slide import render


def test_render(tmp_path: Path):
    output = tmp_path / "prototype.png"
    render(ROOT / "inputs/prototype-slide.json", output)
    assert output.exists()
    with Image.open(output) as image:
        assert image.size == (1080, 1080)
        assert image.format == "PNG"


def test_footer_locked():
    brand = json.loads((ROOT / "config/brand.json").read_text(encoding="utf-8"))
    assert brand["footer_line"] == "The event is factual. The interpretation ideological."
