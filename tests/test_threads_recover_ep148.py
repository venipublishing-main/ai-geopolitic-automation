"""Offline-only tests for the one-shot Threads Ep148 recovery guard."""
import json

import pytest

from src import threads_recover_ep148 as rec
from src.threads_media import ThreadsBlocked


def incident_claim():
    return {
        "episode": rec.EPISODE, "date_sast": rec.DAY,
        "status": "CLAIMED_NO_AUTOMATIC_RETRY",
        "github_run_id": rec.ORIGINAL_RUN,
        "threads_account": rec.EXPECTED_ACCOUNT,
        "threads_user_id": rec.EXPECTED_USER_ID,
        "carousel_items": 10,
        "public_media_commit": "f" * 40,
        "caption_sha256": "a" * 64,
    }


def recovery_signal():
    return {
        "schema": "ai-geopolitic.threads.manual-recovery.v1",
        "episode": rec.EPISODE, "date_sast": rec.DAY,
        "original_failed_run_id": rec.ORIGINAL_RUN,
        "read_only_reconciliation_run_id": rec.READ_ONLY_RUN,
        "confirmation": rec.EXPECTED_APPROVAL,
    }


def test_recovery_auth_is_exact_and_only_in_github_actions(monkeypatch):
    original, signal = incident_claim(), recovery_signal()
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert rec.validate_recovery_inputs(original, signal, run_id="987") == "f" * 40
    signal["confirmation"] = "PUBLISH_THREADS_EP148_20261116"
    with pytest.raises(ThreadsBlocked, match="authorization"):
        rec.validate_recovery_inputs(original, signal, run_id="987")
    signal = recovery_signal()
    original["status"] = "PUBLISHED_VERIFIED"
    with pytest.raises(ThreadsBlocked, match="unresolved incident"):
        rec.validate_recovery_inputs(original, signal, run_id="987")
    monkeypatch.delenv("GITHUB_ACTIONS")
    with pytest.raises(ThreadsBlocked):
        rec.validate_recovery_inputs(incident_claim(), signal, run_id="987")


def test_one_shot_claim_precedes_any_meta_post(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_RUN_ID", "123456")
    monkeypatch.setenv("AI_GEO_THREADS_ACCESS_TOKEN", "t" * 20)
    original_state = rec.state_path(rec.EPISODE, rec.DAY)
    original_state.parent.mkdir(parents=True)
    original_state.write_text(json.dumps(incident_claim()))
    rec.SIGNAL.parent.mkdir(parents=True)
    rec.SIGNAL.write_text(json.dumps(recovery_signal()))
    events = []

    def fake_git(*args):
        return "main" if args[:2] == ("branch", "--show-current") else ""

    def fake_save(path, record):
        events.append("record:" + record["status"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record))

    class FakeGraph:
        def __init__(self, token):
            assert token == "t" * 20

        def check_identity_and_duplicate(self, caption):
            events.append("read_only_duplicate_check")
            return rec.EXPECTED_USER_ID, rec.EXPECTED_ACCOUNT

        def publish_carousel(self, caption, urls):
            events.append("META_POST")
            return {
                "threads_media_id": "123456789",
                "threads_permalink": "https://www.threads.com/@ai_geopolitic/post/abc",
                "caption_verification": "EXACT", "carousel_items_verified": 10,
            }

    monkeypatch.setattr(rec, "_git", fake_git)
    monkeypatch.setattr(rec, "save_state", fake_save)
    monkeypatch.setattr(rec, "restore_immutable_stage", lambda *args: None)
    monkeypatch.setattr(rec, "check_stage", lambda *args: (
        {"caption_sha256": "a" * 64}, "approved caption", ["https://public.test/1.jpg"]))
    monkeypatch.setattr(rec, "verify_public_images", lambda *args: None)
    monkeypatch.setattr(rec, "DiagnosticGraph", FakeGraph)
    outcome = rec.recover()
    assert outcome["status"] == "PUBLISHED_VERIFIED_BY_ONE_SHOT_RECOVERY"
    assert events == [
        "read_only_duplicate_check", "record:RECOVERY_CLAIMED_NO_REPEAT",
        "META_POST", "record:PUBLISHED_VERIFIED",
        "record:RECOVERY_PUBLISHED_VERIFIED",
    ]
    with pytest.raises(ThreadsBlocked, match="already been claimed"):
        rec.recover()
