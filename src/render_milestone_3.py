"""Render the two Milestone 3 test slides.

This script deliberately reuses the proven Milestone 2 rendering engine.
Character portraits, names and accent colours are loaded through
config/characters.json by render_prototype_slide.py.
"""

from __future__ import annotations

from pathlib import Path

from render_prototype_slide import render


ROOT = Path(__file__).resolve().parents[1]

JOBS = (
    (
        ROOT / "inputs" / "test_nora_slide.json",
        ROOT / "output" / "test_nora_slide.png",
    ),
    (
        ROOT / "inputs" / "test_johan_slide.json",
        ROOT / "output" / "test_johan_slide.png",
    ),
)


def main() -> None:
    for input_path, output_path in JOBS:
        if not input_path.exists():
            raise FileNotFoundError(f"Missing input file: {input_path}")

        render(input_path, output_path)
        print(f"Generated {output_path}")


if __name__ == "__main__":
    main()
