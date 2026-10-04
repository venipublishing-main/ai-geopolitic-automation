"""Spatial SDXL conditioning from SceneContract only, with no reference images."""
from .scene_contract import SceneContract, digest


def _location(x, y):
    horizontal = "left" if x < .38 else "right" if x > .62 else "centre"
    vertical = "upper" if y < .34 else "lower" if y > .66 else "middle"
    return f"{vertical}-{horizontal}"


def compile_sdxl_prompt(contract: SceneContract):
    from .semantic_ownership import visual_brief_for, DEPICTION_GUARDS
    if (contract.visual_brief != visual_brief_for(contract.reasoning_family,len(contract.semantic_objects)) or
            contract.depiction_guardrails != DEPICTION_GUARDS.get(contract.reasoning_family, ())):
        raise ValueError("VISUAL_BRIEF_AUTHORITY_MISMATCH")
    if "###" in contract.slide_json:
        raise ValueError("SDXL_DELIMITER_IN_MANIFEST")
    a = contract.art_region
    positive = ["ONE COHERENT TEXT-FREE EDITORIAL ILLUSTRATION. Black-ink newspaper engraving on warm off-white paper, precise cross-hatching, physical depth.",
                "No text, letters, numbers, visible labels, canonical portrait or publishing furniture. The compositor owns those separately.",
                contract.visual_brief]
    for obj in contract.semantic_objects:
        # Reviewed concrete descriptions only. Abstract names, label strings,
        # editorial copy and raw Manifest composition prose never condition SDXL.
        from .semantic_ownership import reviewed_depiction, COMPOSITOR_ABSTRACT
        depiction = reviewed_depiction(obj.label)
        if (obj.ownership, obj.concrete_visual, obj.compositor_mark) != (
                depiction.ownership, depiction.concrete_visual, depiction.compositor_mark):
            raise ValueError("SEMANTIC_OWNERSHIP_AUTHORITY_MISMATCH")
        if obj.ownership == COMPOSITOR_ABSTRACT:
            continue
        x, y = obj.zone.centre
        x, y = (x-a.x0)/(a.x1-a.x0), (y-a.y0)/(a.y1-a.y0)
        positive.append(f"Within the shared scene: {obj.concrete_visual}; {_location(x,y)} region (centre {x:.3f},{y:.3f}), emphasis {obj.importance:.1f}.")
    for z in contract.quiet_zones:
        x0, x1 = max(z.x0, a.x0), min(z.x1, a.x1)
        if x0 < x1:
            positive.append(f"Quiet negative-paper margin across raster x={(x0-a.x0)/(a.x1-a.x0):.3f}..{(x1-a.x0)/(a.x1-a.x0):.3f}.")
    positive.extend(contract.depiction_guardrails)
    negative = ("text, letters, words, typography, captions, labels, signage, logo, branding, watermark, signature, "
                "copyright mark, fake UI, dashboard, poster, collage, contact sheet, cyberpunk, neon, "
                "panelist portrait, celebrity likeness, literal fluffy cloud, cartoon cloud, speech bubble, "
                "infographic, diagram page, evidence cards, labelled stack, consulting diagram")
    if contract.reasoning_family == "layered_system":
        negative += ", pyramid, triangle hierarchy, tiered pyramid, maturity ladder, staircase hierarchy, funnel, pentagon"
    # One delimiter is the existing Horde SDXL CLIP-conditioning handshake.
    return "\n".join(positive) + "###" + negative


def prompt_record(contract):
    prompt = compile_sdxl_prompt(contract)
    positive, negative = prompt.split("###")
    return {"prompt": prompt, "positive": positive, "negative": negative,
            "prompt_sha256": digest(prompt), "contract_sha256": contract.sha256,
            "reference_assets": [], "manual_prompt_override": False}
