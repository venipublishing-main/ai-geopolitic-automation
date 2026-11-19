# AI Geopolitic — six-frame Reel review builder (accepted effects + VS001 master)

**Status: build-only pilot. NOT an Instagram publisher.** This workflow cannot
post anything: it has `contents: read` and no Instagram or Threads secret.

## Locked inputs and output

- Resolve one exact `EpNNN` / SAST `YYYY-MM-DD` archive from the canonical
  `History - Episode List` folder. No newest-folder selection or fallback.
- Require the existing production QC JSON, complete Sisyphus PASS handoff,
  verified carousel packet, six separately verified `ReelFrame01of06.png`
  through `ReelFrame06of06.png` and `EpNNN_ReelCaption.txt`. Read-only Drive.
- Require every image to be exactly **1080×1920**, PNG, SHA-matched to Drive
  readback and correctly numbered. Preserve every **source PNG** unchanged:
  no scene regeneration, re-typesetting, portrait replacement or identity drift.
  Final review videos apply a whole-frame digital zoom to the middle PNGs;
  this is not masked facial animation or a replacement of the accepted files.
- Compile an **18-second 1080×1920 H.264/AAC MP4 at 30 fps**; six original
  frames occupy three seconds each on the timeline. Each of the five 0.30-second
  crossfades is centered on an exact three-second boundary. An original
  **centre-expanding circular light bloom** illuminates each boundary for
  **0.50 seconds**, growing radially from the centre rather than drawing a
  diagonal or travelling streak. The first image fades in from black over
  **0.90 seconds**; the last fades out over the final **0.90 seconds**.
  All middle clips have a continuously changing,
  centered **Steady Out** digital zoom over their approximately three-second hold.
- Create **two separate MP4s** for every review build:
  - `Reel_B_Noticeable.mp4`: middle frames zoom smoothly from **108% to 100%**.
  - `Reel_C_Stronger.mp4`: middle frames zoom smoothly from **112% to 100%**.
  Zoom uses a continuous eased trajectory, not a discrete start/end jump.
  **Ian accepted the stabilised 12% version** after reporting vibration in the v2 previews.
  Effects v3 therefore replaces FFmpeg's integer-quantised `zoompan` crop with
  a **frame-evaluated, cubic-interpolated subpixel camera transform**. Its four
  corners change symmetrically around the centre: no shaking pan or rotation.
  The 12% strength, six-frame sequencing, fades and circular flare are unchanged.
  The subsequent stabilised v3 review passed Ian's visual check. A full-speed,
  single-pixel ink-line motion regression remains required for QC.
- Fade In / Fade Out / Flare / Steady Out are **Edits-inspired approximations**,
  not copies or proven pixel-identical versions of proprietary Edits presets.
  Source PNG text is baked into the images; it therefore also scales. Verify
  legibility and all text/portrait margins on a real phone. Separately layered
  static typography is a later editorial-renderer improvement, not this pilot.
- Every Reel now uses the **exact same Ian-approved 18-second recording**:
  Veni Sonora **VS001 — Candidate C v04b Hook Focus, Version B**, approved
  **19 November 2026**. The file is pinned in the repository at
  `assets/sonora/VS001_AIGeopolitic_C_v04b_HookFocus_18s_MASTER.mp3`.
  SHA-256: `3c0824d3af1cba53a60edd1757e95d7ea8b400af5d2e8f13d7dd0da4d7e8c3b3`.
  A checksum failure or missing file **blocks the build**. The retired
  synthetic motif cannot be substituted. The same recording is used for both
  review zoom variants; **12% is the selected style for future releases**.
- Verify output streams, duration, size, source hashes, audio provenance, and
  unchanged Reel caption. Store a `REVIEW_MP4_READY_NOT_PUBLISHED` receipt.
- The six PNGs, **both** 18-second MP4s, 15 original radial flare frames and
  their middle-frame inspection PNG, caption, exact approved master MP3,
  sonic provenance and stage JSON
  are uploaded as a **private 14-day GitHub Actions artifact** for Ian's review.
  No media branch is published by this workflow.

## How to run

1. Open **Actions → AI Geopolitic Reel — review MP4 only (no publication)**.
2. **Run workflow** on `main` with an exact episode/date, e.g. `Ep145`,
   `2026-11-13`, and `mode=plan` first. A plan is read-only and posts nothing.
3. If the exact archive and six-frame preflight pass, run `mode=build`. Download
   the review artifact from the completed GitHub Actions job. It includes
   `Reel_B_Noticeable.mp4` and `Reel_C_Stronger.mp4`.
4. For a regression review use **Ep149 / 2026-11-17**. The **12% version** is
   the selected future visual treatment. Inspect ink lines and lettering while
   it zooms; they must remain stable without prior vibration. Also inspect
   visual composition, readability on a phone, portrait fidelity,
   the approximation of Edits **Fade In / Steady Out / Flare / Fade Out**,
   approved fixed VS001 soundtrack, and caption text.
   Captions are retained exactly; verify content before any future real release.
5. A future, separate Instagram Reel release path must require episode-scoped
   human approval, immutable HTTPS video URLs, the pinned VS001 audio checksum, verified
   `ai_geopolitic` account, durable claim **before** the first Meta POST,
   independent Reel receipts, and manual reconciliation after ambiguity.

## Editorial and audio integrity

The earlier five-note synthetic review motif is retired from the production
Reel path (retained only as an isolated test fixture). **Version B Hook Focus**
is the permanent, immutable 18-second VS001 music recording for every future
AI Geopolitic Reel until Ian explicitly approves a replacement. It is the
original Veni Sonora track selected after Tribeca-style lounge refinements.
Its source-of-truth master is in the Veni Sonora Drive, file ID
`1QXyWCItlnBHw6-UfVCYNaS1cwIuLbIzd`; the repository contains the same
byte-identical production copy. Each build checks the hardcoded SHA-256 and
emits audio provenance in `stage.json`. It must never generate new music for
each episode. The exact six source PNG files remain immutable. The middle
video clips do use whole-image digital zoom, including text. Any later
per-panelist blink, shimmer or glimmer requires separate masked-region R&D and
QC before another Reel build; such changes are not part of the accepted effects.

## Safety boundary

The existing ten-image Instagram carousel and ten-image Threads carousel are
separate products and untouched. This workflow does not auto-post, cross-post,
schedule, modify the original Drive archive, or clear a publication receipt.
Nothing in a successful build authorizes social-media publication.

API reference for the later publisher: Meta's official
[Instagram Reels publishing guide](https://www.postman.com/meta/instagram/folder/830j7my/reels-publishing).
