from __future__ import annotations

import argparse
import importlib
import json
from collections import Counter
from pathlib import Path

try:
    from .editorial_primitives import LayoutError, ensure
    from .make_contact_sheet import make_contact_sheet
except ImportError:
    from editorial_primitives import LayoutError, ensure
    from make_contact_sheet import make_contact_sheet


RENDER_MODULES = {
    "nora": "render_nora_layout_family",
    "johan_vosloo": "render_johan_layout_family",
    "diane_sterling": "render_diane_layout_family",
    "kai_patel": "render_kai_layout_family",
    "thabo_mokoena": "render_thabo_layout_family",
    "amari_ndlovu": "render_amari_layout_family",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_routing_config(routing: dict, presets: dict) -> None:
    ensure(routing.get("version") == 1, "Unsupported layout routing config version.")
    speakers = routing.get("speakers")
    ensure(isinstance(speakers, dict), "layout_routing.json requires a speakers object.")
    ensure(set(speakers) == set(RENDER_MODULES), "Routing config must define exactly the six locked speakers.")

    for speaker, rules in speakers.items():
        content_types = rules.get("content_types")
        ensure(isinstance(content_types, dict) and content_types,
               f"Routing config for {speaker} requires content_types.")
        approved = set(presets[speaker]["approved_families"])
        for content_type, family in content_types.items():
            ensure(isinstance(content_type, str) and content_type.strip(),
                   f"Blank content type in routing config for {speaker}.")
            ensure(family in approved,
                   f"Routing config maps {speaker}/{content_type} to unapproved family {family}.")


def select_layout(slide: dict, routing: dict, presets: dict) -> tuple[str, str]:
    speaker = slide.get("speaker")
    ensure(speaker in RENDER_MODULES, f"Unknown speaker in routing request: {speaker}")
    approved = set(presets[speaker]["approved_families"])

    override = slide.get("layout_override")
    if override:
        ensure(override in approved,
               f"layout_override {override!r} is not approved for {speaker}.")
        return override, "explicit_override"

    content_type = slide.get("content_type")
    ensure(isinstance(content_type, str) and content_type.strip(),
           f"Slide for {speaker} requires content_type when no layout_override is supplied.")
    mapping = routing["speakers"][speaker]["content_types"]
    ensure(content_type in mapping,
           f"No deterministic layout route for {speaker}/{content_type}.")
    family = mapping[content_type]
    ensure(family in approved,
           f"Selected family {family} is not approved for {speaker}.")
    return family, "content_type_rule"


def validate_manifest(manifest: dict, root: Path) -> list[dict]:
    ensure(isinstance(manifest.get("episode_id"), str) and manifest["episode_id"].strip(),
           "Episode manifest requires episode_id.")
    slides = manifest.get("slides")
    ensure(isinstance(slides, list) and 3 <= len(slides) <= 20,
           "Routing proof manifest must contain 3-20 slides.")

    for index, item in enumerate(slides, start=1):
        ensure(isinstance(item, dict), f"Slide {index} routing entry must be an object.")
        ensure(item.get("speaker") in RENDER_MODULES,
               f"Slide {index} has unknown speaker {item.get('speaker')}.")
        source = item.get("source_input")
        ensure(isinstance(source, str) and source.strip(),
               f"Slide {index} requires source_input.")
        source_path = root / source
        ensure(source_path.exists(), f"Slide {index} source_input does not exist: {source}")
        source_data = load_json(source_path)
        ensure(source_data.get("speaker") == item["speaker"],
               f"Slide {index} speaker does not match source_input speaker.")
    return slides


def render_episode(manifest_path: Path, output_dir: Path) -> dict:
    root = Path(__file__).resolve().parents[1]
    manifest = load_json(manifest_path)
    routing = load_json(root / "config/layout_routing.json")
    presets = load_json(root / "config/layout_presets.json")
    validate_routing_config(routing, presets)
    slides = validate_manifest(manifest, root)

    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_dir = output_dir / "resolved-inputs"
    resolved_dir.mkdir(parents=True, exist_ok=True)
    total = len(slides)
    report_rows: list[dict] = []
    output_paths: list[Path] = []

    for slide_number, route in enumerate(slides, start=1):
        selected, selection_source = select_layout(route, routing, presets)
        expected = route.get("expected_layout")
        if expected:
            ensure(selected == expected,
                   f"Routing proof slide {slide_number}: expected {expected}, selected {selected}.")

        source_path = root / route["source_input"]
        spec = load_json(source_path)
        spec["slide_number"] = slide_number
        spec["total_slides"] = total
        spec["layout_family"] = selected

        if manifest.get("episode_date") and selected in {"episode_opener", "episode_closer"}:
            spec["episode_date"] = manifest["episode_date"]
        if isinstance(route.get("content_overrides"), dict):
            spec.update(route["content_overrides"])

        resolved_path = resolved_dir / f"slide_{slide_number:02d}.json"
        resolved_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        output_path = output_dir / f"slide_{slide_number:02d}.png"

        module = importlib.import_module(RENDER_MODULES[route["speaker"]])
        module.render(resolved_path, output_path)
        ensure(output_path.exists(), f"Renderer did not create slide {slide_number}.")
        output_paths.append(output_path)

        report_rows.append({
            "slide_number": slide_number,
            "speaker": route["speaker"],
            "content_type": route.get("content_type"),
            "selected_layout": selected,
            "selection_source": selection_source,
            "source_input": route["source_input"],
            "resolved_input": str(resolved_path.relative_to(output_dir)),
            "output": str(output_path.relative_to(output_dir)),
        })

    contact_sheet = output_dir / "routing-contact-sheet.png"
    make_contact_sheet(output_paths, contact_sheet, cols=4, thumb=250, label_height=28)

    counts = Counter(row["speaker"] for row in report_rows)
    family_counts = Counter(row["selected_layout"] for row in report_rows)
    report = {
        "episode_id": manifest["episode_id"],
        "episode_title": manifest.get("episode_title"),
        "episode_date": manifest.get("episode_date"),
        "total_slides": total,
        "routing_policy": routing.get("selection_policy"),
        "speaker_counts": dict(sorted(counts.items())),
        "layout_counts": dict(sorted(family_counts.items())),
        "slides": report_rows,
    }
    (output_dir / "routing-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    md = [
        "# AI Geopolitic Milestone 4.4 Routing Report",
        "",
        f"Episode: **{manifest.get('episode_title', manifest['episode_id'])}**",
        f"Slides: **{total}**",
        f"Policy: `{routing.get('selection_policy')}`",
        "",
        "| Slide | Speaker | Content type | Selected layout | Route source |",
        "|---:|---|---|---|---|",
    ]
    for row in report_rows:
        md.append(
            f"| {row['slide_number']:02d} | {row['speaker']} | {row['content_type']} | "
            f"{row['selected_layout']} | {row['selection_source']} |"
        )
    md += [
        "",
        "The routing proof fails closed: unknown content types, unapproved overrides, speaker/source mismatches, or renderer layout errors stop the run rather than falling back silently.",
    ]
    (output_dir / "routing-report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = render_episode(args.manifest, args.output_dir)
    print(f"Rendered {result['total_slides']} routed slides to {args.output_dir.resolve()}")
