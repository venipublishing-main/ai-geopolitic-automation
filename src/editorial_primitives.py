from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W = 1080
H = 1080
SAFE = 76
PAPER = (245, 241, 231)
INK = (24, 26, 28)
MUTED = (75, 73, 68)
BOTTOM_RULE_Y = 966


class LayoutError(RuntimeError):
    pass


def ensure(condition: bool, message: str):
    if not condition:
        raise LayoutError(message)


def font_path(bold: bool = False, serif: bool = False, condensed: bool = False) -> str:
    if serif:
        return "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
    if condensed:
        return "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf"
    return "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(size: int, bold: bool = False, serif: bool = False, condensed: bool = False):
    return ImageFont.truetype(font_path(bold=bold, serif=serif, condensed=condensed), size)


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))


def line_height(draw: ImageDraw.ImageDraw, fnt) -> int:
    b = draw.textbbox((0, 0), "Ag", font=fnt)
    return b[3] - b[1]


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    paragraphs = str(text or "").split("\n")
    out: list[str] = []
    for para in paragraphs:
        words = para.split()
        if not words:
            out.append("")
            continue
        line = words[0]
        for word in words[1:]:
            test = f"{line} {word}"
            box = draw.textbbox((0, 0), test, font=fnt)
            if box[2] - box[0] <= width:
                line = test
            else:
                out.append(line)
                line = word
        out.append(line)
    return out


def fit_wrapped(draw, text: str, width: int, max_lines: int, start: int, minimum: int, **font_kwargs):
    for size in range(start, minimum - 1, -1):
        fnt = font(size, **font_kwargs)
        lines = wrap(draw, text, fnt, width)
        if len(lines) <= max_lines:
            return fnt, lines
    fnt = font(minimum, **font_kwargs)
    return fnt, wrap(draw, text, fnt, width)


def draw_lines(draw, lines: Iterable[str], xy, fnt, fill, spacing=4):
    x, y = xy
    lh = line_height(draw, fnt)
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += lh + spacing
    return y


def paper_texture(img: Image.Image):
    random.seed(20260822)
    px = img.load()
    for _ in range(24000):
        x = random.randrange(W)
        y = random.randrange(H)
        r, g, b = px[x, y]
        d = random.choice((-4, -3, -2, -1, 1, 2, 3))
        px[x, y] = tuple(max(0, min(255, c + d)) for c in (r, g, b))


def distressed_text(img: Image.Image, xy, text: str, fnt, fill, seed=1):
    x, y = xy
    mask = Image.new("L", img.size, 0)
    md = ImageDraw.Draw(mask)
    md.text((x, y), text, font=fnt, fill=255)
    box = md.textbbox((x, y), text, font=fnt)
    random.seed(seed)
    for _ in range(500):
        rx = random.randint(max(int(x), box[0]), max(int(x), box[2]))
        ry = random.randint(max(int(y), box[1]), max(int(y), box[3]))
        if random.random() < 0.75:
            md.ellipse((rx, ry, rx + random.randint(1, 3), ry + random.randint(1, 2)), fill=0)
    colour = Image.new("RGB", img.size, fill)
    img.paste(colour, (0, 0), mask)


def feathered_portrait(path: Path, crop_box, size, fade_bottom: int = 42):
    im = Image.open(path).convert("RGB").crop(tuple(crop_box)).resize(size, Image.Resampling.LANCZOS)
    mask = Image.new("L", size, 255)
    md = ImageDraw.Draw(mask)
    for i in range(fade_bottom):
        alpha = int(255 * i / fade_bottom)
        y = size[1] - fade_bottom + i
        md.rectangle((0, y, size[0], y + 1), fill=255 - alpha)
    return im, mask.filter(ImageFilter.GaussianBlur(6))


def arrow(draw: ImageDraw.ImageDraw, start, end, fill, width=4):
    draw.line((start, end), fill=fill, width=width)
    ang = math.atan2(end[1] - start[1], end[0] - start[0])
    length = 13
    left = (end[0] - length * math.cos(ang - 0.55), end[1] - length * math.sin(ang - 0.55))
    right = (end[0] - length * math.cos(ang + 0.55), end[1] - length * math.sin(ang + 0.55))
    draw.polygon([end, left, right], fill=fill)


def draw_footer(draw: ImageDraw.ImageDraw, accent):
    y = BOTTOM_RULE_Y
    draw.line((SAFE + 18, y, W - SAFE - 18, y), fill=INK, width=2)
    draw.rectangle((SAFE + 18, y + 8, SAFE + 61, y + 42), outline=accent, width=2)
    draw.text((SAFE + 23, y + 8), "AI.", font=font(19, bold=True, serif=True), fill=accent)
    draw.text((SAFE + 72, y + 10), "AI GEOPOLITIC", font=font(18, bold=True, condensed=True), fill=INK)
    draw.text((SAFE + 72, y + 26), "DAILY BRIEFING", font=font(11, bold=True, condensed=True), fill=MUTED)
    footer = "The event is factual. The interpretation ideological."
    ff = font(14, serif=True)
    fb = draw.textbbox((0, 0), footer, font=ff)
    draw.text((W - SAFE - 18 - (fb[2] - fb[0]), y + 18), footer, font=ff, fill=MUTED)


def draw_frame(draw: ImageDraw.ImageDraw, accent, slide_number: int, total_slides: int):
    draw.rectangle((SAFE, SAFE, W - SAFE, H - SAFE), outline=accent, width=3)
    number = f"{slide_number}/{total_slides}"
    nf = font(31, bold=True, serif=True)
    nb = draw.textbbox((0, 0), number, font=nf)
    draw.text((W - SAFE - 14 - (nb[2] - nb[0]), SAFE + 8), number, font=nf, fill=accent)


def draw_headline(img: Image.Image, draw: ImageDraw.ImageDraw, headline: str, accent, xy, width: int, max_lines=4, start=58, minimum=44, accent_first=True):
    fnt, lines = fit_wrapped(draw, headline, width, max_lines, start, minimum, bold=True, condensed=True)
    x, y = xy
    for idx, line in enumerate(lines):
        distressed_text(img, (x, y), line, fnt, accent if (accent_first and idx == 0) else INK, seed=idx + 11)
        y += line_height(draw, fnt) + 1
    return y


def draw_deck(draw, deck: str, xy, width: int, max_lines=4, start=25, minimum=19):
    fnt, lines = fit_wrapped(draw, deck, width, max_lines, start, minimum, serif=True)
    return draw_lines(draw, lines, xy, fnt, INK, spacing=4)


def draw_quote(draw, quote: str, speaker_name: str, accent, box, large=False):
    x0, y0, x1, y1 = box
    draw.line((x0, y0, x1, y0), fill=accent, width=2)
    draw.text((x0, y0 + 10), speaker_name.upper(), font=font(18, bold=True, condensed=True), fill=accent)
    start = 29 if large else 24
    minimum = 20 if large else 17
    qf, qlines = fit_wrapped(draw, quote, x1 - x0 - 52, 4, start, minimum, serif=True)
    draw.text((x0, y0 + 42), "“", font=font(44, bold=True, serif=True), fill=accent)
    draw_lines(draw, qlines, (x0 + 38, y0 + 48), qf, INK, spacing=3)


def draw_takeaway_band(draw, accent, text: str, y=894, label="IDEOLOGICAL LENS / TAKEAWAY"):
    x0, x1 = SAFE + 18, W - SAFE - 18
    draw.rounded_rectangle((x0, y, x1, y + 58), radius=5, outline=accent, width=2)
    draw.text((x0 + 13, y + 7), label, font=font(15, bold=True, condensed=True), fill=accent)
    tf, lines = fit_wrapped(draw, text, 590, 2, 18, 14, serif=True)
    draw_lines(draw, lines, (385, y + 8), tf, INK, spacing=1)


def draw_small_fact_list(draw, facts: Sequence[str], accent, box, heading="KEY FACTS"):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle((x0, y0, x1, y1), radius=7, outline=accent, width=2)
    draw.rectangle((x0, y0, min(x0 + 230, x1), y0 + 34), fill=accent)
    draw.text((x0 + 10, y0 + 4), heading, font=font(16, bold=True, condensed=True), fill=PAPER)
    available = y1 - y0 - 48
    for size in range(16, 12, -1):
        ff = font(size, serif=True)
        rows = [wrap(draw, f, ff, x1 - x0 - 48) for f in facts]
        need = sum(len(r) * (line_height(draw, ff) + 1) + 7 for r in rows)
        if need <= available:
            break
    y = y0 + 46
    for rows in [wrap(draw, f, ff, x1 - x0 - 48) for f in facts]:
        draw.ellipse((x0 + 14, y + 7, x0 + 22, y + 15), fill=accent)
        y = draw_lines(draw, rows, (x0 + 32, y), ff, INK, spacing=1) + 7


def centre_text(draw, text: str, centre, fnt, fill):
    b = draw.textbbox((0, 0), text, font=fnt)
    draw.text((centre[0] - (b[2] - b[0]) / 2, centre[1] - (b[3] - b[1]) / 2), text, font=fnt, fill=fill)
