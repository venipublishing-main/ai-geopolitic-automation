from __future__ import annotations

import argparse
import json
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
        LayoutError,
        arrow,
        centre_text,
        draw_deck,
        editorial_atmosphere,
        draw_footer,
        draw_frame,
        draw_headline,
        draw_quote,
        draw_small_fact_list,
        draw_takeaway_band,
        ensure,
        feathered_portrait,
        font,
        hex_rgb,
        paper_texture,
    )
except ImportError:
    from editorial_primitives import (
        H, INK, MUTED, PAPER, SAFE, W, LayoutError, arrow, centre_text,
        draw_deck, editorial_atmosphere, draw_footer, draw_frame, draw_headline, draw_quote,
        draw_small_fact_list, draw_takeaway_band, ensure, feathered_portrait,
        font, hex_rgb, paper_texture,
    )
try:
    from .contextual_illustrations import apply_context_art
except ImportError:
    from contextual_illustrations import apply_context_art


DEFAULT_CROP = (100, 10, 1450, 1400)
TAKEAWAY_Y = 894
CONTENT_BOTTOM = 875


def portrait(img, root: Path, speaker: dict, xy, size):
    path = root / speaker["portrait"]
    ensure(path.exists(), f"Portrait asset not found: {path}")
    crop = speaker.get("crop_box", DEFAULT_CROP)
    x, y = xy
    ensure(x >= SAFE and x + size[0] <= W - SAFE, f"Portrait crosses horizontal safe area: {speaker['name']}")
    ensure(y >= SAFE and y + size[1] <= TAKEAWAY_Y - 12, f"Portrait crosses lower content boundary: {speaker['name']}")

    # A light printmaker's plate around the locked portrait helps the presenter
    # feel embedded in the editorial composition without altering identity.
    accent = hex_rgb(speaker["accent"])
    plate = Image.new("RGBA", img.size, (0, 0, 0, 0))
    pd = ImageDraw.Draw(plate)
    px0 = max(SAFE, x - 9)
    py0 = max(SAFE, y - 9)
    px1 = min(W - SAFE, x + size[0] + 10)
    py1 = min(TAKEAWAY_Y - 12, y + size[1] + 10)
    pd.rectangle((px0, py0, px1, py1), outline=(*accent, 72), width=2)
    for yy in range(py0 + 16, py1 - 8, 13):
        pd.line((max(px0, px1 - 38), yy, px1, yy), fill=(*accent, 28), width=1)
    for xx in range(px0 + 12, min(px0 + 82, px1 - 5), 11):
        pd.line((xx, max(py0, py1 - 34), xx + 22, py1), fill=(*accent, 22), width=1)
    img.paste(plate, (0, 0), plate)

    fade = max(52, min(78, size[1] // 5))
    p, mask = feathered_portrait(path, crop, size, fade_bottom=fade)
    img.paste(p, xy, mask)


def common_canvas(data, speaker):
    ensure(1 <= int(data["slide_number"]) <= int(data["total_slides"]), "Invalid slide number.")
    accent = hex_rgb(speaker["accent"])
    img = Image.new("RGB", (W, H), PAPER)
    paper_texture(img)
    theme = {
        "NORA": "nora",
        "Johan Vosloo": "johan_vosloo",
        "Diane Sterling": "diane_sterling",
        "Kai Patel": "kai_patel",
        "Thabo Mokoena": "thabo_mokoena",
        "Amari Ndlovu": "amari_ndlovu",
    }.get(speaker.get("name"), "")
    editorial_atmosphere(
        img, accent, theme,
        variant=str(data.get("content_type") or data.get("layout_family") or "identity"),
        seed=int(data["slide_number"]),
    )
    apply_context_art(img, accent, data.get("context_art"), seed=int(data["slide_number"]))
    draw = ImageDraw.Draw(img)
    draw_frame(draw, accent, data["slide_number"], data["total_slides"])
    return img, draw, accent


def upper_left_stack(img, draw, accent, data, *, x, y, width, headline_bottom, deck_bottom, headline_lines=4, headline_start=54, headline_min=42, deck_lines=4, deck_start=24, deck_min=19):
    head_bottom = draw_headline(
        img, draw, data["headline"], accent, (x, y), width,
        max_lines=headline_lines, start=headline_start, minimum=headline_min,
        max_bottom=headline_bottom,
    )
    rule_y = head_bottom + 6
    draw.line((x, rule_y, x + width - 5, rule_y), fill=accent, width=4)
    deck_y = rule_y + 14
    deck_end = draw_deck(
        draw, data["deck"], (x, deck_y), width - 10,
        max_lines=deck_lines, start=deck_start, minimum=deck_min,
        max_bottom=deck_bottom,
    )
    return head_bottom, deck_end


def render_nora(root, data, speaker):
    img, draw, accent = common_canvas(data, speaker)
    _, deck_bottom = upper_left_stack(
        img, draw, accent, data,
        x=96, y=103, width=470,
        headline_bottom=270, deck_bottom=365,
        headline_lines=3, headline_start=56, headline_min=46,
        deck_lines=4, deck_start=25, deck_min=20,
    )
    ensure(deck_bottom <= 372, "NORA deck intrudes into quote region.")
    portrait(img, root, speaker, (610, 128), (350, 355))
    draw = ImageDraw.Draw(img)

    draw_quote(draw, data["quote"], speaker["name"], accent, (96, 390, 535, 548))
    draw_small_fact_list(
        draw, data["facts"], accent, (96, 575, 500, 870),
        heading="SYSTEM OBSERVATIONS", minimum=15, start=17,
    )

    # NORA identity: calm systems geometry, central axis, balanced quadrants.
    cx, cy = 755, 688
    draw.ellipse((cx - 84, cy - 84, cx + 84, cy + 84), outline=accent, width=4)
    centre_text(draw, "SYSTEM", (cx, cy - 10), font(25, bold=True, condensed=True), accent)
    centre_text(draw, "FRAME", (cx, cy + 18), font(25, bold=True, condensed=True), accent)
    draw.line((cx, 540, cx, 842), fill=accent, width=2)
    draw.line((602, cy, 908, cy), fill=accent, width=2)
    labels = data.get("mechanism", ["SIGNAL", "STATE", "FEEDBACK", "OUTCOME"])
    positions = [(650, 570), (860, 570), (650, 805), (860, 805)]
    for label, pos in zip(labels[:4], positions):
        draw.rounded_rectangle((pos[0]-58, pos[1]-28, pos[0]+58, pos[1]+28), radius=14, fill=PAPER, outline=accent, width=2)
        centre_text(draw, label, pos, font(12, bold=True, condensed=True), accent)
        arrow(draw, pos, (cx, cy), accent, width=2)

    draw_takeaway_band(draw, accent, data["takeaway"], label="NORA / SYNTHESIS")
    draw_footer(draw, accent)
    return img


def render_johan(root, data, speaker):
    img, draw, accent = common_canvas(data, speaker)
    portrait(img, root, speaker, (96, 138), (350, 390))
    draw = ImageDraw.Draw(img)

    _, deck_bottom = upper_left_stack(
        img, draw, accent, data,
        x=500, y=112, width=445,
        headline_bottom=286, deck_bottom=365,
        headline_lines=4, headline_start=53, headline_min=42,
        deck_lines=4, deck_start=23, deck_min=19,
    )
    quote_top = max(382, deck_bottom + 16)
    ensure(quote_top <= 405, "Johan headline/deck leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (500, quote_top, 940, 535))

    # Johan identity: rigid institutional spine, squared stages, containment/order.
    x = 265
    draw.text((130, 548), "INSTITUTIONAL SPINE", font=font(15, bold=True, condensed=True), fill=accent)
    draw.line((x, 571, x, 857), fill=accent, width=8)
    stages = data.get("mechanism", ["RULE", "AUTHORITY", "ENFORCEMENT", "TRUST"])
    ys = [598, 674, 750, 826]
    for idx, (label, yy) in enumerate(zip(stages[:4], ys), start=1):
        draw.rectangle((130, yy-23, 400, yy+23), fill=PAPER, outline=accent, width=3)
        draw.rectangle((130, yy-23, 171, yy+23), fill=accent)
        centre_text(draw, str(idx), (150, yy), font(16, bold=True, condensed=True), PAPER)
        draw.text((184, yy-12), label, font=font(16, bold=True, condensed=True), fill=accent)
        if yy != ys[-1]:
            arrow(draw, (x, yy+24), (x, yy+51), accent, width=3)

    draw_small_fact_list(
        draw, data["facts"], accent, (455, 565, 940, 870),
        heading="EVIDENCE / OVERSIGHT", minimum=15, start=17,
    )
    draw_takeaway_band(draw, accent, data["takeaway"], label="JOHAN / ORDER TEST")
    draw_footer(draw, accent)
    return img


def render_diane(root, data, speaker):
    img, draw, accent = common_canvas(data, speaker)
    _, deck_bottom = upper_left_stack(
        img, draw, accent, data,
        x=96, y=105, width=500,
        headline_bottom=270, deck_bottom=345,
        headline_lines=3, headline_start=54, headline_min=44,
        deck_lines=4, deck_start=24, deck_min=19,
    )
    portrait(img, root, speaker, (635, 132), (320, 350))
    draw = ImageDraw.Draw(img)

    quote_top = max(356, deck_bottom + 16)
    ensure(quote_top <= 382, "Diane headline/deck leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (96, quote_top, 565, 515))

    # Diane identity: economic dashboard + transmission grid.
    draw.text((96, 526), "MARKET / DELIVERY TRANSMISSION", font=font(17, bold=True, condensed=True), fill=accent)
    metrics = data.get("metrics", [
        {"label": "INPUT", "value": "PRICE"},
        {"label": "CHANNEL", "value": "FLOW"},
        {"label": "OUTCOME", "value": "DELIVERY"},
    ])
    x0, y0 = 96, 552
    card_w, gap, card_h = 270, 20, 88
    for i, item in enumerate(metrics[:3]):
        x = x0 + i * (card_w + gap)
        draw.rectangle((x, y0, x + card_w, y0 + card_h), fill=PAPER, outline=accent, width=2)
        draw.rectangle((x, y0, x + card_w, y0 + 25), fill=accent)
        centre_text(draw, item.get("label", "METRIC"), (x+card_w/2, y0+12), font(12, bold=True, condensed=True), PAPER)
        centre_text(draw, item.get("value", "—"), (x+card_w/2, y0+57), font(25, bold=True, serif=True), accent)

    fy = 684
    nodes = data.get("mechanism", ["CAPITAL", "CONTRACT", "SERVICE", "HOUSEHOLD"])
    xs = [135, 385, 635, 885]
    for i in range(3):
        arrow(draw, (xs[i]+55, fy), (xs[i+1]-55, fy), accent, width=4)
    for x, label in zip(xs, nodes[:4]):
        draw.rounded_rectangle((x-55, fy-28, x+55, fy+28), radius=6, fill=PAPER, outline=accent, width=3)
        centre_text(draw, label, (x, fy), font(12, bold=True, condensed=True), accent)

    draw_small_fact_list(
        draw, data["facts"], accent, (96, 724, 940, 875),
        heading="ECONOMIC CHECKS", minimum=15, start=17,
    )
    draw_takeaway_band(draw, accent, data["takeaway"], label="DIANE / PERFORMANCE TEST")
    draw_footer(draw, accent)
    return img


def render_kai(root, data, speaker):
    img, draw, accent = common_canvas(data, speaker)
    portrait(img, root, speaker, (96, 145), (335, 360))
    draw = ImageDraw.Draw(img)

    _, deck_bottom = upper_left_stack(
        img, draw, accent, data,
        x=485, y=108, width=455,
        headline_bottom=292, deck_bottom=365,
        headline_lines=4, headline_start=53, headline_min=42,
        deck_lines=4, deck_start=23, deck_min=19,
    )
    quote_top = max(382, deck_bottom + 16)
    ensure(quote_top <= 405, "Kai headline/deck leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (485, quote_top, 940, 530))

    draw_small_fact_list(
        draw, data["facts"], accent, (96, 555, 425, 870),
        heading="NETWORK SIGNALS", minimum=14, start=16,
    )

    # Kai identity: distributed network, circular nodes, feedback paths.
    centre = (690, 700)
    draw.ellipse((centre[0]-72, centre[1]-72, centre[0]+72, centre[1]+72), fill=PAPER, outline=accent, width=4)
    centre_text(draw, "NETWORK", centre, font(22, bold=True, condensed=True), accent)
    labels = data.get("mechanism", ["SENSOR", "MODEL", "NODE", "USER", "REPAIR"])
    ring = [(525, 620), (815, 585), (905, 710), (790, 825), (520, 815)]
    for i, (label, pos) in enumerate(zip(labels[:5], ring)):
        r = 44 if i % 2 == 0 else 36
        draw.ellipse((pos[0]-r, pos[1]-r, pos[0]+r, pos[1]+r), fill=PAPER, outline=accent, width=3)
        centre_text(draw, label, pos, font(11, bold=True, condensed=True), accent)
        draw.line((pos[0], pos[1], centre[0], centre[1]), fill=accent, width=2)
    draw.arc((470, 545, 930, 865), start=205, end=350, fill=accent, width=3)
    arrow(draw, (860, 838), (810, 856), accent, width=3)

    draw_takeaway_band(draw, accent, data["takeaway"], label="KAI / SYSTEM TEST")
    draw_footer(draw, accent)
    return img


def render_thabo(root, data, speaker):
    img, draw, accent = common_canvas(data, speaker)
    _, deck_bottom = upper_left_stack(
        img, draw, accent, data,
        x=96, y=104, width=840,
        headline_bottom=225, deck_bottom=292,
        headline_lines=3, headline_start=56, headline_min=44,
        deck_lines=3, deck_start=24, deck_min=19,
    )
    ensure(deck_bottom <= 300, "Thabo deck intrudes into evidence/quote row.")

    # Separate evidence and quote row: no text is allowed to sit on top of the portrait.
    draw_small_fact_list(
        draw, data["facts"], accent, (96, 300, 485, 500),
        heading="MATERIAL FACTS", minimum=15, start=17,
    )
    draw_quote(draw, data["quote"], speaker["name"], accent, (505, 300, 940, 500), large=True)

    portrait(img, root, speaker, (96, 515), (365, 355))
    draw = ImageDraw.Draw(img)

    # Thabo identity: material burden ledger, heavy stacked blocks, asymmetry.
    draw.text((500, 525), "WHO CARRIES THE BURDEN?", font=font(20, bold=True, condensed=True), fill=accent)
    burdens = data.get("mechanism", ["COST", "TIME", "RISK", "HOUSEHOLD"])
    yy = 565
    widths = [380, 330, 285, 240]
    for i, (label, bw) in enumerate(zip(burdens[:4], widths), start=1):
        draw.rectangle((500, yy, 500+bw, yy+52), fill=accent if i in (1, 4) else PAPER, outline=accent, width=3)
        fill = PAPER if i in (1, 4) else accent
        draw.text((516, yy+11), f"{i}. {label}", font=font(18, bold=True, condensed=True), fill=fill)
        yy += 64
    draw.line((480, 555, 480, 850), fill=accent, width=7)

    draw_takeaway_band(draw, accent, data["takeaway"], label="THABO / MATERIAL TEST")
    draw_footer(draw, accent)
    return img


def render_amari(root, data, speaker):
    img, draw, accent = common_canvas(data, speaker)
    _, deck_bottom = upper_left_stack(
        img, draw, accent, data,
        x=96, y=106, width=500,
        headline_bottom=285, deck_bottom=365,
        headline_lines=4, headline_start=53, headline_min=42,
        deck_lines=4, deck_start=23, deck_min=19,
    )
    portrait(img, root, speaker, (620, 135), (335, 385))
    draw = ImageDraw.Draw(img)

    quote_top = max(382, deck_bottom + 16)
    ensure(quote_top <= 407, "Amari headline/deck leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (96, quote_top, 555, 535))

    draw.text((96, 566), "REGION / MEMORY / DIGNITY", font=font(18, bold=True, condensed=True), fill=accent)
    draw_small_fact_list(
        draw, data["facts"], accent, (96, 590, 455, 872),
        heading="HUMAN / REGIONAL CONTEXT", minimum=14, start=16,
    )

    # Amari identity: organic regional arcs + continuity/memory nodes.
    draw.arc((515, 545, 930, 865), start=190, end=350, fill=accent, width=4)
    draw.arc((565, 590, 875, 820), start=175, end=365, fill=accent, width=2)
    nodes = data.get("mechanism", ["PLACE", "MEMORY", "RIGHTS", "SOLIDARITY"])
    positions = [(560, 690), (690, 605), (850, 690), (715, 820)]
    for label, pos in zip(nodes[:4], positions):
        draw.ellipse((pos[0]-48, pos[1]-48, pos[0]+48, pos[1]+48), fill=PAPER, outline=accent, width=3)
        centre_text(draw, label, pos, font(11, bold=True, condensed=True), accent)
    draw.line((602, 665, 650, 625), fill=accent, width=2)
    draw.line((735, 625, 805, 668), fill=accent, width=2)
    draw.line((825, 730, 750, 790), fill=accent, width=2)
    draw.line((680, 790, 595, 730), fill=accent, width=2)

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


def validate_input(data: dict):
    required = {"slide_number", "total_slides", "speaker", "headline", "deck", "quote", "facts", "takeaway"}
    missing = sorted(required - set(data))
    ensure(not missing, f"Missing required input fields: {', '.join(missing)}")
    ensure(isinstance(data["facts"], list) and 1 <= len(data["facts"]) <= 6, "facts must contain 1-6 items.")


def render(input_path: Path, output_path: Path):
    root = Path(__file__).resolve().parents[1]
    data = json.loads(input_path.read_text(encoding="utf-8"))
    validate_input(data)
    characters = json.loads((root / "config/characters.json").read_text(encoding="utf-8"))
    speaker_key = data["speaker"]
    if speaker_key not in RENDERERS:
        raise ValueError(f"No identity renderer for {speaker_key}")
    ensure(speaker_key in characters, f"Speaker missing from config/characters.json: {speaker_key}")
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
