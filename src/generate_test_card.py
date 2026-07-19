from pathlib import Path
from datetime import date
from PIL import Image, ImageDraw, ImageFont
import argparse

WIDTH = 1080
HEIGHT = 1080
SAFE = 66

PAPER = (245, 241, 231)
INK = (25, 30, 36)
MUTED = (72, 78, 84)
ACCENT = (32, 81, 126)
ACCENT_LIGHT = (218, 229, 238)

def get_font(size=32, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()

def draw_centered(draw, text, y, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, y), text, font=font, fill=fill)

def generate(title, output_path):
    img = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(img)

    # outer frame
    draw.rounded_rectangle(
        (SAFE, SAFE, WIDTH - SAFE, HEIGHT - SAFE),
        radius=10,
        outline=INK,
        width=4
    )

    # header
    draw.rectangle((SAFE, SAFE, WIDTH - SAFE, 174), fill=INK)
    header_font = get_font(26, bold=True)
    date_font = get_font(22, bold=False)

    draw.text((SAFE + 30, SAFE + 34), "AI GEOPOLITIC", font=header_font, fill=PAPER)

    d = date.today().strftime("%d %B %Y").upper()
    bbox = draw.textbbox((0, 0), d, font=date_font)
    w = bbox[2] - bbox[0]
    draw.text((WIDTH - SAFE - 30 - w, SAFE + 36), d, font=date_font, fill=(215, 219, 221))

    # central circle
    cx, cy = WIDTH // 2, 390
    r = 128
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=ACCENT_LIGHT, outline=ACCENT, width=7)

    # simple AI face motif
    draw.arc((430, 302, 650, 522), 205, 335, fill=INK, width=6)
    draw.line((470, 365, 610, 365), fill=INK, width=6)
    draw.ellipse((490, 382, 520, 412), fill=ACCENT)
    draw.ellipse((560, 382, 590, 412), fill=ACCENT)
    draw.line((505, 447, 575, 447), fill=INK, width=5)
    draw.line((540, 262, 540, 224), fill=INK, width=5)
    draw.ellipse((530, 207, 550, 227), fill=ACCENT)

    # headline
    title_font = get_font(72, bold=True)
    draw_centered(draw, title.upper(), 560, title_font, INK)

    # divider
    draw.rounded_rectangle((300, 684, 780, 698), radius=7, fill=ACCENT)

    # subtitle
    subtitle_font = get_font(30, bold=True)
    draw_centered(draw, "THE DAILY IDEOLOGICAL NEWSROOM", 730, subtitle_font, ACCENT)

    body_font = get_font(25, bold=False)
    draw_centered(draw, "Workflow test • locked safe area • code-rendered typography", 792, body_font, MUTED)

    # footer
    footer_y = HEIGHT - SAFE - 92
    draw.line((SAFE + 30, footer_y, WIDTH - SAFE - 30, footer_y), fill=(145, 147, 146), width=2)

    footer_font = get_font(20, bold=False)
    draw.text((SAFE + 30, footer_y + 30), "The event is factual. The interpretation ideological.", font=footer_font, fill=MUTED)

    slide_label = "TEST 01"
    bbox = draw.textbbox((0, 0), slide_label, font=footer_font)
    w = bbox[2] - bbox[0]
    draw.text((WIDTH - SAFE - 30 - w, footer_y + 30), slide_label, font=footer_font, fill=MUTED)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="PNG", optimize=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", default="AI GEOPOLITIC")
    parser.add_argument("--output", default="output/test-card.png")
    args = parser.parse_args()

    generate(args.title, Path(args.output))
    print(f"Generated {args.output}")