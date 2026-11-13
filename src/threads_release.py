"""One-time, human-authorized Threads CAROUSEL publisher.

The action runs only on main after a staged SHA-pinned public media commit.
Claim a durable main-branch receipt BEFORE the first Meta write. A claimed but
unconfirmed delivery requires manual reconciliation, never an automatic rerun.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from src.threads_media import ThreadsBlocked, output_folder, validate_episode, verify_caption

API_ROOT = "https://graph.threads.net/v1.0"
GITHUB_RAW = "https://raw.githubusercontent.com/venipublishing-main/ai-geopolitic-automation"
COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")
EXPECTED_USERNAME = "ai_geopolitic"
LOCKED_HASHTAGS = (
    "#AIGeopolitic", "#SouthAfrica", "#Geopolitics",
    "#PoliticalAnalysis", "#NewsBriefing",
)
MAX_RESPONSE = 256 * 1024
STAGE_SCHEMA = "ai-geopolitic.threads.stage-receipt.v1"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def caption_match(canonical: str, published: str) -> str | None:
    """Allow only the single hashtag marker Meta removed in the Ep145 release.

    Threads can convert one approved hashtag to its native topic representation.
    No other character, punctuation, case or hashtag alteration is permitted.
    This predicate also protects duplicate detection on subsequent releases.
    """
    if not isinstance(canonical, str) or not isinstance(published, str):
        return None
    source, actual = canonical.strip(), published.strip()
    if source == actual:
        return "EXACT"
    for hashtag in LOCKED_HASHTAGS:
        if hashtag in source and source.replace(hashtag, hashtag[1:], 1) == actual:
            return "META_ONE_TOPIC_HASH_REMOVED"
    return None


def verify_published_post(media_id: str, caption: str, post: dict) -> dict | None:
    """Verify the actual account, ten image children and canonical-equivalent text."""
    if not isinstance(post, dict) or str(post.get("id")) != media_id:
        return None
    if str(post.get("username", "")).lower().lstrip("@") != EXPECTED_USERNAME:
        return None
    if post.get("media_type") != "CAROUSEL_ALBUM":
        return None
    match_mode = caption_match(caption, post.get("text"))
    if match_mode is None:
        return None
    children = post.get("children")
    if isinstance(children, dict):
        children = children.get("data")
    if not isinstance(children, list) or len(children) != 10:
        return None
    ids = [str(child.get("id", "")) if isinstance(child, dict) else "" for child in children]
    if any(not x.isdigit() for x in ids) or len(set(ids)) != 10:
        return None
    permalink = str(post.get("permalink", ""))
    parsed = urllib.parse.urlparse(permalink)
    if (parsed.scheme != "https"
            or parsed.hostname not in ("threads.com", "www.threads.com", "threads.net", "www.threads.net")
            or not parsed.path.startswith(f"/@{EXPECTED_USERNAME}/post/")):
        return None
    return {"threads_media_id": media_id, "threads_permalink": permalink,
            "caption_verification": match_mode, "carousel_items_verified": len(ids)}


def check_stage(episode: str, day: str, commit: str, root: Path = Path(".")) -> tuple[dict, str, list[str]]:
    validate_episode(episode, day)
    if not COMMIT_RE.fullmatch(commit):
        raise ThreadsBlocked("Staging commit must be an immutable Git commit SHA.")
    folder = root / output_folder(episode, day)
    receipt = json.loads((folder / "stage.json").read_text(encoding="utf-8"))
    if (receipt.get("schema") != STAGE_SCHEMA or receipt.get("episode") != episode
            or receipt.get("date_sast") != day or receipt.get("slide_count") != 10
            or receipt.get("post_target") != "THREADS_CAROUSEL_ONLY"
            or receipt.get("published") is not False):
        raise ThreadsBlocked("Invalid or previously published staging receipt.")
    text = (folder / "caption.txt").read_text(encoding="utf-8")
    if verify_caption(text) != receipt.get("caption_sha256"):
        raise ThreadsBlocked("Staged caption differs from canonical SHA-256.")
    media = receipt.get("media")
    if not isinstance(media, list) or len(media) != 10:
        raise ThreadsBlocked("Only ten ordered carousel images are permitted.")
    images: list[str] = []
    unique = set()
    for i, entry in enumerate(media, 1):
        name = f"Slide{i:02d}of10.jpg"
        if (not isinstance(entry, dict) or entry.get("name") != name
                or entry.get("width") != 1080 or entry.get("height") != 1350
                or not isinstance(entry.get("bytes"), int)):
            raise ThreadsBlocked("Staged carousel filename, sequence or dimensions incorrect.")
        img = (folder / name).read_bytes()
        if (not 0 < len(img) < 8 * 1024 * 1024
                or len(img) != entry["bytes"] or sha(img) != entry.get("sha256")
                or entry["sha256"] in unique):
            raise ThreadsBlocked("Staged JPEG checksum or uniqueness check failed.")
        unique.add(entry["sha256"])
        with Image.open(folder / name) as opened:
            if opened.format != "JPEG" or opened.size != (1080, 1350):
                raise ThreadsBlocked("Staged JPEG format or dimensions incorrect.")
        images.append(f"{GITHUB_RAW}/{commit}/{output_folder(episode, day).as_posix()}/{name}")
    return receipt, text, images


def verify_public_images(urls: list[str]) -> None:
    if len(urls) != 10 or len(set(urls)) != 10:
        raise ThreadsBlocked("Public media URLs must contain exactly ten unique images.")
    for index, url in enumerate(urls, 1):
        try:
            req = urllib.request.Request(url, method="HEAD",
                                         headers={"User-Agent": "ai-geopolitic-threads-release/1.0"})
            with urllib.request.urlopen(req, timeout=20) as result:
                if result.status != 200 or "image/jpeg" not in result.headers.get("Content-Type", ""):
                    raise ThreadsBlocked(f"Public slide {index:02d} is not a JPEG response.")
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ThreadsBlocked(f"Public slide {index:02d} is not yet accessible; no Threads POST.") from None


class ThreadsGraph:
    def __init__(self, token: str):
        if not isinstance(token, str) or len(token) < 16 or "\n" in token:
            raise ThreadsBlocked("Threads User Access Token missing or invalid.")
        self.token = token

    def request(self, method: str, path: str, params: dict | None = None) -> dict:
        if method not in ("GET", "POST") or not re.fullmatch(r"/[A-Za-z0-9_/,]+", path):
            raise ThreadsBlocked("Disallowed Threads Graph request.")
        params = params or {}
        encoded = urllib.parse.urlencode(params).encode("utf-8")
        url = API_ROOT + path + ("?" + encoded.decode() if method == "GET" and params else "")
        request = urllib.request.Request(url, method=method, data=encoded if method == "POST" else None,
                                         headers={"Authorization": f"Bearer {self.token}",
                                                  "User-Agent": "ai-geopolitic-threads-release/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                raw = response.read(MAX_RESPONSE + 1)
                if len(raw) > MAX_RESPONSE:
                    raise ThreadsBlocked("Threads response exceeds safe size.")
                result = json.loads(raw)
        except urllib.error.HTTPError as exc:
            raise ThreadsBlocked(f"Threads API HTTP {exc.code}; reconcile manually if claim exists.") from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise ThreadsBlocked("Threads API connection or response failed; reconcile if claimed.") from None
        if not isinstance(result, dict) or "error" in result:
            raise ThreadsBlocked("Threads API rejected the operation; reconcile if claimed.")
        return result

    def check_identity_and_duplicate(self, caption: str) -> tuple[str, str]:
        me = self.request("GET", "/me", {"fields": "id,username"})
        if str(me.get("username", "")).lower().lstrip("@") != EXPECTED_USERNAME or not str(me.get("id", "")).isdigit():
            raise ThreadsBlocked("Access token is not for @ai_geopolitic Threads.")
        # This is a second line of protection; the durable GitHub claim is the
        # source of truth. Pagination is not an excuse to retry a claimed post.
        recent = self.request("GET", "/me/threads", {"fields": "id,text,permalink", "limit": "50"})
        posts = recent.get("data", [])
        if not isinstance(posts, list):
            raise ThreadsBlocked("Cannot verify recent Threads posts.")
        if any(isinstance(x, dict) and caption_match(caption, x.get("text")) is not None for x in posts):
            raise ThreadsBlocked("Identical carousel caption is already published on Threads.")
        return str(me["id"]), EXPECTED_USERNAME

    def wait_ready(self, container_id: str) -> None:
        if not str(container_id).isdigit():
            raise ThreadsBlocked("Threads returned an invalid container ID.")
        for attempt in range(16):
            response = self.request("GET", f"/{container_id}", {"fields": "id,status,error_message"})
            if response.get("status") == "FINISHED":
                return
            if response.get("status") in ("ERROR", "EXPIRED", "PUBLISHED"):
                raise ThreadsBlocked("Threads media container is not publishable.")
            if attempt < 15:
                time.sleep(3)
        raise ThreadsBlocked("Threads processing exceeded wait window; reconcile if claimed.")

    def publish_carousel(self, caption: str, image_urls: list[str]) -> dict:
        children = []
        for i, url in enumerate(image_urls, 1):
            result = self.request("POST", "/me/threads", {
                "media_type": "IMAGE", "image_url": url, "is_carousel_item": "true",
                "alt_text": f"AI Geopolitic editorial carousel, slide {i} of 10",
            })
            child = str(result.get("id", ""))
            self.wait_ready(child)
            children.append(child)
        parent = self.request("POST", "/me/threads", {
            "media_type": "CAROUSEL", "children": ",".join(children), "text": caption,
        })
        container = str(parent.get("id", ""))
        self.wait_ready(container)
        published = self.request("POST", "/me/threads_publish", {"creation_id": container})
        media_id = str(published.get("id", ""))
        if not media_id.isdigit():
            raise ThreadsBlocked("Threads publish returned no valid media ID; manual reconciliation.")
        for attempt in range(8):
            post = self.request("GET", f"/{media_id}", {
                "fields": "id,username,text,permalink,media_type,children"})
            verified = verify_published_post(media_id, caption, post)
            if verified is not None:
                return verified
            if attempt < 7:
                time.sleep(4)
        raise ThreadsBlocked("Threads publish response received, but post verification failed; manual reconciliation.")


def _git(*args: str) -> str:
    try:
        result = subprocess.run(["git", *args], check=True, capture_output=True, text=True,
                                timeout=90)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise ThreadsBlocked("Cannot durably update GitHub state; manual reconciliation may be required.") from None


def state_path(episode: str, day: str) -> Path:
    return Path("publisher_state") / f"threads-{episode.lower()}-{day.replace('-', '')}.json"


def save_state(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _git("add", "--", str(path))
    _git("commit", "-m", f"Threads {record['episode']}: {record['status']}")
    _git("push", "origin", "HEAD:refs/heads/main")


def release(episode: str, day: str, commit: str, approval: str,
            *, token: str, run_id: str) -> dict:
    if approval != f"PUBLISH_THREADS_{episode.upper()}_{day.replace('-', '')}":
        raise ThreadsBlocked("Explicit per-episode Threads authorization was not provided.")
    if not run_id.isdigit() or not os.environ.get("GITHUB_ACTIONS") == "true":
        raise ThreadsBlocked("Live release is only allowed in GitHub Actions.")
    if _git("branch", "--show-current") != "main":
        raise ThreadsBlocked("Release must run from the main branch.")
    receipt, caption, image_urls = check_stage(episode, day, commit)
    verify_public_images(image_urls)
    graph = ThreadsGraph(token)
    user_id, username = graph.check_identity_and_duplicate(caption)
    _git("pull", "--ff-only", "origin", "main")
    state = state_path(episode, day)
    if state.exists() or _git("ls-files", "--", str(state)):
        raise ThreadsBlocked("Existing Threads claim/receipt forbids automatic repeat publication.")
    claim = {
        "schema": "ai-geopolitic.threads.publication-receipt.v1",
        "episode": episode, "date_sast": day,
        "threads_account": username, "threads_user_id": user_id,
        "caption_sha256": receipt["caption_sha256"], "carousel_items": 10,
        "public_media_commit": commit, "github_run_id": run_id,
        "claimed_utc": datetime.now(timezone.utc).isoformat(),
        "status": "CLAIMED_NO_AUTOMATIC_RETRY",
    }
    save_state(state, claim)  # Durable claim BEFORE any Meta write.
    try:
        outcome = graph.publish_carousel(caption, image_urls)
    except ThreadsBlocked:
        # Deliberately leave the claim; an ambiguous Meta write must never retry.
        raise
    claim.update(outcome)
    claim["status"] = "PUBLISHED_VERIFIED"
    claim["published_utc"] = datetime.now(timezone.utc).isoformat()
    save_state(state, claim)
    return {"status": claim["status"], "episode": episode,
            "permalink": claim["threads_permalink"], "carousel_items": 10}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode", required=True)
    parser.add_argument("--date-sast", required=True)
    parser.add_argument("--media-commit", required=True)
    parser.add_argument("--approval", required=True)
    args = parser.parse_args(argv)
    try:
        result = release(args.episode, args.date_sast, args.media_commit, args.approval,
                         token=os.environ.get("AI_GEO_THREADS_ACCESS_TOKEN", ""),
                         run_id=os.environ.get("GITHUB_RUN_ID", ""))
        print(json.dumps(result))
        return 0
    except (ThreadsBlocked, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED_OR_RECONCILE", "reason": str(exc),
                          "automatic_retry_allowed": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
