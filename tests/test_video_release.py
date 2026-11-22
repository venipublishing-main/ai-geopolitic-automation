"""Exact-source, per-surface claim-before-Meta and no-caption Story checks."""

import hashlib
import io
import json
from pathlib import Path

import pytest

from src import video_release as vr
from src.reel_media import SONORA_MASTER_SHA256
from tests.test_video_media import CAPTION, fake_plan

EP, DAY, COMMIT = "Ep151", "2026-11-19", "a" * 40
VIDEO = b"mock-mp4" * 25000
INFO = {"name": "reel.mp4", "width": 1080, "height": 1920, "fps": 30,
        "duration_seconds": 18.0, "video_codec": "h264", "audio_codec": "aac",
        "bytes": len(VIDEO), "sha256": hashlib.sha256(VIDEO).hexdigest()}


def make_stage(root):
    folder = root / "publisher_media/video-ep151-20261119"
    folder.mkdir(parents=True)
    (folder / "reel.mp4").write_bytes(VIDEO)
    (folder / "caption.txt").write_text(CAPTION, encoding="utf-8")
    plan = fake_plan()
    rec = {
        "schema": vr.STAGE_SCHEMA, "episode": EP, "date_sast": DAY,
        "post_target": "THREE_INDEPENDENT_VIDEO_PUBLISHERS",
        "status": "STAGED_NOT_PUBLISHED", "published": False,
        "ai_info_required": True, "frame_count": 6, "video_variant": "C_Stronger",
        "duration_seconds": 18.0, "audio_master_sha256": SONORA_MASTER_SHA256,
        "source_frames": plan["frames"],
        "caption_sha256": hashlib.sha256(CAPTION.encode()).hexdigest(),
        "video": INFO,
    }
    (folder / "stage.json").write_text(json.dumps(rec), encoding="utf-8")
    return folder, rec


def test_approval_is_independent_for_each_of_three_surfaces():
    expected = {
        "instagram-reel": "PUBLISH_INSTAGRAM_REEL_EP151_20261119",
        "threads-video": "PUBLISH_THREADS_VIDEO_EP151_20261119",
        "instagram-story": "PUBLISH_INSTAGRAM_STORY_EP151_20261119",
    }
    for surface, literal in expected.items():
        assert vr.approval_for(surface, EP, DAY) == literal
        path = vr.state_path(surface, EP, DAY)
        assert path.as_posix() == f"publisher_state/{surface}-ep151-20261119.json"
    assert len(set(expected.values())) == 3
    with pytest.raises(vr.VideoPublishBlocked):
        vr.approval_for("instagram-post", EP, DAY)


def test_stage_byte_caption_codec_and_audio_guards(monkeypatch, tmp_path):
    folder, rec = make_stage(tmp_path)
    monkeypatch.setattr(vr, "verify_mp4", lambda _: {k: v for k, v in INFO.items() if k != "name"})
    read, caption, url = vr.check_stage(EP, DAY, COMMIT, tmp_path)
    assert read == rec and caption == CAPTION
    assert url.endswith("/publisher_media/video-ep151-20261119/reel.mp4")
    with pytest.raises(vr.VideoPublishBlocked):
        vr.check_stage(EP, DAY, "main", tmp_path)
    (folder / "reel.mp4").write_bytes(VIDEO + b"modified")
    with pytest.raises(vr.VideoPublishBlocked, match="bytes"):
        vr.check_stage(EP, DAY, COMMIT, tmp_path)
    (folder / "reel.mp4").write_bytes(VIDEO)
    (folder / "caption.txt").write_text(CAPTION + "modified", encoding="utf-8")
    with pytest.raises(vr.VideoPublishBlocked):
        vr.check_stage(EP, DAY, COMMIT, tmp_path)
    (folder / "caption.txt").write_text(CAPTION)
    (folder / "stage.json").write_text(json.dumps({**rec,
                                                    "audio_master_sha256": "b" * 64}))
    with pytest.raises(vr.VideoPublishBlocked, match="Version B"):
        vr.check_stage(EP, DAY, COMMIT, tmp_path)


class HttpResponse:
    status = 200
    headers = {"Content-Type": "application/octet-stream"}

    def __init__(self, data):
        self.reader = io.BytesIO(data)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def read(self, size):
        return self.reader.read(size)


def test_public_mp4_download_is_sha_checked_before_meta(monkeypatch):
    url = f"{vr.GITHUB_RAW}/{COMMIT}/publisher_media/video-ep151-20261119/reel.mp4"
    monkeypatch.setattr(vr.urllib.request, "urlopen", lambda *args, **kwargs: HttpResponse(VIDEO))
    vr.verify_public_video({"video": INFO}, url)
    with pytest.raises(vr.VideoPublishBlocked):
        vr.verify_public_video({"video": INFO}, url.replace(COMMIT, "main"))
    monkeypatch.setattr(vr.urllib.request, "urlopen", lambda *args, **kwargs: HttpResponse(VIDEO + b"X"))
    with pytest.raises(vr.VideoPublishBlocked, match="checksum"):
        vr.verify_public_video({"video": INFO}, url)


class FakeIGTransport:
    def __init__(self):
        self.calls = []

    def request(self, method, url, params):
        self.calls.append((method, url, params))
        if url.endswith("/me/assigned_instagram_accounts"):
            return {"data": [{"id": "17841400001234567", "username": "ai_geopolitic"}]}
        if url.endswith("/media") and method == "GET":
            return {"data": []}
        if method == "POST" and url.endswith("/media"):
            return {"id": "17912345678901234"}
        if url.endswith("/media_publish"):
            return {"id": "18012345678901234"}
        if params.get("fields") == "status_code":
            return {"status_code": "FINISHED"}
        if params.get("fields") == "id,permalink,media_type,media_product_type,is_ai_generated":
            product = getattr(self, "verify_product", "REELS")
            return {"id": "18012345678901234", "media_type": "VIDEO",
                    "media_product_type": product, "is_ai_generated": True,
                    "permalink": "https://www.instagram.com/reel/abc/"}
        raise AssertionError((method, url, params))


@pytest.mark.parametrize("surface,product", [
    ("instagram-reel", "REELS"), ("instagram-story", "STORY")])
def test_ig_reel_has_caption_and_story_never_sends_caption(monkeypatch, surface, product):
    graph = vr.InstagramVideoGraph("some-valid-token-text")
    fake = FakeIGTransport()
    fake.verify_product = product
    graph.transport = fake
    user = graph.account(surface, CAPTION)
    assert user == "17841400001234567"
    media_id = graph.publish(surface, user, "https://example.org/reel.mp4", CAPTION)
    assert media_id == "18012345678901234"
    media_posts = [p for m, url, p in fake.calls if m == "POST" and url.endswith("/media")]
    assert len(media_posts) == 1
    assert media_posts[0]["media_type"] == ("REELS" if product == "REELS" else "STORIES")
    assert media_posts[0]["is_ai_generated"] == "true"
    if surface == "instagram-reel":
        assert media_posts[0]["caption"] == CAPTION
        assert media_posts[0]["share_to_feed"] == "true"
    else:
        assert "caption" not in media_posts[0]
        assert "text" not in media_posts[0]
    outcome = graph.verify(surface, media_id)
    assert outcome["media_product_type_verified"] == product
    assert outcome["ai_info_verified"] is True
    if surface == "instagram-story":
        assert "instagram_permalink" not in outcome


def test_story_preflight_does_not_request_unsupported_account_type():
    graph = vr.InstagramVideoGraph("some-valid-token-text")
    fake = FakeIGTransport()
    graph.transport = fake
    assert graph.account("instagram-story", CAPTION) == "17841400001234567"
    # The Graph IG User no longer supports account_type. Story eligibility
    # is enforced by Meta when creating a Story, after the durable claim.
    assert len(fake.calls) == 1
    assert fake.calls[0][0] == "GET"
    assert fake.calls[0][2]["fields"] == "id,username"


def test_story_mismatched_account_fails_before_meta_write():
    graph = vr.InstagramVideoGraph("some-valid-token-text")
    fake = FakeIGTransport()
    original = fake.request

    def wrong_identity(method, url, params):
        if url.endswith("/me/assigned_instagram_accounts"):
            return {"data": [{"id": "17841400001234567", "username": "somebody_else"}]}
        return original(method, url, params)

    fake.request = wrong_identity
    graph.transport = fake
    with pytest.raises(vr.VideoPublishBlocked, match="uniquely target"):
        graph.account("instagram-story", CAPTION)
    assert all(method == "GET" for method, _, _ in fake.calls)


def test_threads_video_is_single_video_with_text_not_carousel(monkeypatch):
    calls = []
    graph = vr.ThreadsGraph("t" * 24)
    graph.wait_ready = lambda media: calls.append(("ready", media))

    def fake(method, path, params=None):
        calls.append((method, path, params))
        if method == "POST":
            return {"id": "123456789" if path == "/me/threads" else "987654321"}
        return {"id": "987654321", "username": "ai_geopolitic",
                "text": CAPTION, "media_type": "VIDEO",
                "permalink": "https://www.threads.com/@ai_geopolitic/post/abc"}

    graph.request = fake
    out = vr.publish_threads_video(graph, CAPTION, "https://example.org/reel.mp4")
    assert out["media_type_verified"] == "VIDEO"
    posts = [entry[2] for entry in calls if len(entry) == 3 and entry[0] == "POST"]
    assert len(posts) == 2
    assert posts[0]["media_type"] == "VIDEO" and posts[0]["text"] == CAPTION
    assert posts[0]["is_made_with_ai"] == "true"
    assert posts[1] == {"creation_id": "123456789"}
    assert out["ai_disclosure_submitted_to_meta"] is True


def prepare_release(monkeypatch, tmp_path, surface):
    events = []
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("GITHUB_REPOSITORY", "venipublishing-main/ai-geopolitic-automation")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_WORKFLOW", vr.WORKFLOW_NAMES[surface])
    monkeypatch.setattr(vr, "_git", lambda *args: "main" if args == (
        "branch", "--show-current") else "")
    monkeypatch.setattr(vr, "check_stage", lambda *args: (
        {"video": INFO, "caption_sha256": hashlib.sha256(CAPTION.encode()).hexdigest()},
        CAPTION, "https://example.org/reel.mp4"))
    monkeypatch.setattr(vr, "verify_public_video", lambda *args: events.append("public_media_verified"))
    monkeypatch.setattr(vr, "state_path", lambda *args: tmp_path / "claimed.json")
    monkeypatch.setattr(vr, "save_state", lambda s, p, record: events.append(record["status"]))

    class FakeIG:
        def __init__(self, token):
            pass

        def account(self, surface, caption):
            events.append("read_only_account")
            return "17841400001234567"

        def publish(self, surface, user_id, url, caption):
            events.append("FIRST_META_POST")
            return "18012345678901234"

        def verify(self, surface, media_id):
            return {"instagram_media_id": media_id, "ai_info_verified": True,
                    "instagram_permalink": "https://www.instagram.com/reel/abc/"}

    class FakeThreads:
        def __init__(self, token):
            pass

        def check_identity_and_duplicate(self, caption):
            events.append("read_only_account")
            return "7654321", "ai_geopolitic"

    monkeypatch.setattr(vr, "InstagramVideoGraph", FakeIG)
    monkeypatch.setattr(vr, "ThreadsGraph", FakeThreads)
    monkeypatch.setattr(vr, "publish_threads_video", lambda *args: (
        events.append("FIRST_META_POST"),
        {"threads_media_id": "987654321", "threads_permalink":
         "https://www.threads.com/@ai_geopolitic/post/abc"})[1])
    return events


@pytest.mark.parametrize("surface", vr.SURFACES)
def test_each_surface_durably_claims_before_meta_post(monkeypatch, tmp_path, surface):
    events = prepare_release(monkeypatch, tmp_path, surface)
    result = vr.release(surface, EP, DAY, COMMIT, vr.approval_for(surface, EP, DAY),
                        token="s" * 25, run_id="123")
    assert result["status"] == vr.SUCCESS_STATUS[surface]
    assert events == ["public_media_verified", "read_only_account",
                      "CLAIMED_NO_AUTOMATIC_RETRY", "FIRST_META_POST", vr.SUCCESS_STATUS[surface]]


def test_wrong_confirmation_and_ever_claimed_block_all_meta_writes(monkeypatch, tmp_path):
    events = prepare_release(monkeypatch, tmp_path, "instagram-reel")
    with pytest.raises(vr.VideoPublishBlocked, match="approval"):
        vr.release("instagram-reel", EP, DAY, COMMIT,
                   vr.approval_for("instagram-story", EP, DAY), token="s" * 25, run_id="123")
    assert events == []
    (tmp_path / "claimed.json").write_text('{"status":"CLAIMED_NO_AUTOMATIC_RETRY"}')
    with pytest.raises(vr.VideoPublishBlocked, match="Existing"):
        vr.release("instagram-reel", EP, DAY, COMMIT,
                   vr.approval_for("instagram-reel", EP, DAY), token="s" * 25, run_id="123")
    assert "FIRST_META_POST" not in events


def test_failed_durable_claim_stops_before_meta(monkeypatch, tmp_path):
    events = prepare_release(monkeypatch, tmp_path, "instagram-story")

    def failed_claim(*args):
        events.append("CLAIM_FAILED")
        raise vr.VideoPublishBlocked("Cannot save durable claim")

    monkeypatch.setattr(vr, "save_state", failed_claim)
    with pytest.raises(vr.VideoPublishBlocked, match="durable"):
        vr.release("instagram-story", EP, DAY, COMMIT,
                   vr.approval_for("instagram-story", EP, DAY), token="s" * 25, run_id="123")
    assert events == ["public_media_verified", "read_only_account", "CLAIM_FAILED"]


def test_wrong_workflow_cannot_invoke_another_video_surface(monkeypatch, tmp_path):
    events = prepare_release(monkeypatch, tmp_path, "instagram-reel")
    monkeypatch.setenv("GITHUB_WORKFLOW", vr.WORKFLOW_NAMES["instagram-story"])
    with pytest.raises(vr.VideoPublishBlocked, match="GitHub Actions"):
        vr.release("instagram-reel", EP, DAY, COMMIT,
                   vr.approval_for("instagram-reel", EP, DAY),
                   token="s" * 25, run_id="123")
    assert events == []

def test_shared_stage_video_receipt_configures_git_identity_before_claim(monkeypatch, tmp_path):
    """All video surfaces must set commit identity, even when reusing another's MP4."""
    commands = []
    monkeypatch.setattr(vr, "_git", lambda *args: commands.append(args) or "")
    path = tmp_path / "publisher_state" / "threads-video-ep151-20261119.json"
    vr.save_state("threads-video", path, {"episode": EP, "status": "CLAIMED_NO_AUTOMATIC_RETRY"})
    assert commands == [
        ("config", "user.name", "github-actions[bot]"),
        ("config", "user.email", "github-actions[bot]@users.noreply.github.com"),
        ("add", "--", str(path)),
        ("commit", "-m", "threads-video Ep151: CLAIMED_NO_AUTOMATIC_RETRY"),
        ("push", "origin", "HEAD:refs/heads/main"),
    ]
    assert path.exists()


def test_video_claim_git_identity_failure_stops_before_writing_claim(monkeypatch, tmp_path):
    path = tmp_path / "publisher_state" / "threads-video-ep151-20261119.json"
    def reject_config(*args):
        raise vr.VideoPublishBlocked("Git identity unavailable")
    monkeypatch.setattr(vr, "_git", reject_config)
    with pytest.raises(vr.VideoPublishBlocked, match="identity"):
        vr.save_state("threads-video", path, {"episode": EP, "status": "CLAIMED_NO_AUTOMATIC_RETRY"})
    assert not path.exists()
