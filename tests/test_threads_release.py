import hashlib
import json

import pytest
from PIL import Image

from src import threads_release as tr
from src.threads_media import ThreadsBlocked, output_folder
from tests.test_threads_media import CAPTION


def make_stage(tmp_path):
    folder = tmp_path / output_folder("Ep145", "2026-11-13")
    folder.mkdir(parents=True)
    data = []
    for i in range(1, 11):
        name = f"Slide{i:02d}of10.jpg"
        Image.new("RGB", (1080, 1350), (i * 14, 10, 35)).save(folder / name, "JPEG")
        contents = (folder / name).read_bytes()
        data.append({"name": name, "sha256": hashlib.sha256(contents).hexdigest(),
                     "bytes": len(contents), "width": 1080, "height": 1350})
    receipt = {"schema": tr.STAGE_SCHEMA, "episode": "Ep145", "date_sast": "2026-11-13",
               "slide_count": 10, "media": data, "post_target": "THREADS_CAROUSEL_ONLY",
               "caption_sha256": hashlib.sha256(CAPTION.encode()).hexdigest(),
               "published": False}
    (folder / "caption.txt").write_text(CAPTION)
    (folder / "stage.json").write_text(json.dumps(receipt))
    return folder


def test_staged_media_sha_and_count_are_verified(tmp_path):
    folder = make_stage(tmp_path)
    receipt, text, urls = tr.check_stage("Ep145", "2026-11-13", "f" * 40, root=tmp_path)
    assert receipt["slide_count"] == 10 and text == CAPTION
    assert len(urls) == 10 and urls[0].endswith("/Slide01of10.jpg")
    (folder / "Slide03of10.jpg").write_bytes(b"tampered")
    with pytest.raises(ThreadsBlocked):
        tr.check_stage("Ep145", "2026-11-13", "f" * 40, root=tmp_path)


def test_no_arbitrary_media_commit(tmp_path):
    make_stage(tmp_path)
    with pytest.raises(ThreadsBlocked):
        tr.check_stage("Ep145", "2026-11-13", "main", root=tmp_path)


def test_threads_graph_account_and_duplicate_checks():
    graph = tr.ThreadsGraph("t" * 20)
    graph.request = lambda method, path, params=None: (
        {"id": "123456", "username": "ai_geopolitic"} if path == "/me"
        else {"data": [{"id": "3", "text": "different"}]}
    )
    assert graph.check_identity_and_duplicate(CAPTION) == ("123456", "ai_geopolitic")
    graph.request = lambda method, path, params=None: (
        {"id": "123456", "username": "wrong-account"} if path == "/me"
        else {"data": []}
    )
    with pytest.raises(ThreadsBlocked):
        graph.check_identity_and_duplicate(CAPTION)
    # Meta removed a single hashtag marker in the real Ep145 post; its
    # normalized text must still block accidental duplicate publication.
    graph.request = lambda method, path, params=None: (
        {"id": "123456", "username": "ai_geopolitic"} if path == "/me"
        else {"data": [{"text": CAPTION.replace("#AIGeopolitic", "AIGeopolitic", 1)}]}
    )
    with pytest.raises(ThreadsBlocked, match="already published"):
        graph.check_identity_and_duplicate(CAPTION)
    graph.request = lambda method, path, params=None: (
        {"id": "123456", "username": "ai_geopolitic"} if path == "/me"
        else {"data": [{"text": CAPTION}]}
    )
    with pytest.raises(ThreadsBlocked):
        graph.check_identity_and_duplicate(CAPTION)


def test_canonical_caption_matching_is_narrow():
    assert tr.caption_match(CAPTION, CAPTION) == "EXACT"
    normalized = CAPTION.replace("#AIGeopolitic", "AIGeopolitic", 1)
    assert tr.caption_match(CAPTION, normalized) == "META_ONE_TOPIC_HASH_REMOVED"
    assert tr.caption_match(CAPTION, normalized.replace("The event", "An event")) is None
    assert tr.caption_match(CAPTION, CAPTION.replace("#AIGeopolitic", "", 1)) is None
    assert tr.caption_match(CAPTION, CAPTION.replace("#", "", 2)) is None


def verified_post(caption=CAPTION, children_count=10):
    return {"id": "10012", "username": "ai_geopolitic", "text": caption,
            "media_type": "CAROUSEL_ALBUM",
            "permalink": "https://www.threads.com/@ai_geopolitic/post/abc",
            "children": {"data": [{"id": str(i)} for i in range(1, children_count + 1)]}}


def test_post_verification_requires_ten_distinct_children_and_right_account():
    assert tr.verify_published_post("10012", CAPTION, verified_post())["carousel_items_verified"] == 10
    assert tr.verify_published_post("10012", CAPTION, verified_post(children_count=9)) is None
    same_ids = verified_post()
    same_ids["children"]["data"][1]["id"] = "1"
    assert tr.verify_published_post("10012", CAPTION, same_ids) is None
    wrong_account = verified_post()
    wrong_account["username"] = "not_ai_geopolitic"
    assert tr.verify_published_post("10012", CAPTION, wrong_account) is None
    wrong_permalink = verified_post()
    wrong_permalink["permalink"] = "https://www.threads.com/@someone_else/post/abc"
    assert tr.verify_published_post("10012", CAPTION, wrong_permalink) is None


def test_threads_graph_posts_image_children_and_carousel_only(monkeypatch):
    graph = tr.ThreadsGraph("t" * 20)
    posts = []
    monkeypatch.setattr(graph, "wait_ready", lambda x: None)
    def send(method, path, params=None):
        if method == "POST":
            posts.append((path, params))
            return {"id": str(10000 + len(posts))}
        return verified_post()
    graph.request = send
    output = graph.publish_carousel(CAPTION, [f"https://sample.test/{i}.jpg" for i in range(10)])
    assert len(posts) == 12
    assert all(x[1]["media_type"] == "IMAGE" and x[1]["is_carousel_item"] == "true" for x in posts[:10])
    assert posts[10][1]["media_type"] == "CAROUSEL"
    assert len(posts[10][1]["children"].split(",")) == 10
    assert posts[10][1]["text"] == CAPTION
    assert posts[11][0] == "/me/threads_publish"
    assert output["threads_permalink"].startswith("https://www.threads.com/")
    assert output["carousel_items_verified"] == 10


def test_threads_publish_accepts_only_the_known_meta_topic_normalization(monkeypatch):
    graph = tr.ThreadsGraph("t" * 20)
    monkeypatch.setattr(graph, "wait_ready", lambda x: None)
    calls = []
    def send(method, path, params=None):
        if method == "POST":
            calls.append(path)
            return {"id": "10012"}
        return verified_post(CAPTION.replace("#AIGeopolitic", "AIGeopolitic", 1))
    graph.request = send
    outcome = graph.publish_carousel(CAPTION, [f"https://sample.test/{i}.jpg" for i in range(10)])
    assert outcome["caption_verification"] == "META_ONE_TOPIC_HASH_REMOVED"
    assert outcome["carousel_items_verified"] == 10
    assert len(calls) == 12


def test_publish_requires_literal_human_gate_before_any_other_action(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    with pytest.raises(ThreadsBlocked, match="authorization"):
        tr.release("Ep145", "2026-11-13", "f" * 40, "wrong",
                   token="t" * 20, run_id="22")


def test_durable_claim_precedes_first_meta_post(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    events = []
    monkeypatch.setattr(tr, "check_stage", lambda *x: (
        {"caption_sha256": hashlib.sha256(CAPTION.encode()).hexdigest()},
        CAPTION, [f"https://sample.test/{i}.jpg" for i in range(10)]))
    monkeypatch.setattr(tr, "verify_public_images", lambda urls: events.append("media_checked"))
    monkeypatch.setattr(tr, "_git", lambda *args: "main" if args[0] == "branch" else "")
    monkeypatch.setattr(tr.ThreadsGraph, "check_identity_and_duplicate", lambda *x: ("123", "ai_geopolitic"))
    def save(path, record):
        events.append(record["status"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record))
    monkeypatch.setattr(tr, "save_state", save)
    def publish(*args):
        events.append("meta_POST")
        return {"threads_media_id": "999", "threads_permalink": "https://www.threads.net/p/999"}
    monkeypatch.setattr(tr.ThreadsGraph, "publish_carousel", publish)
    result = tr.release("Ep145", "2026-11-13", "f" * 40,
                        "PUBLISH_THREADS_EP145_20261113", token="t" * 20, run_id="22")
    assert events == ["media_checked", "CLAIMED_NO_AUTOMATIC_RETRY", "meta_POST", "PUBLISHED_VERIFIED"]
    assert result["carousel_items"] == 10
    with pytest.raises(ThreadsBlocked, match="Existing Threads claim"):
        tr.release("Ep145", "2026-11-13", "f" * 40,
                   "PUBLISH_THREADS_EP145_20261113", token="t" * 20, run_id="23")

