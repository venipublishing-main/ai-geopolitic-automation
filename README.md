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
**Complete — GitHub workflow verified green on 25 August 2026**

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

Local 4.3B validation before upload: **42 tests passed** and all five Johan family proofs plus the contact sheet rendered successfully. The GitHub Actions run subsequently completed green.

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

### Milestone 4.3C — Diane Sterling layout family
**Complete — GitHub workflow verified green on 25 August 2026**

The third multi-layout character family builds all five Diane families already approved in `config/layout_presets.json`:

- `market_grid`
- `transmission_chain`
- `fiscal_flow`
- `portfolio_pipeline`
- `regional_economy`

The family is implemented in:

```text
src/render_diane_layout_family.py
```

Visual logic remains Diane-specific: measurable economic transmission, capital allocation, conversion rates, portfolio readiness, fiscal rails and regional market connections. The layouts deliberately avoid Johan-style institutional hierarchy and Kai-style network-system aesthetics even when they use arrows or connected nodes.

The previous-episode Google Drive library remains the design reference source. 4.3C generalises the established AI Geopolitic economic/dashboard language into reusable code rather than copying a single old slide.

Diane-specific local validation before upload: **7 tests passed**, all five Diane family proofs rendered successfully, and the existing 42-test pre-Diane suite was already verified green in GitHub. The 4.3C GitHub workflow subsequently completed green with the expanded suite.

Workflow:

```text
.github/workflows/render-diane-layout-family.yml
```

Workflow name:

**Render Milestone 4.3C Diane layout family**

Expected Drive destination:

```text
AI-Geopolitical /
Automation - Temporary Artifacts /
Layout Families /
Diane
```

Expected outputs:

- `diane-market-grid.png`
- `diane-transmission-chain.png`
- `diane-fiscal-flow.png`
- `diane-portfolio-pipeline.png`
- `diane-regional-economy.png`
- `diane-layout-family-contact-sheet.png`

### Milestone 4.3D — Kai Patel layout family
**Complete — GitHub workflow verified green on 25 August 2026**

The fourth multi-layout character family builds all five Kai families already approved in `config/layout_presets.json`:

- `network_mesh`
- `feedback_system`
- `monitoring_loop`
- `decentralised_pathway`
- `repair_network`

The family is implemented in:

```text
src/render_kai_layout_family.py
```

Visual logic remains Kai-specific: distributed nodes, live-state monitoring, circular feedback, redundant routing and explicit repair cycles. The family deliberately avoids Johan-style institutional hierarchy, Diane-style financial dashboards and Thabo-style burden ledgers.

The previous-episode library was checked again during this pass. In `Ep029-20July2026`, the Kai **“CLEAR RIVERS NEED OPERATING MEMORY.”** slide uses monitoring, reporting, enforcement, stewardship and maintenance as a continuous operating loop. 4.3D generalises that systems-memory / feedback language into reusable code rather than copying the old slide.

Local validation before upload: **56 tests passed / 0 failed**, including all prior identity, stress, NORA, Johan and Diane tests plus the new Kai family tests. All five Kai family proofs and the contact sheet rendered successfully. The GitHub Actions run subsequently completed green.

Workflow:

```text
.github/workflows/render-kai-layout-family.yml
```

Workflow name:

**Render Milestone 4.3D Kai layout family**

Expected Drive destination:

```text
AI-Geopolitical /
Automation - Temporary Artifacts /
Layout Families /
Kai
```

Expected outputs:

- `kai-network-mesh.png`
- `kai-feedback-system.png`
- `kai-monitoring-loop.png`
- `kai-decentralised-pathway.png`
- `kai-repair-network.png`
- `kai-layout-family-contact-sheet.png`

### Milestone 4.3E — Thabo Mokoena layout family
**Complete — GitHub workflow verified green on 25 August 2026**

The fifth multi-layout character family builds all four Thabo families already approved in `config/layout_presets.json`:

- `burden_ledger`
- `material_chain`
- `structural_gap`
- `continuity_pressure`

The family is implemented in:

```text
src/render_thabo_layout_family.py
```

Visual logic remains Thabo-specific: stacked material burden, broken handoffs, visible class gaps, accumulating pressure and explicit household cost. The family deliberately avoids Diane-style dashboard polish, Kai-style neutral network geometry and NORA-style symmetrical synthesis.

The previous-episode library was checked again during this pass. In `Ep029-20July2026`, the Thabo **“EX-MINEWORKERS ARE THE UNPAID LEDGER.”** slide uses a broken path from injury → claim → review → payment → household relief. 4.3E generalises that material-chain / blocked-handoff logic into reusable code rather than copying the old slide.

Local validation before upload: **63 tests passed / 0 failed**, including all previous identity, stress and character-family tests plus the new Thabo family tests. All four Thabo family proofs and the contact sheet rendered successfully. The GitHub Actions run subsequently completed green.

Workflow:

```text
.github/workflows/render-thabo-layout-family.yml
```

Workflow name:

**Render Milestone 4.3E Thabo layout family**

Expected Drive destination:

```text
AI-Geopolitical /
Automation - Temporary Artifacts /
Layout Families /
Thabo
```

Expected outputs:

- `thabo-burden-ledger.png`
- `thabo-material-chain.png`
- `thabo-structural-gap.png`
- `thabo-continuity-pressure.png`
- `thabo-layout-family-contact-sheet.png`

### Milestone 4.3F — Amari Ndlovu layout family
**Complete — GitHub workflow verified green on 25 August 2026**

The sixth and final character-family expansion builds all five Amari families already approved in `config/layout_presets.json`:

- `regional_memory`
- `dignity_pathway`
- `humanitarian_map`
- `cross_border_bridge`
- `cultural_landscape`

The family is implemented in:

```text
src/render_amari_layout_family.py
```

Visual logic remains Amari-specific: human-centred geography, memory, curved pathways, regional continuity, recognition, dignity and solidarity. The family deliberately avoids Diane-style financial dashboards, Johan-style enforcement hierarchy and Thabo-style burden ledgers.

The previous-episode library was checked again during this pass. In `Ep029-20July2026`, the Amari **“HEALING NEEDS A LIFE AFTER CRISIS.”** slide uses a follow-through pathway from crisis through care, healing, skills, work and dignity. 4.3F generalises that continuity / recognition language into reusable code rather than copying the old slide.

Local validation before upload: **70 tests passed / 0 failed**, including all previous identity, stress and character-family tests plus the new Amari family tests. All five Amari family proofs and the contact sheet rendered successfully. The GitHub Actions run subsequently completed green.

Workflow:

```text
.github/workflows/render-amari-layout-family.yml
```

Workflow name:

**Render Milestone 4.3F Amari layout family**

Expected Drive destination:

```text
AI-Geopolitical /
Automation - Temporary Artifacts /
Layout Families /
Amari
```

Expected outputs:

- `amari-regional-memory.png`
- `amari-dignity-pathway.png`
- `amari-humanitarian-map.png`
- `amari-cross-border-bridge.png`
- `amari-cultural-landscape.png`
- `amari-layout-family-contact-sheet.png`

The full six-character layout-family expansion is now complete.

### Milestone 4.4 — Layout selection / episode routing proof
**Implementation prepared — pending GitHub workflow verification**

This is the first orchestration layer above the individual character renderers. One structured episode manifest now drives slide order, speaker routing and character-specific layout selection.

New routing configuration:

```text
config/layout_routing.json
```

Selection policy:

**deterministic content type + explicit override**

The router deliberately fails closed. It does not silently guess when a content type is unknown, a speaker is invalid, a source input does not match the requested speaker, or an override requests a family that is not approved for that character.

New router:

```text
src/route_episode.py
```

Routing-proof manifest:

```text
inputs/routing-proof-episode.json
```

The 4.4 proof contains **14 ordered slides** and exercises all six presenter renderers plus fourteen distinct layout selections:

1. NORA — episode opener
2. Johan — containment chain
3. Diane — transmission chain
4. Kai — monitoring loop
5. Thabo — material chain
6. Amari — dignity pathway
7. NORA — diagnostic matrix
8. Johan — oversight gate
9. Diane — portfolio pipeline
10. Kai — repair network
11. Thabo — structural gap
12. Amari — humanitarian map
13. NORA — feedback loop
14. NORA — episode closer

The router rewrites slide number / total slide count into resolved per-slide JSON, dispatches each slide to the correct character-family renderer, and produces:

```text
output/routing-proof/slide_01.png ... slide_14.png
output/routing-proof/routing-contact-sheet.png
output/routing-proof/routing-report.json
output/routing-proof/routing-report.md
output/routing-proof/resolved-inputs/slide_01.json ... slide_14.json
```

New tests:

```text
tests/test_episode_router.py
```

The tests validate the routing table against approved families, deterministic content-type selection, explicit overrides, fail-closed behaviour for invalid routes, the proof manifest, all 14 rendered outputs and the generated audit report.

Local validation before upload: **77 tests passed / 0 failed**. The 14-slide routed proof, resolved per-slide JSON, routing reports and contact sheet all generated successfully.

Workflow:

```text
.github/workflows/render-routing-proof.yml
```

Workflow name:

**Render Milestone 4.4 layout routing proof**

Expected Drive destination:

```text
AI-Geopolitical /
Automation - Temporary Artifacts /
Layout Routing Proof
```

After GitHub/Drive verification, proceed to **Milestone 4.5 — production episode schema + layout-routing hardening**, then Milestone 5 batch-render a real approved 20-slide episode.

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
src/render_diane_layout_family.py
src/render_kai_layout_family.py
src/render_thabo_layout_family.py
src/render_amari_layout_family.py
src/route_episode.py
src/make_contact_sheet.py
src/render_prototype_slide.py
src/render_milestone_3.py

tests/test_identity_renderer.py
tests/test_identity_stress.py
tests/test_nora_layout_family.py
tests/test_johan_layout_family.py
tests/test_diane_layout_family.py
tests/test_kai_layout_family.py
tests/test_thabo_layout_family.py
tests/test_amari_layout_family.py
tests/test_episode_router.py
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
