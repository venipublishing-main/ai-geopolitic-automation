# AI Geopolitic daily carousel release — Instagram and Threads

This runbook separates **production**, **episode-specific human approval** and
**irreversible publication**. Each platform has its own authorization, GitHub
Action, immutable media commit, pre-Meta claim and post-publication receipt.

## Production gate

- Select exactly one `EpNNN` and its actual `YYYY-MM-DD` production date in
  South Africa, resolving to `EpNNN-DMonthYYYY` beneath the canonical Drive
  archive parent. **Never use the newest folder or yesterday's episode.**
- Archive contains ten original carousel PNGs, the canonical caption, a
  per-asset SHA-256/readback-verified QC completion JSON, and the separate
  `EpNNN_PUBLISH_HANDOFF.json` **authored by Sisyphus**.
- Handoff must use `ai-geopolitic.publisher.production-handoff.v1`, show
  `PRODUCTION PASSED`, match archive folder/date/episode, pass all seven
  production components, and contain zero blockers. A QC note saying
  `PRODUCTION COMPLETE — PENDING IAN REVIEW` is **not** the handoff.
- Established Ep145 QC (`image_counts` + `delivered`) is the canonical format
  Sisyphus is instructed to continue. The reader also validates the original
  Ep146 QC (`counts` + `images` + `captions` + `deliverables`) without weakening
  source ID, source SHA, visual inspection, exact caption or Drive readback.
- Before staging, the ten **original** PNG byte digests are verified against
  QC. Each is converted to an ordered 1080×1350 JPEG, keeping the unmodified
  editorial composition; caption bytes and SHA stay exact. No Reel is included.

## Human gate and triggering

There is deliberately **no unattended daily publication schedule**. When the
production handoff has passed and Ian has reviewed the episode, run the two
platform workflows manually from GitHub Actions on `main`:

1. **AI Geopolitic Instagram — ten-image carousel (human gate)**:
   - Run `mode=plan`, `episode=Ep146`, `date_sast=2026-11-14` (example).
   - Check the `INSTAGRAM_PREFLIGHT_PASS_NO_PUBLICATION` result.
   - Run `mode=publish` with the same episode/date and the exact confirmation
     `PUBLISH_INSTAGRAM_EP146_20261114`.
2. **AI Geopolitic Threads — ten-image carousel (human gate)**:
   - Run `mode=plan` with the same episode/date.
   - Check `PREFLIGHT_PASSED_NO_PUBLICATION`.
   - Run `mode=publish` with `PUBLISH_THREADS_EP146_20261114`.

The confirmation changes for **every episode and date**. A prior successful
Ep145 signal cannot authorize Ep146. `plan` has no Meta write operations.
For future dates, enter the new episode and SAST date explicitly.

### Connected GitHub plugin launch (no browser sign-in)

The connected GitHub plugin can launch the same gated Actions using the
`AI Geopolitic — authenticated episode release signal` bridge. After Ian's
specific approval, create **one new** text file on `main`:

`publisher_signals/launch-epNNN-YYYYMMDD-{instagram|threads}-{plan|publish}-01.json`

Its six exact string fields are `schema`, `episode`, `date_sast`, `platform`,
`mode`, and `confirmation`. `schema` is
`ai-geopolitic.publisher.launch-signal.v1`; `confirmation` is empty for `plan`
and for `publish` is the exact `PUBLISH_INSTAGRAM_EPNNN_YYYYMMDD` or
`PUBLISH_THREADS_EPNNN_YYYYMMDD` string. `src/release_signal.py` checks the
single newly added file, repository/actor/main-branch identity, matching
filename and contents, a non-future date, the explicit confirmation and the
absence of an existing claim. It then uses its ephemeral GitHub Actions token
to dispatch the **existing** platform workflow on `main`.

Wait for the downstream `workflow_dispatch` run and verified `plan` result
before creating the `publish` signal. After publication, check the immutable
`publisher_state` receipt and final permalink for each platform. Never add a
second `publish` signal to retry an ambiguous result. No schedule, Reel, or
automatic publication is introduced by this bridge; human approval remains
mandatory. The Actions UI remains a supported manual alternative.

## One-time publication safety

- Each channel first verifies 10 public media URLs pinned to a specific Git
  commit, checks the actual account is `@ai_geopolitic`, and searches recent
  account media for the same caption. These read-only operations do not publish.
- The release then pushes a claim onto the main branch at:
  `publisher_state/instagram-epNNN-YYYYMMDD.json` or
  `publisher_state/threads-epNNN-YYYYMMDD.json` **before** any Meta write.
  Any claim, including an unconfirmed claim, forbids an automatic duplicate.
- Instagram creates 10 ordered child images, one carousel with the exact
  caption and `is_ai_generated=true`, publishes once, then verifies returned
  post ID, permalink and AI-information flag. Threads runs its independent
  equivalent, verifying ten children and the account/permalink/text.
- Claims are updated with platform-specific published receipts. If publication
  is ambiguous or verification fails after a claim, **do not click Run workflow
  again**. Inspect the account and reconcile the receipt manually.
- Audio, Reels, Stories, automatic cross-posting, date fallback and retouching
  of the accepted images are outside this release path.

## Required GitHub repository secrets

- Shared Drive: `RCLONE_DRIVE_CLIENT_ID`, `RCLONE_DRIVE_CLIENT_SECRET`,
  `RCLONE_DRIVE_TOKEN`, `AI_GEOPOLITIC_DRIVE_ROOT_FOLDER_ID`.
- Instagram only: `AI_GEO_IG_ACCESS_TOKEN`.
- Threads only: `AI_GEO_THREADS_ACCESS_TOKEN`.

These tokens are never written into the archive, media, receipts or job logs.
