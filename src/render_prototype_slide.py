from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, ImageFilter


W = 1080
H = 1080
SAFE = 76
PAPER = (245, 241, 231)
INK = (24, 26, 28)
MUTED = (75, 73, 68)


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


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = word if not current else current + " " + word
        box = draw.textbbox((0, 0), test, font=fnt)
        if box[2] - box[0] <= width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_wrapped(draw, text: str, width: int, max_lines: int, start: int, minimum: int, **font_kwargs):
    for size in range(start, minimum - 1, -2):
        fnt = font(size, **font_kwargs)
        lines = wrap(draw, text, fnt, width)
        if len(lines) <= max_lines:
            return fnt, lines
    fnt = font(minimum, **font_kwargs)
    return fnt, wrap(draw, text, fnt, width)


def draw_lines(draw, lines: Iterable[str], xy, fnt, fill, spacing=6):
    x, y = xy
    line_height = draw.textbbox((0, 0), "Ag", font=fnt)[3]
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += line_height + spacing
    return y


def paper_texture(img: Image.Image):
    random.seed(20260720)
    px = img.load()
    for _ in range(24000):
        x = random.randrange(W)
        y = random.randrange(H)
        r, g, b = px[x, y]
        d = random.choice((-4, -3, -2, -1, 1, 2, 3))
        px[x, y] = (max(0, min(255, r+d)), max(0, min(255, g+d)), max(0, min(255, b+d)))


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
            md.ellipse((rx, ry, rx+random.randint(1,3), ry+random.randint(1,2)), fill=0)
    colour = Image.new("RGB", img.size, fill)
    img.paste(colour, (0, 0), mask)


def feathered_portrait(path: Path, crop_box, size):
    im = Image.open(path).convert("RGB").crop(crop_box).resize(size, Image.Resampling.LANCZOS)
    mask = Image.new("L", size, 255)
    md = ImageDraw.Draw(mask)
    fade = 44
    for i in range(fade):
        alpha = int(255 * i / fade)
        md.rectangle((0, size[1]-fade+i, size[0], size[1]-fade+i+1), fill=255-alpha)
    mask = mask.filter(ImageFilter.GaussianBlur(7))
    return im, mask


def arrow(draw: ImageDraw.ImageDraw, start, end, fill, width=4):
    draw.line((start, end), fill=fill, width=width)
    ang = math.atan2(end[1]-start[1], end[0]-start[0])
    length = 14
    left = (end[0]-length*math.cos(ang-0.55), end[1]-length*math.sin(ang-0.55))
    right = (end[0]-length*math.cos(ang+0.55), end[1]-length*math.sin(ang+0.55))
    draw.polygon([end, left, right], fill=fill)


def render(input_path: Path, output_path: Path):
    root = Path(__file__).resolve().parents[1]
    data = json.loads(input_path.read_text(encoding="utf-8"))
    characters = json.loads((root / "config/characters.json").read_text(encoding="utf-8"))
    speaker = characters[data["speaker"]]
    accent = hex_rgb(speaker["accent"])

    img = Image.new("RGB", (W, H), PAPER)
    paper_texture(img)
    draw = ImageDraw.Draw(img)

    # Frame and slide number.
    draw.rectangle((SAFE, SAFE, W-SAFE, H-SAFE), outline=accent, width=3)
    number = f'{data["slide_number"]}/{data["total_slides"]}'
    nf = font(34, bold=True, serif=True)
    nb = draw.textbbox((0,0), number, font=nf)
    draw.text((W-SAFE-14-(nb[2]-nb[0]), SAFE+8), number, font=nf, fill=accent)

    # Headline block.
    headline_width = 500
    hf, headline_lines = fit_wrapped(draw, data["headline"], headline_width, 3, 68, 52, bold=True, condensed=True)
    y = SAFE + 20
    for idx, line in enumerate(headline_lines):
        distressed_text(img, (SAFE+18, y), line, hf, accent if idx == 0 else INK, seed=idx+5)
        y += draw.textbbox((0,0), "Ag", font=hf)[3] + 2
    draw = ImageDraw.Draw(img)
    draw.line((SAFE+20, y+4, SAFE+470, y+4), fill=accent, width=5)

    df, deck_lines = fit_wrapped(draw, data["deck"], 480, 4, 27, 22, serif=True)
    deck_y = y + 18
    deck_bottom = draw_lines(draw, deck_lines, (SAFE+20, deck_y), df, INK, spacing=5)

    # Portrait top-right.
    portrait_path = root / speaker["portrait"]
    portrait, pmask = feathered_portrait(portrait_path, (220, 10, 1005, 900), (395, 430))
    img.paste(portrait, (W-SAFE-415, SAFE+52), pmask)
    draw = ImageDraw.Draw(img)

    # Quote block left, below deck.
    quote_top = max(deck_bottom + 22, 392)
    draw.line((SAFE+20, quote_top, SAFE+470, quote_top), fill=accent, width=2)
    draw.text((SAFE+20, quote_top+12), speaker["name"].upper(), font=font(23, bold=True, condensed=True), fill=accent)

    qf, qlines = fit_wrapped(draw, data["quote"], 370, 3, 29, 24, serif=True)
    draw.text((SAFE+20, quote_top+48), "“", font=font(48, bold=True, serif=True), fill=accent)
    quote_y = draw_lines(draw, qlines, (SAFE+65, quote_top+55), qf, INK, spacing=4)
    draw.text((SAFE+425, quote_y-30), "”", font=font(48, bold=True, serif=True), fill=accent)

    # Facts panel.
    facts_left, facts_top, facts_w, facts_bottom = SAFE+20, 638, 390, 872
    draw.rounded_rectangle((facts_left, facts_top, facts_left+facts_w, facts_bottom), radius=8, outline=accent, width=2)
    draw.rectangle((facts_left, facts_top, facts_left+205, facts_top+36), fill=accent)
    draw.text((facts_left+12, facts_top+4), "KEY FACTS / SYNTHESIS", font=font(18, bold=True, condensed=True), fill=PAPER)
    fy = facts_top+50
    fact_font = font(15, serif=True)
    for item in data["facts"]:
        draw.ellipse((facts_left+14, fy+7, facts_left+22, fy+15), fill=accent)
        lines = wrap(draw, item, fact_font, facts_w-48)
        fy = draw_lines(draw, lines, (facts_left+32, fy), fact_font, INK, spacing=1) + 7

    # Process loop in right-lower area.
    cx, cy = 760, 705
    centre_r = 68
    draw.ellipse((cx-centre_r, cy-centre_r, cx+centre_r, cy+centre_r), outline=accent, width=4)
    centre_font = font(28, bold=True, condensed=True)
    centre = data["diagram"]["centre"]
    cb = draw.textbbox((0,0), centre, font=centre_font)
    draw.text((cx-(cb[2]-cb[0])/2, cy-16), centre, font=centre_font, fill=accent)

    steps = data["diagram"]["steps"]
    radius = 150
    node_r = 38
    nodes = []
    for i, label in enumerate(steps):
        angle = -math.pi/2 + i * 2*math.pi/len(steps)
        nx = cx + radius*math.cos(angle)
        ny = cy + radius*math.sin(angle)
        nodes.append((nx, ny, label))

    # Draw arrows before nodes.
    for i, (nx, ny, _) in enumerate(nodes):
        nnx, nny, _ = nodes[(i+1) % len(nodes)]
        vx, vy = nnx-nx, nny-ny
        dist = max(1, math.hypot(vx, vy))
        ux, uy = vx/dist, vy/dist
        start = (nx + ux*(node_r+4), ny + uy*(node_r+4))
        end = (nnx - ux*(node_r+9), nny - uy*(node_r+9))
        arrow(draw, start, end, accent, width=4)

    node_font = font(12, bold=True, condensed=True)
    for nx, ny, label in nodes:
        draw.ellipse((nx-node_r, ny-node_r, nx+node_r, ny+node_r), fill=PAPER, outline=accent, width=3)
        # Minimal symbolic mark.
        draw.ellipse((nx-8, ny-8, nx+8, ny+8), fill=INK)
        label_lines = wrap(draw, label, node_font, 104)
        ly = ny + node_r + 5
        for line in label_lines[:2]:
            lb = draw.textbbox((0,0), line, font=node_font)
            draw.text((nx-(lb[2]-lb[0])/2, ly), line, font=node_font, fill=accent)
            ly += 14

    # Takeaway box.
    take_y = 892
    draw.rounded_rectangle((SAFE+18, take_y, W-SAFE-18, 952), radius=6, outline=accent, width=2)
    draw.text((SAFE+32, take_y+8), "IDEOLOGICAL LENS / TAKEAWAY", font=font(16, bold=True, condensed=True), fill=accent)
    tf, tlines = fit_wrapped(draw, data["takeaway"], 570, 2, 19, 16, serif=True)
    draw_lines(draw, tlines, (380, take_y+8), tf, INK, spacing=1)

    # Footer kept inside the safe frame.
    footer_rule_y = 966
    draw.line((SAFE+18, footer_rule_y, W-SAFE-18, footer_rule_y), fill=INK, width=2)
    draw.rectangle((SAFE+18, footer_rule_y+8, SAFE+61, footer_rule_y+42), outline=accent, width=2)
    draw.text((SAFE+23, footer_rule_y+8), "AI.", font=font(19, bold=True, serif=True), fill=accent)
    draw.text((SAFE+72, footer_rule_y+13), "AI GEOPOLITIC", font=font(17, bold=True, condensed=True), fill=INK)
    footer = "The event is factual. The interpretation ideological."
    ff = font(12, serif=True)
    fb = draw.textbbox((0,0), footer, font=ff)
    draw.text((W-SAFE-18-(fb[2]-fb[0]), footer_rule_y+16), footer, font=ff, fill=MUTED)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG", optimize=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("inputs/prototype-slide.json"))
    parser.add_argument("--output", type=Path, default=Path("output/prototype-slide.png"))
    args = parser.parse_args()
    render(args.input, args.output)
    print(f"Generated {args.output.resolve()}")
