"""Instagram API with Instagram Login: 10-image carousel, disconnected from the CLI.

Uses the direct Instagram Login access-token flow (not Veni Publishing's
Facebook Page or the legacy Veni Faithful token). Required scopes include
instagram_business_basic and instagram_business_content_publish.
Callers must provide ten verified public HTTPS JPEG URLs, the correct account
token, durable idempotency and a separately enabled publish permission. This
module is never called by publisher_cli.py or scheduled GitHub Actions.
"""
from __future__ import annotations

import ipaddress
import json
import re
import time
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .publisher_archive import PublisherBlocked

IDENTIFIER = re.compile(r"^[0-9]{5,30}$")
API_VERSION = re.compile(r"^v[0-9]{1,2}\.[0-9]{1,2}$")
MAX_POLLS = 12
ALLOWED_STATUSES = {"FINISHED", "PUBLISHED"}


class InstagramPublishBlocked(PublisherBlocked):
    pass


class GraphTransport(Protocol):
    def request(self, method: str, url: str, payload: dict) -> dict: ...


@dataclass(frozen=True)
class UrlLibGraphTransport:
    """Never puts access tokens in URLs, error text, or exception messages."""
    token: str
    timeout: int = 25

    def request(self, method: str, url: str, payload: dict) -> dict:
        if method not in ("GET", "POST") or not url.startswith("https://graph.instagram.com/"):
            raise InstagramPublishBlocked("Unexpected Meta Graph API endpoint.")
        if not self.token:
            raise InstagramPublishBlocked("Instagram publishing token is unavailable.")
        if method == "GET":
            request = Request(url + "?" + urlencode(payload),
                              headers={"Authorization": f"Bearer {self.token}"},
                              method="GET")
        else:
            request = Request(url, data=urlencode(payload).encode("utf-8"),
                              headers={"Authorization": f"Bearer {self.token}"},
                              method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read(200_000).decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("Unexpected Graph response.")
                return data
        except (HTTPError, URLError, OSError, ValueError, UnicodeError):
            raise InstagramPublishBlocked(
                "Instagram API request failed; outcome must be reconciled before retry."
            ) from None


def validate_public_urls(urls: list[str], *, allowed_hostname: str) -> None:
    if len(urls) != 10 or len(set(urls)) != 10:
        raise InstagramPublishBlocked("A carousel requires ten distinct public image URLs.")
    if not allowed_hostname or allowed_hostname in ("localhost", "127.0.0.1"):
        raise InstagramPublishBlocked("A dedicated public media-delivery hostname is required.")
    for link in urls:
        if not isinstance(link, str) or len(link) > 2000:
            raise InstagramPublishBlocked("Invalid public media URL.")
        parts = urlparse(link)
        if parts.scheme != "https" or parts.hostname != allowed_hostname:
            raise InstagramPublishBlocked("Media URL host differs from the authorised delivery host.")
        if parts.username or parts.password or parts.fragment or parts.query or not parts.path.lower().endswith(".jpg"):
            raise InstagramPublishBlocked("Delivery URL cannot contain credentials, query tokens or non-JPEG paths.")
        if parts.hostname in ("drive.google.com", "docs.google.com", "localhost"):
            raise InstagramPublishBlocked("Private Drive/share links are not public delivery URLs.")
        try:
            ipaddress.ip_address(parts.hostname)
            raise InstagramPublishBlocked("Raw IP addresses are not approved for image delivery.")
        except ValueError:
            pass


@dataclass
class InstagramCarouselPublisher:
    ig_user_id: str
    graph_version: str
    transport: GraphTransport

    def __post_init__(self):
        if not IDENTIFIER.fullmatch(self.ig_user_id) or not API_VERSION.fullmatch(self.graph_version):
            raise InstagramPublishBlocked("Instagram account or API version is not configured correctly.")

    def _path(self, tail: str) -> str:
        return f"https://graph.instagram.com/{self.graph_version}/{self.ig_user_id}/{tail}"

    def _read_container_status(self, container_id: str) -> str:
        if not IDENTIFIER.fullmatch(container_id):
            raise InstagramPublishBlocked("Meta returned an invalid container identifier.")
        url = f"https://graph.instagram.com/{self.graph_version}/{container_id}"
        result = self.transport.request("GET", url, {"fields": "status_code"})
        return str(result.get("status_code", "")).upper()

    def _ready(self, container_id: str, *, sleep_seconds: float = 2.0) -> None:
        for attempt in range(MAX_POLLS):
            status = self._read_container_status(container_id)
            if status in ALLOWED_STATUSES:
                return
            if status in ("ERROR", "EXPIRED", "FAILED") or (status not in ("IN_PROGRESS", "PENDING", "")):
                raise InstagramPublishBlocked("A Meta image or carousel container failed processing.")
            if attempt != MAX_POLLS - 1:
                time.sleep(sleep_seconds)
        raise InstagramPublishBlocked("Meta processing timed out; do not retry the publish blindly.")

    def publish(
        self, image_urls: list[str], caption: str, *,
        allowed_hostname: str, explicit_external_publish_permission: bool = False,
    ) -> str:
        """One 10-image carousel. No implicit retries after ambiguous POSTs."""
        if explicit_external_publish_permission is not True:
            raise InstagramPublishBlocked("Live publication is disabled by default.")
        validate_public_urls(image_urls, allowed_hostname=allowed_hostname)
        if not isinstance(caption, str) or not 20 <= len(caption) <= 2200:
            raise InstagramPublishBlocked("Invalid Instagram carousel caption.")
        ids: list[str] = []
        for url in image_urls:
            result = self.transport.request(
                "POST", self._path("media"),
                {"image_url": url, "is_carousel_item": "true"},
            )
            child = str(result.get("id", ""))
            if not IDENTIFIER.fullmatch(child):
                raise InstagramPublishBlocked("Media container creation returned no valid ID.")
            self._ready(child)
            ids.append(child)
        parent = self.transport.request(
            "POST", self._path("media"),
            {"media_type": "CAROUSEL", "children": ",".join(ids), "caption": caption},
        )
        container = str(parent.get("id", ""))
        if not IDENTIFIER.fullmatch(container):
            raise InstagramPublishBlocked("Carousel container creation returned no valid ID.")
        self._ready(container)
        result = self.transport.request(
            "POST", self._path("media_publish"), {"creation_id": container}
        )
        published_id = str(result.get("id", ""))
        if not IDENTIFIER.fullmatch(published_id):
            raise InstagramPublishBlocked(
                "Media publish outcome unknown; reconcile account media before retry."
            )
        return published_id
