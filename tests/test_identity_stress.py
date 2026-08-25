import json
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.editorial_primitives import LayoutError
from src.render_identity_slide import render
from src.render_identity_stress_pack import IDENTITY_INPUTS, build_profile_data


def _base_data(speaker_key: str) -> dict:
    return json.loads((ROOT / "inputs" / IDENTITY_INPUTS[speaker_key]).read_text(encoding="utf-8"))


def _render_data(tmp_path: Path, speaker_key: str, label: str, data: dict) -> Path:
    source = tmp_path / f"{speaker_key}-{label}.json"
    output = tmp_path / f"{speaker_key}-{label}.png"
    source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    render(source, output)
    return output


@pytest.mark.parametrize("speaker_key", list(IDENTITY_INPUTS))
@pytest.mark.parametrize("profile", ["short", "dense"])
def test_short_and_dense_profiles_render_cleanly(tmp_path, speaker_key, profile):
    data = build_profile_data(_base_data(speaker_key), speaker_key, profile)
    output = _render_data(tmp_path, speaker_key, profile, data)
    with Image.open(output) as im:
        assert im.size == (1080, 1080)
        assert im.mode == "RGB"


@pytest.mark.parametrize("speaker_key", list(IDENTITY_INPUTS))
def test_dense_profile_is_not_lighter_than_normal_copy(speaker_key):
    base = _base_data(speaker_key)
    dense = build_profile_data(base, speaker_key, "dense")

    def copy_load(data):
        return (
            len(data["headline"])
            + len(data["deck"])
            + len(data["quote"])
            + sum(len(item) for item in data["facts"])
            + len(data["takeaway"])
        )

    assert copy_load(dense) > copy_load(base)


OVERFLOW_CASES = {
    "nora": ("headline", "SYSTEM " * 50),
    "johan_vosloo": (
        "deck",
        "Institutional responsibility must remain visible, bounded and accountable across every handoff. " * 16,
    ),
    "diane_sterling": (
        "facts",
        [
            "This deliberately excessive economic evidence line keeps adding detail until the protected evidence panel cannot remain readable. " * 5
        ] * 4,
    ),
    "kai_patel": (
        "quote",
        "A resilient network must sense failure, route around it, learn from it and repair itself without hiding the feedback path. " * 14,
    ),
    "thabo_mokoena": (
        "facts",
        [
            "This deliberately overlong material burden statement must fail rather than cover the portrait, burden ledger or takeaway region. " * 4
        ] * 4,
    ),
    "amari_ndlovu": (
        "takeaway",
        "Dignity must remain visible through place, history, recognition, delivery and repeated institutional encounters. " * 14,
    ),
}


@pytest.mark.parametrize("speaker_key", list(IDENTITY_INPUTS))
def test_impossible_copy_fails_cleanly(tmp_path, speaker_key):
    data = _base_data(speaker_key)
    field, value = OVERFLOW_CASES[speaker_key]
    data[field] = value
    source = tmp_path / f"{speaker_key}-overflow.json"
    source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(LayoutError):
        render(source, tmp_path / f"{speaker_key}-overflow.png")
