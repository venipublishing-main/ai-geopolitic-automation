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
    from .render_identity_slide import portrait, render_thabo as render_burden_ledger
except ImportError:
    from editorial_primitives import (
        INK, MUTED, PAPER, SAFE, W, LayoutError, arrow, centre_text,
        draw_deck, draw_footer, draw_frame, draw_headline, draw_lines,
        draw_quote, draw_small_fact_list, draw_takeaway_band, ensure,
        fit_wrapped, font, hex_rgb, paper_texture, editorial_atmosphere,
    )
    from render_identity_slide import portrait, render_thabo as render_burden_ledger

try:
    from .contextual_illustrations import apply_context_art
except ImportError:
    from contextual_illustrations import apply_context_art


FAMILIES = {
    "burden_ledger",
    "material_chain",
    "structural_gap",
    "continuity_pressure",
}
TAKEAWAY_Y = 894
CONTENT_BOTTOM = 875


def new_canvas(data: dict, speaker: dict):
    accent = hex_rgb(speaker["accent"])
    img = Image.new("RGB", (1080, 1080), PAPER)
    paper_texture(img)
    editorial_atmosphere(
        img, accent, "thabo_mokoena",
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


def draw_stage_card(draw, accent, box, number: int, label: str, note: str, *, blocked=False, final=False):
    x0, y0, x1, y1 = box
    ensure(x0 >= SAFE and x1 <= W - SAFE and y0 >= SAFE and y1 <= CONTENT_BOTTOM,
           f"Thabo stage card crosses safe area: {box}")
    fill = accent if final else PAPER
    draw.rounded_rectangle(box, radius=7, fill=fill, outline=accent, width=3)
    draw.rectangle((x0, y0, x0 + 34, y0 + 31), fill=accent if not final else PAPER)
    centre_text(draw, str(number), (x0 + 17, y0 + 15), font(13, bold=True, serif=True), PAPER if not final else accent)

    lf, llines = fit_wrapped(
        draw, str(label).upper(), x1 - x0 - 52, 2, 14, 11,
        max_height=34, spacing=0, label="Thabo stage label", bold=True, condensed=True,
    )
    draw_lines(draw, llines, (x0 + 44, y0 + 7), lf, PAPER if final else accent, spacing=0)

    nf, nlines = fit_wrapped(
        draw, str(note), x1 - x0 - 18, 4, 13, 10,
        max_height=y1 - y0 - 49, spacing=1, label="Thabo stage note", serif=True,
    )
    draw_lines(draw, nlines, (x0 + 9, y0 + 43), nf, PAPER if final else INK, spacing=1)

    if blocked:
        draw.line((x0 + 8, y0 + 8, x1 - 8, y1 - 8), fill=accent, width=6)
        draw.line((x1 - 8, y0 + 8, x0 + 8, y1 - 8), fill=accent, width=6)


def render_material_chain(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)
    deck_bottom = top_stack(
        img, draw, accent, data,
        x=96, y=104, width=535,
        headline_bottom=275, deck_bottom=350,
        headline_lines=4, headline_start=54, headline_min=42,
        deck_lines=4, deck_start=23, deck_min=19,
    )
    portrait(img, root, speaker, (675, 126), (265, 292))
    draw = ImageDraw.Draw(img)
    quote_top = max(365, deck_bottom + 16)
    ensure(quote_top <= 392, "Thabo material chain leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (96, quote_top, 555, 525), large=True)
    draw_small_fact_list(
        draw, data["facts"], accent, (585, 430, 940, 600),
        heading="MATERIAL FACTS", minimum=13, start=15,
    )

    chain = data.get("chain")
    ensure(isinstance(chain, list) and len(chain) == 5, "material_chain requires exactly five chain items.")
    draw.text((96, 610), "THE MATERIAL PATH", font=font(19, bold=True, condensed=True), fill=accent)
    draw.line((96, 636, 940, 636), fill=accent, width=2)

    x_positions = [96, 270, 444, 618, 792]
    card_w, card_h, y = 148, 170, 656
    for idx, (item, x) in enumerate(zip(chain, x_positions), start=1):
        draw_stage_card(
            draw, accent, (x, y, x + card_w, y + card_h), idx,
            str(item.get("label", f"STAGE {idx}")),
            str(item.get("note", "")),
            blocked=bool(item.get("blocked", False)),
            final=(idx == len(chain)),
        )
        if idx < len(chain):
            arrow(draw, (x + card_w + 5, y + 84), (x + card_w + 20, y + 84), accent, width=4)

    centre_text(draw, "WHEN ONE HANDOFF STALLS, THE HOUSEHOLD CARRIES THE DELAY", (518, 850), font(11, bold=True, condensed=True), accent)
    draw_takeaway_band(draw, accent, data["takeaway"], label="THABO / MATERIAL CHAIN")
    draw_footer(draw, accent)
    return img


def render_structural_gap(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)
    deck_bottom = top_stack(
        img, draw, accent, data,
        x=96, y=104, width=835,
        headline_bottom=235, deck_bottom=315,
        headline_lines=3, headline_start=56, headline_min=44,
        deck_lines=3, deck_start=24, deck_min=19,
    )
    ensure(deck_bottom <= 322, "Thabo structural gap deck intrudes into content row.")

    portrait(img, root, speaker, (96, 350), (305, 315))
    draw = ImageDraw.Draw(img)
    draw_quote(draw, data["quote"], speaker["name"], accent, (430, 348, 940, 500), large=True)
    draw_small_fact_list(
        draw, data["facts"], accent, (96, 690, 385, 870),
        heading="MATERIAL FACTS", minimum=13, start=15,
    )

    gaps = data.get("gaps")
    ensure(isinstance(gaps, list) and len(gaps) == 3, "structural_gap requires exactly three gap rows.")
    x0, x1 = 430, 940
    y0 = 525
    draw.text((x0, y0), "THE STRUCTURAL GAP", font=font(19, bold=True, condensed=True), fill=accent)
    y0 += 34
    left_x0, left_x1 = x0, 632
    gap_x0, gap_x1 = 646, 724
    right_x0, right_x1 = 738, x1
    draw.rectangle((left_x0, y0, left_x1, y0 + 35), fill=accent)
    draw.rectangle((right_x0, y0, right_x1, y0 + 35), fill=accent)
    centre_text(draw, "PUBLIC PROMISE", ((left_x0 + left_x1)//2, y0 + 17), font(13, bold=True, condensed=True), PAPER)
    centre_text(draw, "HOUSEHOLD REALITY", ((right_x0 + right_x1)//2, y0 + 17), font(13, bold=True, condensed=True), PAPER)
    draw.rectangle((gap_x0, y0, gap_x1, 850), fill=accent)
    centre_text(draw, "GAP", ((gap_x0 + gap_x1)//2, y0 + 18), font(14, bold=True, condensed=True), PAPER)

    row_y = y0 + 48
    row_h = 74
    for idx, item in enumerate(gaps, start=1):
        yy = row_y + (idx - 1) * 84
        draw.rounded_rectangle((left_x0, yy, left_x1, yy + row_h), radius=5, fill=PAPER, outline=accent, width=2)
        draw.rounded_rectangle((right_x0, yy, right_x1, yy + row_h), radius=5, fill=PAPER, outline=accent, width=2)

        lf, llines = fit_wrapped(draw, str(item.get("promise", "PROMISE")), left_x1-left_x0-18, 3, 14, 11,
                                 max_height=53, spacing=1, label="Thabo promise gap", serif=True)
        rf, rlines = fit_wrapped(draw, str(item.get("reality", "REALITY")), right_x1-right_x0-18, 3, 14, 11,
                                 max_height=53, spacing=1, label="Thabo reality gap", serif=True)
        draw_lines(draw, llines, (left_x0 + 9, yy + 13), lf, INK, spacing=1)
        draw_lines(draw, rlines, (right_x0 + 9, yy + 13), rf, INK, spacing=1)
        centre_text(draw, str(idx), ((gap_x0 + gap_x1)//2, yy + row_h//2), font(18, bold=True, serif=True), PAPER)

    centre_text(draw, "THE GAP IS WHERE COST MOVES DOWNWARD", (685, 861), font(11, bold=True, condensed=True), accent)
    draw_takeaway_band(draw, accent, data["takeaway"], label="THABO / STRUCTURAL GAP")
    draw_footer(draw, accent)
    return img


def render_continuity_pressure(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)
    portrait(img, root, speaker, (96, 138), (300, 322))
    draw = ImageDraw.Draw(img)
    deck_bottom = top_stack(
        img, draw, accent, data,
        x=430, y=105, width=510,
        headline_bottom=282, deck_bottom=370,
        headline_lines=4, headline_start=52, headline_min=41,
        deck_lines=4, deck_start=23, deck_min=19,
    )
    quote_top = max(383, deck_bottom + 14)
    ensure(quote_top <= 405, "Thabo continuity pressure leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (430, quote_top, 940, 525), large=True)
    draw_small_fact_list(
        draw, data["facts"], accent, (96, 520, 390, 870),
        heading="PRESSURE SIGNALS", minimum=14, start=16,
    )

    pressure = data.get("pressure_steps")
    ensure(isinstance(pressure, list) and len(pressure) == 4, "continuity_pressure requires exactly four pressure_steps.")
    draw.text((430, 558), "PRESSURE ACCUMULATES OVER TIME", font=font(19, bold=True, condensed=True), fill=accent)
    draw.line((430, 586, 940, 586), fill=accent, width=2)

    base_x = 500
    max_w = 390
    y = 605
    widths = [205, 265, 330, 390]
    bar_h = 62
    for idx, (item, bw) in enumerate(zip(pressure, widths), start=1):
        draw.line((462, y + 31, 490, y + 31), fill=accent, width=4)
        draw.ellipse((447, y + 17, 475, y + 45), fill=accent)
        centre_text(draw, str(idx), (461, y + 31), font(12, bold=True, serif=True), PAPER)
        draw.rounded_rectangle((base_x, y, base_x + bw, y + bar_h), radius=6, fill=accent if idx == 4 else PAPER, outline=accent, width=3)
        label = str(item.get("label", f"STEP {idx}"))
        value = str(item.get("value", "PRESSURE"))
        draw.text((base_x + 13, y + 7), label.upper(), font=font(13, bold=True, condensed=True), fill=PAPER if idx == 4 else accent)
        vf, vlines = fit_wrapped(draw, value, bw - 26, 2, 14, 11, max_height=31, spacing=0, label="Thabo pressure value", serif=True)
        draw_lines(draw, vlines, (base_x + 13, y + 28), vf, PAPER if idx == 4 else INK, spacing=0)
        y += 66

    draw.line((461, 610, 461, 858), fill=accent, width=5)
    arrow(draw, (912, 842), (935, 842), accent, width=4)
    draw_takeaway_band(draw, accent, data["takeaway"], label="THABO / CONTINUITY PRESSURE")
    draw_footer(draw, accent)
    return img


RENDERERS = {
    "burden_ledger": render_burden_ledger,
    "material_chain": render_material_chain,
    "structural_gap": render_structural_gap,
    "continuity_pressure": render_continuity_pressure,
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
    ensure(not missing, f"Missing Thabo layout fields: {', '.join(missing)}")
    ensure(data["speaker"] == "thabo_mokoena", "Thabo layout family only accepts speaker=thabo_mokoena.")
    ensure(data["layout_family"] in FAMILIES, f"Unknown Thabo layout family: {data['layout_family']}")
    ensure(2 <= int(data["slide_number"]) <= int(data["total_slides"]) - 1,
           "Thabo family layouts are standard slides 2-19, not episode opener/closer.")
    ensure(isinstance(data["facts"], list) and 2 <= len(data["facts"]) <= 5,
           "Thabo family requires 2-5 facts.")


def render(input_path: Path, output_path: Path):
    root = Path(__file__).resolve().parents[1]
    data = json.loads(input_path.read_text(encoding="utf-8"))
    validate_input(data)

    presets = json.loads((root / "config/layout_presets.json").read_text(encoding="utf-8"))
    approved = set(presets["thabo_mokoena"]["approved_families"])
    ensure(data["layout_family"] in approved,
           f"Thabo layout not approved in config/layout_presets.json: {data['layout_family']}")

    characters = json.loads((root / "config/characters.json").read_text(encoding="utf-8"))
    speaker = characters["thabo_mokoena"]
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
