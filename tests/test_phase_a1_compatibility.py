"""Independent integration checks for the supplied Ep102 control-document format."""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.control_documents import (MANIFEST_BEGIN, MANIFEST_END, ControlDocumentError,
                                   extract_automation_manifest, parse_control_date,
                                   parse_daily_metadata)
from src.daily_readiness import DailyBuildReadiness, main
from src.production_inputs import DailyDocuments, LocalFileInput

BASE = ROOT / "tests/fixtures/daily_readiness"
TODAY = date(2026, 10, 1)
TITLE = "CHINA IS BUILDING A WAY OUT OF CUDA"


def live_documents():
    return LocalFileInput(BASE / "daily_rnd_ep102.txt", BASE / "slide_design_ep102.txt").read()


def evaluate(docs):
    return DailyBuildReadiness().evaluate(docs, production_date=TODAY)


def handoff_manifest():
    # Compact engineering slide content, with only the supplied live envelope metadata.
    manifest = extract_automation_manifest((BASE / "slide_design_valid.txt").read_text(encoding="utf-8"))
    manifest.update(episode_id="Ep102", episode_title=TITLE, archive_destination="Ep102-1October2026",
                    archive_folder_id="fixture_archive_102")
    return manifest


def add_handoff(docs, manifest):
    block = f"\n{MANIFEST_BEGIN}\n{json.dumps(manifest)}\n{MANIFEST_END}\n"
    return DailyDocuments(docs.rnd, docs.slide_design + block)


def test_ep102_without_handoff_is_blocked_only_by_missing_json():
    docs = live_documents()
    rnd = parse_daily_metadata(docs.rnd)
    design = parse_daily_metadata(docs.slide_design, slide_design=True)
    assert rnd.production_date == design.production_date == design.source_rnd_date == TODAY
    assert rnd.episode_id == design.episode_id == design.source_rnd_episode == "Ep102"
    assert rnd.episode_title == design.episode_title == design.source_rnd_title == TITLE
    assert "WORKING TITLE:" not in docs.slide_design
    result = evaluate(docs)
    assert result.build == "BLOCKED" and result.manifest is None
    assert [item.code for item in result.blockers] == ["AUTOMATION_MANIFEST_MISSING"]


def test_live_format_with_iso_handoff_is_ready():
    result = evaluate(add_handoff(live_documents(), handoff_manifest()))
    assert result.ready and not result.blockers
    assert result.manifest["production_date_sast"] == "2026-10-01"
    assert result.manifest["source_rnd_date_sast"] == "2026-10-01"


@pytest.mark.parametrize("label", ["PRODUCTION DATE", "PRODUCTION DATE (SAST)", "PRODUCTION DATE SAST"])
def test_production_date_aliases(label):
    doc = live_documents().rnd.replace("PRODUCTION DATE (SAST):", label + ":")
    assert parse_daily_metadata(doc).production_date == TODAY


@pytest.mark.parametrize("label", ["EPISODE", "EPISODE ID"])
def test_episode_aliases(label):
    doc = live_documents().rnd.replace("EPISODE:", label + ":")
    assert parse_daily_metadata(doc).episode_id == "Ep102"


@pytest.mark.parametrize("label", ["WORKING TITLE", "WORKING EPISODE TITLE", "RECOMMENDED EPISODE TITLE",
                                   "RECOMMENDED EPISODE / WORKING TITLE"])
def test_title_aliases(label):
    doc = live_documents().rnd.replace("WORKING TITLE:", label + ":")
    assert parse_daily_metadata(doc).episode_title == TITLE


@pytest.mark.parametrize("line", ["PRODUCTION DATE SAST: 2026-10-01", "EPISODE ID: Ep102",
                                  "RECOMMENDED EPISODE / WORKING TITLE: " + TITLE])
def test_duplicate_semantic_aliases_still_fail_closed(line):
    docs = live_documents()
    rnd = docs.rnd.replace("=== END DAILY PAYLOAD ===", line + "\n=== END DAILY PAYLOAD ===")
    assert "METADATA_AMBIGUOUS" in {item.code for item in evaluate(DailyDocuments(rnd, docs.slide_design)).blockers}


@pytest.mark.parametrize("text,expected", [
    ("2026-10-01", TODAY), ("Thursday, 1 October 2026", TODAY),
    ("thursday, 01 october 2026", TODAY),
    ("Thursday, 1 January 2026", date(2026, 1, 1)),
    ("Sunday, 1 February 2026", date(2026, 2, 1)),
    ("Sunday, 1 March 2026", date(2026, 3, 1)),
    ("Wednesday, 1 April 2026", date(2026, 4, 1)),
    ("Friday, 1 May 2026", date(2026, 5, 1)),
    ("Monday, 1 June 2026", date(2026, 6, 1)),
    ("Wednesday, 1 July 2026", date(2026, 7, 1)),
    ("Saturday, 1 August 2026", date(2026, 8, 1)),
    ("Tuesday, 1 September 2026", date(2026, 9, 1)),
    ("Sunday, 1 November 2026", date(2026, 11, 1)),
    ("Tuesday, 1 December 2026", date(2026, 12, 1)),
    ("Thursday, 29 February 2024", date(2024, 2, 29)),
])
def test_dates_use_explicit_english_calendar(text, expected):
    assert parse_control_date(text) == expected


@pytest.mark.parametrize("text", ["Friday, 1 October 2026", "Thursday, 31 February 2026",
                                  "Thursday, 1 Oct 2026", "Thu, 1 October 2026", "1 October 2026",
                                  "Thursday, 1 Oktober 2026", "01/10/2026", "2026-02-30",
                                  "Thursday, 29 February 2026", "Thursday, 1 October 2026 extra"])
def test_malformed_or_contradictory_dates_block(text):
    docs = live_documents()
    docs = DailyDocuments(docs.rnd.replace("Thursday, 1 October 2026", text), docs.slide_design)
    assert "METADATA_DATE_INVALID" in {item.code for item in evaluate(docs).blockers}


@pytest.mark.parametrize("reference", ["", "Ep102 —", "— TITLE", "Ep102—TITLE", "Ep102 - TITLE",
                                      "Ep102 / TITLE", "Ep102 TITLE", "Ep102 — — TITLE"])
def test_malformed_combined_source_reference_blocks(reference):
    docs = live_documents()
    design = docs.slide_design.replace("Ep102 — " + TITLE, reference)
    assert not evaluate(DailyDocuments(docs.rnd, design)).ready
    with pytest.raises(ControlDocumentError):
        parse_daily_metadata(design, slide_design=True)


def test_explicit_title_and_bare_source_id_remain_supported():
    docs = live_documents()
    design = docs.slide_design.replace("Ep102 — " + TITLE, "Ep102")
    design = design.replace("=== END DAILY PAYLOAD ===", "WORKING TITLE: " + TITLE + "\n=== END DAILY PAYLOAD ===")
    parsed = parse_daily_metadata(design, slide_design=True)
    assert parsed.source_rnd_episode == "Ep102" and parsed.source_rnd_title is None
    assert evaluate(add_handoff(DailyDocuments(docs.rnd, design), handoff_manifest())).ready


@pytest.mark.parametrize("explicit", [False, True])
def test_source_title_must_match_rnd_even_with_correct_explicit_title(explicit):
    docs = live_documents()
    design = docs.slide_design.replace("Ep102 — " + TITLE, "Ep102 — CONTRADICTORY TITLE")
    if explicit:
        design = design.replace("=== END DAILY PAYLOAD ===", "WORKING TITLE: " + TITLE + "\n=== END DAILY PAYLOAD ===")
    result = evaluate(add_handoff(DailyDocuments(docs.rnd, design), handoff_manifest()))
    assert "SOURCE_RND_TITLE_MISMATCH" in {item.code for item in result.blockers}


def test_blank_explicit_title_is_not_silently_replaced():
    docs = live_documents()
    design = docs.slide_design.replace("=== END DAILY PAYLOAD ===", "WORKING TITLE: \n=== END DAILY PAYLOAD ===")
    assert "METADATA_MISSING" in {item.code for item in evaluate(DailyDocuments(docs.rnd, design)).blockers}


@pytest.mark.parametrize("kind,status", [
    ("rnd", "ALREADY READY"), ("rnd", "R&D COMPLETE - READY FOR 20-SLIDE DESIGN"),
    ("slide_design", "READY"),
    ("slide_design", "20-SLIDE BLUEPRINT COMPLETE — READY FOR AUTOMATED RENDERING"),
])
def test_statuses_are_explicit_not_substring_matches(kind, status):
    docs = live_documents()
    if kind == "rnd":
        docs = DailyDocuments(docs.rnd.replace("R&D COMPLETE — READY FOR 20-SLIDE DESIGN", status), docs.slide_design)
    else:
        docs = DailyDocuments(docs.rnd, docs.slide_design.replace("20-SLIDE BLUEPRINT COMPLETE — READY FOR MANUAL RENDERING", status))
    code = "RND_NOT_SUCCESSFUL" if kind == "rnd" else "SLIDE_DESIGN_NOT_READY"
    assert code in {item.code for item in evaluate(add_handoff(docs, handoff_manifest())).blockers}


@pytest.mark.parametrize("relationship", ["converge", "oppose", "partially_overlap", "synthesize"])
def test_all_four_relationship_enum_values_are_valid(relationship):
    manifest = handoff_manifest()
    manifest["slides"][1]["central_relationship"] = relationship
    assert evaluate(add_handoff(live_documents(), manifest)).ready


@pytest.mark.parametrize("relationship", ["An arbitrary description", "CONVERGE", " converge ", "", None, {}])
def test_arbitrary_relationship_values_are_invalid(relationship):
    manifest = handoff_manifest()
    manifest["slides"][1]["central_relationship"] = relationship
    assert "DUAL_PAIRING_INVALID" in {item.code for item in evaluate(add_handoff(live_documents(), manifest)).blockers}


@pytest.mark.parametrize("relationship", ["", "converge"])
def test_single_panelist_relationship_must_be_null(relationship):
    manifest = handoff_manifest()
    manifest["slides"][0]["central_relationship"] = relationship
    assert "SINGLE_PAIRING_INVALID" in {item.code for item in evaluate(add_handoff(live_documents(), manifest)).blockers}


@pytest.mark.parametrize("field", ["production_date_sast", "source_rnd_date_sast"])
def test_manifest_dates_stay_iso_only(field):
    manifest = handoff_manifest()
    manifest[field] = "Thursday, 1 October 2026"
    assert "MANIFEST_DATE_INVALID" in {item.code for item in evaluate(add_handoff(live_documents(), manifest)).blockers}


def test_live_format_cli_reports_only_missing_manifest(capsys):
    result = main(["--source", "local", "--rnd-file", str(BASE / "daily_rnd_ep102.txt"),
                   "--slide-design-file", str(BASE / "slide_design_ep102.txt"), "--date", "2026-10-01", "--json"])
    assert result == 1
    assert [item["code"] for item in json.loads(capsys.readouterr().out)["blockers"]] == ["AUTOMATION_MANIFEST_MISSING"]
