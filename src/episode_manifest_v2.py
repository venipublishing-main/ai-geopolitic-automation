"""Manifest v2 handoff validation. No layout selection or rendering."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .control_documents import Blocker, parse_iso_date

PAIRING_MODES = frozenset({"SUPPORTIVE_CONVERGENT", "OPPOSING_FACE_OFF",
                           "QUALIFIED_TENSION", "SYNTHESIS_COMPLEMENTARY"})
TOP_FIELDS = frozenset({"schema_version", "episode_id", "episode_title", "production_date_sast",
                        "source_rnd_date_sast", "archive_destination", "archive_folder_id", "slides"})
COPY_FIELDS = frozenset({"slide_role", "core_argument", "headline", "subheadline", "hero_visual",
                         "main_visual_phrase", "composition_notes", "notices_first",
                         "preferred_visual_reasoning_family", "anti_cliche_guardrail",
                         "portrait_scale_intention", "density_type_size_note"})
LIST_FIELDS = frozenset({"essential_labels", "factual_guardrails", "visual_psychology_traits"})
DUAL_FIELDS = frozenset({"shared_ground", "panelist_contributions", "central_relationship", "why_dual"})
SLIDE_FIELDS = COPY_FIELDS | LIST_FIELDS | DUAL_FIELDS | {
    "slide_number", "panelists", "pairing_mode", "takeaway_ideas", "accent_colours"}


def load_canonical_characters() -> dict:
    return json.loads((Path(__file__).resolve().parents[1] / "config/characters.json").read_text(encoding="utf-8"))


def nonblank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_manifest_v2(manifest: object, characters: dict) -> list[Blocker]:
    errors: list[Blocker] = []

    def check(ok, code, message, path):
        if not ok:
            errors.append(Blocker(code, message, path))

    def fields(value, expected, path):
        for key in sorted(expected - value.keys()):
            errors.append(Blocker("MANIFEST_FIELD_MISSING", f"Required field {key} is missing.", f"{path}.{key}"))
        for key in sorted(value.keys() - expected):
            errors.append(Blocker("MANIFEST_FIELD_UNSUPPORTED", f"Unsupported field {key}.", f"{path}.{key}"))

    if not isinstance(manifest, dict):
        return [Blocker("MANIFEST_INVALID", "Manifest must be a JSON object.", "manifest")]
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 2:
        return [Blocker("MANIFEST_SCHEMA_UNSUPPORTED", "schema_version must be the integer 2.", "schema_version")]
    fields(manifest, TOP_FIELDS, "manifest")
    for key in sorted(TOP_FIELDS - {"schema_version", "slides"}):
        check(nonblank(manifest.get(key)), "MANIFEST_FIELD_INVALID", f"{key} must be nonblank text.", key)
    for key in ("production_date_sast", "source_rnd_date_sast"):
        try:
            parse_iso_date(manifest.get(key))
        except ValueError:
            errors.append(Blocker("MANIFEST_DATE_INVALID", "Require a valid YYYY-MM-DD date.", key))
    episode_id = manifest.get("episode_id")
    check(isinstance(episode_id, str) and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", episode_id)),
          "MANIFEST_FIELD_INVALID", "episode_id must be a 1-80 character safe identifier.", "episode_id")
    folder = manifest.get("archive_folder_id")
    check(isinstance(folder, str) and bool(re.fullmatch(r"[A-Za-z0-9_-]+", folder)),
          "ARCHIVE_FOLDER_MISSING", "Require a nonblank Drive folder ID (not a URL).", "archive_folder_id")
    slides = manifest.get("slides")
    if not isinstance(slides, list):
        return errors + [Blocker("SLIDE_COUNT_INVALID", "slides must be an array of exactly 20 objects.", "slides")]
    check(len(slides) == 20, "SLIDE_COUNT_INVALID", "Require exactly 20 slides.", "slides")
    for index, slide in enumerate(slides, 1):
        path = f"slides[{index - 1}]"
        if not isinstance(slide, dict):
            errors.append(Blocker("SLIDE_INVALID", "Slide must be an object.", path))
            continue
        fields(slide, SLIDE_FIELDS, path)
        check(type(slide.get("slide_number")) is int and slide["slide_number"] == index,
              "SLIDE_NUMBER_INVALID", f"Slide at position {index} must have slide_number {index}.", path)
        for key in sorted(COPY_FIELDS):
            check(nonblank(slide.get(key)), "SLIDE_COPY_INVALID", f"{key} must be nonblank text.", f"{path}.{key}")
        for key in sorted(LIST_FIELDS):
            items = slide.get(key)
            check(isinstance(items, list) and bool(items) and all(nonblank(item) for item in items),
                  "SLIDE_FIELD_INVALID", f"{key} must be a nonempty array of nonblank strings.", f"{path}.{key}")
        takeaways = slide.get("takeaway_ideas")
        check(isinstance(takeaways, list) and len(takeaways) == 3,
              "TAKEAWAY_COUNT_INVALID", "Require exactly three takeaway ideas.", f"{path}.takeaway_ideas")
        if isinstance(takeaways, list):
            for number, idea in enumerate(takeaways):
                valid = isinstance(idea, dict) and set(idea) <= {"idea", "intended_visual_treatment"} and nonblank(idea.get("idea"))
                if valid and "intended_visual_treatment" in idea:
                    valid = nonblank(idea["intended_visual_treatment"])
                check(valid, "TAKEAWAY_INVALID", "Takeaway requires idea text and optional nonblank intended_visual_treatment.", f"{path}.takeaway_ideas[{number}]")
        panelists = slide.get("panelists")
        if not isinstance(panelists, list) or len(panelists) not in (1, 2) or not all(isinstance(p, str) for p in panelists):
            errors.append(Blocker("PANELIST_COUNT_INVALID", "Require one or two panelist slugs.", f"{path}.panelists"))
            continue
        check(all(p in characters for p in panelists), "UNKNOWN_PANELIST", "Panelists must exist in canonical character config.", f"{path}.panelists")
        check(len(set(panelists)) == len(panelists), "DUAL_PAIRING_INVALID", "Panelists must be distinct.", f"{path}.panelists")
        accents = slide.get("accent_colours")
        correct_accents = isinstance(accents, dict) and set(accents) == set(panelists)
        if correct_accents:
            correct_accents = all(isinstance(accents[p], str) and p in characters and
                                  accents[p].upper() == characters[p]["accent"].upper() for p in panelists)
        check(correct_accents, "ACCENT_COLOUR_INVALID", "accent_colours must map each panelist to their canonical hex accent.", f"{path}.accent_colours")
        contributions = slide.get("panelist_contributions")
        if len(panelists) == 2:
            mode = slide.get("pairing_mode")
            check(isinstance(mode, str) and mode in PAIRING_MODES, "DUAL_PAIRING_INVALID", "Require an approved dual pairing mode.", f"{path}.pairing_mode")
            for key in ("shared_ground", "central_relationship", "why_dual"):
                check(nonblank(slide.get(key)), "DUAL_PAIRING_INVALID", f"Dual slide requires nonblank {key}.", f"{path}.{key}")
            check(isinstance(contributions, dict) and set(contributions) == set(panelists) and all(nonblank(v) for v in contributions.values()),
                  "DUAL_PAIRING_INVALID", "Contributions must map exactly the two panelists to nonblank text.", f"{path}.panelist_contributions")
        else:
            check(slide.get("pairing_mode") is None, "SINGLE_PAIRING_INVALID", "Single slide pairing_mode must be null.", f"{path}.pairing_mode")
            for key in ("shared_ground", "central_relationship", "why_dual"):
                check(slide.get(key) in (None, ""), "SINGLE_PAIRING_INVALID", f"Single slide {key} must be null or empty text.", f"{path}.{key}")
            check(contributions is None or contributions == {} or
                  (isinstance(contributions, dict) and set(contributions) == set(panelists) and all(nonblank(v) for v in contributions.values())),
                  "SINGLE_PAIRING_INVALID", "Single contributions must be null, empty, or keyed to that panelist.", f"{path}.panelist_contributions")
    return errors
