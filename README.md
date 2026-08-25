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

### Milestone 4.2B — Layout stress testing
**Complete — GitHub workflow verified green on 25 August 2026**

The six hardened identity layouts are now tested against three copy-density profiles:

- `short` — deliberately sparse copy;
- `normal` — the existing approved identity-proof inputs;
- `dense` — realistic near-limit copy tuned to each character's constrained regions.

The 4.2B QA suite also supplies one deliberately impossible case per character and requires a clean `LayoutError` instead of a silent collision or unreadable fallback. Local validation before upload: **29 tests passed** and all **18 stress renders** plus the contact sheet generated successfully.

New files:

```text
src/render_identity_stress_pack.py
tests/test_identity_stress.py
.github/workflows/render-layout-stress-test.yml
```

Workflow name:

**Render Milestone 4.2B layout stress test**

Expected output:

- 18 standalone stress PNGs: six characters × short/normal/dense;
- `identity-stress-contact-sheet.png`;
- full pytest QA pass before rendering.

Drive destination:

```text
Google Drive
AI-Geopolitical /
Automation - Temporary Artifacts /
Layout Stress Test
```

## Current development stage

### Milestone 4.3A — NORA layout family
**Complete — GitHub workflow verified green on 25 August 2026**

The first multi-layout character family builds all five NORA families already approved in `config/layout_presets.json`:

- `system_axis`
- `feedback_loop`
- `diagnostic_matrix`
- `episode_opener`
- `episode_closer`

The family is implemented in:

```text
src/render_nora_layout_family.py
```

Reference direction was checked against the previous-episode library in Google Drive, including the established full-header NORA opener and the follow-through/open-file visual language from `Ep029-20July2026`. The new code does not reproduce those slides literally; it converts their composition logic into reusable, measured layouts.

New reusable utility:

```text
src/make_contact_sheet.py
```

This utility is intended for NORA now and later character-family proofs and full-episode QA.

Local 4.3A validation before upload: **35 tests passed** and all five NORA family proofs rendered successfully. The GitHub Actions run subsequently completed green.

Workflow:

```text
.github/workflows/render-nora-layout-family.yml
```

Workflow name:

**Render Milestone 4.3A NORA layout family**

Expected Drive destination:

```text
AI-Geopolitical /
Automation - Temporary Artifacts /
Layout Families /
NORA
```

Expected outputs:

- `nora-system-axis.png`
- `nora-feedback-loop.png`
- `nora-diagnostic-matrix.png`
- `nora-episode-opener.png`
- `nora-episode-closer.png`
- `nora-layout-family-contact-sheet.png`

### Milestone 4.3B — Johan Vosloo layout family
**Implementation prepared — pending GitHub workflow verification**

The second multi-layout character family builds all five Johan families already approved in `config/layout_presets.json`:

- `institutional_spine`
- `containment_chain`
- `oversight_gate`
- `order_corridor`
- `principle_test`

The family is implemented in:

```text
src/render_johan_layout_family.py
```

Visual logic remains Johan-specific: rectilinear order, numbered institutional stages, explicit containment, scrutiny and visible chains of authority. The previous-episode library was checked again during this pass. In particular, the Johan **“WATER MUST REACH THE TAP”** slide in `Ep029-20July2026` reinforces the process-chain / last-mile governance language used in the new containment and corridor variants; the new layouts generalise that editorial logic rather than copying the old slide.

Local 4.3B validation before upload: **42 tests passed** and all five Johan family proofs plus the contact sheet rendered successfully.

Workflow:

```text
.github/workflows/render-johan-layout-family.yml
```

Workflow name:

**Render Milestone 4.3B Johan layout family**

Expected Drive destination:

```text
AI-Geopolitical /
Automation - Temporary Artifacts /
Layout Families /
Johan
```

Expected outputs:

- `johan-institutional-spine.png`
- `johan-containment-chain.png`
- `johan-oversight-gate.png`
- `johan-order-corridor.png`
- `johan-principle-test.png`
- `johan-layout-family-contact-sheet.png`

After GitHub/Drive verification, proceed to **Milestone 4.3C — Diane Sterling layout family**.

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
src/render_identity_stress_pack.py
src/render_nora_layout_family.py
src/render_johan_layout_family.py
src/make_contact_sheet.py
src/render_prototype_slide.py
src/render_milestone_3.py

tests/test_identity_renderer.py
tests/test_identity_stress.py
tests/test_nora_layout_family.py
tests/test_johan_layout_family.py
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
