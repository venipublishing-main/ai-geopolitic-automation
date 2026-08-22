# GitHub Actions → Google Drive setup for AI-Geopolitic

This setup will make the existing prototype-render workflow automatically upload rendered PNGs to the shared Google Drive folder.

## 1) Google Drive destination

Use this folder as the root working area:

AI-Geopolitical / Automation - Temporary Artifacts / Portrait Calibration

Folder IDs:
- AI-Geopolitical: `18f3kXjA3id1Bd0IbFkzdNq1aLceZeaKK`
- Automation - Temporary Artifacts: `1Ax7Afq1mnzQBdFvKUvkPgO1KhbKWITLj`
- Portrait Calibration: see below after creation

## 2) GitHub file to replace

Replace:

`.github/workflows/render-prototype-slide.yml`

with the provided updated version.

## 3) GitHub Secrets to add

Repo → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:

### `RCLONE_DRIVE_TOKEN`
This must be the full JSON token string produced by rclone OAuth for your Google account.
It looks roughly like:

`{"access_token":"...","token_type":"Bearer","refresh_token":"...","expiry":"..."}`

### `AI_GEOPOLITIC_DRIVE_ROOT_FOLDER_ID`
Set this to:

`18f3kXjA3id1Bd0IbFkzdNq1aLceZeaKK`

That is the `AI-Geopolitical` folder ID.

## 4) How to get the rclone token locally

On your own machine:

1. Install `rclone`
2. Run:

   `rclone config`

3. Create a new remote named something like `ai_geopolitic_drive`
4. Choose `drive`
5. Complete the Google login in the browser
6. When finished, open your local rclone config file and copy the entire `token = ...` JSON value

Typical config location:
- Windows: `%APPDATA%\\rclone\\rclone.conf`
- macOS/Linux: `~/.config/rclone/rclone.conf`

You only need the token JSON value, not the whole config file.

## 5) Result

When the workflow runs, it will:
- render the two PNGs
- upload the normal GitHub artifact
- copy the same PNGs to Google Drive

