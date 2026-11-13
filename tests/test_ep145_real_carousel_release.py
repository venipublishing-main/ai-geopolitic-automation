"""No-provider, no-network, no-publishing tests for Ep145 real CAROUSEL-ONLY release."""
from __future__ import annotations
import hashlib
import io
import json
from datetime import date
from pathlib import Path

import pytest
from PIL import Image

from src import publisher_ep145_stage as stage
from src import publisher_ep145_real as release

PLAN = Path(__file__).resolve().parents[1] / "publisher_release/ep145-real-plan.json"
TODAY = date(2026, 11, 13)


def approved_signal(plan):
    return {
        "schema":"ai-geopolitic.publisher.ep145-real-approval.v1",
        "episode":"Ep145",
        "date_sast":"2026-11-13",
        "archive_folder_id":"1mvKV0f6LFwv8sln8Ps0YD9Ql5f9lLP9H",
        "approved_account":"ai_geopolitic",
        "post_targets":["CAROUSEL"],
        "no_reel":True, "no_music":True, "test_only":False,
        "previously_published":False,
        "direct_user_approval":"IAN_APPROVED_EP145_CAROUSEL_ONLY_20261113",
        "caption_sha256":plan["carousel_caption"]["sha256"],
    }


def test_plan_is_exactly_10_real_carousel_slides_no_reel_or_music():
    plan = stage.load_plan(PLAN)
    assert len(plan["slide_items"]) == 10
    assert plan["post_targets"] == ["CAROUSEL"]
    assert "reel_items" not in plan and "music" not in plan
    assert plan["carousel_caption"]["content"].startswith("A tenth suspect was arrested")
    assert release.verify_release_signal(approved_signal(plan), plan) == plan["carousel_caption"]["content"]


@pytest.mark.parametrize("change", [
    {"post_targets":["REEL"]}, {"post_targets":["CAROUSEL","REEL"]},
    {"no_music":False}, {"no_reel":False}, {"test_only":True},
    {"previously_published":True}, {"approved_account":"not_our_ig"},
    {"direct_user_approval":"UNKNOWN"}, {"caption_sha256":"0"*64},
])
def test_scope_or_approval_mutations_are_blocked(change):
    plan = stage.load_plan(PLAN)
    signal = approved_signal(plan)
    signal.update(change)
    with pytest.raises(release.RealReleaseBlocked):
        release.verify_release_signal(signal, plan)


def test_stage_verifies_pinned_png_bytes_and_4x5_dimensions(monkeypatch, tmp_path):
    monkeypatch.setattr(stage,"sast_today",lambda: TODAY)
    plan = stage.load_plan(PLAN)
    im = Image.new("RGB", (1080,1350), "white")
    buf = io.BytesIO()
    im.save(buf,format="PNG")
    raw_png = buf.getvalue()
    for item in plan["slide_items"]:
        item["sha256"] = hashlib.sha256(raw_png).hexdigest()
    listing = [{
        "Name":item["name"], "ID":item["id"],"IsDir":False,"MimeType":"image/png",
    } for item in plan["slide_items"]]
    calls = []
    def fake_rclone(*args, limit):
        calls.append(args[0])
        if args[0]=="lsjson":return json.dumps(listing).encode()
        if args[0]=="cat":return raw_png
        raise AssertionError("write command not permitted")
    monkeypatch.setattr(stage,"safe_rclone",fake_rclone)
    receipt = stage.stage(plan, tmp_path / "output")
    assert receipt["count"] == 10
    assert len(list((tmp_path / "output").glob("*.jpg"))) == 10
    assert calls == ["lsjson"]+["cat"]*10
    for file in (tmp_path / "output").glob("*.jpg"):
        with Image.open(file) as out:
            assert out.format=="JPEG" and out.size==(1080,1350)


def test_stage_rejects_original_sha_mismatch_before_staging(monkeypatch, tmp_path):
    monkeypatch.setattr(stage,"sast_today",lambda: TODAY)
    plan = stage.load_plan(PLAN)
    listing = [{
        "Name":item["name"],"ID":item["id"],"IsDir":False,"MimeType":"image/png",
    } for item in plan["slide_items"]]
    monkeypatch.setattr(stage,"safe_rclone",lambda *args, limit:
                        json.dumps(listing).encode() if args[0]=="lsjson" else b"FAKE FILE")
    target = tmp_path / "out"
    with pytest.raises(stage.StageBlocked):
        stage.stage(plan,target)
    assert not target.exists()


def test_stage_rejects_ambiguous_duplicate_archived_names(monkeypatch, tmp_path):
    monkeypatch.setattr(stage,"sast_today",lambda: TODAY)
    plan=stage.load_plan(PLAN)
    entries = [{"Name":x["name"],"ID":x["id"],"IsDir":False,"MimeType":"image/png"}
               for x in plan["slide_items"]]
    entries.append(entries[0].copy())
    monkeypatch.setattr(stage,"safe_rclone",lambda *args, limit:
                        json.dumps(entries).encode())
    with pytest.raises(stage.StageBlocked):
        stage.stage(plan,tmp_path / "out")


def test_staged_immutable_receipt_has_no_reel_and_ten_items(monkeypatch,tmp_path):
    plan=stage.load_plan(PLAN)
    monkeypatch.setattr(release,"STAGE_RECEIPT",tmp_path/"receipt.json")
    media=[{"name":f"Slide{i:02d}of10.jpg","sha256":f"{i:064x}",
            "width":1080,"height":1350,"size":1234} for i in range(1,11)]
    receipt={"schema":"ai-geopolitic.publisher.ep145-carousel-media-stage.v1",
             "episode":"Ep145","archive_folder_id":plan["archive_folder_id"],
             "count":10,"source_sha256_verified":True,
             "no_reel":True,"no_audio":True,"media":media}
    (tmp_path/"receipt.json").write_text(json.dumps(receipt))
    urls, check=release.verify_stage_receipt(plan,"a"*40)
    assert len(urls)==10 and len(set(urls))==10
    assert "/"+("a"*40)+"/" in urls[0]
    assert all(url.endswith(".jpg") for url in urls)
    receipt["no_audio"]=False
    (tmp_path/"receipt.json").write_text(json.dumps(receipt))
    with pytest.raises(release.RealReleaseBlocked):
        release.verify_stage_receipt(plan,"a"*40)


def test_reality_gate_rejects_expired_production_date(monkeypatch):
    monkeypatch.setattr(release, "sast_today", lambda:date(2026,11,14))
    monkeypatch.setenv("AI_GEO_REAL_CAROUSEL_ENABLE","ONE_AUTHORIZED_EP145_REAL_IMAGE_CAROUSEL")
    with pytest.raises(release.RealReleaseBlocked):
        release.run()


def test_double_publish_prevented_by_claim(monkeypatch,tmp_path):
    plan=stage.load_plan(PLAN)
    monkeypatch.setattr(release,"STATE_PATH",tmp_path / "state.json")
    (tmp_path/"state.json").write_text('{"status":"CLAIMED_NO_AUTOMATIC_RETRY"}')
    with pytest.raises(release.RealReleaseBlocked):
        release.claim_once(plan,plan["carousel_caption"]["content"],"a"*40)


def test_release_never_contains_reel_api_path():
    src=Path(release.__file__).read_text(encoding="utf-8")
    assert 'media_type": "REELS"' not in src
    assert "ffmpeg" not in src
    assert "InstagramCarouselPublisher" in src
