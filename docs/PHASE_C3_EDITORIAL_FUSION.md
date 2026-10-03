# Phase C.3 — editorial fusion proof

One internal Ep104 / 2026-10-03 / Slide05 / Kai proof. Status:
**PHASE C.3 EDITORIAL FUSION PROOF READY FOR HUMAN REVIEW**.
No visual parity or production acceptance is claimed. Human review decides that.
ZERO generations, GenerationJobs, provider calls or inference workers. The
original accepted Albedo raster is reused byte-for-byte as input.

## Separate composition path

`src/editorial_fusion.py` owns C.3 composition and reports. C.2's
`src/premium_compositor.py`, tests and documentation remain unchanged and its
original output is retained as the comparison control. C.3 reuses C.2's pure
full-readiness/Manifest compiler, accepted-art/attribution validator, canonical
aspect-preserving portrait crop, perimeter mask and measured text-record guard.
It never calls C.2 composition, the legacy network mesh, Phase C.1 asset plate,
provider/router/job code, Drive or reference images. Existing renderer dispatch
and production behaviour are unchanged. Pillow and standard Python are sufficient.

The pure compiler requires current BUILD_READY, an entirely valid 20-slide v2
Manifest, Ep104 / 2026-10-03, single Kai on 05, null pairing, six exact labels and
canonical portrait/accent from `config/characters.json`. Copy is mapped without
rewriting. Missing/substituted/unapproved art, incorrect credit, path escapes,
input/output aliasing, overlong copy and protected-region route intersections
fail before saving the output. The accepted art digest is:

`af911721d389f3b6a658d18e3e0ba30f93c48bb041be51a7060bf69255f2288b`.

## Common ink and retained macro hierarchy

Hero [380,360,1038,890], portrait [42,354,409,852], headline
[42,116,1038,301], phrase [42,747,455,885] and the three bottom columns
retain C.2's hierarchy. Hero centre alpha is 255; feathering is perimeter-only.
The hero remains the accepted campus illustration, not a redrawn silhouette.
Canonical Kai receives crop/cover once, with no face warp, synthesis or invented
identity/clothing. Screen and tone changes do not alter geometry.

Both sources pass through `prepare_editorial_engraving`: grayscale/autocontrast
cutoff 0.4, controlled contrast, unsharp radius 1.1 / 80% / threshold 3,
gamma, dark-edge preservation with radius 1.2, and INK-to-PAPER mapping.
Hero contrast/gamma/edge strength: 1.26 / 1.12 / 0.65. Portrait: 1.06 / 1.04 /
0.22. Midtones 58..214 receive a restrained 5px dot / 11px diagonal hatch screen;
darkening strengths are 16 and 10. Fine deposition varies ±3. All screen phases
use absolute page coordinates, so both sources share one print field.

Paper uses the existing deterministic fibre/grain helper. Microdetail contains
only faint grid, small ticks/crosses, site construction arcs and shoulder hatch.
No semantic text, coordinates, figures, telemetry, company names or fake data.
Microdetail excludes protected face [90,365,378,743]. Its shoulder marks, paper
release and the incoming route beside the portrait join portrait and campus.
No route or callout crosses the protected face or measured copy bounds.

The six labels use actual glyph-local 1px paper knockout and small leaders/nodes,
not six opaque rectangles. Purple #6540A4 carries headline emphasis, routes,
phrase, labels and numbering; neutral black remains the dominant campus ink.
The phrase has irregular 0..2px engraved edges, shared ±3 deposition, connected
rules and native fitted type. The takeaway rail uses three exact ideas, prominent
native-font 01/02/03 and restrained micro-rules. Masthead/full date/Ep104/05/20,
serif deck, core argument and exact motto remain code-authored and protected.

L0 paper/grid → L1 hero engraving → L2 portrait engraving → L3 dependency routes
→ L4 labels → L5 headline/phrase/rail → L6 publishing furniture. A faint
construction overprint around released edges precedes routes; it excludes face.

## Inspected one-slide anchors

These coordinates refer only to the accepted Albedo raster after cover crop,
not a general computer-vision solution. Original source is 1024×1024; crop is
x=0..1024 / y≈99.57..924.43, scaled uniformly to 658×530 at [380,360].
Coordinates identify illustrative zones, not verified equipment specifications
or claims about a particular real campus. In particular the land point is on
exposed ground, not a small roof; cooling does not assert a fixed water footprint.

| Label | Page endpoint | Source point | Inspected feature |
| --- | --- | --- | --- |
| REMOTE USERS | 492,453 | 175,245 | off-site road / incoming connection margin |
| FIBRE | 576,599 | 305,472 | incoming horizontal conduit at campus edge |
| COMPUTE | 852,622 | 735,507 | central service / equipment building zone |
| COOLING | 625,538 | 381,377 | cylinders and connected pipe plant |
| POWER | 962,401 | 906,164 | rear electrical switchyard / busbar zone |
| LAND | 920,802 | 840,787 | site ground outside the building footprint |

The graph is REMOTE USERS → FIBRE → COMPUTE, then COMPUTE → COOLING / POWER /
LAND. Paths follow inspected scene zones. Every semantic stroke, arrow wing,
leader and terminal node is included in a mask tested against a 2px expansion
of protected facial and measured text regions. JSON records all polyline nodes,
label boxes/leaders and bounds. No generic five-node mesh or decorative circuitry.

## Natural display type

C.3 uses the locally vendored unmodified Anton Regular (170,812 bytes), plus its
SIL OFL 1.1 license, solely for display type. Source:
[Google Fonts Anton](https://github.com/google/fonts/tree/main/ofl/anton).
Font SHA256:
`a4ba3a92350ebb031da0cb47630ac49eb265082ca1bc0450442f4a83ab947cab`.
Vendoring makes this path independent of network and OS-installed display fonts.
Native font sizing retains glyph proportions; there is no glyph raster resizing.
Fine deterministic pinholes use modulus 311 / attenuation 125. Body copy reuses
DejaVu. Actual per-element sizes and font names appear in JSON. C.2's font loader
and all existing font/renderer configurations are unchanged.

## Development references and ignored comparison package

The existing authorized rclone session metadata-resolved and downloaded:

- Primary current final: Drive `1jLaocNFP31PQvXmOAZNDSyjzmkbjaQO4`,
  `Manual - ChatGPT + Instagram/Daily Operations/Daily Slides/Slide05of20.png`.
- Historical **CLEAR RIVERS NEED OPERATING MEMORY**: Drive
  `1mRRuboHP9VVcftljZ9X7lJ1oPhAsbpS9`,
  `History - Episode List/Ep029-20July2026/file_000000007a8881f4af4e455bd93dd159.png`.

Both were visually inspected for the authored-plate / illustration-as-diagram
principle. Historical feedback-loop/connected-node grammar informs the current
dependency routing; no river copy, identity pixels, stock icons or reference
rasters enter composition. `runtime_reference_dependency = false`.

Everything below remains ignored under the existing `output/*` rule:

```text
output/phase-c3/Ep104/slide-05/
  reference/Slide05of20-current-final.png
  reference/kai-historical-exemplar.png
  control/slide05-phase-c2-control.png
  input/context-art.png
  input/readiness.json
  phase3/slide05-phase3.png
  report/fusion-report.json
  report/fusion-report.md
```

The input is a byte-identical copy of
`output/phase-c1/Ep104/slide-5/albedo-sdxl/ai_horde/context-art.png`.
The control is a byte-identical copy of
`output/phase-c2/Ep104/slide-05/premium/slide05-premium.png`
(SHA256 `12b9f51c53eeb71ef6f2ce4621fb427aeb9828c74ef1dcfdd64662999f43908d`).
Source C.1/C.2 evidence is preserved, including rejected Flux evidence/ledgers.
Current Drive readiness was refreshed without a date override: BUILD_READY,
Ep104 / 2026-10-03 / 20 validated slides. Only slide 05 is composed.

The Albedo audit, creator credit and restrictions remain in the C.3 reports.
**Public attribution delivery remains BLOCKED**; internal metadata is not a
public credit surface. No upload or publication is performed.

## Invocation and verification

```text
python -m src.editorial_fusion --readiness <current-local-readiness-json>
```

The CLI reads local inputs only and emits a structured BLOCKED error / exit 1
or the human-review proof status / exit 0. Windows uses the already existing,
ignored `.venv/qa` FriBiDi/RAQM and DejaVu adapter; no production or Linux font
path changes. The new Anton is repo-local on both OSes.

Targeted tests cover exact copy/canonical input/1080 PNG, measured clipping and
collisions, native font sizes, shared ink preparation, unwarped geometry, opaque
and detailed hero, sparse glyph knockouts, meaningful graph, actual route pixel
protection, graphical-only microdetail, restrained accent/neutral ink, offline
composition, provider/job/legacy exclusion, all input gates, path/alias protection,
CLI exits, report/credit and ignored rasters. Synthetic acceptance is confined to
fixtures with an explicitly monkeypatched digest; production retains its pin.
Identity checks use the actual canonical Kai PNG; fixtures use the real Ep104 copy.

Repeated C.2 composition from identical inputs must remain byte-identical before
and after C.3. C.3 must be deterministic and alter hero, portrait/hero boundary,
callout and sparse microdetail regions. Pixel-change occupancy tests demonstrate
that layers run; they are not visual-quality scores. Ablating microdetail also
changes its expected strip and shoulder regions independently of macro-layout.

Required validation sequence completed:

- C.3 targeted: **34 passed in 22.45s**.
- All C.2 compositor tests: **27 passed in 4.01s**.
- Full Windows QA: **744 passed, 1 skipped in 109.32s**. The existing skip is
  opt-in local-worker discovery; no inference is performed.
- `git diff --check`: clean.

The real accepted-input C.2 reproduction also matched its original PNG digest.
All 12 checked prior code/output/metadata/ledger hashes remained unchanged.
Actual C.3 comparisons changed 23,814/35,000 hero pixels, 14,530/25,175 boundary
pixels, 76,487/118,188 callout-zone pixels and 245/6,912 sparse microdetail-strip
pixels by more than six channel levels. These prove local layer execution, not
beauty. The hero detail sample retained 216 luma levels; measured hero pixels
included 142,022 neutral dark and 18,182 purple accent pixels. JSON records these
observations and the exact regions rather than claiming a visual-quality score.

Human review remains pending after the engineering push. No other slide,
panelist, generation or Phase D is authorized by this proof.
