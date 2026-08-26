from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

try:
    from .editorial_primitives import (
        INK,
        MUTED,
        PAPER,
        SAFE,
        W,
        LayoutError,
        arrow,
        centre_text,
        draw_deck,
        draw_footer,
        draw_frame,
        draw_headline,
        draw_lines,
        draw_quote,
        draw_small_fact_list,
        draw_takeaway_band,
        ensure,
        fit_wrapped,
        font,
        hex_rgb,
        paper_texture,
        editorial_atmosphere,
    )
    from .render_identity_slide import portrait, render_amari as render_regional_memory
except ImportError:
    from editorial_primitives import (
        INK, MUTED, PAPER, SAFE, W, LayoutError, arrow, centre_text,
        draw_deck, draw_footer, draw_frame, draw_headline, draw_lines,
        draw_quote, draw_small_fact_list, draw_takeaway_band, ensure,
        fit_wrapped, font, hex_rgb, paper_texture, editorial_atmosphere,
    )
    from render_identity_slide import portrait, render_amari as render_regional_memory

try:
    from .contextual_illustrations import apply_context_art
except ImportError:
    from contextual_illustrations import apply_context_art


FAMILIES = {
    "regional_memory",
    "dignity_pathway",
    "humanitarian_map",
    "cross_border_bridge",
    "cultural_landscape",
}
TAKEAWAY_Y = 894
CONTENT_BOTTOM = 875


def new_canvas(data: dict, speaker: dict):
    accent = hex_rgb(speaker["accent"])
    img = Image.new("RGB", (1080, 1080), PAPER)
    paper_texture(img)
    editorial_atmosphere(
        img, accent, "amari_ndlovu",
        variant=str(data.get("content_type") or data.get("layout_family") or "family"),
        seed=int(data["slide_number"]),
    )
    apply_context_art(img, accent, data.get("context_art"), seed=int(data["slide_number"]))
    draw = ImageDraw.Draw(img)
    draw_frame(draw, accent, int(data["slide_number"]), int(data["total_slides"]))
    return img, draw, accent


def top_stack(
    img,
    draw,
    accent,
    data,
    *,
    x,
    y,
    width,
    headline_bottom,
    deck_bottom,
    headline_lines=4,
    headline_start=53,
    headline_min=42,
    deck_lines=4,
    deck_start=23,
    deck_min=19,
):
    head_bottom = draw_headline(
        img,
        draw,
        data["headline"],
        accent,
        (x, y),
        width,
        max_lines=headline_lines,
        start=headline_start,
        minimum=headline_min,
        max_bottom=headline_bottom,
    )
    rule_y = head_bottom + 7
    draw.line((x, rule_y, x + width - 5, rule_y), fill=accent, width=4)
    deck_end = draw_deck(
        draw,
        data["deck"],
        (x, rule_y + 14),
        width - 8,
        max_lines=deck_lines,
        start=deck_start,
        minimum=deck_min,
        max_bottom=deck_bottom,
    )
    return deck_end


def draw_path_node(draw, accent, centre, label: str, index: int, *, strong=False):
    x, y = centre
    r = 43 if strong else 38
    draw.ellipse((x-r, y-r, x+r, y+r), fill=accent if strong else PAPER, outline=accent, width=3)
    centre_text(draw, str(index), (x, y-10), font(13, bold=True, serif=True), PAPER if strong else accent)
    lf, lines = fit_wrapped(
        draw, label, 74, 2, 11, 9,
        max_height=27, spacing=0, label="Amari pathway node", bold=True, condensed=True,
    )
    y0 = y + 5 - (len(lines)-1)*5
    for line in lines:
        centre_text(draw, line, (x, y0), lf, PAPER if strong else accent)
        y0 += 11


def render_dignity_pathway(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)
    deck_bottom = top_stack(
        img, draw, accent, data,
        x=96, y=104, width=525,
        headline_bottom=275, deck_bottom=355,
        headline_lines=4, headline_start=54, headline_min=42,
        deck_lines=4, deck_start=23, deck_min=19,
    )
    portrait(img, root, speaker, (665, 125), (275, 315))
    draw = ImageDraw.Draw(img)
    quote_top = max(374, deck_bottom + 16)
    ensure(quote_top <= 398, "Amari dignity pathway leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (96, quote_top, 565, 530))
    draw_small_fact_list(
        draw, data["facts"], accent, (96, 565, 455, 870),
        heading="DIGNITY CHECKS", minimum=14, start=16,
    )

    mechanism = data.get("mechanism")
    ensure(isinstance(mechanism, list) and 4 <= len(mechanism) <= 5,
           "dignity_pathway requires 4-5 mechanism labels.")
    draw.text((510, 560), "THE DIGNITY PATHWAY", font=font(18, bold=True, condensed=True), fill=accent)
    draw.line((510, 588, 940, 588), fill=accent, width=2)

    points = [(555, 760), (645, 650), (755, 720), (845, 620), (910, 760)][:len(mechanism)]
    for idx in range(len(points)-1):
        p0, p1 = points[idx], points[idx+1]
        mid = ((p0[0]+p1[0])//2, (p0[1]+p1[1])//2 - 24)
        draw.line((p0, mid, p1), fill=accent, width=3)
        arrow(draw, mid, p1, accent, width=2)
    for idx, (label, point) in enumerate(zip(mechanism, points), start=1):
        draw_path_node(draw, accent, point, str(label), idx, strong=(idx == len(points)))

    draw.arc((530, 595, 930, 860), start=195, end=340, fill=accent, width=2)
    centre_text(draw, "RECOGNITION MUST SURVIVE EVERY HANDOFF", (725, 850), font(11, bold=True, condensed=True), accent)
    draw_takeaway_band(draw, accent, data["takeaway"], label="AMARI / DIGNITY PATHWAY")
    draw_footer(draw, accent)
    return img


def draw_region_shape(draw, accent, box):
    x0, y0, x1, y1 = box
    pts = [
        (x0+40, y0+80), (x0+120, y0+20), (x0+230, y0+44),
        (x0+330, y0+15), (x0+430, y0+90), (x0+395, y0+175),
        (x0+450, y0+245), (x0+340, y0+290), (x0+260, y0+250),
        (x0+190, y0+310), (x0+95, y0+260), (x0+20, y0+185),
    ]
    draw.polygon(pts, fill=(238, 231, 214), outline=accent)
    draw.line(pts + [pts[0]], fill=accent, width=3)
    return pts


def render_humanitarian_map(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)
    deck_bottom = top_stack(
        img, draw, accent, data,
        x=96, y=104, width=835,
        headline_bottom=235, deck_bottom=315,
        headline_lines=3, headline_start=56, headline_min=44,
        deck_lines=3, deck_start=24, deck_min=19,
    )
    ensure(deck_bottom <= 322, "Amari humanitarian map deck intrudes into content row.")

    portrait(img, root, speaker, (96, 350), (300, 305))
    draw = ImageDraw.Draw(img)
    draw_quote(draw, data["quote"], speaker["name"], accent, (430, 348, 940, 500), large=True)
    draw_small_fact_list(
        draw, data["facts"], accent, (96, 665, 410, 875),
        heading="HUMAN / REGIONAL CONTEXT", minimum=12, start=15,
    )

    nodes = data.get("map_nodes")
    ensure(isinstance(nodes, list) and len(nodes) == 4, "humanitarian_map requires exactly four map_nodes.")
    draw.text((430, 525), "SCHEMATIC REGIONAL ACCESS MAP", font=font(18, bold=True, condensed=True), fill=accent)
    draw.text((430, 549), "NOT TO SCALE — RELATIONSHIPS, NOT BORDERS", font=font(10, bold=True, serif=True), fill=MUTED)
    map_box = (430, 575, 940, 860)
    draw_region_shape(draw, accent, map_box)

    plotted = []
    for idx, item in enumerate(nodes, start=1):
        nx = float(item.get("x", 0.5))
        ny = float(item.get("y", 0.5))
        ensure(0.08 <= nx <= 0.92 and 0.08 <= ny <= 0.92, "Amari map node coordinates must stay inside 0.08-0.92.")
        x = int(map_box[0] + nx * (map_box[2]-map_box[0]))
        y = int(map_box[1] + ny * (map_box[3]-map_box[1]))
        plotted.append((x, y))
        draw.ellipse((x-18, y-18, x+18, y+18), fill=accent, outline=PAPER, width=3)
        centre_text(draw, str(idx), (x, y), font(11, bold=True, serif=True), PAPER)
        label = str(item.get("label", f"PLACE {idx}"))
        lf, lines = fit_wrapped(draw, label, 118, 2, 12, 9, max_height=26, spacing=0, label="Amari map label", bold=True, condensed=True)
        ylab = y + 24
        for line in lines:
            centre_text(draw, line, (x, ylab), lf, accent)
            ylab += 12

    for idx in range(len(plotted)-1):
        arrow(draw, plotted[idx], plotted[idx+1], accent, width=2)
    draw.arc((500, 600, 900, 845), start=200, end=345, fill=accent, width=2)
    draw_takeaway_band(draw, accent, data["takeaway"], label="AMARI / HUMANITARIAN MAP")
    draw_footer(draw, accent)
    return img


def render_cross_border_bridge(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)
    portrait(img, root, speaker, (96, 140), (305, 330))
    draw = ImageDraw.Draw(img)
    deck_bottom = top_stack(
        img, draw, accent, data,
        x=440, y=104, width=500,
        headline_bottom=280, deck_bottom=365,
        headline_lines=4, headline_start=52, headline_min=41,
        deck_lines=4, deck_start=23, deck_min=19,
    )
    quote_top = max(380, deck_bottom + 14)
    ensure(quote_top <= 404, "Amari cross-border bridge leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (440, quote_top, 940, 530), large=True)
    draw_small_fact_list(
        draw, data["facts"], accent, (96, 535, 400, 870),
        heading="CROSS-BORDER CONTEXT", minimum=14, start=16,
    )

    bridge = data.get("bridge")
    ensure(isinstance(bridge, list) and len(bridge) == 4, "cross_border_bridge requires exactly four bridge labels.")
    draw.text((440, 560), "A BRIDGE BETWEEN LOCAL LIFE AND REGIONAL SOLIDARITY", font=font(17, bold=True, condensed=True), fill=accent)
    draw.line((440, 588, 940, 588), fill=accent, width=2)

    # Two shores and an open border/gap between them.
    draw.polygon([(455, 815), (455, 690), (590, 650), (630, 815)], fill=(238, 231, 214), outline=accent)
    draw.polygon([(750, 815), (790, 650), (925, 690), (925, 815)], fill=(238, 231, 214), outline=accent)
    draw.line((690, 620, 690, 840), fill=MUTED, width=2)
    draw.text((664, 835), "BORDER", font=font(10, bold=True, condensed=True), fill=MUTED)

    # Bridge arch.
    draw.arc((565, 610, 815, 790), start=190, end=350, fill=accent, width=6)
    deck_y = 730
    draw.line((585, deck_y, 795, deck_y), fill=accent, width=6)
    supports = [610, 665, 720, 775]
    for x in supports:
        draw.line((x, deck_y, x, 790), fill=accent, width=3)
    label_pos = [(530, 630), (630, 610), (750, 610), (850, 630)]
    for idx, (label, pos) in enumerate(zip(bridge, label_pos), start=1):
        draw.rounded_rectangle((pos[0]-55, pos[1]-25, pos[0]+55, pos[1]+25), radius=13, fill=PAPER, outline=accent, width=2)
        lf, lines = fit_wrapped(draw, str(label), 96, 2, 11, 9, max_height=24, spacing=0, label="Amari bridge label", bold=True, condensed=True)
        yy = pos[1] - (len(lines)-1)*5
        for line in lines:
            centre_text(draw, line, (pos[0], yy), lf, accent)
            yy += 11
        if idx < len(label_pos):
            arrow(draw, (pos[0]+56, pos[1]), (label_pos[idx][0]-56, label_pos[idx][1]), accent, width=2)

    centre_text(draw, "MOVEMENT WITHOUT RECOGNITION IS NOT SOLIDARITY", (690, 855), font(11, bold=True, condensed=True), accent)
    draw_takeaway_band(draw, accent, data["takeaway"], label="AMARI / CROSS-BORDER BRIDGE")
    draw_footer(draw, accent)
    return img


def render_cultural_landscape(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)
    deck_bottom = top_stack(
        img, draw, accent, data,
        x=96, y=104, width=560,
        headline_bottom=270, deck_bottom=355,
        headline_lines=4, headline_start=54, headline_min=42,
        deck_lines=4, deck_start=23, deck_min=19,
    )
    portrait(img, root, speaker, (690, 125), (250, 290))
    draw = ImageDraw.Draw(img)
    quote_top = max(370, deck_bottom + 14)
    ensure(quote_top <= 395, "Amari cultural landscape leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (96, quote_top, 620, 520))

    landscape = data.get("landscape")
    ensure(isinstance(landscape, list) and len(landscape) == 4, "cultural_landscape requires exactly four landscape layers.")
    ensure(len(data["facts"]) >= 4, "cultural_landscape requires at least four facts, one per layer.")
    draw.text((96, 548), "THE CULTURAL LANDSCAPE OF DELIVERY", font=font(19, bold=True, condensed=True), fill=accent)
    draw.line((96, 578, 940, 578), fill=accent, width=2)

    y = 595
    layer_h = 66
    fills = [PAPER, (239, 233, 220), PAPER, (233, 225, 205)]
    for idx, (layer, fact) in enumerate(zip(landscape, data["facts"][:4]), start=1):
        x0 = 96 + (idx-1)*18
        x1 = 940 - (idx-1)*18
        draw.rounded_rectangle((x0, y, x1, y+layer_h), radius=8, fill=fills[idx-1], outline=accent, width=2)
        draw.rectangle((x0, y, x0+145, y+layer_h), fill=accent if idx in (1, 4) else PAPER, outline=accent, width=2)
        label_fill = PAPER if idx in (1, 4) else accent
        lf, llines = fit_wrapped(draw, str(layer), 125, 2, 14, 11, max_height=42, spacing=0, label="Amari landscape label", bold=True, condensed=True)
        yy = y + 18
        for line in llines:
            centre_text(draw, line, (x0+72, yy), lf, label_fill)
            yy += 14
        ff, flines = fit_wrapped(draw, str(fact), x1-(x0+165)-88, 3, 15, 12, max_height=48, spacing=1, label="Amari landscape fact", serif=True)
        draw_lines(draw, flines, (x0+165, y+13), ff, INK, spacing=1)
        y += 70

    # Organic continuity line through all layers.
    pts = [(900, 607), (875, 672), (895, 742), (870, 812), (900, 852)]
    draw.line(pts, fill=accent, width=3)
    for p in pts[1:-1]:
        draw.ellipse((p[0]-5, p[1]-5, p[0]+5, p[1]+5), fill=accent)
    centre_text(draw, "PLACE → MEMORY → RECOGNITION → DIGNITY", (520, 860), font(12, bold=True, condensed=True), accent)
    draw_takeaway_band(draw, accent, data["takeaway"], label="AMARI / CULTURAL LANDSCAPE")
    draw_footer(draw, accent)
    return img


RENDERERS = {
    "regional_memory": render_regional_memory,
    "dignity_pathway": render_dignity_pathway,
    "humanitarian_map": render_humanitarian_map,
    "cross_border_bridge": render_cross_border_bridge,
    "cultural_landscape": render_cultural_landscape,
}


def validate_input(data: dict):
    required = {
        "slide_number",
        "total_slides",
        "speaker",
        "layout_family",
        "headline",
        "deck",
        "quote",
        "facts",
        "takeaway",
    }
    missing = sorted(required - set(data))
    ensure(not missing, f"Missing Amari layout fields: {', '.join(missing)}")
    ensure(data["speaker"] == "amari_ndlovu", "Amari layout family only accepts speaker=amari_ndlovu.")
    ensure(data["layout_family"] in FAMILIES, f"Unknown Amari layout family: {data['layout_family']}")
    ensure(2 <= int(data["slide_number"]) <= int(data["total_slides"]) - 1,
           "Amari family layouts are standard slides 2-19, not episode opener/closer.")
    ensure(isinstance(data["facts"], list) and 2 <= len(data["facts"]) <= 5,
           "Amari family requires 2-5 facts.")


def render(input_path: Path, output_path: Path):
    root = Path(__file__).resolve().parents[1]
    data = json.loads(input_path.read_text(encoding="utf-8"))
    validate_input(data)

    presets = json.loads((root / "config/layout_presets.json").read_text(encoding="utf-8"))
    approved = set(presets["amari_ndlovu"]["approved_families"])
    ensure(data["layout_family"] in approved,
           f"Amari layout not approved in config/layout_presets.json: {data['layout_family']}")

    characters = json.loads((root / "config/characters.json").read_text(encoding="utf-8"))
    speaker = characters["amari_ndlovu"]
    img = RENDERERS[data["layout_family"]](root, data, speaker)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG", optimize=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    render(args.input, args.output)
    print(f"Generated {args.output.resolve()}")
