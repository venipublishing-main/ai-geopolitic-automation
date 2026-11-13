"""One-time Ep145 CAROUSEL-ONLY archival Drive -> GitHub media staging.

Read exact approved PNGs, verify ID and SHA, convert to Meta-ready JPEG.
No upload, deletion, Reel, audio, Meta call or automatic post in this module.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from PIL import Image, UnidentifiedImageError

from .publisher_archive import PublisherBlocked, sast_today

EPISODE = "Ep145"
DATE = date(2026, 11, 13)
PLAN_PATH = Path("publisher_code/publisher_release/ep145-real-plan.json")
OUTPUT_DIR = Path("publisher_media/ep145-real-20261113")
MAX_PNG_BYTES = 10 * 1024 * 1024


class StageBlocked(PublisherBlocked):
    pass


def load_plan(path: Path = PLAN_PATH) -> dict:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise StageBlocked("Pinned publication plan is unavailable.") from None
    if (
        plan.get("schema") != "ai-geopolitic.publisher.ep145-real-plan.v1"
        or plan.get("episode") != EPISODE
        or plan.get("date_sast") != DATE.isoformat()
        or plan.get("username") != "ai_geopolitic"
        or plan.get("post_targets") != ["CAROUSEL"]
        or plan.get("publish_scope") != "EXACTLY_ONE_REAL_EP145_IMAGE_CAROUSEL_NO_REEL_NO_MUSIC"
        or plan.get("archive_folder_id") != "1mvKV0f6LFwv8sln8Ps0YD9Ql5f9lLP9H"
        or len(plan.get("slide_items", [])) != 10
        or "reel_items" in plan or "music" in plan
    ):
        raise StageBlocked("Release plan is not the exact carousel-only Ep145 approval.")
    for i, item in enumerate(plan["slide_items"], 1):
        if (
            item.get("name") != f"Ep145_Slide{i:02d}of10.png"
            or item.get("width") != 1080
            or item.get("height") != 1350
            or len(item.get("sha256", "")) != 64
            or not isinstance(item.get("id"), str)
        ):
            raise StageBlocked("A pinned archive slide has invalid metadata.")
    return plan


def safe_rclone(*args: str, limit: int) -> bytes:
    if args[0] not in ("lsjson", "cat"):
        raise StageBlocked("Only read-only Drive operations are authorized.")
    try:
        p = subprocess.run(
            [os.environ.get("RCLONE", "rclone"), *args],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=90,
        )
    except (OSError, subprocess.SubprocessError):
        raise StageBlocked("Authenticated Drive read failed; no image was staged.") from None
    if len(p.stdout) > limit:
        raise StageBlocked("Drive response exceeded the maximum permitted size.")
    return p.stdout


def stage(plan: dict, target: Path = OUTPUT_DIR) -> dict:
    if sast_today() != DATE:
        raise StageBlocked("Ep145 production-day release window has expired.")
    remote = os.environ.get("AI_GEO_RCLONE_REMOTE", "ai_geopolitic_drive")
    if remote != "ai_geopolitic_drive":
        raise StageBlocked("Unexpected Drive remote.")
    folder = plan["archive_folder_id"]
    raw = safe_rclone("lsjson", f"{remote}:", "--drive-root-folder-id", folder,
                      "--files-only", "--no-modtime", limit=512 * 1024)
    try:
        entries = json.loads(raw.decode("utf-8"))
        if not isinstance(entries, list):
            raise ValueError
    except (ValueError, UnicodeError):
        raise StageBlocked("Malformed canonical archive listing.") from None
    # Refuse duplicate names and unexpected aliases of pinned IDs.
    if len({e.get("Name") for e in entries}) != len(entries):
        raise StageBlocked("Duplicate archive names; refuse ambiguous file selection.")
    if len({e.get("ID") for e in entries}) != len(entries):
        raise StageBlocked("Duplicate archive IDs; refuse ambiguous file selection.")
    expected = {a["name"]: a for a in plan["slide_items"]}
    found = {e.get("Name"): e for e in entries}
    for name, item in expected.items():
        metadata = found.get(name)
        if (
            not metadata or metadata.get("IsDir") is not False
            or metadata.get("ID") != item["id"]
            or metadata.get("MimeType") != "image/png"
        ):
            raise StageBlocked("Expected image ID/MIME was not found in the episode archive.")

    # Validate all accepted source PNGs before creating the first staging JPEG.
    staged = []
    for i, item in enumerate(plan["slide_items"], 1):
        name = item["name"]
        raw_png = safe_rclone("cat", f"{remote}:{name}", "--drive-root-folder-id", folder,
                              "--count", str(MAX_PNG_BYTES + 1), limit=MAX_PNG_BYTES)
        if hashlib.sha256(raw_png).hexdigest() != item["sha256"]:
            raise StageBlocked(f"Image {i} failed archived SHA-256 readback.")
        try:
            with Image.open(io.BytesIO(raw_png)) as image:
                if image.format != "PNG" or image.size != (1080, 1350):
                    raise StageBlocked("Canonical carousel image has wrong size or format.")
                jpeg = io.BytesIO()
                image.convert("RGB").save(jpeg, format="JPEG", quality=94,
                                          subsampling=0, optimize=True)
        except (OSError, UnidentifiedImageError, Image.DecompressionBombError):
            raise StageBlocked("Canonical image could not be decoded.") from None
        encoded = jpeg.getvalue()
        if len(encoded) > 8 * 1024 * 1024:
            raise StageBlocked("JPEG image exceeds Meta's allowed staging size.")
        staged.append((f"Slide{i:02d}of10.jpg", encoded))

    target.mkdir(parents=True, exist_ok=False)
    receipts = []
    for filename, data in staged:
        (target / filename).write_bytes(data)
        receipts.append({"name":filename,"sha256":hashlib.sha256(data).hexdigest(),
                         "size":len(data),"width":1080,"height":1350})
    receipt = {
        "schema":"ai-geopolitic.publisher.ep145-carousel-media-stage.v1",
        "episode":EPISODE, "date_sast":DATE.isoformat(),
        "archive_folder_id":folder,
        "source_sha256_verified":True,
        "count":10,"media":receipts,"no_reel":True,"no_audio":True,
    }
    (target / "receipt.json").write_text(json.dumps(receipt, indent=2)+"\n",
                                         encoding="utf-8")
    return receipt


def main() -> int:
    try:
        p = load_plan()
        r = stage(p)
        print(json.dumps({"stage":"PASS","episode":"Ep145","carousel":r["count"],
                          "no_reel":True,"no_audio":True}))
        return 0
    except (StageBlocked, OSError) as exc:
        print(json.dumps({"stage":"BLOCKED","reason":str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
