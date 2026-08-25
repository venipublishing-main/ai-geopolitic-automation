from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from editorial_primitives import PAPER, editorial_atmosphere, draw_small_fact_list, hex_rgb
from render_identity_slide import portrait

THEMES = [
    "nora",
    "johan_vosloo",
    "diane_sterling",
    "kai_patel",
    "thabo_mokoena",
    "amari_ndlovu",
]


def digest(image: Image.Image) -> str:
    return hashlib.sha256(image.tobytes()).hexdigest()


def test_editorial_atmosphere_is_deterministic():
    accent = (23, 105, 170)
    a = Image.new("RGB", (1080, 1080), PAPER)
    b = Image.new("RGB", (1080, 1080), PAPER)
    editorial_atmosphere(a, accent, "nora", variant="feedback_cycle", seed=10)
    editorial_atmosphere(b, accent, "nora", variant="feedback_cycle", seed=10)
    assert digest(a) == digest(b)


def test_all_six_editorial_atmospheres_are_visually_distinct():
    accent = (80, 80, 80)
    hashes = set()
    for idx, theme in enumerate(THEMES, start=1):
        image = Image.new("RGB", (1080, 1080), PAPER)
        editorial_atmosphere(image, accent, theme, variant="benchmark", seed=idx)
        hashes.add(digest(image))
        # The atmosphere must visibly alter more than a token handful of pixels.
        raw = image.tobytes()
        paper = bytes(PAPER)
        changed = sum(raw[i:i+3] != paper for i in range(0, len(raw), 3))
        assert changed > 2500
    assert len(hashes) == len(THEMES)


def test_numbered_fact_ledger_and_portrait_plate_preserve_locked_assets():
    image = Image.new("RGB", (1080, 1080), PAPER)
    draw = ImageDraw.Draw(image)
    draw_small_fact_list(
        draw,
        [
            "One evidence row remains readable.",
            "A second row is visibly numbered.",
            "The ledger treatment stays inside the reserved panel.",
        ],
        (23, 60, 104),
        (100, 500, 530, 820),
        heading="EVIDENCE / TEST",
        minimum=14,
        start=16,
    )

    chars = json.loads((ROOT / "config/characters.json").read_text(encoding="utf-8"))
    speaker = chars["johan_vosloo"]
    asset = ROOT / speaker["portrait"]
    before = hashlib.sha256(asset.read_bytes()).hexdigest()
    portrait(image, ROOT, speaker, (600, 180), (320, 360))
    after = hashlib.sha256(asset.read_bytes()).hexdigest()
    assert before == after

    accent = hex_rgb(speaker["accent"])
    # The printmaker plate extends just beyond the pasted portrait on the right.
    sample = image.crop((920, 190, 930, 525))
    raw = sample.tobytes()
    pixels = [tuple(raw[i:i+3]) for i in range(0, len(raw), 3)]
    assert sum(px != PAPER for px in pixels) > 100
    assert max(max(abs(px[i] - PAPER[i]) for i in range(3)) for px in pixels) >= 6
