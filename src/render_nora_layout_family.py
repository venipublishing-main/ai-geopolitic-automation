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
        block_height,
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
        line_height,
        paper_texture,
        editorial_atmosphere,
        wrap,
    )
    from .render_identity_slide import portrait, render_nora as render_system_axis
except ImportError:
    from editorial_primitives import (
        H, INK, MUTED, PAPER, SAFE, W, LayoutError, arrow, block_height,
        centre_text, draw_deck, draw_footer, draw_frame, draw_headline,
        draw_lines, draw_quote, draw_small_fact_list, draw_takeaway_band,
        ensure, fit_wrapped, font, hex_rgb, line_height, paper_texture, editorial_atmosphere, wrap,
    )
    from render_identity_slide import portrait, render_nora as render_system_axis


FAMILIES = {
    "system_axis",
    "feedback_loop",
    "diagnostic_matrix",
    "episode_opener",
    "episode_closer",
}
TAKEAWAY_Y = 894


def new_canvas(data: dict, speaker: dict, *, show_slide_number: bool = True):
    accent = hex_rgb(speaker["accent"])
    img = Image.new("RGB", (W, H), PAPER)
    paper_texture(img)
    editorial_atmosphere(
        img, accent, "nora",
        variant=str(data.get("content_type") or data.get("layout_family") or "family"),
        seed=int(data["slide_number"]),
    )
    draw = ImageDraw.Draw(img)
    if show_slide_number:
        draw_frame(draw, accent, int(data["slide_number"]), int(data["total_slides"]))
    else:
        draw.rectangle((SAFE, SAFE, W - SAFE, H - SAFE), outline=accent, width=3)
    return img, draw, accent


def draw_episode_header(draw: ImageDraw.ImageDraw, accent, data: dict):
    date = str(data.get("episode_date", "")).strip()
    ensure(date, "episode_date is required for NORA opener/closer layouts.")

    # Compact version of the established full episode/date header system.
    y0 = 92
    draw.rectangle((96, y0, 154, y0 + 48), outline=accent, width=2)
    draw.text((106, y0 + 7), "AI.", font=font(23, bold=True, serif=True), fill=accent)
    draw.text((174, y0 + 2), "AI GEOPOLITIC", font=font(25, bold=True, condensed=True), fill=INK)
    draw.text((174, y0 + 27), "ANALYSIS. DIALOGUE. CIVILIZATION.", font=font(11, bold=True, serif=True), fill=MUTED)

    date_font, date_lines = fit_wrapped(
        draw, date, 235, 2, 21, 17,
        max_height=48, spacing=0, label="episode date", bold=True, serif=True,
    )
    date_x = 653
    draw.text((date_x, y0 + 1), "DATE", font=font(11, bold=True, condensed=True), fill=accent)
    draw_lines(draw, date_lines, (date_x, y0 + 16), date_font, INK, spacing=0)

    slide = f"{data['slide_number']}/{data['total_slides']}"
    sf = font(31, bold=True, serif=True)
    box = draw.textbbox((0, 0), slide, font=sf)
    draw.text((942 - (box[2] - box[0]), y0 + 8), slide, font=sf, fill=accent)
    draw.line((96, 153, 944, 153), fill=accent, width=2)
    return 153


def draw_labelled_list(draw, facts, accent, box, heading: str, min_font=15):
    x0, y0, x1, y1 = box
    ensure(x0 >= SAFE and x1 <= W - SAFE and y0 >= SAFE and y1 < TAKEAWAY_Y,
           f"List box crosses reserved region: {box}")
    draw.text((x0, y0), heading, font=font(17, bold=True, condensed=True), fill=accent)
    y = y0 + 30
    available = y1 - y
    width = x1 - x0 - 46
    chosen = None
    for size in range(18, min_font - 1, -1):
        ff = font(size, serif=True)
        rows = [wrap(draw, str(item), ff, width) for item in facts]
        need = sum(block_height(draw, row, ff, spacing=1) + 11 for row in rows)
        if need <= available:
            chosen = ff, rows
            break
    if chosen is None:
        raise LayoutError(f"{heading} list does not fit its reserved region.")
    ff, rows = chosen
    for idx, lines in enumerate(rows, start=1):
        draw.ellipse((x0 + 3, y + 5, x0 + 15, y + 17), outline=accent, width=2)
        centre_text(draw, str(idx), (x0 + 9, y + 11), font(9, bold=True, condensed=True), accent)
        y = draw_lines(draw, lines, (x0 + 26, y), ff, INK, spacing=1) + 11
    ensure(y <= y1, f"{heading} list crossed its bottom boundary.")
    return y


def draw_loop(draw, accent, labels, centre=(770, 690), radius=145, title="FOLLOW-THROUGH LOOP"):
    cx, cy = centre
    labels = list(labels)[:5]
    ensure(3 <= len(labels) <= 5, "feedback_loop requires 3-5 mechanism labels.")
    draw.text((cx - 160, cy - radius - 58), title, font=font(16, bold=True, condensed=True), fill=accent)
    positions = [
        (cx, cy - radius),
        (cx + radius, cy - 35),
        (cx + 92, cy + 125),
        (cx - 92, cy + 125),
        (cx - radius, cy - 35),
    ][: len(labels)]
    for i, (label, pos) in enumerate(zip(labels, positions)):
        draw.rounded_rectangle((pos[0]-64, pos[1]-28, pos[0]+64, pos[1]+28), radius=8, fill=PAPER, outline=accent, width=3)
        centre_text(draw, label, pos, font(12, bold=True, condensed=True), accent)
        nxt = positions[(i + 1) % len(positions)]
        dx, dy = nxt[0] - pos[0], nxt[1] - pos[1]
        dist = max(1.0, (dx * dx + dy * dy) ** 0.5)
        ux, uy = dx / dist, dy / dist
        start = (pos[0] + ux * 58, pos[1] + uy * 36)
        end = (nxt[0] - ux * 58, nxt[1] - uy * 36)
        arrow(draw, start, end, accent, width=2)
    draw.ellipse((cx - 57, cy - 57, cx + 57, cy + 57), fill=PAPER, outline=accent, width=4)
    centre_text(draw, "SYSTEM", (cx, cy - 8), font(17, bold=True, condensed=True), accent)
    centre_text(draw, "CLOSES", (cx, cy + 16), font(17, bold=True, condensed=True), accent)


def render_feedback_loop(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)

    head_bottom = draw_headline(
        img, draw, data["headline"], accent, (96, 105), 500,
        max_lines=3, start=56, minimum=44, max_bottom=270,
    )
    draw.line((96, head_bottom + 7, 560, head_bottom + 7), fill=accent, width=4)
    deck_bottom = draw_deck(
        draw, data["deck"], (96, head_bottom + 22), 465,
        max_lines=4, start=24, minimum=19, max_bottom=355,
    )
    ensure(deck_bottom < 374, "NORA feedback-loop deck intrudes into quote.")

    portrait(img, root, speaker, (630, 125), (315, 330))
    draw = ImageDraw.Draw(img)
    draw_quote(draw, data["quote"], speaker["name"], accent, (96, 385, 560, 535))
    draw_small_fact_list(draw, data["facts"], accent, (96, 565, 470, 872), heading="SYSTEM SIGNALS", minimum=15, start=17)
    draw_loop(draw, accent, data.get("mechanism", []), centre=(760, 700), radius=135)
    draw_takeaway_band(draw, accent, data["takeaway"], label="NORA / FOLLOW-THROUGH TEST")
    draw_footer(draw, accent)
    return img


def render_diagnostic_matrix(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker)

    head_bottom = draw_headline(
        img, draw, data["headline"], accent, (96, 104), 560,
        max_lines=3, start=54, minimum=43, max_bottom=265,
    )
    draw.line((96, head_bottom + 7, 628, head_bottom + 7), fill=accent, width=4)
    deck_bottom = draw_deck(
        draw, data["deck"], (96, head_bottom + 22), 525,
        max_lines=3, start=23, minimum=19, max_bottom=352,
    )
    portrait(img, root, speaker, (685, 126), (260, 280))
    draw = ImageDraw.Draw(img)
    quote_top = max(370, deck_bottom + 18)
    draw_quote(draw, data["quote"], speaker["name"], accent, (96, quote_top, 620, 500))

    matrix = data.get("matrix")
    ensure(isinstance(matrix, list) and len(matrix) == 4, "diagnostic_matrix requires exactly four matrix items.")
    draw.text((96, 530), "SYSTEM DIAGNOSTIC", font=font(18, bold=True, condensed=True), fill=accent)

    x0, y0 = 96, 560
    cell_w, cell_h, gap = 405, 126, 14
    for idx, item in enumerate(matrix):
        row, col = divmod(idx, 2)
        x = x0 + col * (cell_w + gap)
        y = y0 + row * (cell_h + gap)
        draw.rounded_rectangle((x, y, x + cell_w, y + cell_h), radius=7, fill=PAPER, outline=accent, width=2)
        draw.rectangle((x, y, x + 132, y + 30), fill=accent)
        draw.text((x + 10, y + 5), str(item.get("label", f"TEST {idx+1}")).upper(), font=font(14, bold=True, condensed=True), fill=PAPER)
        value = str(item.get("value", "UNRESOLVED"))
        vf, vlines = fit_wrapped(draw, value, cell_w - 162, 2, 21, 16, max_height=49, spacing=1, label="matrix value", bold=True, serif=True)
        draw_lines(draw, vlines, (x + 150, y + 10), vf, accent, spacing=1)
        note = str(item.get("note", ""))
        nf, nlines = fit_wrapped(draw, note, cell_w - 24, 3, 15, 13, max_height=66, spacing=1, label="matrix note", serif=True)
        draw_lines(draw, nlines, (x + 12, y + 51), nf, INK, spacing=1)

    draw_takeaway_band(draw, accent, data["takeaway"], label="NORA / DIAGNOSTIC RESULT")
    draw_footer(draw, accent)
    return img


def render_episode_opener(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker, show_slide_number=False)
    draw_episode_header(draw, accent, data)

    head_bottom = draw_headline(
        img, draw, data["headline"], accent, (96, 178), 590,
        max_lines=3, start=61, minimum=48, max_bottom=330,
    )
    deck_bottom = draw_deck(
        draw, data["deck"], (96, head_bottom + 14), 565,
        max_lines=3, start=28, minimum=21, max_bottom=405,
    )
    question = str(data.get("question", "")).strip()
    ensure(question, "episode_opener requires a question field.")
    qf, qlines = fit_wrapped(draw, question, 560, 2, 23, 18, max_height=54, spacing=1, label="opener question", bold=True, serif=True)
    draw.line((96, deck_bottom + 10, 575, deck_bottom + 10), fill=accent, width=2)
    draw_lines(draw, qlines, (96, deck_bottom + 19), qf, accent, spacing=1)

    portrait(img, root, speaker, (690, 178), (255, 300))
    draw = ImageDraw.Draw(img)
    draw_quote(draw, data["quote"], speaker["name"], accent, (96, 480, 520, 605))
    draw_labelled_list(draw, data["facts"], accent, (96, 635, 500, 872), "OPEN FILE", min_font=14)
    draw_loop(draw, accent, data.get("mechanism", []), centre=(755, 695), radius=123, title="FROM PROMISE TO DELIVERY")
    draw_takeaway_band(draw, accent, data["takeaway"], label="NORA / EPISODE FRAME")
    draw_footer(draw, accent)
    return img


def render_episode_closer(root: Path, data: dict, speaker: dict):
    img, draw, accent = new_canvas(data, speaker, show_slide_number=False)
    draw_episode_header(draw, accent, data)

    head_bottom = draw_headline(
        img, draw, data["headline"], accent, (96, 178), 850,
        max_lines=3, start=59, minimum=46, max_bottom=315,
    )
    draw.line((96, head_bottom + 8, 935, head_bottom + 8), fill=accent, width=4)
    deck_bottom = draw_deck(
        draw, data["deck"], (96, head_bottom + 22), 820,
        max_lines=3, start=25, minimum=20, max_bottom=390,
    )
    ensure(deck_bottom < 405, "episode_closer deck intrudes into synthesis row.")

    portrait(img, root, speaker, (96, 425), (285, 320))
    draw = ImageDraw.Draw(img)
    draw_quote(draw, data["quote"], speaker["name"], accent, (405, 420, 940, 555))

    facts = list(data["facts"])
    ensure(3 <= len(facts) <= 4, "episode_closer expects 3-4 synthesis facts.")
    draw.text((405, 580), "WHAT THE SYSTEM MUST PROVE", font=font(18, bold=True, condensed=True), fill=accent)
    y = 614
    card_h = 58
    for idx, item in enumerate(facts, start=1):
        draw.rounded_rectangle((405, y, 940, y + card_h), radius=7, fill=PAPER, outline=accent, width=2)
        draw.rectangle((405, y, 450, y + card_h), fill=accent)
        centre_text(draw, str(idx), (427, y + card_h/2), font(17, bold=True, serif=True), PAPER)
        ff, lines = fit_wrapped(draw, str(item), 462, 2, 17, 14, max_height=44, spacing=1, label="closer synthesis", serif=True)
        draw_lines(draw, lines, (466, y + 9), ff, INK, spacing=1)
        y += card_h + 10

    stages = data.get("mechanism", ["SIGNAL", "RESPONSE", "RESULT", "TRUST"])
    ensure(3 <= len(stages) <= 4, "episode_closer mechanism expects 3-4 stages.")
    draw.text((96, 775), "CLOSE THE LOOP", font=font(14, bold=True, condensed=True), fill=accent)
    y_chain = 824
    xs = [127, 205, 283, 361][:len(stages)]
    for i, (x, label) in enumerate(zip(xs, stages)):
        draw.ellipse((x-31, y_chain-23, x+31, y_chain+23), fill=PAPER, outline=accent, width=2)
        centre_text(draw, str(label), (x, y_chain), font(8, bold=True, condensed=True), accent)
        if i < len(xs) - 1:
            arrow(draw, (x+33, y_chain), (xs[i+1]-33, y_chain), accent, width=2)

    draw_takeaway_band(draw, accent, data["takeaway"], label="NORA / FINAL SYSTEM TEST")
    draw_footer(draw, accent)
    return img


RENDERERS = {
    "system_axis": render_system_axis,
    "feedback_loop": render_feedback_loop,
    "diagnostic_matrix": render_diagnostic_matrix,
    "episode_opener": render_episode_opener,
    "episode_closer": render_episode_closer,
}


def validate_input(data: dict):
    required = {"slide_number", "total_slides", "speaker", "layout_family", "headline", "deck", "quote", "facts", "takeaway"}
    missing = sorted(required - set(data))
    ensure(not missing, f"Missing required NORA family fields: {', '.join(missing)}")
    ensure(data["speaker"] == "nora", "NORA family renderer only accepts speaker='nora'.")
    ensure(data["layout_family"] in FAMILIES, f"Unknown NORA layout family: {data['layout_family']}")
    ensure(isinstance(data["facts"], list) and 1 <= len(data["facts"]) <= 6, "facts must contain 1-6 items.")
    if data["layout_family"] == "episode_opener":
        ensure(int(data["slide_number"]) == 1, "episode_opener must be slide 1.")
    if data["layout_family"] == "episode_closer":
        ensure(int(data["slide_number"]) == int(data["total_slides"]), "episode_closer must be the final slide.")


def render(input_path: Path, output_path: Path):
    root = Path(__file__).resolve().parents[1]
    data = json.loads(input_path.read_text(encoding="utf-8"))
    validate_input(data)
    characters = json.loads((root / "config/characters.json").read_text(encoding="utf-8"))
    speaker = characters["nora"]
    family = data["layout_family"]
    img = RENDERERS[family](root, data, speaker)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG", optimize=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    render(args.input, args.output)
    print(f"Generated {args.output.resolve()}")
