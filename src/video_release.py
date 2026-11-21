"""Three independently claimed, human-gated GitHub Actions video publishers.

Instagram Reel and Story use Facebook Graph; Threads video uses Threads Graph.
No Sisyphus session or Meta browser login is involved. A durable main-branch
claim MUST be pushed before the first Meta POST, and no uncertain outcome is
ever retried automatically. The Story endpoint never receives a caption.
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

from src.instagram_graph import (
    GRAPH_ROOT, ID_RE, USERNAME, InstagramPublishBlocked,
    UrlLibGraphTransport,
)
from src.reel_media import (
    DURATION, FRAME_COUNT, HEIGHT, SONORA_MASTER_SHA256, WIDTH,
    verify_mp4, verify_reel_caption,
)
from src.threads_media import SHA_RE, ThreadsBlocked, validate_episode
from src.threads_release import (
    EXPECTED_USERNAME, ThreadsGraph, caption_match,
)
from src.video_media import (
    MAX_PUBLIC_MP4, PUBLIC_CAPTION_NAME, PUBLIC_VIDEO_NAME,
    STAGE_SCHEMA, output_folder,
)

GITHUB_RAW = "https://raw.githubusercontent.com/venipublishing-main/ai-geopolitic-automation"
COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")
SURFACES = ("instagram-reel", "threads-video", "instagram-story")
SUCCESS_STATUS = {
    "instagram-reel": "PUBLISHED_AI_INFO_VERIFIED",
    "threads-video": "PUBLISHED_VERIFIED",
    "instagram-story": "PUBLISHED_STORY_AI_INFO_VERIFIED",
}
WORKFLOW_NAMES = {
    "instagram-reel": "AI Geopolitic Instagram — Reel video (human gate)",
    "threads-video": "AI Geopolitic Threads — Reel video (human gate)",
    "instagram-story": "AI Geopolitic Instagram — Story video (human gate)",
}


class VideoPublishBlocked(ThreadsBlocked):
    """Fail closed; an existing claim requires human reconciliation."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def approval_for(surface: str, episode: str, day: str) -> str:
    if surface not in SURFACES:
        raise VideoPublishBlocked("Unknown video publishing surface.")
    validate_episode(episode, day)
    return f"PUBLISH_{surface.upper().replace('-', '_')}_{episode.upper()}_{day.replace('-', '')}"


def state_path(surface: str, episode: str, day: str) -> Path:
    approval_for(surface, episode, day)
    return Path("publisher_state") / f"{surface}-{episode.lower()}-{day.replace('-', '')}.json"


def check_stage(episode: str, day: str, commit: str, root: Path = Path(".")) -> tuple[dict, str, str]:
    validate_episode(episode, day)
    if not COMMIT_RE.fullmatch(commit):
        raise VideoPublishBlocked("Public video must be pinned to an immutable Git commit.")
    folder = root / output_folder(episode, day)
    receipt = json.loads((folder / "stage.json").read_text(encoding="utf-8"))
    if (not isinstance(receipt, dict)
            or receipt.get("schema") != STAGE_SCHEMA
            or receipt.get("episode") != episode or receipt.get("date_sast") != day
            or receipt.get("post_target") != "THREE_INDEPENDENT_VIDEO_PUBLISHERS"
            or receipt.get("status") != "STAGED_NOT_PUBLISHED"
            or receipt.get("published") is not False
            or receipt.get("ai_info_required") is not True
            or receipt.get("frame_count") != FRAME_COUNT
            or receipt.get("video_variant") != "C_Stronger"
            or receipt.get("duration_seconds") != DURATION
            or receipt.get("audio_master_sha256") != SONORA_MASTER_SHA256):
        raise VideoPublishBlocked("Staging record is not the accepted, unpublished Version B Reel.")
    frames = receipt.get("source_frames")
    if (not isinstance(frames, list) or len(frames) != FRAME_COUNT
            or any(not isinstance(frame, dict)
                   or frame.get("name") != f"ReelFrame{index:02d}of06.png"
                   or not SHA_RE.fullmatch(str(frame.get("sha256", "")))
                   or frame.get("width") != WIDTH or frame.get("height") != HEIGHT
                   for index, frame in enumerate(frames, 1))):
        raise VideoPublishBlocked("Source frame provenance is missing or invalid.")
    caption = (folder / PUBLIC_CAPTION_NAME).read_text(encoding="utf-8")
    if verify_reel_caption(caption) != receipt.get("caption_sha256"):
        raise VideoPublishBlocked("Staged Reel caption is not byte-identical to archive QC.")
    info = receipt.get("video")
    if (not isinstance(info, dict) or info.get("name") != PUBLIC_VIDEO_NAME
            or not SHA_RE.fullmatch(str(info.get("sha256", "")))
            or type(info.get("bytes")) is not int
            or not 100_000 <= info["bytes"] <= MAX_PUBLIC_MP4):
        raise VideoPublishBlocked("Video checksum, identity or size is invalid.")
    mp4 = folder / PUBLIC_VIDEO_NAME
    if (mp4.stat().st_size != info["bytes"] or sha(mp4.read_bytes()) != info["sha256"]
            or verify_mp4(mp4) != {key: info[key] for key in (
                "width", "height", "fps", "duration_seconds", "video_codec",
                "audio_codec", "bytes", "sha256")}):
        raise VideoPublishBlocked("Staged video bytes, codecs or duration differ from QC.")
    url = f"{GITHUB_RAW}/{commit}/{output_folder(episode, day).as_posix()}/{PUBLIC_VIDEO_NAME}"
    return receipt, caption, url


def verify_public_video(receipt: dict, url: str) -> None:
    """Read the actual public video bytes before any Meta write, not merely HEAD."""
    parsed = urllib.parse.urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname != "raw.githubusercontent.com"
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or not parsed.path.endswith("/reel.mp4")
            or not re.fullmatch(
                r"/venipublishing-main/ai-geopolitic-automation/[0-9a-f]{40}"
                r"/publisher_media/video-ep[1-9][0-9]{0,5}-[0-9]{8}/reel\.mp4",
                parsed.path,
            )):
        raise VideoPublishBlocked("Only the exact immutable GitHub MP4 URL is trusted.")
    try:
        req = urllib.request.Request(url, method="GET", headers={
            "User-Agent": "ai-geopolitic-video-preflight/1.0",
        })
        with urllib.request.urlopen(req, timeout=90) as response:
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            if response.status != 200 or content_type not in (
                    "video/mp4", "application/octet-stream", "binary/octet-stream"):
                raise VideoPublishBlocked("Public video has the wrong HTTP status/content type.")
            digest = hashlib.sha256()
            size = 0
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_PUBLIC_MP4:
                    raise VideoPublishBlocked("Public MP4 exceeded the permitted byte limit.")
                digest.update(chunk)
    except (urllib.error.URLError, TimeoutError, OSError):
        raise VideoPublishBlocked("Immutable public MP4 unavailable; no Meta POST.") from None
    if (size != receipt["video"]["bytes"]
            or digest.hexdigest() != receipt["video"]["sha256"]):
        raise VideoPublishBlocked("Public MP4 checksum does not match the reviewed video.")


class InstagramVideoGraph:
    def __init__(self, token: str):
        if not isinstance(token, str) or len(token) < 16 or "\n" in token:
            raise VideoPublishBlocked("Instagram token is not configured.")
        self.transport = UrlLibGraphTransport(token, timeout=45)

    def account(self, surface: str, caption: str) -> str:
        result = self.transport.request("GET", GRAPH_ROOT + "/me/assigned_instagram_accounts",
                                        {"fields": "id,username", "limit": "100"})
        accounts = result.get("data")
        if not isinstance(accounts, list) or result.get("paging", {}).get("next"):
            raise VideoPublishBlocked("Cannot uniquely verify assigned Instagram account.")
        matches = [str(entry["id"]) for entry in accounts if isinstance(entry, dict)
                   and str(entry.get("username", "")).lower().lstrip("@") == USERNAME
                   and ID_RE.fullmatch(str(entry.get("id", "")))]
        if len(matches) != 1:
            raise VideoPublishBlocked("Instagram token does not uniquely target @ai_geopolitic.")
        user_id = matches[0]
        if surface == "instagram-story":
            # Facebook Login's Stories publishing is Business-only, not Creator.
            detail = self.transport.request("GET", f"{GRAPH_ROOT}/{user_id}",
                                            {"fields": "account_type"})
            if detail.get("account_type") != "BUSINESS":
                raise VideoPublishBlocked("Instagram Story publishing requires a Business account.")
        else:
            recent = self.transport.request("GET", f"{GRAPH_ROOT}/{user_id}/media",
                                            {"fields": "id,caption,media_product_type", "limit": "50"})
            posts = recent.get("data")
            if not isinstance(posts, list):
                raise VideoPublishBlocked("Instagram recent-media duplicate check failed.")
            if any(isinstance(post, dict) and post.get("media_product_type") == "REELS"
                   and str(post.get("caption", "")).strip() == caption.strip()
                   for post in posts):
                raise VideoPublishBlocked("An Instagram Reel with this caption already exists.")
        return user_id

    def _wait_ready(self, container: str) -> None:
        if not ID_RE.fullmatch(container):
            raise VideoPublishBlocked("Invalid Instagram container ID.")
        for attempt in range(24):
            status = self.transport.request("GET", f"{GRAPH_ROOT}/{container}",
                                            {"fields": "status_code"}).get("status_code")
            if status == "FINISHED":
                return
            if status not in ("IN_PROGRESS", "PENDING", None):
                raise VideoPublishBlocked("Instagram video container failed or expired.")
            if attempt < 23:
                time.sleep(5)
        raise VideoPublishBlocked("Instagram processing timed out; reconcile manually.")

    def publish(self, surface: str, user_id: str, url: str, caption: str) -> str:
        if surface not in ("instagram-reel", "instagram-story") or not ID_RE.fullmatch(user_id):
            raise VideoPublishBlocked("Instagram video publishing target is invalid.")
        params = {"media_type": "REELS" if surface == "instagram-reel" else "STORIES",
                  "video_url": url, "is_ai_generated": "true"}
        if surface == "instagram-reel":
            params.update({"caption": caption, "share_to_feed": "true"})
        # Deliberately no caption or story text parameter for Instagram Stories.
        response = self.transport.request("POST", f"{GRAPH_ROOT}/{user_id}/media", params)
        container = str(response.get("id", ""))
        self._wait_ready(container)
        published = self.transport.request("POST", f"{GRAPH_ROOT}/{user_id}/media_publish",
                                           {"creation_id": container})
        media_id = str(published.get("id", ""))
        if not ID_RE.fullmatch(media_id):
            raise VideoPublishBlocked("Instagram publish result is ambiguous; manual reconciliation.")
        return media_id

    def verify(self, surface: str, media_id: str) -> dict:
        if not ID_RE.fullmatch(media_id):
            raise VideoPublishBlocked("Invalid Instagram published ID.")
        item = self.transport.request("GET", f"{GRAPH_ROOT}/{media_id}", {
            "fields": "id,permalink,media_type,media_product_type,is_ai_generated",
        })
        expected_product = "REELS" if surface == "instagram-reel" else "STORY"
        if (str(item.get("id")) != media_id or item.get("media_type") != "VIDEO"
                or item.get("media_product_type") != expected_product):
            raise VideoPublishBlocked("Instagram video surface or identity could not be verified.")
        output = {"instagram_media_id": media_id,
                  "media_product_type_verified": expected_product,
                  "ai_info_verified": item.get("is_ai_generated") is True}
        permalink = item.get("permalink")
        if surface == "instagram-reel":
            parsed = urllib.parse.urlparse(permalink) if isinstance(permalink, str) else None
            if (parsed is None or parsed.scheme != "https"
                    or parsed.hostname not in ("instagram.com", "www.instagram.com")
                    or not parsed.path.startswith("/reel/")):
                raise VideoPublishBlocked("Instagram Reel permalink not confirmed.")
            output["instagram_permalink"] = permalink
        elif isinstance(permalink, str) and permalink:
            parsed = urllib.parse.urlparse(permalink)
            if parsed.scheme == "https" and parsed.hostname in ("instagram.com", "www.instagram.com"):
                output["instagram_story_permalink"] = permalink
        return output


def verify_threads_video(media_id: str, caption: str, post: dict) -> dict | None:
    if (not isinstance(post, dict) or str(post.get("id")) != media_id
            or str(post.get("username", "")).lower().lstrip("@") != EXPECTED_USERNAME
            or post.get("media_type") != "VIDEO"):
        return None
    match = caption_match(caption, post.get("text"))
    url = post.get("permalink", "")
    parsed = urllib.parse.urlparse(url) if isinstance(url, str) else None
    if (match is None or parsed is None or parsed.scheme != "https"
            or parsed.hostname not in ("threads.com", "www.threads.com", "threads.net", "www.threads.net")
            or not parsed.path.startswith(f"/@{EXPECTED_USERNAME}/post/")):
        return None
    return {"threads_media_id": media_id, "threads_permalink": url,
            "caption_verification": match, "media_type_verified": "VIDEO"}


def publish_threads_video(graph: ThreadsGraph, caption: str, url: str) -> dict:
    created = graph.request("POST", "/me/threads", {
        "media_type": "VIDEO", "video_url": url, "text": caption,
        "is_made_with_ai": "true",
        "alt_text": "AI Geopolitic, six-frame editorial Reel",
    })
    container = str(created.get("id", ""))
    graph.wait_ready(container)
    published = graph.request("POST", "/me/threads_publish", {"creation_id": container})
    media_id = str(published.get("id", ""))
    if not media_id.isdigit():
        raise VideoPublishBlocked("Threads publish response had no valid media ID.")
    for attempt in range(8):
        post = graph.request("GET", f"/{media_id}", {
            "fields": "id,username,text,permalink,media_type",
        })
        confirmed = verify_threads_video(media_id, caption, post)
        if confirmed is not None:
            # Threads AI disclosure was sent on creation; the separate Threads
            # post verification checks content but not a readable AI flag.
            confirmed["ai_disclosure_submitted_to_meta"] = True
            return confirmed
        if attempt < 7:
            time.sleep(4)
    raise VideoPublishBlocked("Threads video posted but verification is ambiguous.")


def _git(*args: str) -> str:
    try:
        result = subprocess.run(["git", *args], capture_output=True, check=True,
                                text=True, timeout=90)
    except (OSError, subprocess.SubprocessError):
        raise VideoPublishBlocked("GitHub claim/receipt write unavailable; reconcile manually.") from None
    return result.stdout.strip()


def save_state(surface: str, path: Path, record: dict) -> None:
    # Existing shared-video staging branches do not configure a Git author.
    # Set identity on every publication claim/receipt, before any Meta POST.
    # Do not assume the MP4 producer was also this surface's publisher.
    _git("config", "user.name", "github-actions[bot]")
    _git("config", "user.email", "github-actions[bot]@users.noreply.github.com")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    _git("add", "--", str(path))
    _git("commit", "-m", f"{surface} {record['episode']}: {record['status']}")
    _git("push", "origin", "HEAD:refs/heads/main")


def release(surface: str, episode: str, day: str, commit: str, approval: str,
            *, token: str, run_id: str) -> dict:
    expected = approval_for(surface, episode, day)
    if approval != expected:
        raise VideoPublishBlocked("Exact surface-specific, episode-scoped approval is missing.")
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
            or os.environ.get("GITHUB_REPOSITORY") != "venipublishing-main/ai-geopolitic-automation"
            or os.environ.get("GITHUB_REF") != "refs/heads/main"
            or os.environ.get("GITHUB_WORKFLOW") != WORKFLOW_NAMES[surface]
            or not run_id.isdigit() or _git("branch", "--show-current") != "main"):
        raise VideoPublishBlocked("Live release is allowed only in main-branch GitHub Actions.")
    if not isinstance(token, str) or len(token) < 16 or "\n" in token:
        raise VideoPublishBlocked("Surface-specific Meta token is missing.")
    receipt, caption, url = check_stage(episode, day, commit)
    verify_public_video(receipt, url)
    if surface == "threads-video":
        graph = ThreadsGraph(token)
        account_id, account_name = graph.check_identity_and_duplicate(caption)
    else:
        graph = InstagramVideoGraph(token)
        account_id = graph.account(surface, caption)
        account_name = USERNAME
    # Recheck after stage verification and read-only account preflight, before claim.
    _git("pull", "--ff-only", "origin", "main")
    state = state_path(surface, episode, day)
    if state.exists() or _git("ls-files", "--", str(state)):
        raise VideoPublishBlocked("Existing per-surface publication claim blocks duplicate posting.")
    record = {
        "schema": "ai-geopolitic.publisher.video-publication-receipt.v1",
        "surface": surface, "episode": episode, "date_sast": day,
        "account": account_name, "account_id": account_id,
        "video_sha256": receipt["video"]["sha256"],
        "caption_sha256": receipt["caption_sha256"] if surface != "instagram-story" else None,
        "caption_sent": surface != "instagram-story",
        "audio_master_sha256": SONORA_MASTER_SHA256,
        "public_media_commit": commit, "github_run_id": run_id,
        "claimed_utc": datetime.now(timezone.utc).isoformat(),
        "status": "CLAIMED_NO_AUTOMATIC_RETRY",
    }
    save_state(surface, state, record)  # IRREVERSIBLE GATE: before any Meta POST.
    try:
        if surface == "threads-video":
            outcome = publish_threads_video(graph, caption, url)
        else:
            media_id = graph.publish(surface, account_id, url, caption)
            outcome = graph.verify(surface, media_id)
    except (ThreadsBlocked, InstagramPublishBlocked, VideoPublishBlocked):
        # Claim remains permanent even when Meta completed the POST but timed out.
        raise
    record.update(outcome)
    record["status"] = SUCCESS_STATUS[surface]
    if surface == "instagram-reel" and not outcome["ai_info_verified"]:
        record["status"] = "PUBLISHED_AI_INFO_UNVERIFIED"
    if surface == "instagram-story" and not outcome["ai_info_verified"]:
        record["status"] = "PUBLISHED_STORY_AI_INFO_UNVERIFIED"
    record["published_utc"] = datetime.now(timezone.utc).isoformat()
    # An unrelated publisher may have advanced main. Never resend the Meta POST.
    _git("pull", "--rebase", "origin", "main")
    save_state(surface, state, record)
    if record["status"] != SUCCESS_STATUS[surface]:
        raise VideoPublishBlocked("Video is possibly live; AI label needs manual verification.")
    return {"status": record["status"], "surface": surface, "episode": episode,
            "media_id": outcome.get("instagram_media_id", outcome.get("threads_media_id")),
            "permalink": outcome.get("instagram_permalink", outcome.get("threads_permalink"))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surface", choices=SURFACES, required=True)
    parser.add_argument("--episode", required=True)
    parser.add_argument("--date-sast", required=True)
    parser.add_argument("--media-commit", required=True)
    parser.add_argument("--approval", required=True)
    args = parser.parse_args(argv)
    token_name = ("AI_GEO_THREADS_ACCESS_TOKEN" if args.surface == "threads-video"
                  else "AI_GEO_IG_ACCESS_TOKEN")
    try:
        result = release(args.surface, args.episode, args.date_sast,
                         args.media_commit, args.approval,
                         token=os.environ.get(token_name, ""),
                         run_id=os.environ.get("GITHUB_RUN_ID", ""))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ThreadsBlocked, InstagramPublishBlocked, OSError, ValueError,
            TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED_OR_RECONCILE", "reason": str(exc),
                          "automatic_retry_allowed": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
