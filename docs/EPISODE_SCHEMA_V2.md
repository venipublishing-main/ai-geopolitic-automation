# Episode Manifest v2 — Phase A automation handoff

The v2 manifest is the strict machine-readable handoff from upstream ChatGPT
automation to daily readiness validation. It does not replace the Milestone 4.5
v1 rendering schema. The existing renderer, deterministic layout families,
canonical portraits, fail-closed routing, and Milestone 5.2 `visual.context_art`
hook remain intact. Phase A does not convert v2 into v1 or render v2 slides.

The authoritative validator is `src/episode_manifest_v2.py`. Unknown fields are
rejected, including `layout_family`; future extensions need a deliberate contract
update. No LLM interprets or repairs a manifest.

## Envelope

All these fields are required:

| Field | Contract |
|---|---|
| `schema_version` | Integer `2`; strings, floats, booleans and v1 are rejected |
| `episode_id` | Nonblank identifier, 1–80 characters: letters/digits then letters/digits/`.`/`_`/`-`; exact identity match across sources |
| `episode_title` | Nonblank string; exact title match across source metadata |
| `production_date_sast` | Valid `YYYY-MM-DD`, matching both documents and the current SAST day |
| `source_rnd_date_sast` | Valid `YYYY-MM-DD`, matching Daily R&D and the Slide Design source date |
| `archive_destination` | Nonblank human archive path; exact match across documents |
| `archive_folder_id` | Nonblank Drive ID using letters/digits/`_`/`-`, not a URL |
| `slides` | Exactly 20 objects in canonical order |

Archive validation checks declared identity and ID syntax; it does not query Drive
to prove that the archive folder exists or that its path resolves to that ID.

## Slide fields

Every field below must be present, including fields that allow null for a single
panelist. Numbering must be the integers 1 through 20 in array order; no coercion,
sorting, renumbering, duplicates or gaps are allowed.

| Field(s) | Type and validation |
|---|---|
| `slide_number` | Integer equal to the slide's 1-based array position |
| `panelists` | Array of one or two distinct canonical slugs |
| `pairing_mode` | Null for single; an approved string for dual |
| `shared_ground` | Nonblank description for dual; null or empty string for single |
| `panelist_contributions` | Object keyed by panelist slug, with nonblank contribution strings; exactly both keys for dual; null, `{}`, or the single panelist's key for single |
| `central_relationship` | Nonblank editorial description connecting the contributions for dual; null or empty string for single |
| `why_dual` | Nonblank explanation for dual; null or empty string for single |
| `slide_role`, `core_argument`, `headline`, `subheadline` | Nonblank strings |
| `hero_visual`, `main_visual_phrase` | Nonblank strings |
| `essential_labels` | Nonempty array of nonblank strings |
| `takeaway_ideas` | Exactly three objects, each with nonblank `idea` and optional nonblank `intended_visual_treatment`; no other entry keys |
| `accent_colours` | Object mapping exactly the slide's panelist slugs to canonical hex accents (hex case insensitive) |
| `factual_guardrails` | Nonempty array of nonblank strings |
| `composition_notes` | Nonblank string |
| `visual_psychology_traits` | Nonempty array of nonblank strings |
| `notices_first`, `preferred_visual_reasoning_family` | Nonblank strings |
| `anti_cliche_guardrail`, `portrait_scale_intention`, `density_type_size_note` | Nonblank strings |

`central_relationship` is descriptive text, not a second enum. Phase A validates
its presence and type; it does not use inference to assess editorial meaning.
`preferred_visual_reasoning_family` is an editorial brief, not a forced v1
`layout_family` route. No extra NORA opener/closer constraints are imposed on v2.

## Panelists and pairing

Valid slugs are `nora`, `diane_sterling`, `johan_vosloo`, `kai_patel`,
`thabo_mokoena`, and `amari_ndlovu`. Validation reads keys and accent colours from
the existing `config/characters.json`; no second character registry is introduced.

Approved dual pairing modes:

- `SUPPORTIVE_CONVERGENT`
- `OPPOSING_FACE_OFF`
- `QUALIFIED_TENSION`
- `SYNTHESIS_COMPLEMENTARY`

Single example (fragment):

```json
{
  "panelists": ["nora"],
  "pairing_mode": null,
  "shared_ground": null,
  "panelist_contributions": {},
  "central_relationship": null,
  "why_dual": null,
  "accent_colours": {"nora": "#1769AA"}
}
```

Dual example (fragment):

```json
{
  "panelists": ["diane_sterling", "johan_vosloo"],
  "pairing_mode": "SYNTHESIS_COMPLEMENTARY",
  "shared_ground": "Delivery requires an accountable handoff.",
  "panelist_contributions": {
    "diane_sterling": "Trace the resource allocation.",
    "johan_vosloo": "Identify the accountable owner."
  },
  "central_relationship": "Resource allocation and accountability explain the same handoff.",
  "why_dual": "Both explanations are needed to assess delivery.",
  "accent_colours": {"diane_sterling": "#176B4A", "johan_vosloo": "#173C68"}
}
```

The complete 20-slide example is
`tests/fixtures/daily_readiness/slide_design_valid.txt`. It includes single and
dual slides, all six canonical panelists, and every required slide field.

## Exact JSON handoff

The human-readable Daily Slide Design remains. Upstream ChatGPT automation will
eventually also populate this literal block in that document:

```text
=== BEGIN AUTOMATION MANIFEST JSON ===
{ valid JSON conforming to the complete v2 contract }
=== END AUTOMATION MANIFEST JSON ===
```

Each marker must be a standalone literal line and occur exactly once in the
entire document. The block may be inside the daily payload or elsewhere in the
document. Its contents must be JSON alone: no Markdown fence, comments, trailing
commas, duplicate keys, `NaN` or `Infinity`. Missing, ambiguous, malformed,
unsupported or metadata-inconsistent handoffs block BUILD. Human slide prose is
never translated heuristically into machine fields.
