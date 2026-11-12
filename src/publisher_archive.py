"""Read-only archive selection and QC validation for the AI Geopolitic publisher.

Nothing here publishes, edits the original archive or depends on the renderer.
The intended SAST *date* is authoritative; folder modified timestamps are not.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from typing import Mapping
from urllib.parse import urlparse

ARCHIVE_PARENT_ID = "1QcCh-qMHOH97ZWdTLULwNygibJcZRb4q"
FOLDER = re.compile(r"^Ep(?P<number>[1-9]\d{0,5})-(?P<day>[1-9]|[12]\d|3[01])"
                    r"(?P<month>January|February|March|April|May|June|July|August|"
                    r"September|October|November|December)(?P<year>20\d{2})$")
FILE_ID = re.compile(r"^[a-zA-Z0-9_-]{10,100}$")


class PublisherBlocked(ValueError):
    """A safe, deterministic hard stop; never continue using an older episode."""


@dataclass(frozen=True)
class Episode:
    number: int
    day: date
    name: str
    folder_id: str

    @property
    def episode_id(self) -> str:
        return f"Ep{self.number}"

    @property
    def qc_filename(self) -> str:
        return f"{self.episode_id}_QC_Completion.json"

    @property
    def caption_filename(self) -> str:
        return f"{self.episode_id}_CarouselCaption.txt"

    @property
    def slide_names(self) -> tuple[str, ...]:
        return tuple(f"{self.episode_id}_Slide{i:02d}of10.png" for i in range(1, 11))


def sast_today(now: datetime | None = None) -> date:
    utc = now or datetime.now(timezone.utc)
    if utc.tzinfo is None or utc.utcoffset() is None:
        raise PublisherBlocked("A timezone-aware clock is required.")
    return utc.astimezone(timezone(timedelta(hours=2))).date()


def parse_episode_folder(name: str, folder_id: str) -> Episode | None:
    match = FOLDER.fullmatch(name)
    if not match or not FILE_ID.fullmatch(folder_id):
        return None
    groups = match.groupdict()
    try:
        day = date(int(groups["year"]), list(calendar.month_name).index(groups["month"]),
                   int(groups["day"]))
    except ValueError:
        return None
    return Episode(int(groups["number"]), day, name, folder_id)


def select_episode(folder_entries: list[dict], *, day: date,
                   explicit_episode: str | None = None) -> Episode:
    """Exactly one matching folder, no fallback to yesterday or highest mtime."""
    folders: list[Episode] = []
    for entry in folder_entries:
        if not isinstance(entry, dict) or entry.get("IsDir") is not True:
            continue
        found = parse_episode_folder(entry.get("Name", ""), entry.get("ID", ""))
        if found is not None:
            folders.append(found)
    if explicit_episode is not None:
        if not re.fullmatch(r"Ep[1-9]\d{0,5}", explicit_episode):
            raise PublisherBlocked("Invalid explicitly selected episode ID.")
        matches = [e for e in folders if e.episode_id == explicit_episode]
    else:
        matches = [e for e in folders if e.day == day]
    if len(matches) != 1:
        raise PublisherBlocked("Expected one unique intended episode archive; will not fall back.")
    if explicit_episode is None and matches[0].day != day:
        raise PublisherBlocked("Selected archive date does not match the SAST production date.")
    return matches[0]


def manual_exclusion(history: Mapping, episode: Episode, channel: str = "instagram") -> bool:
    """Never repost a user-reported manual publication just because QC is stale."""
    items = history.get("excluded_publications", [])
    return any(isinstance(v, dict) and v.get("episode_id") == episode.episode_id
               and v.get("channel") == channel
               and v.get("status") in ("USER_REPORTED_MANUALLY_PUBLISHED", "PUBLISHED")
               for v in items)


def _unique_files(files: list[dict]) -> dict[str, dict]:
    indexed = {}
    for item in files:
        if not isinstance(item, dict):
            raise PublisherBlocked("Invalid archive listing.")
        name = item.get("Name")
        if not isinstance(name, str) or not name or name in indexed:
            raise PublisherBlocked("Archive file names must be unique.")
        indexed[name] = item
    return indexed


def plan_carousel(episode: Episode, file_entries: list[dict], qc: dict,
                  caption: str, *, manual_history: Mapping | None = None) -> dict:
    """Return metadata-only, immutable pinned-file plan; no publishing side effects."""
    if manual_exclusion(manual_history or {}, episode):
        raise PublisherBlocked("This episode has already been manually published on Instagram.")
    if not isinstance(qc, dict) or qc.get("episode") != episode.episode_id:
        raise PublisherBlocked("QC episode identifier differs from selected folder.")
    if qc.get("production_date_sast") != episode.day.isoformat():
        raise PublisherBlocked("QC production date differs from folder date.")
    if qc.get("status", "").split("—", 1)[0].strip() != "PRODUCTION COMPLETE":
        raise PublisherBlocked("Episode production is not complete.")
    if qc.get("counts", {}).get("carousel") != 10:
        raise PublisherBlocked("QC does not declare exactly ten carousel images.")
    archive_url = qc.get("archive_url", "")
    parsed = urlparse(archive_url)
    if parsed.scheme != "https" or parsed.netloc != "drive.google.com" or parsed.path.rstrip("/").split("/")[-1] != episode.folder_id:
        raise PublisherBlocked("QC archive URL is not the selected Drive folder.")
    if not isinstance(caption, str) or len(caption.strip()) < 20 or len(caption) > 2200:
        raise PublisherBlocked("Carousel caption is missing or too long for Instagram.")
    if "#AIGeopolitic" not in caption or "The event is factual. The interpretation ideological." not in caption:
        raise PublisherBlocked("Caption is missing canonical editorial markers.")
    per_stage = qc.get("per_stage_and_per_image_qc", {})
    cap_gate = per_stage.get("captions", {}) if isinstance(per_stage, dict) else {}
    if not cap_gate.get("status", "").startswith("QC_PASS"):
        raise PublisherBlocked("Caption QC did not pass.")
    deliverables = qc.get("deliverables")
    if not isinstance(deliverables, dict):
        raise PublisherBlocked("QC deliverables are missing.")
    indexed = _unique_files(file_entries)
    expected = list(episode.slide_names) + [episode.qc_filename, episode.caption_filename]
    for filename in expected:
        found = indexed.get(filename)
        record = deliverables.get(filename)
        if not found or not isinstance(record, dict):
            raise PublisherBlocked("Required archived file or QC record is missing.")
        if found.get("IsDir") is not False or found.get("ID") != record.get("id"):
            raise PublisherBlocked("Actual Drive file ID disagrees with the QC record.")
        expected_mime = "image/png" if filename.endswith(".png") else (
            "text/plain" if filename.endswith(".txt") else "application/json")
        if found.get("MimeType") != expected_mime:
            raise PublisherBlocked("Unexpected media type in the archived file inventory.")
        if not FILE_ID.fullmatch(found["ID"]):
            raise PublisherBlocked("Invalid archived Drive asset identifier.")
    slides = []
    for filename in episode.slide_names:
        record = deliverables[filename]
        if (record.get("dimensions") not in ([1080, 1350], [1080, 1440])
                or record.get("readback_identical") is not True
                or not re.fullmatch(r"[0-9a-f]{64}", record.get("sha256", ""))):
            raise PublisherBlocked("Image QC missing, wrong-size or not readback-verified.")
        slides.append({
            "name": filename,
            "file_id": record["id"],
            "source_sha256": record["sha256"],
            "source_dimensions": record["dimensions"],
        })
    cap_record = deliverables[episode.caption_filename]
    if not re.fullmatch(r"[0-9a-f]{64}", cap_record.get("sha256", "")):
        raise PublisherBlocked("Caption QC has no SHA-256 proof.")
    if hashlib.sha256(caption.encode("utf-8")).hexdigest() != cap_record["sha256"]:
        # The text export must reproduce exact original UTF-8 bytes, not a
        # decoded/transformed interpretation of the archived text.
        raise PublisherBlocked("Caption bytes do not match the recorded checksum.")
    return {
        "schema": "ai-geopolitic.publisher.carousel-plan.v1",
        "episode": episode.episode_id,
        "production_date_sast": episode.day.isoformat(),
        "archive_folder_id": episode.folder_id,
        "archive_name": episode.name,
        "slide_count": 10,
        "slides": slides,
        "caption_file_id": cap_record["id"],
        "caption_sha256": cap_record["sha256"],
        "caption_length": len(caption),
        "release_authorized": False,
        "mode": "DRY_RUN",
        "source": "exact_drive_id_and_qc",
    }
