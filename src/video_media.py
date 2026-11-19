"""Verify one exact archive and stage its approved 18s Reel as immutable MP4.

This is a media builder, never a Meta client. It renders ONLY the accepted 12%
variant with the SHA-pinned VS001 Version B recording. The public staging folder
contains one video, one canonical caption, and a checksum receipt; none of the
private original PNGs, soundtrack or intermediate frames are committed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from src.reel_media import (
    DURATION, FRAME_COUNT, HEIGHT, SONORA_MASTER_SHA256, WIDTH, ReelBlocked,
    ffmpeg_command, make_flare_overlay, read_frame, read_reel_archive,
    verify_mp4, verify_reel_caption, verified_sonora_master,
)
from src.threads_media import SHA_RE, validate_episode

STAGE_SCHEMA = "ai-geopolitic.publisher.video-stage.v1"
PUBLIC_VIDEO_NAME = "reel.mp4"
PUBLIC_CAPTION_NAME = "caption.txt"
# GitHub refuses blobs over 100 MiB; Meta's eligible video formats are smaller.
MAX_PUBLIC_MP4 = 90 * 1024 * 1024


def output_folder(episode: str, day_text: str) -> Path:
    validate_episode(episode, day_text)
    return Path("publisher_media") / f"video-{episode.lower()}-{day_text.replace('-', '')}"


def stage_video(plan: dict, caption: str, destination: Path) -> dict:
    """Perform archive-backed, deterministic rendering without a publication signal."""
    if destination.exists():
        raise ReelBlocked("Immutable public video stage already exists.")
    if (plan.get("approved_for_reel_publication") is not False
            or plan.get("carousel_handoff_passed") is not True
            or plan.get("frame_count") != FRAME_COUNT
            or not isinstance(plan.get("frames"), list)
            or len(plan["frames"]) != FRAME_COUNT
            or verify_reel_caption(caption) != plan.get("reel_caption_sha256")):
        raise ReelBlocked("Video stage requires complete verified production QC, not publication approval.")
    audio = verified_sonora_master()
    if (plan.get("approved_audio_sha256") != SONORA_MASTER_SHA256
            or audio["sha256"] != SONORA_MASTER_SHA256):
        raise ReelBlocked("Only Ian's locked VS001 Version B recording is allowed.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="video-stage-", dir=destination.parent) as temp_name:
        temp = Path(temp_name)
        frames = []
        for index, entry in enumerate(plan["frames"], 1):
            name = f"ReelFrame{index:02d}of06.png"
            if (not isinstance(entry, dict) or entry.get("name") != name
                    or not SHA_RE.fullmatch(str(entry.get("sha256", "")))
                    or entry.get("width") != WIDTH or entry.get("height") != HEIGHT):
                raise ReelBlocked("Accepted source frame identity or dimensions changed.")
            frame = temp / name
            frame.write_bytes(read_frame(name, plan["archive_folder_id"], entry["sha256"]))
            frames.append(frame)
        flare = make_flare_overlay(temp / "flare_overlay.png")
        audio_file = temp / "locked-vs001.mp3"
        verified_sonora_master(audio_file)
        rendered = temp / PUBLIC_VIDEO_NAME
        try:
            subprocess.run(
                ffmpeg_command(frames, audio_file, temp / flare["animation_pattern"],
                               rendered, variant="C_Stronger"),
                check=True, capture_output=True, timeout=1200,
            )
        except (OSError, subprocess.SubprocessError):
            raise ReelBlocked("Approved 12% video render failed; no publication.") from None
        video = verify_mp4(rendered)
        if not 100_000 <= video["bytes"] <= MAX_PUBLIC_MP4:
            raise ReelBlocked("Rendered MP4 exceeds public Git staging size limit.")
        # No overwrite: the public artifact is a copy of exactly the probed bytes.
        destination.mkdir(parents=True, exist_ok=False)
        try:
            shutil.copyfile(rendered, destination / PUBLIC_VIDEO_NAME)
            (destination / PUBLIC_CAPTION_NAME).write_bytes(caption.encode("utf-8"))
            receipt = {
                "schema": STAGE_SCHEMA,
                "episode": plan["episode"], "date_sast": plan["date_sast"],
                "archive_folder_id": plan["archive_folder_id"],
                "post_target": "THREE_INDEPENDENT_VIDEO_PUBLISHERS",
                "status": "STAGED_NOT_PUBLISHED", "published": False,
                "source_frames": plan["frames"], "frame_count": FRAME_COUNT,
                "caption_sha256": plan["reel_caption_sha256"],
                "video": {"name": PUBLIC_VIDEO_NAME, **video},
                "video_variant": "C_Stronger", "duration_seconds": DURATION,
                "audio_master_sha256": audio["sha256"],
                "audio_master_id": audio["master_id"],
                "ai_info_required": True,
            }
            (destination / "stage.json").write_text(
                json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        except BaseException:
            shutil.rmtree(destination)
            raise
        return receipt


def verify_reusable_stage(plan: dict, caption: str, destination: Path) -> dict:
    """Reuse an existing immutable public commit only if original QC is identical.

    The downstream release module independently checks the public bytes and
    pinned commit again, including actual FFprobe codec validation.
    """
    receipt = json.loads((destination / "stage.json").read_text(encoding="utf-8"))
    if (not isinstance(receipt, dict) or receipt.get("schema") != STAGE_SCHEMA
            or receipt.get("episode") != plan.get("episode")
            or receipt.get("date_sast") != plan.get("date_sast")
            or receipt.get("archive_folder_id") != plan.get("archive_folder_id")
            or receipt.get("source_frames") != plan.get("frames")
            or receipt.get("caption_sha256") != plan.get("reel_caption_sha256")
            or receipt.get("audio_master_sha256") != SONORA_MASTER_SHA256
            or receipt.get("video_variant") != "C_Stronger"
            or receipt.get("status") != "STAGED_NOT_PUBLISHED"
            or receipt.get("published") is not False
            or (destination / PUBLIC_CAPTION_NAME).read_bytes() != caption.encode("utf-8")):
        raise ReelBlocked("Existing shared video stage differs from canonical Drive QC.")
    details = receipt.get("video")
    video_file = destination / PUBLIC_VIDEO_NAME
    if not isinstance(details, dict) or details.get("name") != PUBLIC_VIDEO_NAME:
        raise ReelBlocked("Shared video stage has no recorded selected MP4.")
    verified = verify_mp4(video_file)
    if any(details.get(key) != value for key, value in verified.items()):
        raise ReelBlocked("Shared staged MP4 checksum, codec or duration differs from QC.")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "stage", "verify"))
    parser.add_argument("--episode", required=True)
    parser.add_argument("--date-sast", required=True)
    args = parser.parse_args(argv)
    try:
        plan, caption = read_reel_archive(args.episode, args.date_sast)
        if args.mode == "plan":
            result = {"status": "VERIFIED_REEL_SOURCE_NO_PUBLICATION",
                      "episode": plan["episode"], "date_sast": plan["date_sast"],
                      "frames": FRAME_COUNT, "audio_master_sha256": SONORA_MASTER_SHA256,
                      "caption_sha256": hashlib.sha256(caption.encode()).hexdigest()}
        elif args.mode == "stage":
            receipt = stage_video(plan, caption, output_folder(args.episode, args.date_sast))
            result = {"status": receipt["status"], "episode": receipt["episode"],
                      "video": receipt["video"]}
        else:
            receipt = verify_reusable_stage(
                plan, caption, output_folder(args.episode, args.date_sast))
            result = {"status": "EXISTING_IMMUTABLE_VIDEO_QC_REVERIFIED",
                      "episode": receipt["episode"], "video": receipt["video"]}
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ReelBlocked, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "VIDEO_BLOCKED_NO_PUBLICATION", "reason": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
