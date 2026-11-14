"""The Instagram release is explicit, exactly once, and claim-before-Meta."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest
from PIL import Image

from src import instagram_graph as ig
from src import instagram_release as release

EPISODE, DAY = "Ep146", "2026-11-14"
CAPTION = (
    "Guinean authorities report a provisional toll after 11 November clashes. "
    "#AIGeopolitic #SouthAfrica #Geopolitics #PoliticalAnalysis #NewsBriefing\n\n"
    "The event is factual. The interpretation ideological."
)
COMMIT = "a" * 40


def jpeg_bytes(number: int) -> bytes:
    image = Image.new("RGB", (1080, 1350), (number * 15, 70, 90))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def build_stage(root: Path) -> Path:
    folder = root / "publisher_media/instagram-ep146-20261114"
    folder.mkdir(parents=True)
    media = []
    for i in range(1, 11):
        name = f"Slide{i:02d}of10.jpg"
        data = jpeg_bytes(i)
        (folder / name).write_bytes(data)
        media.append({"name": name, "sha256": release.sha(data), "bytes": len(data),
                      "source_sha256": f"{i:064x}", "width": 1080, "height": 1350})
    (folder / "caption.txt").write_text(CAPTION, encoding="utf-8")
    (folder / "stage.json").write_text(json.dumps({
        "schema": release.STAGE_SCHEMA, "episode": EPISODE, "date_sast": DAY,
        "slide_count": 10, "post_target": "INSTAGRAM_CAROUSEL_ONLY",
        "ai_info_required": True, "approved_for_publication": False,
        "status": "STAGED_FOR_REVIEW_NOT_PUBLISHED", "published": False,
        "caption_sha256": hashlib.sha256(CAPTION.encode()).hexdigest(), "media": media,
    }), encoding="utf-8")
    return folder


def test_instagram_stage_requires_exact_unique_ten_and_ai_flag(tmp_path):
    folder = build_stage(tmp_path)
    receipt, caption, urls = release.check_stage(EPISODE, DAY, COMMIT, tmp_path)
    assert receipt["slide_count"] == 10
    assert caption == CAPTION
    assert len(urls) == 10
    assert urls[0].endswith("/Slide01of10.jpg")
    assert all(COMMIT in url for url in urls)
    stage_path = folder / "stage.json"
    original = json.loads(stage_path.read_text())
    stage_path.write_text(json.dumps(dict(original, ai_info_required=False)))
    with pytest.raises(ig.InstagramPublishBlocked):
        release.check_stage(EPISODE, DAY, COMMIT, tmp_path)
    stage_path.write_text(json.dumps(original))
    (folder / "Slide10of10.jpg").write_bytes((folder / "Slide09of10.jpg").read_bytes())
    with pytest.raises(ig.InstagramPublishBlocked):
        release.check_stage(EPISODE, DAY, COMMIT, tmp_path)


def test_untrusted_public_urls_are_blocked():
    good = [f"{release.GITHUB_RAW}/{COMMIT}/media/Slide{i:02d}of10.jpg"
            for i in range(1, 11)]
    ig.validate_public_urls(good)
    for first in ("https://drive.google.com/private.jpg", "http://raw.githubusercontent.com/a.jpg",
                  "https://raw.githubusercontent.com/test.jpg?secret=abc"):
        with pytest.raises(ig.InstagramPublishBlocked):
            ig.validate_public_urls([first, *good[1:]])


def test_release_requires_literal_approval_before_touching_stage(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(release, "check_stage", lambda *args: pytest.fail("stage access is forbidden"))
    with pytest.raises(ig.InstagramPublishBlocked):
        release.release(EPISODE, DAY, COMMIT, "PUBLISH_THREADS_EP146_20261114",
                        token="valid-instagram-test-token", run_id="123")


def test_claim_is_durable_before_first_meta_publish(monkeypatch, tmp_path):
    sequence = []
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(release, "check_stage", lambda *args: (
        {"caption_sha256": hashlib.sha256(CAPTION.encode()).hexdigest()},
        CAPTION, [f"https://raw.githubusercontent.com/{COMMIT}/{i}.jpg" for i in range(10)]
    ))
    monkeypatch.setattr(release, "verify_public_images", lambda *args: sequence.append("checked_images"))
    monkeypatch.setattr(release, "state_path", lambda *args: tmp_path / "claim.json")
    monkeypatch.setattr(release, "_git", lambda *args: "main" if args == ("branch", "--show-current") else "")
    monkeypatch.setattr(release, "save_state", lambda path, record: sequence.append(record["status"]))

    class StubGraph:
        def __init__(self, transport):
            pass

        def account(self, caption):
            sequence.append("account_readonly")
            return "17841400001234567"

        def publish(self, user_id, urls, caption):
            sequence.append("FIRST_META_POST")
            return "17900123456789012"

        def verify_publication(self, media_id):
            return {"instagram_media_id": media_id,
                    "instagram_permalink": "https://www.instagram.com/p/example/",
                    "ai_info_verified": True}

    monkeypatch.setattr(release, "InstagramGraph", StubGraph)
    result = release.release(EPISODE, DAY, COMMIT, "PUBLISH_INSTAGRAM_EP146_20261114",
                             token="valid-instagram-test-token", run_id="123")
    assert result["status"] == "PUBLISHED_AI_INFO_VERIFIED"
    assert sequence == ["checked_images", "account_readonly", "CLAIMED_NO_AUTOMATIC_RETRY",
                        "FIRST_META_POST", "PUBLISHED_AI_INFO_VERIFIED"]


def test_existing_claim_blocks_without_meta_write(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    state = tmp_path / "claim.json"
    state.write_text('{"status":"CLAIMED_NO_AUTOMATIC_RETRY"}')
    monkeypatch.setattr(release, "state_path", lambda *args: state)
    monkeypatch.setattr(release, "check_stage", lambda *args: (
        {"caption_sha256": release.sha(CAPTION.encode())}, CAPTION, ["url"] * 10
    ))
    monkeypatch.setattr(release, "verify_public_images", lambda *args: None)
    monkeypatch.setattr(release, "_git", lambda *args: "main" if args == ("branch", "--show-current") else "")

    class StubGraph:
        def __init__(self, transport):
            pass

        def account(self, caption):
            return "17841400001234567"

        def publish(self, *args):
            pytest.fail("Existing claim must preclude any POST")

    monkeypatch.setattr(release, "InstagramGraph", StubGraph)
    with pytest.raises(ig.InstagramPublishBlocked, match="Existing Instagram claim"):
        release.release(EPISODE, DAY, COMMIT, "PUBLISH_INSTAGRAM_EP146_20261114",
                        token="valid-instagram-test-token", run_id="123")


def test_no_automatic_retry_if_ai_label_unverified(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    sequence = []
    monkeypatch.setattr(release, "check_stage", lambda *args: (
        {"caption_sha256": release.sha(CAPTION.encode())}, CAPTION, ["url"] * 10
    ))
    monkeypatch.setattr(release, "verify_public_images", lambda *args: None)
    monkeypatch.setattr(release, "state_path", lambda *args: tmp_path / "claim.json")
    monkeypatch.setattr(release, "_git", lambda *args: "main" if args == ("branch", "--show-current") else "")
    monkeypatch.setattr(release, "save_state", lambda path, record: sequence.append(record["status"]))

    class StubGraph:
        def __init__(self, transport):
            pass

        def account(self, caption):
            return "17841400001234567"

        def publish(self, *args):
            return "17900123456789012"

        def verify_publication(self, media_id):
            return {"instagram_media_id": media_id,
                    "instagram_permalink": "https://www.instagram.com/p/example/",
                    "ai_info_verified": False}

    monkeypatch.setattr(release, "InstagramGraph", StubGraph)
    with pytest.raises(ig.InstagramPublishBlocked, match="manual reconciliation"):
        release.release(EPISODE, DAY, COMMIT, "PUBLISH_INSTAGRAM_EP146_20261114",
                        token="valid-instagram-test-token", run_id="123")
    assert sequence == ["CLAIMED_NO_AUTOMATIC_RETRY", "PUBLISHED_AI_INFO_UNVERIFIED"]
