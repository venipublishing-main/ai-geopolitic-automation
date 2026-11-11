# R2.2c — Real canonical-portrait single/dual proof checkpoint

**Date:** 11 November 2026 (SAST)  
**Repository:** `venipublishing-main/ai-geopolitic-automation` **ONLY**  
**Branch:** `feat/r2-2c-canonical-proof-20261111` stacked on draft PR #5  
**Episode:** *Historical* accepted Ep136 (4 November 2026), used as a read-only regression input. NOT a current-day episode or a replacement of accepted Ep136 assets.

## Inputs and provenance

- Read original archived [Ep136 Slide Design](https://docs.google.com/document/d/1nzuxxVoyZtNqQ5w7gLKimv5FVQoRqXhjlILIhz44oJc/edit) as exported text. The archived doc's standing instructions include example manifest delimiters; the test runner parses the final active JSON block, checks `Ep136` / `2026-11-04`, and validates the complete closed Manifest v2.
- Used accepted archived **Slide 01 Nora** and **Slide 09 Nora + Amari** as two distinct analytic layout cases; did not read or change current Daily Slide Design.
- Loaded the exact original Drive transparent `Nora_CANONICAL_PANELIST.png` and `Amari_Ndlovu_CANONICAL_PANELIST.png` bytes into an isolated local execution environment. SHA-256 values were checked against the pinned allowlist in `src/v3_canon_assets.py`:
  - Nora `9a82adee1f10515e8e97108579fb2f646debdc697995efbe8e223c348650600c`
  - Amari `0eccf1164eb8dbfc7ec1c81a5b2f8c5ffabb19236965f9c85aa139296a0ffee4`
- The original approved **Ep128 Slides 01 and 09** were loaded from their exact source bytes and SHA-256 checked as style-input provenance. Neither image was stretched, recoloured, overlaid into the new output or committed to GitHub.
- Original accepted Ep136 Slides 01 and 09 were inspected side-by-side as visual quality comparison only.

## Code implemented

- Added a fifth optional arrangement: `paired-synthesis`. It permits two genuine complementary voices grouped at the left of a shared right-side apparatus; does not require an artificial opposing-face-off layout.
- Added `PortraitPlacement.fit = "cover"` as an **aspect-preserving proportional crop** (legacy default remains `contain`). Portrait source pixels are never stretched, colour-washed or re-generated; crops can strengthen legibility while retaining the originally approved face.
- Added output-readback **opaque-pixel integrity verification**. For every assigned PNG, compare all fully opaque pixels of the *actual resized/cropped original source* to the decoded final exported PNG after foreground linework, lettering and furniture. Any mismatch blocks composition. The external per-item Render Integrity checker requires the corresponding proof map.
- Added `src/v3_historical_proof.py`: local-only, offline, deterministic **bespoke technical schematic** illustrating Ep136 Slide 01's layered sovereignty/access map and Slide 09's five-ring sovereignty mechanism. Exact headlines, subheadlines, essential labels and main phrases come from historical Manifest v2; original portraits and Ep128 style references are required. Distinct scene geometry and protected foreground overlays are used. No source assets or original portraits are embedded in GitHub.
- Added offline regressions for synthesis spacing, source-output pixel preservation, proportional cover crop, forbidden stretching and wrong historical fixture IDs. The existing R1b and R2.1/R2.2 test suites remain intact.
- A short-lived GitHub Actions artifact packages **source code only**, not original portraits, historical editorial text or proofs, allowing a local test against approved data without adding private images to CI.

## Actual local read-only proof execution

The source-only package from the scoped GitHub Actions job was unpacked in a disposable test directory. The historical accepted Ep136 slide blueprint and raw canonical assets were read locally; the proof runner generated **two independent standalone 1080×1350 RGB PNGs**, plus separate QC receipts. Exact output hashes:

| Historical test item | SHA-256 of final test PNG | Source-pixel audit | External Render Integrity Gate |
|---|---|---|---|
| Slide 01 — Nora | `11add2e2a31e7fc27b066a5c083d2364e92feb5b8aad659d74270c25d60a79b7` | `nora=True` | `HUMAN_REVIEW_REQUIRED` |
| Slide 09 — Nora / Amari | `e0f9e3d2c87542c59f96bd984f2f15594c1c465a9e7608f1fdab026f26549bcd` | `nora=True, amari_ndlovu=True` | `HUMAN_REVIEW_REQUIRED` |

Both QC receipts report exact current v3.1 4:5 dimensions, correct slide count/counter positions, explicit pending review and `publication_authorised=False`. No external image provider calls or publishing took place. Files remain in an isolated local proof directory; they were **not uploaded to GitHub, the manual directory, the episode archive or Daily Operations**.

## Visual inspection and honest acceptance

**Engineering source/geometry proof: PASS. Premium visual acceptance: NOT GRANTED.**

Observed improvements compared with the previous wholly synthetic fixture:
- Correct, recognisable actual canonical Nora and Amari identities, with source-hash verification and post-export fully opaque pixel equality.
- More prominent faces via permitted proportional crop, materially placed source phrases, distinct mapped/wheel analytic concepts, exact 4:5 raster and complete fixed publication furniture.
- Correctly separate final output assets and independent QC receipts; no generated substitute faces.

Remaining deficiencies versus inspected *accepted* Ep136 and *primary Ep128* style:
- Simplified vector map and sovereignty wheel are far less sophisticated than the accepted engraved, high-information hero systems.
- The illustrations have little contextual detail, nuanced analytical annotations or material architecture.
- Portrait integration remains too abruptly rectangular at some crop edges, especially the two-panelist proof.
- Masthead, headline and supporting information hierarchy are mechanically correct but materially flatter than the premium reference.
- Not all approved three-takeaway ideas receive an equally developed informational visual treatment.
- Ep128-grade spatial depth, lettering/tactility and argument-specific editorial density remain unproven.

The engineering proofs must not be treated as accepted replacements or published assets. Their receipts remain `HUMAN_REVIEW_REQUIRED`, and they do not confer an automatic PASS.

## Next gate — R2.2d

Build a genuinely richer background/foreground scene authoring method (human-reviewed assets or bounded provider research), protect portrait cutout edges, use full accepted fact/takeaway content, and redesign material lettering surfaces to inhabit the illustration rather than a quiet poster strip. Compare a true premium single and authorised dual proof against Ep128 and archival Ep136. Continue using local proof isolation and item-level visual QC before any archive or posting.

**Safety:** No changes to `main`, legacy R2, manual canonical ledgers, source portraits or accepted episode archive. All development remains draft-only.
