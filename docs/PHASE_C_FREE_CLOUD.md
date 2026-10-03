# Phase C.1 — free cloud provider network

Implementation and offline verification are separate from real-image acceptance.
The prior local Phase C commit is retained; WanGP/ComfyUI remain dormant until
their hardware and reviewed profile gates pass. Cloud transport has no local GPU
requirement. No Pollinations/Puter implementation, carousel batch or publishing
workflow is introduced.

## Contract and priority

`src/providers/cloud/` implements the unchanged `GenerationProvider` protocol.
`GenerationRouter` retains its selection/lifecycle contract; `ZeroCostPolicy` is unchanged: production accepts only
`ZERO_COST`, with exact reviewed model permission and current availability.
The cloud registry is explicitly supplied by the cloud consumer; the generic
registry remains empty by default. No cloud API/settings leak into neutral jobs.

`python -m src.phase_c_cloud` reads current Drive documents using the existing
rclone configuration and performs discovery only. `--execute` is required for
inference. Priority defaults to `cloudflare_workers_ai,ai_horde`; `--priority`
must name both exactly once. Paid/unknown/offline/unsupported/unlicensed providers
can be skipped before dispatch. One provider is selected and submitted once
through the existing router; exceptions never dispatch to a second provider.
Future providers and verified local workers can be registered explicitly later.

The report includes actual SAST readiness, episode source, selected slide/model,
priority, health, cost, model permissions/evidence, resources, quota observations,
predicted generation count and durable reserved attempts. Discovery never submits
an inference request. A blocked document's human episode is labelled a hint;
it cannot replace a validated Manifest. There is no date override in this CLI.

## Cloudflare Workers AI

The exact pinned model is `@cf/black-forest-labs/flux-1-schnell`; there is no dev
substitution. Official REST model search proves current model availability.
Inference uses the direct account `/ai/run/{model}` endpoint with prompt,
four steps and an optional seed. A single-thread executor isolates the synchronous
REST call: `submit()` returns a local coordination ID promptly; status reports
queued/running/succeeded/failed. This ID is never claimed to be a Cloudflare
remote task ID. Remote cancellation is unsupported and advertised false.

Environment configuration (never print or include values in reports):

```text
AI_GEOPOLITIC_CLOUDFLARE_ACCOUNT_ID       32-character account identifier
AI_GEOPOLITIC_CLOUDFLARE_API_TOKEN        Workers AI scoped token
AI_GEOPOLITIC_CLOUDFLARE_PLAN             workers-free
AI_GEOPOLITIC_CLOUDFLARE_FREE_ALLOCATION_ONLY  1
```

The last two fields are explicit operator declarations after verifying the actual
account plan. An adapter token cannot prove billing status; no automated billing
verification is claimed. Both declarations must match exactly for `ZERO_COST`.
A working token alone, paid/absent plan or missing declaration yields `UNKNOWN`.
No SDK, AI Gateway, wallet, prepaid credit or upgrade path is used. Absent
credentials produce `NOT_CONFIGURED`. Authentication/entitlement/quota failures
block the adapter; billing/entitlement rejection also revokes its zero-cost
classification. A new process requires a fresh observation/declaration; the
adapter cannot control account changes made outside this application.

[Cloudflare pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)
documents Free allocation exhaustion as rejection rather than paid overage.
Remaining neurons/reset observation stays null: no account quota API is assumed.
A successful image does not imply remaining allowance. Rate/quota rejection
means allocation is unavailable for this runtime; it does not invent a remaining
neuron count or a precise cause when the HTTP response is ambiguous.

[Cloudflare's model card](https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/)
and [official REST reference](https://developers.cloudflare.com/api/resources/ai/methods/run/)
show seed input. The model-specific input schema is narrower than the generic
image schema. This slice requests and strictly checks 1024-square output;
live dimension compatibility remains unproven until inference succeeds. Ignored
dimension inputs cannot produce falsely dimension-labelled artifacts: wrong
dimensions fail instead of being resized. Prompts longer than 2048 characters
are blocked, with no silent truncation of Manifest guardrails.

The approved `ModelRegistry` entry is IMAGE, Apache-2.0, commercial output allowed,
no generated-output attribution condition, no reference/edit support and no client
VRAM requirement. Evidence: [BFL Schnell model card](https://huggingface.co/black-forest-labs/FLUX.1-schnell),
[BFL repository](https://github.com/black-forest-labs/flux/blob/main/README.md), and
[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0). Weight/code distribution
has separate notice obligations. Model-card guidance and service terms still apply;
the registry does not guarantee copyright, factual accuracy or reproducible pixels
across hosted implementation changes.

## AI Horde

The adapter uses the [official image API](https://aihorde.net/api/swagger.json):
POST `/v2/generate/async`, GET `/v2/generate/check/{id}`, GET result status, DELETE
result status. Only canonical acknowledged UUIDs become owned jobs. Malformed or
lost acknowledgements reserve the identity and never authorize duplicate dispatch.
Polling maps validated counts/flags into queued/running/failed/succeeded states.
Completion must contain exactly one image, exact requested model, no censorship
or fault metadata, and the requested dimensions.

`AI_GEOPOLITIC_HORDE_API_KEY` is optional; absence uses official public key
`0000000000`. Personal keys remain secret. Volunteer compute is `ZERO_COST`;
kudos indicate scheduling priority, not money. Anonymous jobs have lower priority
and the service makes them shared even if `shared=false` is requested.
This behaviour is documented by the [official service repository](https://github.com/Haidra-Org/AI-Horde).

Dynamic `/v2/status/models?type=image` discovery exposes active worker counts and
service estimates. It grants no licence. The candidate is exactly
`Flux.1-Schnell fp8 (Compact)`, with a fixed single-image four-step Euler/Karras
request and `allow_downgrade=false`. `r2=false` requests base64 output; no remote
artifact URL is followed. Generic deterministic seed support is false because
heterogeneous/batched workers do not guarantee deterministic execution. An explicit
deterministic-seed requirement fails before dispatch.

**The exact compact Schnell checkpoint is now approved.** The original v1 record
did not provide permission evidence; the current official
[v2 record](https://models.aihorde.net/api/model_references/v2/image_generation/model/Flux.1-Schnell%20fp8%20%28Compact%29)
explicitly binds its exact name/hash to Apache-2.0 and `commercial_use=allowed`.
Its evidence points to the authoritative BFL Schnell card. The official Apache
definition lists no material restrictions; `include_license` concerns redistribution
of model/code, with no generated-image attribution obligation identified.
See [the recorded permission review](HORDE_MODEL_PERMISSION.md) for the exact hash,
sources, intended contextual-art use, active-model cross-match and limitations.
The conditional-permission extension also registers exact AlbedoBase XL 3.1 and
SDXL 1.0 metadata; see [conditional model permissions](CONDITIONAL_MODEL_PERMISSIONS.md).
The default adapter still selects compact Schnell. Other identifiers/unknown permissions retain
the existing fail-closed checks. Transport tests still use clearly labelled
synthetic metadata where needed; separate tests cover the real reviewed registry
against offline HTTP fixtures and the recorded official reference snapshots.

DELETE is request/result cancellation, not a promise to interrupt physical worker
inference. The official server returns a **pre-cancellation** snapshot; an HTTP
success alone is never reported as cancelled. A subsequent check must observe
terminal no-work/no-result state. If a completed image wins the race, success wins.
Timeout or missing acknowledgement leaves the job unresolved. See the
[official cancellation implementation](https://github.com/Haidra-Org/AI-Horde/blob/main/horde/apis/v2/stable.py).

## HTTP and artifacts

The stdlib transport allows only fixed official HTTPS origins, disables redirects
and environment proxies, sets finite timeouts and bounds responses to 32 MiB.
Structured errors omit response text, URLs, headers, keys and exception chains.
No HTTP SDK or new dependency is added. Base64 is bounded and strictly validated;
Pillow decodes only PNG/JPEG/WEBP single-frame images of exactly the requested
size with non-uniform content. Valid pixels convert losslessly to RGB PNG without
resizing; artifacts are confined to ignored `output/phase-c[1]/` locations.

The bridge has two explicit profiles: `THABO_MATERIAL_CHAIN` preserves the earlier
single-Thabo mapping with five explicit stage labels and Manifest reasoning family
`material_chain`. `KAI_NETWORK_MESH` accepts only current Slide 05, single Kai,
null pairing/central relationship and interior numbering. It maps headline,
subheadline, main visual phrase, three takeaway ideas and core argument verbatim
to the approved existing `network_mesh` renderer. This is a provisional benchmark
compatibility mapping, not a general layout compiler. The renderer retains its
existing NETWORK/SENSOR/MODEL/NODE/USER/REPAIR diagram labels; Manifest essential
labels are not silently truncated into its five-node mechanism. Other profiles
fail closed. No stale identity, reconstructed Manifest, invented factual copy or
shortened text is accepted. Cloud trace uses the validated current episode/slide.

Kai's background plate occupies `[470,545,940,875]`, under the deterministic mesh.
It clears the portrait `[96,145,431,505]`, top copy/quote `[485,108,940,530]`, facts
`[96,555,425,870]` and footer/takeaway starting below y890. Opaque network nodes
and exact ink/accent foreground draw afterward. Pixel tests use the full recorded
Ep104 copy and preserve these regions, header/counter and mesh foreground.
The shared Milestone 5.2 asset hook, temporary assets path, tint, opacity and
cleanup remain authoritative; no renderer or canonical asset changes are needed.

The shared `execute_candidate` consumer performs artifact QA, ignored temporary
asset staging and the existing Milestone 5.2 compositor. Code retains portrait,
accent, text, labels, factual copy, footer and slide number. Human visual review
is still required; successful transport is not editorial acceptance.

Use `--execute --defer-composition` to hold the one mechanically validated asset
for visual inspection before invoking the same `phase_c.compose()` function with
the validated render spec. Exit 0 / `ARTIFACT_REVIEW_REQUIRED` means generation
succeeded but composition and acceptance remain pending. It does not authorize
another inference request. The successful attempt remains consumed in the ledger.
Default composition behaviour is preserved for existing callers.

A benchmark-only pass-through transport observer captures already-issued Horde
ACK/check/result responses, whitelisting counts, job ID, seed, model and worker
metadata. It sends no additional requests and stores no credentials, headers,
payloads or base64. Queue/generation durations are first-observed polling bounds;
unobserved phases stay null. It does not change the provider or router. Progress
write failure does not change ACK/status semantics. The ledger persists the real
job ID immediately after acknowledgement, before polling.

The durable `output/phase-c1/attempt-ledger.json` allows one normal dispatch,
plus one explicit diagnosed retry after proven terminal technical failure, using
a new job identity. It persists across processes/days, does not reset per episode,
and never permits a second-provider comparison or aesthetic retry. A process lock
prevents concurrent CLI dispatch. Lost acknowledgements/status, REST timeout or
ambiguous coordinator failure mark the attempt unresolved and block retry.
Missing/contradictory Cloudflare success flags also remain unresolved, block the
runtime and revoke its cost classification; a malformed acknowledgement is not
proof that remote inference has stopped.
Copy/composition failures consume the successful image and never regenerate art.
Do not delete the ledger/lock to bypass these controls; this is a controlled
benchmark, not a restart-safe production scheduler.

Report: `output/phase-c1/benchmark-report.json`. A successful candidate adds
`output/phase-c1/<episode>/slide-<N>/<provider>/context-art.png`,
`slide-composite.png` and `generation-metadata.json`. Adapter originals remain
under `cloudflare-runtime/` or `horde-runtime/`. Binaries remain ignored. The
authorized Ep104 Slide05 package may be copied with existing rclone to
`AI-Geopolitical/Automation - Temporary Artifacts/Phase C Free Cloud Benchmark/Ep104 Slide05`,
as a benchmark candidate awaiting human review; never Daily Slides/final archive.

## Validation and current gates

```powershell
.\.venv\qa\Scripts\python.exe -m pytest -q tests/test_phase_c_cloud.py
.\.venv\qa\Scripts\python.exe .venv/qa/run_full_qa.py -q tests/test_phase_c.py tests/test_phase_c_live.py
.\.venv\qa\Scripts\python.exe -m pytest -q tests/test_generation_contracts.py tests/test_generation_router.py
.\.venv\qa\Scripts\python.exe -m pytest -q tests/test_daily_readiness.py tests/test_phase_a1_compatibility.py
.\.venv\qa\Scripts\python.exe .venv/qa/run_full_qa.py
python -m src.phase_c_cloud
# Only after all readiness/permission/free-plan gates pass:
python -m src.phase_c_cloud --execute
```

Normal tests mock HTTP and prohibit accidental network calls. Full Windows QA
uses the existing ignored DejaVu/FriBiDi adapter; Linux/CI, requirements, canonical
assets, renderer code, Manifest/readiness and router lifecycle contracts remain unchanged.

Current validation: Kai bridge **18 passed**; cloud C.1 **116 passed**; local C **64 passed, 1 skipped**
(opt-in worker discovery); Phase B **172 passed**; Phase A/A.1 **189 passed**;
full Windows QA **661 passed, 1 skipped in 87.91s** before inference. The additional 102 existing
renderer/integration tests remain green. `git diff --check` passes.

2026-10-03: the live dry run passes `BUILD_READY`, Ep104, 20 validated slides,
Slide 05, `kai_patel`, `network_mesh`, eligible zero-cost Horde with the exact
approved compact Schnell model, 1024-square output and predicted generation count
1. There are no bridge/readiness blockers; the dry run recorded zero attempts.
The exact live copy also passed deterministic renderer preflight on Windows with
the existing ignored DejaVu/FriBiDi font adapter, preserving Linux/CI behaviour.
Horde completed the one authorized job `af14c755-88db-4dbd-a4ea-6473282d7e92`,
seed `3681541205`, worker `AstralWeaver` (`8f13e7eb-1950-4a55-925a-e875980aef90`).
Observed queue duration was 1012.016 seconds, processing 30.422 seconds, and total
through result retrieval/mechanical QA 1044.985 seconds. These are polling bounds.
The returned 1024×1024 nonuniform PNG passes mechanical QA. Pre-composition visual
inspection found generated lettering, a copyright/signature-like mark and a large
literal fluffy cloud contrary to the Manifest guardrail. Report blocker:
`CONTEXT_ART_VISUAL_GUARDRAILS_FAILED`. Generation succeeded; candidate acceptance
did not. The asset is withheld: no final composite, upload, aesthetic retry or new
commit/push. The three prior local Phase C commits remain intact. Successful-slice
post-tests/commit/push conditions have not been met. No visual parity is claimed.

Next-provider candidates remain Phase C.2 only: Pollinations must prove zero price
for the exact current model; Puter must use only verified free allowance with no
purchased credits or paid subscription fallback. Neither is implemented here.

The later exact AlbedoBase XL 3.1 internal benchmark passed its mandatory visual
screen and produced one Ep104 Slide05 candidate. Conditional credit handling,
the independent one-attempt ledger, live evidence, protected-region checks and
limited single-provider acceptance are recorded in
[conditional model permissions](CONDITIONAL_MODEL_PERMISSIONS.md). The preceding
Flux rejection remains historical evidence; it has not been reversed. Production
public-credit delivery and human visual quality review remain outstanding.
