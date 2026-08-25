from __future__ import annotations

import argparse
import importlib
import json
import re
from collections import Counter
from pathlib import Path

try:
    from .editorial_primitives import ensure
    from .make_contact_sheet import make_contact_sheet
    from .route_episode import (
        RENDER_MODULES,
        load_json,
        select_layout,
        validate_routing_config,
    )
except ImportError:
    from editorial_primitives import ensure
    from make_contact_sheet import make_contact_sheet
    from route_episode import RENDER_MODULES, load_json, select_layout, validate_routing_config


SCHEMA_VERSION = 1
TOTAL_SLIDES = 20
COMMON_SLIDE_FIELDS = {
    "speaker",
    "content_type",
    "layout_override",
    "headline",
    "deck",
    "quote",
    "facts",
    "takeaway",
    "visual",
}
FORBIDDEN_PRODUCTION_FIELDS = {
    "slide_number",
    "total_slides",
    "layout_family",
    "source_input",
    "expected_layout",
    "content_overrides",
}
VISUAL_RESERVED_FIELDS = {
    "slide_number",
    "total_slides",
    "speaker",
    "layout_family",
    "headline",
    "deck",
    "quote",
    "facts",
    "takeaway",
    "episode_date",
    "episode_title",
    "content_type",
    "layout_override",
    "source_input",
}


def _nonblank(value, label: str) -> str:
    ensure(isinstance(value, str) and value.strip(), f"{label} must be a non-empty string.")
    return value.strip()


def _validate_slide_copy(slide: dict, index: int) -> None:
    forbidden = sorted(FORBIDDEN_PRODUCTION_FIELDS.intersection(slide))
    ensure(not forbidden,
           f"Production slide {index} contains compiler-owned fields: {', '.join(forbidden)}.")

    _nonblank(slide.get("headline"), f"Slide {index} headline")
    _nonblank(slide.get("deck"), f"Slide {index} deck")
    _nonblank(slide.get("quote"), f"Slide {index} quote")
    _nonblank(slide.get("takeaway"), f"Slide {index} takeaway")

    facts = slide.get("facts")
    ensure(isinstance(facts, list) and 1 <= len(facts) <= 6,
           f"Slide {index} facts must contain 1-6 items.")
    for fact_index, fact in enumerate(facts, start=1):
        _nonblank(fact, f"Slide {index} fact {fact_index}")

    visual = slide.get("visual", {})
    ensure(isinstance(visual, dict), f"Slide {index} visual must be an object when supplied.")
    collisions = sorted(VISUAL_RESERVED_FIELDS.intersection(visual))
    ensure(not collisions,
           f"Slide {index} visual contains reserved fields: {', '.join(collisions)}.")


def validate_production_manifest(manifest: dict, routing: dict, presets: dict) -> list[dict]:
    ensure(manifest.get("schema_version") == SCHEMA_VERSION,
           f"Production episode schema_version must be {SCHEMA_VERSION}.")
    episode_id = _nonblank(manifest.get("episode_id"), "episode_id")
    ensure(re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,79}", episode_id),
           "episode_id must be a lowercase filesystem-safe slug (3-80 characters).")
    _nonblank(manifest.get("episode_title"), "episode_title")
    _nonblank(manifest.get("episode_date"), "episode_date")

    slides = manifest.get("slides")
    ensure(isinstance(slides, list) and len(slides) == TOTAL_SLIDES,
           f"A production episode must contain exactly {TOTAL_SLIDES} slides.")

    resolved_layouts: list[str] = []
    for index, slide in enumerate(slides, start=1):
        ensure(isinstance(slide, dict), f"Production slide {index} must be an object.")
        ensure(slide.get("speaker") in RENDER_MODULES,
               f"Production slide {index} has unknown speaker {slide.get('speaker')!r}.")
        _validate_slide_copy(slide, index)
        selected, _ = select_layout(slide, routing, presets)
        resolved_layouts.append(selected)

        if index == 1:
            ensure(slide["speaker"] == "nora" and selected == "episode_opener",
                   "Production slide 1 must be NORA routed to episode_opener.")
        elif index == TOTAL_SLIDES:
            ensure(slide["speaker"] == "nora" and selected == "episode_closer",
                   "Production slide 20 must be NORA routed to episode_closer.")
        else:
            ensure(selected not in {"episode_opener", "episode_closer"},
                   f"Production slide {index} cannot use the full episode opener/closer layout.")

    return slides


def compile_slide(manifest: dict, slide: dict, index: int, routing: dict, presets: dict) -> tuple[dict, dict]:
    selected, selection_source = select_layout(slide, routing, presets)
    spec = {
        "slide_number": index,
        "total_slides": TOTAL_SLIDES,
        "speaker": slide["speaker"],
        "layout_family": selected,
        "headline": slide["headline"],
        "deck": slide["deck"],
        "quote": slide["quote"],
        "facts": slide["facts"],
        "takeaway": slide["takeaway"],
    }
    visual = slide.get("visual") or {}
    spec.update(visual)

    if selected in {"episode_opener", "episode_closer"}:
        spec["episode_date"] = manifest["episode_date"]
        spec["episode_title"] = manifest["episode_title"]

    audit = {
        "slide_number": index,
        "speaker": slide["speaker"],
        "content_type": slide.get("content_type"),
        "selected_layout": selected,
        "selection_source": selection_source,
        "layout_override": slide.get("layout_override"),
        "visual_keys": sorted(visual),
    }
    return spec, audit


def render_production_episode(manifest_path: Path, output_dir: Path) -> dict:
    root = Path(__file__).resolve().parents[1]
    manifest = load_json(manifest_path)
    routing = load_json(root / "config/layout_routing.json")
    presets = load_json(root / "config/layout_presets.json")
    validate_routing_config(routing, presets)
    slides = validate_production_manifest(manifest, routing, presets)

    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_dir = output_dir / "resolved-inputs"
    resolved_dir.mkdir(parents=True, exist_ok=True)

    audit_rows: list[dict] = []
    output_paths: list[Path] = []
    resolved_episode = {
        "schema_version": SCHEMA_VERSION,
        "episode_id": manifest["episode_id"],
        "episode_title": manifest["episode_title"],
        "episode_date": manifest["episode_date"],
        "slides": [],
    }

    for index, slide in enumerate(slides, start=1):
        spec, audit = compile_slide(manifest, slide, index, routing, presets)
        resolved_path = resolved_dir / f"slide_{index:02d}.json"
        resolved_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        output_path = output_dir / f"slide_{index:02d}.png"

        module = importlib.import_module(RENDER_MODULES[slide["speaker"]])
        module.render(resolved_path, output_path)
        ensure(output_path.exists(), f"Renderer did not create production slide {index}.")

        audit["resolved_input"] = str(resolved_path.relative_to(output_dir))
        audit["output"] = str(output_path.relative_to(output_dir))
        audit_rows.append(audit)
        output_paths.append(output_path)
        resolved_episode["slides"].append(spec)

    contact_sheet = output_dir / "episode-contact-sheet.png"
    make_contact_sheet(output_paths, contact_sheet, cols=4, thumb=250, label_height=28)

    (output_dir / "resolved-episode.json").write_text(
        json.dumps(resolved_episode, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    speaker_counts = Counter(row["speaker"] for row in audit_rows)
    layout_counts = Counter(row["selected_layout"] for row in audit_rows)
    report = {
        "schema_version": SCHEMA_VERSION,
        "episode_id": manifest["episode_id"],
        "episode_title": manifest["episode_title"],
        "episode_date": manifest["episode_date"],
        "total_slides": TOTAL_SLIDES,
        "routing_policy": routing.get("selection_policy"),
        "override_count": sum(1 for row in audit_rows if row["selection_source"] == "explicit_override"),
        "speaker_counts": dict(sorted(speaker_counts.items())),
        "layout_counts": dict(sorted(layout_counts.items())),
        "slides": audit_rows,
    }
    (output_dir / "production-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    md = [
        "# AI Geopolitic Milestone 4.5 Production Schema Report",
        "",
        f"Episode: **{manifest['episode_title']}**",
        f"Episode ID: `{manifest['episode_id']}`",
        f"Date: **{manifest['episode_date']}**",
        f"Slides: **{TOTAL_SLIDES}**",
        f"Routing policy: `{routing.get('selection_policy')}`",
        "",
        "| Slide | Speaker | Content type | Selected layout | Visual payload |",
        "|---:|---|---|---|---|",
    ]
    for row in audit_rows:
        visual = ", ".join(row["visual_keys"]) if row["visual_keys"] else "—"
        md.append(
            f"| {row['slide_number']:02d} | {row['speaker']} | {row['content_type']} | "
            f"{row['selected_layout']} | {visual} |"
        )
    md += [
        "",
        "The production schema owns editorial content only. Slide numbering, total slide count and layout_family are compiler-owned and are injected after validation.",
        "Unknown content types, unapproved overrides, invalid opener/closer placement, reserved-field collisions and renderer layout failures stop the run.",
    ]
    (output_dir / "production-report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = render_production_episode(args.manifest, args.output_dir)
    print(f"Rendered production episode: {result['total_slides']} slides -> {args.output_dir.resolve()}")
