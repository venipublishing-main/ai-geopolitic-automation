# Instagram carousel publishing hardening — reusable review foundation

Status: **review-only foundation; no publishing authorized**.

The Episode 145 one-time Instagram production release remains unchanged. The
existing Publisher P1 draft PR #8 targets `automation-v2` and is not merged
into main. This new, smaller path is intended to replace one-off staging with
independent per-episode review before implementing a generic live release.

## Review workflow

`.github/workflows/ai-geopolitic-instagram-review.yml` supports `workflow_dispatch`
on `main` with explicit `episode` and `date_sast` and two modes:

- `plan`: authenticated read-only Drive archive selection, exact SAST folder,
  Sisyphus `PRODUCTION PASSED`, completed QC and SHA-verified caption and slides.
- `stage`: all of the above, plus **ten** unique 1080×1350 JPEG delivery copies,
  SHA-256 hashes and a private 14-day artifact. Archive PNGs are never edited.

All source verification reuses `src/threads_media.py`, already used by the
successful Ep145 Threads release. The new `src/instagram_media.py` records an
Instagram-specific, non-publishing manifest. The original canonical caption
remains unchanged and no audio is added to still-image carousels.

## Explicit authorization boundary

This workflow has **no Meta access token**, repository `contents: read`, no
public media staging branch, no automatic schedule and no provider POST.

Before any future Instagram carousel release, the live publisher must:

1. Take an explicit, episode-specific decision from Ian to publish the exact
   caption and ten verified images to `@ai_geopolitic`.
2. Reverify the immutable source and public delivery digests, account identity,
   recent duplicates, and AI-generated-media disclosure.
3. Persist a channel-specific **CLAIMED_NO_AUTOMATIC_RETRY** receipt to `main`
   before the first Meta write; no automatic rerun after ambiguous responses.
4. Publish only one ten-image carousel, then verify media ID, permalink and
   AI information label, with a separate published receipt.
5. Keep Instagram and Threads channel states independent; never repost a
   successful channel because another failed.

Do not confuse editorial `PRODUCTION PASSED` with consent to publish.
