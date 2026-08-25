# AI Geopolitic Fidelity Benchmark

## Benchmark source

Milestone 5 uses the archived **Ep029 — 20 July 2026** carousel as the controlled visual benchmark. The finished historical episode remains in Google Drive under the AI-Geopolitical episode history library.

The benchmark is useful because the editorial content, presenter sequence and finished target already exist. Improvements can therefore be judged against a real AI Geopolitic product rather than against an invented engineering demo.

## What Milestone 5.0 proved

The automated pipeline can now produce a complete 20-slide episode with:

- correct slide order;
- locked character portraits;
- character-specific accent colours;
- deterministic layout routing;
- 4–5 layout families per presenter;
- exact text rendering;
- safe-margin and overflow QA;
- a contact sheet and routing/production reports.

The largest remaining gap is **visual fidelity**, not orchestration.

## Fidelity gaps observed against Ep029

Ranked by impact:

1. **Contextual illustration richness** — the originals integrate maps, buildings, chains, labour scenes, institutional symbols and other bespoke visual metaphors more aggressively.
2. **Portrait integration** — the originals often make the presenter part of the illustration field rather than a separate portrait card.
3. **Background atmosphere** — the originals use engraved marks, map contours, systems traces and editorial texture to avoid sterile whitespace.
4. **Evidence treatment** — original facts often use icons, numbered evidence, stamps or semantic pictograms rather than generic bullets.
5. **Compositional asymmetry** — the handcrafted slides can break grids more confidently because a human/AI art pass controls the whole composition.

## Milestone 5.1 corrections

Milestone 5.1 deliberately improves reusable primitives rather than adding more templates.

### Shared editorial atmosphere

`src/editorial_primitives.py` now supplies deterministic character-specific background marks:

- NORA — system axes / globe contours;
- Johan — institutional facade / authority geometry;
- Diane — market bars / transmission traces;
- Kai — distributed network / circuit traces;
- Thabo — ledger rows / burden hatching;
- Amari — regional contours / route lines.

These marks are low-contrast and sit behind foreground content so exact text remains code-controlled.

### Richer paper material

The cream background keeps deterministic grain but adds faint print-fibre scratches. The purpose is material depth, not visible noise.

### Portrait integration

Locked portraits remain unchanged. The shared portrait compositor now adds a subtle printmaker plate / hatch frame and a slightly deeper bottom fade so the portrait sits inside the composition rather than reading as a pasted rectangular card.

### Evidence ledger

Shared fact panels now use numbered evidence markers and a vertical ledger rule instead of anonymous dots. This increases editorial character without changing the underlying content model.

## What 5.1 intentionally does not solve

Milestone 5.1 does **not** claim parity with the original episodes. The largest remaining difference is still contextual illustration.

The next fidelity stage should introduce a reusable **contextual illustration layer** that can draw or composite content-specific maps, institutional scenes, objects and metaphors without asking an image model to render exact text or regenerate presenter identities.

That layer may later use local RTX 3080 generation or external free/low-cost generation, but code must continue to own typography, portraits, borders, branding and QA.
