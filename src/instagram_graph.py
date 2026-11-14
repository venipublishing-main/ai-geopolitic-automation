"""Narrow Graph API client for an explicitly approved Instagram carousel.

This client cannot select an account or episode by recency, schedule posts,
or publish a Reel. A durable publication claim is the caller's responsibility.
"""
from __future__ import annotations

import ipaddress
import json
import re
import time
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from src.instagram_media import InstagramStageBlocked

GRAPH_ROOT = "https://graph.facebook.com/v26.0"
ID_RE = re.compile(r"[0-9]{5,30}\Z")
USERNAME = "ai_geopolitic"
HOST = "raw.githubusercontent.com"


class InstagramPublishBlocked(InstagramStageBlocked):
    """Never retry automatically after a Meta write might have occurred."""


class GraphTransport(Protocol):
    def request(self, method: str, url: str, payload: dict) -> dict: ...


@dataclass(frozen=True)
class UrlLibGraphTransport:
    token: str
    timeout: int = 30

    def request(self, method: str, url: str, payload: dict) -> dict:
        if (method not in ("GET", "POST")
                or not url.startswith(GRAPH_ROOT + "/")
                or not self.token or "\n" in self.token):
            raise InstagramPublishBlocked("Instagram Graph transport is not configured safely.")
        encoded = urlencode(payload)
        request = Request(
            url + ("?" + encoded if method == "GET" and encoded else ""),
            data=encoded.encode("utf-8") if method == "POST" else None,
            headers={"Authorization": "Bearer " + self.token,
                     "User-Agent": "ai-geopolitic-instagram-release/1.0"},
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read(256 * 1024 + 1)
                if len(raw) > 256 * 1024:
                    raise InstagramPublishBlocked("Meta response exceeds safe limit.")
                data = json.loads(raw.decode("utf-8"))
        except (HTTPError, URLError, OSError, TimeoutError, ValueError, UnicodeError):
            # Errors may include credentials; never include raw provider text.
            raise InstagramPublishBlocked("Meta request failed; reconcile an existing claim manually.") from None
        if not isinstance(data, dict) or "error" in data:
            raise InstagramPublishBlocked("Meta response was rejected or malformed.")
        return data


def validate_public_urls(urls: list[str]) -> None:
    if not isinstance(urls, list) or len(urls) != 10 or len(set(urls)) != 10:
        raise InstagramPublishBlocked("Exactly ten distinct public slide URLs are required.")
    for link in urls:
        if not isinstance(link, str) or len(link) > 2000:
            raise InstagramPublishBlocked("Invalid media URL.")
        parts = urlparse(link)
        if (parts.scheme != "https" or parts.hostname != HOST
                or parts.username or parts.password or parts.fragment or parts.query
                or not parts.path.endswith(".jpg")):
            raise InstagramPublishBlocked("Media must use approved immutable public JPEG URLs.")
        try:
            ipaddress.ip_address(parts.hostname)
        except ValueError:
            pass
        else:
            raise InstagramPublishBlocked("Raw IP addresses are not approved.")


@dataclass
class InstagramGraph:
    transport: GraphTransport

    def account(self, caption: str) -> str:
        """Check unique assigned target and recent duplicate captions read-only."""
        result = self.transport.request("GET", GRAPH_ROOT + "/me/assigned_instagram_accounts",
                                        {"fields": "id,username", "limit": "100"})
        data = result.get("data")
        if not isinstance(data, list) or result.get("paging", {}).get("next"):
            raise InstagramPublishBlocked("Assigned Instagram accounts cannot be verified uniquely.")
        matches = [str(x["id"]) for x in data if isinstance(x, dict)
                   and str(x.get("username", "")).lower().lstrip("@") == USERNAME
                   and ID_RE.fullmatch(str(x.get("id", "")))]
        if len(matches) != 1:
            raise InstagramPublishBlocked("Token is not uniquely associated with @ai_geopolitic.")
        ig_id = matches[0]
        recent = self.transport.request("GET", f"{GRAPH_ROOT}/{ig_id}/media",
                                        {"fields": "id,caption,permalink", "limit": "50"})
        posts = recent.get("data")
        if not isinstance(posts, list):
            raise InstagramPublishBlocked("Could not verify recent Instagram publications.")
        if any(isinstance(post, dict) and str(post.get("caption", "")).strip() == caption.strip()
               for post in posts):
            raise InstagramPublishBlocked("This exact caption already exists on Instagram.")
        return ig_id

    def _ready(self, media_id: str) -> None:
        if not ID_RE.fullmatch(str(media_id)):
            raise InstagramPublishBlocked("Meta media container ID is invalid.")
        for attempt in range(12):
            item = self.transport.request("GET", f"{GRAPH_ROOT}/{media_id}",
                                          {"fields": "status_code"})
            status = str(item.get("status_code", "")).upper()
            if status in ("FINISHED", "PUBLISHED"):
                return
            if status not in ("IN_PROGRESS", "PENDING", ""):
                raise InstagramPublishBlocked("Meta media container failed processing.")
            if attempt < 11:
                time.sleep(2)
        raise InstagramPublishBlocked("Meta media timed out; do not automatically retry.")

    def publish(self, ig_id: str, urls: list[str], caption: str) -> str:
        if not ID_RE.fullmatch(str(ig_id)):
            raise InstagramPublishBlocked("Invalid approved Instagram account ID.")
        validate_public_urls(urls)
        if not isinstance(caption, str) or not 30 <= len(caption) <= 2200:
            raise InstagramPublishBlocked("Invalid carousel caption.")
        endpoint = f"{GRAPH_ROOT}/{ig_id}/media"
        children: list[str] = []
        for link in urls:
            response = self.transport.request("POST", endpoint,
                                              {"image_url": link, "is_carousel_item": "true"})
            child = str(response.get("id", ""))
            self._ready(child)
            children.append(child)
        parent = self.transport.request("POST", endpoint, {
            "media_type": "CAROUSEL", "children": ",".join(children),
            "caption": caption, "is_ai_generated": "true",
        })
        container = str(parent.get("id", ""))
        self._ready(container)
        published = self.transport.request("POST", f"{GRAPH_ROOT}/{ig_id}/media_publish",
                                           {"creation_id": container})
        media_id = str(published.get("id", ""))
        if not ID_RE.fullmatch(media_id):
            raise InstagramPublishBlocked("Media publish outcome is ambiguous; reconcile manually.")
        return media_id

    def verify_publication(self, media_id: str) -> dict:
        if not ID_RE.fullmatch(str(media_id)):
            raise InstagramPublishBlocked("Invalid published media ID.")
        result = self.transport.request("GET", f"{GRAPH_ROOT}/{media_id}",
                                        {"fields": "id,permalink,is_ai_generated"})
        if str(result.get("id")) != media_id:
            raise InstagramPublishBlocked("Cannot verify Instagram post identifier.")
        permalink = result.get("permalink")
        parsed = urlparse(permalink) if isinstance(permalink, str) else None
        if (parsed is None or parsed.scheme != "https"
                or parsed.hostname not in ("www.instagram.com", "instagram.com")
                or not parsed.path.startswith(("/p/", "/reel/"))):
            raise InstagramPublishBlocked("Instagram permalink is not verified.")
        return {"instagram_media_id": media_id, "instagram_permalink": permalink,
                "ai_info_verified": result.get("is_ai_generated") is True}
