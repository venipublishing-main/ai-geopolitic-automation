"""Reusable one-time, episode-authorized Instagram 10-image carousel publisher.

Release is deliberately GitHub Actions-only. It pins the original Drive-QC
media to a public immutable Git commit, writes a durable main-branch claim
BEFORE any Meta POST, and never automatically retries an uncertain result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image

from src.instagram_graph import (
    HOST, InstagramGraph, InstagramPublishBlocked, UrlLibGraphTransport,
    validate_public_urls,
)
from src.instagram_media import STAGE_SCHEMA, output_folder
from src.threads_media import ThreadsBlocked, validate_episode, verify_caption

GITHUB_RAW = "https://raw.githubusercontent.com/venipublishing-main/ai-geopolitic-automation"
COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")
MAX_JPEG = 8 * 1024 * 1024


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_stage(episode: str, day: str, commit: str, root: Path = Path(".")) -> tuple[dict, str, list[str]]:
    validate_episode(episode, day)
    if not COMMIT_RE.fullmatch(commit):
        raise InstagramPublishBlocked("Media must be pinned to an immutable Git commit.")
    folder = root / output_folder(episode, day)
    receipt = json.loads((folder / "stage.json").read_text(encoding="utf-8"))
    if (receipt.get("schema") != STAGE_SCHEMA
            or receipt.get("episode") != episode or receipt.get("date_sast") != day
            or receipt.get("slide_count") != 10
            or receipt.get("post_target") != "INSTAGRAM_CAROUSEL_ONLY"
            or receipt.get("ai_info_required") is not True
            or receipt.get("approved_for_publication") is not False
            or receipt.get("published") is not False
            or receipt.get("status") != "STAGED_FOR_REVIEW_NOT_PUBLISHED"):
        raise InstagramPublishBlocked("Stage receipt is not an unpublished exact carousel.")
    caption = (folder / "caption.txt").read_text(encoding="utf-8")
    if verify_caption(caption) != receipt.get("caption_sha256"):
        raise InstagramPublishBlocked("Canonical caption differs from its verified SHA-256.")
    media = receipt.get("media")
    if not isinstance(media, list) or len(media) != 10:
        raise InstagramPublishBlocked("Instagram stage must have exactly ten ordered slides.")
    urls, digests = [], set()
    for i, record in enumerate(media, 1):
        filename = f"Slide{i:02d}of10.jpg"
        if (not isinstance(record, dict) or record.get("name") != filename
                or record.get("width") != 1080 or record.get("height") != 1350
                or not isinstance(record.get("bytes"), int)
                or not re.fullmatch(r"[0-9a-f]{64}", str(record.get("source_sha256", "")))):
            raise InstagramPublishBlocked("Staged slide source or dimensions are invalid.")
        data = (folder / filename).read_bytes()
        digest = sha(data)
        if (not 0 < len(data) < MAX_JPEG or len(data) != record["bytes"]
                or digest != record.get("sha256") or digest in digests):
            raise InstagramPublishBlocked("Staged JPEG bytes or uniqueness checks failed.")
        digests.add(digest)
        with Image.open(folder / filename) as image:
            if image.format != "JPEG" or image.size != (1080, 1350):
                raise InstagramPublishBlocked("Staged carousel image has invalid pixels.")
        urls.append(f"{GITHUB_RAW}/{commit}/{output_folder(episode, day).as_posix()}/{filename}")
    validate_public_urls(urls)
    return receipt, caption, urls


def verify_public_images(receipt: dict, urls: list[str]) -> None:
    """Recheck every public image byte against its staged SHA before Meta POST."""
    validate_public_urls(urls)
    for i, link in enumerate(urls):
        try:
            req = Request(link, method="GET",
                          headers={"User-Agent": "ai-geopolitic-instagram-preflight/1.0"})
            with urlopen(req, timeout=30) as result:
                content_type = result.headers.get("Content-Type", "").split(";", 1)[0].lower()
                raw = result.read(MAX_JPEG + 1)
                if (result.status != 200 or content_type not in ("image/jpeg", "image/jpg")
                        or not raw.startswith(b"\xff\xd8\xff")
                        or len(raw) != receipt["media"][i]["bytes"]
                        or sha(raw) != receipt["media"][i]["sha256"]):
                    raise InstagramPublishBlocked("Public JPEG differs from verified stage.")
        except (HTTPError, URLError, TimeoutError, OSError):
            raise InstagramPublishBlocked("Public media is not safely reachable; no Meta POST.") from None


def _git(*args: str) -> str:
    try:
        result = subprocess.run(["git", *args], check=True, capture_output=True,
                                text=True, timeout=90)
    except (OSError, subprocess.SubprocessError):
        raise InstagramPublishBlocked("Durable GitHub claim unavailable; manual reconciliation required.") from None
    return result.stdout.strip()


def state_path(episode: str, day: str) -> Path:
    validate_episode(episode, day)
    return Path("publisher_state") / f"instagram-{episode.lower()}-{day.replace('-', '')}.json"


def save_state(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _git("add", "--", str(path))
    _git("commit", "-m", f"Instagram {record['episode']}: {record['status']}")
    _git("push", "origin", "HEAD:refs/heads/main")


def release(episode: str, day: str, commit: str, approval: str,
            *, token: str, run_id: str) -> dict:
    validate_episode(episode, day)
    if approval != f"PUBLISH_INSTAGRAM_{episode.upper()}_{day.replace('-', '')}":
        raise InstagramPublishBlocked("No exact episode-scoped Instagram authorization.")
    if os.environ.get("GITHUB_ACTIONS") != "true" or not run_id.isdigit():
        raise InstagramPublishBlocked("Live publishing is only allowed in GitHub Actions.")
    if _git("branch", "--show-current") != "main":
        raise InstagramPublishBlocked("Instagram release must run from main.")
    if not isinstance(token, str) or len(token) < 16 or "\n" in token:
        raise InstagramPublishBlocked("Instagram token is missing or invalid.")
    receipt, caption, urls = check_stage(episode, day, commit)
    verify_public_images(receipt, urls)
    graph = InstagramGraph(UrlLibGraphTransport(token))
    ig_id = graph.account(caption)
    _git("pull", "--ff-only", "origin", "main")
    state = state_path(episode, day)
    if state.exists() or _git("ls-files", "--", str(state)):
        raise InstagramPublishBlocked("Existing Instagram claim/receipt forbids duplicate publishing.")
    record = {
        "schema": "ai-geopolitic.instagram.publication-receipt.v1",
        "episode": episode, "date_sast": day,
        "instagram_account": "ai_geopolitic", "instagram_user_id": ig_id,
        "caption_sha256": receipt["caption_sha256"], "carousel_items": 10,
        "public_media_commit": commit, "github_run_id": run_id,
        "claimed_utc": datetime.now(timezone.utc).isoformat(),
        "ai_info_required": True, "status": "CLAIMED_NO_AUTOMATIC_RETRY",
    }
    save_state(state, record)  # The critical irreversible gate: BEFORE the first Meta write.
    media_id = graph.publish(ig_id, urls, caption)
    record["instagram_media_id"] = media_id
    try:
        outcome = graph.verify_publication(media_id)
        record.update(outcome)
        record["status"] = ("PUBLISHED_AI_INFO_VERIFIED" if outcome["ai_info_verified"]
                            else "PUBLISHED_AI_INFO_UNVERIFIED")
    except InstagramPublishBlocked:
        record["status"] = "PUBLISHED_RECEIPT_UNVERIFIED"
    record["published_utc"] = datetime.now(timezone.utc).isoformat()
    save_state(state, record)
    if record["status"] != "PUBLISHED_AI_INFO_VERIFIED":
        raise InstagramPublishBlocked("Post may be live but AI label or permalink needs manual reconciliation.")
    return {"status": record["status"], "episode": episode,
            "permalink": record["instagram_permalink"], "carousel_items": 10}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode", required=True)
    parser.add_argument("--date-sast", required=True)
    parser.add_argument("--media-commit", required=True)
    parser.add_argument("--approval", required=True)
    args = parser.parse_args(argv)
    try:
        result = release(args.episode, args.date_sast, args.media_commit, args.approval,
                         token=os.environ.get("AI_GEO_IG_ACCESS_TOKEN", ""),
                         run_id=os.environ.get("GITHUB_RUN_ID", ""))
        print(json.dumps(result))
        return 0
    except (ThreadsBlocked, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "BLOCKED_OR_RECONCILE", "reason": str(exc),
                          "automatic_retry_allowed": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
