# AI Geopolitic Threads publisher — v1

Scope: **10-image, canonical-caption Threads carousel to `@ai_geopolitic` only.** It is
independent of the successful Instagram Episode 145 publisher, contains no Reel,
video, Threads reply or music route, and does not run on a daily schedule.

## Release contract

1. Human selects exact `EpNNN` and its SAST production date (e.g. `Ep145`,
   `2026-11-13`). The workflow resolves exactly one archive folder beneath
   `History - Episode List`. Never select the newest or closest folder.
2. Drive QC completion and publisher handoff must show a full production PASS,
   ten verified numbered slide IDs and hashes, and zero defects. The historical
   Instagram-only handoff label does **not** grant Threads publication authority.
3. The **canonical CarouselCaption** must be exactly preserved; reject if more
   than 500 UTF-8 bytes, missing the locked footer or missing `#AIGeopolitic`.
   For Episode 145: **334 characters / 336 UTF-8 bytes**.
4. All ten original PNG checksums and dimensions are verified before generating
   ten 1080×1350 JPEGs, preserving each composition and order. The converted
   media and stage receipt live on a **separate, public, SHA-pinned GitHub media
   branch**, not in `main`. This provides public URLs for Meta's image fetch.
5. Before any Threads write, the publisher verifies all ten URLs are publicly
   reachable, checks the authorized Threads username is `ai_geopolitic`, checks
   recent posts for duplicate canonical *or Meta-normalized* caption, and **commits a one-time claim on `main`**
   in `publisher_state/threads-epNNN-YYYYMMDD.json`.
6. Only then create ten `IMAGE` carousel-item containers, one `CAROUSEL` parent
   with the untouched canonical caption, and call `/me/threads_publish`. Verify
   the published Threads post ID, username, permalink, `CAROUSEL_ALBUM` type,
   ten distinct child IDs and caption; update the same receipt. Meta removed
   **one `#` from an approved hashtag** in the real Episode 145 result; a
   single marker removed from one of the five locked hashtags is an explicitly
   recognized *readback* variant, not permission to modify the source caption.
   All other text changes still fail verification.
7. If anything fails after the durable claim, state remains
   `CLAIMED_NO_AUTOMATIC_RETRY`. **Stop and reconcile manually** before any
   human-directed recovery. An API timeout may mean the post was created.

## Launch procedure

1. Review/merge the implementation PR after CI is green. Do not merge the
   existing unrelated generic publisher PR as a dependency.
2. In the repository's **Settings → Secrets and variables → Actions**, add
   `AI_GEO_THREADS_ACCESS_TOKEN` as a **GitHub repository secret**, never in
   source code, a handoff JSON, or ChatGPT. Obtain a **Threads User Access Token**
   for `@ai_geopolitic` with `threads_basic` and `threads_content_publish` via
   the Threads API Meta app use case. It is **not** the Instagram access token.
   Existing GitHub Drive secrets are reused:
   `RCLONE_DRIVE_CLIENT_ID`, `RCLONE_DRIVE_CLIENT_SECRET`,
   `RCLONE_DRIVE_TOKEN`, `AI_GEOPOLITIC_DRIVE_ROOT_FOLDER_ID`.
   Renew the Threads token before its expiry under Meta's long-lived token rules.
3. Open **Actions → AI Geopolitic Threads — ten-image carousel (human gate) →
   Run workflow** on `main`. First choose `mode=plan` with exact episode and
   SAST date. Confirm `PREFLIGHT_PASSED_NO_PUBLICATION` with ten slides and the
   500-byte caption check. This run never calls the Threads API.
4. After Ian inspects and explicitly approves Threads publication, launch
   `mode=publish` on `main` with the same episode/date and the literal
   confirmation `PUBLISH_THREADS_EP145_20261113` (for Episode 145).
   **This triggers a real public Threads post; only run once.**
5. Inspect the receipt's `PUBLISHED_VERIFIED` state and the link in its
   `threads_permalink`. If `CLAIMED_NO_AUTOMATIC_RETRY`, do not rerun: inspect
   `@ai_geopolitic` and the Graph API outcome manually.

## Episode 145 incident and resolution

- Live workflow run `43412922861` published the carousel at 12:57:59 SAST on
  13 November 2026, but returned `BLOCKED_OR_RECONCILE` because Threads'
  readback text dropped one `#` from the untouched 334-character source.
- A **GET-only** reconciliation run `43414290650` confirmed account
  `ai_geopolitic`, post `18470584774185284`, `CAROUSEL_ALBUM`, **ten child
  images**, and permalink
  <https://www.threads.com/@ai_geopolitic/post/DfreDZkoNcp>.
- The canonical caption was 334 characters; Meta returned 333 characters.
  The only difference was a missing hashtag marker. No retry was made. The
  durable receipt on `main` was reconciled to `PUBLISHED_VERIFIED`.
- The updated parser accepts only this narrow normalization after full media,
  identity and permalink verification. The existing at-most-once claim remains
  mandatory and is never removed to clear a failed job.

## API references and restrictions

- Meta Threads API `POST /me/threads` with `media_type=IMAGE`,
  `image_url`, `is_carousel_item=true`; ten separate items.
- Meta Threads API `POST /me/threads` with `media_type=CAROUSEL`,
  `children=<ten ordered container IDs>`, and the approved `text`.
- Meta Threads API `POST /me/threads_publish` with `creation_id`.
- Status polling and verification use the read-only Threads Graph API.
- Meta official API collection: <https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api>.

No audio sourcing, no Instagram edits, no Story/Reel publication, no manual
browser interaction, and no cross-posting to a different account is authorized
by this workflow. Instagram Episode 145 is already published and is untouched.
