"""Pure, deterministic parsing of exported daily control-document text."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date

PAYLOAD_BEGIN = "=== BEGIN DAILY PAYLOAD ==="
PAYLOAD_END = "=== END DAILY PAYLOAD ==="
MANIFEST_BEGIN = "=== BEGIN AUTOMATION MANIFEST JSON ==="
MANIFEST_END = "=== END AUTOMATION MANIFEST JSON ==="


@dataclass(frozen=True)
class Blocker:
    code: str
    message: str
    path: str = ""


class ControlDocumentError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def extract_block(text: str, begin: str, end: str, prefix: str) -> str:
    """Require exactly one ordered pair of standalone, literal marker lines."""
    if begin not in text and end not in text:
        raise ControlDocumentError(f"{prefix}_MISSING", f"Missing {begin} block.")
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ControlDocumentError(f"{prefix}_AMBIGUOUS", "Require exactly one begin/end marker pair.")
    lines = text.splitlines()
    if begin not in lines or end not in lines or lines.index(begin) >= lines.index(end):
        raise ControlDocumentError(f"{prefix}_INVALID", "Markers must be standalone lines in begin/end order.")
    return "\n".join(lines[lines.index(begin) + 1:lines.index(end)])


def parse_iso_date(value: object) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Date must be YYYY-MM-DD.")
    return date.fromisoformat(value)


ENGLISH_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}
ENGLISH_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
EPISODE_ID_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}"


def parse_control_date(value: str) -> date:
    """Human metadata accepts ISO or a complete English weekday/day/month/year."""
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return parse_iso_date(value)
    match = re.fullmatch(r"([A-Za-z]+),[ \t]+([0-9]{1,2})[ \t]+([A-Za-z]+)[ \t]+([0-9]{4})", value)
    if not match:
        raise ValueError("Control date must be YYYY-MM-DD or Weekday, D Month YYYY.")
    weekday, day, month, year = match.groups()
    if weekday.casefold() not in ENGLISH_WEEKDAYS or month.casefold() not in ENGLISH_MONTHS:
        raise ValueError("Control date requires full English weekday and month names.")
    result = date(int(year), ENGLISH_MONTHS[month.casefold()], int(day))
    if ENGLISH_WEEKDAYS[result.weekday()] != weekday.casefold():
        raise ValueError("Control date weekday contradicts its calendar date.")
    return result


def parse_episode_reference(value: str) -> tuple[str, str | None]:
    """Accept an ID alone or exactly ID + spaced em dash + a nonblank title."""
    if re.fullmatch(EPISODE_ID_PATTERN, value):
        return value, None
    match = re.fullmatch(rf"({EPISODE_ID_PATTERN})[ \t]+—[ \t]+(\S.*)", value)
    if not match:
        raise ControlDocumentError("SOURCE_EPISODE_INVALID", "Source episode must be an ID or ID — TITLE.")
    episode_id, title = match.groups()
    if title.startswith(("—", "–", "-")):
        raise ControlDocumentError("SOURCE_EPISODE_INVALID", "Source episode title must not begin with another separator.")
    return episode_id, title.strip()


@dataclass(frozen=True)
class DailyMetadata:
    production_date: date
    status: str
    episode_id: str
    episode_title: str
    archive_destination: str
    archive_folder_id: str | None
    source_rnd_date: date | None = None
    source_rnd_episode: str | None = None
    source_rnd_title: str | None = None


# An explicit label vocabulary, not free-text inference. Alias collisions fail closed.
LABELS = {
    "production date": "production_date",
    "production date (sast)": "production_date",
    "production date sast": "production_date",
    "status": "status",
    "episode id": "episode_id",
    "episode": "episode_id",
    "working title": "episode_title",
    "working episode title": "episode_title",
    "recommended episode title": "episode_title",
    "recommended episode / working title": "episode_title",
    "archive destination": "archive_destination",
    "archive folder id": "archive_folder_id",
    "source daily r&d date": "source_rnd_date",
    "source daily r&d episode": "source_rnd_episode",
}


def parse_daily_metadata(text: str, *, slide_design: bool = False) -> DailyMetadata:
    payload = extract_block(text, PAYLOAD_BEGIN, PAYLOAD_END, "DAILY_PAYLOAD")
    # JSON is opaque to the human-metadata parser, even when nested in the payload.
    if MANIFEST_BEGIN in payload or MANIFEST_END in payload:
        extract_block(payload, MANIFEST_BEGIN, MANIFEST_END, "AUTOMATION_MANIFEST")
        start = payload.index(MANIFEST_BEGIN)
        finish = payload.index(MANIFEST_END) + len(MANIFEST_END)
        payload = payload[:start] + payload[finish:]
    values: dict[str, str] = {}
    for line in payload.splitlines():
        label, sep, value = line.partition(":")
        key = LABELS.get(label.strip().casefold()) if sep else None
        if key:
            if key in values:
                raise ControlDocumentError("METADATA_AMBIGUOUS", f"Duplicate metadata field: {key}.")
            values[key] = value.strip()
    required = {"production_date", "status", "episode_id", "archive_destination"}
    if slide_design:
        required |= {"source_rnd_date", "source_rnd_episode"}
    else:
        required.add("episode_title")
    missing = sorted(key for key in required if not values.get(key))
    if missing:
        raise ControlDocumentError("METADATA_MISSING", f"Missing/blank metadata: {', '.join(missing)}.")
    source_episode, source_title = (parse_episode_reference(values["source_rnd_episode"])
                                    if slide_design else (None, None))
    # An explicit title field must be nonblank; only an absent field can use the source title.
    title = values.get("episode_title", source_title)
    if not title:
        raise ControlDocumentError("METADATA_MISSING", "Missing/blank episode_title (explicit or source-reference title).")
    try:
        production = parse_control_date(values["production_date"])
        source = parse_control_date(values["source_rnd_date"]) if slide_design else None
    except ValueError as exc:
        raise ControlDocumentError("METADATA_DATE_INVALID", str(exc)) from exc
    return DailyMetadata(production, values["status"], values["episode_id"],
                         title, values["archive_destination"],
                         values.get("archive_folder_id") or None, source,
                         source_episode, source_title)


def extract_automation_manifest(text: str) -> object:
    raw = extract_block(text, MANIFEST_BEGIN, MANIFEST_END, "AUTOMATION_MANIFEST")

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}.")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError(f"Non-JSON constant: {value}.")

    try:
        return json.loads(raw, object_pairs_hook=unique_object, parse_constant=invalid_constant)
    except (ValueError, RecursionError) as exc:
        raise ControlDocumentError("AUTOMATION_MANIFEST_INVALID_JSON", str(exc)) from exc
