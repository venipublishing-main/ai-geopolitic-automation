# Active Drive v3 readiness — R0/R1 implementation

**Date:** 4 November 2026 (SAST)
**Branch:** `feat/v3-10-slide-readiness-20261104`
**Authority:** [Automation & Manifest Contract v3](https://docs.google.com/document/d/1s4VrG66Z3V-uidPzqtr6VqlKYGTUY6pr0uyHMmfsagg/edit), subordinate to the [Bootstrap Index v3](https://docs.google.com/document/d/1Pn-AJnC219CnyTMO7UkscxXAHF--6qtEcuhLzPImfNU/edit) and [Production Contract v3](https://docs.google.com/document/d/1b3gN0qELVsZtTbe8TAlnhai1EigiuOhexecI7cIyVmY/edit).

## Scope and safety

This is a **pure, zero-generation compatibility adapter**, not a v3 renderer or approval mechanism. It does not generate artwork, mutate Drive, consume provider credits, use local GPU inference or publish.

The frozen historical 20-slide automation is left as the default for the old `DailyBuildReadiness` and `validate_manifest_v2` entry points. This preserves prior benchmark fixtures, original 1080×1080 rendering code, old accent metadata and evidence hashes. Explicitly use `V3DailyBuildReadiness` for active 10-slide production; do **not** use the legacy readiness class to authorise a current build.

## Active v3 input rules

- Daily R&D, Slide Design and Manifest must match the **current Africa/Johannesburg date**, episode ID, title and declared archive identity.
- R&D success status `R&D COMPLETE — READY FOR 10-SLIDE DESIGN` is recognized.
- Slide Design must say exactly `STATUS: READY FOR CAROUSEL RENDERING`.
- Within the unique Daily Slide Design payload there must be exactly one `DESIGN INTEGRITY GATE: PASS`.
- Exactly one manifest block must occur **inside** the payload, after the gate, using the currently approved literal delimiter lines `[BEGIN AUTOMATION MANIFEST JSON marker]` and `[END AUTOMATION MANIFEST JSON marker]`. Legacy `=== BEGIN AUTOMATION MANIFEST JSON ===` is not accepted by the v3 gate.
- The ten human briefs must be numbered SLIDE 01 /10 through SLIDE 10 /10 in order. The slide role and all 17 labelled human fields are compared with their corresponding Manifest object (casting, copy, labels, takeaways, colours, factual guardrails, composition, visual psychology, hierarchy and rendering intentions). Dual CASTING also states its authorised pairing mode. The generic CASTING LOGIC prose is not a JSON field.
- `schema_version` stays integer 2, with the same closed top-level and per-slide keys; slides must be exactly **10**, numbered 1 through 10. One or two canonical panelists, approved pairing modes, exact source facts and three takeaways per slide are validated by the existing strict schema validator.
- Current canonical accents are: Nora `#336BA3`; Diane `#204F39`; Johan `#253852`; Kai `#7352A8`; Thabo `#89301D`; Amari `#8B6E2C`.
- The active PNG portrait **Drive IDs** are pinned in `src/v3_readiness.py`. Old repo portraits, JPEGs and historical accent colours are not the active identity authority.

## External verification is mandatory

The v3 validator requires trusted proof callbacks for:
1. **Archive existence**: `archive_folder_exists(folder_id) -> bool`, backed by an authenticated Drive folder metadata lookup that also checks it is the expected episode folder.
2. **Canonical portrait assets**: `portrait_asset_exists(panelist_slug, file_id) -> bool`, backed by authenticated Drive metadata/readback for the actual approved transparent PNG. Validation must check a PDF/JPEG or unrelated PNG is not substituted.

Without these callbacks, the result is `BUILD_BLOCKED` with `ARCHIVE_FOLDER_UNVERIFIED` and/or `CANONICAL_PORTRAITS_UNVERIFIED`; a valid-looking Drive identifier is **not** proof that the remote asset exists.

The gate only covers **input readiness**. It performs exact human/JSON label comparisons but does **not** independently judge the truth or quality of narrative claims, infer nonliteral dual-panelist logic, verify all Ep128 visual aesthetics, prove 1080×1440 dimensions or pixel identity, confer user acceptance, or authorise publication. Those remain separate downstream QC/authorization stages. Do not launch BUILD or PUBLISH on the basis of a synthetic test.

## Developer example

```python
from datetime import date

from src.production_inputs import DailyDocuments
from src.v3_readiness import V3DailyBuildReadiness

# Supply real, separately retrieved Drive document text:
docs = DailyDocuments(rnd=rnd_text, slide_design=slide_design_text)
gate = V3DailyBuildReadiness(
    archive_folder_exists=trusted_drive_archive_lookup,
    portrait_asset_exists=trusted_drive_canonical_png_lookup,
)
result = gate.evaluate(docs, production_date=date(2026, 11, 4))
print(result.to_dict())
```

No production Drive checker is wired in this milestone. The existing legacy `python -m src.daily_readiness` CLI is **not** automatically upgraded to v3 and should not be used as a v3 readiness signal.

## Regression

```sh
python -m pytest -q tests/test_daily_readiness.py tests/test_v3_readiness.py
```

The new tests build a synthetic ten-slide Ep136-shaped envelope from frozen local fixtures; they do not commit the live Daily Slide Design or re-render accepted Ep136 assets. Cases cover valid single/dual casting, ten ordered human briefs and all 17 labelled field synchronizations plus slide role, legacy 20-slide compatibility, wrong slide counts, stale dates, invalid gates, wrong marker forms and location, v3 accents, closed schema, remote lookup failure and absent proof callbacks.

## Next engineering gates

**R1b:** connect authenticated Drive lookup callbacks; read the live Ep136 R&D/Slide Design as an **immutable regression snapshot**, confirm actual archives and canonical PNG mime/dimensions/alpha without modifying them. Run local and CI Python tests; record observed results.

**R2:** deterministic 1080×1440 single-slide composition and exact 10-dot/counter QC with original canon; one background per item; compare against Ep128 with human visual acceptance. Legacy 20-slide renderer remains historical.

**R3–R5:** tightly bounded zero-cost contextual-art benchmark, ten-slide draft build, six distinct reel frames, selective EDIT, then authenticated PUBLISH only with explicit approval and idempotent state.

**No provider calls and no publication until authorised.**

## Observed connected-Drive audit and CI (4 November 2026)

The separate [read-only Ep136 audit](R1B_EP136_LIVE_READONLY_AUDIT_20261104.md) verified the live Daily R&D + Daily Slide Design (10 human briefs and 10 strict Manifest objects; **180/180 inspected human/JSON field comparisons agree**), the expected Ep136 archive folder, all 16 archived PNG filenames and the current six canonical transparent-source PNG IDs/MIME/parents. PNG alpha and byte equivalence were NOT examined. This does NOT wire runtime Drive checkers.

At commit `ce6205119fcd2970f7830a2a8dc49cfe84f75c1e`, GitHub Actions [run #41860621874](https://github.com/venipublishing-main/ai-geopolitic-automation/actions/runs/41860621874) reported **160 passed, zero failed** for `tests/test_daily_readiness.py` and `tests/test_v3_readiness.py` on Python 3.12. It was a scoped test suite, not the entire historical repo.
