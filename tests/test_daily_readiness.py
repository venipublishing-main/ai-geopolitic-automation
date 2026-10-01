from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.control_documents import (MANIFEST_BEGIN, MANIFEST_END, PAYLOAD_BEGIN, PAYLOAD_END,
                                   ControlDocumentError, extract_automation_manifest, parse_daily_metadata)
from src.daily_readiness import DailyBuildReadiness, current_production_date, main
from src.episode_manifest_v2 import COPY_FIELDS, PAIRING_MODES, SLIDE_FIELDS, TOP_FIELDS, load_canonical_characters
from src.production_inputs import DailyDocuments, InputSourceError, LocalFileInput, MemoryInput, RcloneDriveInput

BASE = ROOT / "tests/fixtures/daily_readiness"
TODAY = date(2026, 10, 1)


def documents():
    return LocalFileInput(BASE / "daily_rnd.txt", BASE / "slide_design_valid.txt").read()


def with_manifest(docs, manifest):
    text = docs.slide_design
    start = text.index(MANIFEST_BEGIN) + len(MANIFEST_BEGIN)
    end = text.index(MANIFEST_END)
    return DailyDocuments(docs.rnd, text[:start] + "\n" + json.dumps(manifest) + "\n" + text[end:])


def check(docs=None):
    return DailyBuildReadiness().evaluate(docs or documents(), production_date=TODAY)


def codes(result):
    return {blocker.code for blocker in result.blockers}


def test_current_fixture_ready_with_single_and_dual_slides():
    result = check()
    assert result.ready and result.state == "BUILD_READY"
    assert not result.blockers
    assert len(result.manifest["slides"]) == 20
    assert len(result.manifest["slides"][0]["panelists"]) == 1
    assert len(result.manifest["slides"][1]["panelists"]) == 2
    assert "layout_family" not in result.manifest["slides"][0]
    source = MemoryInput(documents().rnd, documents().slide_design)
    assert DailyBuildReadiness().check(source, production_date=TODAY) == result


def test_today_rnd_yesterday_design_waits_and_never_exposes_buildable_manifest():
    docs = LocalFileInput(BASE / "daily_rnd.txt", BASE / "slide_design_stale.txt").read()
    result = check(docs)
    assert not result.ready
    assert result.state == "WAITING_FOR_CURRENT_SLIDE_DESIGN"
    assert "SLIDE_DESIGN_STALE" in codes(result)
    assert result.manifest is None
    assert check(DailyDocuments(docs.rnd.replace("2026-10-01", "2026-09-30"), docs.slide_design)).state == "BUILD_BLOCKED"


@pytest.mark.parametrize("case", json.loads((BASE / "cases.json").read_text()), ids=lambda case: case["name"])
def test_failure_fixtures(case):
    docs = documents()
    manifest = extract_automation_manifest(docs.slide_design)
    if "replace" in case:
        docs = DailyDocuments(docs.rnd, docs.slide_design.replace(*case["replace"]))
    elif case.get("manifest") == "missing":
        start = docs.slide_design.index(MANIFEST_BEGIN)
        end = docs.slide_design.index(MANIFEST_END) + len(MANIFEST_END)
        docs = DailyDocuments(docs.rnd, docs.slide_design[:start] + docs.slide_design[end:])
    elif case.get("manifest") == "malformed":
        docs = with_manifest(docs, manifest)
        docs = DailyDocuments(docs.rnd, docs.slide_design.replace('"schema_version": 2', '"schema_version": INVALID'))
    elif case.get("manifest") == "nineteen":
        manifest["slides"].pop()
        docs = with_manifest(docs, manifest)
    else:
        slide = manifest["slides"][case["slide"]]
        if case.get("delete"):
            del slide[case["field"]]
        else:
            slide[case["field"]] = case["value"]
        docs = with_manifest(docs, manifest)
    result = check(docs)
    assert not result.ready and case["code"] in codes(result)
    assert result.manifest is None


@pytest.mark.parametrize("field", sorted(SLIDE_FIELDS))
def test_all_slide_fields_required(field):
    docs = documents()
    manifest = extract_automation_manifest(docs.slide_design)
    del manifest["slides"][0][field]
    assert "MANIFEST_FIELD_MISSING" in codes(check(with_manifest(docs, manifest)))


@pytest.mark.parametrize("field", sorted(TOP_FIELDS - {"schema_version"}))
def test_all_top_fields_required(field):
    docs = documents()
    manifest = extract_automation_manifest(docs.slide_design)
    del manifest[field]
    assert "MANIFEST_FIELD_MISSING" in codes(check(with_manifest(docs, manifest)))


@pytest.mark.parametrize("field", sorted(COPY_FIELDS))
def test_required_copy_is_nonblank(field):
    docs = documents()
    manifest = extract_automation_manifest(docs.slide_design)
    manifest["slides"][0][field] = "  "
    assert "SLIDE_COPY_INVALID" in codes(check(with_manifest(docs, manifest)))


@pytest.mark.parametrize("field,value,code", [
    ("panelists", ["nora", "nora"], "DUAL_PAIRING_INVALID"),
    ("panelists", [], "PANELIST_COUNT_INVALID"),
    ("panelists", ["nora", "kai_patel", "amari_ndlovu"], "PANELIST_COUNT_INVALID"),
    ("panelists", [{"slug": "nora"}], "PANELIST_COUNT_INVALID"),
    ("pairing_mode", "QUALIFIED_TENSION", "SINGLE_PAIRING_INVALID"),
    ("takeaway_ideas", [{"idea": "One"}], "TAKEAWAY_COUNT_INVALID"),
    ("takeaway_ideas", [{"idea": " "}] * 3, "TAKEAWAY_INVALID"),
    ("takeaway_ideas", [{"idea": "One", "intended_visual_treatment": None}] * 3, "TAKEAWAY_INVALID"),
    ("accent_colours", {"nora": "#FFFFFF"}, "ACCENT_COLOUR_INVALID"),
    ("accent_colours", {"nora": "#1769AA", "kai_patel": "#6540A4"}, "ACCENT_COLOUR_INVALID"),
    ("factual_guardrails", [], "SLIDE_FIELD_INVALID"),
    ("slide_number", True, "SLIDE_NUMBER_INVALID"),
    ("layout_family", "system_axis", "MANIFEST_FIELD_UNSUPPORTED"),
])
def test_slide_type_and_content_constraints(field, value, code):
    docs = documents()
    manifest = extract_automation_manifest(docs.slide_design)
    manifest["slides"][0][field] = value
    assert code in codes(check(with_manifest(docs, manifest)))


@pytest.mark.parametrize("field,value", [
    ("central_relationship", None), ("shared_ground", ""), ("why_dual", " "),
    ("panelist_contributions", {"nora": "Wrong contributor"}),
    ("panelist_contributions", {"diane_sterling": "Only one"}), ("pairing_mode", {}),
])
def test_invalid_dual_relationship_and_contributions(field, value):
    docs = documents()
    manifest = extract_automation_manifest(docs.slide_design)
    manifest["slides"][1][field] = value
    assert "DUAL_PAIRING_INVALID" in codes(check(with_manifest(docs, manifest)))


@pytest.mark.parametrize("mode", sorted(PAIRING_MODES))
def test_all_dual_pairing_modes_are_supported(mode):
    docs = documents()
    manifest = extract_automation_manifest(docs.slide_design)
    manifest["slides"][1]["pairing_mode"] = mode
    assert check(with_manifest(docs, manifest)).ready


@pytest.mark.parametrize("value", [None, [], 2, "text", {"schema_version": 1}, {"schema_version": 2.0}])
def test_non_object_or_unsupported_manifest_fails_closed(value):
    assert not check(with_manifest(documents(), value)).ready


@pytest.mark.parametrize("raw", ['{"schema_version":2,"schema_version":2}', '{"value":NaN}', '{"value":Infinity}', '{} trailing'])
def test_json_is_strict(raw):
    with pytest.raises(ControlDocumentError) as error:
        extract_automation_manifest(f"{MANIFEST_BEGIN}\n{raw}\n{MANIFEST_END}")
    assert error.value.code == "AUTOMATION_MANIFEST_INVALID_JSON"


@pytest.mark.parametrize("marker", [PAYLOAD_BEGIN, PAYLOAD_END, MANIFEST_BEGIN, MANIFEST_END])
def test_duplicate_markers_block(marker):
    docs = documents()
    assert not check(DailyDocuments(docs.rnd, docs.slide_design + "\n" + marker)).ready


@pytest.mark.parametrize("change", ["missing_date", "duplicate_date", "bad_date", "duplicate_title", "reversed_markers", "inline_marker"])
def test_metadata_is_deterministic_and_fail_closed(change):
    docs = documents()
    text = docs.rnd
    if change == "missing_date":
        text = text.replace("Production date:", "Unrecognised date:")
    elif change == "duplicate_date":
        text = text.replace("Production date:", "Production date: 2026-10-01\nProduction date:")
    elif change == "bad_date":
        text = text.replace("2026-10-01", "2026-02-30")
    elif change == "duplicate_title":
        text = text.replace("Recommended episode title:", "Working title: THE DELIVERY TEST\nRecommended episode title:")
    elif change == "reversed_markers":
        text = text.replace(PAYLOAD_BEGIN, "TEMP").replace(PAYLOAD_END, PAYLOAD_BEGIN).replace("TEMP", PAYLOAD_END)
    else:
        text = text.replace(PAYLOAD_BEGIN, "prefix " + PAYLOAD_BEGIN)
    assert not check(DailyDocuments(text, docs.slide_design)).ready


@pytest.mark.parametrize("kind,old,new,code", [
    ("rnd", "2026-10-01", "2026-09-30", "RND_STALE"),
    ("rnd", "READY FOR SLIDE DESIGN", "FAILED", "RND_NOT_SUCCESSFUL"),
    ("slide_design", "READY FOR CAROUSEL RENDERING", "DRAFT", "SLIDE_DESIGN_NOT_READY"),
    ("slide_design", "fixture_archive_042", "different_folder", "ARCHIVE_IDENTITY_MISMATCH"),
    ("slide_design", "Ep042-01October2026", "DifferentArchive", "ARCHIVE_IDENTITY_MISMATCH"),
    ("slide_design", "THE DELIVERY TEST", "CHANGED TITLE", "DOCUMENT_TITLE_MISMATCH"),
])
def test_status_freshness_and_archive_identity(kind, old, new, code):
    docs = documents()
    texts = {"rnd": docs.rnd, "slide_design": docs.slide_design}
    texts[kind] = texts[kind].replace(old, new)
    assert code in codes(check(DailyDocuments(**texts)))


def test_rnd_archive_folder_optional_but_design_required():
    docs = documents()
    assert check(DailyDocuments(docs.rnd.replace("Archive folder ID: fixture_archive_042", ""), docs.slide_design)).ready


def test_outside_payload_metadata_is_ignored_and_json_is_opaque():
    docs = documents()
    parsed = parse_daily_metadata("Episode ID: misleading\n" + docs.rnd)
    assert parsed.episode_id == "ep042"
    assert check(DailyDocuments(docs.rnd, "Status: DRAFT\n" + docs.slide_design)).ready


def test_manifest_metadata_changes_block():
    docs = documents()
    manifest = extract_automation_manifest(docs.slide_design)
    manifest["source_rnd_date_sast"] = "2026-09-30"
    assert "MANIFEST_METADATA_MISMATCH" in codes(check(with_manifest(docs, manifest)))


def test_config_is_reused_for_accent_validation():
    docs = documents()
    characters = deepcopy(load_canonical_characters())
    characters["nora"]["accent"] = "#FFFFFF"
    result = DailyBuildReadiness(characters).evaluate(docs, production_date=TODAY)
    assert "ACCENT_COLOUR_INVALID" in codes(result)


def test_sast_date_at_utc_day_boundary_and_without_iana_data(monkeypatch):
    from src import daily_readiness
    assert current_production_date(datetime(2026, 9, 30, 22, 1, tzinfo=timezone.utc)) == TODAY
    assert current_production_date(datetime(2026, 9, 30, 21, 59, tzinfo=timezone.utc)) == date(2026, 9, 30)
    def unavailable(name):
        assert name == "Africa/Johannesburg"
        raise daily_readiness.ZoneInfoNotFoundError(name)
    monkeypatch.setattr(daily_readiness, "ZoneInfo", unavailable)
    assert current_production_date(datetime(2026, 9, 30, 22, 1, tzinfo=timezone.utc)) == TODAY
    with pytest.raises(ValueError):
        current_production_date(datetime(2026, 10, 1))


def test_cli_ready_blocked_json_local_and_missing_inputs(capsys, monkeypatch):
    assert main(["--source", "fixtures", "--date", "2026-10-01"]) == 0
    assert "BUILD READY" in capsys.readouterr().out
    assert main(["--fixture", "stale", "--date", "2026-10-01", "--json"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["state"] == "WAITING_FOR_CURRENT_SLIDE_DESIGN"
    assert result["manifest"] is None
    assert main(["--source", "local", "--rnd-file", str(BASE / "daily_rnd.txt"), "--slide-design-file", str(BASE / "slide_design_valid.txt"), "--date", "2026-10-01"]) == 0
    capsys.readouterr()
    monkeypatch.delenv("AI_GEOPOLITIC_RND_PATH", raising=False)
    monkeypatch.delenv("AI_GEOPOLITIC_SLIDE_DESIGN_PATH", raising=False)
    assert main(["--source", "drive", "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["blockers"][0]["code"] == "INPUT_SOURCE_UNAVAILABLE"
    assert not DailyBuildReadiness().check(LocalFileInput(BASE / "absent", BASE / "absent"), production_date=TODAY).ready


def test_drive_adapter_uses_txt_export_and_exact_paths(monkeypatch):
    calls = []
    def run(args, **kwargs):
        calls.append((args, kwargs))
        if args[1] == "lsjson":
            return subprocess.CompletedProcess(args, 0, json.dumps([{"Name": "Daily R&D.txt"}, {"Name": "Daily Slide Design.txt"}]))
        return subprocess.CompletedProcess(args, 0, "exported text")
    monkeypatch.setattr(subprocess, "run", run)
    source = RcloneDriveInput("ai_geopolitic_drive", "Control/Daily R&D.txt", "Control/Daily Slide Design.txt")
    assert source.read() == DailyDocuments("exported text", "exported text")
    assert len(calls) == 4
    assert all(call[0][-2:] == ["--drive-export-formats", "txt"] for call in calls)
    assert all("shell" not in call[1] and call[1]["timeout"] == 60 for call in calls)


@pytest.mark.parametrize("response", ['[]', '[{"Name":"Daily.txt"},{"Name":"Daily.txt"}]', '{}', 'invalid'])
def test_drive_missing_ambiguous_or_invalid_listing_blocks(monkeypatch, response):
    monkeypatch.setattr(subprocess, "run", lambda args, **kwargs: subprocess.CompletedProcess(args, 0, response))
    with pytest.raises(InputSourceError):
        RcloneDriveInput("drive", "Daily.txt", "Daily.txt").read()


@pytest.mark.parametrize("failure", [FileNotFoundError(), subprocess.TimeoutExpired("rclone", 60), subprocess.CalledProcessError(1, "rclone", stderr="secret")])
def test_drive_errors_are_structured_without_credentials(monkeypatch, failure):
    def run(*args, **kwargs):
        raise failure
    monkeypatch.setattr(subprocess, "run", run)
    result = DailyBuildReadiness().check(RcloneDriveInput("drive", "Daily.txt", "Design.txt"), production_date=TODAY)
    assert codes(result) == {"INPUT_SOURCE_UNAVAILABLE"}
    assert "secret" not in json.dumps(result.to_dict())
