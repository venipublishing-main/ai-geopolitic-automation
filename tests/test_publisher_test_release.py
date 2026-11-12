"""Offline dry-run and idempotency regression for single Ep145 QA test release."""
import copy
import hashlib
import json
from datetime import date

import pytest

from src.publisher_archive import Episode
from src.publisher_handoff import example_handoff
from src import publisher_test_release as release

EP = Episode(145, date(2026,11,13), "Ep145-13November2026",
             "1FAKE_EP145_DRIVE_FOLDER_123456789")
CAPTION = ("A fake editorial headline for automated publishing tests.\n\n"
           "#AIGeopolitic #SouthAfrica #Geopolitics #PoliticalAnalysis #NewsBriefing\n"
           "The event is factual. The interpretation ideological.")


def good_signal():
    handoff=example_handoff(EP)
    handoff["status"]="PRODUCTION PASSED"
    handoff["unresolved_blockers"]=[]
    handoff["component_results"]={k:"PASS" for k in handoff["component_results"]}
    return {
        "schema":"ai-geopolitic.publisher.signal.v1",
        "episode_id":"Ep145","production_date_sast":"2026-11-13",
        "archive_folder_id":EP.folder_id,
        "source":"SISYPHUS_DRIVE_VERIFIED",
        "sisyphus_handoff":handoff,"test_only":True,
        "archived_carousel_caption":CAPTION,
        "caption_sha256":hashlib.sha256(CAPTION.encode()).hexdigest(),
        "previously_published":False,
    }


def test_accepted_signal_produces_test_caption_with_full_archive_copy():
    ep,caption=release.validate_signal(good_signal(),current_day=date(2026,11,13))
    assert ep==EP
    assert caption.endswith(CAPTION)
    assert caption.startswith("TEST ONLY")
    assert len(caption)<=2200


@pytest.mark.parametrize("mutation", [
    ("status","PENDING IAN REVIEW"),
    ("episode_id","Ep144"),
    ("production_date_sast","2026-11-12"),
    ("source","SOME_UNKNOWN_SOURCE"),
    ("test_only",False),
    ("previously_published",True),
    ("caption_sha256","0"*64),
])
def test_reject_signal_changes(mutation):
    key,value=mutation
    s=good_signal()
    if key=="status":
        s["sisyphus_handoff"]["status"]=value
    else:
        s[key]=value
    with pytest.raises(release.ReleaseBlocked):
        release.validate_signal(s,current_day=date(2026,11,13))


def test_reject_other_date_no_fallback():
    with pytest.raises(release.ReleaseBlocked):
        release.validate_signal(good_signal(),current_day=date(2026,11,14))


def test_exactly_ten_pinned_urls_and_allowed_hostname():
    urls=release.image_urls()
    assert len(urls)==len(set(urls))==10
    assert all("37dac6614a6d01ae4691a5af5561735dd3f14ef1" in u for u in urls)
    assert urls[0].endswith("/TEST_Slide01of10.jpg")
    assert urls[-1].endswith("/TEST_Slide10of10.jpg")


def test_claim_written_before_any_meta_call_and_blocks_retry(tmp_path,monkeypatch):
    state=tmp_path/"publisher_state"/"ep145-instagram-test.json"
    calls=[]
    monkeypatch.setattr(release,"STATE_FILE",state)
    monkeypatch.setattr(release,"safe_git",lambda *args:calls.append(args))
    release.claim_once(EP,CAPTION,run_id="123")
    record=json.loads(state.read_text())
    assert record["status"]=="CLAIMED_NO_AUTOMATIC_RETRY"
    assert record["instagram_media_id"] is None
    assert any(x[0]=="push" for x in calls)
    with pytest.raises(release.ReleaseBlocked):
        release.claim_once(EP,CAPTION,run_id="124")


def test_success_requires_full_sequencing_and_metadata(tmp_path,monkeypatch):
    import os
    s=good_signal()
    signal=tmp_path/"signal.json"
    signal.write_text(json.dumps(s))
    calls=[]
    monkeypatch.setattr(release,"sast_today",lambda:date(2026,11,13))
    monkeypatch.setattr(release,"verify_public_images",lambda urls:calls.append("media_checked"))
    monkeypatch.setattr(release,"verified_ig_id",lambda token:"178400001234567890")
    monkeypatch.setattr(release,"inspect_duplicate",lambda tok,ig:calls.append("duplicate_checked"))
    monkeypatch.setattr(release,"claim_once",lambda ep,cap,run_id:calls.append("claimed"))
    monkeypatch.setattr(release,"verify_published_media",lambda tok,media_id:
                       ("PUBLISHED_AI_INFO_VERIFIED","https://www.instagram.com/p/fake/"))
    monkeypatch.setattr(release,"save_receipt",lambda *args:calls.append("receipt"))
    class FakeClient:
        def __init__(self,*args): pass
        def publish(self,urls,caption,allowed_hostname,explicit_external_publish_permission):
            assert explicit_external_publish_permission is True
            assert len(urls)==10
            assert caption.endswith(CAPTION)
            assert allowed_hostname=="raw.githubusercontent.com"
            calls.append("PUBLISHED")
            return "17840123456789001"
    monkeypatch.setattr(release,"InstagramCarouselPublisher",FakeClient)
    monkeypatch.setenv("AI_GEO_IG_ACCESS_TOKEN","FAKE_TEST_TOKEN")
    monkeypatch.setenv("AI_GEO_ONE_TIME_TEST_ENABLE","EXACTLY_ONE_EP145_QA_CAROUSEL")
    out=release.run(signal)
    assert out["status"]=="PUBLISHED_AI_INFO_VERIFIED" and out["posted"]
    assert calls==["media_checked","duplicate_checked","claimed","PUBLISHED","receipt"]


def test_no_enable_switch_means_zero_network(monkeypatch,tmp_path):
    monkeypatch.delenv("AI_GEO_ONE_TIME_TEST_ENABLE",raising=False)
    with pytest.raises(release.ReleaseBlocked):
        release.run(tmp_path/"absent.json")


def test_readonly_release_requires_actual_pass_not_completeness(monkeypatch,tmp_path):
    s=good_signal()
    s["sisyphus_handoff"]["status"]="PRODUCTION COMPLETE — PENDING IAN REVIEW"
    f=tmp_path/"signal.json"
    f.write_text(json.dumps(s))
    monkeypatch.setattr(release,"sast_today",lambda:date(2026,11,13))
    monkeypatch.setenv("AI_GEO_ONE_TIME_TEST_ENABLE","EXACTLY_ONE_EP145_QA_CAROUSEL")
    monkeypatch.setattr(release,"verify_public_images",lambda urls:
                        pytest.fail("SHOULD NOT TOUCH PUBLIC MEDIA BEFORE PASS"))
    with pytest.raises(release.ReleaseBlocked):
        release.run(f)
