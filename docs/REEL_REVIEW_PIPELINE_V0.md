# AI Geopolitic — six-frame Reel review builder (v0.1)

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
- Compile a **30-second 1080×1920 H.264/AAC MP4 at 30 fps**; each original frame
  is held stationary for approximately five seconds, with only five gentle
  0.30-second dissolves. A simple original stereo ambient five-note motif is
  synthesized deterministically, not selected from Instagram's licensed catalog.
- Verify output streams, duration, size, source hashes, audio provenance, and
  unchanged Reel caption. Store a `REVIEW_MP4_READY_NOT_PUBLISHED` receipt.
- The six PNGs, 30-second MP4, caption, WAV, sonic provenance and stage JSON
  are uploaded as a **private 14-day GitHub Actions artifact** for Ian's review.
  No media branch is published by this workflow.

## How to run

1. Open **Actions → AI Geopolitic Reel — review MP4 only (no publication)**.
2. **Run workflow** on `main` with an exact episode/date, e.g. `Ep145`,
   `2026-11-13`, and `mode=plan` first. A plan is read-only and posts nothing.
3. If the exact archive and six-frame preflight pass, run `mode=build`. Download
   the review artifact from the completed GitHub Actions job.
4. Inspect visual composition, readability on a phone, portrait fidelity,
   transition pace, musical tone, and caption text. The Ep145 canonical Reel
   caption currently ends **“Post is Live!”**; this wording is retained exactly
   and should be reviewed before any real release.
5. A future, separate Instagram Reel release path must require episode-scoped
   human approval, immutable HTTPS video URLs, original-audio sign-off, verified
   `ai_geopolitic` account, durable claim **before** the first Meta POST,
   independent Reel receipts, and manual reconciliation after ambiguity.

## Editorial and audio integrity

This first soundtrack is an original **instrumental pilot** with a five-note
motif, restrained dynamics and no vocals or sampled third-party audio. It is not
a locked Veni Sonora master and cannot silently substitute for an Ian-approved
sonic identity. The source frames are never animated by whole-image movement;
any later per-panelist blink, shimmer or glimmer requires separate masked-region
R&D and QC before a replacement Reel build.

## Safety boundary

The existing ten-image Instagram carousel and ten-image Threads carousel are
separate products and untouched. This workflow does not auto-post, cross-post,
schedule, modify the original Drive archive, or clear a publication receipt.
Nothing in a successful build authorizes social-media publication.

API reference for the later publisher: Meta's official
[Instagram Reels publishing guide](https://www.postman.com/meta/instagram/folder/830j7my/reels-publishing).
