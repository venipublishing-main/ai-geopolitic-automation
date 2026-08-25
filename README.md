# AI Geopolitic Automation

Automated visual-production pipeline for the **AI Geopolitic** editorial project by **Veni Publishing**.

## Project goal

Build a low-cost, ideally $0/month, production pipeline:

**Research → 20-slide episode → Instagram carousel → Reel/video → Story → publishing → logging/analytics**

For now, approved R&D/content can still be supplied manually. Visual fidelity and identity consistency take priority over premature full automation.

## Locked repository structure

```text
.github/
  workflows/
assets/
  characters/
config/
docs/
inputs/
output/
src/
tests/
```

Do not introduce duplicate folder structures or rename established files casually.

## Locked character assets

Canonical presenter portraits live in:

```text
assets/characters/
```

Files:

```text
amari_ndlovu.png
diane_sterling.png
johan_vosloo.png
kai_patel.png
nora.png
thabo_mokoena.png
```

These are fixed identity anchors and must not be regenerated during normal production.

Character metadata and calibrated crop boxes live in:

```text
config/characters.json
```

## Editorial standard

- 1080 × 1080 standalone PNGs
- cream/off-white textured paper
- black engraved/editorial visual language
- distressed condensed uppercase headlines
- editorial serif body copy
- one ideological accent colour per speaker
- reusable maps, chains, systems diagrams, market grids, networks and regional structures
- critical safe margin of roughly 76 px / 7%
- slides 2–19 do not use the full date/header bar

Locked footer:

**The event is factual. The interpretation ideological.**

## Milestone status

### Milestone 1 — References / architecture
**Complete**

Established repository structure, locked portraits, brand/layout configuration and production specification.

### Milestone 2 — Automated render proof
**Complete**

GitHub Actions successfully rendered a code-generated 1080 × 1080 AI Geopolitic prototype.

### Milestone 3 — Data-driven rendering
**Complete**

Structured inputs successfully switched speaker, portrait, accent colour and content.

### Milestone 3.1 — Layout refinement
**Complete**

Added dynamic text fitting, diagram modes, stronger footer treatment and basic layout QA.

### Milestone 3.2 — Portrait calibration
**Complete**

All six characters have calibrated portrait crops in `config/characters.json`.

### Milestone 4.1 — Character layout identity proof
**Complete**

Each panelist received a distinct visual grammar:

- NORA — `system_axis`
- Johan Vosloo — `institutional_spine`
- Diane Sterling — `market_grid`
- Kai Patel — `network_mesh`
- Thabo Mokoena — `burden_ledger`
- Amari Ndlovu — `regional_memory`

Configuration:

```text
config/layout_presets.json
```

Renderer:

```text
src/render_identity_slide.py
```

### Milestone 4.2A — Hardened identity layouts
**Complete — workflow verified green on 25 August 2026**

The six base identity layouts were hardened before expanding the layout library.

Implemented:

- measured headline/deck/quote regions
- collision and overflow protection
- readable minimum text sizes
- guarded fact panels
- safe portrait/content separation
- corrected Thabo portrait/facts collision
- improved Johan and Kai upper-stack spacing
- regression tests for all six presenters
- deliberate overflow tests using `LayoutError`
- GitHub Actions runs `pytest -q` before rendering/uploading

Current workflow:

```text
.github/workflows/render-layout-identity-proof.yml
```

Workflow name:

**Render Milestone 4.2A hardened identity proof**

Output destination:

```text
Google Drive
AI-Geopolitical /
Automation - Temporary Artifacts /
Layout Identity Proof
```

## Current development stage

### Next: Milestone 4.2B — Stress testing

Before creating more layout families, stress-test all six base layouts with short, normal and deliberately difficult copy.

Goals:

- no silent text collisions
- no unreadably small fallback text
- no portrait overlap
- no footer/takeaway collisions
- clean failure through `LayoutError` when content cannot fit
- retain character-specific visual identity under variable copy length

### Then: Milestone 4.3 — 3–5 layout families per character

The previous-episode library in Google Drive is the visual reference source for expanding each character into approximately 3–5 reusable compositions.

Do not create 20–30 unrelated giant templates. Build variants from reusable editorial primitives while preserving each character's visual grammar.

## Main production files

```text
docs/PRODUCTION_SPEC.md
config/brand.json
config/characters.json
config/layouts.json
config/layout_presets.json

src/editorial_primitives.py
src/render_identity_slide.py
src/render_prototype_slide.py
src/render_milestone_3.py

tests/test_identity_renderer.py
tests/test_prototype.py
```

## Development rule: README must move with the code

**Every milestone or meaningful GitHub update must include a `README.md` update in the same upload/commit package.**

At minimum, update:

1. current milestone status;
2. what changed;
3. workflow name/path if relevant;
4. expected outputs/destination;
5. next development step.

The repository README is the canonical quick handover/status record.

## Long-term roadmap

After the layout engine is reliable:

1. expand reusable character layout families;
2. build layout selection;
3. render a real approved 20-slide episode;
4. export 20 PNGs + contact sheet + QA report;
5. generate caption + exactly five hashtags;
6. generate Reel/video assets from the strongest approximately six slides;
7. add optional local RTX 3080 enhancement jobs;
8. publish through official Meta/Instagram APIs;
9. add retries, logging and analytics.

Quality review remains mandatory until the automated output consistently matches the established AI Geopolitic editorial standard.
