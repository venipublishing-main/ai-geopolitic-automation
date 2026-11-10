# R2.2b — Argument-responsive compositions & material-integrated lettering

**Automation-only engineering** | 10 November 2026 | stacked on R2.2 protected scene layers.  
**Production authority:** active Drive Bootstrap / Production / Automation / Ep128 v3.1 read-only ledgers.  
**No modifications** to the Manual directory, source portraits, accepted Ep142 archives, production assets, publishing accounts or old historical renderer branches.

## Why

The first 4:5 synthetic R2 proof and protected-layer proof passed geometry/QC tests, but their artwork still appeared flat and template-driven. The editorial requirement is not merely placing a face and headline on a poster. Layout must follow the specific argumentative visual mechanism, with exact text integrated into an illustrative surface whenever feasible.

## Added software

- `src/v3_adaptive_layout.py` defines **per-slide, explicit** geometries: `portrait-left`, `portrait-right`, `central-portrait`, and `paired-dialogue`. No permanent layout assignment by panelist or topic. The old `legacy` mode is retained only as compatibility path.
- `LetteringSurface` defines a physically reserved and *reviewed* area within the bespoke hero, including material (`engraved` / `stamped`), a tightly bounded rotation and exact pixel coordinates. Any surface crossing editorial safe areas or an actual portrait aperture is blocked.
- `compose_material_lettering` typesets the **exact source `main_visual_phrase`**, wraps without invented copy, preserves all required characters, applies repeatable dry-ink distress and restrained perspective while leaving the underlying artwork visible outside glyph pixels. It does **not create a filled opaque card**. A contrast/complexity preflight rejects overly busy background regions. Material art surfaces are human-authored; the algorithm cannot certify artistic quality.
- `compose_r2_slide` optionally executes the new plan and moves the source phrase **from the detached lower strip into its designated illustrated surface**. Supporting subheadline and essential evidence labels remain deterministic lower editorial copy. A corresponding independent QC receipt records arrangement, exact text SHA, material orientation, font and reviewed surface coordinates.
- Existing alpha-protected foreground illustration remains independent. All six pinned original PNG source hash gates, current 4:5 output, 10 dots, counter, masthead and ideological footer remain mandatory.

## Safety and fallbacks

- Missing surface review, unapproved layout, portrait overlap, unreadable long words, too-small typesetting, extreme rotation and geometry drift fail closed.
- This system cannot generate bespoke scene artwork, replace a human inspection, or determine whether an unrelated generated human appears in a background.
- For a background with no viable real lettering surface, the active v3.1 Production Contract permits accurate type on deliberate negative space. Do not fake material integration with an opaque overlaid box.
- `RENDER_QC_PENDING` remains the default even if all deterministic checks pass; visual/source-fact/style/continuity approval stays separate. No publishing path or Drive archival writes have been added.

## QA and visual proof

Scoped synthetic tests are in `tests/test_v3_adaptive_layout.py`, covering different portrait arrangements, material phrase accuracy, no opaque cards, wrong-side and dual errors, unreviewed/overlapping surfaces, out-of-range rotation and exact copy overflow. The existing R1b and R2 tests run alongside them in GitHub Actions.

A short-lived **synthetic, not-for-publication 4:5** artifact can be retrieved and inspected. This is *not* an accepted Ep128-quality real slide; its fake portrait and placeholder hero are deliberately used to test one engineering feature only.

**Next gate:** inspect CI artifact, then create genuine single- and dual-panelist proof with separately approved bespoke hero art and original hash-pinned PNGs. Establish per-image RENDER_QC evidence. Do not promote a software test to visual acceptance, merge the stacked PRs or publish.

## Verified engineering checkpoint — 10 November 2026

- [GitHub Actions #42844925356](https://github.com/venipublishing-main/ai-geopolitic-automation/actions/runs/42844925356) completed successfully at commit `eb782746c3490b195c5e4bdd6a99e0500b456e0c`, **235 tests passed, 0 failures** on Python 3.12. The scoped suite includes all previous R1b/R2/R2.1/R2.2 checks and the new adaptive-layout and busy-surface cases.
- Downloaded and inspected the actual ephemeral `r2-adaptive-material-synthetic-nonpublishable` image emitted by Actions. The decoded 1080×1350 image shows the EXACT phrase “RIGHTS AND PRACTICE” directly on the illustration behind an engraved ink effect, without an opaque text plate; ten rail dots, `01/10`, masthead, date and full footer remain visible and separated. The source is synthetic Ep136-shaped fixture text, **NOT the actual accepted Ep136 editorial image**.
- The proof's purple geometric head silhouette and line-art apparatus are deliberately fake test inputs and **fail the premium Ep128 artistic-quality gate**. The material phrase is technically legible but the background complexity and geometry remain oversimplified. This is evidence that the new compositing mechanism works, not evidence that the complete pipeline produces an acceptable slide.
- Do not accept publication or archival production output from this fixture; keep PR #5 as a draft until reviewed.

Next: run a carefully bounded genuine visual pilot with a separately authored/prescreened hero background, real original hashed canonical portrait(s), and actual per-item v3.1 Render Integrity evidence. Preserve all legacy R1b/R2 and accepted manual outputs.
