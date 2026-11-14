"""Drive-verified 10-slide Threads delivery, independent of Instagram publishing.

Only read-only rclone operations are permitted. An episode is selected by its
exact ID and SAST archive date, never by the most recently modified folder.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import io
import json
import os
import re
import subprocess
from datetime import date
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

ARCHIVE_PARENT_ID = "1QcCh-qMHOH97ZWdTLULwNygibJcZRb4q"
EXPECTED_HANDOFF_SCHEMA = "ai-geopolitic.publisher.production-handoff.v1"
HANDOFF_COMPONENTS = {
    "rnd", "slide_design", "carousel_10", "carousel_caption",
    "reel_frames_6", "reel_caption", "archive_drive_readback",
}
MAX_PNG = 40 * 1024 * 1024
MAX_JPEG = 8 * 1024 * 1024
NAME_RE = re.compile(r"Ep[1-9][0-9]{0,5}\Z")
DRIVE_ID_RE = re.compile(r"[a-zA-Z0-9_-]{10,100}\Z")
SHA_RE = re.compile(r"[a-f0-9]{64}\Z")
PAPER = (247, 244, 235)


class ThreadsBlocked(ValueError):
    """Fail closed. Never silently choose another episode, file, or account."""


def validate_episode(episode: str, day_text: str) -> tuple[str, date, str]:
    if not NAME_RE.fullmatch(episode):
        raise ThreadsBlocked("Invalid explicit episode ID.")
    if not isinstance(day_text, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day_text):
        raise ThreadsBlocked("SAST production date must be exactly YYYY-MM-DD.")
    try:
        day = date.fromisoformat(day_text)
    except (ValueError, TypeError):
        raise ThreadsBlocked("SAST production date must be YYYY-MM-DD.") from None
    folder_name = f"{episode}-{day.day}{calendar.month_name[day.month]}{day.year}"
    return episode, day, folder_name


def verify_caption(caption: str) -> str:
    """Use the canonical caption, unmodified. Conservative UTF-8 byte bound."""
    if (
        not isinstance(caption, str)
        or not 30 <= len(caption.encode("utf-8")) <= 500
        or not caption.rstrip().endswith(
            "The event is factual. The interpretation ideological."
        )
        or "#AIGeopolitic" not in caption
        or caption.startswith("TEST ONLY")
    ):
        raise ThreadsBlocked("Canonical Threads caption is missing, invalid or exceeds 500 bytes.")
    return hashlib.sha256(caption.encode("utf-8")).hexdigest()


def verify_handoff(handoff: dict, episode: str, day: date, folder_id: str) -> None:
    """Production PASS proves QC completion, never social-platform consent."""
    if (
        not isinstance(handoff, dict)
        or handoff.get("schema") != EXPECTED_HANDOFF_SCHEMA
        or handoff.get("episode_id") != episode
        or handoff.get("production_date_sast") != day.isoformat()
        or handoff.get("archive_folder_id") != folder_id
        or handoff.get("status") != "PRODUCTION PASSED"
        or handoff.get("author") != "Sisyphus"
        or handoff.get("carousel_items") != 10
        or handoff.get("unresolved_blockers") != []
        or not isinstance(handoff.get("component_results"), dict)
        or set(handoff["component_results"]) != HANDOFF_COMPONENTS
        or any(value != "PASS" for value in handoff["component_results"].values())
    ):
        raise ThreadsBlocked("Independent production handoff is not a complete Sisyphus PASS.")
    # Existing handoffs can name an older Instagram TEST target. They are NOT
    # treated as social publishing consent: platform releases require either
    # an explicit manual signal or the separate standing-authority controller,
    # which constructs episode-scoped confirmations only after this PASS gate.


def safe_rclone(command: str, remote_path: str, folder_id: str, *, limit: int) -> bytes:
    if command not in ("lsjson", "cat") or not DRIVE_ID_RE.fullmatch(folder_id):
        raise ThreadsBlocked("Drive operation or folder ID is not permitted.")
    remote = os.environ.get("AI_GEO_RCLONE_REMOTE", "ai_geopolitic_drive")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", remote):
        raise ThreadsBlocked("Invalid configured Drive remote.")
    if remote_path != f"{remote}:" and not remote_path.startswith(f"{remote}:Ep"):
        raise ThreadsBlocked("Unexpected Drive source path.")
    args = ["rclone", command, remote_path, "--drive-root-folder-id", folder_id]
    args.extend(["--dirs-only" if folder_id == ARCHIVE_PARENT_ID else "--files-only",
                 "--no-modtime"] if command == "lsjson" else ["--count", str(limit + 1)])
    try:
        result = subprocess.run(args, check=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=120)
    except (OSError, subprocess.SubprocessError):
        # stderr may contain credentials. Never echo it.
        raise ThreadsBlocked("Authenticated read-only Google Drive access failed.") from None
    if not result.stdout or len(result.stdout) > limit:
        raise ThreadsBlocked("Drive response missing or beyond safe size limit.")
    return result.stdout


def _entries(folder_id: str) -> list[dict]:
    try:
        result = json.loads(safe_rclone(
            "lsjson", f"{os.environ.get('AI_GEO_RCLONE_REMOTE', 'ai_geopolitic_drive')}:",
            folder_id, limit=1024 * 1024
        ).decode("utf-8-sig"))
    except (UnicodeError, ValueError):
        raise ThreadsBlocked("Drive folder listing is malformed.") from None
    if not isinstance(result, list) or len(result) > 1000:
        raise ThreadsBlocked("Drive folder listing is ambiguous.")
    ids = [x.get("ID") for x in result if isinstance(x, dict)]
    names = [x.get("Name") for x in result if isinstance(x, dict)]
    if len(ids) != len(result) or len(set(ids)) != len(ids) or len(set(names)) != len(names):
        raise ThreadsBlocked("Drive folder has duplicate or invalid entries.")
    return result


def _read_json(name: str, folder_id: str, limit: int) -> dict:
    raw = safe_rclone(
        "cat", f"{os.environ.get('AI_GEO_RCLONE_REMOTE', 'ai_geopolitic_drive')}:{name}",
        folder_id, limit=limit
    )
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, ValueError):
        raise ThreadsBlocked("Archived QC or handoff JSON is malformed.") from None
    if not isinstance(data, dict):
        raise ThreadsBlocked("Archived QC or handoff must be an object.")
    return data


def verified_qc_records(qc: dict, episode: str, day: date, folder_id: str) -> dict:
    """Normalize two real QC ledgers without relaxing any readback evidence.

    Ep145 uses ``image_counts`` / ``delivered``; Ep146 uses ``counts`` /
    ``images`` / ``captions`` / ``deliverables``. Both must independently
    identify the exact source Drive IDs and original SHA-256 digests. The
    actual bytes are verified again during the staged download.
    """
    if (
        not isinstance(qc, dict)
        or qc.get("episode") != episode
        or qc.get("production_date_sast") != day.isoformat()
        or qc.get("archive_folder_id") != folder_id
        or not isinstance(qc.get("status"), str)
        or not qc["status"].startswith("PRODUCTION COMPLETE")
        or qc.get("unresolved_defects") != []
    ):
        raise ThreadsBlocked("Archive QC is not an exact defect-free completed episode.")

    # The older, already deployed Ep145 evidence contract remains unchanged.
    if "delivered" in qc:
        if (not isinstance(qc.get("image_counts"), dict)
                or qc["image_counts"].get("carousel") != 10
                or not isinstance(qc["delivered"], dict)):
            raise ThreadsBlocked("Legacy QC readback evidence is incomplete.")
        return qc["delivered"]

    counts, images, captions, deliverables = (
        qc.get("counts"), qc.get("images"), qc.get("captions"), qc.get("deliverables")
    )
    if (not isinstance(counts, dict) or counts.get("carousel") != 10
            or counts.get("reel") != 6
            or not isinstance(images, list) or len(images) != 16
            or not isinstance(captions, dict)
            or not isinstance(deliverables, list)):
        raise ThreadsBlocked("Production QC v2 counts or records are incomplete.")
    index: dict[str, dict] = {}
    for item in deliverables:
        if (not isinstance(item, dict) or not isinstance(item.get("name"), str)
                or item["name"] in index
                or not DRIVE_ID_RE.fullmatch(str(item.get("id", "")))
                or not isinstance(item.get("mime_type"), str)):
            raise ThreadsBlocked("Production QC has duplicate or invalid deliverable IDs.")
        index[item["name"]] = item

    evidence: dict[str, dict] = {}
    for item in images:
        if not isinstance(item, dict):
            raise ThreadsBlocked("Production QC image evidence is malformed.")
        archive, visual = item.get("archive"), item.get("visual_qc")
        if not isinstance(archive, dict) or not isinstance(visual, dict):
            raise ThreadsBlocked("Production QC image readback or visual check missing.")
        name, source, readback = (
            archive.get("filename"), archive.get("local_sha256"),
            archive.get("readback_sha256")
        )
        if (not isinstance(name, str) or name in evidence
                or not SHA_RE.fullmatch(str(source or "")) or source != readback
                or archive.get("bytes_identical") is not True
                or archive.get("format") != "PNG"
                or not isinstance(archive.get("byte_count"), int)
                or archive["byte_count"] <= 0
                or visual.get("item") != name
                or visual.get("status") != "RENDER_QC_PASS"
                or visual.get("actual_export_inspected") is not True
                or visual.get("sha256") != source
                or visual.get("dimensions") != archive.get("dimensions")
                or index.get(name, {}).get("id") != archive.get("drive_id")
                or index[name].get("mime_type") != "image/png"):
            raise ThreadsBlocked("Production QC image has unverified source identity.")
        evidence[name] = {
            "drive_id": archive["drive_id"], "source_sha256": source,
            "readback_sha256": readback, "readback_verified": True,
            "dimensions": archive["dimensions"],
        }

    expected_images = {
        *(f"{episode}_Slide{i:02d}of10.png" for i in range(1, 11)),
        *(f"ReelFrame{i:02d}of06.png" for i in range(1, 7)),
    }
    if set(evidence) != expected_images:
        raise ThreadsBlocked("Production QC image inventory is not exact.")
    cap_name = f"{episode}_CarouselCaption.txt"
    cap = captions.get("Carousel")
    if not isinstance(cap, dict) or not isinstance(cap.get("archive"), dict):
        raise ThreadsBlocked("Canonical carousel caption QC is missing.")
    cap_archive = cap["archive"]
    source, readback = cap_archive.get("local_sha256"), cap_archive.get("readback_sha256")
    if (cap_archive.get("filename") != cap_name
            or not SHA_RE.fullmatch(str(source or "")) or source != readback
            or cap.get("sha256") != source
            or cap_archive.get("bytes_identical") is not True
            or cap_archive.get("exact_text_bytes_including_linebreaks") is not True
            or index.get(cap_name, {}).get("id") != cap_archive.get("drive_id")
            or index[cap_name].get("mime_type") != "text/plain"
            or not isinstance(cap.get("text"), str)
            or hashlib.sha256(cap["text"].encode("utf-8")).hexdigest() != source
            or cap_archive.get("byte_count") != len(cap["text"].encode("utf-8"))):
        raise ThreadsBlocked("Canonical caption lacks exact Drive readback evidence.")
    evidence[cap_name] = {
        "drive_id": cap_archive["drive_id"], "sha256": source,
        "readback_verified": True, "canonical_text": cap["text"],
    }
    return evidence


def read_approved_archive(episode: str, day_text: str) -> tuple[dict, str, list[dict]]:
    """Verify a real archive inventory, QC bytes, approved source IDs, and PASS."""
    episode, day, expected_folder = validate_episode(episode, day_text)
    folders = _entries(ARCHIVE_PARENT_ID)
    matches = [x for x in folders if x.get("Name") == expected_folder
               and x.get("IsDir") is True and DRIVE_ID_RE.fullmatch(x.get("ID", ""))]
    if len(matches) != 1:
        raise ThreadsBlocked("Expected one exact SAST archive folder; no fallback.")
    folder_id = matches[0]["ID"]
    files = _entries(folder_id)
    found = {x["Name"]: x for x in files}
    qc_name, handoff_name, cap_name = (
        f"{episode}_QC_Completion.json",
        f"{episode}_PUBLISH_HANDOFF.json",
        f"{episode}_CarouselCaption.txt",
    )
    required = [qc_name, handoff_name, cap_name] + [
        f"{episode}_Slide{i:02d}of10.png" for i in range(1, 11)
    ]
    if any(name not in found or found[name].get("IsDir") is not False for name in required):
        raise ThreadsBlocked("Archive is missing the exact 10 slides, caption, QC or handoff.")
    qc = _read_json(qc_name, folder_id, 2_000_000)
    handoff = _read_json(handoff_name, folder_id, 100_000)
    verify_handoff(handoff, episode, day, folder_id)
    delivered = verified_qc_records(qc, episode, day, folder_id)
    cap_raw = safe_rclone(
        "cat", f"{os.environ.get('AI_GEO_RCLONE_REMOTE', 'ai_geopolitic_drive')}:{cap_name}",
        folder_id, limit=16_000
    )
    try:
        caption = cap_raw.decode("utf-8-sig")
    except UnicodeError:
        raise ThreadsBlocked("Archived caption is not valid UTF-8.") from None
    cap_sha = verify_caption(caption)
    cap_rec = delivered.get(cap_name, {})
    if (cap_rec.get("drive_id") != found[cap_name].get("ID")
            or cap_rec.get("sha256") != cap_sha
            or cap_rec.get("readback_verified") is not True
            or ("canonical_text" in cap_rec and cap_rec["canonical_text"] != caption)):
        raise ThreadsBlocked("Archived caption does not match QC ID and SHA-256.")
    slides: list[dict] = []
    for i in range(1, 11):
        name = f"{episode}_Slide{i:02d}of10.png"
        meta, record = found[name], delivered.get(name, {})
        if (
            meta.get("MimeType") != "image/png"
            or meta.get("ID") != record.get("drive_id")
            or not DRIVE_ID_RE.fullmatch(meta.get("ID", ""))
            or not SHA_RE.fullmatch(record.get("source_sha256", ""))
            or record.get("source_sha256") != record.get("readback_sha256")
            or record.get("readback_verified") is not True
            or record.get("dimensions") not in ([1080, 1350], [1080, 1440])
        ):
            raise ThreadsBlocked(f"Slide {i:02d} does not have verified source identity.")
        slides.append({"name": name, "id": meta["ID"],
                       "sha256": record["source_sha256"],
                       "dimensions": record["dimensions"]})
    plan = {
        "schema": "ai-geopolitic.threads.archive-plan.v1",
        "episode": episode, "date_sast": day.isoformat(),
        "archive_folder_id": folder_id,
        "caption_sha256": cap_sha, "caption_utf8_bytes": len(cap_raw),
        "slides": slides, "carousel_items": 10,
        "production_passed": True, "approved_for_threads_publishing": False,
    }
    return plan, caption, files


def _jpeg_from_png(raw: bytes, digest: str, dimensions: list[int]) -> bytes:
    if not raw or len(raw) > MAX_PNG or hashlib.sha256(raw).hexdigest() != digest:
        raise ThreadsBlocked("Original PNG source checksum or size is invalid.")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format != "PNG" or list(image.size) != dimensions:
                raise ThreadsBlocked("Image pixels differ from source QC dimensions.")
            if "A" in image.getbands() or "transparency" in image.info:
                flattened = Image.new("RGBA", image.size, PAPER + (255,))
                flattened.alpha_composite(image.convert("RGBA"))
                image_rgb = flattened.convert("RGB")
            else:
                image_rgb = image.convert("RGB")
            size = (1080, 1350)
            if image_rgb.size != size:
                fitted = ImageOps.contain(image_rgb, size, Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", size, PAPER)
                canvas.paste(fitted, ((size[0] - fitted.width)//2, (size[1] - fitted.height)//2))
                image_rgb = canvas
            stream = io.BytesIO()
            image_rgb.save(stream, "JPEG", quality=94, subsampling=0,
                           optimize=True, progressive=True)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ThreadsBlocked("Archived PNG cannot be converted safely.") from None
    encoded = stream.getvalue()
    if len(encoded) > MAX_JPEG:
        raise ThreadsBlocked("Staged JPEG is larger than the platform limit.")
    return encoded


def stage_archive(plan: dict, caption: str, files: list[dict], out_dir: Path) -> dict:
    """Verify and convert all ten before writing any staged media."""
    if out_dir.exists():
        raise ThreadsBlocked("An existing stage cannot be silently overwritten.")
    inventory = {x["Name"]: x for x in files}
    staged = []
    seen = set()
    for i, item in enumerate(plan["slides"], 1):
        current = inventory.get(item["name"], {})
        if current.get("ID") != item["id"]:
            raise ThreadsBlocked("Archived image ID changed after planning.")
        raw = safe_rclone(
            "cat", f"{os.environ.get('AI_GEO_RCLONE_REMOTE', 'ai_geopolitic_drive')}:{item['name']}",
            plan["archive_folder_id"], limit=MAX_PNG
        )
        jpg = _jpeg_from_png(raw, item["sha256"], item["dimensions"])
        digest = hashlib.sha256(jpg).hexdigest()
        if digest in seen:
            raise ThreadsBlocked("Two slides produce identical delivery images.")
        seen.add(digest)
        staged.append((f"Slide{i:02d}of10.jpg", jpg, digest))
    if verify_caption(caption) != plan["caption_sha256"]:
        raise ThreadsBlocked("Caption changed between planning and staging.")
    out_dir.mkdir(parents=True)
    media = []
    for name, data, digest in staged:
        (out_dir/name).write_bytes(data)
        media.append({"name": name, "sha256": digest, "bytes": len(data),
                      "width": 1080, "height": 1350})
    (out_dir/"caption.txt").write_bytes(caption.encode("utf-8"))
    receipt = {
        "schema": "ai-geopolitic.threads.stage-receipt.v1",
        "episode": plan["episode"], "date_sast": plan["date_sast"],
        "archive_folder_id": plan["archive_folder_id"],
        "caption_sha256": plan["caption_sha256"],
        "media": media, "slide_count": 10,
        "post_target": "THREADS_CAROUSEL_ONLY",
        "published": False,
    }
    (out_dir/"stage.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
    return receipt


def output_folder(episode: str, day_text: str) -> Path:
    validate_episode(episode, day_text)
    return Path("publisher_media") / f"threads-{episode.lower()}-{day_text.replace('-', '')}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "stage"))
    parser.add_argument("--episode", required=True)
    parser.add_argument("--date-sast", required=True)
    args = parser.parse_args(argv)
    try:
        plan, caption, files = read_approved_archive(args.episode, args.date_sast)
        if args.mode == "plan":
            result = {"status": "PREFLIGHT_PASSED_NO_PUBLICATION", "episode": args.episode,
                      "slides": 10, "caption_utf8_bytes": plan["caption_utf8_bytes"],
                      "production_passed": True}
        else:
            folder = output_folder(args.episode, args.date_sast)
            stage_archive(plan, caption, files, folder)
            result = {"status": "STAGED_NOT_PUBLISHED", "episode": args.episode,
                      "slides": 10, "folder": str(folder)}
        print(json.dumps(result))
        return 0
    except (ThreadsBlocked, OSError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc), "published": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
