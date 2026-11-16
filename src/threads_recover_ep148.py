"""One-shot, claim-preserving recovery for confirmed-unpublished Ep148 Threads.

Never runs on a schedule. An existing original claim remains immutable until a
second exact-episode publication has been verified on Threads. A separate
durable recovery claim is written to main *before* making a Meta POST.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from src.threads_media import ThreadsBlocked, output_folder
from src.threads_release import (
    ThreadsGraph,
    _git,
    check_stage,
    save_state,
    state_path,
    verify_public_images,
)


EPISODE = "Ep148"
DAY = "2026-11-16"
ORIGINAL_RUN = "43810385187"
READ_ONLY_RUN = "43826454452"
EXPECTED_APPROVAL = "RECOVER_THREADS_EP148_20261116_AFTER_NEGATIVE_RECONCILIATION"
SIGNAL = Path("publisher_signals/threads-ep148-recovery-20261116.json")
RECOVERY_CLAIM = Path("publisher_state/threads-ep148-recovery-20261116.json")
EXPECTED_ACCOUNT = "ai_geopolitic"
EXPECTED_USER_ID = "40667622232822942"


def validate_recovery_inputs(original: dict, signal: dict, *, run_id: str) -> str:
    """Accept only the single previously investigated publication incident."""
    expected_state = {
        "episode": EPISODE,
        "date_sast": DAY,
        "status": "CLAIMED_NO_AUTOMATIC_RETRY",
        "github_run_id": ORIGINAL_RUN,
        "threads_account": EXPECTED_ACCOUNT,
        "threads_user_id": EXPECTED_USER_ID,
        "carousel_items": 10,
    }
    if any(original.get(key) != value for key, value in expected_state.items()):
        raise ThreadsBlocked("Original Ep148 claim is not the exact unresolved incident.")
    source = str(original.get("public_media_commit", ""))
    if not re.fullmatch(r"[a-f0-9]{40}", source):
        raise ThreadsBlocked("Original immutable media commit is invalid.")
    if not re.fullmatch(r"[a-f0-9]{64}", str(original.get("caption_sha256", ""))):
        raise ThreadsBlocked("Original caption fingerprint is invalid.")
    required_signal = {
        "schema": "ai-geopolitic.threads.manual-recovery.v1",
        "episode": EPISODE,
        "date_sast": DAY,
        "original_failed_run_id": ORIGINAL_RUN,
        "read_only_reconciliation_run_id": READ_ONLY_RUN,
        "confirmation": EXPECTED_APPROVAL,
    }
    if any(signal.get(key) != value for key, value in required_signal.items()):
        raise ThreadsBlocked("Exact incident recovery signal or authorization missing.")
    if not run_id.isdigit() or not os.environ.get("GITHUB_ACTIONS") == "true":
        raise ThreadsBlocked("Recovery can execute only inside GitHub Actions.")
    return source


def restore_immutable_stage(commit: str) -> None:
    """Read the exact original published media commit; never regenerate assets."""
    folder = output_folder(EPISODE, DAY)
    folder.mkdir(parents=True, exist_ok=True)
    for name in ["stage.json", "caption.txt", *[f"Slide{i:02d}of10.jpg" for i in range(1, 11)]]:
        source = f"{commit}:{folder.as_posix()}/{name}"
        try:
            data = subprocess.run(["git", "show", source], check=True,
                                  capture_output=True, timeout=30).stdout
        except (OSError, subprocess.SubprocessError):
            raise ThreadsBlocked("Cannot load original pinned Threads media; no Meta POST.") from None
        if not data or len(data) > 8 * 1024 * 1024:
            raise ThreadsBlocked("Original pinned Threads media is empty or oversized.")
        (folder / name).write_bytes(data)


class DiagnosticGraph(ThreadsGraph):
    """On failure, identify which of the twelve Meta write phases was reached."""

    def __init__(self, token: str):
        super().__init__(token)
        self.write_number = 0

    def request(self, method: str, path: str, params: dict | None = None) -> dict:
        if method == "POST":
            self.write_number += 1
        try:
            return super().request(method, path, params)
        except ThreadsBlocked as exc:
            phase = (
                f"child_{self.write_number}_of_10" if self.write_number <= 10
                else "parent_carousel" if self.write_number == 11
                else "publish_container" if self.write_number == 12
                else "unexpected"
            )
            print(json.dumps({"status": "THREADS_META_STEP_FAILED",
                              "last_meta_post_stage": phase,
                              "method": method,
                              "error": str(exc),
                              "automatic_retry_allowed": False}))
            raise


def recover() -> dict:
    if _git("branch", "--show-current") != "main":
        raise ThreadsBlocked("Recovery must execute on main.")
    state = state_path(EPISODE, DAY)
    original = json.loads(state.read_text(encoding="utf-8"))
    signal = json.loads(SIGNAL.read_text(encoding="utf-8"))
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if RECOVERY_CLAIM.exists() or _git("ls-files", "--", str(RECOVERY_CLAIM)):
        raise ThreadsBlocked("One-shot Ep148 recovery has already been claimed; never repeat.")
    source = validate_recovery_inputs(original, signal, run_id=run_id)
    restore_immutable_stage(source)
    staged, caption, urls = check_stage(EPISODE, DAY, source)
    if staged["caption_sha256"] != original["caption_sha256"]:
        raise ThreadsBlocked("Original and staged caption fingerprints disagree.")
    verify_public_images(urls)
    graph = DiagnosticGraph(os.environ.get("AI_GEO_THREADS_ACCESS_TOKEN", ""))
    user_id, username = graph.check_identity_and_duplicate(caption)
    if user_id != EXPECTED_USER_ID or username != EXPECTED_ACCOUNT:
        raise ThreadsBlocked("Meta account does not match original claim.")
    print(json.dumps({"status": "READ_ONLY_NEGATIVE_CHECK_PASSED",
                      "episode": EPISODE, "public_media_commit": source,
                      "meta_write_performed": False}))

    # Avoid a concurrent receipt write between our preflight and recovery claim.
    _git("pull", "--ff-only", "origin", "main")
    if RECOVERY_CLAIM.exists() or _git("ls-files", "--", str(RECOVERY_CLAIM)):
        raise ThreadsBlocked("Concurrent recovery claim detected; aborting.")
    latest = json.loads(state.read_text(encoding="utf-8"))
    validate_recovery_inputs(latest, signal, run_id=run_id)
    recovery = {
        "schema": "ai-geopolitic.threads.manual-recovery-receipt.v1",
        "episode": EPISODE, "date_sast": DAY,
        "original_claim": str(state),
        "original_failed_run_id": ORIGINAL_RUN,
        "read_only_reconciliation_run_id": READ_ONLY_RUN,
        "recovery_run_id": run_id,
        "source_media_commit": source,
        "caption_sha256": staged["caption_sha256"],
        "status": "RECOVERY_CLAIMED_NO_REPEAT",
        "claimed_utc": datetime.now(timezone.utc).isoformat(),
    }
    save_state(RECOVERY_CLAIM, recovery)  # Durably commit before any Meta write.
    print(json.dumps({"status": "ONE_SHOT_RECOVERY_CLAIM_PERSISTED",
                      "meta_write_will_follow": True}))

    result = graph.publish_carousel(caption, urls)

    # If either receipt update fails, durable recovery claim prevents repeats.
    latest.update(result)
    latest.update({
        "status": "PUBLISHED_VERIFIED",
        "published_utc": datetime.now(timezone.utc).isoformat(),
        "recovery_run_id": run_id,
        "recovery_claim": str(RECOVERY_CLAIM),
        "read_only_reconciliation_run_id": READ_ONLY_RUN,
    })
    save_state(state, latest)
    recovery.update(result)
    recovery["status"] = "RECOVERY_PUBLISHED_VERIFIED"
    recovery["published_utc"] = latest["published_utc"]
    save_state(RECOVERY_CLAIM, recovery)
    return {"status": "PUBLISHED_VERIFIED_BY_ONE_SHOT_RECOVERY",
            "episode": EPISODE, "permalink": result["threads_permalink"],
            "carousel_items_verified": result["carousel_items_verified"]}


def main() -> int:
    try:
        print(json.dumps(recover()))
        return 0
    except (ThreadsBlocked, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED_OR_RECONCILE",
                          "reason": str(exc),
                          "automatic_retry_allowed": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
