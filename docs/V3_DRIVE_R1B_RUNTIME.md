# R1b — Authenticated live-Drive read-only integration

**Date:** 4 November 2026 (SAST)  
**PR:** #1, draft against `automation-v2`  
**State:** Implementation available for a local authorized Drive run; no real rclone-OAuth execution observed in this connected development runtime.

## Purpose

The active 10-slide gate must not declare input BUILD readiness merely because the R&D and Slide Design text describes an archive folder and canonical portrait IDs. The application now has an isolated authenticated Drive verifier using rclone's read-only `lsjson` and `cat` commands. No external image provider or publisher is wired to this executable.

## Fixed Drive identity boundaries

The code pins the current native Google Docs by **both folder ID and file ID**:

- Daily Operations parent: `1oVynOtXYo0YQCAZ9Mcvhs0OM5lpF_c7J`
- Native Daily R&D: `1GBvuPF_C4Lna5sZiE5FSthv10J0gmorqdiTnbBgcds4` → exported `Daily R&D.txt`
- Native Daily Slide Design: `19PgSfKDLCSZt0YrjVbXDHz-nkN728CxBjkySEh4GVNs` → exported `Daily Slide Design.txt`
- History - Episode List parent: `1QcCh-qMHOH97ZWdTLULwNygibJcZRb4q`; archive must match the **current** metadata's exact declared folder ID and `EpNNN-DMonthYYYY` folder name
- Canonical panelist parent: `1CYYVI5jXH0lgJBPmqP3VqE9mKrbUva5J`; each assigned portrait must match the corresponding ID in `V3_PORTRAIT_IDS`, approved `*_CANONICAL_PANELIST.png` filename, `image/png` MIME, positive bounded byte length, actual PNG raster and at least one nonopaque alpha pixel

If the Google Drive account cannot access any pinned ID or parent, the verifier returns BLOCKED. Filename alone never constitutes identity evidence; duplicate matches block. The runtime does not accept an alternate portrait from another folder.

## Read-only commands and limits

The verifier uses an existing *locally authorized* rclone Google Drive remote and calls only:

- `rclone lsjson <remote>: --drive-root-folder-id <known-parent> --files-only|--dirs-only`
- `rclone lsjson <remote>: --drive-root-folder-id <Daily-Operations-parent> --files-only --drive-export-formats txt`
- `rclone cat <remote>:<approved-filename> --drive-root-folder-id <known-parent>`

The exact argument arrays are passed to `subprocess.run` **without a shell**. No `copy`, `sync`, `move`, `delete`, `purge`, `mkdir`, `rc`, `serve` or provider POST is present. Each authenticated call has a timeout. Portrait transfers are bounded at 8 MiB and native-document text exports at 1 MiB via `--count`; the application rejects missing/oversized/wrong-type content.

Command arguments, OAuth tokens and full document contents are never emitted in the CLI's JSON result. Remote failures return sanitized blockers; rclone stderr is not exposed. Current document text is held transiently in process memory and is not committed, saved or transmitted elsewhere by the application.

## Execution

On a workstation or trusted runner with an existing authorized `ai_geopolitic_drive` remote, from the repository root:

```powershell
python -m pip install -r requirements.txt
python -m src.v3_drive_readiness --json
```

Optional environment overrides:

```powershell
$env:AI_GEOPOLITIC_DRIVE_REMOTE = 'ai_geopolitic_drive'
$env:AI_GEOPOLITIC_RCLONE = 'rclone'
```

Use a Google Drive `drive.readonly` scoped rclone connection if feasible. Google Docs are exported to TXT read-only. Existing legacy CLI `python -m src.daily_readiness` remains the historical 20-slide validator and is **not a v3 authorization signal**. The active v3 CLI does NOT depend on setting `AI_GEOPOLITIC_RND_PATH` or `AI_GEOPOLITIC_SLIDE_DESIGN_PATH`: it reads the pinned documents via Drive IDs.

A successful result means **BUILD INPUTS ARE READY** for the current SAST episode, **not** image generation or publication permission. No user approval, image export, portrait pixel identity or Ep128 aesthetic QC is implied by input readiness.

## Offline CI and first live run boundary

Tests in `tests/test_v3_drive_proof.py` inject a fake subprocess rather than requesting Google credentials. They cover exact native text ID matching, archive folder ID/name/parent, six canonical PNG identities, transparency, corrupted/opaque images, duplicate names and IDs, bad MIME, wrong sizes, missing OAuth/rclone, malformed responses and a full read-only CLI path. R1 tests still check the historical 20-slide and active ten-slide contracts independently.

These tests validate the *implementation*, not the owner's current live rclone authorization. **No Google OAuth token or rclone config has been placed in GitHub, a test fixture or the recovery diary.** A live run on an authenticated machine must produce a sanitized `READY` result before the runtime integration is considered operational.

## Remaining safety and design boundaries

- Google Drive reads are sequential, not atomic; the production operator should recheck freshness before actual draft BUILD.
- Verified `image/png` transparency is not byte-for-byte agreement with the originally approved canonical pixels. A later compositor/QC stage must preserve canonical pixels.
- Image dimensions of archived 10× carousel and 6× reel outputs, visual design quality, human acceptance and Meta publishing remain separate later gates.
- The current roster and Drive IDs come from 4 November v3 authority; later canon revisions must update this pinned boundary explicitly.
- This PR must remain draft/unmerged until review and a live configured-run checkpoint. No background monitoring or automatic execution is enabled.

**Authority:** [Automation v3](https://docs.google.com/document/d/1s4VrG66Z3V-uidPzqtr6VqlKYGTUY6pr0uyHMmfsagg/edit) • [Production Contract v3](https://docs.google.com/document/d/1b3gN0qELVsZtTbe8TAlnhai1EigiuOhexecI7cIyVmY/edit) • [Recovery Handover](https://docs.google.com/document/d/14-Pr08MGMiW0d-hMCQWcLGIPxXpq4QZyZGw0qZHdMmY/edit)
