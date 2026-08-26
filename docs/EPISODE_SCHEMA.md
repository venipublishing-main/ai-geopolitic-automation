# AI Geopolitic Production Episode Schema — v1

Milestone 4.5 introduces the daily inline episode format. The production manifest contains **exactly 20 slides** and no longer points at test-fixture `source_input` files.

## Top-level fields

```json
{
  "schema_version": 1,
  "episode_id": "filesystem-safe-lowercase-slug",
  "episode_title": "APPROVED EPISODE TITLE",
  "episode_date": "25 AUGUST 2026",
  "slides": []
}
```

## Slide fields

Every slide contains the editorial copy directly:

```json
{
  "speaker": "kai_patel",
  "content_type": "monitoring_cycle",
  "headline": "...",
  "deck": "...",
  "quote": "...",
  "facts": ["..."],
  "takeaway": "...",
  "visual": {
    "monitors": []
  }
}
```

`layout_override` is optional. Use it only when an editor intentionally wants a different approved family for that speaker.

Do **not** put `slide_number`, `total_slides`, `layout_family`, `source_input`, or `content_overrides` in a production slide. Those are compiler-owned or legacy proof fields. Slide order in the JSON array is canonical.

Slide 1 must route to NORA `episode_opener`; slide 20 must route to NORA `episode_closer`; slides 2–19 cannot use either full-header layout.

## Routing and visual payload reference

The router maps `speaker + content_type` to an approved layout family. Layout-specific structured data belongs under `visual`.

| Speaker | Content type | Layout family | `visual` keys used by current renderer |
|---|---|---|---|
| `amari_ndlovu` | `cross_border_connection` | `cross_border_bridge` | `bridge` |
| `amari_ndlovu` | `cultural_context` | `cultural_landscape` | `landscape` |
| `amari_ndlovu` | `dignity_continuity` | `dignity_pathway` | `mechanism` |
| `amari_ndlovu` | `humanitarian_geography` | `humanitarian_map` | `map_nodes` |
| `amari_ndlovu` | `regional_continuity` | `regional_memory` | `mechanism` |
| `diane_sterling` | `fiscal_allocation` | `fiscal_flow` | `flows`, `total` |
| `diane_sterling` | `market_dashboard` | `market_grid` | `mechanism`, `metrics` |
| `diane_sterling` | `investment_pipeline` | `portfolio_pipeline` | `mechanism`, `portfolio` |
| `diane_sterling` | `regional_market` | `regional_economy` | `regions` |
| `diane_sterling` | `economic_transmission` | `transmission_chain` | `stages` |
| `johan_vosloo` | `governance_handoff` | `containment_chain` | `mechanism` |
| `johan_vosloo` | `institutional_sequence` | `institutional_spine` | `mechanism` |
| `johan_vosloo` | `order_pathway` | `order_corridor` | `mechanism` |
| `johan_vosloo` | `oversight_checkpoint` | `oversight_gate` | `mechanism` |
| `johan_vosloo` | `principle_check` | `principle_test` | `tests` |
| `kai_patel` | `distributed_delivery` | `decentralised_pathway` | `routes` |
| `kai_patel` | `system_feedback` | `feedback_system` | `mechanism` |
| `kai_patel` | `monitoring_cycle` | `monitoring_loop` | `monitors` |
| `kai_patel` | `distributed_system` | `network_mesh` | `mechanism` |
| `kai_patel` | `repair_cycle` | `repair_network` | `repair_steps` |
| `nora` | `diagnostic_comparison` | `diagnostic_matrix` | `matrix` |
| `nora` | `episode_close` | `episode_closer` | `mechanism` |
| `nora` | `episode_open` | `episode_opener` | `mechanism`, `question` |
| `nora` | `feedback_cycle` | `feedback_loop` | `mechanism` |
| `nora` | `systems_synthesis` | `system_axis` | `mechanism` |
| `thabo_mokoena` | `burden_distribution` | `burden_ledger` | `mechanism` |
| `thabo_mokoena` | `pressure_over_time` | `continuity_pressure` | `pressure_steps` |
| `thabo_mokoena` | `material_handoff` | `material_chain` | `chain` |
| `thabo_mokoena` | `class_gap` | `structural_gap` | `gaps` |

## Daily use

1. Copy `inputs/production-episode-template.json`.
2. Change `episode_id`, `episode_title` and `episode_date`.
3. Replace the 20 slide copy blocks with the approved R&D/content plan.
4. Keep `speaker` and `content_type` within the routing vocabulary above, or use a valid `layout_override`.
5. Put family-specific diagram/map/network data in `visual`.
6. Run the production-schema workflow. Validation happens before any upload to Drive.

The current template intentionally contains known-good test content so it remains structurally valid while being edited. Milestone 5 will replace this proof content with a real approved daily episode.

## Contextual illustration payload — Milestone 5.2

Production slides may optionally include `visual.context_art`. Context art never owns headline/body copy or presenter identity; it is a composited illustration layer only.

```json
{
  "visual": {
    "context_art": {
      "source": "procedural",
      "kind": "river_monitoring",
      "box": [420, 520, 945, 875],
      "layer": "foreground",
      "opacity": 0.4,
      "paper_wash": false,
      "exclusions": [[625, 625, 800, 795]]
    }
  }
}
```

The compiler validates the illustration specification before rendering. Invalid kinds, unsafe boxes, invalid layers and asset paths outside `assets/` fail the run.

See `docs/CONTEXTUAL_ILLUSTRATION.md` for the complete contract and current proof kinds.
