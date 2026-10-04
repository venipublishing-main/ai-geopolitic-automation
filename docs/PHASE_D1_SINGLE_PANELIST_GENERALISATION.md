# Phase D.1 — Single-panelist generalisation

D.1 is deterministic planning and internal synthetic-raster composition only.
It performs zero image generations, provider submissions or quota expenditure.
It does not establish visual quality across panelists or accept a production
carousel. Kai Ep104 Slide 05 fidelity tuning remains closed. D.2 is not started.

## Shared composition authority

`SceneContract` binds the full validated Manifest, selected slide and canonical
configuration. Frozen dataclasses and tuples retain immutable geometry; canonical
JSON strings preserve every original slide field, including optional takeaway
treatments. `to_dict` and strict structural `from_dict` support JSON round trips.
Deserialisation is not readiness permission. The renderer recompiles the full
Manifest and requires the identical contract hash before drawing.

The contract contains:

- Schema version 1, episode/date/slide, panelist/name/accent, Manifest/config hashes.
- Identity grammar, argument family, route/shape/micro-detail/accent tendencies.
- Page-relative hero region; hero-relative square art region and quiet lanes.
- One semantic object per exact essential label: ID, hero-relative zone, structural
  role, importance, related object IDs, annotation side, exact fitted label and leader.
- Portrait side, width fraction, vertical position, canonical file/crop/hash,
  conservative protected upper portrait region, transition and overlap allowance.
- Naturally fitted Anton headline and phrase, serif deck, three exact takeaways,
  deterministic publishing furniture, and the original authoritative slide JSON.

All zones use 0–1 coordinates. Labels are ordered from the Manifest: the first is
the primary emphasis; subsequent roles and links describe diagram reading order.
These roles are **not** inferred factual causation or object recognition. Leaders
terminate at planned semantic-zone centres. No hand-inspected image coordinates,
slide-specific object names, runtime language model or reference lookup are used.

The prompt translates hero-relative zones through the same square contain
transform used by the renderer. The illustration is neither cropped nor stretched.
Portrait preparation retains canonical proportions. Copy is measured using actual
font metrics before rendering; oversized words and exhausted label/copy capacity
block rather than clip, rewrite or stretch glyphs. Capacity is at most eight unique
essential labels. Supported portrait width intentions are explicit 18–26% values
or ranges; ambiguous or out-of-range intentions block.

## Argument grammar and identity grammar

Argument families determine object distribution, route topology, hero proportions,
portrait-side variation and takeaway arrangement. Identity supplies tendencies,
not six fixed templates. The locked `config/layout_presets.json` identity names
and visual logic are validated and included in prompt/config provenance;
`config/characters.json` remains canonical portrait/accent authority.
Neither old `approved_families` nor Phase-1 routing are dispatch targets.

| Panelist | Locked grammar | Shape / micro-detail tendency |
| --- | --- | --- |
| Nora | system_axis | balanced axes / axis ticks |
| Diane Sterling | market_grid | transmission rails / measurement ticks |
| Johan Vosloo | institutional_spine | rectilinear gates / numbered stages |
| Kai Patel | network_mesh | node junctions / repair nodes |
| Thabo Mokoena | burden_ledger | asymmetric pressure / ledger strikes |
| Amari Ndlovu | regional_memory | contour arcs / continuity rings |

The supported premium taxonomy is `system_map`, `evidence_dossier`,
`physical_stack`, `dependency_chain`, `institutional_sequence`, `allocation_flow`,
`regional_pathway`, `feedback_loop`, `comparison_field`, `decision_tree`.
An explicit alias table accepts reviewed natural-language Manifest family names,
including the historical Ep104 combinations. Unknown phrases or new combinations
block; isolated keywords are not used to guess their meaning. Extending the
vocabulary is a reviewed code change.

Headline arrangements are full-width two-tier, compact stacked and left/right
weighted. Phrase treatments include accent block, engraved pull quote, doctrine
strip and hero-integrated callout. Takeaways use three-column rail, numbered
vertical rail or three-node sequence. Synthetic cases cover all six panelists.
Thabo's case deliberately adapts the cost-consequence brief as an offline test
input; it is not a claim of an accepted Thabo production slide. Kai stack versus
feedback loop and Diane allocation versus comparison prove argument variation
within the same identity grammar.

## Ownership and fail-closed behaviour

Generator instructions request illustration only: no typography, labels, furniture,
logos/watermarks, signatures, panelist likeness, neon or literal fluffy cloud.
Text/stamp/sign references in a Manifest illustration brief are semantic concepts,
never permission to generate lettering. Code supplies all exact copy, canonical
portrait, restrained accent, publishing furniture and annotation geometry.
The prompt preserves creative/factual instructions as context; this is not a
semantic interpreter of arbitrary prose. Explicit unsupported ownership commands
block; compliance with more subtle prose remains a required human-review question.

Unknown panelists, invalid full Manifest, unsupported family, invalid canonical
portrait configuration, unrepresentable art commands, ambiguous portrait scale,
excess/duplicate labels and copy/label overflow block. Dual slides return exactly
`DUAL_PANELIST_NOT_SUPPORTED_D1`. There is no call or fallback to Phase-1 renderers.

`premium_hero_qa.py` checks valid PNG, square dimensions 512–4096, nonuniformity,
exact contract/prompt binding and SHA-bound existing content-guard evidence when
provided. It uses the existing `agent_visual_screen` field names. Missing evidence
is explicitly `NOT_INSPECTED_NO_DETECTOR`; negative evidence is rejected, never
manufactured by raster statistics. Semantic placement and prohibited portrait/text
recognition are not mechanically verified. The inspector does not claim OCR or CV.

The renderer repeats mechanical QA and validates contract, prompt, raster and
canonical portrait bindings. It produces only
`INTERNAL_PREVIEW_HUMAN_REVIEW_REQUIRED`; publication is always `BLOCKED_D1`.
Passing mechanical QA does not imply human visual QA or licence/publication approval.
Synthetic raster fixtures prove implementation mechanics, not style fidelity.

The general renderer reuses only neutral C.2 canonical portrait preparation and
C.3 grayscale/engraving preparation. Warm paper, shared ink, glyph-local labels,
deterministic print texture, modest accent and argument-specific routes are retained.
C.2/C.3 proof compilers/layouts and C.4 finish effects are never executed by D.1.
No existing source, config, canonical asset, provider, readiness gate, dependency or
workflow changes. Style authorities remain development references, not runtime inputs.

## Inspection CLI and Ep104 replay

Live inspection keeps today's Africa/Johannesburg readiness gate:

```sh
python -m src.premium_scene_compiler --source drive --dry-run
```

It uses the existing rclone environment and isolated input adapter. Local mode
requires `--rnd-file` and `--slide-design-file`. There is no `--execute` or date
override. All compiler APIs and inspection results have expected generation count
zero; no `GenerationJob` or provider is constructed. Output includes contracts,
prompts, hashes and structured per-slide blockers. Exit 0 means every slide compiled;
exit 1 means any global or per-slide blocker; argument errors exit 2.

On 2026-10-04 the accepted Ep104 Manifest is historical (2026-10-03). The authorised
run uses the existing accepted C.4 readiness snapshot explicitly:

```sh
python -m src.premium_scene_compiler --accepted-snapshot output/phase-c4/Ep104/slide-05/input/readiness.json --dry-run
```

It is labelled `ACCEPTED_SNAPSHOT_HISTORICAL_REPLAY`, with current readiness
`NOT_ASSERTED`, never current `BUILD_READY`. The envelope must claim the previously
accepted READY/BUILD_READY state with no blockers and matching production/source
dates, and its full Manifest is revalidated. This is operator-supplied historical
evidence, not an authenticated production-readiness token or production API.
Manifest canonical SHA-256:
`955c5aad9d28e044f7454032cd811f39bc7eb5fa55798d87e5384b6a6f2e405d`.
The same Manifest is committed as a text-only offline regression fixture.

| Slides | Result |
| --- | --- |
| 1, 20 | Nora / system_map |
| 2 | Nora / evidence_dossier |
| 3 | Kai / physical_stack |
| 5, 6 | Kai / dependency_chain |
| 8 | Johan / decision_tree |
| 9 | Diane / dependency_chain |
| 11, 15 | Johan / institutional_sequence |
| 12 | Diane / allocation_flow |
| 14 | Nora / physical_stack |
| 16 | Amari / regional_pathway |
| 4, 7, 10, 13, 17, 18, 19 | DUAL_PANELIST_NOT_SUPPORTED_D1 |

13 singles compile, seven duals block, exit 1 as expected. No other compile blockers.
Ignored evidence: `output/phase-d1/ep104-dry-run.json` and
`output/phase-d1/preserved-evidence.json`. No carousel is rendered.

## Validation

The D.1 suite patches the constructors of GenerationJob, GenerationRouter,
AIHordeProvider, CloudflareWorkersAIProvider, WanGPProvider and ComfyUIProvider
to fail on instantiation. Network connection, urllib and subprocess execution,
old identity/Kai render entrypoints and C.2/C.3 proof composition entrypoints are
also prohibited. Six synthetic raster tests exercise the general compositor,
determinism, exact copy, canonical portrait ownership and honest pending visual QA.
Bounds tests independently measure every compiled Ep104 copy region and verify
disjoint text zones and protected portrait regions. Tamper/stale raster/QA,
content-guard rejection, malformed inputs, current-date and snapshot boundaries
are tested. All tests are offline and do not require ignored accepted images.

Windows uses the existing ignored `.venv/qa/run_full_qa.py` adapter: bundled DejaVu
fonts replace Linux absolute paths only in the QA process; FriBiDi enables the
same RAQM shaping. An ignored `.venv/qa/d1_cli.py` wraps the same font setup for
inspection. No adapter, DLL, font binary or environment change is committed.
CI/Linux continues to use its existing native fonts/shaping.

Final validation on 2026-10-04:

| Suite | Result |
| --- | --- |
| D.1 targeted | 55 passed |
| C.4 | 34 passed |
| C.3 | 34 passed |
| C.2 | 27 passed |
| Provider/licence regression (contracts, router, local/cloud Phase C, conditional licence, Kai bridge) | 392 passed |
| Full Windows QA | 833 passed, 1 skipped |

The skip is the existing opt-in live worker discovery check. `git diff --check`
passes. All 24 recorded historical evidence file hashes remain unchanged,
including C.2/C.3/C.4 PNGs, proof source/tests/docs, accepted Albedo/previous Flux
artifacts, generation metadata/ledgers and canonical Kai portrait.
No binary files are committed; no dependencies or CI/Linux behaviour change.

**PHASE D.1 SINGLE-PANELIST GENERALISATION ARCHITECTURE ACCEPTED** means
deterministic planning for supported singles. Human visual quality and full-carousel
production remain unaccepted. Architecture acceptance does not authorise D.2 or publication.
