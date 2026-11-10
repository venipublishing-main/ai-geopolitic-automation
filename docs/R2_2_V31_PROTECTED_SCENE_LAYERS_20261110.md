# R2.2 first increment — portrait-protected scene layers

**Date:** 10 November 2026 (SAST)
**Home:** AI Geopolitic automation repository, *not* the manual production directory.
**Branch:** `feat/r2-2-v31-scene-layering-20261110`, stacked after draft R2.1 PR #3.

## Problem observed in the R2.1 4:5 synthetic QA proof

The fixed template met raster/counter/furniture geometry but still looked generic: isolated article text, an overlarge synthetic portrait silhouette and simple diagram linework placed behind it. This is not Ep128-equivalent artwork and received **no visual approval**.

The production ledger v3.1 requires:
- Ep128 as primary style authority, with Ep142 limited to higher-dimensional environmental craft and materially integrated typography;
- organic integration of original transparent source portrait(s) without recolour, redraw, fake substitute or opaque card;
- purposeful analytical foreground objects that can share scene depth with the subject without compromising their source appearance.

## Implemented in this increment

`src/v3_scene_layers.py` accepts an optional **authored transparent analytical foreground PNG** that exactly fits the active scene hero aperture, and rejects opaque, absent, malformed, excessively large or stretched assets.

The R2 compositor now has the *optional* arguments `foreground_layer_png` and `foreground_reviewed`. If artwork is supplied, explicit pre-composite scene review is mandatory.

Foreground compositing is pixel-protected: it derives a silhouette occupancy mask from the **actual alpha-resampled source PNG**, removes every foreground-ink pixel where the original portrait is nontransparent, then composites the remaining analytical engraving **around and behind** the portrait. This preserves all visible portrait pixels and cutout edges. The receipt records the foreground asset SHA-256, review state and count of protected pixels. This is not a new Manifest v2 field and does not enable publication.

Regression cases compare composited output with/without an overlay at selected portrait and background pixels, reject missing foreground review and mismatched hero aperture dimensions. All previous R1b/R2/R2.1 pure regressions remain in the suite.

## Limits / next R2.2 increment

This is a layering primitive, not a scene generator or final flexible layout engine. We still need a compositional *arrangement contract* for multiple argument-responsive geometries, typography planned around physical illustration surfaces and deliberate foreground/background layering. A human must inspect each proposed real scene/portrait aperture and complete the independent v3.1 Render Integrity Gate.

One synthetic proof with flat placeholder portrait geometry does **not** establish premium Ep128 quality. Do not publish, archive or equate it with an accepted slide.

No manual ledger change, accepted episode archive mutation, image provider spend or source portrait rewrite is performed.

## Observed verification — 10 November 2026

- [GitHub Actions run #42841499717](https://github.com/venipublishing-main/ai-geopolitic-automation/actions/runs/42841499717): **224 passed, zero failed**, scoped R1b/R2/R2.1/R2.2 suite on Python 3.12.
- Retrieved the GitHub artifact `r2-layered-scene-synthetic-nonpublishable`, decoded and visually inspected the actual 1080×1350 PNG. The authored red horizontal demonstration mark is visibly present across the background but is clipped at the synthetic portrait silhouette. The portrait colour/shape is not overpainted.
- This fixture has no realistic panelist and no argument-specific premium hero; its aesthetic is **NOT accepted**. It is engineering-only proof of layering, shape and identity-protection behaviour.
- R2.2 still needs layout geometry variation, material-integrated typesetting and a genuine source-portrait/bespoke-art human-reviewed proof before premium visual acceptance.

The automation branch and PR #4 remain drafts; no manual directory files, accepted episode assets, publication or providers were touched.
