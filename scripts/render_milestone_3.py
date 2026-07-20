from PIL import Image, ImageDraw, ImageFont
import json
import os
import textwrap

WIDTH, HEIGHT = 1080, 1080
BG = "#f3f0e8"
BLACK = "#111111"
OUTPUT_DIR = "output"
CONTENT_DIR = "content"
PORTRAITS_DIR = "assets/portraits"

def load_font(size, bold=False):
    candidates = []
    if bold:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf"
        ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()

TITLE_FONT = load_font(48, bold=True)
SUBTITLE_FONT = load_font(28, bold=False)
LABEL_FONT = load_font(18, bold=True)
BODY_FONT = load_font(18, bold=False)
QUOTE_FONT = load_font(25, bold=False)
SMALL_FONT = load_font(16, bold=False)
FOOTER_FONT = load_font(15, bold=False)

def wrap_text(text, width_chars):
    return textwrap.fill(text, width=width_chars)

def draw_multiline(draw, text, xy, font, fill, max_width_chars, line_spacing=8):
    wrapped = textwrap.wrap(text, width=max_width_chars)
    x, y = xy
    bbox = draw.multiline_textbbox((x, y), "\n".join(wrapped), font=font, spacing=line_spacing)
    draw.multiline_text((x, y), "\n".join(wrapped), font=font, fill=fill, spacing=line_spacing)
    return bbox[3] - bbox[1]

def paste_portrait(canvas, portrait_path, box):
    if not os.path.exists(portrait_path):
        return
    img = Image.open(portrait_path).convert("RGB")
    img.thumbnail((box[2] - box[0], box[3] - box[1]))
    x = box[0] + ((box[2] - box[0]) - img.width) // 2
    y = box[1] + ((box[3] - box[1]) - img.height) // 2
    canvas.paste(img, (x, y))

def draw_box(draw, box, outline, width=2, fill=None):
    draw.rounded_rectangle(box, radius=10, outline=outline, width=width, fill=fill)

def draw_footer(draw, accent):
    y = 1000
    draw.line((70, y, 1010, y), fill=BLACK, width=2)
    draw.rectangle((70, 970, 130, 1005), outline=accent, width=2)
    draw.text((82, 975), "AI.", font=LABEL_FONT, fill=accent)
    draw.text((145, 978), "AI GEOPOLITIC", font=LABEL_FONT, fill=BLACK)
    draw.text((675, 980), "The event is factual. The interpretation ideological.", font=FOOTER_FONT, fill="#444444")

def draw_header(draw, accent, slide_number):
    draw.rectangle((70, 70, 1010, 1010), outline=accent, width=3)
    draw.text((925, 78), slide_number, font=TITLE_FONT, fill=accent)

def draw_title_block(draw, title, subtitle, accent):
    y = 95
    title_wrapped = textwrap.wrap(title, width=18)
    draw.multiline_text((95, y), "\n".join(title_wrapped), font=TITLE_FONT, fill=BLACK, spacing=0)
    title_height = draw.multiline_textbbox((95, y), "\n".join(title_wrapped), font=TITLE_FONT, spacing=0)[3] - y
    draw.line((95, y + title_height + 10, 520, y + title_height + 10), fill=accent, width=3)
    draw_multiline(draw, subtitle, (95, y + title_height + 28), SUBTITLE_FONT, BLACK, 33, line_spacing=6)
    return y + title_height + 140

def draw_quote_block(draw, speaker, quote, accent, top_y):
    draw.text((95, top_y), speaker, font=load_font(22, bold=True), fill=accent)
    draw.text((95, top_y + 34), "“", font=load_font(42, bold=True), fill=accent)
    quote_height = draw_multiline(draw, quote, (140, top_y + 44), QUOTE_FONT, BLACK, 24, line_spacing=8)
    draw.text((470, top_y + 44 + quote_height - 12), "”", font=load_font(42, bold=True), fill=accent)
    return top_y + 120

def draw_facts_box(draw, heading, facts, accent, top_y):
    draw.rectangle((95, top_y, 460, top_y + 230), outline=accent, width=2)
    draw.rectangle((95, top_y, 300, top_y + 34), fill=accent)
    draw.text((108, top_y + 7), heading, font=LABEL_FONT, fill="white")

    y = top_y + 50
    for fact in facts:
        draw.text((112, y), "•", font=BODY_FONT, fill=accent)
        fact_height = draw_multiline(draw, fact, (130, y), BODY_FONT, BLACK, 29, line_spacing=4)
        y += max(34, fact_height + 10)

def draw_takeaway_box(draw, heading, takeaway, accent):
    y = 920
    draw.rectangle((95, y, 975, y + 60), outline=accent, width=2)
    draw.text((110, y + 16), heading, font=LABEL_FONT, fill=accent)
    draw.text((380, y + 16), takeaway, font=BODY_FONT, fill=BLACK)

def draw_trust_loop(draw, accent):
    center = (760, 700)
    r = 120
    draw.ellipse((center[0]-65, center[1]-65, center[0]+65, center[1]+65), outline=accent, width=3)
    draw.text((713, 683), "TRUST", font=load_font(28, bold=True), fill=accent)

    nodes = [
        ("PROMISE", (760, 540)),
        ("IMPLEMENTATION", (885, 625)),
        ("MONITORING", (850, 805)),
        ("CORRECTION", (670, 805)),
        ("DELIVERY", (615, 650))
    ]

    for label, (x, y) in nodes:
        draw.ellipse((x-35, y-35, x+35, y+35), outline=accent, width=3)
        draw.ellipse((x-6, y-6, x+6, y+6), fill=BLACK)
        tw = draw.textbbox((0, 0), label, font=SMALL_FONT)[2]
        draw.text((x - tw/2, y + 45), label, font=SMALL_FONT, fill=accent)

    connections = [
        ((760, 575), (850, 635)),
        ((885, 660), (850, 770)),
        ((815, 825), (705, 825)),
        ((650, 785), (620, 690)),
        ((645, 620), (725, 565))
    ]
    for (x1, y1), (x2, y2) in connections:
        draw.line((x1, y1, x2, y2), fill=accent, width=3)

def draw_containment_chain(draw, accent):
    draw.text((585, 585), "THE CONTAINMENT–TO–TRUST CHAIN", font=load_font(24, bold=True), fill=BLACK)
    labels = [
        "REACTOR /\nMAINTENANCE\nAREA",
        "DETECTION",
        "MONITORING",
        "FILTRATION /\nCONTAINMENT",
        "DISCLOSURE",
        "PUBLIC\nTRUST"
    ]
    x = 610
    y = 675
    gap = 65
    for i, label in enumerate(labels):
        draw.ellipse((x-28, y-28, x+28, y+28), outline=accent, width=3)
        draw.text((x-18, y-10), str(i+1), font=LABEL_FONT, fill=accent)
        label_lines = label.split("\n")
        ly = y + 45
        for line in label_lines:
            tw = draw.textbbox((0, 0), line, font=SMALL_FONT)[2]
            draw.text((x - tw/2, ly), line, font=SMALL_FONT, fill=BLACK)
            ly += 17
        if i < len(labels)-1:
            draw.line((x+28, y, x+gap-28, y), fill=accent, width=3)
        x += gap

    draw.rectangle((600, 865, 340+600, 905), outline=accent, width=2)
    draw.text((615, 877), "CONTAINMENT IS THE MECHANISM. TRANSPARENCY IS THE MULTIPLIER.", font=SMALL_FONT, fill=accent)

def render_slide(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    accent = data["accent"]
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    draw_header(draw, accent, data["slide_number"])
    next_y = draw_title_block(draw, data["title"], data["subtitle"], accent)

    portrait_path = os.path.join(PORTRAITS_DIR, data["portrait"])
    paste_portrait(img, portrait_path, (575, 110, 980, 560))

    quote_y = next_y + 10
    draw_quote_block(draw, data["speaker"], data["quote"], accent, quote_y)
    draw_facts_box(draw, data["facts_heading"], data["facts"], accent, 640)

    if data["diagram_type"] == "trust_loop":
        draw_trust_loop(draw, accent)
    elif data["diagram_type"] == "containment_chain":
        draw_containment_chain(draw, accent)

    draw_takeaway_box(draw, data["takeaway_heading"], data["takeaway"], accent)
    draw_footer(draw, accent)

    out_name = os.path.splitext(os.path.basename(json_path))[0] + ".png"
    out_path = os.path.join(OUTPUT_DIR, out_name)
    img.save(out_path)
    print(f"Saved {out_path}")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for file in os.listdir(CONTENT_DIR):
        if file.endswith(".json"):
            render_slide(os.path.join(CONTENT_DIR, file))

if __name__ == "__main__":
    main()
