# Daily control-document ingestion — Phase A / A.1

Phase A implements:

```text
ProductionInput.read() -> DailyDocuments (two current text snapshots)
  -> exact daily-payload metadata + exact automation JSON extraction
  -> canonical-config-backed v2 validation + SAST freshness/identity gate
  -> DailyBuildReadinessResult: BUILD READY or BUILD BLOCKED with blockers
```

`MemoryInput`, `LocalFileInput` and `RcloneDriveInput` implement the small source
protocol in `src/production_inputs.py`. I/O is isolated from the pure parsing and
validation modules. `DailyBuildReadiness.evaluate()` accepts already-read text;
`check()` obtains that text through the protocol and reports source failures.
No network or subprocess call occurs during metadata or manifest validation.

## Deterministic control metadata

Both documents require exactly one ordered pair of standalone literal markers:

```text
=== BEGIN DAILY PAYLOAD ===
Production date: 2026-10-01
Status: READY FOR SLIDE DESIGN
Episode ID: ep042
Recommended episode title: THE DELIVERY TEST
Archive destination: AI-Geopolitical / History - Episode List / Ep042-01October2026
Archive folder ID: fixture_archive_042
=== END DAILY PAYLOAD ===
```

For Slide Design use `Status: READY FOR CAROUSEL RENDERING` and `Working title: ...`,
and add:

```text
Source Daily R&D date: 2026-10-01
Source Daily R&D episode: ep042
```

Phase A.1 also accepts the actual Ep102 metadata shape supplied for integration.
Metadata labels are case insensitive and allow surrounding whitespace, but are
otherwise literal `label: value` lines. The explicit alias table accepts:

| Semantic field | Supported labels |
|---|---|
| Production date | `PRODUCTION DATE`, `PRODUCTION DATE (SAST)`, `PRODUCTION DATE SAST` |
| Episode ID | `EPISODE`, `EPISODE ID` |
| Title | `WORKING TITLE`, `WORKING EPISODE TITLE`, `RECOMMENDED EPISODE TITLE`, `RECOMMENDED EPISODE / WORKING TITLE` |
| Source date | `SOURCE DAILY R&D DATE` |
| Source episode | `SOURCE DAILY R&D EPISODE` |

Existing status and archive labels remain unchanged. Duplicate aliases resolving
to one field still fail closed, even when their values agree. No fuzzy label
matching, Markdown label interpretation, multiline values or prose inference is
used.

Human dates accept either ISO `YYYY-MM-DD` or the complete English form
`Thursday, 1 October 2026`. English month/weekday names are parsed through explicit
maps rather than process locale. Names are case insensitive; abbreviated names
and dates without a weekday are unsupported. The weekday must agree with the
calendar date. Impossible dates and contradictory weekdays fail closed. Manifest
v2 dates and the CLI `--date` argument remain strictly ISO.

The source episode value accepts a safe episode ID alone or `ID — TITLE`, using a
spaced em dash. Thus `Ep102 — CHINA IS BUILDING A WAY OUT OF CUDA` becomes episode
ID `Ep102` plus an optional source title. Malformed references fail closed; the
parser does not guess other separators. The source title, when supplied, must
match Daily R&D's title even if Slide Design also has an explicit title.

Required labels: production date, status, episode ID and archive destination;
Daily R&D also requires a title. Slide Design requires source Daily R&D date/episode
and obtains its title from an explicit title field or, when that field is absent,
the combined source-reference title. A blank explicit title is invalid and is not
silently replaced. A bare source ID without either title leaves metadata incomplete.
Missing, blank or invalid required values fail closed. R&D's folder ID is optional when
absent; Slide Design and the manifest require it. Any supplied R&D ID must match.
Metadata outside the daily payload is ignored. JSON contents are opaque to the
metadata parser. The full v2 contract and exact JSON markers are documented in
[EPISODE_SCHEMA_V2.md](EPISODE_SCHEMA_V2.md).

Accepted successful R&D statuses are exactly `COMPLETE`, `R&D COMPLETE`,
`READY FOR SLIDE DESIGN`, or `R&D COMPLETE — READY FOR 20-SLIDE DESIGN`.
Accepted Slide Design completion statuses are exactly `READY FOR CAROUSEL RENDERING`
or `20-SLIDE BLUEPRINT COMPLETE — READY FOR MANUAL RENDERING`. These represent an
explicit successful upstream handoff; arbitrary text containing READY still blocks.
The manual-rendering status acknowledges a completed blueprint during Phase A.1;
it does not waive JSON validation or start a renderer. A future status such as
`20-SLIDE BLUEPRINT COMPLETE — READY FOR AUTOMATED RENDERING` must be added explicitly
to the completion-status set in a later change; it is not enabled yet.
Status values and identity strings are case sensitive.
Titles, archive destinations and supplied archive IDs must agree exactly after
trimming surrounding metadata whitespace.

## Readiness and the daily transition

The current day is computed in `Africa/Johannesburg`. An aware UTC clock is
converted using `zoneinfo`; Windows installations lacking IANA data use modern
Johannesburg's fixed UTC+02:00 fallback. `--date` explicitly injects a production
day for reproducible developer checks; it does not default to the input date.

Both daily dates must equal that day. Slide Design's source R&D date/episode must
match R&D. The manifest must match both documents' episode, title, production/source
dates, and archive identity. All strict slide checks must pass before readiness.

Today's R&D plus yesterday's otherwise-valid Slide Design returns:

```text
BUILD BLOCKED | WAITING_FOR_CURRENT_SLIDE_DESIGN
```

Yesterday's design is never reused. Future dates are also blocked. Missing or
unparseable inputs, unsuccessful R&D, a design that is not ready, or invalid JSON
also return BUILD BLOCKED. There is no last-known-good fallback or persistent state.

Results contain `production_date_sast`, `build`, `state`, `blockers` and `manifest`.
Each blocker has `code`, `message` and `path`. Only a READY result exposes the
validated manifest; a BLOCKED result has `manifest: null`. Codes include
`RND_STALE`, `SLIDE_DESIGN_STALE`, `SOURCE_RND_MISMATCH`, `EPISODE_MISMATCH`,
`SOURCE_RND_TITLE_MISMATCH`, `SOURCE_EPISODE_INVALID`,
`RND_NOT_SUCCESSFUL`, `SLIDE_DESIGN_NOT_READY`, `AUTOMATION_MANIFEST_MISSING`,
`AUTOMATION_MANIFEST_INVALID_JSON`, `MANIFEST_SCHEMA_UNSUPPORTED`,
`MANIFEST_METADATA_MISMATCH`, `ARCHIVE_IDENTITY_MISMATCH`, `ARCHIVE_FOLDER_MISSING`,
`SLIDE_COUNT_INVALID`, `SLIDE_NUMBER_INVALID`, `UNKNOWN_PANELIST`,
`DUAL_PAIRING_INVALID`, `SINGLE_PAIRING_INVALID`, `ACCENT_COLOUR_INVALID` and
`INPUT_SOURCE_UNAVAILABLE`. Independent validatable checks accumulate blockers;
checks dependent on missing/invalid metadata are skipped rather than guessed.

Archive IDs are checked for presence, syntax and declared agreement. Phase A does
not verify remote folder existence or permissions. Two Drive reads are sequential
snapshots, not an atomic Drive transaction; inconsistent versions fail the gate.

## Developer CLI

Run from the repository root with Python 3.12+:

```powershell
python -m src.daily_readiness --source fixtures --date 2026-10-01
python -m src.daily_readiness --source fixtures --fixture stale --date 2026-10-01
python -m src.daily_readiness --source fixtures --date 2026-10-01 --json
python -m src.daily_readiness --source local --rnd-file daily-rnd.txt --slide-design-file daily-design.txt
python -m src.daily_readiness --source drive --json
```

Exit code is `0` for READY, `1` for BLOCKED, `2` for invalid CLI arguments. Fixture
dates are fixed at 2026-10-01; omitting `--date` intentionally uses the actual day.
Both local file arguments may also override fixture paths together. Local files
must be UTF-8 (an initial BOM is accepted). The CLI writes no production artifacts.

## Live Drive setup

This adapter follows the repository's existing `ai_geopolitic_drive` rclone remote
precedent in `setup-rclone-drive.md` and the GitHub proof workflows. It adds no
Google SDK or Python dependencies. Configure an authorized rclone Drive remote
outside the repository, preferably with read-only access for this ingestion job.
Keep tokens/config files outside Git; existing rclone environment configuration
is inherited without being printed or rewritten.

Set:

```powershell
$env:AI_GEOPOLITIC_DRIVE_REMOTE = 'ai_geopolitic_drive'
$env:AI_GEOPOLITIC_RND_PATH = 'Control/Daily R&D.txt'
$env:AI_GEOPOLITIC_SLIDE_DESIGN_PATH = 'Control/Daily Slide Design.txt'
# Optional if rclone is not on PATH:
$env:AI_GEOPOLITIC_RCLONE = 'C:\Tools\rclone.exe'
python -m src.daily_readiness --source drive
```

Paths are relative to the configured remote root. A native Google Doc named
`Daily R&D` is exposed as `Daily R&D.txt` with `--drive-export-formats txt`, as
described in the [rclone Drive export documentation](https://rclone.org/drive/#import-export-of-google-documents).
The adapter lists the parent with `lsjson --files-only`, requires exactly one
matching exported name, then reads it with [rclone cat](https://rclone.org/commands/rclone_cat/).
Both calls use TXT export, argument arrays without a shell, and a 60-second timeout.
Ambiguous filenames fail instead of concatenating several documents. Listing/read
failures return a sanitized source blocker without exposing rclone stderr.

Live access has not been exercised in Phase A/A.1. Phase A.1 verifies the supplied
Ep102 metadata through local reproductions, using synthetic archive IDs. Setup
still requires rclone, an authorized remote, exact unique document paths, and
confirmation of the actual exports. No real Drive document is modified by this
repository. The upstream ChatGPT Slide Design automation must add the complete
v2 JSON block while leaving the human blueprint intact. That JSON must use ISO
dates even if the human metadata uses long-form dates. Until then missing JSON
blocks BUILD.

## Ep102 pre-handoff integration check

The local Ep102 metadata fixtures omit the JSON block, as the supplied current
Slide Design does. They include the full live completion statuses, a combined
source episode/title, long-form dates and no separate Slide Design title.
For the supplied production day, run:

```powershell
python -m src.daily_readiness --source local --rnd-file tests/fixtures/daily_readiness/daily_rnd_ep102.txt --slide-design-file tests/fixtures/daily_readiness/slide_design_ep102.txt --date 2026-10-01 --json
```

Expected result: BUILD BLOCKED, exit 1, with exactly
`AUTOMATION_MANIFEST_MISSING`. Human metadata parsing, status, episode, source date,
title and declared archive checks all pass. A synthetic test adds a fully valid
ISO-dated v2 manifest to these texts and requires READY. Subsequent real daily
checks must use the current SAST day rather than continuing to override the date
to 2026-10-01.

Phase A.1 validation: all **291 tests passed** using the documented Windows QA
adapter (102 existing + 119 Phase A + 70 integration tests). The 189 Phase A/A.1
tests also passed with ordinary pytest. The local Ep102 CLI check returned exit 1
with only `AUTOMATION_MANIFEST_MISSING`; the synthetic ISO JSON handoff integration
returned READY. Existing renderers, Milestone 5.2, config/assets, dependencies and
GitHub workflows were not modified.

## Fixtures and validation

`tests/fixtures/daily_readiness/` contains compact realistic payload envelopes,
one current 20-slide design, one stale design, and `cases.json` with deterministic
failure variants. The tests materialize those variants in memory to avoid copying
20 slides for every failure. Coverage includes the requested 13 acceptance scenarios,
all required fields, blank copy, strict JSON, malformed markers, canonical accents,
dual relationships, SAST rollover, source errors and CLI output/exit codes.

Run the complete existing and new suite with `python -m pytest -q` in the configured
QA environment. The existing rendering tests require DejaVu fonts at their existing
Linux paths (the GitHub Actions environment). Phase A does not change font routing,
renderers, proof workflows, image generation, publishing or persistent state.

### Phase A validation on 2026-10-01

The complete suite passed: **221 tests (102 existing + 119 new), 0 failures**.
This included the existing v1 20-slide production proofs and the Milestone 5.2
context-art regression render. The standalone new suite passed with the ordinary
pytest command. Both JSON CLI demonstrations also ran under the system Python
without extra packages: valid fixture -> READY / exit 0 / 20 slides; stale fixture
-> WAITING_FOR_CURRENT_SLIDE_DESIGN / exit 1 / no buildable manifest.

Local QA used Python 3.12.14 with the repository's pinned Pillow 11.3.0 and pytest
8.4.1 in the ignored `.venv/qa/` environment. An initial plain Windows run failed
because the existing Linux font paths were unavailable. Supplying DejaVu alone
left two existing Diane layout failures due to missing text shaping support.
Enabling Pillow's documented
[FriBiDi support](https://pillow.readthedocs.io/en/stable/installation/building-from-source.html)
resolved those failures without editing source or assertions.

The local `.venv/qa/run_full_qa.py` adapter maps only the existing Linux DejaVu
font paths to the original local font files and loads the local FriBiDi DLL before
Pillow. It invokes the full `pytest -q --tb=short` suite without skipping tests,
changing layouts or altering metrics. Rerun this prepared environment with:

```powershell
.\.venv\qa\Scripts\python.exe .venv/qa/run_full_qa.py
```

Fonts came from the original
[DejaVu 2.37 release](https://github.com/dejavu-fonts/dejavu-fonts/releases/tag/version_2_37),
and the shaping DLL from the official
[MSYS2 FriBiDi package](https://packages.msys2.org/packages/mingw-w64-ucrt-x86_64-fribidi).
Both archive SHA256 values were verified against the publishers' values. These
are local QA artifacts, not production dependencies or tracked project files.
The existing Linux GitHub Actions font/shaping setup and workflows remain intact;
no remote workflow was dispatched during Phase A.
