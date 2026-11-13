"""Exact-archive Instagram carousel staging; safe for review, never publishing.

Reuses the independently verified production QC and loss-minimising JPEG
conversion already exercised by the Threads delivery pipeline. It produces
an Instagram-specific receipt, not a Threads publication authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from src.threads_media import (
    MAX_PNG,
    SHA_RE,
    ThreadsBlocked,
    _jpeg_from_png,
    read_approved_archive,
    safe_rclone,
    validate_episode,
    verify_caption,
)

STAGE_SCHEMA = "ai-geopolitic.instagram.stage-receipt.v1"
JPEG_SIZE = (1080, 1350)
COUNT = 10


class InstagramStageBlocked(ThreadsBlocked):
    """No fallback, implicit Instagram publishing, or partial valid output."""


def output_folder(episode: str, date_sast: str) -> Path:
    validate_episode(episode, date_sast)
    return Path("publisher_media") / f"instagram-{episode.lower()}-{date_sast.replace('-', '')}"


def validate_plan(plan: dict, caption: str, inventory: list[dict]) -> None:
    if not isinstance(plan, dict) or plan.get("schema") != "ai-geopolitic.threads.archive-plan.v1":
        raise InstagramStageBlocked("Plan must come from independent canonical Drive QC.")
    episode, _, _ = validate_episode(plan.get("episode"), plan.get("date_sast"))
    try:
        caption_digest = verify_caption(caption)
    except ThreadsBlocked:
        raise InstagramStageBlocked("Canonical Instagram caption failed publication QC.") from None
    if (plan.get("carousel_items") != COUNT
            or plan.get("production_passed") is not True
            or plan.get("approved_for_threads_publishing") is not False
            or caption_digest != plan.get("caption_sha256")):
        raise InstagramStageBlocked("Plan, production PASS or canonical caption is invalid.")
    slides = plan.get("slides")
    if not isinstance(slides, list) or len(slides) != COUNT:
        raise InstagramStageBlocked("Exactly ten QC-verified slides are required.")
    if not isinstance(inventory, list) or any(not isinstance(x, dict) for x in inventory):
        raise InstagramStageBlocked("Drive inventory is malformed.")
    by_name = {x.get("Name"): x for x in inventory}
    if len(by_name) != len(inventory):
        raise InstagramStageBlocked("Ambiguous source image names.")
    seen_source = set()
    for i, item in enumerate(slides, 1):
        source_name = f"{episode}_Slide{i:02d}of10.png"
        if (not isinstance(item, dict) or item.get("name") != source_name
                or not SHA_RE.fullmatch(str(item.get("sha256", "")))
                or item.get("dimensions") not in ([1080, 1350], [1080, 1440])
                or not isinstance(item.get("id"), str)
                or by_name.get(source_name, {}).get("ID") != item["id"]
                or by_name[source_name].get("MimeType") != "image/png"
                or item["sha256"] in seen_source):
            raise InstagramStageBlocked("Source carousel identity or uniqueness check failed.")
        seen_source.add(item["sha256"])


def stage(plan: dict, caption: str, inventory: list[dict], destination: Path) -> dict:
    """Downloads only exact archive PNGs; creates a private review-only stage."""
    destination = Path(destination)
    if destination.exists():
        raise InstagramStageBlocked("Existing Instagram stage may not be overwritten.")
    validate_plan(plan, caption, inventory)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="ig-review-", dir=destination.parent))
    try:
        media = []
        delivery_shas = set()
        remote = os.environ.get("AI_GEO_RCLONE_REMOTE", "ai_geopolitic_drive")
        for i, source in enumerate(plan["slides"], 1):
            raw = safe_rclone(
                "cat", f"{remote}:{source['name']}",
                plan["archive_folder_id"], limit=MAX_PNG,
            )
            jpg = _jpeg_from_png(raw, source["sha256"], source["dimensions"])
            digest = hashlib.sha256(jpg).hexdigest()
            if digest in delivery_shas:
                raise InstagramStageBlocked("Converted carousel frames are not unique.")
            delivery_shas.add(digest)
            filename = f"Slide{i:02d}of10.jpg"
            (staging / filename).write_bytes(jpg)
            media.append({"name": filename, "sha256": digest, "bytes": len(jpg),
                          "source_sha256": source["sha256"],
                          "width": JPEG_SIZE[0], "height": JPEG_SIZE[1]})
        (staging / "caption.txt").write_bytes(caption.encode("utf-8"))
        receipt = {
            "schema": STAGE_SCHEMA,
            "episode": plan["episode"], "date_sast": plan["date_sast"],
            "archive_folder_id": plan["archive_folder_id"],
            "caption_sha256": plan["caption_sha256"], "slide_count": COUNT,
            "media": media, "post_target": "INSTAGRAM_CAROUSEL_ONLY",
            "ai_info_required": True,
            "approved_for_publication": False, "published": False,
            "status": "STAGED_FOR_REVIEW_NOT_PUBLISHED",
        }
        (staging / "stage.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        staging.rename(destination)
        return receipt
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "stage"))
    parser.add_argument("--episode", required=True)
    parser.add_argument("--date-sast", required=True)
    args = parser.parse_args(argv)
    try:
        plan, caption, inventory = read_approved_archive(args.episode, args.date_sast)
        validate_plan(plan, caption, inventory)
        if args.mode == "plan":
            result = {"status": "INSTAGRAM_PREFLIGHT_PASS_NO_PUBLICATION",
                      "episode": plan["episode"], "slide_count": COUNT,
                      "caption_sha256": plan["caption_sha256"]}
        else:
            destination = output_folder(args.episode, args.date_sast)
            stage(plan, caption, inventory, destination)
            result = {"status": "STAGED_FOR_REVIEW_NOT_PUBLISHED",
                      "episode": plan["episode"], "folder": str(destination)}
        print(json.dumps(result))
        return 0
    except (ThreadsBlocked, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "INSTAGRAM_BLOCKED_NO_PUBLICATION", "reason": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
