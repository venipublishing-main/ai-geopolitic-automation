"""Daily build readiness service and developer CLI; never renders or publishes."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .control_documents import (Blocker, ControlDocumentError, DailyMetadata,
                                extract_automation_manifest, parse_daily_metadata, parse_iso_date)
from .episode_manifest_v2 import load_canonical_characters, validate_manifest_v2
from .production_inputs import (DailyDocuments, InputSourceError, LocalFileInput,
                                ProductionInput, RcloneDriveInput)

RND_SUCCESS_STATUSES = frozenset({"COMPLETE", "R&D COMPLETE", "READY FOR SLIDE DESIGN",
                                 "R&D COMPLETE — READY FOR 20-SLIDE DESIGN"})
DESIGN_READY_STATUS = "READY FOR CAROUSEL RENDERING"
DESIGN_READY_STATUSES = frozenset({DESIGN_READY_STATUS,
                                  "20-SLIDE BLUEPRINT COMPLETE — READY FOR MANUAL RENDERING"})
ROOT = Path(__file__).resolve().parents[1]


def current_production_date(now: datetime | None = None) -> date:
    instant = now if now is not None else datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Clock must be timezone-aware.")
    try:
        sast = ZoneInfo("Africa/Johannesburg")
    except ZoneInfoNotFoundError:
        # Windows may lack IANA data. Modern Johannesburg is fixed UTC+02:00.
        sast = timezone(timedelta(hours=2), "Africa/Johannesburg")
    return instant.astimezone(sast).date()


@dataclass(frozen=True)
class DailyBuildReadinessResult:
    production_date_sast: str
    build: str
    state: str
    blockers: tuple[Blocker, ...]
    manifest: dict | None = None

    @property
    def ready(self) -> bool:
        return self.build == "READY"

    def to_dict(self) -> dict:
        return asdict(self)


class DailyBuildReadiness:
    def __init__(self, characters: dict | None = None):
        self.characters = load_canonical_characters() if characters is None else characters

    def check(self, source: ProductionInput, *, production_date: date | None = None) -> DailyBuildReadinessResult:
        today = production_date if production_date is not None else current_production_date()
        try:
            documents = source.read()
        except InputSourceError as exc:
            return DailyBuildReadinessResult(today.isoformat(), "BLOCKED", "BUILD_BLOCKED",
                                            (Blocker("INPUT_SOURCE_UNAVAILABLE", str(exc), "source"),))
        return self.evaluate(documents, production_date=today)

    def evaluate(self, documents: DailyDocuments, *, production_date: date | None = None) -> DailyBuildReadinessResult:
        """Pure evaluation of a supplied text snapshot and explicit/injected production day."""
        today = production_date if production_date is not None else current_production_date()
        blockers: list[Blocker] = []

        def block(code, message, path=""):
            blockers.append(Blocker(code, message, path))

        def metadata(text, kind) -> DailyMetadata | None:
            try:
                return parse_daily_metadata(text, slide_design=kind == "slide_design")
            except ControlDocumentError as exc:
                block(exc.code, str(exc), kind)
                return None

        rnd = metadata(documents.rnd, "rnd")
        design = metadata(documents.slide_design, "slide_design")
        manifest = None
        manifest_parsed = False
        try:
            manifest = extract_automation_manifest(documents.slide_design)
            manifest_parsed = True
        except ControlDocumentError as exc:
            block(exc.code, str(exc), "slide_design.manifest")
        if rnd:
            if rnd.production_date != today:
                block("RND_STALE", f"R&D date {rnd.production_date} does not match {today}.", "rnd.production_date")
            if rnd.status not in RND_SUCCESS_STATUSES:
                block("RND_NOT_SUCCESSFUL", "R&D must have an explicitly supported success status.", "rnd.status")
        if design:
            if design.production_date != today:
                block("SLIDE_DESIGN_STALE", f"Slide Design date {design.production_date} does not match {today}.", "slide_design.production_date")
            if design.status not in DESIGN_READY_STATUSES:
                block("SLIDE_DESIGN_NOT_READY", "Slide Design must have an explicitly supported completion status.", "slide_design.status")
        if rnd and design:
            if rnd.episode_id != design.episode_id:
                block("EPISODE_MISMATCH", "R&D and Slide Design episodes differ.")
            if rnd.production_date != design.source_rnd_date or rnd.episode_id != design.source_rnd_episode:
                block("SOURCE_RND_MISMATCH", "Slide Design source R&D date/episode differs from Daily R&D.")
            if design.source_rnd_title is not None and design.source_rnd_title != rnd.episode_title:
                block("SOURCE_RND_TITLE_MISMATCH", "Slide Design source R&D title differs from Daily R&D.", "slide_design.source_rnd_title")
            if rnd.episode_title != design.episode_title:
                block("DOCUMENT_TITLE_MISMATCH", "R&D and Slide Design titles differ.")
            if rnd.archive_destination != design.archive_destination:
                block("ARCHIVE_IDENTITY_MISMATCH", "R&D and Slide Design archive destinations differ.")
            if rnd.archive_folder_id and rnd.archive_folder_id != design.archive_folder_id:
                block("ARCHIVE_IDENTITY_MISMATCH", "R&D and Slide Design archive folder IDs differ.")
        for kind, doc in (("rnd", rnd), ("slide_design", design)):
            if doc and ((kind == "slide_design" and not doc.archive_folder_id) or
                        (doc.archive_folder_id and not re.fullmatch(r"[A-Za-z0-9_-]+", doc.archive_folder_id))):
                block("ARCHIVE_FOLDER_MISSING", "Require a valid Drive archive folder ID.", f"{kind}.archive_folder_id")
        if manifest_parsed:
            blockers.extend(validate_manifest_v2(manifest, self.characters))
            if isinstance(manifest, dict):
                for kind, doc in (("rnd", rnd), ("slide_design", design)):
                    if not doc:
                        continue
                    expected = {"episode_id": doc.episode_id, "episode_title": doc.episode_title,
                                "production_date_sast": doc.production_date.isoformat(),
                                "source_rnd_date_sast": (doc.source_rnd_date or doc.production_date).isoformat(),
                                "archive_destination": doc.archive_destination}
                    if doc.archive_folder_id:
                        expected["archive_folder_id"] = doc.archive_folder_id
                    for key, value in expected.items():
                        if manifest.get(key) != value:
                            block("MANIFEST_METADATA_MISMATCH", f"Manifest {key} differs from {kind}.", f"manifest.{key}")
        ready = not blockers
        waiting = (rnd is not None and rnd.production_date == today and
                   design is not None and design.production_date < today)
        state = "BUILD_READY" if ready else ("WAITING_FOR_CURRENT_SLIDE_DESIGN" if waiting else "BUILD_BLOCKED")
        return DailyBuildReadinessResult(today.isoformat(), "READY" if ready else "BLOCKED", state,
                                        tuple(blockers), manifest if ready else None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("fixtures", "local", "drive"), default="fixtures")
    parser.add_argument("--fixture", choices=("valid", "stale"), default="valid")
    parser.add_argument("--rnd-file", type=Path)
    parser.add_argument("--slide-design-file", type=Path)
    parser.add_argument("--date", type=parse_iso_date, help="Explicit SAST production date (YYYY-MM-DD).")
    parser.add_argument("--json", action="store_true", help="Print structured result as JSON.")
    args = parser.parse_args(argv)
    today = args.date if args.date is not None else current_production_date()
    try:
        if args.source == "drive":
            if args.rnd_file or args.slide_design_file:
                parser.error("Drive source does not accept local file overrides.")
            source = RcloneDriveInput.from_environment()
        elif args.source == "local":
            if not args.rnd_file or not args.slide_design_file:
                parser.error("Local source requires --rnd-file and --slide-design-file.")
            source = LocalFileInput(args.rnd_file, args.slide_design_file)
        else:
            if bool(args.rnd_file) != bool(args.slide_design_file):
                parser.error("Supply both local file overrides together.")
            base = ROOT / "tests/fixtures/daily_readiness"
            source = LocalFileInput(args.rnd_file or base / "daily_rnd.txt",
                                    args.slide_design_file or base / f"slide_design_{args.fixture}.txt")
        result = DailyBuildReadiness().check(source, production_date=today)
    except InputSourceError as exc:
        result = DailyBuildReadinessResult(today.isoformat(), "BLOCKED", "BUILD_BLOCKED",
                                          (Blocker("INPUT_SOURCE_UNAVAILABLE", str(exc), "source"),))
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"BUILD {result.build} | {result.state} | SAST {result.production_date_sast}")
        for item in result.blockers:
            print(f"- {item.code} [{item.path}]: {item.message}")
        if result.ready:
            print(f"Episode {result.manifest['episode_id']}: 20 validated slides.")
    return 0 if result.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
