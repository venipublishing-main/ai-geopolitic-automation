# AI Geopolitic — three independent video publishing Actions

**Created:** 19 November 2026. **Mode:** manual, individually gated, GitHub Actions only.
This adds three publishers; it does **not** modify the existing automatic
carousel controller or the existing Reel *review-only* workflow.

## Responsibility boundary

Sisyphus generates and archives the editorial assets with a production PASS.
GitHub Actions independently verifies the canonical Drive QC and Sisyphus
handoff, renders the accepted video, owns Meta credentials, publishes, and saves
receipts. **Sisyphus must not log into or call Instagram/Threads directly.**

## Three new Actions

| GitHub workflow | Destination | Caption sent | Manual confirmation pattern | Receipt |
|---|---|---|---|---|
| `ai-geopolitic-instagram-reel.yml` | Instagram Reel (also shared to feed) | Exact archived Reel caption | `PUBLISH_INSTAGRAM_REEL_EPNNN_YYYYMMDD` | `publisher_state/instagram-reel-epnnn-yyyymmdd.json` |
| `ai-geopolitic-threads-video.yml` | Threads native video post | Exact archived Reel caption | `PUBLISH_THREADS_VIDEO_EPNNN_YYYYMMDD` | `publisher_state/threads-video-epnnn-yyyymmdd.json` |
| `ai-geopolitic-instagram-story.yml` | Instagram video Story | **None: never send a caption** | `PUBLISH_INSTAGRAM_STORY_EPNNN_YYYYMMDD` | `publisher_state/instagram-story-epnnn-yyyymmdd.json` |

For example, on `Ep151 / 2026-11-19` the Instagram Reel confirmation is
`PUBLISH_INSTAGRAM_REEL_EP151_20261119`.

To preview without publishing: open **Actions**, choose the precise publisher,
select `main`, provide the exact episode and archive date, and select `plan`.
The plan is read-only. To publish, explicitly choose `publish` and enter that
surface's exact confirmation. Neither `plan` nor a failed preflight publishes.

## Locked inputs and media staging

- **Canonical Drive**: one exact archive episode/date, complete Sisyphus
  `PRODUCTION PASSED` handoff, independently verified 10-slide QC, six numbered
  1080×1920 Reel PNGs and exact UTF-8 Reel caption. No latest-folder fallback.
- **Visual**: same accepted 18s, six-frame video, with the stabilised 12% zoom,
  0.9s beginning/end fades and five central circular flare transitions.
- **Sound**: exact Veni Sonora VS001 Version B master, SHA-256
  `3c0824d3af1cba53a60edd1757e95d7ea8b400af5d2e8f13d7dd0da4d7e8c3b3`.
  No new music, fallback audio or silent tracks.
- **Public staging**: the first publisher renders a single H.264/AAC MP4,
  pins `reel.mp4` + canonical `caption.txt` + `stage.json` to one shared,
  immutable episode-specific public Git commit. The other two publishers
  reuse it **only after comparing the source frames, caption, archive ID,
  soundtrack checksum and video codecs against the same current Drive QC**.
  Each then verifies the public video's SHA-256 before its own Meta POST.
  Source images and music are not published. Reusing one commit avoids storing
  three identical videos per day.

This approach follows Meta's public-URL requirements for [Instagram Reels](https://www.postman.com/meta/instagram/folder/830j7my/reels-publishing)
and [Threads videos](https://www.postman.com/meta/threads/request/34203612-a51eb091-5c5e-436a-b4bb-c3d53c8aa901).
Stories use Instagram's `media_type=STORIES`, which requires a **Business**
account under Facebook Login. The publisher checks that account type, targets
only `@ai_geopolitic`, and never passes the Reel caption to Story creation.

## Safety and manual incident procedure

1. The action must see correct episode/date, successful QC, target account,
   exact media bytes, and literal publish approval before making a Meta POST.
2. A **surface-specific, episode-specific** `CLAIMED_NO_AUTOMATIC_RETRY` record
   is pushed to `main` **before the first Meta POST**. If the push fails, no
   Meta write may happen. An existing claim blocks a second attempt.
3. Instagram Reel verifies the returned media as `REELS` and checks its
   permalink and AI-information flag. Instagram Story verifies `STORY` with
   its media ID and AI flag; Story permalink is optional. Threads creates the
   video container with `is_made_with_ai=true` (the official Threads AI info
   label switch), and verifies `VIDEO`, the account, caption equivalence, and
   its permalink. Its receipt records that AI disclosure was submitted to Meta,
   not a separately read-back display flag.
4. After an ambiguous outcome, **do not rerun `publish`**. Inspect the Meta
   account and the immutable claim. Reconcile manually using evidence, never
   reset/delete the claim to force another upload.

No hosted Meta tests or real posts were triggered when these three Actions
were implemented. There are no new paid integrations or new Meta secrets; they
reuse `AI_GEO_IG_ACCESS_TOKEN`, `AI_GEO_THREADS_ACCESS_TOKEN`, and the existing
read-only rclone Drive configuration.

The daily automatic dispatcher currently dispatches only the two carousel
workflows. **Wiring these new actions into scheduling remains a separate task**
to fix the automatic-release issues, as Ian requested.
