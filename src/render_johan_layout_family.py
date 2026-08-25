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
    from .render_identity_slide import portrait, render_johan as render_institutional_spine
except ImportError:
    from editorial_primitives import (
        H, INK, MUTED, PAPER, SAFE, W, LayoutError, arrow, centre_text,
        draw_deck, draw_footer, draw_frame, draw_headline, draw_lines,
        draw_quote, draw_small_fact_list, draw_takeaway_band, ensure,
        fit_wrapped, font, hex_rgb, paper_texture, editorial_atmosphere,
    )
    from render_identity_slide import portrait, render_johan as render_institutional_spine


FAMILIES = {
    "institutional_spine",
    "containment_chain",
    "oversight_gate",
    "order_corridor",
    "principle_test",
}


def new_canvas(data: dict, speaker: dict):
    accent = hex_rgb(speaker["accent"])
    img = Image.new("RGB", (W, H), PAPER)
    paper_texture(img)
    editorial_atmosphere(
        img, accent, "johan_vosloo",
        variant=str(data.get("content_type") or data.get("layout_family") or "family"),
        seed=int(data["slide_number"]),
    )
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
    draw.line((x, rule_y, x + width - 4, rule_y), fill=accent, width=4)
    deck_y = rule_y + 14
    deck_end = draw_deck(
        draw,
        data["deck"],
        (x, deck_y),
        width - 8,
        max_lines=deck_lines,
        start=deck_start,
        minimum=deck_min,
        max_bottom=deck_bottom,
    )
    return deck_end


def draw_stage_box(draw, accent, box, number: int, label: str, *, filled=False):
    x0, y0, x1, y1 = box
    ensure(x0 >= SAFE and x1 <= W - SAFE and y0 >= SAFE and y1 <= 875,
           f"Johan stage box crosses safe area: {box}")
    draw.rounded_rectangle(
        box,
        radius=5,
        fill=accent if filled else PAPER,
        outline=accent,
        width=3,
    )
    num_fill = PAPER if filled else accent
    label_fill = PAPER if filled else INK
    draw.rectangle((x0, y0, x0 + 40, y1), fill=accent if not filled else PAPER)
    centre_text(
        draw,
        str(number),
        (x0 + 20, (y0 + y1) / 2),
        font(15, bold=True, serif=True),
        PAPER if not filled else accent,
    )
    lf, lines = fit_wrapped(
        draw,
        str(label).upper(),
        x1 - x0 - 55,
        2,
        16,
        12,
        max_height=y1 - y0 - 10,
        spacing=0,
        label="Johan stage label",
        bold=True,
        condensed=True,
    )
    draw_lines(draw, lines, (x0 + 49, y0 + 10), lf, label_fill, spacing=0)


def render_containment_chain(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)

    portrait(img, root, speaker, (96, 132), (315, 345))
    draw = ImageDraw.Draw(img)

    deck_bottom = top_stack(
        img,
        draw,
        accent,
        data,
        x=470,
        y=108,
        width=470,
        headline_bottom=280,
        deck_bottom=355,
        headline_lines=4,
        headline_start=52,
        headline_min=41,
        deck_lines=4,
        deck_start=23,
        deck_min=19,
    )
    quote_top = max(375, deck_bottom + 16)
    ensure(quote_top <= 398, "Johan containment chain leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (470, quote_top, 940, 520))

    draw.text((96, 540), "CONTAINMENT CHAIN", font=font(18, bold=True, condensed=True), fill=accent)
    stages = list(data.get("mechanism", []))
    ensure(3 <= len(stages) <= 5, "containment_chain requires 3-5 mechanism stages.")
    stages = stages[:4]
    n = len(stages)
    chain_left, chain_right, y0, h, gap = 96, 940, 574, 70, 16
    card_w = int((chain_right - chain_left - gap * (n - 1)) / n)

    boxes = []
    for i, label in enumerate(stages, start=1):
        x0 = chain_left + (i - 1) * (card_w + gap)
        box = (x0, y0, x0 + card_w, y0 + h)
        boxes.append(box)
        draw_stage_box(draw, accent, box, i, label, filled=(i == n))
        if i > 1:
            prev = boxes[i - 2]
            arrow(
                draw,
                (prev[2] + 3, (prev[1] + prev[3]) / 2),
                (box[0] - 4, (box[1] + box[3]) / 2),
                accent,
                width=3,
            )

    # A hard lower rule makes the chain read like an institutional boundary.
    draw.line((96, 662, 940, 662), fill=accent, width=3)
    centre_text(draw, "AUTHORITY MUST PASS EVERY CHECK", (518, 678), font(14, bold=True, condensed=True), accent)

    draw_small_fact_list(
        draw,
        data["facts"],
        accent,
        (96, 704, 940, 870),
        heading="CONTAINMENT EVIDENCE",
        minimum=15,
        start=17,
    )
    draw_takeaway_band(draw, accent, data["takeaway"], label="JOHAN / CONTAINMENT TEST")
    draw_footer(draw, accent)
    return img


def render_oversight_gate(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)

    deck_bottom = top_stack(
        img,
        draw,
        accent,
        data,
        x=96,
        y=105,
        width=535,
        headline_bottom=265,
        deck_bottom=350,
        headline_lines=3,
        headline_start=54,
        headline_min=42,
        deck_lines=4,
        deck_start=23,
        deck_min=19,
    )
    portrait(img, root, speaker, (680, 125), (260, 300))
    draw = ImageDraw.Draw(img)
    quote_top = max(368, deck_bottom + 16)
    ensure(quote_top <= 392, "Johan oversight gate leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (96, quote_top, 585, 515))

    draw_small_fact_list(
        draw,
        data["facts"],
        accent,
        (96, 548, 455, 870),
        heading="OVERSIGHT RECORD",
        minimum=14,
        start=16,
    )

    labels = list(data.get("mechanism", []))
    ensure(len(labels) >= 4, "oversight_gate requires four mechanism labels.")
    labels = labels[:4]

    # Gate geometry: mandate enters, bounded authority passes between scrutiny pillars.
    gx0, gx1 = 520, 940
    draw.text((gx0, 548), "OVERSIGHT GATE", font=font(18, bold=True, condensed=True), fill=accent)
    pillar_y0, pillar_y1 = 600, 827
    left_pillar = (560, pillar_y0, 650, pillar_y1)
    right_pillar = (810, pillar_y0, 900, pillar_y1)
    for box in (left_pillar, right_pillar):
        draw.rectangle(box, fill=PAPER, outline=accent, width=4)
        draw.rectangle((box[0] + 8, box[1] + 8, box[2] - 8, box[1] + 38), fill=accent)

    centre_text(draw, labels[0], (605, 628), font(13, bold=True, condensed=True), PAPER)
    centre_text(draw, labels[1], (605, 705), font(14, bold=True, condensed=True), accent)
    centre_text(draw, labels[2], (855, 628), font(13, bold=True, condensed=True), PAPER)
    centre_text(draw, labels[3], (855, 705), font(14, bold=True, condensed=True), accent)

    # lintel and threshold
    draw.rectangle((550, 580, 910, 604), fill=accent)
    centre_text(draw, "POWER ENTERS THROUGH RULE", (730, 592), font(12, bold=True, condensed=True), PAPER)
    draw.line((540, 842, 920, 842), fill=accent, width=5)

    draw.rounded_rectangle((682, 665, 778, 760), radius=6, fill=PAPER, outline=accent, width=4)
    centre_text(draw, "BOUND", (730, 693), font(16, bold=True, condensed=True), accent)
    centre_text(draw, "POWER", (730, 718), font(16, bold=True, condensed=True), accent)
    centre_text(draw, "ANSWERABLE", (730, 746), font(11, bold=True, condensed=True), MUTED)

    arrow(draw, (500, 712), (675, 712), accent, width=3)
    arrow(draw, (785, 712), (932, 712), accent, width=3)

    draw_takeaway_band(draw, accent, data["takeaway"], label="JOHAN / OVERSIGHT TEST")
    draw_footer(draw, accent)
    return img


def render_order_corridor(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)

    portrait(img, root, speaker, (96, 132), (300, 335))
    draw = ImageDraw.Draw(img)
    deck_bottom = top_stack(
        img,
        draw,
        accent,
        data,
        x=455,
        y=108,
        width=485,
        headline_bottom=278,
        deck_bottom=352,
        headline_lines=4,
        headline_start=52,
        headline_min=41,
        deck_lines=4,
        deck_start=23,
        deck_min=19,
    )
    quote_top = max(372, deck_bottom + 16)
    ensure(quote_top <= 398, "Johan order corridor leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (455, quote_top, 940, 520))

    draw_small_fact_list(
        draw,
        data["facts"],
        accent,
        (96, 550, 435, 870),
        heading="ORDER CONDITIONS",
        minimum=14,
        start=16,
    )

    stages = list(data.get("mechanism", []))
    ensure(4 <= len(stages) <= 5, "order_corridor requires 4-5 mechanism stages.")
    stages = stages[:4]

    draw.text((485, 550), "ORDER CORRIDOR", font=font(18, bold=True, condensed=True), fill=accent)

    # Perspective corridor: parallel rules converge toward the final institutional test.
    left, right, top, bottom = 490, 940, 600, 852
    vp = (715, 585)
    draw.line((left, bottom, vp[0] - 35, top), fill=accent, width=4)
    draw.line((right, bottom, vp[0] + 35, top), fill=accent, width=4)
    draw.line((left + 55, bottom, vp[0] - 12, top), fill=accent, width=2)
    draw.line((right - 55, bottom, vp[0] + 12, top), fill=accent, width=2)

    ys = [805, 748, 690, 632]
    widths = [360, 300, 238, 178]
    for idx, (label, yy, ww) in enumerate(zip(stages, ys, widths), start=1):
        cx = 715
        x0, x1 = cx - ww // 2, cx + ww // 2
        draw.rounded_rectangle((x0, yy - 22, x1, yy + 22), radius=4, fill=PAPER, outline=accent, width=3)
        draw.rectangle((x0, yy - 22, x0 + 38, yy + 22), fill=accent)
        centre_text(draw, str(idx), (x0 + 19, yy), font(13, bold=True, serif=True), PAPER)
        lf, lines = fit_wrapped(
            draw,
            str(label).upper(),
            ww - 52,
            1,
            15,
            11,
            max_height=27,
            spacing=0,
            label="order corridor label",
            bold=True,
            condensed=True,
        )
        centre_text(draw, lines[0], ((x0 + 38 + x1) / 2, yy), lf, accent)

    centre_text(draw, "LEGIBLE AUTHORITY", (715, 864), font(13, bold=True, condensed=True), accent)
    draw_takeaway_band(draw, accent, data["takeaway"], label="JOHAN / ORDER TEST")
    draw_footer(draw, accent)
    return img


def render_principle_test(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)

    head_bottom = draw_headline(
        img,
        draw,
        data["headline"],
        accent,
        (96, 104),
        840,
        max_lines=3,
        start=56,
        minimum=44,
        max_bottom=245,
    )
    draw.line((96, head_bottom + 7, 940, head_bottom + 7), fill=accent, width=5)
    deck_bottom = draw_deck(
        draw,
        data["deck"],
        (96, head_bottom + 21),
        820,
        max_lines=3,
        start=24,
        minimum=19,
        max_bottom=315,
    )
    ensure(deck_bottom <= 320, "Johan principle-test deck intrudes into evidence row.")

    portrait(img, root, speaker, (96, 352), (285, 310))
    draw = ImageDraw.Draw(img)
    draw_quote(draw, data["quote"], speaker["name"], accent, (410, 342, 940, 485))

    tests = data.get("tests")
    ensure(isinstance(tests, list) and len(tests) == 4, "principle_test requires exactly four tests.")

    draw.text((410, 515), "PRINCIPLE / PRACTICE TEST", font=font(18, bold=True, condensed=True), fill=accent)
    x0, y0, cell_w, cell_h, gap = 410, 548, 255, 118, 14
    for idx, item in enumerate(tests):
        row, col = divmod(idx, 2)
        x = x0 + col * (cell_w + gap)
        y = y0 + row * (cell_h + gap)
        draw.rounded_rectangle((x, y, x + cell_w, y + cell_h), radius=6, fill=PAPER, outline=accent, width=2)
        label = str(item.get("label", f"TEST {idx+1}")).upper()
        status = str(item.get("status", "OPEN")).upper()
        note = str(item.get("note", ""))

        draw.rectangle((x, y, x + cell_w, y + 28), fill=accent if idx in (0, 3) else PAPER, outline=accent, width=2)
        centre_text(
            draw,
            label,
            (x + cell_w / 2, y + 14),
            font(13, bold=True, condensed=True),
            PAPER if idx in (0, 3) else accent,
        )
        centre_text(draw, status, (x + 68, y + 55), font(18, bold=True, serif=True), accent)
        nf, nlines = fit_wrapped(
            draw,
            note,
            cell_w - 22,
            2,
            14,
            12,
            max_height=42,
            spacing=1,
            label="principle note",
            serif=True,
        )
        draw_lines(draw, nlines, (x + 11, y + 78), nf, INK, spacing=1)

    draw_small_fact_list(
        draw,
        data["facts"],
        accent,
        (96, 690, 380, 870),
        heading="RULE OF LAW",
        minimum=13,
        start=15,
    )

    draw_takeaway_band(draw, accent, data["takeaway"], label="JOHAN / PRINCIPLE TEST")
    draw_footer(draw, accent)
    return img


RENDERERS = {
    "institutional_spine": render_institutional_spine,
    "containment_chain": render_containment_chain,
    "oversight_gate": render_oversight_gate,
    "order_corridor": render_order_corridor,
    "principle_test": render_principle_test,
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
    ensure(not missing, f"Missing Johan layout fields: {', '.join(missing)}")
    ensure(data["speaker"] == "johan_vosloo", "Johan layout family only accepts speaker=johan_vosloo.")
    ensure(data["layout_family"] in FAMILIES, f"Unknown Johan layout family: {data['layout_family']}")
    ensure(2 <= int(data["slide_number"]) <= int(data["total_slides"]) - 1,
           "Johan family layouts are standard slides 2-19, not episode opener/closer.")
    ensure(isinstance(data["facts"], list) and 2 <= len(data["facts"]) <= 5,
           "Johan family requires 2-5 facts.")


def render(input_path: Path, output_path: Path):
    root = Path(__file__).resolve().parents[1]
    data = json.loads(input_path.read_text(encoding="utf-8"))
    validate_input(data)

    presets = json.loads((root / "config/layout_presets.json").read_text(encoding="utf-8"))
    approved = set(presets["johan_vosloo"]["approved_families"])
    ensure(data["layout_family"] in approved, f"Johan layout not approved in config/layout_presets.json: {data['layout_family']}")

    characters = json.loads((root / "config/characters.json").read_text(encoding="utf-8"))
    speaker = characters["johan_vosloo"]
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
