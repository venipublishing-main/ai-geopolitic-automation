"""Active Drive v3 readiness boundary. Zero generation, zero publishing.

Keeps the frozen 20-slide Manifest v2 fixtures as a separate historical path.
The two external proof callbacks must be supplied by a trusted Drive adapter:
a syntactically correct Drive ID is NOT evidence that an asset exists.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import date

from .control_documents import (
    Blocker, ControlDocumentError, MANIFEST_BEGIN, MANIFEST_END,
    PAYLOAD_BEGIN, PAYLOAD_END, extract_block,
)
from .daily_readiness import (
    DailyBuildReadiness, DailyBuildReadinessResult, DESIGN_READY_STATUS,
)
from .episode_manifest_v2 import load_canonical_characters
from .production_inputs import DailyDocuments

# Approved 4 November 2026. These values are from the ACTIVE v3 Drive
# Production/Automation contracts, NOT legacy renderer config/characters.json.
V3_ACCENTS = {
    "nora": "#336BA3",
    "diane_sterling": "#204F39",
    "johan_vosloo": "#253852",
    "kai_patel": "#7352A8",
    "thabo_mokoena": "#89301D",
    "amari_ndlovu": "#8B6E2C",
}
V3_PORTRAIT_IDS = {
    "nora": "1SJDUwvhLbfTP5VZsl4c9j58lqqN6wX-U",
    "diane_sterling": "1AAibQUfgGiLappONOqB9H8HxDdArJkPL",
    "johan_vosloo": "1EZ_fZXr2QBp7YzYR8qoQ8h1vpIYHvzpI",
    "kai_patel": "1UfKbYekZAPJEaS4NsPseEKK3I-7Roe_b",
    "thabo_mokoena": "1t-TlH3M4_Nf0Lp42vXXnA7le2GVbjhc6",
    "amari_ndlovu": "1WoRMXeakthKlPG0Whp_tPJJy9ZkjmYqC",
}

# Literal strings in the current accepted Ep136 Daily Slide Design payload.
V3_MANIFEST_BEGIN = "[BEGIN AUTOMATION MANIFEST JSON marker]"
V3_MANIFEST_END = "[END AUTOMATION MANIFEST JSON marker]"
V3_INTEGRITY_GATE = "DESIGN INTEGRITY GATE: PASS"

ArchiveChecker = Callable[[str], bool]
PortraitChecker = Callable[[str, str], bool]


def v3_characters() -> dict:
    """Use current canonical colours while isolating historical render config."""
    characters = load_canonical_characters()
    if set(characters) != set(V3_ACCENTS) or set(characters) != set(V3_PORTRAIT_IDS):
        raise ValueError("Legacy character roster does not match the active v3 canon.")
    for slug, character in characters.items():
        character["accent"] = V3_ACCENTS[slug]
    return characters


def normalize_v3_design(text: str) -> tuple[str, list[Blocker]]:
    """Check the active payload's literal markers and design integrity gate.

    Replace the two v3 delimiters only in a private in-memory snapshot, so the
    existing strict JSON parser can be reused without rewriting a Drive Doc.
    """
    issues: list[Blocker] = []
    try:
        payload = extract_block(text, PAYLOAD_BEGIN, PAYLOAD_END, "DAILY_PAYLOAD")
    except ControlDocumentError as exc:
        return text, [Blocker(exc.code, str(exc), "slide_design.payload")]

    gate_lines = [line.strip() for line in payload.splitlines()
                  if line.strip().startswith("DESIGN INTEGRITY GATE:")]
    if gate_lines != [V3_INTEGRITY_GATE]:
        issues.append(Blocker("DESIGN_INTEGRITY_NOT_PASSED",
                              "Require exactly one DESIGN INTEGRITY GATE: PASS inside the Daily Slide Design payload.",
                              "slide_design.design_integrity_gate"))
    if MANIFEST_BEGIN in text or MANIFEST_END in text:
        issues.append(Blocker("AUTOMATION_MANIFEST_MARKER_MISMATCH",
                              "Historical manifest markers are not valid for the active v3 handoff.",
                              "slide_design.manifest"))
    try:
        extract_block(payload, V3_MANIFEST_BEGIN, V3_MANIFEST_END, "AUTOMATION_MANIFEST")
        if text.count(V3_MANIFEST_BEGIN) != 1 or text.count(V3_MANIFEST_END) != 1:
            raise ControlDocumentError("AUTOMATION_MANIFEST_AMBIGUOUS",
                                       "Exactly one manifest pair is required across the whole document.")
        if gate_lines == [V3_INTEGRITY_GATE] and payload.index(V3_MANIFEST_BEGIN) < payload.index(V3_INTEGRITY_GATE):
            issues.append(Blocker("AUTOMATION_MANIFEST_POSITION_INVALID",
                                  "Manifest must follow human briefs and the design-integrity audit.",
                                  "slide_design.manifest"))
    except ControlDocumentError as exc:
        issues.append(Blocker(exc.code, str(exc), "slide_design.manifest"))

    normalized = text.replace(V3_MANIFEST_BEGIN, MANIFEST_BEGIN).replace(V3_MANIFEST_END, MANIFEST_END)
    return normalized, issues


class V3DailyBuildReadiness(DailyBuildReadiness):
    """Validate v3 semantics, then require actual archive and portrait evidence.

    No callback means BLOCKED, never implicit success. Tests may inject a pure
    stub; production must connect these to authenticated Drive metadata reads.
    This is a build-input readiness gate, NOT visual QC or publication approval.
    """
    def __init__(self, *, archive_folder_exists: ArchiveChecker | None = None,
                 portrait_asset_exists: PortraitChecker | None = None):
        super().__init__(characters=v3_characters(), expected_slide_count=10)
        self.archive_folder_exists = archive_folder_exists
        self.portrait_asset_exists = portrait_asset_exists

    def evaluate(self, documents: DailyDocuments, *,
                 production_date: date | None = None) -> DailyBuildReadinessResult:
        normalized_design, issues = normalize_v3_design(documents.slide_design)
        result = super().evaluate(
            DailyDocuments(documents.rnd, normalized_design), production_date=production_date
        )
        blockers = list(result.blockers) + issues

        # The historical status was deliberately permissive; v3 is not.
        try:
            from .control_documents import parse_daily_metadata
            design = parse_daily_metadata(documents.slide_design, slide_design=True)
            if design.status != DESIGN_READY_STATUS:
                blockers.append(Blocker("SLIDE_DESIGN_NOT_READY",
                                        "v3 requires STATUS: READY FOR CAROUSEL RENDERING.",
                                        "slide_design.status"))
        except ControlDocumentError:
            # The base parser has already produced a structured blocker.
            pass

        if result.ready and not issues:
            manifest = result.manifest
            archive_id = manifest["archive_folder_id"]
            if self.archive_folder_exists is None:
                blockers.append(Blocker("ARCHIVE_FOLDER_UNVERIFIED",
                                        "Supply authenticated Drive folder existence verification.",
                                        "manifest.archive_folder_id"))
            else:
                try:
                    exists = self.archive_folder_exists(archive_id)
                except Exception:
                    exists = False
                if not exists:
                    blockers.append(Blocker("ARCHIVE_FOLDER_NOT_VERIFIED",
                                            "Archive folder was not verified in Drive.",
                                            "manifest.archive_folder_id"))

            assigned = {slug for slide in manifest["slides"] for slug in slide["panelists"]}
            if self.portrait_asset_exists is None:
                blockers.append(Blocker("CANONICAL_PORTRAITS_UNVERIFIED",
                                        "Supply authenticated Drive portrait ID verification.",
                                        "manifest.slides.panelists"))
            else:
                for slug in sorted(assigned):
                    try:
                        exists = self.portrait_asset_exists(slug, V3_PORTRAIT_IDS[slug])
                    except Exception:
                        exists = False
                    if not exists:
                        blockers.append(Blocker("CANONICAL_PORTRAIT_NOT_VERIFIED",
                                                f"Canonical transparent PNG not verified for {slug}.",
                                                f"panelists.{slug}"))

        if blockers:
            state = (result.state if result.state == "WAITING_FOR_CURRENT_SLIDE_DESIGN"
                     else "BUILD_BLOCKED")
            return DailyBuildReadinessResult(result.production_date_sast, "BLOCKED", state,
                                             tuple(blockers), None)
        return result
