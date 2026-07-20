from pathlib import Path
import json
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from render_prototype_slide import LayoutError, render


def assert_png(path: Path):
    assert path.exists()
    with Image.open(path) as image:
        assert image.size == (1080, 1080)
        assert image.format == "PNG"


def test_render_nora(tmp_path: Path):
    output = tmp_path / "nora.png"
    render(ROOT / "inputs/prototype-slide.json", output)
    assert_png(output)


def test_render_johan(tmp_path: Path):
    output = tmp_path / "johan.png"
    render(ROOT / "inputs/johan-containment.json", output)
    assert_png(output)


def test_footer_locked():
    brand = json.loads((ROOT / "config/brand.json").read_text(encoding="utf-8"))
    assert brand["footer_line"] == "The event is factual. The interpretation ideological."


def test_invalid_overflow_raises(tmp_path: Path):
    bad_input = tmp_path / "bad.json"
    data = json.loads((ROOT / "inputs/prototype-slide.json").read_text(encoding="utf-8"))
    data["quote"] = " ".join(["Overflow"] * 160)
    bad_input.write_text(json.dumps(data), encoding="utf-8")
    try:
        render(bad_input, tmp_path / "bad.png")
    except LayoutError:
        pass
    else:
        raise AssertionError("Expected LayoutError when content overflows.")
