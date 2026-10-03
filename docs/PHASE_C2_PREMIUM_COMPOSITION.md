# Phase C.2 — premium hero composition proof

This is one internal Ep104 / 2026-10-03 / Slide05 proof awaiting human visual
review. It makes no claim of visual parity, 20-slide readiness or production
publication. ZERO new image generations: no generation provider, router, job,
image API or local inference worker participates in this path.

## Architecture

`src/premium_compositor.py` is a separate local Pillow compositor. It does not
invoke or change Kai's legacy `network_mesh`, `phase_c.compose`,
`contextual_illustrations._asset_plate`, or `apply_context_art`. The generated
editorial illustration supplies the primary scene. Code supplies typography,
canonical identity, exact labels, editorial columns and publication furniture.
Existing paper/ink colours, paper texture, font loader and distressed type helper
are reused. No dependency, renderer, canonical asset or font configuration changes.

`compile_slide()` revalidates the complete current 20-slide Manifest v2 and
BUILD_READY state, then accepts only Ep104 Slide05, single Kai, null pairing and
the six exact infrastructure labels. It maps episode/date, headline, deck, main
phrase, three takeaway ideas and core argument without rewriting or inventing
supporting copy. Canonical portrait and #6540A4 accent come from
`config/characters.json`. Other slides and stale or malformed inputs fail closed.

`accepted_asset()` resolves workspace paths, verifies the previously accepted
Albedo SHA256, successful Ep104/05 metadata and approved visual screen, and
checks the retained internal attribution audit and blocked publishing handoff.
Missing, substituted or unapproved art and path escapes fail before output.
The SHA256 trust anchor is
`af911721d389f3b6a658d18e3e0ba30f93c48bb041be51a7060bf69255f2288b`.

`prepare_hero_art()` uses aspect-preserving cover/crop, grayscale/autocontrast,
modest contrast and opaque INK-to-PAPER tones. Only perimeter pixels feather;
the central alpha is 255. This is a distinct hero treatment, not a raised opacity
setting in the faint background-plate path. Detail stays readable at full strength.

The hero occupies [380,360,1038,890]: 348,740px², about 63% of the usable scene
field and 2.25 times the old 155,100px² plate. Canonical Kai occupies
[42,354,409,852]: 182,766px², about 34% of slide width and 1.52 times the old
card-scale portrait area. His configured source crop receives an additional top
trim to exclude its printed border, aspect-preserving cover, paper release and
edge feathering. Facial proportions are preserved; no synthesis or reference
portrait extraction occurs. Portrait and hero overlap through feathered edges.

The compact masthead contains branding, episode, full Manifest date and 05/20.
Two large distressed condensed lines carry the exact headline; the physical
infrastructure clause is Kai purple. One serif deck bridges into the hero.
Six local scene callouts use only REMOTE USERS, FIBRE, COMPUTE, COOLING, POWER and
LAND. REMOTE USERS connects toward FIBRE; the remaining pointers attach to the
scene. There is no generic five-node diagram and no invented WATER label copied
from the reference. The main phrase is a prominent lower-left purple block.
Three bottom editorial columns render exact 01/02/03 takeaway ideas, followed by
the exact core argument and motto. No rounded dashboard cards or factual rewriting.

Text bounds are measured after wrapping/glyph transformation, checked against
safe margins and checked pairwise for collisions before writing a PNG. Callout
segments are also checked against protected type. Overlong copy fails instead of
clipping or disappearing. Display type may be condensed deterministically;
hero and portrait images are never stretched. Geometry checks prove architecture
and visibility, not beauty. Human review remains the acceptance authority.

## Reference and provenance

The real final Drive `Slide05of20.png`, file
`1jLaocNFP31PQvXmOAZNDSyjzmkbjaQO4`, was metadata-checked and copied using the
existing authorized rclone session from
`Manual - ChatGPT + Instagram/Daily Operations/Daily Slides/`.
The source was read only. Its local ignored reference is
`output/phase-c2/Ep104/slide-05/reference/Slide05of20-reference.png`.
It guided composition inspection; no portrait, type or pixel layer was extracted
from it. The production compositor neither reads nor requires the reference.

Existing accepted Albedo source:
`output/phase-c1/Ep104/slide-5/albedo-sdxl/ai_horde/context-art.png`.
Its byte-identical local input copy is `input/context-art.png` in the C.2 package.
The exact existing C.1 composite was copied into
`control/slide05-phase-c1-control.png`; it was not rerendered.
Reference, input, control, premium PNGs, readiness snapshots and reports are
ignored by the existing `output/*` rule. None is committed.

Creator credit and restrictions remain in both composition reports. The public
credit delivery handoff remains BLOCKED; internal JSON is not public attribution.
No upload or production publication is performed in this proof.

## Local entry point and validation

```text
python -m src.premium_compositor --readiness <current-local-readiness-json>
```

The entry point consumes a current readiness snapshot and accepted local art;
it performs no Drive, provider or network operations. Windows rendering/tests use
the existing ignored DejaVu/FriBiDi adapter; Linux/CI font behaviour is unchanged.
The development reference copy and rclone readiness read are separate operations.

Package: `output/phase-c2/Ep104/slide-05/`.

- `premium/slide05-premium.png` — 1080×1080 PNG for human inspection.
- `report/composition-report.json` — exact content, measured bounds, geometry,
  hashes, source identity, zero provider calls and retained licence handoff.
- `report/composition-report.md` — readable architecture/credit/review record.

Targeted regressions cover exact mapping, opaque hero visibility, larger identity
and headline zones, six label anchors, three columns, footer/counter, output QA,
missing or substituted art, attribution handoff, path confinement, long-copy
failure, ignored references and operation without a reference PNG. A dedicated
test rejects provider/job construction, subprocesses, the old Kai renderers and
the old asset-plate functions while completing local composition.

2026-10-03 validation: Phase C.2 targeted suite **27 passed in 4.14s**;
full Windows QA **710 passed, 1 skipped in 86.62s**. The existing skip is
opt-in local worker discovery; no inference ran. `git diff --check` passes.
All C.2 raster paths are ignored, and the prior C.1 art, control composite,
Flux evidence and both attempt ledgers remain unchanged. The downloaded
reference is development-only and no Drive file was modified.

PHASE C.2 PREMIUM COMPOSITION PROOF READY FOR HUMAN REVIEW

No full visual parity claim. Do not build the other 19 slides or begin Phase D
until the user has reviewed the premium candidate.
