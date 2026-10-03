# Phase C: Ep103 Slide 12 only

Implementation is tested against offline engineering fixtures. The real generation,
live-copy-fit and visual-composition gates remain open. No model is selected or
commercially approved by this repository. Neither a real result nor an automatic
visual winner can be inferred from passing tests.

## Boundaries and official interfaces

The existing GenerationProvider contract and production zero-cost router are
unchanged. Standard-library HTTP/MCP transports isolate worker dependency trees.
Only plain HTTP on literal localhost is accepted; environment proxies and redirects
are disabled. There is no worker auto-start, model download, browser automation,
public endpoint, tunnel, partner workflow or cloud fallback.

WanGP's current [MCP v2 implementation](https://github.com/deepbeepmeep/Wan2GP/blob/main/shared/mcp_v2.py)
advertises model discovery/inspection and `wangp_session` actions for job polling
and targeted cancellation. The adapter requires async generation in tool discovery,
an image-only model and its default square resolution. It maps the headless API's
started task to RUNNING and trusts only explicit terminal result flags.
The [official API](https://github.com/deepbeepmeep/Wan2GP/blob/main/docs/API.md)
must be checked against installed help before launching an isolated worker.
Use MCP API v2 with async and a loopback-bound Streamable HTTP server; its configured
URL must include the actual MCP route. The client implements the
[2025-06-18 Streamable HTTP protocol](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports).

ComfyUI uses [official server endpoints](https://github.com/Comfy-Org/ComfyUI/blob/master/server.py)
for `/system_stats`, `/object_info`, `/queue`, `/prompt`, `/api/jobs`, `/api/jobs/{id}`,
`/api/jobs/{id}/cancel` and `/view`. The
[jobs normalizer](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_execution/jobs.py)
can label unspecified history as completed, so the adapter additionally requires
`execution_status.status_str=success` and `completed=true`. Cancellation acknowledgements
are requests; only actual polled terminal state becomes CANCELLED. There is no global
`/interrupt` fallback. Older installations lacking the jobs API remain unavailable.

The fixed ComfyUI workflow uses CheckpointLoaderSimple, CLIPTextEncode,
EmptyLatentImage, KSampler, VAEDecode and SaveImage. All must advertise core
`python_module=nodes`. Checkpoint, dimensions, sampler, scheduler and sampling
bounds are checked against runtime discovery. Architectures needing different
loaders/custom nodes are unsupported in this slice; do not retrofit them by
passing arbitrary workflow JSON. Batch size is one.

## Reviewed external profiles

Supply an ignored, local configuration with top-level `wangp` and/or `comfyui`.
Each entry contains exactly `worker`, `artifact_root`, and `profile`:

- `worker`: LocalWorkerConfig fields `endpoint`, `runtime_path`, optional `worker_id`.
- `artifact_root`: absolute local worker output/retrieval directory.
- `profile.model`: existing ModelMetadata fields. Provider must match; modality IMAGE.
  Explicit licence, verified commercial-output permission, known attribution and
  minimum VRAM are required; unknown permission/restrictions remain blockers.
- `profile.evidence_urls`: authoritative model-card/licence, requirements and worker
  sources reviewed by the operator. URLs alone are not licence proof; the operator
  must read and record the determination before authoring this trusted profile.
- `profile.worker_revision`: WanGP SHA256 of installed `shared/mcp_v2.py`, checked
  against `worker.runtime_path`; ComfyUI exact `/system_stats` version, after reviewing
  that installation's API implementation. Source/version changes invalidate approval.
- `profile.width`/`height`: discovered supported square dimensions. Prefer 1024+
  when proven; no forced unsupported size. WanGP uses its discovered default.
- `profile.required_model_files`: complete reviewed absolute file inventory from
  actual model definition/discovery, including auxiliary weights. All must exist
  and be nonempty. There is no auto-download on missing files.
- `profile.seed_supported`, `cancellation_verified`, `local_execution_verified`:
  booleans reflecting actual reviewed capabilities. Cancellation remains false
  unless the installed targeted route/action is proven. Local execution must be
  verified before claiming ZERO_COST. No repository example grants real permission.

Evidence notes should include the licence terms/attribution determination, model
repository/revision, required files, approximate download/storage and reviewed
hardware/settings. Keep credentials out of profiles. Profile approval is an operator
policy boundary, not an automated legal assessment. Test fixture approvals are
explicitly synthetic and must never be used for production selection.

The registry remains empty by default. The execution router receives only the
reviewed profile's ModelMetadata. GPU free memory is checked both by router and
adapter. WanGP measures local NVIDIA resources; ComfyUI reads its actual CUDA device.
Unverified/multiple-device selection fails closed. No RTX 3080 is assumed.

## Commands and live source

Use the existing documented rclone environment variables/session, with UTF-8 output
on Windows. Do not put tokens in command lines or Git. These commands accept no date
override and no fixture/source substitute:

```powershell
python -m src.phase_c
python -m src.phase_c --profiles path/to/reviewed-local-profiles.json
python -m src.phase_c --profiles path/to/reviewed-local-profiles.json --execute
```

Dry run reads current Drive readiness, machine information and configured workers'
discovery APIs. It never submits a job. Execute requires suitable measured GPU,
current BUILD_READY, revalidated full Manifest v2, Ep103 and single Thabo Slide 12.
Only `slides[11]` is compiled. Readiness blockers remain in the report. A second
provider may run after the first technically fails; no automatic retries occur.

The persistent `output/phase-c/ep103-slide12/attempt-ledger.json` and exclusive run
lock enforce at most two submissions per provider/four total. A lost acknowledgement,
malformed lifecycle, timeout or abandoned reservation remains unresolved and cannot
authorize a retry. Terminal worker failure or corrupt/missing artifact after explicit
success can authorize one diagnosed retry:

```powershell
python -m src.phase_c --profiles path/to/reviewed-local-profiles.json --execute --retry-provider comfyui --technical-diagnosis "Specific diagnosed terminal technical failure"
```

Never delete/reset the ledger to evade the budget or retry for aesthetics. A stale
lock requires checking outstanding real worker jobs before operator recovery. A
failed router eligibility check may conservatively consume a reservation without
dispatch; reservation count is not proof that inference actually began. Normal
successful execution submits once per configured provider. Shared seed 10312 is
requested only if every participating profile proves seed support; this does not
prove cross-backend pixel determinism or weight identity. Model control remains
unproven until exact underlying weights are compared by the operator.

## Provisional compatibility bridge and composition

The mapping is fixed to material_handoff/material_chain for this one slide:
headline←headline, deck←subheadline, quote←main_visual_phrase,
facts←three takeaway idea values, takeaway←core_argument. Five essential labels map
in supplied order to five chain stages, with empty notes; any other count blocks.
This is an explicit compatibility limitation, not general Manifest routing.
No LLM, truncation or editorial reconstruction is used. Text overflow is a
composition blocker, never a reason to regenerate contextual art.

The prompt includes hero_visual, core_argument, visual_psychology_traits,
preferred_visual_reasoning_family, anti_cliche_guardrail and factual_guardrails,
then locked engraving/text-free/no-portrait constraints. Generators own context only.
Successful PNGs must decode as single-frame, exact dimensions and nonuniform content.
These technical checks cannot prove subject/style suitability or lack of generated
text, faces, logos, anatomical errors or collage: HUMAN REVIEW REQUIRED.

Composition stages the image temporarily under ignored `assets/_phase_c_runtime/`,
uses the existing Milestone 5.2 background asset hook, and cleans the per-run staging
directory even on failure. Existing Thabo renderer/config own #A73528, canonical
portrait, all exact text, footer and 12/20. The provisional art box/exclusions protect
portrait and typography but reduce visible art area; a real candidate must be visually
reviewed for sufficient hero legibility. No visual success is claimed in this run.
The existing optional paper wash is disabled in this asset spec because the hook
applies it after exclusions; this keeps protected portrait pixels identical to the
baseline. An actual offline renderer test checks portrait/footer/counter regions.

## Outputs, tests and current open gates

Reports are `output/phase-c/ep103-slide12/benchmark-report.{json,md}`. Actual successful
candidates add provider subdirectories containing context-art.png, slide-composite.png
and generation-metadata.json. Two completed composites produce a comparison contact
sheet. Reports record real IDs, observed states/duration, dimensions, profiles,
technical QA and composition blockers. Sampled whole-device VRAM is labelled as such;
it is not a process peak. Missing measurements remain null. Binaries are ignored.
No Drive write occurs automatically; an optional temporary-artifact copy is deferred
until successful local results exist. Never upload these as Daily Slides/final Ep103.

Normal tests use deterministic engineering fixtures without Drive, GPU, worker
processes or inference. Opt-in discovery smoke test requires both
`AI_GEOPOLITIC_PHASE_C_LIVE=1` and `AI_GEOPOLITIC_PHASE_C_PROFILES` pointing to the reviewed
configuration. Real inference is exclusively the explicit CLI path above.
Full Windows regression uses the existing ignored `.venv/qa/run_full_qa.py` adapter
for DejaVu/FriBiDi; production Linux/font behaviour is unchanged.
Final full result: 527 passed, 1 skipped (64 new offline checks; the skip is the
explicit opt-in real worker discovery test). Phase A/A.1 and Phase B remain green.

On 2026-10-03 Windows reports Intel HD Graphics 530, driver 31.0.101.2111,
Windows 10 Pro 10.0.19045 and about 15.89 GiB RAM. NVIDIA inspection exits 4
(insufficient permissions), so NVIDIA model/driver/CUDA/VRAM remain unknown.
Targeted searches in the user's Downloads/Documents/Desktop and E:/Dev found no
WanGP/ComfyUI installation/model assets; no known worker listener was found.
Searches are bounded discovery evidence, not an exhaustive proof of absence.
Python 3.14/3.13 are registered; isolated existing QA Python is 3.12.14.
The preflight Python process list can include the preflight/QA processes themselves;
it is not evidence that a generation worker is running.
No worker/dependency/model installation was performed. Only small official source
text references were downloaded into ignored output for API inspection.

The fresh live Drive read returns BUILD_BLOCKED, 2026-10-03, with
AUTOMATION_MANIFEST_MISSING. An earlier read also had SLIDE_DESIGN_NOT_READY; that
status blocker cleared during this run, while no validated manifest was returned.
Zero real submissions, job IDs, contextual-art candidates, final composites or
Drive uploads exist. Suitable hardware, live manifest, installed/reviewed workers
and models/licences must be resolved before real Phase C acceptance. Stop at this
one-slide gate; no Slide 13, 20-slide compiler, UI or publishing is implemented.
