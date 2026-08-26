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
    from .render_identity_slide import portrait, render_diane as render_market_grid
except ImportError:
    from editorial_primitives import (
        INK, MUTED, PAPER, SAFE, W, LayoutError, arrow, centre_text,
        draw_deck, draw_footer, draw_frame, draw_headline, draw_lines,
        draw_quote, draw_small_fact_list, draw_takeaway_band, ensure,
        fit_wrapped, font, hex_rgb, paper_texture, editorial_atmosphere,
    )
    from render_identity_slide import portrait, render_diane as render_market_grid

try:
    from .contextual_illustrations import apply_context_art
except ImportError:
    from contextual_illustrations import apply_context_art


FAMILIES = {
    "market_grid",
    "transmission_chain",
    "fiscal_flow",
    "portfolio_pipeline",
    "regional_economy",
}


def new_canvas(data: dict, speaker: dict):
    accent = hex_rgb(speaker["accent"])
    img = Image.new("RGB", (1080, 1080), PAPER)
    paper_texture(img)
    editorial_atmosphere(
        img, accent, "diane_sterling",
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


def draw_metric_card(draw, accent, box, label: str, value: str, *, dark=False, note: str = ""):
    x0, y0, x1, y1 = box
    ensure(x0 >= SAFE and x1 <= W - SAFE and y0 >= SAFE and y1 <= 875,
           f"Diane metric card crosses safe area: {box}")
    draw.rounded_rectangle(box, radius=6, fill=accent if dark else PAPER, outline=accent, width=2)
    top_fill = PAPER if dark else accent
    draw.rectangle((x0, y0, x1, y0 + 29), fill=top_fill)
    centre_text(
        draw,
        str(label).upper(),
        ((x0 + x1) / 2, y0 + 14),
        font(13, bold=True, condensed=True),
        accent if dark else PAPER,
    )
    vf, vlines = fit_wrapped(
        draw,
        str(value),
        x1 - x0 - 20,
        2,
        24,
        16,
        max_height=54,
        spacing=0,
        label="Diane metric value",
        bold=True,
        serif=True,
    )
    value_fill = PAPER if dark else accent
    start_y = y0 + 42
    for line in vlines:
        centre_text(draw, line, ((x0 + x1) / 2, start_y + 12), vf, value_fill)
        start_y += 25
    if note:
        nf, nlines = fit_wrapped(
            draw,
            note,
            x1 - x0 - 20,
            2,
            13,
            11,
            max_height=38,
            spacing=0,
            label="Diane metric note",
            serif=True,
        )
        draw_lines(draw, nlines, (x0 + 10, y1 - 40), nf, PAPER if dark else INK, spacing=0)


def render_transmission_chain(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)
    deck_bottom = top_stack(
        img, draw, accent, data,
        x=96, y=104, width=535,
        headline_bottom=265, deck_bottom=350,
        headline_lines=3, headline_start=54, headline_min=43,
        deck_lines=4, deck_start=23, deck_min=19,
    )
    portrait(img, root, speaker, (680, 125), (260, 300))
    draw = ImageDraw.Draw(img)
    quote_top = max(366, deck_bottom + 16)
    ensure(quote_top <= 390, "Diane transmission chain leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (96, quote_top, 585, 515))

    stages = list(data.get("stages", []))
    ensure(3 <= len(stages) <= 5, "transmission_chain requires 3-5 stages.")
    stages = stages[:4]
    draw.text((96, 530), "TRANSMISSION CHAIN", font=font(18, bold=True, condensed=True), fill=accent)

    x0, y0, gap = 96, 560, 14
    available = 844
    card_w = int((available - gap * (len(stages) - 1)) / len(stages))
    boxes = []
    for idx, item in enumerate(stages):
        x = x0 + idx * (card_w + gap)
        box = (x, y0, x + card_w, y0 + 125)
        boxes.append(box)
        draw_metric_card(
            draw,
            accent,
            box,
            str(item.get("label", f"STAGE {idx+1}")),
            str(item.get("value", "—")),
            dark=(idx == len(stages) - 1),
            note=str(item.get("note", "")),
        )
        if idx > 0:
            prev = boxes[idx - 1]
            arrow(draw, (prev[2] + 2, y0 + 68), (box[0] - 3, y0 + 68), accent, width=3)

    centre_text(draw, "VALUE MUST SURVIVE EVERY HANDOFF", (518, 702), font(14, bold=True, condensed=True), accent)
    draw.line((96, 716, 940, 716), fill=accent, width=2)
    draw_small_fact_list(
        draw,
        data["facts"],
        accent,
        (96, 728, 940, 875),
        heading="DELIVERY CHECKS",
        minimum=14,
        start=16,
    )
    draw_takeaway_band(draw, accent, data["takeaway"], label="DIANE / TRANSMISSION TEST")
    draw_footer(draw, accent)
    return img


def render_fiscal_flow(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)
    portrait(img, root, speaker, (96, 132), (300, 330))
    draw = ImageDraw.Draw(img)
    deck_bottom = top_stack(
        img, draw, accent, data,
        x=445, y=108, width=495,
        headline_bottom=280, deck_bottom=352,
        headline_lines=4, headline_start=52, headline_min=41,
        deck_lines=4, deck_start=23, deck_min=19,
    )
    quote_top = max(372, deck_bottom + 16)
    ensure(quote_top <= 398, "Diane fiscal flow leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (445, quote_top, 940, 520))

    flows = list(data.get("flows", []))
    ensure(len(flows) == 4, "fiscal_flow requires exactly four flow items.")
    total = str(data.get("total", "100%"))

    draw.text((96, 545), "FISCAL FLOW", font=font(18, bold=True, condensed=True), fill=accent)
    draw_small_fact_list(
        draw,
        data["facts"],
        accent,
        (96, 575, 392, 870),
        heading="FISCAL SIGNALS",
        minimum=14,
        start=16,
    )

    # Central allocation reservoir with incoming budget and proportional output rails.
    cx, cy = 625, 692
    draw.rounded_rectangle((520, 620, 730, 762), radius=8, fill=PAPER, outline=accent, width=4)
    draw.rectangle((520, 620, 730, 652), fill=accent)
    centre_text(draw, "ALLOCATED", (625, 636), font(13, bold=True, condensed=True), PAPER)
    centre_text(draw, total, (625, 698), font(32, bold=True, serif=True), accent)
    centre_text(draw, "PUBLIC CAPITAL", (625, 735), font(12, bold=True, condensed=True), MUTED)
    arrow(draw, (430, 692), (510, 692), accent, width=5)
    draw.text((412, 650), "BUDGET", font=font(13, bold=True, condensed=True), fill=accent)

    ys = [584, 660, 736, 812]
    for idx, (item, yy) in enumerate(zip(flows, ys)):
        share = float(item.get("share", 25))
        share = max(5.0, min(100.0, share))
        rail_w = max(2, int(2 + share / 12))
        arrow(draw, (738, cy), (784, yy), accent, width=rail_w)
        draw.rounded_rectangle((792, yy - 28, 940, yy + 28), radius=5, fill=PAPER, outline=accent, width=2)
        centre_text(draw, str(item.get("label", f"FLOW {idx+1}")).upper(), (850, yy - 9), font(11, bold=True, condensed=True), accent)
        centre_text(draw, str(item.get("value", f"{share:.0f}%")), (866, yy + 12), font(15, bold=True, serif=True), INK)

    draw_takeaway_band(draw, accent, data["takeaway"], label="DIANE / FISCAL TEST")
    draw_footer(draw, accent)
    return img


def render_portfolio_pipeline(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)
    deck_bottom = top_stack(
        img, draw, accent, data,
        x=96, y=104, width=560,
        headline_bottom=262, deck_bottom=345,
        headline_lines=3, headline_start=54, headline_min=43,
        deck_lines=4, deck_start=23, deck_min=19,
    )
    portrait(img, root, speaker, (700, 125), (240, 285))
    draw = ImageDraw.Draw(img)
    quote_top = max(360, deck_bottom + 16)
    ensure(quote_top <= 385, "Diane portfolio pipeline leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (96, quote_top, 610, 505))

    portfolio = data.get("portfolio")
    ensure(isinstance(portfolio, list) and len(portfolio) == 4, "portfolio_pipeline requires exactly four portfolio items.")
    draw.text((96, 530), "PORTFOLIO PIPELINE", font=font(18, bold=True, condensed=True), fill=accent)

    x0, y0, cell_w, cell_h, gap = 96, 560, 405, 125, 14
    for idx, item in enumerate(portfolio):
        row, col = divmod(idx, 2)
        x = x0 + col * (cell_w + gap)
        y = y0 + row * (cell_h + gap)
        draw.rounded_rectangle((x, y, x + cell_w, y + cell_h), radius=7, fill=PAPER, outline=accent, width=2)
        status = str(item.get("status", "OPEN")).upper()
        draw.rectangle((x, y, x + 112, y + 31), fill=accent if idx in (1, 3) else PAPER, outline=accent, width=2)
        centre_text(draw, status, (x + 56, y + 15), font(12, bold=True, condensed=True), PAPER if idx in (1, 3) else accent)
        project = str(item.get("project", f"PROJECT {idx+1}"))
        pf, plines = fit_wrapped(draw, project, 255, 2, 17, 13, max_height=46, spacing=0, label="portfolio project", bold=True, serif=True)
        draw_lines(draw, plines, (x + 130, y + 9), pf, INK, spacing=0)
        value = str(item.get("value", "—"))
        centre_text(draw, value, (x + 78, y + 76), font(24, bold=True, serif=True), accent)
        note = str(item.get("note", ""))
        nf, nlines = fit_wrapped(draw, note, cell_w - 170, 3, 14, 11, max_height=52, spacing=1, label="portfolio note", serif=True)
        draw_lines(draw, nlines, (x + 145, y + 63), nf, MUTED, spacing=1)

    # Conversion rail under the portfolio makes the family read as pipeline, not dashboard.
    rail_y = 845
    labels = list(data.get("mechanism", ["APPROVE", "PROCURE", "BUILD", "DELIVER"]))[:4]
    xs = [145, 390, 635, 880]
    for i in range(3):
        arrow(draw, (xs[i] + 45, rail_y), (xs[i + 1] - 45, rail_y), accent, width=3)
    for x, label in zip(xs, labels):
        draw.rounded_rectangle((x - 45, rail_y - 20, x + 45, rail_y + 20), radius=5, fill=PAPER, outline=accent, width=2)
        centre_text(draw, str(label).upper(), (x, rail_y), font(11, bold=True, condensed=True), accent)

    draw_takeaway_band(draw, accent, data["takeaway"], label="DIANE / PORTFOLIO TEST")
    draw_footer(draw, accent)
    return img


def render_regional_economy(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)
    portrait(img, root, speaker, (96, 135), (285, 315))
    draw = ImageDraw.Draw(img)
    deck_bottom = top_stack(
        img, draw, accent, data,
        x=430, y=106, width=510,
        headline_bottom=270, deck_bottom=350,
        headline_lines=4, headline_start=52, headline_min=41,
        deck_lines=4, deck_start=23, deck_min=19,
    )
    quote_top = max(368, deck_bottom + 16)
    ensure(quote_top <= 396, "Diane regional economy leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (430, quote_top, 940, 520))

    regions = data.get("regions")
    ensure(isinstance(regions, list) and len(regions) == 4, "regional_economy requires exactly four regions.")
    draw_small_fact_list(
        draw,
        data["facts"],
        accent,
        (96, 548, 400, 870),
        heading="REGIONAL SIGNALS",
        minimum=14,
        start=16,
    )

    draw.text((450, 548), "REGIONAL ECONOMY", font=font(18, bold=True, condensed=True), fill=accent)
    hub = (710, 713)
    draw.ellipse((hub[0] - 72, hub[1] - 72, hub[0] + 72, hub[1] + 72), fill=PAPER, outline=accent, width=4)
    centre_text(draw, "NATIONAL", (hub[0], hub[1] - 11), font(16, bold=True, condensed=True), accent)
    centre_text(draw, "MARKET", (hub[0], hub[1] + 13), font(18, bold=True, serif=True), accent)

    positions = [(520, 620), (845, 615), (875, 815), (525, 820)]
    for idx, (item, pos) in enumerate(zip(regions, positions)):
        x, y = pos
        draw.rounded_rectangle((x - 78, y - 46, x + 78, y + 46), radius=8, fill=PAPER, outline=accent, width=2)
        centre_text(draw, str(item.get("name", f"REGION {idx+1}")).upper(), (x, y - 20), font(12, bold=True, condensed=True), accent)
        centre_text(draw, str(item.get("value", "—")), (x, y + 3), font(18, bold=True, serif=True), INK)
        note = str(item.get("note", ""))
        nf, nlines = fit_wrapped(draw, note, 135, 2, 11, 9, max_height=30, spacing=0, label="regional note", serif=True)
        if nlines:
            centre_text(draw, nlines[0], (x, y + 28), nf, MUTED)
        # Draw bidirectional-looking trade link by line + arrow into the hub.
        arrow(draw, (x, y), hub, accent, width=2)

    draw.arc((462, 562, 925, 866), start=205, end=345, fill=accent, width=2)
    centre_text(draw, "GROWTH IS A NETWORK OF PLACES, NOT ONE NATIONAL NUMBER", (700, 874), font(11, bold=True, condensed=True), accent)

    draw_takeaway_band(draw, accent, data["takeaway"], label="DIANE / REGIONAL TEST")
    draw_footer(draw, accent)
    return img


RENDERERS = {
    "market_grid": render_market_grid,
    "transmission_chain": render_transmission_chain,
    "fiscal_flow": render_fiscal_flow,
    "portfolio_pipeline": render_portfolio_pipeline,
    "regional_economy": render_regional_economy,
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
    ensure(not missing, f"Missing Diane layout fields: {', '.join(missing)}")
    ensure(data["speaker"] == "diane_sterling", "Diane layout family only accepts speaker=diane_sterling.")
    ensure(data["layout_family"] in FAMILIES, f"Unknown Diane layout family: {data['layout_family']}")
    ensure(2 <= int(data["slide_number"]) <= int(data["total_slides"]) - 1,
           "Diane family layouts are standard slides 2-19, not episode opener/closer.")
    ensure(isinstance(data["facts"], list) and 2 <= len(data["facts"]) <= 5,
           "Diane family requires 2-5 facts.")


def render(input_path: Path, output_path: Path):
    root = Path(__file__).resolve().parents[1]
    data = json.loads(input_path.read_text(encoding="utf-8"))
    validate_input(data)

    presets = json.loads((root / "config/layout_presets.json").read_text(encoding="utf-8"))
    approved = set(presets["diane_sterling"]["approved_families"])
    ensure(data["layout_family"] in approved,
           f"Diane layout not approved in config/layout_presets.json: {data['layout_family']}")

    characters = json.loads((root / "config/characters.json").read_text(encoding="utf-8"))
    speaker = characters["diane_sterling"]
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
