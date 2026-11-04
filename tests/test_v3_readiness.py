"""Zero-generation v3 contract regression tests; no network or provider calls."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from src.control_documents import MANIFEST_BEGIN, MANIFEST_END, extract_automation_manifest
from src.daily_readiness import DailyBuildReadiness
from src.production_inputs import DailyDocuments, LocalFileInput
from src.v3_readiness import (
    V3_ACCENTS, V3_INTEGRITY_GATE, V3_MANIFEST_BEGIN, V3_MANIFEST_END,
    V3_PORTRAIT_IDS, V3DailyBuildReadiness,
)

BASE = Path(__file__).resolve().parent / "fixtures/daily_readiness"
TODAY = date(2026, 11, 4)
EPISODE = "Ep136"
TITLE = "SYNTHETIC V3 CONTRACT REGRESSION"
ARCHIVE = "fixture_v3_archive"


def v3_fixture() -> DailyDocuments:
    legacy = LocalFileInput(BASE / "daily_rnd.txt", BASE / "slide_design_valid.txt").read()
    manifest = extract_automation_manifest(legacy.slide_design)
    manifest.update(
        episode_id=EPISODE, episode_title=TITLE, production_date_sast=TODAY.isoformat(),
        source_rnd_date_sast=TODAY.isoformat(), archive_destination="Ep136-4November2026",
        archive_folder_id=ARCHIVE,
    )
    manifest["slides"] = manifest["slides"][:10]
    for number, slide in enumerate(manifest["slides"], start=1):
        slide["slide_number"] = number
        slide["accent_colours"] = {slug: V3_ACCENTS[slug] for slug in slide["panelists"]}
    rnd = (
        "R&D operating instructions outside payload\n"
        "=== BEGIN DAILY PAYLOAD ===\n"
        "PRODUCTION DATE (SAST): Wednesday, 4 November 2026\n"
        f"EPISODE: {EPISODE}\n"
        f"WORKING TITLE: {TITLE}\n"
        "STATUS: R&D COMPLETE — READY FOR 10-SLIDE DESIGN\n"
        "ARCHIVE DESTINATION: Ep136-4November2026\n"
        f"ARCHIVE FOLDER ID: {ARCHIVE}\n"
        "=== END DAILY PAYLOAD ===\n"
    )
    design = (
        "Current v3 controls outside the payload\n"
        "=== BEGIN DAILY PAYLOAD ===\n"
        "=== CURRENT EP136 SLIDE DESIGN — AUTHORITATIVE ===\n"
        "SOURCE DAILY R&D DATE: Wednesday, 4 November 2026\n"
        f"SOURCE DAILY R&D EPISODE: {EPISODE} — {TITLE}\n"
        f"EPISODE: {EPISODE}\n"
        "PRODUCTION DATE: Wednesday, 4 November 2026\n"
        "ARCHIVE DESTINATION: Ep136-4November2026\n"
        f"ARCHIVE FOLDER ID: {ARCHIVE}\n"
        "STATUS: READY FOR CAROUSEL RENDERING\n"
        "TEN HUMAN BRIEFS: synthetic, not approved publication artwork\n"
        f"{V3_INTEGRITY_GATE}\n"
        f"{V3_MANIFEST_BEGIN}\n"
        + json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n"
        + f"{V3_MANIFEST_END}\n"
        "=== END DAILY PAYLOAD ===\n"
    )
    return DailyDocuments(rnd, design)


def validator(**overrides):
    opts = {
        "archive_folder_exists": lambda folder: folder == ARCHIVE,
        "portrait_asset_exists": lambda slug, file_id: V3_PORTRAIT_IDS[slug] == file_id,
    }
    opts.update(overrides)
    return V3DailyBuildReadiness(**opts)


def check(documents=None, **overrides):
    return validator(**overrides).evaluate(documents or v3_fixture(), production_date=TODAY)


def codes(result):
    return {blocker.code for blocker in result.blockers}


def alter_manifest(docs, change):
    start = docs.slide_design.index(V3_MANIFEST_BEGIN) + len(V3_MANIFEST_BEGIN)
    end = docs.slide_design.index(V3_MANIFEST_END)
    manifest = json.loads(docs.slide_design[start:end])
    change(manifest)
    return DailyDocuments(docs.rnd, docs.slide_design[:start] + "\n"
                          + json.dumps(manifest, ensure_ascii=False) + "\n"
                          + docs.slide_design[end:])


def test_current_v3_contract_ready_with_verified_external_assets():
    result = check()
    assert result.ready
    assert result.production_date_sast == "2026-11-04"
    assert [slide["slide_number"] for slide in result.manifest["slides"]] == list(range(1, 11))
    assert len(result.manifest["slides"][1]["panelists"]) == 2
    assert result.manifest["slides"][0]["accent_colours"]["nora"] == "#336BA3"
    assert not result.blockers


def test_frozen_twenty_slide_legacy_fixture_still_passes_legacy_gate():
    legacy = LocalFileInput(BASE / "daily_rnd.txt", BASE / "slide_design_valid.txt").read()
    result = DailyBuildReadiness().evaluate(legacy, production_date=date(2026, 10, 1))
    assert result.ready and len(result.manifest["slides"]) == 20
    assert MANIFEST_BEGIN in legacy.slide_design and MANIFEST_END in legacy.slide_design


@pytest.mark.parametrize("count", [9, 11, 20])
def test_wrong_slide_count_fails_closed(count):
    docs = alter_manifest(v3_fixture(), lambda m: m.update(
        slides=(m["slides"][:count] if count <= 10
                else [m["slides"][i % 10] for i in range(count)])))
    result = check(docs)
    assert not result.ready and "SLIDE_COUNT_INVALID" in codes(result)
    assert result.manifest is None


def test_stale_rnd_or_design_blocks_build():
    docs = v3_fixture()
    stale_rnd = DailyDocuments(docs.rnd.replace("Wednesday, 4 November 2026",
                                                "Tuesday, 3 November 2026"), docs.slide_design)
    assert "RND_STALE" in codes(check(stale_rnd))
    stale_design = DailyDocuments(docs.rnd, docs.slide_design.replace(
        "PRODUCTION DATE: Wednesday, 4 November 2026",
        "PRODUCTION DATE: Tuesday, 3 November 2026"))
    assert "SLIDE_DESIGN_STALE" in codes(check(stale_design))


@pytest.mark.parametrize("gate", ["DESIGN INTEGRITY GATE: REVALIDATION REQUIRED",
                                  "DESIGN INTEGRITY GATE: FAIL", ""])
def test_integrity_gate_must_have_exactly_one_pass(gate):
    docs = v3_fixture()
    changed = docs.slide_design.replace(V3_INTEGRITY_GATE, gate)
    result = check(DailyDocuments(docs.rnd, changed))
    assert not result.ready
    assert "DESIGN_INTEGRITY_NOT_PASSED" in codes(result)


def test_duplicate_integrity_gate_blocks():
    docs = v3_fixture()
    changed = docs.slide_design.replace(V3_INTEGRITY_GATE,
                                        V3_INTEGRITY_GATE + "\n" + V3_INTEGRITY_GATE)
    assert "DESIGN_INTEGRITY_NOT_PASSED" in codes(check(DailyDocuments(docs.rnd, changed)))


def test_manifest_must_follow_integrity_gate():
    docs = v3_fixture()
    changed = docs.slide_design.replace(V3_INTEGRITY_GATE + "\n", "", 1).replace(
        V3_MANIFEST_END + "\n", V3_MANIFEST_END + "\n" + V3_INTEGRITY_GATE + "\n", 1)
    assert "AUTOMATION_MANIFEST_POSITION_INVALID" in codes(
        check(DailyDocuments(docs.rnd, changed)))


def test_historical_manifest_delimiters_are_not_accepted_by_v3():
    docs = v3_fixture()
    changed = docs.slide_design.replace(V3_MANIFEST_BEGIN, MANIFEST_BEGIN).replace(
        V3_MANIFEST_END, MANIFEST_END)
    result = check(DailyDocuments(docs.rnd, changed))
    assert "AUTOMATION_MANIFEST_MARKER_MISMATCH" in codes(result)
    assert result.manifest is None


def test_missing_duplicate_or_outside_payload_manifest_is_blocked():
    docs = v3_fixture()
    missing = docs.slide_design.replace(V3_MANIFEST_BEGIN, "MISSING").replace(
        V3_MANIFEST_END, "MISSING")
    assert not check(DailyDocuments(docs.rnd, missing)).ready
    duplicate = docs.slide_design + V3_MANIFEST_BEGIN + "\n" + V3_MANIFEST_END
    assert "AUTOMATION_MANIFEST_AMBIGUOUS" in codes(
        check(DailyDocuments(docs.rnd, duplicate)))
    outside = docs.slide_design.replace(V3_MANIFEST_BEGIN, "REMOVED").replace(
        V3_MANIFEST_END, "REMOVED") + "\n" + V3_MANIFEST_BEGIN + "\n{}\n" + V3_MANIFEST_END
    assert not check(DailyDocuments(docs.rnd, outside)).ready


def test_wrong_old_accent_colour_rejected():
    docs = alter_manifest(v3_fixture(), lambda m: m["slides"][0]["accent_colours"].update(
        nora="#1769AA"))
    assert "ACCENT_COLOUR_INVALID" in codes(check(docs))


def test_closed_schema_extra_key_rejected():
    docs = alter_manifest(v3_fixture(), lambda m: m.update(publication_status="READY"))
    assert "MANIFEST_FIELD_UNSUPPORTED" in codes(check(docs))


def test_dual_relationship_must_be_approved():
    docs = alter_manifest(v3_fixture(), lambda m: m["slides"][1].update(
        pairing_mode="UNSUPPORTED"))
    assert "DUAL_PAIRING_INVALID" in codes(check(docs))


def test_external_checks_are_mandatory_not_assumed():
    result = check(archive_folder_exists=None, portrait_asset_exists=None)
    assert not result.ready
    assert {"ARCHIVE_FOLDER_UNVERIFIED", "CANONICAL_PORTRAITS_UNVERIFIED"} <= codes(result)


def test_archive_and_portrait_failures_are_fail_closed():
    assert "ARCHIVE_FOLDER_NOT_VERIFIED" in codes(
        check(archive_folder_exists=lambda folder: False))
    assert "CANONICAL_PORTRAIT_NOT_VERIFIED" in codes(
        check(portrait_asset_exists=lambda slug, file_id: False))
    def failed_network(folder):
        raise OSError("Private network error: secrets should not be leaked")
    result = check(archive_folder_exists=failed_network)
    assert "ARCHIVE_FOLDER_NOT_VERIFIED" in codes(result)
    assert "secrets" not in json.dumps(result.to_dict())


def test_historical_20_slide_status_does_not_authorize_v3():
    docs = v3_fixture()
    changed = docs.slide_design.replace(
        "STATUS: READY FOR CAROUSEL RENDERING",
        "STATUS: 20-SLIDE BLUEPRINT COMPLETE — READY FOR MANUAL RENDERING")
    assert "SLIDE_DESIGN_NOT_READY" in codes(check(DailyDocuments(docs.rnd, changed)))


def test_bad_manifest_date_and_extra_field_fail_closed():
    docs = alter_manifest(v3_fixture(), lambda m: m.update(
        production_date_sast="2026-11-03"))
    assert "MANIFEST_METADATA_MISMATCH" in codes(check(docs))
    assert check(docs).manifest is None
