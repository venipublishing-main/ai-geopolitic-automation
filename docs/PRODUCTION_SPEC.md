# AI Geopolitic Automated Visual Production Specification v1.1

This specification combines the current human slide-generation workflow with the two uploaded 20-slide episode references and the six locked portraits.

## 1. Authority hierarchy

When instructions appear to conflict, apply them in this order:

1. The six locked portrait assets and character mapping.
2. The current episode's approved R&D and slide copy.
3. This production specification.
4. The two uploaded visual episode references.
5. General creative judgement.

## 2. Production principle

Automation must preserve the quality of the existing product. It must not reduce AI Geopolitic to generic text cards.

Use:

- AI or sourced artwork for non-text editorial scenes, maps and contextual imagery.
- Code for exact text, typography, portrait placement, accent colour, rules, safe margins, slide numbering, branding and footer.
- Locked portraits for all recurring panelists. Never generate substitute faces.

## 3. Canvas and safe area

- Output: one standalone 1080 × 1080 PNG per slide.
- Critical safe margin: at least 76 px on every edge, approximately 7%.
- Prefer additional breathing room where possible.
- No critical text, slide number, logo, footer or thin border may cross the safe area.

## 4. Header rules

### Slides 1 and 20

Include the full episode header:

- AI Geopolitic branding
- episode date
- episode title
- slide number
- NORA
- opening or final systems board

### Slides 2–19

- Do not use the full date/header bar.
- Do not repeat the episode date.
- Include the slide number and normal footer branding.

## 5. Visual identity

- Off-white or cream textured paper.
- Monochrome black etched editorial illustration.
- One accent colour tied to the active speaker.
- Distressed, condensed, uppercase editorial headlines.
- Serif editorial body and quotations.
- Thin rules, boxes, arrows, icons, maps, charts, chains and loops.
- Serious, mature, analytical and institutional.
- Never glossy, neon, comic, meme-like, generic television news, or corporate stock design.

## 6. Character colour mapping

- NORA: editorial blue
- Diane Sterling: green
- Johan Vosloo: navy/deep blue
- Kai Patel: purple
- Thabo Mokoena: red
- Amari Ndlovu: gold/earth

## 7. Slide archetypes

The system may vary composition, but it must select an approved archetype:

1. Opener
2. Opening frame / why this matters
3. Character analysis
4. Data / infographic
5. Map / systems geography
6. Process / chain / loop
7. Human cost / field impact
8. Transition / synthesis
9. Final closing

Not every slide must contain every possible element. Mandatory components depend on archetype. This prevents overcrowding while preserving the editorial product.

## 8. Standard topical slide content

A normal slide from 2–19 should contain most of the following, according to archetype:

- slide number
- large headline
- concise deck/core line
- correct speaker portrait and name
- short speaker quotation
- key facts or system points
- a visual argument: scene, diagram, map, chart or process
- ideological lens / takeaway
- AI Geopolitic branding
- exact footer line

## 9. Exact footer

Use exactly:

**The event is factual. The interpretation ideological.**

Do not pluralise, paraphrase or alter the punctuation.

## 10. Asset policy

- Locked portraits are composited; they are never regenerated.
- Background and contextual art may be generated, but it must not introduce new panelists or substitute faces.
- Text is never rendered by a generative image model.
- Logos, dates, slide numbers, labels and captions are always code-rendered.
- Maps and charts must be treated as explanatory graphics, not decorative filler.

## 11. Human-facing production sequence

The manual slide-generation conversation may continue using packs:

- 1–5
- 6–10
- 11–15
- 16–20

The automation itself may generate all 20 in a single run, but must export twenty separate images.

## 12. Quality control

Reject or flag a slide when:

- portrait and speaker do not match
- accent colour is incorrect
- text crosses the safe area
- the footer line changes
- slide numbering is wrong
- a date appears on slides 2–19
- the headline or body becomes unreadably small
- the layout is visually too similar to adjacent slides
- a generative model has altered the panelist's face
- the slide looks like a generic template rather than AI Geopolitic
- the visual does not support the political argument

## 13. Phase-one workflow

1. User supplies approved R&D.
2. Model converts R&D into structured 20-slide copy.
3. System assigns archetypes and speakers.
4. Contextual artwork is supplied or generated.
5. Code composes portraits, artwork and exact typography.
6. Automated QA runs.
7. Twenty individual PNGs, contact sheet, caption and Reel plan are exported.
8. Human review occurs before publication.

## 14. Long-term workflow

Research, planning, visual production, QA, Reel/Story creation and publishing may eventually run automatically, but must retain a kill switch and review mode.
