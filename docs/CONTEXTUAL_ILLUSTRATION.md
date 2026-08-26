# AI Geopolitic Contextual Illustration Layer — Milestone 5.2

Milestone 5.2 exists because the Ep029 benchmark proved that layout correctness alone is not enough. The automated slides are readable and coherent, but the handcrafted reference episodes still have substantially stronger contextual illustration, iconography and visual storytelling.

The illustration layer therefore stays **separate from exact typography and locked presenter identity**.

## Architectural rule

Code continues to own:

- exact copy;
- typography;
- presenter portrait placement;
- accent colour;
- slide number and frame;
- safe margins;
- footer;
- routing and QA.

Contextual illustration is an optional composited layer described by `visual.context_art`.

This is important because a future local RTX 3080, NVIDIA endpoint or other image generator can replace the current procedural proof without giving the image model control of text or presenter identity.

## `visual.context_art` contract

Example procedural illustration:

```json
{
  "visual": {
    "context_art": {
      "source": "procedural",
      "kind": "water_infrastructure",
      "box": [455, 520, 945, 875],
      "layer": "foreground",
      "opacity": 0.42,
      "paper_wash": false,
      "exclusions": [
        [615, 600, 815, 660],
        [585, 660, 845, 718]
      ]
    }
  }
}
```

Future raster/generated asset:

```json
{
  "visual": {
    "context_art": {
      "source": "asset",
      "path": "assets/.../approved-context-art.png",
      "box": [455, 520, 945, 875],
      "layer": "background",
      "opacity": 0.72,
      "tint": "ink_accent"
    }
  }
}
```

Milestone 5.2 does **not** create a new illustration-assets folder yet. The `asset` hook is only the interface contract for a later generation backend. Any new permanent asset directory must be discussed before it is introduced.

## Fields

### `source`

- `procedural` — deterministic Pillow line art; no inference/API cost.
- `asset` — repository illustration file under `assets/`; intended for a later local/API generation backend.

### `kind`

Required for `procedural` source.

5.2 proof kinds:

- `casefile_system`
- `water_infrastructure`
- `river_monitoring`
- `mineworker_claims`
- `care_pathway`
- `oil_market`

### `box`

Absolute 1080×1080 slide coordinates `[x0, y0, x1, y1]`.

The compositor rejects boxes outside the protected editorial content area.

### `layer`

- `background` — composited before the layout foreground.
- `foreground` — composited after the renderer has produced the slide.

Foreground mode is useful when a contextual engraving needs to remain visible around an existing diagram rather than disappear behind opaque panels.

### `exclusions`

Optional absolute rectangles that erase contextual art from protected areas. These exist specifically to prevent foreground illustrations from drawing across exact labels, copy or important diagram nodes.

### `opacity`

Accepted range: `0.15–1.0`.

### `paper_wash`

Optional cream wash used to push contextual art backward into the paper stock.

### `tint`

Used by future `asset` sources. Current supported values are `ink_accent`, `accent`, and `original`.

## Ep029 proof set

The Milestone 5.2 benchmark adds six contextual illustrations — one for each presenter — while leaving the other fourteen slides as the Milestone 5.1 control:

1. NORA / slide 2 — `casefile_system`
2. Kai Patel / slide 4 — `river_monitoring`
3. Johan Vosloo / slide 5 — `water_infrastructure`
4. Thabo Mokoena / slide 7 — `mineworker_claims`
5. Amari Ndlovu / slide 8 — `care_pathway`
6. Diane Sterling / slide 16 — `oil_market`

The production report records illustration count, source, kind and layer.

## What 5.2 proves — and what it does not

5.2 proves:

- a production slide can request context-specific art without giving up exact layout control;
- the art layer can be deterministic and zero-cost;
- foreground and background composition are both supported;
- protected text/diagram regions can be excluded;
- future generated raster assets have a defined compositor hook;
- the illustration layer remains auditable in the production report.

5.2 does **not** prove final visual parity with the handcrafted reference episodes.

The procedural line art is intentionally an engineering backend, not the final artistic backend. The original slides still win on scene richness, engraved detail, bespoke iconography and image-led storytelling.

## Recommended next step

After 5.2 is GitHub/Drive green, stop increasing procedural illustration complexity.

Milestone 5.3 should focus on the **generated contextual-asset backend interface**: take a structured illustration brief, produce or accept a raster illustration without text/presenter identity, store/approve it, and feed it back through the 5.2 compositor.

That backend can initially be manual or API-assisted, and later move to the local RTX 3080 when the machine is ready.
