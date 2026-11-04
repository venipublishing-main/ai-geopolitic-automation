# R2: deterministic 1080 × 1440 compositor — proof boundary

**Date:** 4 November 2026 (SAST)  
**Branch:** `feat/r2-v3-3x4-compositor-20261104`  
**Target:** draft PR #2 into the R1b branch, not `main` and not `automation-v2` until review  
**Authority:** [Production Contract v3](https://docs.google.com/document/d/1b3gN0qELVsZtTbe8TAlnhai1EigiuOhexecI7cIyVmY/edit), [Ep128 Visual Quality References](https://docs.google.com/document/d/1vg1rZFnD9kaDRlknIuiTiGAnVThN2r1MeySRF_jgvrY/edit), [Panelist Canon v1](https://docs.google.com/document/d/1WsC-IXnM3TYxh6XSDgR-h-LQU4zLhnx8nzffYeSXGTc/edit) and [Manifest v3](https://docs.google.com/document/d/1s4VrG66Z3V-uidPzqtr6VqlKYGTUY6pr0uyHMmfsagg/edit).

## Read and inspected actual style references

On 4 November 2026, retrieved and **visually inspected actual pixels**, not just the linked Drive docs:
- Ep128 Slide 01, source ID `1u6Fux5vvIJHRzgnnZ_Yrr-TabpZlvQeY`, SHA-256 `86a78988f3b1243b277a2fc737c33a207c3701ea3a9284f06ca918c443513e72`.
- Ep128 Slide 09, source ID `1paH71uL8n5R9r8e-s4LtWtwa0Txrzo62`, SHA-256 `f4baf9191820482e649339cdd73ab5761a453c0b06e5d3c52ac777b6b80ef0ee`.

Both are 1254×1254 original square references and are **STYLE, not the target crop/size**. The inspected grammar includes warm neutral paper, dense near-black engraving, type-first hierarchy, actual geographic/strategic apparatus, integrated portraits with analytical accent, masthead, baseline-aligned dot rail and two-line fixed footer. Neither historical image is stretched into a 3:4 slide. Other Ep128 reference IDs remain eligible for later hydration only after independent visual inspection/hash registration.

## Current new code

- `src/v3_canon_assets.py` validates exact SHA-256 raw PNG bytes for all six currently approved Drive portrait IDs. Only canonical PNGs pass, even if a same-named replacement is also an RGBA file. Exact style reference raw bytes must also hash match.
- `src/v3_compositor.py` composes **one** slide from a validated ten-slide Manifest v2, one bespoke pre-existing background-only hero PNG, exact 1/2 assigned portrait PNGs, an explicit per-slide visual/aperture plan, and an actual approved Ep128 PNG reference. It does not load an image service, render a substitute face, transfer files, or publish.
- `R2SlidePlan` binds its specific visual reasoning family, unique bespoke hero visual ID, exact manifest slide, precise portrait safe-zone boxes, approved Ep128 original ID, and explicit background-human-free review attestation. The attestation is not a computer-vision substitute for human inspection.
- A separate in-memory compositor normalizes only the **hero** image to its designated region using aspect-preserving crop; it never stretches an accepted reference or canonical portrait.
- The final output is one **exact 1080×1440, RGB PNG**, read back after encoding; canonical portraits are used in alpha-preserving proportionate scaling, without tint, recolour, facial redrawing, or background matte.
- Masthead, date, title, subheadline, main phrase, essential labels, ten aligned markers (one filled), two-digit XX/10 and the exact footer are deterministic; text never gets silently ellipsized.
- `R2Composite.qc` returns count, size, SHA-256 evidence and explicitly `visual_review=REQUIRED`, `publication_authorised=false`, `image_generation_performed=false`.

## Scope and nonclaims

This is an **R2 compositor and test harness**, not the scene generator and not an approved premium magazine illustration. It cannot invent unique political apparatus or inspect whether someone maliciously inserted a fake person into the supplied background. It only accepts a reviewed, separately prepared, argument-specific background-only artwork image and an explicit portrait aperture plan. The model may still visually fail Ep128 in a completed proof; style approval is human-led. Text content is copied from a validated Manifest but full artistic/factual QA requires an independent review.

R2 does not modify any historical D.2/D.2R/D.2V files. The user's original `E:\Dev\ai-geopolitic-automation` with uncommitted D2V files remains untouched. The accepted Ep136 carousel/reel archive is never overwritten.

## R2 pure call example

```python
from src.v3_compositor import R2SlidePlan, PortraitPlacement, compose_r2_slide

plan = R2SlidePlan(
    slide_number=1,
    visual_id="per-slide-background-v1",
    hero_family=manifest["slides"][0]["preferred_visual_reasoning_family"],
    placements=(PortraitPlacement(slug="nora", box=(70, 475, 605, 1080)),),
    ep128_reference_id="1u6Fux5vvIJHRzgnnZ_Yrr-TabpZlvQeY",
    background_human_free_reviewed=True, # only after real human inspection
)
draft = compose_r2_slide(
    manifest, plan,
    hero_png=hero_background_only_png,
    portrait_pngs={"nora": original_drive_nora_png_bytes},
    ep128_reference_png=original_ep128_slide_01_png_bytes,
)
# No archiving or publishing API exists in this module.
# The caller MAY save draft.png_bytes to an isolated staging path for review.
```

Do not use mocked or synthetic portrait data in production. The test suite patches its own mock SHA-256 allowlist for fake portraits; the actual compositor module uses the pinned six originals and rejects those fake bytes.

## Tests / acceptance criteria

```sh
python -m pip install pytest==8.4.1 Pillow==11.3.0
python -m pytest -q tests/test_daily_readiness.py tests/test_v3_readiness.py tests/test_v3_drive_proof.py tests/test_v3_compositor.py
```

Coverage includes single/dual casting, source/hash mismatch, authenticated-input compatibility, exact dimensions, all ten-dot geometry, deterministic output, identity alpha, hero proportions and type-overflow fail-closed behavior.

**R2 code QA PASS requires a completed green CI run on the R2 head commit.** 
**R2 visual PASS additionally requires a generated-free composited proof visually inspected against actual Ep128.** 
**R2 acceptance for future daily production requires a genuinely bespoke hero background per slide and user-approved visual review.**

No preview image, published carousel, Drive archive mutation or user visual approval is implied merely by a passing unit test. 
