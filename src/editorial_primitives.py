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


def block_height(draw: ImageDraw.ImageDraw, lines: Sequence[str], fnt, spacing: int = 4) -> int:
    if not lines:
        return 0
    return len(lines) * line_height(draw, fnt) + max(0, len(lines) - 1) * spacing


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


def fit_wrapped(
    draw,
    text: str,
    width: int,
    max_lines: int,
    start: int,
    minimum: int,
    *,
    max_height: int | None = None,
    spacing: int = 4,
    label: str = "text",
    **font_kwargs,
):
    for size in range(start, minimum - 1, -1):
        fnt = font(size, **font_kwargs)
        lines = wrap(draw, text, fnt, width)
        if len(lines) > max_lines:
            continue
        if max_height is not None and block_height(draw, lines, fnt, spacing) > max_height:
            continue
        return fnt, lines
    raise LayoutError(
        f"{label} does not fit: width={width}, max_lines={max_lines}, min_font={minimum}, max_height={max_height}."
    )


def draw_lines(draw, lines: Iterable[str], xy, fnt, fill, spacing=4):
    x, y = xy
    lh = line_height(draw, fnt)
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill)
        y += lh + spacing
    return y - spacing if lines else y


def paper_texture(img: Image.Image):
    """Deterministic paper grain with faint fibre scratches.

    The original handcrafted episodes are materially denser than a flat cream
    canvas. Keep this subtle enough for body copy while avoiding a sterile
    template background.
    """
    rng = random.Random(20260822)
    px = img.load()
    for _ in range(30000):
        x = rng.randrange(W)
        y = rng.randrange(H)
        r, g, b = px[x, y]
        d = rng.choice((-5, -4, -3, -2, -1, 1, 2, 3, 4))
        px[x, y] = tuple(max(0, min(255, c + d)) for c in (r, g, b))

    fibre = Image.new("RGBA", img.size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(fibre)
    for _ in range(190):
        x = rng.randrange(18, W - 18)
        y = rng.randrange(18, H - 18)
        length = rng.randrange(14, 90)
        alpha = rng.randrange(5, 12)
        colour = (*INK, alpha) if rng.random() < 0.72 else (255, 255, 255, alpha)
        fd.line((x, y, min(W - 1, x + length), y + rng.choice((-1, 0, 1))), fill=colour, width=1)
    img.paste(fibre, (0, 0), fibre)


def _stable_seed(*parts) -> int:
    text = "|".join(str(p or "") for p in parts)
    return sum((idx + 1) * ord(ch) for idx, ch in enumerate(text)) & 0xFFFFFFFF


def editorial_atmosphere(
    img: Image.Image,
    accent,
    theme: str,
    *,
    variant: str = "",
    seed: int = 0,
):
    """Add a low-contrast character-specific editorial background layer.

    This is deliberately decorative rather than informational. It supplies the
    engraved maps / institutional geometry / network traces / ledger marks that
    make the reference episodes feel authored, while leaving exact content to
    the foreground renderer.
    """
    theme = str(theme or "").strip().lower()
    rng = random.Random(_stable_seed(theme, variant, seed, 20260825))
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    faint = (*accent, 22)
    soft = (*accent, 34)
    ghost_ink = (*INK, 12)

    # Universal registration / print texture, mostly around the frame edges.
    for x0, y0 in ((105, 805), (830, 190)):
        for yy in range(y0, y0 + 96, 12):
            for xx in range(x0, x0 + 132, 12):
                if rng.random() < 0.52:
                    d.ellipse((xx, yy, xx + 2, yy + 2), fill=faint)
    for x in (116, 132, 148):
        d.line((x, 86, x, 99), fill=soft, width=1)
    for y in (932, 944):
        d.line((906, y, 958, y), fill=ghost_ink, width=1)

    if theme == "nora":
        # Systems / globe / diagnostic axes.
        box = (690, 400, 1080, 790)
        for inset in (0, 38, 76):
            b = (box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset)
            d.arc(b, 196, 352, fill=faint, width=2)
        d.line((785, 540, 1015, 540), fill=faint, width=2)
        d.line((900, 425, 900, 690), fill=faint, width=2)
        for px, py in ((780, 540), (900, 425), (1015, 540), (900, 690)):
            d.ellipse((px - 5, py - 5, px + 5, py + 5), outline=soft, width=2)

    elif theme == "johan_vosloo":
        # Institutional facade / chain-of-authority geometry.
        base_y = 855
        d.line((680, base_y, 1010, base_y), fill=faint, width=3)
        for x in range(712, 990, 55):
            d.line((x, 640, x, base_y), fill=faint, width=3)
            d.line((x - 12, 640, x + 12, 640), fill=soft, width=2)
            d.line((x - 16, base_y, x + 16, base_y), fill=soft, width=2)
        d.arc((680, 555, 1010, 760), 190, 350, fill=faint, width=3)
        for y in (700, 740, 780):
            d.line((630, y, 690, y), fill=ghost_ink, width=2)

    elif theme == "diane_sterling":
        # Market ticks, conversion bars and transmission slope.
        x0, y0 = 650, 815
        d.line((x0, y0, 1025, y0), fill=faint, width=2)
        heights = [42, 76, 58, 112, 95, 142]
        for i, h in enumerate(heights):
            x = x0 + 28 + i * 52
            d.rectangle((x, y0 - h, x + 22, y0), outline=faint, width=2)
        pts = [(655, 480), (720, 455), (785, 500), (850, 430), (920, 448), (1000, 380)]
        d.line(pts, fill=soft, width=2)
        for x, y in pts:
            d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=soft)

    elif theme == "kai_patel":
        # Distributed network / circuit traces.
        nodes = [(655, 420), (780, 360), (915, 430), (1005, 560), (895, 680), (730, 650), (635, 545)]
        links = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 0), (1, 5), (2, 5), (0, 4)]
        for a, b in links:
            d.line((nodes[a], nodes[b]), fill=faint, width=2)
        for x, y in nodes:
            r = 7 if rng.random() < 0.35 else 5
            d.ellipse((x - r, y - r, x + r, y + r), outline=soft, width=2)
        for y in (770, 790, 810):
            d.line((650, y, 1015, y), fill=ghost_ink, width=1)

    elif theme == "thabo_mokoena":
        # Ledger / burden / strike marks.
        for y in range(620, 865, 34):
            d.line((610, y, 1015, y), fill=faint, width=2)
            d.line((610, y, 655, y), fill=soft, width=4)
        for x in range(700, 1020, 18):
            d.line((x, 410, x - 105, 540), fill=ghost_ink, width=2)
        d.line((660, 870, 1015, 545), fill=(*accent, 28), width=5)

    elif theme == "amari_ndlovu":
        # Regional contours, routes and memory rings.
        centre = (865, 620)
        for r in (80, 125, 170, 220):
            d.arc((centre[0]-r, centre[1]-r, centre[0]+r, centre[1]+r), 205, 28, fill=faint, width=2)
        route = [(620, 780), (690, 700), (760, 735), (835, 640), (925, 675), (1015, 565)]
        d.line(route, fill=soft, width=3)
        for x, y in route:
            d.ellipse((x - 5, y - 5, x + 5, y + 5), outline=soft, width=2)
        for x in range(625, 1000, 42):
            d.arc((x, 385, x + 54, 440), 190, 345, fill=ghost_ink, width=1)

    img.paste(overlay, (0, 0), overlay)


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
    source = Image.open(path).convert("RGB")
    crop = tuple(int(v) for v in crop_box)
    ensure(crop[0] >= 0 and crop[1] >= 0 and crop[2] <= source.width and crop[3] <= source.height, f"Portrait crop outside source: {path}")
    ensure(crop[2] > crop[0] and crop[3] > crop[1], f"Invalid portrait crop: {path}")
    im = source.crop(crop).resize(size, Image.Resampling.LANCZOS)
    mask = Image.new("L", size, 255)
    md = ImageDraw.Draw(mask)
    fade_bottom = min(fade_bottom, size[1])
    for i in range(fade_bottom):
        alpha = int(255 * i / max(1, fade_bottom))
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


def validate_box(box, label="box"):
    x0, y0, x1, y1 = box
    ensure(x0 < x1 and y0 < y1, f"{label} has invalid dimensions: {box}")
    ensure(x0 >= SAFE and x1 <= W - SAFE, f"{label} crosses horizontal safe area: {box}")
    ensure(y0 >= SAFE and y1 <= BOTTOM_RULE_Y - 10, f"{label} crosses vertical safe area: {box}")


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


def draw_headline(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    headline: str,
    accent,
    xy,
    width: int,
    max_lines=4,
    start=58,
    minimum=44,
    accent_first=True,
    max_bottom: int | None = None,
):
    x, y = xy
    max_height = None if max_bottom is None else max_bottom - y
    fnt, lines = fit_wrapped(
        draw, headline, width, max_lines, start, minimum,
        max_height=max_height, spacing=1, label="headline", bold=True, condensed=True,
    )
    for idx, line in enumerate(lines):
        distressed_text(img, (x, y), line, fnt, accent if (accent_first and idx == 0) else INK, seed=idx + 11)
        y += line_height(draw, fnt) + 1
    bottom = y - 1
    if max_bottom is not None:
        ensure(bottom <= max_bottom, "Headline crossed its reserved region.")
    return bottom


def draw_deck(
    draw,
    deck: str,
    xy,
    width: int,
    max_lines=4,
    start=25,
    minimum=19,
    max_bottom: int | None = None,
):
    x, y = xy
    max_height = None if max_bottom is None else max_bottom - y
    fnt, lines = fit_wrapped(
        draw, deck, width, max_lines, start, minimum,
        max_height=max_height, spacing=4, label="deck", serif=True,
    )
    bottom = draw_lines(draw, lines, (x, y), fnt, INK, spacing=4)
    if max_bottom is not None:
        ensure(bottom <= max_bottom, "Deck crossed its reserved region.")
    return bottom


def draw_quote(draw, quote: str, speaker_name: str, accent, box, large=False):
    validate_box(box, "quote")
    x0, y0, x1, y1 = box
    draw.line((x0, y0, x1, y0), fill=accent, width=2)
    name_font = font(18, bold=True, condensed=True)
    draw.text((x0, y0 + 10), speaker_name.upper(), font=name_font, fill=accent)

    quote_y = y0 + 47
    quote_x = x0 + 38
    quote_width = x1 - quote_x - 10
    quote_height = y1 - quote_y - 8
    start = 27 if large else 23
    minimum = 18 if large else 17
    qf, qlines = fit_wrapped(
        draw, quote, quote_width, 5, start, minimum,
        max_height=quote_height, spacing=3, label=f"quote ({speaker_name})", serif=True,
    )
    draw.text((x0, y0 + 39), "“", font=font(43, bold=True, serif=True), fill=accent)
    bottom = draw_lines(draw, qlines, (quote_x, quote_y), qf, INK, spacing=3)
    ensure(bottom <= y1 - 5, f"Quote for {speaker_name} overflowed its box.")
    return bottom


def draw_takeaway_band(draw, accent, text: str, y=894, label="IDEOLOGICAL LENS / TAKEAWAY"):
    x0, x1 = SAFE + 18, W - SAFE - 18
    box = (x0, y, x1, y + 58)
    validate_box(box, "takeaway")
    draw.rounded_rectangle(box, radius=5, fill=PAPER, outline=accent, width=2)
    label_font = font(15, bold=True, condensed=True)
    draw.text((x0 + 13, y + 7), label, font=label_font, fill=accent)
    text_x = 382
    tf, lines = fit_wrapped(
        draw, text, x1 - text_x - 12, 2, 18, 15,
        max_height=42, spacing=1, label="takeaway", serif=True,
    )
    bottom = draw_lines(draw, lines, (text_x, y + 8), tf, INK, spacing=1)
    ensure(bottom <= y + 51, "Takeaway text overflowed band.")
    return y + 58


def draw_small_fact_list(
    draw,
    facts: Sequence[str],
    accent,
    box,
    heading="KEY FACTS",
    *,
    minimum: int = 14,
    start: int = 16,
    fill_background: bool = True,
):
    validate_box(box, "facts")
    x0, y0, x1, y1 = box
    if fill_background:
        draw.rounded_rectangle((x0, y0, x1, y1), radius=7, fill=PAPER, outline=accent, width=2)
    else:
        draw.rounded_rectangle((x0, y0, x1, y1), radius=7, outline=accent, width=2)
    header_w = min(max(230, int((x1 - x0) * 0.42)), x1 - x0)
    draw.rectangle((x0, y0, x0 + header_w, y0 + 34), fill=accent)
    heading_font, heading_lines = fit_wrapped(
        draw, heading, header_w - 20, 1, 16, 13,
        max_height=24, spacing=0, label="facts heading", bold=True, condensed=True,
    )
    draw.text((x0 + 10, y0 + 4), heading_lines[0], font=heading_font, fill=PAPER)

    body_y = y0 + 46
    available = y1 - body_y - 8
    marker_x = x0 + 27
    text_x = x0 + 45
    body_width = x1 - text_x - 12
    selected = None
    for size in range(start, minimum - 1, -1):
        ff = font(size, serif=True)
        rows = [wrap(draw, f, ff, body_width) for f in facts]
        # 7 px between numbered evidence rows, 1 px between wrapped lines.
        need = sum(block_height(draw, r, ff, spacing=1) + 7 for r in rows)
        if need <= available:
            selected = ff, rows
            break
    if selected is None:
        raise LayoutError(
            f"Facts do not fit in {box} at minimum {minimum}px. Reduce copy or enlarge facts panel."
        )
    ff, rows = selected
    draw.line((marker_x, body_y + 4, marker_x, y1 - 11), fill=accent, width=1)
    y = body_y
    for index, row_lines in enumerate(rows, start=1):
        marker_y = y + 10
        draw.ellipse((marker_x - 9, marker_y - 9, marker_x + 9, marker_y + 9), fill=PAPER, outline=accent, width=2)
        centre_text(draw, f"{index:02d}", (marker_x, marker_y), font(8, bold=True, condensed=True), accent)
        y = draw_lines(draw, row_lines, (text_x, y), ff, INK, spacing=1) + 7
        if index != len(rows) and y + 1 < y1:
            draw.line((text_x, y - 3, x1 - 12, y - 3), fill=accent, width=1)
    ensure(y <= y1, "Facts crossed bottom of facts panel.")
    return y


def centre_text(draw, text: str, centre, fnt, fill):
    b = draw.textbbox((0, 0), text, font=fnt)
    draw.text((centre[0] - (b[2] - b[0]) / 2, centre[1] - (b[3] - b[1]) / 2), text, font=fnt, fill=fill)
