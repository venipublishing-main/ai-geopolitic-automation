# AI Geopolitic — six-frame Reel review builder (v0.2)

**Status: build-only pilot. NOT an Instagram publisher.** This workflow cannot
post anything: it has `contents: read` and no Instagram or Threads secret.

## Locked inputs and output

- Resolve one exact `EpNNN` / SAST `YYYY-MM-DD` archive from the canonical
  `History - Episode List` folder. No newest-folder selection or fallback.
- Require the existing production QC JSON, complete Sisyphus PASS handoff,
  verified carousel packet, six separately verified `ReelFrame01of06.png`
  through `ReelFrame06of06.png` and `EpNNN_ReelCaption.txt`. Read-only Drive.
- Require every image to be exactly **1080×1920**, PNG, SHA-matched to Drive
  readback and correctly numbered. Preserve every frame's pixels: no scene
  regeneration, zoom, shake, sliding, re-typesetting or AI identity drift.
- Compile an **18-second 1080×1920 H.264/AAC MP4 at 30 fps**; six original
  frames occupy three seconds each on the timeline. Each of the five 0.30-second
  transitions is centered on an exact three-second boundary, blending images
  through an original, deterministic light-flare overlay. The first image fades
  in and the last fades out. Intermediate images remain stationary until their
  flare-assisted exit (our conservative **Steady Out** approximation).
- The Flare and Steady Out effects are **inspired by**, not pixel-identical to,
  proprietary Instagram Edits presets. Ian must review a real episode preview
  before accepting their fidelity; no camera shake, zoom, typography edits or
  portrait movement is introduced.
- A simple original stereo ambient five-note motif is synthesized at 18 seconds
  **only as private review filler**. It is NOT the approved Veni Sonora VS001
  master and must never become an automatic publication fallback.
- Verify output streams, duration, size, source hashes, audio provenance, and
  unchanged Reel caption. Store a `REVIEW_MP4_READY_NOT_PUBLISHED` receipt.
- The six PNGs, 18-second MP4, original flare overlay, caption, preview WAV,
  sonic provenance and stage JSON
  are uploaded as a **private 14-day GitHub Actions artifact** for Ian's review.
  No media branch is published by this workflow.

## How to run

1. Open **Actions → AI Geopolitic Reel — review MP4 only (no publication)**.
2. **Run workflow** on `main` with an exact episode/date, e.g. `Ep145`,
   `2026-11-13`, and `mode=plan` first. A plan is read-only and posts nothing.
3. If the exact archive and six-frame preflight pass, run `mode=build`. Download
   the review artifact from the completed GitHub Actions job.
4. Inspect visual composition, readability on a phone, portrait fidelity,
   the approximation of Edits **Fade In / Steady Out / Flare / Fade Out**,
   placeholder musical tone, and caption text. Captions are retained exactly;
   verify their content before any future real release.
5. A future, separate Instagram Reel release path must require episode-scoped
   human approval, immutable HTTPS video URLs, original-audio sign-off, verified
   `ai_geopolitic` account, durable claim **before** the first Meta POST,
   independent Reel receipts, and manual reconciliation after ambiguity.

## Editorial and audio integrity

This first soundtrack is an original **instrumental pilot** with a five-note
motif, restrained dynamics and no vocals or sampled third-party audio. It is not
a locked Veni Sonora master and cannot silently substitute for an Ian-approved
sonic identity. The future publisher must require a versioned 18-second VS001
master with matching SHA-256 and rights provenance, without generating new music
for each episode. The source frames are never animated by whole-image movement;
any later per-panelist blink, shimmer or glimmer requires separate masked-region
R&D and QC before a replacement Reel build.

## Safety boundary

The existing ten-image Instagram carousel and ten-image Threads carousel are
separate products and untouched. This workflow does not auto-post, cross-post,
schedule, modify the original Drive archive, or clear a publication receipt.
Nothing in a successful build authorizes social-media publication.

API reference for the later publisher: Meta's official
[Instagram Reels publishing guide](https://www.postman.com/meta/instagram/folder/830j7my/reels-publishing).
