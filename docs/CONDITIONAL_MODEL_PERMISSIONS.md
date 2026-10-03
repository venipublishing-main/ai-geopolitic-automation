# Conditional model permissions — unpublished Phase C benchmark

`PermissionState` distinguishes UNKNOWN, PROHIBITED, ALLOWED and
ALLOWED_WITH_OBLIGATIONS. Unknown/prohibited permissions still block dispatch.
Commercial permission, attribution certainty and evidence are separate facts;
conditions do not make proven commercial permission unknown.

The neutral job adds `UseRequirements`: INTERNAL_BENCHMARK or PRODUCTION_PUBLISH,
an explicit NON_PERSONAL_INFRASTRUCTURE use case, and obligation recording.
Existing registry entries without an explicit permission state retain their
established legacy behaviour. New conditional entries cannot use the legacy
`output.attribution_allowed` flag as a public credit surface.

For internal infrastructure illustration, recognised Attachment A restrictions
remain recorded. Medical advice, personal profiling and legal/law-enforcement
decisioning are excluded by the declared task scope. Other content/legal
restrictions remain HUMAN_REVIEW_REQUIRED, not automatically compliant. Unknown
restrictions and unsupported purposes/reference edits fail closed. No real-person
generation, decisioning or harmful personal-data use is authorised by this scope.

An attribution-required conditional entry requires creator, credit text, HTTPS
permission/licence evidence, commercial permission and explicit recording.
Production use is BLOCKED while a publicly appropriate attribution surface is
unconfigured. Hidden JSON/logs do not satisfy public attribution. No publishing
UX or public-credit implementation is introduced.

## Exact checkpoint evidence

AlbedoBase XL 3.1 / Civitai model 140737 / version 1041855 is bound to
`albedobaseXL_V31Large.safetensors`, SHA256
`C379D154EB476B67B390E31463C41C79AC9E766466315408886EBB7FAA2EA098`.
The [exact Horde reference](https://models.aihorde.net/api/model_references/v2/image_generation/model/AlbedoBase%20XL%203.1)
matches the [Civitai version](https://civitai.com/api/v1/model-versions/1041855).
The [author record](https://civitai.com/api/v1/models/140737) identifies albedobond,
`allowNoCredit=false`, and commercial Image/RentCivit/Rent uses. Derivatives are
allowed; different licensing is not. This task distributes no weights, sells no
model, and infers no permissions from older versions. Credit is conservatively
required for images: “Context illustration generated with AlbedoBase XL 3.1 by
albedobond.” Exact public delivery remains unresolved and blocked.

Both Albedo and the metadata-only SDXL 1.0 fallback retain the
[CreativeML Open RAIL++-M licence](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/main/LICENSE.md)
and its eleven Attachment A use restrictions. An empty restrictions array in the
reference licence definition does not erase Attachment A. The base licence
claims no rights in generated output, subject to its use conditions; it is not a
blanket prohibition on commercial outputs. Model redistribution has additional
licence/notice obligations and is outside this benchmark.

The router and direct cloud submit path share one policy function. Zero-cost,
resources, exact model selection, provider priority and no post-dispatch fallback
remain in place. Authoritative obligations propagate through GenerationResult
data, generation metadata, JSON/Markdown reports and a BLOCKED future publication
handoff. They are never generated onto the raster.

## One Albedo benchmark

```powershell
python -m src.phase_c_cloud --horde-profile albedo-sdxl --slide 5
# Only after targeted tests, full Windows QA and live dry run all pass:
python -m src.phase_c_cloud --horde-profile albedo-sdxl --slide 5 --execute
```

This profile is restricted to current BUILD_READY Ep104 / 2026-10-03 / Slide05 /
KAI_NETWORK_MESH and Horde alone. Its independent package and durable one-attempt
ledger are `output/phase-c1/Ep104/slide-5/albedo-sdxl/`. No diagnosis can authorise
a second attempt. The earlier rejected Flux artifact/ledger remain intact.
SDXL 1.0 is registered only as a reviewed fallback candidate; no profile or
automatic fallback dispatch is provided.

The prepared positive prompt uses live hero/guardrails and physical infrastructure,
without the deterministic “cloud” quote. Horde's supported `positive###negative`
syntax supplies separate SDXL CLIP conditioning; CFG 7.5, 30 steps, Euler ancestral,
Karras and seed 1234567890 come from the official SDXL-family tutorial, not a claim
of exact-checkpoint author recommendations. Fixed seed does not promise identical
pixels across workers. Default Flux sampling remains unchanged.

Composition is always deferred. Inspect for text/pseudotext, signatures/watermarks,
logos, literal fluffy clouds, neon/cyberpunk, poster/contact-sheet layout and
generated panelist identity. Failure preserves the asset and returns
FREE_HORDE_MODEL_QUALITY_GATE_UNMET; never crop markings or regenerate. A passing
asset may produce one internal candidate through the existing compositor. Human
visual review and deliberate public-credit configuration remain required before
production publishing. No final 20-slide provider acceptance is implied.

## 2026-10-03 live result

Live dry run: READY / BUILD_READY, Ep104, 20 validated slides, Slide05 /
KAI_NETWORK_MESH, healthy exact AlbedoBase XL 3.1, ZERO_COST,
ALLOWED_WITH_OBLIGATIONS, internal credit recorded, one predicted generation,
zero blockers and zero attempts before dispatch. Actual SAST date; no override.

Exactly one job was submitted: `2d75ba3f-3c3e-4097-998b-5298ce2c9649`, returned
generation `75ec3249-0ca4-4a78-b937-1f408d1ff8cc`, worker AstralWeaver
(`8f13e7eb-1950-4a55-925a-e875980aef90`), requested/returned seed 1234567890.
Observed queue duration 928.875s, processing 13.766s, total through artifact QA
946.422s; these are polling bounds, not worker instrumentation. No retries or
fallback dispatch occurred. Returned image: nonuniform 1024-square PNG.

Agent visual screening found no discernible forbidden text/pseudotext,
watermark/signature, logo, fluffy cloud/icon, neon/cyberpunk, poster/contact-sheet
layout or generated panelist likeness. Appearance is a lighter architectural/CAD
illustration rather than dense newspaper engraving: human quality review remains
required. The asset was not cropped or repaired to pass the screen.

One internal 1080-square Slide05 candidate was composed through the existing
Milestone 5.2 hook. A fresh live Manifest read matched the generation snapshot.
Protected portrait, copy/quote, facts, header/counter, mesh foreground and footer
regions match the deterministic baseline pixel-for-pixel. Renderer/assets/fonts
are unchanged; Windows QA uses the existing ignored DejaVu/FriBiDi adapter.
No production publication or Drive upload was performed. Future public-credit
delivery remains BLOCKED.

Artifact SHA256:
`af911721d389f3b6a658d18e3e0ba30f93c48bb041be51a7060bf69255f2288b`.
Composite SHA256:
`0153447add74a2b42c543d357ce1d72b08aee2bfe464f06bb528b5cf4b91722f`.
Artifacts, credit-bearing metadata, reports, scoped ledger and lifecycle evidence
remain in the ignored package named above. Prior rejected Flux evidence is
unchanged.

Targeted routing/cloud/Kai/licence suite: 249 passed. Conditional-licence suite:
22 passed after requested-seed audit correction. Full Windows QA: 683 passed,
1 skipped (opt-in local-worker discovery), before dispatch and again during the
queue. A further full run is required after the acceptance commit before push.

PHASE C FREE-CLOUD SINGLE-PROVIDER VERTICAL SLICE ACCEPTED

HUMAN VISUAL QUALITY REVIEW STILL REQUIRED
