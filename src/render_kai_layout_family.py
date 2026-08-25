from __future__ import annotations

import argparse
import json
import math
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
    from .render_identity_slide import portrait, render_kai as render_network_mesh
except ImportError:
    from editorial_primitives import (
        INK, MUTED, PAPER, SAFE, W, LayoutError, arrow, centre_text,
        draw_deck, draw_footer, draw_frame, draw_headline, draw_lines,
        draw_quote, draw_small_fact_list, draw_takeaway_band, ensure,
        fit_wrapped, font, hex_rgb, paper_texture, editorial_atmosphere,
    )
    from render_identity_slide import portrait, render_kai as render_network_mesh


FAMILIES = {
    "network_mesh",
    "feedback_system",
    "monitoring_loop",
    "decentralised_pathway",
    "repair_network",
}


def new_canvas(data: dict, speaker: dict):
    accent = hex_rgb(speaker["accent"])
    img = Image.new("RGB", (1080, 1080), PAPER)
    paper_texture(img)
    editorial_atmosphere(
        img, accent, "kai_patel",
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


def draw_node(draw, accent, pos, label: str, *, radius=42, filled=False, sublabel: str = ""):
    x, y = pos
    ensure(x - radius >= SAFE and x + radius <= W - SAFE and y - radius >= SAFE and y + radius <= 875,
           f"Kai network node crosses safe area: {(x, y, radius)}")
    draw.ellipse(
        (x - radius, y - radius, x + radius, y + radius),
        fill=accent if filled else PAPER,
        outline=accent,
        width=3,
    )
    lf, lines = fit_wrapped(
        draw,
        str(label).upper(),
        radius * 2 - 16,
        2,
        13,
        10,
        max_height=35,
        spacing=0,
        label="Kai node label",
        bold=True,
        condensed=True,
    )
    line_y = y - 14 if len(lines) == 2 else y - 7
    for line in lines:
        centre_text(draw, line, (x, line_y), lf, PAPER if filled else accent)
        line_y += 14
    if sublabel:
        sf, slines = fit_wrapped(
            draw, str(sublabel), radius * 2 + 20, 2, 10, 8,
            max_height=26, spacing=0, label="Kai node sublabel", serif=True,
        )
        if slines:
            centre_text(draw, slines[0], (x, y + radius + 14), sf, MUTED)


def draw_circular_feedback(draw, accent, labels, *, centre=(760, 700), radius=137, title="FEEDBACK SYSTEM"):
    labels = list(labels)
    ensure(4 <= len(labels) <= 6, "feedback_system requires 4-6 mechanism labels.")
    labels = labels[:5]
    cx, cy = centre
    draw.text((cx - 165, cy - radius - 70), title, font=font(17, bold=True, condensed=True), fill=accent)
    positions = []
    for idx in range(len(labels)):
        angle = -math.pi / 2 + idx * (2 * math.pi / len(labels))
        positions.append((cx + int(math.cos(angle) * radius), cy + int(math.sin(angle) * radius)))

    for idx, (label, pos) in enumerate(zip(labels, positions)):
        draw_node(draw, accent, pos, label, radius=38, filled=(idx == len(labels) - 1))
        nxt = positions[(idx + 1) % len(positions)]
        dx, dy = nxt[0] - pos[0], nxt[1] - pos[1]
        dist = max(1.0, (dx * dx + dy * dy) ** 0.5)
        ux, uy = dx / dist, dy / dist
        arrow(
            draw,
            (pos[0] + ux * 42, pos[1] + uy * 42),
            (nxt[0] - ux * 42, nxt[1] - uy * 42),
            accent,
            width=2,
        )

    draw.ellipse((cx - 62, cy - 62, cx + 62, cy + 62), fill=PAPER, outline=accent, width=4)
    centre_text(draw, "LEARN", (cx, cy - 11), font(18, bold=True, condensed=True), accent)
    centre_text(draw, "& ADAPT", (cx, cy + 14), font(15, bold=True, condensed=True), accent)


def render_feedback_system(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)
    deck_bottom = top_stack(
        img, draw, accent, data,
        x=96, y=104, width=520,
        headline_bottom=282, deck_bottom=352,
        headline_lines=4, headline_start=54, headline_min=41,
        deck_lines=4, deck_start=23, deck_min=19,
    )
    portrait(img, root, speaker, (670, 126), (270, 300))
    draw = ImageDraw.Draw(img)
    quote_top = max(367, deck_bottom + 16)
    ensure(quote_top <= 392, "Kai feedback system leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (96, quote_top, 585, 520))
    draw_small_fact_list(
        draw, data["facts"], accent, (96, 550, 435, 870),
        heading="SYSTEM SIGNALS", minimum=14, start=16,
    )
    draw_circular_feedback(draw, accent, data.get("mechanism", []), centre=(750, 706), radius=132)
    draw_takeaway_band(draw, accent, data["takeaway"], label="KAI / FEEDBACK TEST")
    draw_footer(draw, accent)
    return img


def render_monitoring_loop(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)
    portrait(img, root, speaker, (96, 135), (300, 330))
    draw = ImageDraw.Draw(img)
    deck_bottom = top_stack(
        img, draw, accent, data,
        x=445, y=106, width=495,
        headline_bottom=278, deck_bottom=370,
        headline_lines=4, headline_start=52, headline_min=41,
        deck_lines=4, deck_start=23, deck_min=19,
    )
    quote_top = max(372, deck_bottom + 16)
    ensure(quote_top <= 398, "Kai monitoring loop leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (445, quote_top, 940, 520))

    monitors = data.get("monitors")
    ensure(isinstance(monitors, list) and len(monitors) == 4, "monitoring_loop requires exactly four monitor items.")
    draw_small_fact_list(
        draw, data["facts"], accent, (96, 548, 390, 870),
        heading="MONITORING SIGNALS", minimum=14, start=16,
    )

    draw.text((438, 548), "LIVE MONITORING LOOP", font=font(18, bold=True, condensed=True), fill=accent)
    centre = (710, 710)
    draw.ellipse((centre[0]-74, centre[1]-74, centre[0]+74, centre[1]+74), fill=PAPER, outline=accent, width=4)
    centre_text(draw, "LIVE", (centre[0], centre[1]-13), font(19, bold=True, condensed=True), accent)
    centre_text(draw, "STATE", (centre[0], centre[1]+14), font(22, bold=True, serif=True), accent)

    positions = [(520, 625), (855, 620), (875, 812), (520, 815)]
    for idx, (item, pos) in enumerate(zip(monitors, positions)):
        x, y = pos
        draw.rounded_rectangle((x-72, y-42, x+72, y+42), radius=9, fill=PAPER, outline=accent, width=2)
        centre_text(draw, str(item.get("label", f"SIGNAL {idx+1}")).upper(), (x, y-17), font(11, bold=True, condensed=True), accent)
        centre_text(draw, str(item.get("value", "LIVE")), (x, y+8), font(17, bold=True, serif=True), INK)
        arrow(draw, pos, centre, accent, width=2)

    # Repaint the live-state hub above link lines so telemetry does not cross its label.
    draw.ellipse((centre[0]-74, centre[1]-74, centre[0]+74, centre[1]+74), fill=accent, outline=accent, width=4)
    centre_text(draw, "LIVE", (centre[0], centre[1]-13), font(19, bold=True, condensed=True), PAPER)
    centre_text(draw, "STATE", (centre[0], centre[1]+14), font(22, bold=True, serif=True), PAPER)

    # Small telemetry rail reinforces monitoring rather than a generic network.
    bars = [18, 34, 26, 48, 38, 56, 44, 61]
    bx = 610
    for i, height in enumerate(bars):
        x = bx + i * 18
        draw.rectangle((x, 856-height, x+9, 856), fill=accent if i in (3, 7) else PAPER, outline=accent, width=1)
    draw.text((610, 861), "TELEMETRY / ALERT / VERIFY", font=font(10, bold=True, condensed=True), fill=accent)

    draw_takeaway_band(draw, accent, data["takeaway"], label="KAI / MONITORING TEST")
    draw_footer(draw, accent)
    return img


def render_decentralised_pathway(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)
    deck_bottom = top_stack(
        img, draw, accent, data,
        x=96, y=104, width=555,
        headline_bottom=282, deck_bottom=355,
        headline_lines=4, headline_start=53, headline_min=41,
        deck_lines=4, deck_start=23, deck_min=19,
    )
    portrait(img, root, speaker, (700, 126), (240, 285))
    draw = ImageDraw.Draw(img)
    quote_top = max(366, deck_bottom + 16)
    ensure(quote_top <= 392, "Kai decentralised pathway leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (96, quote_top, 610, 515))

    routes = data.get("routes")
    ensure(isinstance(routes, list) and len(routes) == 5, "decentralised_pathway requires exactly five route labels.")
    draw_small_fact_list(
        draw, data["facts"], accent, (96, 548, 390, 870),
        heading="ROUTING SIGNALS", minimum=14, start=16,
    )
    draw.text((438, 548), "DECENTRALISED PATHWAY", font=font(18, bold=True, condensed=True), fill=accent)

    source = (500, 704)
    branch_a = (640, 625)
    branch_b = (640, 790)
    edge = (790, 704)
    user = (915, 704)
    positions = [source, branch_a, branch_b, edge, user]
    labels = [str(x) for x in routes]

    # Redundant branch: source can flow through either node before converging at the edge.
    arrow(draw, source, branch_a, accent, width=3)
    arrow(draw, source, branch_b, accent, width=3)
    arrow(draw, branch_a, edge, accent, width=3)
    arrow(draw, branch_b, edge, accent, width=3)
    arrow(draw, edge, user, accent, width=4)
    draw.arc((548, 590, 842, 826), start=115, end=245, fill=accent, width=2)

    for idx, (label, pos) in enumerate(zip(labels, positions)):
        draw_node(draw, accent, pos, label, radius=40 if idx not in (1,2) else 36, filled=(idx == 4))

    centre_text(draw, "NO SINGLE HANDOFF OWNS THE WHOLE ROUTE", (710, 858), font(11, bold=True, condensed=True), accent)
    draw_takeaway_band(draw, accent, data["takeaway"], label="KAI / DECENTRALISATION TEST")
    draw_footer(draw, accent)
    return img


def render_repair_network(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)
    portrait(img, root, speaker, (96, 140), (290, 320))
    draw = ImageDraw.Draw(img)
    deck_bottom = top_stack(
        img, draw, accent, data,
        x=435, y=106, width=505,
        headline_bottom=278, deck_bottom=370,
        headline_lines=4, headline_start=52, headline_min=41,
        deck_lines=4, deck_start=23, deck_min=19,
    )
    quote_top = max(390, deck_bottom + 14)
    ensure(quote_top <= 412, "Kai repair network leaves insufficient quote space.")
    draw_quote(draw, data["quote"], speaker["name"], accent, (435, quote_top, 940, 530))

    steps = data.get("repair_steps")
    ensure(isinstance(steps, list) and len(steps) == 5, "repair_network requires exactly five repair_steps.")
    draw_small_fact_list(
        draw, data["facts"], accent, (96, 548, 390, 870),
        heading="REPAIR SIGNALS", minimum=14, start=16,
    )
    draw.text((438, 548), "REPAIR NETWORK", font=font(18, bold=True, condensed=True), fill=accent)

    cx, cy = 710, 710
    draw.ellipse((cx-70, cy-70, cx+70, cy+70), fill=accent, outline=accent, width=4)
    centre_text(draw, "INCIDENT", (cx, cy-11), font(16, bold=True, condensed=True), PAPER)
    centre_text(draw, "STATE", (cx, cy+14), font(20, bold=True, serif=True), PAPER)

    ring = [(520, 620), (800, 585), (900, 710), (800, 835), (520, 815)]
    for idx, (step, pos) in enumerate(zip(steps, ring)):
        draw_node(draw, accent, pos, str(step), radius=40, filled=(idx == 4))
        if idx < 4:
            arrow(draw, (cx, cy), pos, accent, width=2)
        else:
            arrow(draw, pos, (cx, cy), accent, width=3)

    # Repaint the incident hub above repair links so the central state stays legible.
    draw.ellipse((cx-70, cy-70, cx+70, cy+70), fill=accent, outline=accent, width=4)
    centre_text(draw, "INCIDENT", (cx, cy-11), font(16, bold=True, condensed=True), PAPER)
    centre_text(draw, "STATE", (cx, cy+14), font(20, bold=True, serif=True), PAPER)

    # Show the repair cycle explicitly returning to service rather than ending at a node.
    draw.arc((476, 560, 930, 860), start=190, end=352, fill=accent, width=3)
    arrow(draw, (865, 840), (817, 858), accent, width=3)
    centre_text(draw, "DETECT → ISOLATE → REROUTE → REPAIR → VERIFY", (710, 872), font(10, bold=True, condensed=True), accent)

    draw_takeaway_band(draw, accent, data["takeaway"], label="KAI / REPAIR TEST")
    draw_footer(draw, accent)
    return img


RENDERERS = {
    "network_mesh": render_network_mesh,
    "feedback_system": render_feedback_system,
    "monitoring_loop": render_monitoring_loop,
    "decentralised_pathway": render_decentralised_pathway,
    "repair_network": render_repair_network,
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
    ensure(not missing, f"Missing Kai layout fields: {', '.join(missing)}")
    ensure(data["speaker"] == "kai_patel", "Kai layout family only accepts speaker=kai_patel.")
    ensure(data["layout_family"] in FAMILIES, f"Unknown Kai layout family: {data['layout_family']}")
    ensure(2 <= int(data["slide_number"]) <= int(data["total_slides"]) - 1,
           "Kai family layouts are standard slides 2-19, not episode opener/closer.")
    ensure(isinstance(data["facts"], list) and 2 <= len(data["facts"]) <= 5,
           "Kai family requires 2-5 facts.")


def render(input_path: Path, output_path: Path):
    root = Path(__file__).resolve().parents[1]
    data = json.loads(input_path.read_text(encoding="utf-8"))
    validate_input(data)

    presets = json.loads((root / "config/layout_presets.json").read_text(encoding="utf-8"))
    approved = set(presets["kai_patel"]["approved_families"])
    ensure(data["layout_family"] in approved,
           f"Kai layout not approved in config/layout_presets.json: {data['layout_family']}")

    characters = json.loads((root / "config/characters.json").read_text(encoding="utf-8"))
    speaker = characters["kai_patel"]
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
