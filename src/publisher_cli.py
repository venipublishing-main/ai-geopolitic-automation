"""Safe draft publishing CLI: find today's exact archive, verify and stage carousel.

There is deliberately NO Instagram API call or automatic schedule here yet.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .publisher_archive import (
    PublisherBlocked, manual_exclusion, plan_carousel, sast_today, select_episode,
)
from .publisher_delivery import create_test_deck, to_api_jpeg
from .publisher_drive import RclonePublisherArchive

DEFAULT_HISTORY = Path(__file__).resolve().parents[1] / "config/publisher_manual_exclusions.json"


def load_history(path: Path = DEFAULT_HISTORY) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise PublisherBlocked("Manual publication exclusion ledger is unavailable.") from exc
    if not isinstance(data, dict) or data.get("schema") != "ai-geopolitic.publisher.manual-exclusions.v1":
        raise PublisherBlocked("Manual publication exclusion ledger has wrong schema.")
    return data


def evaluate(source: RclonePublisherArchive, *,
             for_day: date | None = None, explicit_episode: str | None = None,
             history: dict | None = None) -> tuple[dict, str, object, list[dict]]:
    day = for_day or sast_today()
    episode = select_episode(source.list_folders(), day=day,
                             explicit_episode=explicit_episode)
    file_entries = source.list_files(episode)
    qc = source.read_json(episode, file_entries)
    caption = source.read_caption(episode, file_entries)
    plan = plan_carousel(episode, file_entries, qc, caption,
                         manual_history=history if history is not None else load_history())
    return plan, caption, episode, file_entries


def stage_from_plan(source: RclonePublisherArchive, plan: dict,
                    caption: str, episode, files: list[dict],
                    output_dir: Path) -> dict:
    """Use precisely the ten pinned QC IDs/SHAs; never mutate the archive."""
    out = Path(output_dir) / episode.episode_id
    # Do not overwrite any previous staged version without explicit cleanup.
    if out.exists():
        raise PublisherBlocked("Staging directory already exists; refusing to overwrite.")
    out.mkdir(parents=True)
    exported = []
    try:
        for slide in plan["slides"]:
            raw = source.read_bytes(episode, files, slide["name"], slide["file_id"],
                                    max_bytes=40_000_000)
            jpeg = to_api_jpeg(raw, source_sha256=slide["source_sha256"],
                               expected_dimensions=slide["source_dimensions"])
            name = slide["name"].removesuffix(".png") + ".jpg"
            (out / name).write_bytes(jpeg)
            import hashlib
            exported.append({"name": name, "sha256": hashlib.sha256(jpeg).hexdigest(),
                             "bytes": len(jpeg), "source_file_id": slide["file_id"]})
        (out / "caption.txt").write_text(caption, encoding="utf-8")
        delivery = {
            "episode": plan["episode"], "day": plan["production_date_sast"],
            "source_archive_folder_id": plan["archive_folder_id"],
            "images": exported, "mode": "STAGED_NOT_PUBLISHED",
            "instagram_post_id": None, "public_image_urls": [],
            "no_live_post_allowed": True,
        }
        (out / "delivery_manifest.json").write_text(
            json.dumps(delivery, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return delivery
    except Exception:
        # A partial stage is never a valid deliverable.
        for item in out.iterdir():
            if item.is_file():
                item.unlink()
        out.rmdir()
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("plan", "stage", "test-deck"),
                        default="plan")
    parser.add_argument("--date", help="SAST production day YYYY-MM-DD (default: today)")
    parser.add_argument("--episode", help="Explicit EpNNN for a historical dry-run (never repost)")
    parser.add_argument("--out", type=Path, default=Path("output/publisher-v1"))
    args = parser.parse_args(argv)
    try:
        if args.mode == "test-deck":
            details = create_test_deck(args.out / "TEST_DECK")
            print(json.dumps({"status": "TEST_ASSETS_CREATED", "count": details["carousel_count"],
                              "path": str(args.out / "TEST_DECK"),
                              "published": False}, indent=2))
            return 0
        day = date.fromisoformat(args.date) if args.date else sast_today()
        source = RclonePublisherArchive.from_environment()
        plan, caption, episode, files = evaluate(
            source, for_day=day, explicit_episode=args.episode
        )
        if args.mode == "stage":
            delivery = stage_from_plan(source, plan, caption, episode, files, args.out)
            print(json.dumps({"status": "STAGED", "episode": plan["episode"],
                              "count": len(delivery["images"]), "published": False,
                              "path": str(args.out / plan["episode"])}, indent=2))
        else:
            print(json.dumps({"status": "DRY_RUN_READY", "published": False,
                              "plan": plan}, indent=2))
        return 0
    except (PublisherBlocked, OSError, ValueError) as exc:
        # No caption, editorial copy, credentials, token, or rclone stderr in stdout.
        message = str(exc) if isinstance(exc, PublisherBlocked) else "Invalid input or local I/O."
        print(json.dumps({"status": "BLOCKED", "reason": message, "published": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
