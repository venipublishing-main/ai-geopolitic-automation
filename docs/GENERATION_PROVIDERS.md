# Phase B: generation / worker foundation

AI-Geopolitic owns the generation contract and routing policy. Workers are
interchangeable implementations of that contract. This phase implements contracts,
an in-memory coordinator, audits, a deterministic mock and inactive adapter seams.
It performs no real generation, worker installation, model download or API call.
There are no new dependencies and no connection to production rendering.

Phase A was accepted through real Drive/rclone ingestion: `BUILD_READY`, Ep103,
2026-10-02 SAST, 20 validated slides, exit 0. Its parsing, manifest schema and
readiness behaviour are unchanged here.

## Boundary and packages

```text
Manifest v2 -> future SlideJob compiler -> GenerationJob -> GenerationRouter
                                                        |-> MockProvider
                                                        |-> WanGPProvider seam
                                                        |-> ComfyUIProvider seam
                                                        |-> future free-cloud providers
```

The SlideJob compiler and production consumer are deferred. `GenerationJob` is
not a slide schema: it can describe a context illustration, Reel frame or future
audio task. Episode ID, slide number, attempt and extra immutable trace tags are
optional tracing context. No provider-specific workflow or endpoint fields live
in the job. The current modules are:

- `src/providers/contracts.py`: frozen dataclasses, enum vocabulary, provider
  protocol, job/capability/resource validation and shared compatibility checks.
- `router.py`: explicit zero-cost policy, provider selection audits, worker-ID
  mapping and guarded status/result/cancellation delegation.
- `mock.py`: manually advanced IMAGE-only simulation with structured output.
- `model_registry.py`: empty production registry plus model/licence metadata.
- `local/base.py`, `local/wangp.py`, `local/comfyui.py`: isolated configuration
  and inactive local adapters using the same protocol.

## Job and asynchronous lifecycle

A caller supplies a unique `job_id`, modality, purpose, prompt and output format.
IMAGE/VIDEO require positive width/height; AUDIO does not use those dimensions.
Reference asset identifiers/paths, image-edit requirements, cancellation
requirements, model preference, deterministic seed and minimum compute resources
are explicit. Reference identifiers are carried intact; the foundation does not
load assets. The future worker boundary must resolve and validate those assets.
An explicit model preference is a requirement, with no automatic model substitution.

`IMAGE`, `VIDEO` and `AUDIO` vocabulary exists. Only the mock IMAGE lifecycle is
implemented in Phase B. No video/audio generation is implemented or advertised.

Provider operations are:

```python
submit(job) -> provider_job_id
status(provider_job_id) -> JobStatus
result(provider_job_id) -> GenerationResult
cancel(provider_job_id) -> JobStatus
available() -> bool
health() -> HealthReport
capabilities() -> ProviderCapabilities
resource_state() -> ResourceState
```

The Python methods return acknowledgements or snapshots; they are not a blocking
`generate() -> file` interface and do not require an asyncio framework. A future
transport may perform brief control-plane I/O but must not wait for generation to
finish inside `submit`. Generation remains an asynchronous worker job.

The explicit states are `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`.
Normal progress is queued -> running -> succeeded/failed. Queued/running jobs may
be cancelled. Terminal states cannot change; repeated cancellation is idempotent
and cancellation of successful/failed jobs retains that terminal state. Polling
may skip intermediate states, but observed running/terminal states cannot regress.
Failure snapshots contain a code and message; progress is optional and finite.

`GenerationRouter.submit()` returns the application job ID. `submission(job_id)`
exposes the selected provider and its worker-specific ID. `status`, `result` and
`cancel` accept the application ID and delegate to that same provider. Provider
response identities, modality and output format/dimensions are checked. A result
requires explicit `SUCCEEDED`; an existing file path does not establish success.
Results describe artifacts or synthetic structured data. File decoding, hash and
visual-content QA belong to the future artifact consumer.

## Deterministic selection and fail-closed policy

Registration order is the default priority. An explicit priority tuple must name
every registered provider exactly once. For each provider, selection evaluates:

1. Strict job validity before any provider probe.
2. Explicit availability, healthy status and well-formed capability/resource
   snapshots. Probe exceptions reject the provider.
3. Modality, format, references/editing, cancellation and seed support, requested
   model, and known dimension bounds. Pixel output with unknown bounds is blocked.
4. The project's immutable `ZeroCostPolicy`: only the enum `ZERO_COST` is allowed.
5. Online/idle resources, or explicitly supported queueing while busy. Unknown
   online/activity state blocks; requested GPU/memory and model availability must
   be proven. A model's known minimum VRAM is enforced even without a job minimum.
6. For real providers, provider/model/modality-specific licence permission.

The first eligible provider is selected; exactly one submission is attempted.
Every provider has an immutable `ProviderDecision` containing `provider_id`,
`eligible`, reason codes and a `selected` flag. Lower-priority eligible providers
remain visibly eligible but are not dispatched. `audit(job_id)` returns these
decisions even when selection fails. Typical rejection codes include
`PROVIDER_UNAVAILABLE`, `PROVIDER_UNHEALTHY`, `ZERO_COST_POLICY_REJECTED`,
`REFERENCE_IMAGES_UNSUPPORTED`, `DIMENSIONS_UNSUPPORTED`, `RESOURCE_BUSY`,
`VRAM_INSUFFICIENT_OR_UNKNOWN` and `MODEL_COMMERCIAL_PERMISSION_UNPROVEN`.

No eligible provider raises `NoFreeGenerationProviderAvailable` with its audit.
Submission failure raises `SubmissionFailed` and records `SUBMISSION_FAILED`;
there is no second-provider retry because the first worker may have accepted the
job before its acknowledgement failed. That identity remains reserved. A rejection
before any submission can be retried when resources recover. No paid fallback,
dimension/modality/reference changes or legacy-renderer fallback exists.

The job's `zero_cost_required` flag records caller intent. Setting it false never
relaxes the production router's project policy. Providers cannot supply an alternate
monetary policy. `PAID` and `UNKNOWN` remain rejected in development too.

## Monetary cost and compute resources

Zero marginal API charge is separate from finite execution capacity. Local does
not imply unlimited GPU/VRAM, RAM, model availability, disk or time. Capabilities
declare location and monetary classification separately. `ResourceState` carries
online/activity state, worker and GPU identity, total/free VRAM and RAM, active
job, loaded model and available model IDs. Unknown readings remain `None`.

No GPU or free-memory values are fabricated by the mock or local seams. Resource
requirements with unknown measurements fail closed. Known loaded-model state is
informational; requested/default models must be in the available model inventory.
Supported model identifiers in capabilities describe compatibility separately
from that inventory. The structure can represent several household workers, but
no worker networking, hardware probing or execution service is implemented yet.

## Production model permission

`ModelMetadata` holds provider/model identity, modality, minimum/preferred VRAM,
reference/edit support, quantization, licence, commercial-output permission,
attribution requirements, known restrictions and optional benchmark score. The
shipped registry has **no entries**; tests use clearly invented contract fixtures.
There are no speculative claims about external models or licences.

For a real provider, absent/unknown/false commercial permission or a missing
licence blocks selection. Unknown attribution requirements block; required
attribution needs the job's explicit permission. Recorded restrictions block
until their handling is implemented. Model reference/edit capabilities and known
minimum VRAM are enforced. Benchmark score is only a registry field in Phase B;
Phase C must establish a scoring method, approval evidence and acceptance threshold.
Permission claims must come from reviewed authoritative evidence before populating
the production registry. No WanGP/ComfyUI worker is production-selected here.

## Deterministic mock

`MockProvider` is explicitly synthetic. It creates no files and does not import
Pillow, call a network, access a GPU or invoke an image API. Calling `advance()`
manually moves QUEUED -> RUNNING -> SUCCEEDED or configured FAILED. Cancellation,
unknown IDs, duplicate identities, capability/resource rejections and result
retrieval exercise the same contract. Results are immutable key/value data,
marked `synthetic=True`, with no visual output.

Production-default routing rejects synthetic providers. An explicit
`RoutingPolicy.development()` enables mock routing; only synthetic providers skip
commercial-model permission checks. Real providers still need that evidence and
all providers still need the zero-cost gate.

```python
from src.providers.contracts import GenerationJob, Modality, OutputRequirements
from src.providers.mock import MockProvider
from src.providers.router import GenerationRouter, RoutingPolicy

mock = MockProvider()
router = GenerationRouter((mock,), policy=RoutingPolicy.development())
job = GenerationJob("demo-1", Modality.IMAGE, "context-art contract test",
                    "A system diagram brief", OutputRequirements("png", 1080, 1080))
job_id = router.submit(job)
worker_id = router.submission(job_id).provider_job_id
mock.advance(worker_id)  # RUNNING
mock.advance(worker_id)  # SUCCEEDED; structured data only
result = router.result(job_id)
assert result.synthetic and not result.artifacts
```

## Inactive local seams

WanGP is the candidate **general-purpose local multimodal worker**. ComfyUI is
the candidate **specialist local image/edit worker**. Neither is production-selected
until the controlled benchmark and transport integration are verified.

Both accept a neutral `LocalWorkerConfig` with optional endpoint/runtime path and
worker identity. Without runtime/endpoint configuration they report NOT_CONFIGURED.
With either supplied they report INTEGRATION_PENDING and remain unavailable.
They advertise no proven modalities/models/capabilities or monetary classification;
hardware/online values remain unknown. All job operations safely reject execution.

They import no WanGP/ComfyUI internals and never launch processes, contact endpoints,
download models, click a GUI or fabricate successful generation. Phase C must
verify the actual headless/API/job semantics and translate inside each adapter.
The generic protocol already accommodates queue/status/progress, file results,
cancellation, modality expansion and resource/loaded-model snapshots without
assuming one endpoint schema or reusable-session implementation.

## Validation and the next boundary

Run from the repository root:

```powershell
.\.venv\qa\Scripts\python.exe -m pytest tests/test_generation_contracts.py tests/test_generation_router.py -q
.\.venv\qa\Scripts\python.exe -m pytest tests/test_daily_readiness.py tests/test_phase_a1_compatibility.py -q
.\.venv\qa\Scripts\python.exe .venv/qa/run_full_qa.py
```

The Phase B tests use no internet, Drive, GPU, worker installations or paid APIs.
Validation completed: **172 Phase B tests passed in 0.56s**, **189 Phase A/A.1 tests
passed in 0.86s**, and **463 total tests passed in 65.38s** through the full Windows
QA adapter (172 + 189 + 102 existing). No tests were skipped.
The existing ignored Windows QA adapter supplies the existing renderer font/shaping
requirements for the full suite. No tests are skipped and no renderer assertions,
fonts/config/assets, Phase A behaviour or Manifest v2 fields are changed.

This foundation stores jobs/audits in memory under one coordinator. Durable state,
restart-safe idempotency, concurrent dispatch coordination, transport retries,
worker networking, real artifact inspection and licence/benchmark approval data
are deferred. It is not a production execution service.

Phase C is one controlled slide and visual benchmark: verify selected WanGP and
ComfyUI routes, then connect an approved contextual asset through Milestone 5.2's
existing `asset` seam. The future SlideJob compiler and artifact consumer need
their own reviewed integration. No 20-image batch, review UI or publishing is
started in Phase B.
