# AI Geopolitic Automation

Automated visual-production pipeline for the **AI Geopolitic** editorial project by **Veni Publishing**.

## Current status — Phase D.2 three-slide real benchmark

D.2 exercises the generalized SceneContract → spatial SDXL prompt → AI Horde →
hero QA → premium renderer path for exactly Nora 14, Diane Sterling 12 and Amari
Ndlovu 16, in that order. The durable ledger caps the run at three submissions,
one attempt per target; ambiguous/technical/engineering failures stop, and visual
failures preserve rejected art without composition or retry. AlbedoBase XL 3.1
requires fresh exact-model, health, ZERO_COST and conditional-permission gates.
References from Daily Slides are development comparisons only, never generator
inputs or renderer dependencies. No new dependency or CI workflow is introduced.

The historical Ep104 snapshot is dated **2026-10-03**:
`CURRENT_READINESS = NOT_ASSERTED`,
`SOURCE = ACCEPTED_EP104_HISTORICAL_SNAPSHOT`. Public publication remains BLOCKED;
credit obligations stay in receipts, outside the raster. Human review is authoritative.
Ignored outputs and the comparison report live under `output/phase-d2/Ep104/`.
The run stopped after **two acknowledged submissions**. Nora completed technically
but failed visual guardrails (generated lettering and an incompatible pyramid);
composition was withheld. Diane status polling became ambiguous, triggering
`D2_AMBIGUOUS_STATUS_STOP`; its remote outcome is unknown. Amari was never submitted.
There are no real generalized renders, retries or further provider calls. The
three-slide benchmark is incomplete; neither human-review readiness nor D.2 visual
acceptance is claimed.
D.2 tests: **36 passed**. D.1: **55**; C.4: **34**; C.3: **34**; C.2: **27**;
provider/licence: **392**. Full Windows QA: **869 passed, 1 skipped**.
The skip remains opt-in local-worker discovery. Evidence bindings verify two
distinct ACKs/two recorded submission requests; all 31 protected historical,
compiler, portrait and font files remain byte-identical. `git diff --check` passes.
See [D.2 procedure and architecture](docs/PHASE_D2_THREE_SLIDE_BENCHMARK.md).
The next step is operator review of the stopped evidence and a separately authorised
decision about the ambiguous remote job. No further inference or carousel follows.

## Phase D.1 single-panelist generalisation

Deterministic premium SceneContracts now separate panelist tendencies from
argument geometry for Nora, Diane, Johan, Kai, Thabo and Amari. The illustration
prompt, mechanical hero QA and internal premium renderer share normalized zones;
all exact copy and canonical portraits remain compositor-owned. Unknown families,
invalid inputs and overflow block, with no legacy renderer fallback.

D.1 performs **zero generations/provider submissions**. The explicitly historical
Ep104 snapshot compiles **13 singles** and blocks **7 duals** with
`DUAL_PANELIST_NOT_SUPPORTED_D1`; its inspection exit code is 1. Historical replay
does not claim current `BUILD_READY`. Publication and human visual QA remain open.
Six synthetic fixture cases prove architecture, not visual parity or carousel
acceptance. C.3/C.4 remain accepted historical evidence; Kai Slide 05 tuning is closed.
D.1 targeted: **55 passed**. Full Windows QA: **833 passed, 1 skipped**.
See [D.1 architecture and validation](docs/PHASE_D1_SINGLE_PANELIST_GENERALISATION.md).

```sh
python -m src.premium_scene_compiler --source drive --dry-run
python -m src.premium_scene_compiler --accepted-snapshot output/phase-c4/Ep104/slide-05/input/readiness.json --dry-run
```

The sections below retain earlier milestone history.

## Phase C.1 — Free cloud provider implementation

**Narrow Kai Slide 05 bridge implemented; real vertical slice blocked by image content.**
Full Windows QA: **661 passed, 1 skipped** (18 Kai bridge + 116 cloud + 64 local Phase C +
172 Phase B + 189 Phase A/A.1 + 102 existing; the skip is opt-in worker discovery).
Cloudflare Workers AI and AI Horde now implement the existing provider contract
through isolated stdlib HTTPS transports. The existing router/zero-cost policy
and dormant WanGP/ComfyUI work are retained. No dependencies, renderer behaviour,
canonical assets, readiness rules or CI workflows change.

`python -m src.phase_c_cloud` defaults to discovery/dry run; only `--execute`
permits one contextual image after current readiness, exact model licence and
free-cost gates pass. Configurable priority starts Cloudflare → Horde → BLOCK.
Cloudflare's exact `@cf/black-forest-labs/flux-1-schnell` has a reviewed Apache-2.0
entry; a token alone cannot prove free cost. Workers Free and free-allocation-only
declarations are required. Horde supports personal/official anonymous keys.
The exact compact Schnell checkpoint is now approved from the official v2 Horde
reference's explicit Apache-2.0/commercial permission and its upstream evidence.
Credentials are environment-only; see [.env.example](.env.example).

The existing one-slide bridge, artifact QA, ledger, staging and asset compositor
are reused for one compatible **current** Manifest slide; cloud jobs never assume
Ep103/12. Code retains all portrait/copy/layout ownership. A durable two-attempt
maximum permits only one diagnosed terminal technical retry; unresolved submission
never permits fallback. Reports/artifacts stay in ignored `output/phase-c1/`.

**2026-10-03 Slide 05 benchmark:** live readiness and Horde-first dry run pass
`BUILD_READY`, Ep104, 20 validated slides, no blockers and predicted image count 1.
`KAI_NETWORK_MESH` supports only single Kai on interior Slide 05, with null
pairing/central relationship; the original `THABO_MATERIAL_CHAIN` profile remains.
The provisional mapping uses exact Manifest copy and the unchanged approved Kai
renderer, retaining canonical portrait, purple accent, typography, counter and
footer. Context art stays in the lower-right background beneath the existing
network diagram. This does not implement a general 20-slide compiler.
Real job `af14c755-88db-4dbd-a4ea-6473282d7e92` completed on the single authorized
attempt (seed `3681541205`, worker `AstralWeaver`). Its nonuniform 1024-square PNG
passes mechanical QA. Visual inspection found generated lettering and a
copyright/signature-like mark, plus a large literal fluffy cloud despite the
Manifest guardrail. The asset was withheld before composition: no final candidate,
upload, retry or new commit/push. This content failure does not authorize a
technical retry. Human/operator review remains required; visual parity and the
real vertical slice are not accepted.
See [exact Horde permission review](docs/HORDE_MODEL_PERMISSION.md).
Pollinations/Puter
remain future Phase C.2 candidates. See [free cloud provider details](docs/PHASE_C_FREE_CLOUD.md).

## Phase C — Controlled local one-slide integration

**Transport/bridge implementation; real-generation acceptance remains open.**
Full Windows QA: **527 passed, 1 skipped** (463 existing + 64 new offline tests;
the real-worker discovery smoke check is explicitly opt-in).
WanGP now has a stdlib localhost MCP v2 adapter; ComfyUI has an official HTTP jobs
adapter and a fixed core-node-only workflow. Both remain unavailable by default.
External operator-reviewed profiles must bind runtime discovery, installed model
files, supported dimensions, hardware requirements and authoritative licence evidence.
No local production model permissions are shipped. The Phase B contract/router, renderers,
readiness, canonical assets, requirements and GitHub workflows remain unchanged.

`python -m src.phase_c` defaults to preflight/dry run, reads current live Drive
readiness without a date override and writes its report to
`output/phase-c/ep103-slide12/`. Only explicit `--execute` permits inference, after
the current validated Ep103 Slide 12, suitable GPU and reviewed worker gates pass.
There is no carousel loop. The provisional bridge uses the existing Thabo
`material_chain` renderer and exact Manifest copy; it requires five explicit
stage labels and preserves the canonical portrait, accent, footer and 12/20.
Ignored `assets/_phase_c_runtime/` staging is cleaned after composition.

**2026-10-03 preflight:** Windows detects Intel HD Graphics 530; suitable NVIDIA
hardware/CUDA/VRAM could not be verified. No WanGP/ComfyUI installation, model
download or generation was performed. Current Drive readiness is blocked by
`AUTOMATION_MANIFEST_MISSING`. Zero real generations; no final slide candidates
or Drive uploads. A blocked report records the measurements and open gates.

Offline transport, permission, lifecycle, bridge, artifact, compositor and budget
tests accompany the integration. Real worker discovery is explicitly opt-in;
normal pytest never launches a model. See [Phase C benchmark](docs/PHASE_C_BENCHMARK.md)
for commands, external profile requirements and limitations. These local adapters
are now dormant while C.1 provides the active free-cloud acceptance path.

## Phase B — Generation / worker foundation

**Validated — 463 tests passed: 172 Phase B + 189 Phase A/A.1 + 102 existing.**
The full suite passed through the existing Windows QA adapter without skips;
both targeted suites also passed with ordinary pytest in the QA environment.

Provider-neutral job contracts, explicit asynchronous lifecycle, deterministic
single-provider routing and selection audits now live in `src/providers/`.
`IMAGE`, `VIDEO` and `AUDIO` vocabulary is defined; the deterministic IMAGE mock
exercises queue/run/success/failure/cancellation with structured data and no images.
The production policy permits only proven `ZERO_COST`, enforces commercial-model
permission and separates monetary cost from finite compute resources. Paid and
unknown-cost providers fail closed; mocks require an explicit development policy.

WanGP and ComfyUI have isolated, inactive adapter seams behind the same contract.
They remain unavailable even with configuration until transport/capabilities are
verified. No workers are installed or launched, no models are downloaded, no image
APIs are called and no quota is used. Existing renderers, portraits, Manifest v2,
readiness, dependencies and GitHub workflows are unchanged.

**Phase A end-to-end accepted:** real Google Drive/rclone returned `BUILD_READY`,
Ep103, 2026-10-02 SAST, 20 validated slides, exit 0. The historical Phase A/A.1
sections below record their earlier local validation and pre-handoff state.

Phase B adds offline contract/routing tests and uses the existing Windows QA
adapter for full renderer regression validation. No workflow or production output
destination is added. The next phase is a controlled **one-slide** WanGP/ComfyUI
visual benchmark and verified adapter integration, using Milestone 5.2's `asset`
seam. Phase B does not begin that benchmark or connect to production rendering.

See [Generation providers](docs/GENERATION_PROVIDERS.md) for contracts, lifecycle,
policy, mock usage, adapter boundaries and explicitly deferred work.

## Phase A.1 — Current Drive metadata compatibility

**Locally validated — 291 tests passed (102 existing + 119 Phase A + 70 Phase A.1).**
The full suite uses the documented Windows QA adapter; the 189 ingestion/readiness
tests also pass with ordinary pytest. No new dependencies or renderer changes.

Phase A.1 aligns deterministic ingestion with the supplied current Ep102 control
metadata. It preserves every Phase A alias and adds `PRODUCTION DATE (SAST)`,
`EPISODE`, and `RECOMMENDED EPISODE / WORKING TITLE`. Human dates accept ISO or
full English dates such as `Thursday, 1 October 2026`, with weekday validation
independent of Windows locale. Manifest dates remain ISO `YYYY-MM-DD`.

`SOURCE DAILY R&D EPISODE: Ep102 — TITLE` is parsed into an ID and optional title.
When Slide Design lacks a separate title field, that source title supplies it;
the source title is always checked against Daily R&D. Explicit full R&D and
manual-blueprint completion statuses are supported; arbitrary READY text is not.
Dual-slide `central_relationship` now requires `converge`, `oppose`,
`partially_overlap`, or `synthesize`; single slides require null.

The local Ep102 pre-handoff fixture must return BLOCKED solely because
`AUTOMATION_MANIFEST_MISSING`:

```powershell
python -m src.daily_readiness --source local --rnd-file tests/fixtures/daily_readiness/daily_rnd_ep102.txt --slide-design-file tests/fixtures/daily_readiness/slide_design_ep102.txt --date 2026-10-01 --json
```

The upstream ChatGPT Slide Design automation must add the exact automation JSON
markers and a complete ISO-dated v2 manifest while preserving the human blueprint.
This repository does not modify the live Drive documents. The next real Drive
readiness test remains blocked until that handoff exists. Existing v1 rendering,
Milestone 5.2, assets, configuration and GitHub workflows remain intact.

See [Drive ingestion](docs/DRIVE_INGESTION.md) and
[Manifest v2](docs/EPISODE_SCHEMA_V2.md) for the corrected contract.

## Phase A — Daily ingestion and readiness foundation

**Implemented and locally validated — 221 tests passed (102 existing + 119 new).**
Windows rendering QA used original DejaVu fonts and Pillow's FriBiDi shaping
support through a local test adapter; production renderer code is unchanged.
Live Drive integration still requires configuration and actual-export verification.

Phase A adds deterministic Daily R&D + Daily Slide Design ingestion, freshness
checks in `Africa/Johannesburg`, and a strict **Episode Manifest v2** automation
handoff. It returns **BUILD READY** or **BUILD BLOCKED**, with structured blocker
codes and paths. Today's R&D with yesterday's Slide Design explicitly returns
`WAITING_FOR_CURRENT_SLIDE_DESIGN`; yesterday's design is never reused.

The existing Milestone 4.5 **v1 production renderer**, canonical character config,
deterministic layout families, fail-closed routing, Milestone 5.2 `context_art`
hook and GitHub Actions proofs remain intact. V2 is validated independently and
is not forced into a v1 `layout_family`. Phase A stops at readiness; it does not
generate images, render v2 slides, redesign composition, add a web UI or publish.

The human-readable Slide Design remains. Upstream ChatGPT automation will
eventually also populate these exact standalone markers with a valid v2 JSON
object between them:

```text
=== BEGIN AUTOMATION MANIFEST JSON ===
{ valid JSON conforming to Episode Manifest v2 }
=== END AUTOMATION MANIFEST JSON ===
```

Missing, duplicated, malformed, unsupported or inconsistent JSON fails closed.
No LLM or heuristic converts human slide prose into a manifest. Both documents
also require the exact `=== BEGIN DAILY PAYLOAD ===` / `=== END DAILY PAYLOAD ===`
metadata envelope.

Developer examples (from the repository root):

```powershell
python -m src.daily_readiness --source fixtures --date 2026-10-01
python -m src.daily_readiness --source fixtures --fixture stale --date 2026-10-01
python -m src.daily_readiness --source local --rnd-file daily-rnd.txt --slide-design-file daily-design.txt --json
python -m src.daily_readiness --source drive --json
python -m pytest -q
```

The fixture commands demonstrate READY and BLOCKED respectively. `--json` returns
the structured result; exit codes are 0 for READY and 1 for BLOCKED. Live Drive
uses the existing rclone remote architecture and requires local configuration;
no credentials or new Python dependencies are added.

New modules: `src/production_inputs.py`, `src/control_documents.py`,
`src/episode_manifest_v2.py`, and `src/daily_readiness.py`. Tests and compact control
document fixtures live in `tests/test_daily_readiness.py` and
`tests/fixtures/daily_readiness/`.

See [Episode Manifest v2](docs/EPISODE_SCHEMA_V2.md) for the strict field contract
and [Drive ingestion](docs/DRIVE_INGESTION.md) for metadata labels, statuses,
readiness philosophy, environment variables, live setup and assumptions. The next
integration step is to align actual control-document exports and have upstream
ChatGPT populate the JSON handoff; Phase A ends here for review.

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
**Complete — GitHub workflow verified green on 25 August 2026**

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

GitHub/Drive verification completed green. Milestone 4.5 then promoted the routing proof into a strict daily-use 20-slide production schema.

### Milestone 4.5 — Production episode schema + routing hardening
**Complete — GitHub workflow verified green on 25 August 2026**

Milestone 4.5 introduces the first daily-use episode manifest. Production slides now contain approved editorial copy inline rather than pointing at character-family test fixtures through `source_input`.

New renderer/compiler:

```text
src/render_production_episode.py
```

New working production proof and copy template:

```text
inputs/production-schema-proof.json
inputs/production-episode-template.json
```

New schema documentation:

```text
docs/EPISODE_SCHEMA.md
```

The v1 production contract requires exactly **20 slides**. Array order is canonical; `slide_number`, `total_slides` and `layout_family` are compiler-owned and must not appear in daily slide content. Slide 1 must be NORA `episode_opener`, slide 20 must be NORA `episode_closer`, and slides 2–19 may not use either full-header family.

Each slide supplies common copy (`headline`, `deck`, `quote`, `facts`, `takeaway`) plus optional family-specific structured data under a `visual` object. The deterministic 4.4 router still selects the approved character layout using `speaker + content_type`, with `layout_override` retained for deliberate editorial intervention.

Hardening added in 4.5:

- exact 20-slide production validation;
- safe lowercase `episode_id`;
- blank-copy and fact-list validation;
- compiler-owned field rejection;
- reserved `visual` field collision rejection;
- NORA opener/closer position enforcement;
- resolved per-slide renderer JSON;
- `resolved-episode.json`;
- production routing/QA reports in JSON and Markdown;
- 20-slide contact sheet;
- fail-closed renderer dispatch.

Local reconstructed-suite validation before upload: the existing package tests plus the new 4.5 tests pass cleanly; the GitHub workflow runs the repository's full `pytest -q` suite before rendering. The 4.5 proof itself renders **20 standalone 1080×1080 PNGs**.

Workflow:

```text
.github/workflows/render-production-schema-proof.yml
```

Workflow name:

**Render Milestone 4.5 production schema proof**

Expected Drive destination:

```text
AI-Geopolitical /
Automation - Temporary Artifacts /
Production Schema Proof
```

The GitHub/Drive verification completed green. The repository had **84 tests** at the end of Milestone 4.5.

### Milestone 5.0 — First approved 20-slide automated episode benchmark
**Complete — GitHub workflow verified green on 25 August 2026**

The first production-scale benchmark uses the archived, approved **Ep029 — 20 July 2026 — “THE FOLLOW-THROUGH GAP”** episode rather than synthetic engineering copy. This gives the automation a fixed editorial target whose original 20-slide finished carousel already exists in Google Drive under:

```text
AI-Geopolitical /
History - Episode List /
Ep029-20July2026
```

The benchmark production manifest is:

```text
inputs/episode-029-20july2026.json
inputs/episode-029-context-art-5.2.json
```

It preserves the original episode's 20-slide presenter sequence and editorial themes while expressing them through the v1 production schema. Layout selection remains deterministic: the manifest supplies `speaker + content_type`; `config/layout_routing.json` selects the approved family; no manual `layout_override` is used in the benchmark.

The benchmark exercises all six presenters and routes across **14 distinct character-specific layout families**, including NORA opener/closer, Johan governance/oversight/order layouts, Diane market/transmission layouts, Kai monitoring/network/repair layouts, Thabo material/burden layouts, and Amari dignity/humanitarian layouts.

New regression coverage:

```text
tests/test_milestone_5_ep029.py
```

The new tests protect:

- exactly 20 production slides;
- the archived presenter sequence;
- expected deterministic layout selection;
- zero manual layout overrides;
- 20 standalone 1080×1080 PNG outputs plus resolved inputs, reports and contact sheet.

The 4.5 baseline contains **84 GitHub-green tests**. Milestone 5.0 adds **5 benchmark tests**, so the repository should collect **89 tests** after upload. The Ep029 production manifest has already rendered locally as a complete 20-slide batch.

Workflow:

```text
.github/workflows/render-milestone-5-ep029.yml
```

Workflow name:

**Render Milestone 5.0 Ep029 benchmark episode**

Expected Drive destination:

```text
AI-Geopolitical /
Automation - Temporary Artifacts /
Production Episodes /
Ep029 Benchmark
```

Milestone 5.0 is a **benchmark, not a claim of final visual parity**. The automated output should be reviewed against the original Ep029 carousel for typography, density, illustration richness, visual storytelling and mobile readability. Any repeated shortcomings should be fixed in reusable primitives/layouts rather than hand-patching one historical episode.

The GitHub/Drive benchmark completed green. The side-by-side comparison confirmed that orchestration, identity, routing and readable information architecture are working; the remaining gap is primarily visual fidelity, especially contextual illustration richness, portrait integration and background editorial atmosphere.

### Milestone 5.1 — Benchmark QA + reusable fidelity corrections
**Complete — GitHub workflow verified green on 25 August 2026**

Milestone 5.1 improves shared primitives rather than creating more layouts. The goal is to make the entire existing library feel less template-like before a current daily episode is attempted.

Changes:

- richer deterministic paper grain with faint print-fibre scratches;
- shared character-specific editorial atmosphere behind foreground content;
- NORA system/globe contours;
- Johan institutional facade/authority geometry;
- Diane market bars/transmission traces;
- Kai network/circuit traces;
- Thabo ledger/burden hatching;
- Amari regional contours/route lines;
- subtle printmaker plate and deeper feathering around the locked portraits;
- numbered evidence-ledger treatment in shared fact panels;
- no changes to locked portrait files, routing rules, episode schema or approved layout families.

Benchmark notes are documented in:

```text
docs/FIDELITY_BENCHMARK.md
```

New regression coverage:

```text
tests/test_fidelity_primitives.py
```

The 5.0 repository baseline contains **89 GitHub-green tests**. Milestone 5.1 adds **3 primitive/fidelity tests**, so the repository should collect **92 tests** after upload. The updated Ep029 benchmark has already rendered locally as a complete 20-slide batch.

Workflow:

```text
.github/workflows/render-milestone-5-1-fidelity.yml
```

Workflow name:

**Render Milestone 5.1 fidelity benchmark**

Expected Drive destination:

```text
AI-Geopolitical /
Automation - Temporary Artifacts /
Production Episodes /
Ep029 Fidelity 5.1
```

Milestone 5.1 is still not final visual parity. The GitHub/Drive run completed green, confirming that the shared fidelity changes did not break the renderer. The biggest remaining gap remains bespoke contextual illustration.

### Milestone 5.2 — Contextual illustration layer proof
**Implementation prepared — pending GitHub workflow verification**

Milestone 5.2 adds a reusable contextual-art compositor rather than more layout families. The aim is to separate rich illustration from exact typography and locked presenter identity.

New compositor:

```text
src/contextual_illustrations.py
```

The illustration contract supports two sources:

- `procedural` — deterministic zero-cost Pillow line art;
- `asset` — a future repository PNG/WebP under `assets/`, intended for local RTX/NVIDIA/API-generated or manually approved context art.

The production schema now accepts `visual.context_art` with a protected `box`, `layer`, `opacity`, optional `paper_wash`, and `exclusions` that prevent foreground artwork from crossing exact labels or copy. Invalid kinds, unsafe boxes, invalid layers and asset paths outside `assets/` fail closed before production.

Milestone 5.2 uses a controlled Ep029 proof manifest:

```text
inputs/episode-029-context-art-5.2.json
```

Six slides — one per presenter — receive context-specific procedural illustration while the other fourteen remain the 5.1 control:

- NORA / slide 2 — `casefile_system`;
- Kai Patel / slide 4 — `river_monitoring`;
- Johan Vosloo / slide 5 — `water_infrastructure`;
- Thabo Mokoena / slide 7 — `mineworker_claims`;
- Amari Ndlovu / slide 8 — `care_pathway`;
- Diane Sterling / slide 16 — `oil_market`.

The production report now records contextual-art count, source, kind and layer.

Documentation:

```text
docs/CONTEXTUAL_ILLUSTRATION.md
docs/EPISODE_SCHEMA.md
```

Regression coverage:

```text
tests/test_contextual_illustrations.py
```

The 5.1 baseline contains **92 GitHub-green tests**. Milestone 5.2 adds **6 contextual-illustration tests**, so the repository should collect **98 tests** after upload. The full 20-slide Ep029 5.2 proof already renders locally.

Workflow:

```text
.github/workflows/render-milestone-5-2-contextual.yml
```

Workflow name:

**Render Milestone 5.2 contextual illustration proof**

Expected Drive destination:

```text
AI-Geopolitical /
Automation - Temporary Artifacts /
Production Episodes /
Ep029 Contextual 5.2
```

Milestone 5.2 is an **architecture proof, not visual parity**. The procedural backend gives the compositor something deterministic to test, but the original reference slides still have much stronger bespoke scene illustration and engraved detail. After 5.2 is green, do not keep polishing procedural drawings indefinitely. Proceed to **Milestone 5.3 — generated contextual-asset backend proof**, using the 5.2 `asset` hook while code continues to own all text and locked identities.


Do not create 20–30 unrelated giant templates. Build variants from reusable editorial primitives while preserving each character's visual grammar.

## Main production files

```text
docs/PRODUCTION_SPEC.md
docs/FIDELITY_BENCHMARK.md
docs/CONTEXTUAL_ILLUSTRATION.md
config/brand.json
config/characters.json
config/layouts.json
config/layout_presets.json

src/editorial_primitives.py
src/contextual_illustrations.py
src/render_identity_slide.py
src/render_identity_stress_pack.py
src/render_nora_layout_family.py
src/render_johan_layout_family.py
src/render_diane_layout_family.py
src/render_kai_layout_family.py
src/render_thabo_layout_family.py
src/render_amari_layout_family.py
src/route_episode.py
src/render_production_episode.py
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
tests/test_production_episode.py
tests/test_milestone_5_ep029.py
tests/test_fidelity_primitives.py
tests/test_contextual_illustrations.py
tests/test_prototype.py

inputs/episode-029-20july2026.json
inputs/episode-029-context-art-5.2.json
.github/workflows/render-milestone-5-ep029.yml
.github/workflows/render-milestone-5-1-fidelity.yml
.github/workflows/render-milestone-5-2-contextual.yml
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
3. benchmark and render approved 20-slide production episodes;
4. export 20 PNGs + contact sheet + QA report;
5. generate caption + exactly five hashtags;
6. generate Reel/video assets from the strongest approximately six slides;
7. add optional local RTX 3080 enhancement jobs;
8. publish through official Meta/Instagram APIs;
9. add retries, logging and analytics.

Quality review remains mandatory until the automated output consistently matches the established AI Geopolitic editorial standard.
