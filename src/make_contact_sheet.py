from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def make_contact_sheet(paths: list[Path], output: Path, *, cols: int = 3, thumb: int = 360, label_height: int = 34):
    if not paths:
        raise ValueError("No images supplied for contact sheet.")
    cols = max(1, int(cols))
    rows = (len(paths) + cols - 1) // cols
    cell_w = thumb + 24
    cell_h = thumb + label_height + 24
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    draw = ImageDraw.Draw(sheet)

    for idx, path in enumerate(paths):
        if not path.exists():
            raise FileNotFoundError(path)
        with Image.open(path) as source:
            im = source.convert("RGB")
        im.thumbnail((thumb, thumb), Image.Resampling.LANCZOS)
        row, col = divmod(idx, cols)
        x0 = col * cell_w + (cell_w - im.width) // 2
        y0 = row * cell_h + 10
        sheet.paste(im, (x0, y0))
        draw.text((col * cell_w + 12, row * cell_h + thumb + 16), path.stem, fill="black")

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, "PNG", optimize=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--glob", dest="pattern", help="Glob such as output/nora-*.png")
    group.add_argument("--files", nargs="+", help="Explicit image paths in contact-sheet order")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cols", type=int, default=3)
    parser.add_argument("--thumb", type=int, default=360)
    args = parser.parse_args()

    if args.files:
        paths = [Path(value) for value in args.files]
    else:
        paths = sorted(Path(".").glob(args.pattern))
    make_contact_sheet(paths, args.output, cols=args.cols, thumb=args.thumb)
    print(f"Generated {args.output.resolve()} from {len(paths)} images")
