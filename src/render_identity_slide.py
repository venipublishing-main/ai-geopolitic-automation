from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

try:
    from .editorial_primitives import (
    H,
    INK,
    MUTED,
    PAPER,
    SAFE,
    W,
    arrow,
    centre_text,
    draw_deck,
    draw_footer,
    draw_frame,
    draw_headline,
    draw_quote,
    draw_small_fact_list,
    draw_takeaway_band,
    feathered_portrait,
    font,
    hex_rgb,
    paper_texture,
    wrap,
    )
except ImportError:
    from editorial_primitives import (
        H, INK, MUTED, PAPER, SAFE, W, arrow, centre_text, draw_deck, draw_footer,
        draw_frame, draw_headline, draw_quote, draw_small_fact_list, draw_takeaway_band,
        feathered_portrait, font, hex_rgb, paper_texture, wrap,
    )

DEFAULT_CROP = (100, 10, 1450, 1400)


def portrait(img, root: Path, speaker: dict, xy, size):
    path = root / speaker["portrait"]
    crop = speaker.get("crop_box", DEFAULT_CROP)
    p, mask = feathered_portrait(path, crop, size)
    img.paste(p, xy, mask)


def common_canvas(data, speaker):
    accent = hex_rgb(speaker["accent"])
    img = Image.new("RGB", (W, H), PAPER)
    paper_texture(img)
    draw = ImageDraw.Draw(img)
    draw_frame(draw, accent, data["slide_number"], data["total_slides"])
    return img, draw, accent


def render_nora(root, data, speaker):
    img, draw, accent = common_canvas(data, speaker)
    y = draw_headline(img, draw, data["headline"], accent, (96, 103), 470, max_lines=3, start=56, minimum=46)
    draw.line((96, y + 5, 550, y + 5), fill=accent, width=4)
    draw_deck(draw, data["deck"], (96, y + 20), 450, max_lines=4, start=25, minimum=20)
    portrait(img, root, speaker, (610, 128), (350, 355))
    draw = ImageDraw.Draw(img)

    # NORA identity: calm systems geometry, central axis, balanced quadrants.
    cx, cy = 755, 688
    draw.ellipse((cx - 84, cy - 84, cx + 84, cy + 84), outline=accent, width=4)
    centre_text(draw, "SYSTEM", (cx, cy - 10), font(25, bold=True, condensed=True), accent)
    centre_text(draw, "FRAME", (cx, cy + 18), font(25, bold=True, condensed=True), accent)
    draw.line((cx, 540, cx, 842), fill=accent, width=2)
    draw.line((602, cy, 908, cy), fill=accent, width=2)
    labels = data.get("mechanism", ["SIGNAL", "STATE", "FEEDBACK", "OUTCOME"])
    positions = [(650, 570), (860, 570), (650, 805), (860, 805)]
    for i, (label, pos) in enumerate(zip(labels[:4], positions)):
        draw.rounded_rectangle((pos[0]-58, pos[1]-28, pos[0]+58, pos[1]+28), radius=14, outline=accent, width=2)
        centre_text(draw, label, pos, font(12, bold=True, condensed=True), accent)
        arrow(draw, pos, (cx, cy), accent, width=2)

    draw_quote(draw, data["quote"], speaker["name"], accent, (96, 390, 535, 548))
    draw_small_fact_list(draw, data["facts"], accent, (96, 575, 500, 870), heading="SYSTEM OBSERVATIONS")
    draw_takeaway_band(draw, accent, data["takeaway"], label="NORA / SYNTHESIS")
    draw_footer(draw, accent)
    return img


def render_johan(root, data, speaker):
    img, draw, accent = common_canvas(data, speaker)
    portrait(img, root, speaker, (96, 138), (350, 390))
    draw = ImageDraw.Draw(img)
    y = draw_headline(img, draw, data["headline"], accent, (500, 112), 445, max_lines=4, start=53, minimum=42)
    draw.line((500, y + 5, 938, y + 5), fill=accent, width=4)
    draw_deck(draw, data["deck"], (500, y + 20), 430, max_lines=4, start=23, minimum=19)
    draw_quote(draw, data["quote"], speaker["name"], accent, (500, 385, 940, 530))

    # Johan identity: rigid institutional spine, squared stages, containment/order.
    x = 265
    draw.line((x, 555, x, 857), fill=accent, width=8)
    stages = data.get("mechanism", ["RULE", "AUTHORITY", "ENFORCEMENT", "TRUST"])
    ys = [590, 670, 750, 830]
    for idx, (label, yy) in enumerate(zip(stages[:4], ys), start=1):
        draw.rectangle((130, yy-25, 400, yy+25), outline=accent, width=3)
        draw.rectangle((130, yy-25, 171, yy+25), fill=accent)
        centre_text(draw, str(idx), (150, yy), font(16, bold=True, condensed=True), PAPER)
        draw.text((184, yy-12), label, font=font(16, bold=True, condensed=True), fill=accent)
        if yy != ys[-1]:
            arrow(draw, (x, yy+26), (x, yy+54), accent, width=3)
    draw.text((130, 548), "INSTITUTIONAL SPINE", font=font(15, bold=True, condensed=True), fill=accent)
    draw_small_fact_list(draw, data["facts"], accent, (455, 565, 940, 870), heading="EVIDENCE / OVERSIGHT")
    draw_takeaway_band(draw, accent, data["takeaway"], label="JOHAN / ORDER TEST")
    draw_footer(draw, accent)
    return img


def render_diane(root, data, speaker):
    img, draw, accent = common_canvas(data, speaker)
    y = draw_headline(img, draw, data["headline"], accent, (96, 105), 500, max_lines=3, start=54, minimum=44)
    draw.line((96, y + 5, 565, y + 5), fill=accent, width=4)
    draw_deck(draw, data["deck"], (96, y + 19), 465, max_lines=4, start=24, minimum=19)
    portrait(img, root, speaker, (635, 132), (320, 350))
    draw = ImageDraw.Draw(img)
    draw_quote(draw, data["quote"], speaker["name"], accent, (96, 365, 565, 515))

    # Diane identity: economic dashboard + transmission grid.
    draw.text((96, 548), "MARKET / DELIVERY TRANSMISSION", font=font(17, bold=True, condensed=True), fill=accent)
    metrics = data.get("metrics", [
        {"label": "INPUT", "value": "PRICE"},
        {"label": "CHANNEL", "value": "FLOW"},
        {"label": "OUTCOME", "value": "DELIVERY"},
    ])
    x0, y0 = 96, 578
    card_w, gap = 270, 20
    for i, item in enumerate(metrics[:3]):
        x = x0 + i * (card_w + gap)
        draw.rectangle((x, y0, x + card_w, y0 + 112), outline=accent, width=2)
        draw.rectangle((x, y0, x + card_w, y0 + 28), fill=accent)
        centre_text(draw, item.get("label", "METRIC"), (x+card_w/2, y0+14), font(13, bold=True, condensed=True), PAPER)
        centre_text(draw, item.get("value", "—"), (x+card_w/2, y0+66), font(27, bold=True, serif=True), accent)
    # flow rail
    fy = 725
    nodes = data.get("mechanism", ["CAPITAL", "CONTRACT", "SERVICE", "HOUSEHOLD"])
    xs = [135, 385, 635, 885]
    for i in range(3):
        arrow(draw, (xs[i]+55, fy), (xs[i+1]-55, fy), accent, width=4)
    for x, label in zip(xs, nodes[:4]):
        draw.rounded_rectangle((x-55, fy-32, x+55, fy+32), radius=6, outline=accent, width=3)
        centre_text(draw, label, (x, fy), font(12, bold=True, condensed=True), accent)
    draw_small_fact_list(draw, data["facts"], accent, (96, 780, 940, 874), heading="ECONOMIC CHECKS")
    draw_takeaway_band(draw, accent, data["takeaway"], label="DIANE / PERFORMANCE TEST")
    draw_footer(draw, accent)
    return img


def render_kai(root, data, speaker):
    img, draw, accent = common_canvas(data, speaker)
    portrait(img, root, speaker, (96, 145), (335, 360))
    draw = ImageDraw.Draw(img)
    y = draw_headline(img, draw, data["headline"], accent, (485, 108), 455, max_lines=4, start=53, minimum=42)
    draw.line((485, y + 5, 940, y + 5), fill=accent, width=4)
    draw_deck(draw, data["deck"], (485, y + 20), 445, max_lines=4, start=23, minimum=19)
    draw_quote(draw, data["quote"], speaker["name"], accent, (485, 390, 940, 525))

    # Kai identity: distributed network, circular nodes, feedback paths.
    centre = (690, 700)
    draw.ellipse((centre[0]-72, centre[1]-72, centre[0]+72, centre[1]+72), outline=accent, width=4)
    centre_text(draw, "NETWORK", centre, font(22, bold=True, condensed=True), accent)
    labels = data.get("mechanism", ["SENSOR", "MODEL", "NODE", "USER", "REPAIR"])
    ring = [(525, 620), (815, 585), (905, 710), (790, 825), (520, 815)]
    for i, (label, pos) in enumerate(zip(labels[:5], ring)):
        r = 44 if i % 2 == 0 else 36
        draw.ellipse((pos[0]-r, pos[1]-r, pos[0]+r, pos[1]+r), outline=accent, width=3)
        centre_text(draw, label, pos, font(11, bold=True, condensed=True), accent)
        draw.line((pos[0], pos[1], centre[0], centre[1]), fill=accent, width=2)
    # feedback arc / dotted hint
    draw.arc((470, 545, 930, 865), start=205, end=350, fill=accent, width=3)
    arrow(draw, (860, 838), (810, 856), accent, width=3)
    draw_small_fact_list(draw, data["facts"], accent, (96, 555, 425, 870), heading="NETWORK SIGNALS")
    draw_takeaway_band(draw, accent, data["takeaway"], label="KAI / SYSTEM TEST")
    draw_footer(draw, accent)
    return img


def render_thabo(root, data, speaker):
    img, draw, accent = common_canvas(data, speaker)
    y = draw_headline(img, draw, data["headline"], accent, (96, 104), 840, max_lines=3, start=56, minimum=44)
    draw.line((96, y + 5, 940, y + 5), fill=accent, width=5)
    draw_deck(draw, data["deck"], (96, y + 20), 820, max_lines=3, start=24, minimum=19)
    portrait(img, root, speaker, (96, 420), (365, 440))
    draw = ImageDraw.Draw(img)
    draw_quote(draw, data["quote"], speaker["name"], accent, (500, 340, 940, 490), large=True)

    # Thabo identity: material burden ledger, heavy stacked blocks, asymmetry.
    draw.text((500, 525), "WHO CARRIES THE BURDEN?", font=font(20, bold=True, condensed=True), fill=accent)
    burdens = data.get("mechanism", ["COST", "TIME", "RISK", "HOUSEHOLD"])
    yy = 565
    widths = [380, 330, 285, 240]
    for i, (label, bw) in enumerate(zip(burdens[:4], widths), start=1):
        draw.rectangle((500, yy, 500+bw, yy+52), fill=accent if i in (1,4) else PAPER, outline=accent, width=3)
        fill = PAPER if i in (1,4) else accent
        draw.text((516, yy+11), f"{i}. {label}", font=font(18, bold=True, condensed=True), fill=fill)
        yy += 64
    draw.line((480, 555, 480, 850), fill=accent, width=7)
    draw_small_fact_list(draw, data["facts"], accent, (96, 760, 455, 875), heading="MATERIAL FACTS")
    draw_takeaway_band(draw, accent, data["takeaway"], label="THABO / MATERIAL TEST")
    draw_footer(draw, accent)
    return img


def render_amari(root, data, speaker):
    img, draw, accent = common_canvas(data, speaker)
    y = draw_headline(img, draw, data["headline"], accent, (96, 106), 500, max_lines=4, start=53, minimum=42)
    draw.line((96, y + 5, 560, y + 5), fill=accent, width=4)
    draw_deck(draw, data["deck"], (96, y + 20), 455, max_lines=4, start=23, minimum=19)
    portrait(img, root, speaker, (620, 135), (335, 385))
    draw = ImageDraw.Draw(img)
    draw_quote(draw, data["quote"], speaker["name"], accent, (96, 385, 555, 535))

    # Amari identity: organic regional arcs + continuity/memory nodes.
    draw.text((96, 575), "REGION / MEMORY / DIGNITY", font=font(18, bold=True, condensed=True), fill=accent)
    cx, cy = 720, 710
    draw.arc((515, 545, 930, 865), start=190, end=350, fill=accent, width=4)
    draw.arc((565, 590, 875, 820), start=175, end=365, fill=accent, width=2)
    nodes = data.get("mechanism", ["PLACE", "MEMORY", "RIGHTS", "SOLIDARITY"])
    positions = [(560, 690), (690, 605), (850, 690), (715, 820)]
    for label, pos in zip(nodes[:4], positions):
        draw.ellipse((pos[0]-48, pos[1]-48, pos[0]+48, pos[1]+48), fill=PAPER, outline=accent, width=3)
        centre_text(draw, label, pos, font(11, bold=True, condensed=True), accent)
    # continuity lines are deliberately curved/soft rather than mechanical.
    draw.line((602, 665, 650, 625), fill=accent, width=2)
    draw.line((735, 625, 805, 668), fill=accent, width=2)
    draw.line((825, 730, 750, 790), fill=accent, width=2)
    draw.line((680, 790, 595, 730), fill=accent, width=2)
    draw_small_fact_list(draw, data["facts"], accent, (96, 590, 455, 872), heading="HUMAN / REGIONAL CONTEXT")
    draw_takeaway_band(draw, accent, data["takeaway"], label="AMARI / DIGNITY TEST")
    draw_footer(draw, accent)
    return img


RENDERERS = {
    "nora": render_nora,
    "johan_vosloo": render_johan,
    "diane_sterling": render_diane,
    "kai_patel": render_kai,
    "thabo_mokoena": render_thabo,
    "amari_ndlovu": render_amari,
}


def render(input_path: Path, output_path: Path):
    root = Path(__file__).resolve().parents[1]
    data = json.loads(input_path.read_text(encoding="utf-8"))
    characters = json.loads((root / "config/characters.json").read_text(encoding="utf-8"))
    speaker_key = data["speaker"]
    if speaker_key not in RENDERERS:
        raise ValueError(f"No identity renderer for {speaker_key}")
    speaker = characters[speaker_key]
    img = RENDERERS[speaker_key](root, data, speaker)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG", optimize=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    render(args.input, args.output)
    print(f"Generated {args.output.resolve()}")
