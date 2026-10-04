# Phase D.2 — three-slide real generalisation benchmark

This is an unpublished internal benchmark of historical Ep104, production date
2026-10-03. `CURRENT_READINESS = NOT_ASSERTED` and
`SOURCE = ACCEPTED_EP104_HISTORICAL_SNAPSHOT`. No date override, current Drive
readiness claim, carousel, dual slide or additional Kai experiment is permitted.
Human visual approval is separate from engineering QA and Git publication.

## Authority and selected path

The full accepted Manifest is the D.1 text fixture, pinned to canonical SHA256
`955c5aad9d28e044f7454032cd811f39bc7eb5fa55798d87e5384b6a6f2e405d`.
All three SceneContracts must compile before the first submit. Existing preflight
contract/prompt evidence cannot be overwritten with different content. Rendering
recompiles the same Manifest/configuration and compares contract hashes.

| Order | Slide | Panelist grammar | Argument family | Portrait / copy plan |
| --- | --- | --- | --- | --- |
| 1 | 14 Nora | system_axis | physical_stack | left 20%, mid; vertical takeaway rail |
| 2 | 12 Diane Sterling | market_grid | allocation_flow | right 22%, mid; three-node sequence |
| 3 | 16 Amari Ndlovu | regional_memory | regional_pathway | right 22%, lower-mid; left-weighted headline, three-node sequence |

The contracts differ in portrait geometry, hero geometry, object distribution,
headline arrangement and route/shape/micro-detail tendencies. All exact labels,
headlines, decks, main phrases and three takeaway ideas remain Manifest-owned.

`premium_sdxl_prompt.py` is a generic SceneContract-to-SDXL bridge. It converts
hero coordinates through the same square contain transform as rendering, names
the planned regions and quiet lanes, and retains the semantic/factual brief.
Manifest sign/stamp/label names describe concepts, never generated lettering.
One `positive###negative` delimiter uses the accepted Horde SDXL conditioning
path. Negative conditioning excludes lettering, branding, marks, panelist portraits,
neon, contact sheets and literal fluffy-cloud metaphors. No per-slide manual prompt,
reference image, alternative seed, runtime language model or manual anchor map exists.

## Exact provider and permission gate

Only the existing `AIHordeProvider`, `ALBEDO_SETTINGS` and exact
`AlbedoBase XL 3.1` are used. Settings remain 30 steps, CFG 7.5, Euler ancestral,
Karras, one 1024-square image and requested seed `1234567890`. Worker-returned
seeds are recorded separately: heterogeneous worker execution is not deterministic.

Before every submission, the coordinator retrieves current official
[Horde model reference](https://models.aihorde.net/api/model_references/v2/image_generation/model/AlbedoBase%20XL%203.1),
[author permissions](https://civitai.com/api/v1/models/140737),
[exact version](https://civitai.com/api/v1/model-versions/1041855) and
[base licence](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/main/LICENSE.md).
Model/version/creator, checkpoint SHA, conditional commercial permissions,
credit requirement and the reviewed base-licence bytes must still match. Then the
existing cloud policy validates provider health, exact active model, ZERO_COST,
INTERNAL_BENCHMARK scope and recorded obligations. Unavailable or changed evidence
blocks submission; no alternate model/provider is tried.

Creator `albedobond` and required credit remain in every generation receipt:
“Context illustration generated with AlbedoBase XL 3.1 by albedobond.”
Publication attribution is required. Public publication is BLOCKED while credit
delivery and human review remain unresolved. Credit is not rasterised into slides.

## Durable sequential execution

`phase_d2_benchmark.py` implements a fixed ordered selection and independent ledger
with an exclusive mutation lock, atomic replace and fsync. Each attempted submit
is reserved before POST. A crash or lost ACK consumes the slot; it cannot lead
to a retry. The ledger permits at most three reservations, at most one per slide,
and only the next selected slide. No reset/retry, fourth-slide or fallback API exists.

The next generation is blocked until the previous hero is technically complete,
explicitly inspected and either rendered or withheld as a visual/content failure.
Uncertain submission/status, timeout, confirmed technical failure, authority/copy/
portrait/rendering failure stops the run. Visual guardrail failure preserves the
rejected hero and withholds composition. A clearly visual semantic incompatibility
can likewise be preserved without rendering; no aesthetic retry follows either.
Further preauthorised targets may proceed only through fresh provider/licence gates.

The existing provider raster consumer stages byte-identical PNGs under ignored
`output/phase-c1/phase-d2-staging/`, preserving its confinement policy. Copies are
placed in the D.2 package and hash-bound to receipts. No provider transport, old
attempt ledger, licence policy, canonical portrait, font or proof compositor changes.

## Visual and mechanical QA

Technical checks validate the actual 1024-square PNG, nonuniformity, exact declared
provider/model, one result, remote ACK, returned seed, contract/prompt/raster hashes
and conditional licence receipt. D.2 adds a receipt-bound hero source kind; generic
unproven new-generation sources remain blocked in D.1.

Agent visual observation uses the existing content-screen flag vocabulary, with
SHA-bound evidence. It records semantic-placement compatibility, annotation-anchor
plausibility, quiet regions and composition safety. This is visual judgement, not
computer vision or object recognition. Human review remains authoritative.
Missing, failed or incompatible visual evidence cannot enter D.2 rendering.

Only `premium_slide_renderer.render_preview` composes successful heroes. Neutral
C.2 portrait preparation and C.3 engraving helpers already reused by D.1 are
retained, but C.2/C.3/C.4 proof entrypoints and Phase-1 renderers are never called.
C.4 finishing is not applied globally. The renderer adds an actual text-draw trace
and collision/protected-face checks; the new metadata does not alter the D.1 ink
process or canonical identity. No reference is read during composition.

Render QA checks valid 1080-square PNG, pixel/hash binding, actual copy draw trace
against the Manifest, exactly three takeaways, canonical portrait hash, exact
panelist accent, furniture/counter/date/footer, safe text zones and no face collisions.
Copy verification is a rendering trace, not OCR. Output remains internal and
BLOCKED for publication regardless of mechanical or agent visual results.

## Package and review references

Ignored root: `output/phase-d2/Ep104/`. Each selected slide has `contract.json`,
`prompt.json`, `context-art.png`, `generated-metadata.json`, `reference-final.png`,
reference metadata and `review.json`. `rendered-slide.png` exists only when the
hero passes guardrails and is sufficiently contract-compatible. Rejected heroes
remain visible. Reports are `benchmark-report.json` and `benchmark-report.md`.
Provider lifecycle observations capture queue/processing/completion timing bounds;
these are polling observations, not instrumented worker execution durations.

The actual final PNGs were metadata-verified and copied read-only from Drive:

| Slide | Reference file ID |
| --- | --- |
| 14 | 1YGdFRhHfLWeu-WxodaO5iVYrgL6CEEa7 |
| 12 | 1bZvww27-qLxTYnDMNNyC2XTFKwFUB3HZ |
| 16 | 1QrpSm2mJk34MJQMbGnJEUMS5d8QJv397 |

References are development/human-review comparisons only. They are not generation
inputs or runtime dependencies. Evidence verification rechecks actual stored job
IDs, returned model/seed observations, artifact/copy authority and package hashes.
It makes no claim that SHA metadata authenticates the remote model's weight bytes.

## Entry points and tests

```sh
python -m src.phase_d2_benchmark                   # zero-generation all-three preflight
python -m src.phase_d2_benchmark --execute-next    # one reserved job, never a retry
python -m src.phase_d2_benchmark --record-review <evidence.json> --review-slide 14
python -m src.phase_d2_benchmark --report
```

The ignored Windows `.venv/qa/d2_cli.py` uses the existing DejaVu/FriBiDi/RAQM
font adapter. Linux/CI behaviour and dependencies are unchanged. Offline tests
simulate queued/running/terminal jobs, lost ACK/status, terminal failure, restart,
visual rejection, missing/tampered evidence and the hard fourth-request ceiling.
Network and old compositor entrypoints are prohibited during tests. Synthetic
rasters prove mechanics only, never semantic placement or visual parity.

Final job IDs, seeds, observations, outputs and post-benchmark test counts belong
in the ignored benchmark report. Successful engineering permits only
**PHASE D.2 THREE-SLIDE GENERALISATION BENCHMARK READY FOR HUMAN REVIEW**.
It never means D.2 ACCEPTED. No other singles, duals, variants or carousel follow.

## Observed run — stopped before completion

Two jobs were acknowledged on 2026-10-04; only Nora returned a verified image.
All three contracts and prompts were fixed before the first submission. No prompt
retuning, alternate seed, failed-slide retry or fourth request occurred.

| Slide | Horde job | Seed | Outcome |
| --- | --- | --- | --- |
| 14 Nora | 6075d1d0-8f40-4a88-bc55-a08aa4da51d6 | returned 1234567890 | Technical QA passed; HERO_VISUAL_GUARDRAIL_FAILED; visually incompatible; no composition |
| 12 Diane | 599f7b74-f21a-4244-b92e-97bfa752d343 | requested 1234567890; returned unknown | AMBIGUOUS_STATUS_STOP; remote outcome unknown; no further polling or composition |
| 16 Amari | none | none | Not reserved or submitted after Diane stop |

Nora's polling observations bound queue wait to 922.375 seconds and processing
to 106.046 seconds. The image contains multiple numeral/letter/pseudotext marks
and a broad geometric pyramid, rather than five identifiable dependency layers.
The lower pyramid intrudes into planned quiet lanes; deterministic annotation
terminals would be semantically ungrounded. This is agent visual judgement, not
computer vision. The failed PNG is preserved alongside its manual reference.

Diane's last successful observation was still queued and not faulted at elapsed
570.719 seconds, queue position 52, provider ETA 137 seconds. Subsequent status
polling failed, leaving no confirmed terminal result. This is not evidence that
remote inference was cancelled or failed. The stop rule prohibited further calls
and the Amari job. Requested seed must not be confused with a returned seed.

The three-slide benchmark is incomplete. It is **not READY FOR HUMAN REVIEW** as
a completed benchmark and is not accepted. Real hero-to-render cooperation and
the C.3 visual-quality target remain unproven. The generalized renderer is covered
by offline synthetic cases, not by a completed real D.2 composition in this run.
Code publication records the bounded implementation and its stopped evidence;
it does not declare production or visual acceptance.

Post-run QA: D.2 **36 passed** (18.26 s); D.1 **55 passed** (19.11 s);
C.4 **34 passed** (72.89 s); C.3 **34 passed** (24.87 s); C.2 **27 passed**
(4.53 s); provider/licence regressions **392 passed** (19.37 s).
Full Windows QA: **869 passed, 1 skipped in 223.20 s**. The skip is the existing
opt-in local-worker discovery smoke check, never inference. `git diff --check`
passes. No Linux/CI workflow, production font configuration or dependency changed.

The local evidence verifier checks both distinct acknowledged IDs, exactly two
recorded POSTs, returned Nora model/seed, contract/prompt/raster hashes and package
hashes. It retains the blocked publication flag and development-only references.
All 31 protected baseline files outside the two intentionally changed D.1 QA/
renderer sources remain byte-identical, including all 24 historical Phase C proof
files and the canonical portraits/font/compiler. No failed or missing hero is
replaced with a synthetic raster to disguise the live outcome.
