"""Publish exactly one real Ep145 10-image carousel from approved archived PNGs.

No Reel, video, music, audio, future episode fallback or automatic Meta retry.
Every external media link is pinned to a staged Git commit and digest.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import time
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image, UnidentifiedImageError

from .publisher_archive import PublisherBlocked, sast_today
from .publisher_ep145_stage import load_plan
from .publisher_instagram import InstagramCarouselPublisher, UrlLibGraphTransport, validate_public_urls
from .publisher_test_release import verified_ig_id, verify_published_media


class RealReleaseBlocked(PublisherBlocked):
    pass


DAY = date(2026, 11, 13)
SIGNAL_PATH = Path("publisher_signals/ep145-real-carousel-20261113.json")
STATE_PATH = Path("publisher_state/ep145-real-carousel.json")
STAGE_RECEIPT = Path("publisher_media/ep145-real-20261113/receipt.json")
PREFIX = "https://raw.githubusercontent.com/venipublishing-main/ai-geopolitic-automation"
MAX_MEDIA_BYTES = 8 * 1024 * 1024


def verify_release_signal(signal: dict, plan: dict) -> str:
    if not isinstance(signal, dict):
        raise RealReleaseBlocked("Explicit real Ep145 approval signal was not found.")
    expected = {
        "schema": "ai-geopolitic.publisher.ep145-real-approval.v1",
        "episode": "Ep145",
        "date_sast": "2026-11-13",
        "archive_folder_id": "1mvKV0f6LFwv8sln8Ps0YD9Ql5f9lLP9H",
        "approved_account": "ai_geopolitic",
        "post_targets": ["CAROUSEL"],
        "no_reel": True,
        "no_music": True,
        "test_only": False,
        "previously_published": False,
        "direct_user_approval": "IAN_APPROVED_EP145_CAROUSEL_ONLY_20261113",
    }
    if any(signal.get(k) != v for k, v in expected.items()):
        raise RealReleaseBlocked("Real carousel approval signal is missing or inconsistent.")
    if plan.get("post_targets") != ["CAROUSEL"]:
        raise RealReleaseBlocked("Release plan includes something other than one carousel.")
    caption = plan.get("carousel_caption", {}).get("content", "")
    if not isinstance(caption, str) or not 40 <= len(caption) <= 2200:
        raise RealReleaseBlocked("Archived carousel caption is invalid.")
    expected_sha = plan["carousel_caption"].get("sha256")
    digest = hashlib.sha256(caption.encode("utf-8")).hexdigest()
    if digest != expected_sha or signal.get("caption_sha256") != digest:
        raise RealReleaseBlocked("Archived caption does not match the approved digest.")
    if not caption.rstrip().endswith("The event is factual. The interpretation ideological."):
        raise RealReleaseBlocked("Required canonical footer is not in the caption.")
    if caption.startswith("TEST ONLY"):
        raise RealReleaseBlocked("Refusing to post a test-caption or test-artwork as genuine.")
    return caption


def verify_stage_receipt(plan: dict, sha: str) -> tuple[list[str], list[dict]]:
    if not re.fullmatch(r"[0-9a-f]{40}", sha or ""):
        raise RealReleaseBlocked("Staging commit is not an immutable Git SHA.")
    try:
        stage = json.loads(STAGE_RECEIPT.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise RealReleaseBlocked("Public image stage receipt is missing.") from None
    if (stage.get("schema") != "ai-geopolitic.publisher.ep145-carousel-media-stage.v1"
            or stage.get("archive_folder_id") != plan.get("archive_folder_id")
            or stage.get("episode") != "Ep145" or stage.get("count") != 10
            or stage.get("source_sha256_verified") is not True
            or stage.get("no_reel") is not True or stage.get("no_audio") is not True):
        raise RealReleaseBlocked("Ten-image stage receipt failed exact scope checks.")
    media = stage.get("media")
    if not isinstance(media, list) or len(media) != 10:
        raise RealReleaseBlocked("Staged media does not contain exactly ten images.")
    urls = []
    for i, item in enumerate(media, 1):
        if (item.get("name") != f"Slide{i:02d}of10.jpg"
                or item.get("width") != 1080 or item.get("height") != 1350
                or not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", ""))):
            raise RealReleaseBlocked("Staged media manifest is malformed.")
        urls.append(f"{PREFIX}/{sha}/publisher_media/ep145-real-20261113/{item['name']}")
    validate_public_urls(urls, allowed_hostname="raw.githubusercontent.com")
    return urls, media


def verify_public_media(urls: list[str], items: list[dict]) -> None:
    """Only GET 10 pinned JPEGs before the durable claim; never retry Meta POST."""
    seen = set()
    for url, item in zip(urls, items, strict=True):
        data = None
        # GitHub immutable commit raw media can take a moment to become available.
        for attempt in range(5):
            try:
                req = Request(url, headers={"User-Agent": "AI-Geopolitic-Archive-Preflight/1"})
                with urlopen(req, timeout=25) as resp:
                    if resp.headers.get("Content-Type", "").split(";")[0].strip().lower() not in ("image/jpeg", "image/jpg"):
                        raise RealReleaseBlocked("Public staged image is not JPEG.")
                    data = resp.read(MAX_MEDIA_BYTES + 1)
                break
            except (HTTPError, URLError, TimeoutError, OSError):
                if attempt == 4:
                    raise RealReleaseBlocked("Public media not reachable; no Meta post attempted.") from None
                time.sleep(2)
        if data is None or len(data) > MAX_MEDIA_BYTES:
            raise RealReleaseBlocked("Public image is empty or oversized.")
        digest = hashlib.sha256(data).hexdigest()
        if digest != item["sha256"] or digest in seen:
            raise RealReleaseBlocked("Staged image checksum differs or images duplicate.")
        seen.add(digest)
        try:
            with Image.open(io.BytesIO(data)) as im:
                if im.format != "JPEG" or im.size != (1080, 1350):
                    raise RealReleaseBlocked("Public image dimensions are invalid.")
        except (OSError, UnidentifiedImageError, Image.DecompressionBombError):
            raise RealReleaseBlocked("Public media could not be decoded.") from None


def inspect_previous_posts(token: str, ig_id: str, caption: str) -> None:
    url = f"https://graph.facebook.com/v26.0/{ig_id}/media?fields=id,caption,permalink&limit=50"
    request = Request(url, headers={"Authorization":"Bearer "+token}, method="GET")
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read(150_000).decode("utf-8"))
    except (HTTPError, URLError, OSError, ValueError, UnicodeError):
        raise RealReleaseBlocked("Could not reconcile existing Instagram posts.") from None
    entries = result.get("data")
    if not isinstance(entries, list):
        raise RealReleaseBlocked("Instagram media history incomplete or malformed; no posting.")
    signature = caption.splitlines()[0].strip()
    for item in entries:
        old = item.get("caption") if isinstance(item, dict) else None
        if isinstance(old, str) and (
            old.strip() == caption.strip()
            or (signature and signature in old and not old.startswith("TEST ONLY"))
        ):
            raise RealReleaseBlocked("Ep145 appears to be already published; do not duplicate.")


def safe_git(*args: str) -> str:
    try:
        cp = subprocess.run(["git", *args],check=True,capture_output=True,
                            encoding="utf-8",timeout=45)
        return cp.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise RealReleaseBlocked("Cannot durably persist release receipt in GitHub.") from None


def claim_once(plan: dict, caption: str, media_sha: str) -> None:
    if STATE_PATH.exists():
        raise RealReleaseBlocked("Ep145 real carousel already claimed; never retry automatically.")
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": "ai-geopolitic.publisher.real-carousel-receipt.v1",
        "episode": "Ep145", "date_sast": DAY.isoformat(),
        "account_username": "ai_geopolitic",
        "archive_folder_id": plan["archive_folder_id"],
        "content": "CAROUSEL_ONLY", "slide_count":10,"reel":False,"music":False,
        "caption_sha256": hashlib.sha256(caption.encode("utf-8")).hexdigest(),
        "media_commit_sha":media_sha,
        "status":"CLAIMED_NO_AUTOMATIC_RETRY", "instagram_media_id":None,"permalink":None,
        "github_run_id":os.environ.get("GITHUB_RUN_ID", ""),
    }
    STATE_PATH.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    safe_git("config","user.name","github-actions[bot]")
    safe_git("config","user.email","github-actions[bot]@users.noreply.github.com")
    safe_git("add",str(STATE_PATH))
    safe_git("commit","-m","Claim one-time REAL Ep145 carousel before Meta POST")
    safe_git("push","origin","HEAD:main")


def record_result(media_id: str, status: str, permalink: str | None) -> None:
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    state.update(status=status, instagram_media_id=media_id, permalink=permalink)
    STATE_PATH.write_text(json.dumps(state,indent=2)+"\n",encoding="utf-8")
    safe_git("add",str(STATE_PATH))
    safe_git("commit","-m","Record actual Ep145 Instagram carousel publication receipt")
    safe_git("push","origin","HEAD:main")


def run() -> dict:
    if os.environ.get("AI_GEO_REAL_CAROUSEL_ENABLE") != "ONE_AUTHORIZED_EP145_REAL_IMAGE_CAROUSEL":
        raise RealReleaseBlocked("Real Ep145 carousel publishing not enabled.")
    if sast_today() != DAY:
        raise RealReleaseBlocked("Approval is restricted to Friday 13 November 2026 SAST.")
    plan = load_plan()
    try:
        signal = json.loads(SIGNAL_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise RealReleaseBlocked("Explicit release approval signal is absent.") from None
    caption = verify_release_signal(signal, plan)
    media_sha = os.environ.get("AI_GEO_EP145_MEDIA_COMMIT", "")
    urls, items = verify_stage_receipt(plan, media_sha)
    if STATE_PATH.exists():
        raise RealReleaseBlocked("Already claimed/published. No repeat permitted.")
    verify_public_media(urls, items)
    token = os.environ.get("AI_GEO_IG_ACCESS_TOKEN", "")
    if not token:
        raise RealReleaseBlocked("Instagram access token is unavailable.")
    ig_id = verified_ig_id(token)
    inspect_previous_posts(token, ig_id, caption)
    claim_once(plan, caption, media_sha)
    # A Meta POST may have succeeded even if the HTTP response is lost. Never retry.
    media_id = InstagramCarouselPublisher(ig_id, "v26.0", UrlLibGraphTransport(token)).publish(
        urls, caption, allowed_hostname="raw.githubusercontent.com",
        explicit_external_publish_permission=True,
    )
    status, permalink = verify_published_media(token, media_id)
    record_result(media_id, status, permalink)
    return {
        "status":status, "episode":"Ep145", "type":"CAROUSEL_ONLY",
        "posted":True, "reel_posted":False, "music_attached":False,
        "instagram_media_id":media_id, "permalink":permalink,
    }


def main() -> int:
    try:
        print(json.dumps(run(),indent=2))
        return 0
    except RealReleaseBlocked as exc:
        print(json.dumps({"status":"BLOCKED","reason":str(exc),
                          "posted_by_this_run":"NOT_CONFIRMED","automatic_retry":False}))
    except Exception:
        print(json.dumps({"status":"BLOCKED","reason":"UNEXPECTED_RELEASE_FAILURE",
                          "posted_by_this_run":"NOT_CONFIRMED","automatic_retry":False}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
