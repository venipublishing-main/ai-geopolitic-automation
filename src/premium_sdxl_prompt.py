"""Spatial SDXL conditioning from SceneContract only, with no reference images."""
from .scene_contract import SceneContract, digest


def _location(x, y):
    horizontal = "left" if x < .38 else "right" if x > .62 else "centre"
    vertical = "upper" if y < .34 else "lower" if y > .66 else "middle"
    return f"{vertical}-{horizontal}"


def compile_sdxl_prompt(contract: SceneContract):
    slide = contract.slide
    if "###" in contract.slide_json:
        raise ValueError("SDXL_DELIMITER_IN_MANIFEST")
    a = contract.art_region
    positive = ["Black-ink newspaper editorial engraving on warm off-white paper, precise cross-hatching, coherent contextual infrastructure illustration, physical depth.",
                f"Argument structure: {contract.reasoning_family.replace('_', ' ')}; {contract.shape_language}.",
                "Semantic brief; all label/sign/stamp names mean concepts, never lettering: " + slide["hero_visual"]]
    for obj in contract.semantic_objects:
        x, y = obj.zone.centre
        x, y = (x-a.x0)/(a.x1-a.x0), (y-a.y0)/(a.y1-a.y0)
        positive.append(f"Depict the {obj.label} concept in the {_location(x,y)} region (centre {x:.3f},{y:.3f}), emphasis {obj.importance:.1f}.")
    for z in contract.quiet_zones:
        x0, x1 = max(z.x0, a.x0), min(z.x1, a.x1)
        if x0 < x1:
            positive.append(f"Quiet negative-paper annotation lane across raster x={(x0-a.x0)/(a.x1-a.x0):.3f}..{(x1-a.x0)/(a.x1-a.x0):.3f}.")
    positive.extend((f"Diagram rhythm: {contract.route_grammar}; {contract.micro_detail}. Connections are reading order, not invented causal facts.",
        "Clean portrait-side transition toward " + contract.portrait.side + "; portrait and headline are outside this illustration, owned by compositor.",
        "Editorial purpose: " + slide["core_argument"],
        "Factual constraints: " + "; ".join(slide["factual_guardrails"]),
        "Composition: " + slide["composition_notes"],
        "Attention: " + slide["notices_first"] + "; " + "; ".join(slide["visual_psychology_traits"]),
        "Anti-cliche instruction: " + slide["anti_cliche_guardrail"]))
    negative = ("text, letters, words, typography, captions, labels, signage, logo, branding, watermark, signature, "
                "copyright mark, fake UI, dashboard, poster, collage, contact sheet, cyberpunk, neon, "
                "panelist portrait, celebrity likeness, literal fluffy cloud, cartoon cloud, speech bubble")
    # One delimiter is the existing Horde SDXL CLIP-conditioning handshake.
    return "\n".join(positive) + "###" + negative


def prompt_record(contract):
    prompt = compile_sdxl_prompt(contract)
    positive, negative = prompt.split("###")
    return {"prompt": prompt, "positive": positive, "negative": negative,
            "prompt_sha256": digest(prompt), "contract_sha256": contract.sha256,
            "reference_assets": [], "manual_prompt_override": False}
