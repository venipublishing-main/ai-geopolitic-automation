# Phase C.4 — final fidelity / colour and detail proof

**PHASE C.4 FINAL FIDELITY PROOF READY FOR HUMAN REVIEW**.
One Ep104 / Slide05 / Kai finishing pass. ZERO generations, provider calls,
GenerationJobs, inference workers or image APIs. Visual parity is NOT CLAIMED.
Human review is authoritative. No further automatic Slide05 optimisation follows
this proof; generalisation is a later, separately authorised project phase.

## Separate finalisation, preserved accepted evidence

`src/fidelity_finish.py` finishes a working copy of the accepted C.3 PNG.
It preserves C.3 composition code, output, reports, typography and macro-layout.
No renderer dispatch, provider, character config, existing font path or runtime
behaviour changes. No new dependencies. C.4 uses Pillow, standard Python and
C.3's pure source-preparation helpers. It never calls `compose_fusion`,
`compose_premium`, the legacy network mesh or Phase C.1 asset plate.

The accepted control is:
`output/phase-c3/Ep104/slide-05/phase3/slide05-phase3.png`, SHA256
`530787d58f9dfd1074ccf89858e610567f01c6d4bf9e73d372b8faf3c0a76672`.
Its copy is `control/slide05-phase-c3-control.png` under the C.4 package.
Accepted source art remains
`output/phase-c1/Ep104/slide-5/albedo-sdxl/ai_horde/context-art.png`, SHA256
`af911721d389f3b6a658d18e3e0ba30f93c48bb041be51a7060bf69255f2288b`.
Canonical Kai remains `assets/characters/kai_patel.png`, SHA256
`bea8bcaf13c94316852b8ee8989540d31e65822d12d83b33465aa01c035ccc48`.

The full accepted Manifest is independently revalidated and pinned by canonical
JSON SHA256 (`sort_keys`, compact separators, UTF-8):
`955c5aad9d28e044f7454032cd811f39bc7eb5fa55798d87e5384b6a6f2e405d`.
Even a valid change to another slide cannot silently replace this snapshot.
The C.3 core pin is
`2f4aadf41cfb4151923a10303191a671b801e2a3a58e7daee8742a1966a73692`;
it covers state, slide, output/art/portrait hashes, accent, geometry and typography.
This binds measured copy/face protection to the reviewed C.3 raster, while allowing
its independent development/Git report supplements. Missing/altered assets,
changed metadata, malformed manifests, path escapes and output aliases fail closed.

## Explicit historical benchmark replay

Client date is 4 October 2026 in Africa/Johannesburg. The user explicitly requests
the same accepted Ep104 Manifest, dated 3 October 2026. C.4 therefore exposes only
`ACCEPTED_EP104_ARTIFACT_REPLAY`, not a fresh production readiness decision.
It requires the recorded READY/BUILD_READY snapshot with no blockers, checks its
fixed date/episode, revalidates all 20 slides and matches the accepted Manifest pin.
The proof preserves the printed date and never claims today's BUILD_READY.

Live readiness remains unchanged and rejects that snapshot on 4 October.
No production clock override or relaxed daily-readiness gate is introduced.
A targeted regression proves the live gate still rejects it while this explicitly
dated, pinned internal proof can finish. C.3 historical reproduction uses a
QA-only fixed clock for comparison, not a new production mode.

## Colour, local engraving and depth

All colour derives from Kai #6540A4. Black structural engraving stays dominant.
Selective violet print separations apply only to inspected midtone surfaces,
78 < luma < 220; paper highlights and dark structural ink retain their role.
Density is non-uniform, not a global purple wash or texture filter.

| Surface | Tint alpha / 255 | Edge gain | Hatch pitch / slope | Hatch alpha | Stipple pitch |
| --- | --- | --- | --- | --- | --- |
| front facade | 100 | .42 | 6 / 0 | 38 | 13 |
| compute | 116 | .30 | 5 / 1 | 33 | 11 |
| cooling | 120 | .34 | 5 / -1 | 31 | 13 |
| power | 110 | .40 | 4 / 2 | 36 | 9 |
| land | 36 | .10 | 10 / -2 | 19 | 17 |

JSON/code record each exact inspected polygon. Dark-edge extraction uses a .85px
blur and caps extra edge darkening at 26. Fine stipple darkening is 13. Tint
deposition varies by ±4. Existing C.3 source engraving and page-phased screen
remain the foundation. Far-background architecture receives a 12/255 paper
release; the foreground's reinforced edges provide depth without photographic
blur or glossy gradients. Open paper stays quiet.

A short selected conduit trace uses accent opacity 190/255. Canonical purple
pigment is recovered from the original Kai crop/cover at strength .68, outside
protected face and copy only. This restores existing clothing/background accents;
it invents no marks, changes no identity geometry and does not colour skin.
Protected facial pixels are exactly identical to C.3, including eyes, nose,
mouth and contour. No reference image supplies portrait identity.

## Finer routing, transition and print furniture

C.3's REMOTE USERS → FIBRE → COMPUTE and COMPUTE → COOLING / POWER / LAND graph,
physical endpoints, leaders and six glyph-local label placements are retained.
Before finishing, only the old route/halo pixels are restored from C.3's exact
pre-route source scene; no type or whole-layout redraw occurs. Trunk width is 2px,
branches and leaders 1px, arrows 7px, terminal radius 4px. A narrow 70% paper
release supports the new line hierarchy without large white fringes.

Every new route, arrow, terminal and selected conduit mask is checked against
the 2px-expanded face and copy protection. Finishing overlays also exclude these
regions, and a final raster difference check proves every protected face and
copy bounding rectangle remains byte-identical. There are no opaque label cards.
Natural fitted Anton type, sizes, exact headline/deck/phrase, three takeaway ideas,
footer and 05/20 remain intact. No glyph raster stretching or copy rewriting.

Technical finish uses small ruler ticks, registration crosses, terrain arcs,
object brackets, shoulder hatch, rail hatch and sparse phrase-edge ink loss.
Marks contain no generated prose, values, coordinates, telemetry or fake facts.
Registration offsets are at most 2px; added marks are low contrast and local.
The shoulder bracket/hatch shares the infrastructure print field while keeping
the protected face clear. Fine rail fragments and phrase-edge distress tie the
existing macro hierarchy together. This is a finish, not a redesigned composition.

## References and ignored output package

The current Drive primary reference was metadata-checked with the existing rclone
session: file `1jLaocNFP31PQvXmOAZNDSyjzmkbjaQO4`,
`Manual - ChatGPT + Instagram/Daily Operations/Daily Slides/Slide05of20.png`.
It is still the same Ep104 final (modified 3 October), so its previously verified
bytes were copied into this package. The historical character-specific reference
is **CLEAR RIVERS NEED OPERATING MEMORY**, Drive
`1mRRuboHP9VVcftljZ9X7lJ1oPhAsbpS9`. Both, and C.3, were visually inspected for
print separation, physical dependency illustration, connected-node grammar and
finish. No reference pixels are composited. No reference is read at runtime.

```text
output/phase-c4/Ep104/slide-05/
  reference/Slide05of20-current-final.png
  reference/kai-historical-exemplar.png
  control/slide05-phase-c3-control.png
  input/context-art.png
  input/readiness.json
  phase4/slide05-phase4.png
  report/fidelity-report.json
  report/fidelity-report.md
```

Raster/input/report packages stay ignored under the existing output rule.
JSON records source/portrait/control/output hashes, pinned Manifest/core,
geometry, protection, native typography, all finish parameters, graphical
primitives, development-only references and zero provider/generation counts.
The original Albedo licence audit/creator credit are retained. Public attribution
delivery remains **BLOCKED**; metadata is not public credit and no publication
occurs. No claim of parity or automatic human approval.

## Invocation and verification

```text
python -m src.fidelity_finish --accepted-snapshot <local-accepted-Ep104-snapshot.json>
```

The CLI is local only: proof status / exit 0 or structured BLOCKED / exit 1.
Windows uses the unchanged ignored `.venv/qa` FriBiDi/RAQM/DejaVu adapter.
Linux and existing production behaviour remain unchanged.

Tests use real Ep104 copy and canonical Kai, with synthetic hero/acceptance records
and pins explicitly overridden only in fixtures. Production pins are separately
asserted. Coverage includes exact copy/layout, face/copy/furniture pixel identity,
no clipping, valid PNG, local non-uniform detail, object-anchored safe routing,
graphical-only microdetail, immutable/reproducible C.3, deterministic C.4,
provider/job/network/legacy/reference exclusion, fixed-date replay versus live
readiness, altered/malformed inputs, canonical identity, path/alias safety,
blocked publishing, CLI exits and report provenance.

Actual raster deltas must occur in hero surfaces, accent systems, the portrait
transition and the technical microdetail strip. Accent coverage increases relative
to C.3 while neutral dark structure remains dominant. These are mark-language and
layer-execution sanity checks, not beauty metrics or optimisation targets.

Required validation sequence completed: C.4 targeted → C.3 → C.2 → full Windows
QA → `git diff --check`. This is the last automatic Slide05 finish; stop for
human review.

The final raster was produced once and visually inspected. Its SHA256 is
`af930237f1df7d85d7906c76998b4cb377b844a840d5becd32acd4501b53e930`.
Subsequent work verifies the artifact and reports; it does not run another visual
optimisation iteration. Protected face/copy pixel checks passed on the real PNG.
The real C.3 reproduction matched its accepted hash, with a QA-only historical
clock, and all 19 checked prior code/raster/report/metadata/ledger files remained
unchanged. The original C.3 output and reports were not overwritten.

Measured hero-region accent pixels increased from 18,182 to 20,032; C.4 retains
136,392 neutral dark pixels. Changes exceeding six channel levels occur in
7,788/57,750 hero-surface pixels, 5,795/51,150 accent-system pixels,
2,828/7,347 transition pixels and 192/7,488 microdetail-strip pixels. These are
recorded observations of layer execution, not visual-fidelity percentages.

Final validation:

- C.4 targeted: **34 passed in 72.79s**.
- C.3: **34 passed in 23.71s**.
- C.2: **27 passed in 4.01s**.
- Full Windows QA: **778 passed, 1 skipped in 200.19s**. The existing skip is
  opt-in real localhost worker discovery; normal tests launch no models.
- Working and staged `git diff --check`: clean.

The engineering commit/push records implementation completion only. Human
visual approval remains pending; the raster/report package remains ignored.
