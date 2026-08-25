from __future__ import annotations

import argparse
import copy
import json
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

try:
    from .editorial_primitives import INK, MUTED, PAPER, font, hex_rgb
    from .render_identity_slide import render
except ImportError:
    from editorial_primitives import INK, MUTED, PAPER, font, hex_rgb
    from render_identity_slide import render


IDENTITY_INPUTS = {
    "nora": "identity-nora.json",
    "johan_vosloo": "identity-johan.json",
    "diane_sterling": "identity-diane.json",
    "kai_patel": "identity-kai.json",
    "thabo_mokoena": "identity-thabo.json",
    "amari_ndlovu": "identity-amari.json",
}

PROFILES = ("short", "normal", "dense")

SHORT_PROFILE = {
    "headline": "THE SYSTEM MUST CLOSE.",
    "deck": "Delivery works only when the whole chain is visible.",
    "quote": "A usable answer matters more than a promise.",
    "facts": [
        "Access is only the start.",
        "State changes must be visible.",
        "Failures need feedback.",
    ],
    "takeaway": "Trust grows when the full system remains legible.",
}

# Dense profiles deliberately press the existing layout without becoming absurd
# production copy. Each character stresses the regions that are most constrained
# in that identity grammar.
DENSE_SUFFIXES = {
    "nora": {
        "headline": " UNDER PRESSURE.",
        "deck": " Handoffs must remain visible.",
        "quote": " Especially when pressure rises.",
        "fact": " Feedback must close.",
        "takeaway": " The loop must remain visible under pressure.",
    },
    "johan_vosloo": {
        "headline": "",
        "deck": " Responsibility must stay visible.",
        "quote": " Power must remain answerable under pressure.",
        "fact": " Accountability remains visible.",
        "takeaway": " The chain must stay bounded under pressure.",
    },
    "diane_sterling": {
        "headline": "",
        "deck": " Execution is the real performance test.",
        "quote": " Delivery must be measurable end to end.",
        "fact": " This must remain measurable.",
        "takeaway": " Performance must survive the handoff.",
    },
    "kai_patel": {
        "headline": "",
        # Kai's base deck is already close to the guarded limit. Stress the
        # quote, facts and takeaway instead of forcing unreadable deck text.
        "deck": "",
        "quote": " The network must still learn under pressure.",
        "fact": " Repair must stay visible.",
        "takeaway": " Feedback must remain distributed under strain.",
    },
    "thabo_mokoena": {
        "headline": "",
        "deck": " The burden compounds when repair is delayed.",
        "quote": " The cost is carried in time, wages and care.",
        "fact": " Costs keep moving down.",
        "takeaway": " Repair must stop the burden moving downward.",
    },
    "amari_ndlovu": {
        "headline": "",
        "deck": " Recognition must survive the handoff.",
        "quote": " Belonging is tested in repeated encounters.",
        "fact": " Dignity must remain visible.",
        "takeaway": " Dignity must remain visible through delivery.",
    },
}


def build_profile_data(base: dict, speaker_key: str, profile: str) -> dict:
    if speaker_key not in IDENTITY_INPUTS:
        raise ValueError(f"Unknown speaker for stress profile: {speaker_key}")
    if profile not in PROFILES:
        raise ValueError(f"Unknown stress profile: {profile}")

    data = copy.deepcopy(base)

    if profile == "normal":
        return data

    if profile == "short":
        for key, value in SHORT_PROFILE.items():
            data[key] = copy.deepcopy(value)
        return data

    suffix = DENSE_SUFFIXES[speaker_key]
    if suffix["headline"]:
        data["headline"] = data["headline"].rstrip(".") + suffix["headline"]
    data["deck"] += suffix["deck"]
    data["quote"] += suffix["quote"]
    data["facts"] = [fact + suffix["fact"] for fact in data["facts"]]
    data["takeaway"] += suffix["takeaway"]
    return data


def render_profile(root: Path, speaker_key: str, profile: str, output_path: Path):
    input_name = IDENTITY_INPUTS[speaker_key]
    base = json.loads((root / "inputs" / input_name).read_text(encoding="utf-8"))
    data = build_profile_data(base, speaker_key, profile)

    with tempfile.TemporaryDirectory(prefix="ai-geopolitic-stress-") as tmp:
        temp_input = Path(tmp) / f"{speaker_key}-{profile}.json"
        temp_input.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        render(temp_input, output_path)


def build_contact_sheet(root: Path, outputs: dict[tuple[str, str], Path], output_path: Path):
    characters = json.loads((root / "config" / "characters.json").read_text(encoding="utf-8"))
    thumb = 320
    col_gap = 20
    left = 40
    top = 46
    label_h = 44
    row_h = thumb + label_h
    width = 1080
    height = top + len(IDENTITY_INPUTS) * row_h + 24

    sheet = Image.new("RGB", (width, height), PAPER)
    draw = ImageDraw.Draw(sheet)

    header_font = font(21, bold=True, condensed=True)
    for col, profile in enumerate(PROFILES):
        x = left + col * (thumb + col_gap)
        draw.text((x, 10), profile.upper(), font=header_font, fill=INK)

    for row, speaker_key in enumerate(IDENTITY_INPUTS):
        character = characters[speaker_key]
        accent = hex_rgb(character["accent"])
        y = top + row * row_h
        for col, profile in enumerate(PROFILES):
            x = left + col * (thumb + col_gap)
            with Image.open(outputs[(speaker_key, profile)]) as im:
                preview = im.convert("RGB").resize((thumb, thumb), Image.Resampling.LANCZOS)
            sheet.paste(preview, (x, y))
            label = f"{character['name']} / {profile.upper()}"
            draw.text((x + 4, y + thumb + 7), label, font=font(15, bold=True, condensed=True), fill=accent)

        draw.line((left, y + row_h - 4, width - left, y + row_h - 4), fill=MUTED, width=1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, "PNG", optimize=True)


def render_stress_pack(root: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[tuple[str, str], Path] = {}

    for speaker_key in IDENTITY_INPUTS:
        for profile in PROFILES:
            output = output_dir / f"stress-{profile}-{speaker_key}.png"
            render_profile(root, speaker_key, profile, output)
            outputs[(speaker_key, profile)] = output

    contact = output_dir / "identity-stress-contact-sheet.png"
    build_contact_sheet(root, outputs, contact)
    return outputs, contact


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parents[1]
    outputs, contact = render_stress_pack(project_root, args.output_dir)
    print(f"Generated {len(outputs)} stress renders")
    print(f"Contact sheet: {contact.resolve()}")
