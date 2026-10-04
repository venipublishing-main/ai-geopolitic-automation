"""Shared natural type measurement for D.1 compile and render; no glyph resizing."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .editorial_primitives import font, wrap
from .scene_contract import TextPlan

DISPLAY_FONT = Path(__file__).resolve().parents[1] / "assets/fonts/anton/Anton-Regular.ttf"


def typeface(kind, size):
    return ImageFont.truetype(str(DISPLAY_FONT), size) if kind == "display" else font(
        size, serif=kind == "serif", bold=kind == "label", condensed=kind == "label")


def fit_text(text, zone, treatment, *, kind="serif", start=26, minimum=17, parent=(0, 0, 1080, 1080)):
    box = zone.pixels(parent)
    width, height = box[2] - box[0] - 12, box[3] - box[1] - 8
    draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    for size in range(start, minimum - 1, -1):
        face = typeface(kind, size)
        lines = tuple(wrap(draw, text, face, width))
        bounds = [draw.textbbox((0, 0), line or " ", font=face) for line in lines]
        step = max(b[3] - b[1] for b in bounds) + 4
        if (all(b[2] - b[0] <= width for b in bounds) and
                len(lines) * step - 4 <= height):
            return TextPlan(text, zone, treatment, kind, size, lines, step)
    raise ValueError("COPY_OVERFLOW" if treatment != "annotation" else "LABEL_OVERFLOW")


def draw_text(draw, plan, colour, *, parent=(0, 0, 1080, 1080)):
    x, y, _, _ = plan.zone.pixels(parent)
    face = typeface(plan.font_kind, plan.font_size)
    for line in plan.lines:
        b = draw.textbbox((0, 0), line or " ", font=face)
        draw.text((x + 6 - b[0], y + 4 - b[1]), line, font=face, fill=colour)
        y += plan.line_step
