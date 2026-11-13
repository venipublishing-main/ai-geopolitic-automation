# Publisher orchestration correction — Repository owns the release

Date: 13 November 2026 (Africa/Johannesburg)

## Decision

The permanent AI Geopolitic publisher is operated by **GitHub Actions** in
`venipublishing-main/ai-geopolitic-automation`, not by a recurring ChatGPT
condition-watch. The ChatGPT Ep145 hourly watcher is a **one-day emergency bridge**
because the GitHub Actions rclone Drive token failed refresh. It is NOT the
production scheduler, nor a permanent dependency. The canonical Drive archive
remains the source of truth.

## Preferred event-driven path

1. Sisyphus completes and validates the episode, archives assets and writes
   the exact final production handoff (`PRODUCTION PASSED`) with Drive read-back
   evidence. An unfinished or partial production is NOT a publish trigger.
2. An authenticated, independently validating publisher intake obtains the
   handoff and exact Drive assets. Preferred direct event: the intake commits
   a unique, validated `publisher_signals/EpNNN.json` to the repository. An
   optional GitHub Action hourly poll provides recovery from missed handoffs.
   The signal creator must have verified Drive permission; never treat a
   self-declared unverified JSON file as independent QC.
3. A GitHub workflow handles the release, with concurrency lock, exact episode
   ID/date, 10 ordered slides, caption SHA-256, no past platform receipt,
   authenticated Meta account, QA media preflight, AI disclosure, permanent
   at-most-once claim and media/post permalink receipts.
4. New episodes run from the fixed archive parent
   `1QcCh-qMHOH97ZWdTLULwNygibJcZRb4q`, **not** from modified-date
   ordering, an unverified latest folder, or ChatGPT conversation content.
5. Channel results are independent: Instagram carousel, Threads carousel,
   then Instagram and Threads video. A successful channel never reposts just
   because another channel failed. The initial Ep145 test remains one
   clearly marked 10-image QA carousel, not the actual artwork.

## Present 13-Nov reality

- The one-time signal-driven release workflow ALREADY exists on main:
  `.github/workflows/ai-geopolitic-ep145-test-release.yml`.
- On the last recorded ChatGPT watch run at roughly 07:41 SAST, Ep145's
  `Ep145_PUBLISH_HANDOFF.json` and `Ep145_QC_Completion.json` were not present.
  No signal or Instagram post was created.
- GitHub's pre-existing `RCLONE_DRIVE_TOKEN` OAuth refresh was rejected
  (last authenticated runner probe, 12 November). Thus its current runner
  **cannot independently inspect the private Drive episode archive**.
  The ChatGPT Drive connector has a separate active authenticated identity.
- Do not add or activate a GitHub hourly publisher that simply trusts an
  unverified status file; this would weaken the production PASS boundary.
- The current one-day ChatGPT watcher may remain enabled as the Ep145
  contingency until a tested GitHub Drive intake (or independently verified,
  authenticated Sisyphus-to-GitHub signal) replaces it.
- After a successful GitHub-owned intake test, disable the ChatGPT watcher
  and remove ChatGPT from the production critical path. Do not have two
  competing signal writers; `publisher_signals` is create-once.

## GitHub-owned hourly fallback migration

**Prerequisite:** restore a durable read-only Google Drive credential in the
repository Actions secrets (existing rclone token or an approved equivalent).
Do not commit refresh tokens/configuration or expose them in workflow logs.
Verify exact access to the History parent and current episode archive from
an actual Actions run before turning on publishing.

Then add a GitHub Actions `schedule: 0 * * * *` monitor (plus
`workflow_dispatch`), with branch-concurrency and a metadata-only probe.
On successful handoff verification, create the unique episode signal.
On absent, pending or ambiguous handoff, perform no write and no post.
Commit of that signal triggers the already independent idempotent release
workflow. A direct Sisyphus event can make publishing faster than hourly
polling; hourly GitHub checks are for recovery and operational visibility.

## First-test guardrails

- Only Friday 13 November 2026 Ep145 is eligible under the current one-time
  release; no automatic fallback to Ep144.
- One ten-slide TEST ONLY Instagram carousel, original archived caption
  prefaced with the QA disclosure and `is_ai_generated=true`.
- Do not select random/unlicensed audio; Instagram static carousel Graph
  publishing does not expose a music-track attachment option.
- Never retry an uncertain Meta publish; reconcile by inspecting recorded
  durable claim and actual Instagram media.
- The user will manually delete the one test post after success.
- No production account or credential changes should occur merely because
  this architecture decision was recorded.

## Acceptance gate for removing ChatGPT

A GitHub Actions run must demonstrate that it can read the current Drive
handoff and QC with the restored credential, correctly block missing or
wrong inputs, write at most one signal, and produce no Meta POST before the
signal and release checks pass. Only then remove the ChatGPT watcher.
