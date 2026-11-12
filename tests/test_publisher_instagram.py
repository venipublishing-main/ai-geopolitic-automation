"""Offline Instagram transaction tests: absolutely no real Meta requests."""
from __future__ import annotations

import pytest

from src.publisher_instagram import (
    InstagramCarouselPublisher, InstagramPublishBlocked, validate_public_urls,
)

IG_ID = "17841412345678901"
CAPTION = "TEST ONLY — automated QA; not a production news briefing."
URLS = [f"https://media.test.example/qa/test_slide_{i:02d}.jpg" for i in range(1, 11)]


class FakeGraph:
    def __init__(self):
        self.calls = []
        self.counter = 0
        self.failed_status = None
        self.ambiguous_publish = False

    def request(self, method: str, url: str, payload: dict) -> dict:
        self.calls.append((method, url, payload.copy()))
        if method == "GET":
            return {"status_code": self.failed_status or "FINISHED"}
        if url.endswith("/media_publish"):
            return {} if self.ambiguous_publish else {"id": "17899012345678900"}
        if "media_type" in payload:
            return {"id": "17777777777777777"}
        self.counter += 1
        return {"id": str(17700000000000000 + self.counter)}


def client(graph):
    return InstagramCarouselPublisher(IG_ID, "v24.0", graph)


def test_ten_image_carousel_creates_10_children_then_parent_then_one_publish():
    transport = FakeGraph()
    returned = client(transport).publish(
        URLS, CAPTION, allowed_hostname="media.test.example",
        explicit_external_publish_permission=True,
    )
    assert returned == "17899012345678900"
    children = [c for c in transport.calls if c[0] == "POST"
                and c[1].endswith("/media") and c[2].get("is_carousel_item") == "true"]
    parents = [c for c in transport.calls if c[0] == "POST"
               and c[2].get("media_type") == "CAROUSEL"]
    publishes = [c for c in transport.calls if c[0] == "POST"
                 and c[1].endswith("/media_publish")]
    assert len(children) == 10 and len(parents) == 1 and len(publishes) == 1
    assert [c[2]["image_url"] for c in children] == URLS
    assert parents[0][2]["caption"] == CAPTION
    assert parents[0][2]["is_ai_generated"] == "true"
    assert all("is_ai_generated" not in c[2] for c in children)
    assert parents[0][2]["children"] == ",".join(str(17700000000000000 + i)
                                                  for i in range(1, 11))
    assert publishes[0][2]["creation_id"] == "17777777777777777"


def test_no_permission_means_zero_calls():
    fake = FakeGraph()
    with pytest.raises(InstagramPublishBlocked, match="disabled"):
        client(fake).publish(URLS, CAPTION, allowed_hostname="media.test.example")
    assert fake.calls == []


@pytest.mark.parametrize("mutation", [
    "only_nine", "duplicate", "drive_url", "http", "wrong_host", "query_token",
    "local_ip", "wrong_extension",
])
def test_unsafe_or_missing_media_blocks_before_first_request(mutation):
    urls = URLS[:]
    hostname = "media.test.example"
    if mutation == "only_nine":
        urls.pop()
    elif mutation == "duplicate":
        urls[1] = urls[0]
    elif mutation == "drive_url":
        urls[0] = "https://drive.google.com/file/d/1234567890/view.jpg"
        hostname = "drive.google.com"
    elif mutation == "http":
        urls[0] = urls[0].replace("https://", "http://")
    elif mutation == "wrong_host":
        urls[0] = urls[0].replace("media.test.example", "unknown.example")
    elif mutation == "query_token":
        urls[0] += "?oauth=abc"
    elif mutation == "local_ip":
        urls = [f"https://127.0.0.1/assets/{i}.jpg" for i in range(10)]
        hostname = "127.0.0.1"
    else:
        urls[0] = urls[0].replace(".jpg", ".png")
    fake = FakeGraph()
    with pytest.raises(InstagramPublishBlocked):
        client(fake).publish(urls, CAPTION, allowed_hostname=hostname,
                             explicit_external_publish_permission=True)
    assert fake.calls == []


def test_parent_cannot_publish_if_child_image_processing_failed(monkeypatch):
    transport = FakeGraph()
    transport.failed_status = "ERROR"
    with pytest.raises(InstagramPublishBlocked):
        client(transport).publish(URLS, CAPTION, allowed_hostname="media.test.example",
                                  explicit_external_publish_permission=True)
    assert not any(x[1].endswith("/media_publish") for x in transport.calls)
    assert not any(x[2].get("media_type") == "CAROUSEL" for x in transport.calls)


def test_meta_ambiguous_publish_id_is_not_treated_as_success():
    transport = FakeGraph()
    transport.ambiguous_publish = True
    with pytest.raises(InstagramPublishBlocked, match="unknown"):
        client(transport).publish(URLS, CAPTION, allowed_hostname="media.test.example",
                                  explicit_external_publish_permission=True)
    assert len([x for x in transport.calls if x[1].endswith("/media_publish")]) == 1


def test_account_id_and_version_are_configured_not_guessed():
    with pytest.raises(InstagramPublishBlocked):
        InstagramCarouselPublisher("not-an-id", "v24.0", FakeGraph())
    with pytest.raises(InstagramPublishBlocked):
        InstagramCarouselPublisher(IG_ID, "latest", FakeGraph())


def test_creator_publishing_uses_unified_login_graph_host():
    fake = FakeGraph()
    client(fake).publish(URLS, CAPTION, allowed_hostname="media.test.example",
                         explicit_external_publish_permission=True)
    assert fake.calls
    assert all(call[1].startswith("https://graph.facebook.com/v24.0/")
               for call in fake.calls)
    assert not any("graph.instagram.com" in call[1] for call in fake.calls)
