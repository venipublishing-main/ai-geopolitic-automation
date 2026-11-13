# Ep145 — one-time Instagram TEST carousel publishing runbook

**Intended production day:** Friday 13 November 2026, Africa/Johannesburg.
**Archive:** fixed Drive History - Episode List root ID `1QcCh-qMHOH97ZWdTLULwNygibJcZRb4q`; exact folder name `Ep145-13November2026`.
**Account:** `Ai_Geopolitic` Instagram Creator account, verified on Meta Unified Login with the repository's secured `AI_GEO_IG_ACCESS_TOKEN`.
**User authorization:** one TEST-only ten-image carousel after a genuine Sisyphus PRODUCTION PASSED handoff; user will manually delete that single test post.
**No production image posting, Threads or Reels on this first test.**

## Status at 12 November

- Hourly ChatGPT condition-watch automation scheduled for 13 Nov SAST (24 hourly checks), ID `6af60bcd73488191b9ed806921ebc9a4`.
- Separate publisher branch `feat/publisher-v1-archive-selection-20261112`, draft PR #8.
- Ten unique TEST ONLY JPEGs (1080×1350), with 01/10..10/10 and NOT NEWS labelling, hosted in the repository's dedicated public media branch. Immutable QA media commit `37dac6614a6d01ae4691a5af5561735dd3f14ef1`.
- Real HTTPS preflight from GitHub Actions run `43288916285`: all ten pinned public JPEG URLs fetched as JPEG successfully. Isolated tests: **91 passed**, Meta read-only account verification CONNECTED. No Meta POST.
- One-time GitHub Actions release workflow installed on the repository's **main** branch: `.github/workflows/ai-geopolitic-ep145-test-release.yml`. It has **no fixed-time post**; it triggers only when `publisher_signals/ep145-20261113.json` is created on main after verified production handoff.
- Separate repo manual-exclusion ledger still blocks Ep144, 12 Nov (user-reported manually published). Do not repost Ep144.
- **Known blocker to direct GitHub Drive access:** its existing rclone OAuth token refresh was rejected during a read-only runner check on 12 Nov (`TOKEN_REFRESH_REJECTED`), even though the secret is present. Do not assume a GitHub cron runner can read the archive. The conditional ChatGPT hourly watch uses the connected Drive integration instead, with a GitHub signal write if supported. If it cannot verify Drive or write the signal, the run stays blocked and must report the issue; it may NEVER infer PASS.

## Exact Sisyphus production handoff (required)

Once Sisyphus actually finishes the full episode, the following separate file must be saved to the **Ep145 archive folder**, alongside `Ep145_QC_Completion.json` and other accepted assets:

`Ep145_PUBLISH_HANDOFF.json`:

```json
{
  "schema": "ai-geopolitic.publisher.production-handoff.v1",
  "episode_id": "Ep145",
  "production_date_sast": "2026-11-13",
  "archive_folder_id": "<ACTUAL VERIFIED DRIVE FOLDER ID>",
  "status": "PRODUCTION PASSED",
  "author": "Sisyphus",
  "publish_target": "INSTAGRAM_CAROUSEL_TEST_ONLY",
  "carousel_items": 10,
  "reel_frames": 6,
  "unresolved_blockers": [],
  "component_results": {
    "rnd": "PASS",
    "slide_design": "PASS",
    "carousel_10": "PASS",
    "carousel_caption": "PASS",
    "reel_frames_6": "PASS",
    "reel_caption": "PASS",
    "archive_drive_readback": "PASS"
  }
}
```

Sisyphus must only write the file after every named component is genuinely verified in Drive with zero blocking defects. **Never forge, prefill, or assume this PASS.** Canonical Authority: AI Geopolitic Automation & Manifest Contract v3.1 (appendix dated 12 Nov). This file is a separate operational handoff, not a new Manifest v2 field.

## Hourly signal-to-publication chain

1. ChatGPT's 13 Nov watch reads the real Ep145 episode and final handoff via the authenticated connected Drive. It requires exact archive identity, 10 numbered slides and six reel PNGs, QC PASS, caption original UTF-8 and SHA-256, and no prior publisher receipt/manual-exclusion.
2. If and only if all checks genuinely pass, the watch writes ONE GitHub file on **main**: `publisher_signals/ep145-20261113.json`, schema `ai-geopolitic.publisher.signal.v1`, with the exact Sisyphus handoff object, real archive ID, original UTF-8 caption and its SHA-256, `test_only=true`, `previously_published=false` (subject to later Meta duplicate reconciliation) and `source=SISYPHUS_DRIVE_VERIFIED`. It must never overwrite an existing signal.
3. The GitHub main workflow reacts to that specific path being created, checks 13 Nov SAST date, validates signal and component PASS status, verifies all ten pinned public JPEG URLs via real HTTPS GET, and confirms the exact Instagram account and publishing scopes via Meta GET.
4. The workflow checks IG recent media for a previous Ep145 QA post and commits a durable `publisher_state/ep145-instagram-test.json` **CLAIMED** state to main BEFORE the first Meta POST. If that Git push fails, it does not post. A CLAIMED or PUBLISHED record permanently blocks retries without human reconciliation.
5. The workflow creates ten child JPEG containers, one parent `CAROUSEL` with the entire original archived caption after an explicit TEST ONLY preamble, `is_ai_generated=true` **on the parent only**, then one `media_publish`.
6. Upon a successful Meta media ID, it GETs `permalink,is_ai_generated` and writes the final receipt. If the publishing response is ambiguous or receipt verification fails, the system **never automatically retries**. The user removes the test carousel manually from Instagram when confirmed.
7. Music is not attached: static-image Instagram API carousel publishing cannot choose an audio track. Real Reel + Threads publishing remain later phases.

## Failure policy

No Sisyphus handoff = no post. Pending review/completion text ≠ PRODUCTION PASSED. Missing caption or wrong SHA = no post. Missing media URL or token = no post. Duplicate release state or uncertain Meta result = no repost. Late run after 13 Nov SAST = no post. Test-only images must never be silently exchanged with real Ep145 artwork.

**No Instagram POST has occurred as of this document's creation on 12 November 2026.**
