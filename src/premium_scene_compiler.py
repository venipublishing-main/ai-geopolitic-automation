"""D.1 deterministic planning only. No jobs, providers, network or legacy fallback.

Live CLI ingestion retains daily readiness. Accepted snapshots are explicitly
historical inspection, not an alternative production-readiness gate.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date
import hashlib
import json
from pathlib import Path
import re

from PIL import Image

from .control_documents import Blocker
from .episode_manifest_v2 import load_canonical_characters, validate_manifest_v2
from .premium_typography import fit_text
from .scene_contract import (PortraitPlan, SceneContract, SemanticObject, Zone, canonical_json, digest)
from .semantic_ownership import reviewed_depiction, visual_brief_for, DEPICTION_GUARDS, PHYSICAL_ARCHITECTURE_CONCEPTS

ROOT = Path(__file__).resolve().parents[1]

# Explicit vocabulary, not inference from isolated keywords. New upstream
# combinations require a reviewed mapping; unknown families fail closed.
FAMILY_ALIASES = {
    "system_map": ("systems synthesis", "synthesis map + dependency gates", "synthesis wheel + evidence labels"),
    "evidence_dossier": ("evidence dossier + boundary rail",),
    "physical_stack": ("architecture stack", "physical / technical system", "physical dependency stack"),
    "layered_system": ("synthesis stack",),
    "dependency_chain": ("network-to-physical transition", "queue/network", "cost curve + consequence chain", "material burden / consequence"),
    "institutional_sequence": ("institutional sequence", "permit ladder + status map", "authority gate + precedent chain"),
    "allocation_flow": ("economic / allocation flow", "capital-flow + retention scorecard", "cost allocation flow", "value_flow"),
    "regional_pathway": ("regional / sovereignty pathway", "layered local map + sovereignty framework"),
    "feedback_loop": ("monitoring feedback loop", "feedback system", "monitoring cycle"),
    "comparison_field": ("investment opportunity comparison", "comparison",),
    "decision_tree": ("authority chain + decision tree",),
}


def _normalise(value):
    return " ".join(value.lower().replace("_", " ").split())


FAMILIES = {_normalise(alias): family for family, aliases in FAMILY_ALIASES.items()
            for alias in (family, *aliases)}

# Tendencies compose with argument geometry, never dispatch to old layout names.
GRAMMARS = {
    "nora": ("system_axis", "left", "balanced axes", "axis ticks", "first tier"),
    "diane_sterling": ("market_grid", "right", "transmission rails", "measurement ticks", "rail terminals"),
    "johan_vosloo": ("institutional_spine", "left", "rectilinear gates", "numbered stages", "gate edges"),
    "kai_patel": ("network_mesh", "right", "node junctions", "repair nodes", "node terminals"),
    "thabo_mokoena": ("burden_ledger", "left", "asymmetric pressure", "ledger strikes", "pressure edge"),
    "amari_ndlovu": ("regional_memory", "right", "contour arcs", "continuity rings", "regional path"),
}


class SceneCompileError(ValueError):
    def __init__(self, code, message=None, path="slide"):
        self.blocker = Blocker(code, message or code, path)
        super().__init__(code)


def _configuration():
    characters = load_canonical_characters()
    grammar = json.loads((ROOT / "config/layout_presets.json").read_text(encoding="utf-8"))
    return characters, grammar


def _portrait_config(panelist, characters, grammars):
    try:
        config = characters[panelist]
        grammar = grammars[panelist]
        if grammar["identity_grammar"] != GRAMMARS[panelist][0]:
            raise ValueError()
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", config["accent"]) or not config["name"].strip():
            raise ValueError()
        path = (ROOT / config["portrait"]).resolve()
        if not path.is_relative_to((ROOT / "assets/characters").resolve()):
            raise ValueError()
        crop = tuple(config["crop_box"])
        if len(crop) != 4 or any(type(n) is not int for n in crop):
            raise ValueError()
        with Image.open(path) as image:
            image.load()
            if not (0 <= crop[0] < crop[2] <= image.width and 0 <= crop[1] < crop[3] <= image.height):
                raise ValueError()
        return config, grammar, hashlib.sha256(path.read_bytes()).hexdigest()
    except (KeyError, TypeError, ValueError, OSError):
        raise SceneCompileError("PORTRAIT_CONFIGURATION_INVALID") from None


def _validate(manifest, characters):
    try:
        errors = validate_manifest_v2(manifest, characters)
    except (KeyError, TypeError, AttributeError, ValueError):
        raise SceneCompileError("MANIFEST_INVALID") from None
    if errors:
        raise SceneCompileError("MANIFEST_INVALID", canonical_json([asdict(b) for b in errors]), "manifest")


def compile_scene(manifest, slide_number, *, characters=None, grammars=None) -> SceneContract:
    defaults, default_grammars = _configuration()
    characters = defaults if characters is None else characters
    grammars = default_grammars if grammars is None else grammars
    _validate(manifest, characters)
    if type(slide_number) is not int or not 1 <= slide_number <= 20:
        raise SceneCompileError("SLIDE_NUMBER_INVALID")
    slide = manifest["slides"][slide_number - 1]
    if len(slide["panelists"]) != 1:
        raise SceneCompileError("DUAL_PANELIST_NOT_SUPPORTED_D1")
    panelist = slide["panelists"][0]
    if panelist not in GRAMMARS:
        raise SceneCompileError("UNKNOWN_PANELIST")
    config, grammar, portrait_hash = _portrait_config(panelist, characters, grammars)
    family = FAMILIES.get(_normalise(slide["preferred_visual_reasoning_family"]))
    if family is None:
        raise SceneCompileError("UNSUPPORTED_REASONING_FAMILY")
    # Reject explicit ownership conflicts; natural-language compliance still
    # requires human review. This is not a semantic verifier of arbitrary prose.
    if re.search(r"\b(?:render|write|print|include|generate)\s+(?:the\s+)?(?:headline|typography|logo|watermark|panelist portrait)\b|\b(?:pixel coordinates|photorealistic panelist)\b",
                 slide["hero_visual"], re.I):
        raise SceneCompileError("ART_REQUIREMENT_NOT_REPRESENTABLE")
    labels = slide["essential_labels"]
    if len(labels) > 8 or len(set(labels)) != len(labels):
        raise SceneCompileError("LABEL_CAPACITY_EXCEEDED")
    if family == "physical_stack" and len(set(labels) & PHYSICAL_ARCHITECTURE_CONCEPTS) < 2:
        raise SceneCompileError("PHYSICAL_STACK_SEMANTICS_REQUIRED")
    percentages = re.findall(r"(\d+(?:\.\d+)?)\s*(?:[–-]\s*(\d+(?:\.\d+)?))?\s*%", slide["portrait_scale_intention"])
    if len(percentages) != 1:
        raise SceneCompileError("PORTRAIT_SCALE_UNSUPPORTED")
    lower, upper = percentages[0]
    scale = (float(lower) + float(upper or lower)) / 200
    if not .18 <= scale <= .26:
        raise SceneCompileError("PORTRAIT_SCALE_UNSUPPORTED")
    tendency, side, shape, micro, accent_behaviour = GRAMMARS[panelist]
    if family in {"comparison_field", "feedback_loop", "decision_tree"}:
        side = "right" if side == "left" else "left"
    portrait_x = .04 if side == "left" else .96 - scale
    py = .38 if family in {"regional_pathway", "dependency_chain"} else .35
    portrait_zone = Zone(portrait_x, py, portrait_x + scale, py + .36)
    protected = Zone(portrait_x + .02, py + .01, portrait_x + scale - .02, py + .28)
    transition = Zone(portrait_x, py + .29, portrait_x + scale, py + .36)
    portrait = PortraitPlan(side, scale, "mid" if py == .35 else "lower_mid", portrait_zone,
        protected, transition, 0, config["portrait"], tuple(config["crop_box"]), portrait_hash)
    vertical = family in {"physical_stack", "institutional_sequence"}
    hero_left, hero_right = ((portrait_x + scale + .025, .96) if side == "left" else (.04, portrait_x - .025))
    if vertical:
        # Takeaways occupy a separate side rail, never the portrait's face.
        if side == "left":
            hero_right = .68
            take_x = (.71, .96)
        else:
            hero_left = .32
            take_x = (.04, .29)
    hero = Zone(hero_left, .36, hero_right, .75 if not vertical else .77)
    hero_pixels = hero.pixels()
    hw, hh = hero_pixels[2]-hero_pixels[0], hero_pixels[3]-hero_pixels[1]
    art_size = min(hw, hh)
    art_region = Zone((hw-art_size)/2/hw, (hh-art_size)/2/hh,
                      (hw+art_size)/2/hw, (hh+art_size)/2/hh)
    quiet = (Zone(0, 0, .31, 1), Zone(.69, 0, 1, 1))
    objects = []
    rows = (len(labels) + 1) // 2
    for i, label in enumerate(labels):
        # Ordered label pairs have disjoint lanes. Zones vary by argument;
        # structural links express reading order, not invented causal facts.
        row, col = divmod(i, 2)
        cy = (row + .5) / rows
        cx = .42 if col == 0 else .58
        if family in {"physical_stack", "institutional_sequence"}:
            cx = .5
            cy = (i + .5) / len(labels)
        elif family in {"regional_pathway", "allocation_flow"}:
            cx = .40 + .20 * row / max(1, rows - 1) + (-.07 if col == 0 else .07)
        elif family in {"system_map", "feedback_loop"}:
            cx = .40 if (row + col) % 2 == 0 else .60
        radius_y = min(.055, .4 / len(labels))
        cx = art_region.x0 + cx * (art_region.x1-art_region.x0)
        cy = art_region.y0 + cy * (art_region.y1-art_region.y0)
        radius_x = .045 * (art_region.x1-art_region.x0)
        radius_y *= art_region.y1-art_region.y0
        zone = Zone(cx - radius_x, cy - radius_y, cx + radius_x, cy + radius_y)
        annotation_zone = Zone(.015 if col == 0 else .705, row / rows + .012,
                               .295 if col == 0 else .985, (row + 1) / rows - .012)
        label_plan = fit_text(label, annotation_zone, "annotation", kind="label", start=22,
                              minimum=14, parent=hero_pixels)
        anchor = (.30 if col == 0 else .70, annotation_zone.centre[1])
        leader = (anchor, ((anchor[0] + cx) / 2, anchor[1]), zone.centre)
        links = (f"object_{i - 1}",) if i and family != "layered_system" else ()
        role = "equal_condition" if family == "layered_system" else (
            "primary_system" if i == 0 else ("evidence_item" if family == "evidence_dossier" else "ordered_component"))
        try:
            depiction = reviewed_depiction(label)
        except ValueError as exc:
            raise SceneCompileError(str(exc)) from None
        objects.append(SemanticObject(f"object_{i}", label, zone, role,
            "left" if col == 0 else "right", 1.0 if i == 0 or family == "layered_system" else .7,
            links, label_plan, leader, depiction.ownership, depiction.concrete_visual, depiction.compositor_mark))
    headline_arrangement = "compact_stacked" if len(slide["headline"]) > 65 else "full_width_two_tier"
    headline_zone = Zone(.04, .105, .96, .245)
    if family == "regional_pathway" and len(slide["headline"]) < 50:
        headline_arrangement = "right_weighted" if side == "left" else "left_weighted"
        headline_zone = Zone(.18 if side == "left" else .04, .105, .96 if side == "left" else .82, .245)
    headline = fit_text(slide["headline"], headline_zone, headline_arrangement, kind="display", start=68, minimum=38)
    subheadline = fit_text(slide["subheadline"], Zone(.04, .26, .96, .33), "deck", start=25, minimum=19)
    phrase_style = {"system_map": "accent_block", "evidence_dossier": "doctrine_strip",
        "institutional_sequence": "doctrine_strip", "regional_pathway": "engraved_pull_quote",
        "feedback_loop": "hero_integrated_callout"}.get(family, "engraved_pull_quote")
    phrase = fit_text(slide["main_visual_phrase"], Zone(.04, .795, .96, .86), phrase_style,
                      kind="display", start=36, minimum=24)
    arrangement = "numbered_vertical_rail" if vertical else (
        "three_node_sequence" if family in {"dependency_chain", "regional_pathway", "feedback_loop", "allocation_flow"} else "three_column_rail")
    takeaways = []
    for i, item in enumerate(slide["takeaway_ideas"]):
        if vertical:
            zone = Zone(take_x[0], .37 + i * .135, take_x[1], .49 + i * .135)
        else:
            zone = Zone(.04 + i * .31, .89, .33 + i * .31, .955)
        takeaways.append(fit_text(item["idea"], zone, arrangement, start=23, minimum=17))
    published_date = date.fromisoformat(manifest["production_date_sast"])
    furniture_copy = ("AI GEOPOLITIC / VENI PUBLISHING", f"{manifest['episode_id']} / {published_date.isoformat()} / {slide_number:02d}/20",
                      "The event is factual. The interpretation ideological.", config["name"])
    furniture_zones = (Zone(.04, .04, .60, .08), Zone(.61, .04, .96, .08),
        Zone(.04, .97, .96, .998), Zone(portrait_x, py + .37, portrait_x + scale, py + .415))
    furniture = tuple(fit_text(text, z, "furniture", kind="label", start=17, minimum=12)
                      for text, z in zip(furniture_copy, furniture_zones))
    route = "radial" if family == "system_map" else (
        "closed_loop" if family == "feedback_loop" else "branch" if family == "decision_tree" else
        "parallel" if family in {"comparison_field", "evidence_dossier", "layered_system"} else "ordered_path")
    return SceneContract(2, manifest["episode_id"], manifest["production_date_sast"], slide_number,
        panelist, config["name"], config["accent"], tendency, family, route, micro, shape,
        "equal condition nodes" if family == "layered_system" else accent_behaviour,
        hero, art_region, quiet, tuple(objects), portrait, headline, subheadline, phrase,
        arrangement, tuple(takeaways), furniture, digest(manifest), digest((config, grammar)),
        canonical_json(slide), canonical_json(grammar), visual_brief_for(family,len(labels)), DEPICTION_GUARDS.get(family, ()))


def compile_episode(manifest):
    characters, _ = _configuration()
    report = {"state": "D1_INSPECTION_ONLY", "expected_generation_count": 0,
              "provider_submissions": 0, "production_publication": "BLOCKED", "slides": [], "blockers": []}
    try:
        _validate(manifest, characters)
    except SceneCompileError as exc:
        report["blockers"].append(asdict(exc.blocker))
        return report
    report.update(episode_id=manifest["episode_id"], production_date_sast=manifest["production_date_sast"],
                  manifest_sha256=digest(manifest))
    for slide in manifest["slides"]:
        row = {"slide_number": slide["slide_number"], "panelists": slide["panelists"],
               "expected_generation_count": 0, "blockers": []}
        try:
            contract = compile_scene(manifest, slide["slide_number"])
            prompt = compile_prompt(contract)
            row.update(state="CONTRACT_COMPILED", contract=contract.to_dict(),
                       contract_sha256=contract.sha256, prompt=prompt, prompt_sha256=digest(prompt))
        except SceneCompileError as exc:
            row.update(state="BLOCKED", blockers=[asdict(exc.blocker)])
        except ValueError as exc:
            row.update(state="BLOCKED", blockers=[asdict(Blocker(str(exc), "Copy cannot fit the supported contract.", "slide"))])
        report["slides"].append(row)
    return report


def compile_prompt(contract: SceneContract):
    # D.1 inspection/QA uses the same ownership-safe conditioning as SDXL.
    from .premium_sdxl_prompt import compile_sdxl_prompt
    return compile_sdxl_prompt(contract)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--source", choices=("drive", "local"))
    mode.add_argument("--accepted-snapshot", type=Path)
    parser.add_argument("--dry-run", action="store_true", required=True)
    parser.add_argument("--rnd-file", type=Path)
    parser.add_argument("--slide-design-file", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.accepted_snapshot:
            if args.rnd_file or args.slide_design_file:
                parser.error("Snapshot mode does not accept live input overrides.")
            snapshot = json.loads(args.accepted_snapshot.read_text(encoding="utf-8"))
            if not isinstance(snapshot, dict) or not isinstance(snapshot.get("manifest"), dict):
                raise ValueError("ACCEPTED_SNAPSHOT_INVALID")
            if (snapshot.get("build") != "READY" or snapshot.get("state") != "BUILD_READY" or
                    snapshot.get("blockers") != [] or snapshot.get("production_date_sast") != snapshot.get("manifest", {}).get("production_date_sast") or
                    snapshot.get("production_date_sast") != snapshot.get("manifest", {}).get("source_rnd_date_sast")):
                raise ValueError("ACCEPTED_SNAPSHOT_INVALID")
            result = compile_episode(snapshot["manifest"])
            result["input_mode"] = "ACCEPTED_SNAPSHOT_HISTORICAL_REPLAY"
            result["current_build_readiness"] = "NOT_ASSERTED"
        else:
            from .daily_readiness import DailyBuildReadiness
            from .production_inputs import LocalFileInput, RcloneDriveInput
            if args.source == "drive":
                if args.rnd_file or args.slide_design_file:
                    parser.error("Drive mode does not accept local input overrides.")
                source = RcloneDriveInput.from_environment()
            else:
                if not args.rnd_file or not args.slide_design_file:
                    parser.error("Local mode requires both input files.")
                source = LocalFileInput(args.rnd_file, args.slide_design_file)
            readiness = DailyBuildReadiness().check(source)
            if not readiness.ready:
                result = {"state": "BUILD_BLOCKED", "blockers": [asdict(b) for b in readiness.blockers],
                          "slides": [], "expected_generation_count": 0}
            else:
                result = compile_episode(readiness.manifest)
            result["input_mode"] = "CURRENT_DAILY_READINESS"
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"state": "BLOCKED", "expected_generation_count": 0, "slides": [],
                  "blockers": [asdict(Blocker("INPUT_INVALID", str(exc), "source"))]}
    # ASCII escapes preserve exact Unicode copy on Windows redirected stdout.
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 1 if result["blockers"] or any(s["blockers"] for s in result["slides"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
