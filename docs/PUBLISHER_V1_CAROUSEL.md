# AI Geopolitic Publisher — v1 Carousel Track

Created 12 November 2026 (SAST). Development branch feat/publisher-v1-archive-selection-20261112. Live publication is **disabled**.

## Source selection

Source of truth: AI-Geopolitical / History - Episode List, fixed parent folder ID 1QcCh-qMHOH97ZWdTLULwNygibJcZRb4q.

1. Find the one folder exactly matching the target SAST production date. Folder names must match EpNNN-DMonthYYYY. Never choose by modification time or silently use yesterday if today's files are missing.
2. Read the selected EpNNN_QC_Completion.json and EpNNN_CarouselCaption.txt by matching actual Drive IDs in the chosen folder; validate identity and contents.
3. Pin the exact ten EpNNN_Slide01of10.png through EpNNN_Slide10of10.png in number order, cross-check the actual Drive IDs against QC deliverables, verify 1080x1350/1080x1440 dimensions, required QC fields, readback flags and SHA-256.
4. Read a separate manual-publication exclusion ledger. Ep144 on 12 November 2026 is marked USER_REPORTED_MANUALLY_PUBLISHED for Instagram per the user's explicit report. This prevents reposting even when the production QC record still says NOT PUBLISHED.
5. Stage converted delivery images independently from original archived PNGs. For 1080x1350, preserve full artwork; for 1080x1440, fit full artwork to 1080x1350 with off-white side margins rather than crop or distort. Export high quality JPEG with an 8 MiB maximum.
6. Independently deliver the ten JPEGs by a public, HTTPS, short-lived media origin. This origin must not be the private Google Drive view URL; public delivery hosting remains to be implemented and verified.
7. Publish on Instagram: create ten ordered is_carousel_item child containers, await valid processing, create CAROUSEL parent with caption, publish the parent and record the Instagram post ID. The Graph transaction code exists but is intentionally DISCONNECTED from the safe CLI and all scheduled workflows.

## Read-only developer commands

The repository already depends on Pillow and pytest. None of these commands calls the Meta publishing API.

    python -m pip install -r requirements.txt
    python -m src.publisher_cli --mode test-deck
    python -m src.publisher_cli --mode plan
    python -m src.publisher_cli --mode plan --episode Ep143 --date 2026-11-11
    python -m src.publisher_cli --mode stage --episode Ep143 --date 2026-11-11

The first command creates ten locally staged TEST ONLY 1080x1350 JPEGs. The default plan mode selects the exact SAST date. Ep144 should BLOCK in the ordinary planning mode because it has been manually published.

## Test-publishing strategy

The first real-account end-to-end test should be **ONE ten-image carousel**, not ten separate posts. All slides explicitly say TEST ONLY, NOT NEWS, 01/10 ... 10/10. A separate caption calls the publication a temporary technical test.

Prefer a dedicated Instagram professional test account. If using the real account, use a quiet test window and remove the completed carousel immediately after inspection. Instagram's standard publishing Graph API does not provide a general delete-published-media operation: manually delete this single test carousel within the Instagram application. Record the Instagram media ID and URL first. Do not delete the original archive or the QC ledger.

Never retry an ambiguous publish call blindly: reconcile the actual account media first. A durable state/receipt store and single-run lock or workflow concurrency group must precede automatic deployment.

## Later tracks

P1 — Instagram carousel: use the direct Instagram Login API for the AI Geopolitic Creator account, with instagram_business_basic and instagram_business_content_publish, graph.instagram.com, and no Page linkage required; then add public HTTPS delivery hosting, durable idempotency and publication receipts, run a manual TEST carousel, and separately authorize unattended scheduling.

P2 — Instagram Reel: create a final actual MP4 (H.264 video, AAC audio when used) from the six 1080x1920 archived frame PNGs; QC composition, playback, timing, video dimensions and caption. Meta's REELS container accepts a video URL, not six still images.

P3 — Threads: integrate the correct Threads account and OAuth, reuse archived carousel artwork in a Threads-specific carousel of ten items, use a platform-specific <=500 character caption, publish through the Threads container and threads_publish endpoints. Threads has an official post deletion endpoint suitable for test cleanup. Keep receipts and retries independent for Instagram Carousel, Instagram Reel and Threads Carousel.

Potential independent daily channel states: QC_READY -> IG_CAROUSEL_PUBLISHED -> THREADS_CAROUSEL_PUBLISHED -> IG_REEL_PUBLISHED, with any channel permitted to remain pending without reposting the channels that succeeded.

## Boundaries

Production QC completion and independent per-channel duplicate checks are required. No new daily manual approval should be necessary after one-time commissioning if the configured operating policy allows automatic QC-based release. This current development branch performs no publication, archive mutation, provider generation, R1b merge or live account configuration.

Archived Ep144 image QC reports 1080x1350 JPEG-compatible shape despite earlier canonical work referencing 1080x1440. Source PNG originals remain unchanged. Actual JPEG format is mandatory for Instagram Graph API posting.

References:
Meta Instagram: https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api
Meta Threads carousel: https://www.postman.com/meta/threads/request/34203612-b0861a47-db0e-4940-a692-2304669603b3
Meta Threads post deletion: https://www.postman.com/meta/threads/request/34203612-0a51cfc6-6407-4aec-974f-5bcbfbbf9da3
Archive root: https://drive.google.com/drive/folders/1QcCh-qMHOH97ZWdTLULwNygibJcZRb4q

## Account-boundary clarification (12 November 2026)

AI Geopolitic is an Instagram Creator/Professional account. The user has a Veni Publishing Facebook Page, but there is no separate AI Geopolitic Facebook Page. The existing Page is not evidence of any linkage to the AI Geopolitic Instagram account. Do not create or require a new Facebook Page for this publishing integration. Use Instagram API with Instagram Login directly, hosted at graph.instagram.com, requesting instagram_business_basic and instagram_business_content_publish. Never reuse the prior Veni Faithful account's Instagram ID or token; that repo is an architecture reference only.

The alternative Facebook Login API uses graph.facebook.com and requires an Instagram-linked Facebook Page. Do not mix the different token types, permissions, or API hosts. The draft Instagram client remains disconnected and disabled; this does not imply live OAuth or successful real-account testing.
