# Exact Horde model permission review — 2026-10-03

Approved exact model: `Flux.1-Schnell fp8 (Compact)`, version 1.0, IMAGE,
fp8, Apache-2.0, commercial output allowed, generated-output attribution not required.
The worker-hosted checkpoint needs no client GPU/VRAM and supports the adapter's
single-image four-step Euler/Karras request at 1024 square. Seed determinism remains
unproven and is not advertised. The neutral contract/router/zero-cost policy and
readiness validation are unchanged.

The current [official v2 model record](https://models.aihorde.net/api/model_references/v2/image_generation/model/Flux.1-Schnell%20fp8%20%28Compact%29)
provides explicit licence/commercial conclusions for this exact identifier, plus
its exact `flux1CompactCLIPAnd_Flux1SchnellFp8.safetensors` checkpoint hash:

```text
5C2C590E92ED47500092EF8E1A00FD1F8E61009DA93B89130A80940F5257DF17
```

The record reports `license_expression=Apache-2.0`, `commercial_use=allowed`,
`redistribution=allowed_with_conditions`, and `obligations=[include_license]`.
Its reviewer is `horde-model-reference-license-backfill`, reviewed 2026-08-26.
Its note identifies the mirrored checkpoint as Schnell and cites the
[authoritative BFL Schnell card](https://huggingface.co/black-forest-labs/FLUX.1-schnell),
which explicitly permits commercial model use. The
[official Horde licence definition](https://models.aihorde.net/api/model_references/v2/licensing/licenses/Apache-2.0)
reports commercial use allowed, no restrictions, and the canonical
[Apache-2.0 text](https://www.apache.org/licenses/LICENSE-2.0).

Output-attribution review: Apache notice/licence obligations concern distribution
of the licensed model/code and its derivatives. No condition requiring attribution
on generated contextual images is identified in these sources. This benchmark
does not redistribute model weights. The BFL out-of-scope guidance was also reviewed:
the intended text-free infrastructure illustration has no identity generation,
factual image claims, harmful deception, targeted harassment or automated decisions.
Deterministic code retains all factual copy, portrait, labels and layout; human
editorial review remains necessary. Model-card guidance/service rules still apply.

This approval is for this exact checkpoint as recorded by the official service;
it does not approve another compact variant, dev model or whole Flux family.
The previous v1/Civitai evidence gap is resolved by the explicit current v2 record.
The checkpoint hash binds the metadata review; it is not a claim that remote worker
weights were cryptographically inspected. No model download occurred.

## Discovery and choice

The actual [active-model endpoint](https://aihorde.net/api/v2/status/models?type=image)
was cross-matched by exact identifier against the current official
[v2 search](https://models.aihorde.net/api/model_references/v2/image_generation/search?limit=500&source=horde)
and [popular](https://models.aihorde.net/api/model_references/v2/image_generation/popular)
routes. Search returned all 163 records with no remaining page. The initial active
snapshot had 145 records and 142 exact positive-worker matches; zero-worker records
were ineligible and an unmatched identifier was not approved.

The compact Schnell entry was the only cross-matched Apache-2.0 candidate. It is
generalist, non-NSFW, has an active worker and a compatible four-step profile;
it avoids the unhandled conditions of other recorded licences. The initial
snapshot had one worker and estimated ETA 577 seconds. Availability/ETA may change
and do not prove a specific job can finish. No exploratory generation was made.

Reviewed metadata is recorded in `src/providers/cloud/models.py`; original official
model/licence snapshots are in `tests/fixtures/cloud/`. Broader discovery snapshots
are ignored under `output/phase-c1/horde-permission-review/`. Live discovery remains
separate from permission: unreviewed/unknown/prohibited models still fail closed.

## Current Ep104 candidate and remaining gate

Readiness now returns exit 0, READY / BUILD_READY, Ep104, 2026-10-03, 20 validated
slides, no blockers, using live rclone and the actual SAST clock.
The selected editorial candidate is Slide 5, Kai Patel:
“THE CLOUD” STILL NEEDS MEGAWATTS, PIPES AND LAND.
Its Manifest hero is a user network flowing into a cutaway campus with fibre,
transformers, cooling and water infrastructure. This is suitable for contextual
art with deterministic portrait/text/labels/composition.

The existing bridge accepts only single-Thabo material chains with five explicit
labels. Candidate 5 has Kai and six labels; all Thabo appearances in the current
Manifest are dual-panelist slides. No current slide satisfies the supported bridge.
The dry run records `requested_slide=5`, `selected_slide=null`, expected dimensions
1024 square, Horde eligible/ZERO_COST/Apache-2.0, and predicted generation count 0.
It fails `CURRENT_SLIDE_BRIDGE_UNAVAILABLE` / `SINGLE_THABO_SLIDE_REQUIRED` before
inference. Cloudflare staying NOT_CONFIGURED is not the blocker.

Per the task's stop condition for another real acceptance blocker: zero generation
attempts, no Horde job/lifecycle/duration, no image/composite/upload and no push.
Acceptance is not declared. A reviewed bridge for a supported current candidate
is needed before the one-image benchmark can execute.

Verification: `python -m pytest -q tests/test_phase_c_cloud.py --tb=short` passed
116 tests in 16.49s; `python .venv/qa/run_full_qa.py` passed 643 tests with one
opt-in worker-discovery skip in 84.15s. Both used the existing QA Python environment.
The added checks bind the recorded exact reference/hash/licence, exercise the
production reviewed registry through mocked Horde transport, and prove a ready
current Manifest with unsupported composition cannot dispatch an image. The
original fail-closed permission tests remain. `git diff --check` passes.
