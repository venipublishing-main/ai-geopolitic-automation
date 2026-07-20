from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw, ImageFont, ImageFilter


W = 1080
H = 1080
SAFE = 76
PAPER = (245, 241, 231)
INK = (24, 26, 28)
MUTED = (75, 73, 68)

LEFT = SAFE + 20
RIGHT = W - SAFE - 20
CONTENT_TOP = SAFE + 22
BOTTOM_RULE_Y = 966
TAKE_Y = 892


class LayoutError(RuntimeError):
    pass


DEFAULT_PORTRAIT_CROPS = {
    "nora": (220, 10, 1005, 900),
    "johan_vosloo": (220, 10, 1005, 900),
    "diane_sterling": (220, 10, 1005, 900),
    "kai_patel": (220, 10, 1005, 900),
    "thabo_mokoena": (220, 10, 1005, 900),
    "amari_ndlovu": (220, 10, 1005, 900),
}


ICON_ALIASES = {
    "PROMISE": "document",
    "IMPLEMENTATION": "gear",
    "MONITORING": "monitor",
    "CORRECTION": "wrench",
    "DELIVERY": "truck",
    "TRUST": "trust",
    "CONTROLLED AREA": "shield",
    "DETECTION": "alert",
    "CONTAINMENT": "shield",
    "DISCLOSURE": "document",
    "PUBLIC TRUST": "trust",
    "LAB CONFIRMATION": "lab",
    "TREATMENT": "care",
    "PUBLIC COMMUNICATION": "megaphone",
    "LOGISTICS": "truck",
    "SAFETY": "shield",
}


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
    if not text:
        return []
    paragraphs = str(text).split("\n")
    all_lines: list[str] = []
    for para in paragraphs:
        words = para.split()
        if not words:
            all_lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            test = current + " " + word
            box = draw.textbbox((0, 0), test, font=fnt)
            if box[2] - box[0] <= width:
                current = test
            else:
                all_lines.append(current)
                current = word
        all_lines.append(current)
    return all_lines


def fit_wrapped(draw, text: str, width: int, max_lines: int, start: int, minimum: int, **font_kwargs):
    for size in range(start, minimum - 1, -1):
        fnt = font(size, **font_kwargs)
        lines = wrap(draw, text, fnt, width)
        if len(lines) <= max_lines:
            return fnt, lines
    fnt = font(minimum, **font_kwargs)
    return fnt, wrap(draw, text, fnt, width)


def block_height(draw, lines: Sequence[str], fnt, spacing=0) -> int:
    if not lines:
        return 0
    return len(lines) * line_height(draw, fnt) + max(0, len(lines) - 1) * spacing


def draw_lines(draw, lines: Iterable[str], xy, fnt, fill, spacing=6):
    x, y = xy
    lh = line_height(draw, fnt)
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += lh + spacing
    return y


def paper_texture(img: Image.Image):
    random.seed(20260720)
    px = img.load()
    for _ in range(24000):
        x = random.randrange(W)
        y = random.randrange(H)
        r, g, b = px[x, y]
        d = random.choice((-4, -3, -2, -1, 1, 2, 3))
        px[x, y] = (max(0, min(255, r + d)), max(0, min(255, g + d)), max(0, min(255, b + d)))


def distressed_text(img: Image.Image, xy, text: str, fnt, fill, seed=1):
    x, y = xy
    mask = Image.new("L", img.size, 0)
    md = ImageDraw.Draw(mask)
    md.text((x, y), text, font=fnt, fill=255)
    box = md.textbbox((x, y), text, font=fnt)
    random.seed(seed)
    for _ in range(550):
        rx = random.randint(max(int(x), box[0]), max(int(x), box[2]))
        ry = random.randint(max(int(y), box[1]), max(int(y), box[3]))
        if random.random() < 0.75:
            md.ellipse((rx, ry, rx + random.randint(1, 3), ry + random.randint(1, 2)), fill=0)
    colour = Image.new("RGB", img.size, fill)
    img.paste(colour, (0, 0), mask)


def feathered_portrait(path: Path, crop_box, size):
    im = Image.open(path).convert("RGB").crop(crop_box).resize(size, Image.Resampling.LANCZOS)
    mask = Image.new("L", size, 255)
    md = ImageDraw.Draw(mask)
    fade = 44
    for i in range(fade):
        alpha = int(255 * i / fade)
        md.rectangle((0, size[1] - fade + i, size[0], size[1] - fade + i + 1), fill=255 - alpha)
    mask = mask.filter(ImageFilter.GaussianBlur(7))
    return im, mask


def arrow(draw: ImageDraw.ImageDraw, start, end, fill, width=4):
    draw.line((start, end), fill=fill, width=width)
    ang = math.atan2(end[1] - start[1], end[0] - start[0])
    length = 14
    left = (end[0] - length * math.cos(ang - 0.55), end[1] - length * math.sin(ang - 0.55))
    right = (end[0] - length * math.cos(ang + 0.55), end[1] - length * math.sin(ang + 0.55))
    draw.polygon([end, left, right], fill=fill)


def draw_icon(draw: ImageDraw.ImageDraw, centre, kind: str, colour, scale=1.0, width=3):
    cx, cy = centre
    s = scale
    kind = ICON_ALIASES.get(kind.upper(), kind).lower()

    if kind == "document":
        draw.rounded_rectangle((cx - 10 * s, cy - 13 * s, cx + 10 * s, cy + 13 * s), radius=2, outline=colour, width=width)
        draw.line((cx - 5 * s, cy - 4 * s, cx + 5 * s, cy - 4 * s), fill=colour, width=width)
        draw.line((cx - 5 * s, cy + 2 * s, cx + 5 * s, cy + 2 * s), fill=colour, width=width)
    elif kind == "gear":
        draw.ellipse((cx - 10 * s, cy - 10 * s, cx + 10 * s, cy + 10 * s), outline=colour, width=width)
        draw.ellipse((cx - 4 * s, cy - 4 * s, cx + 4 * s, cy + 4 * s), outline=colour, width=width)
        for ang in [0, 60, 120]:
            rad = math.radians(ang)
            dx = math.cos(rad) * 13 * s
            dy = math.sin(rad) * 13 * s
            draw.line((cx - dx, cy - dy, cx + dx, cy + dy), fill=colour, width=width)
    elif kind == "monitor":
        draw.rectangle((cx - 11 * s, cy - 9 * s, cx + 11 * s, cy + 7 * s), outline=colour, width=width)
        draw.line((cx - 6 * s, cy + 10 * s, cx + 6 * s, cy + 10 * s), fill=colour, width=width)
        draw.line((cx, cy + 7 * s, cx, cy + 11 * s), fill=colour, width=width)
    elif kind == "wrench":
        draw.line((cx - 10 * s, cy + 8 * s, cx + 9 * s, cy - 11 * s), fill=colour, width=width)
        draw.arc((cx + 2 * s, cy - 17 * s, cx + 17 * s, cy - 2 * s), 45, 320, fill=colour, width=width)
    elif kind == "truck":
        draw.rectangle((cx - 15 * s, cy - 6 * s, cx + 3 * s, cy + 8 * s), outline=colour, width=width)
        draw.rectangle((cx + 3 * s, cy - 2 * s, cx + 15 * s, cy + 8 * s), outline=colour, width=width)
        draw.ellipse((cx - 9 * s, cy + 7 * s, cx - 3 * s, cy + 13 * s), outline=colour, width=width)
        draw.ellipse((cx + 6 * s, cy + 7 * s, cx + 12 * s, cy + 13 * s), outline=colour, width=width)
    elif kind == "shield":
        pts = [(cx, cy - 14 * s), (cx + 12 * s, cy - 6 * s), (cx + 9 * s, cy + 10 * s), (cx, cy + 15 * s), (cx - 9 * s, cy + 10 * s), (cx - 12 * s, cy - 6 * s)]
        draw.polygon(pts, outline=colour, fill=None)
    elif kind == "alert":
        draw.polygon([(cx, cy - 13 * s), (cx + 12 * s, cy + 10 * s), (cx - 12 * s, cy + 10 * s)], outline=colour, fill=None)
        draw.line((cx, cy - 5 * s, cx, cy + 3 * s), fill=colour, width=width)
        draw.ellipse((cx - 1.5 * s, cy + 6 * s, cx + 1.5 * s, cy + 9 * s), fill=colour)
    elif kind == "lab":
        draw.polygon([(cx - 8 * s, cy - 12 * s), (cx + 8 * s, cy - 12 * s), (cx + 4 * s, cy - 2 * s), (cx + 11 * s, cy + 12 * s), (cx - 11 * s, cy + 12 * s), (cx - 4 * s, cy - 2 * s)], outline=colour, fill=None)
    elif kind == "care":
        draw.rectangle((cx - 12 * s, cy - 12 * s, cx + 12 * s, cy + 12 * s), outline=colour, width=width)
        draw.line((cx - 7 * s, cy, cx + 7 * s, cy), fill=colour, width=width)
        draw.line((cx, cy - 7 * s, cx, cy + 7 * s), fill=colour, width=width)
    elif kind == "megaphone":
        draw.polygon([(cx - 10 * s, cy - 6 * s), (cx + 4 * s, cy - 12 * s), (cx + 4 * s, cy + 12 * s), (cx - 10 * s, cy + 6 * s)], outline=colour, fill=None)
        draw.line((cx - 10 * s, cy + 4 * s, cx - 14 * s, cy + 10 * s), fill=colour, width=width)
    elif kind == "trust":
        draw.ellipse((cx - 8 * s, cy - 10 * s, cx, cy - 2 * s), fill=colour)
        draw.ellipse((cx, cy - 10 * s, cx + 8 * s, cy - 2 * s), fill=colour)
        draw.polygon([(cx - 9 * s, cy - 5 * s), (cx + 9 * s, cy - 5 * s), (cx, cy + 10 * s)], fill=colour)
    else:
        draw.ellipse((cx - 7 * s, cy - 7 * s, cx + 7 * s, cy + 7 * s), fill=colour)


def ensure(condition: bool, message: str):
    if not condition:
        raise LayoutError(message)


def measure_facts(draw, facts: Sequence[str], width: int, start_size=16, min_size=13, spacing=4):
    best = None
    for size in range(start_size, min_size - 1, -1):
        fnt = font(size, serif=True)
        items = [wrap(draw, item, fnt, width - 48) for item in facts]
        total = 0
        for lines in items:
            total += block_height(draw, lines, fnt, spacing=1) + 8
        best = (fnt, items, total)
        if total <= 185:
            return best
    return best


def draw_footer(draw: ImageDraw.ImageDraw, accent):
    footer_rule_y = BOTTOM_RULE_Y
    draw.line((SAFE + 18, footer_rule_y, W - SAFE - 18, footer_rule_y), fill=INK, width=2)
    draw.rectangle((SAFE + 18, footer_rule_y + 8, SAFE + 61, footer_rule_y + 42), outline=accent, width=2)
    draw.text((SAFE + 23, footer_rule_y + 8), "AI.", font=font(19, bold=True, serif=True), fill=accent)
    draw.text((SAFE + 72, footer_rule_y + 10), "AI GEOPOLITIC", font=font(18, bold=True, condensed=True), fill=INK)
    draw.text((SAFE + 72, footer_rule_y + 26), "DAILY BRIEFING", font=font(11, bold=True, condensed=True), fill=MUTED)
    footer = "The event is factual. The interpretation ideological."
    ff = font(14, serif=True)
    fb = draw.textbbox((0, 0), footer, font=ff)
    draw.text((W - SAFE - 18 - (fb[2] - fb[0]), footer_rule_y + 18), footer, font=ff, fill=MUTED)


def draw_takeaway(draw: ImageDraw.ImageDraw, accent, text: str):
    draw.rounded_rectangle((SAFE + 18, TAKE_Y, W - SAFE - 18, 952), radius=6, outline=accent, width=2)
    draw.text((SAFE + 32, TAKE_Y + 8), "IDEOLOGICAL LENS / TAKEAWAY", font=font(16, bold=True, condensed=True), fill=accent)
    tf, tlines = fit_wrapped(draw, text, 560, 2, 19, 15, serif=True)
    draw_lines(draw, tlines, (380, TAKE_Y + 9), tf, INK, spacing=1)


def draw_loop_diagram(draw: ImageDraw.ImageDraw, accent, diagram: dict):
    cx, cy = 760, 705
    centre_r = 72
    draw.ellipse((cx - centre_r, cy - centre_r, cx + centre_r, cy + centre_r), outline=accent, width=4)
    centre_font = font(28, bold=True, condensed=True)
    centre = diagram["centre"]
    cb = draw.textbbox((0, 0), centre, font=centre_font)
    draw.text((cx - (cb[2] - cb[0]) / 2, cy - 17), centre, font=centre_font, fill=accent)

    steps = diagram["steps"]
    radius = 153
    node_r = 38
    nodes = []
    for i, label in enumerate(steps):
        angle = -math.pi / 2 + i * 2 * math.pi / len(steps)
        nx = cx + radius * math.cos(angle)
        ny = cy + radius * math.sin(angle)
        nodes.append((nx, ny, label))

    for i, (nx, ny, _) in enumerate(nodes):
        nnx, nny, _ = nodes[(i + 1) % len(nodes)]
        vx, vy = nnx - nx, nny - ny
        dist = max(1, math.hypot(vx, vy))
        ux, uy = vx / dist, vy / dist
        start = (nx + ux * (node_r + 4), ny + uy * (node_r + 4))
        end = (nnx - ux * (node_r + 9), nny - uy * (node_r + 9))
        arrow(draw, start, end, accent, width=4)

    node_font = font(12, bold=True, condensed=True)
    for nx, ny, label in nodes:
        draw.ellipse((nx - node_r, ny - node_r, nx + node_r, ny + node_r), fill=PAPER, outline=accent, width=3)
        draw_icon(draw, (nx, ny), label, INK, scale=0.9, width=2)
        label_lines = wrap(draw, label, node_font, 104)
        ly = ny + node_r + 5
        for line in label_lines[:2]:
            lb = draw.textbbox((0, 0), line, font=node_font)
            draw.text((nx - (lb[2] - lb[0]) / 2, ly), line, font=node_font, fill=accent)
            ly += 14


def draw_chain_diagram(draw: ImageDraw.ImageDraw, accent, diagram: dict):
    x0 = 535
    x1 = RIGHT - 10
    width = x1 - x0
    draw.text((x0 + 70, 632), diagram.get("title", "THE CONTAINMENT–TO–TRUST CHAIN"), font=font(17, bold=True, condensed=True), fill=accent)
    draw.line((x0, 655, x1, 655), fill=accent, width=2)

    steps = diagram["steps"]
    n = len(steps)
    gap = width / max(n - 1, 1)
    cy = 735
    node_r = 29
    xs = [x0 + i * gap for i in range(n)]

    for i in range(n - 1):
        arrow(draw, (xs[i] + node_r + 6, cy), (xs[i + 1] - node_r - 8, cy), accent, width=4)

    label_font = font(11, bold=True, condensed=True)
    desc_font = font(10, serif=True)
    num_font = font(12, bold=True, condensed=True)
    for i, x in enumerate(xs):
        step = steps[i]
        if isinstance(step, str):
            step = {"label": step}
        label = step["label"]
        desc = step.get("description", "")
        draw.ellipse((x - node_r, cy - node_r, x + node_r, cy + node_r), fill=PAPER, outline=accent, width=3)
        draw_icon(draw, (x, cy), label, INK, scale=0.8, width=2)
        draw.ellipse((x - 9, cy + node_r + 6, x + 9, cy + node_r + 24), fill=accent)
        nb = draw.textbbox((0, 0), str(i + 1), font=num_font)
        draw.text((x - (nb[2] - nb[0]) / 2, cy + node_r + 8), str(i + 1), font=num_font, fill=PAPER)
        label_lines = wrap(draw, label, label_font, 110)
        ly = cy + node_r + 33
        for line in label_lines[:2]:
            lb = draw.textbbox((0, 0), line, font=label_font)
            draw.text((x - (lb[2] - lb[0]) / 2, ly), line, font=label_font, fill=accent)
            ly += 12
        desc_lines = wrap(draw, desc, desc_font, 112)
        ly += 3
        for line in desc_lines[:3]:
            lb = draw.textbbox((0, 0), line, font=desc_font)
            draw.text((x - (lb[2] - lb[0]) / 2, ly), line, font=desc_font, fill=MUTED)
            ly += 11

    strap = diagram.get("strap")
    if strap:
        y = 864
        draw.rounded_rectangle((x0 + 82, y, x1 - 24, y + 28), radius=3, outline=accent, width=2)
        sb = draw.textbbox((0, 0), strap, font=font(15, bold=True, condensed=True))
        draw.text(((x0 + x1 - (sb[2] - sb[0])) / 2, y + 4), strap, font=font(15, bold=True, condensed=True), fill=accent)


def render(input_path: Path, output_path: Path):
    root = Path(__file__).resolve().parents[1]
    data = json.loads(input_path.read_text(encoding="utf-8"))
    characters = json.loads((root / "config/characters.json").read_text(encoding="utf-8"))
    speaker_key = data["speaker"]
    speaker = characters[speaker_key]
    accent = hex_rgb(speaker["accent"])

    img = Image.new("RGB", (W, H), PAPER)
    paper_texture(img)
    draw = ImageDraw.Draw(img)

    draw.rectangle((SAFE, SAFE, W - SAFE, H - SAFE), outline=accent, width=3)
    number = f'{data["slide_number"]}/{data["total_slides"]}'
    nf = font(34, bold=True, serif=True)
    nb = draw.textbbox((0, 0), number, font=nf)
    draw.text((W - SAFE - 14 - (nb[2] - nb[0]), SAFE + 8), number, font=nf, fill=accent)

    headline_width = 470
    hf, headline_lines = fit_wrapped(draw, data["headline"], headline_width, 4, 62, 50, bold=True, condensed=True)
    y = CONTENT_TOP
    for idx, line in enumerate(headline_lines):
        distressed_text(img, (LEFT, y), line, hf, accent if idx == 0 else INK, seed=idx + 5)
        y += line_height(draw, hf) + 2
    draw = ImageDraw.Draw(img)
    head_rule_y = y + 4
    draw.line((LEFT, head_rule_y, LEFT + 452, head_rule_y), fill=accent, width=4)

    df, deck_lines = fit_wrapped(draw, data["deck"], 455, 5, 28, 21, serif=True)
    deck_y = head_rule_y + 18
    deck_bottom = draw_lines(draw, deck_lines, (LEFT, deck_y), df, INK, spacing=5)

    portrait_path = root / speaker["portrait"]
    crop_box = tuple(speaker.get("crop_box", DEFAULT_PORTRAIT_CROPS.get(speaker_key, (220, 10, 1005, 900))))
    portrait, pmask = feathered_portrait(portrait_path, crop_box, (395, 405))
    img.paste(portrait, (RIGHT - 395, SAFE + 52), pmask)
    draw = ImageDraw.Draw(img)

    quote_top = max(deck_bottom + 28, 390)
    q_name_font = font(22, bold=True, condensed=True)
    quote_block_width = 360
    available_for_quote = 636 - (quote_top + 56)
    qf, qlines = fit_wrapped(draw, data["quote"], quote_block_width, 4, 28, 20, serif=True)
    while block_height(draw, qlines, qf, spacing=4) > available_for_quote and qf.size > 18:
        qf = font(qf.size - 1, serif=True)
        qlines = wrap(draw, data["quote"], qf, quote_block_width)
    quote_height = block_height(draw, qlines, qf, spacing=4)
    draw.line((LEFT, quote_top, LEFT + 452, quote_top), fill=accent, width=2)
    draw.text((LEFT, quote_top + 12), speaker["name"].upper(), font=q_name_font, fill=accent)
    quote_text_top = quote_top + 48
    draw.text((LEFT, quote_text_top - 4), "“", font=font(48, bold=True, serif=True), fill=accent)
    quote_y_end = draw_lines(draw, qlines, (LEFT + 45, quote_text_top), qf, INK, spacing=4)
    draw.text((LEFT + 45 + quote_block_width - 10, quote_text_top + max(0, quote_height - 18)), "”", font=font(48, bold=True, serif=True), fill=accent)
    quote_bottom = quote_text_top + quote_height

    facts_left, facts_w = LEFT, 392
    facts_top = max(646, quote_bottom + 22)
    facts_bottom = 872
    ensure(facts_top + 100 < facts_bottom, "Facts panel has no usable height; quote block is too tall.")
    heading_w = 240
    draw.rounded_rectangle((facts_left, facts_top, facts_left + facts_w, facts_bottom), radius=8, outline=accent, width=2)
    draw.rectangle((facts_left, facts_top, facts_left + heading_w, facts_top + 36), fill=accent)
    draw.text((facts_left + 12, facts_top + 4), "KEY FACTS / SYNTHESIS", font=font(18, bold=True, condensed=True), fill=PAPER)

    fact_font, fact_lines, total_fact_height = measure_facts(draw, data["facts"], facts_w)
    available_fact_height = facts_bottom - (facts_top + 50) - 10
    ensure(total_fact_height <= available_fact_height + 18, "Facts text overflows facts panel. Reduce copy or expand layout.")
    fy = facts_top + 50
    for item_lines in fact_lines:
        draw.ellipse((facts_left + 14, fy + 7, facts_left + 22, fy + 15), fill=accent)
        fy = draw_lines(draw, item_lines, (facts_left + 32, fy), fact_font, INK, spacing=1) + 8

    diagram = data.get("diagram", {})
    dtype = diagram.get("type", "loop")
    if dtype == "chain":
        draw_chain_diagram(draw, accent, diagram)
    else:
        draw_loop_diagram(draw, accent, diagram)

    draw_takeaway(draw, accent, data["takeaway"])
    draw_footer(draw, accent)

    ensure(deck_bottom < quote_top - 8, "Deck overlaps quote block.")
    ensure(quote_bottom < facts_top - 8, "Quote overlaps facts panel.")
    ensure(facts_bottom < TAKE_Y - 8, "Facts panel overlaps takeaway box.")
    ensure(BOTTOM_RULE_Y > TAKE_Y + 60, "Footer overlaps takeaway box.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG", optimize=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("inputs/prototype-slide.json"))
    parser.add_argument("--output", type=Path, default=Path("output/prototype-slide.png"))
    args = parser.parse_args()
    render(args.input, args.output)
    print(f"Generated {args.output.resolve()}")
