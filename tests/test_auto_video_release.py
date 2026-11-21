import json
from datetime import date

import pytest

from src import auto_release as car
from src import auto_video_release as v
from src.video_release import approval_for as video_approval


DAY = date(2026, 11, 22)
EP = "Ep154"
TOKEN = "test-only-long-token-without-credentials"


def test_policy_is_exact_and_starts_after_existing_day():
    raw = json.loads(v.CONFIG_PATH.read_text())
    assert v.validate_policy(raw)["enabled"] is True
    assert raw["start_date_sast"] == "2026-11-22"
    assert raw["require_both_carousels"] is True
    assert raw["surfaces_in_order"] == list(v.SURFACES)
    assert len(v.SURFACES) == 3


@pytest.mark.parametrize("mod", [
    {"schema": "wrong"},
    {"enabled": "true"},
    {"start_date_sast": "22-11-2026"},
    {"surfaces_in_order": ["instagram-reel", "instagram-story"]},
    {"surfaces_in_order": list(reversed(v.SURFACES))},
    {"require_both_carousels": False},
    {"unexpected": True},
])
def test_invalid_policy_rejected(mod):
    raw = json.loads(v.CONFIG_PATH.read_text())
    raw.update(mod)
    with pytest.raises(car.AutoBlocked):
        v.validate_policy(raw)


def test_all_video_approvals_match_existing_publishers():
    for surface in v.SURFACES:
        assert v.approval_for(surface, EP, DAY) == video_approval(
            surface, EP, DAY.isoformat())
    assert v.approval_for("threads", EP, DAY) == "PUBLISH_THREADS_EP154_20261122"
    with pytest.raises(car.AutoBlocked):
        v.approval_for("unknown", EP, DAY)


def test_gate_demands_auto_claim_and_both_identity_verified_receipts(monkeypatch):
    monkeypatch.setattr(car, "get_state", lambda *_: None)
    assert v.verified_carousel_episode(TOKEN, DAY) is None
    monkeypatch.setattr(car, "get_state", lambda *_: ({"episode": EP}, "a" * 40))
    records = {
        "instagram": {"schema": v.CAROUSEL_RECEIPTS["instagram"][0],
                      "status": car.INSTAGRAM_SUCCESS, "episode": EP,
                      "date_sast": DAY.isoformat(), "instagram_account": "ai_geopolitic"},
        "threads": {"schema": v.CAROUSEL_RECEIPTS["threads"][0],
                    "status": car.THREADS_SUCCESS, "episode": EP,
                    "date_sast": DAY.isoformat(), "threads_account": "ai_geopolitic"},
    }
    def lookup(path, token):
        assert token == TOKEN
        for surface in records:
            if path == car.receipt_path(surface, EP, DAY):
                return (records[surface], "x" * 40) if records[surface] else None
        raise AssertionError(path)
    monkeypatch.setattr(car, "get_repo_json", lookup)
    assert v.verified_carousel_episode(TOKEN, DAY) == EP
    records["threads"] = None
    assert v.verified_carousel_episode(TOKEN, DAY) is None
    records["threads"] = {"schema": v.CAROUSEL_RECEIPTS["threads"][0],
                          "status": "CLAIMED_NO_AUTOMATIC_RETRY", "episode": EP,
                          "date_sast": DAY.isoformat(), "threads_account": "ai_geopolitic"}
    assert v.verified_carousel_episode(TOKEN, DAY) is None
    records["threads"]["status"] = car.THREADS_SUCCESS
    records["threads"]["episode"] = "Ep153"
    with pytest.raises(car.AutoBlocked, match="identity"):
        v.verified_carousel_episode(TOKEN, DAY)


def test_surface_receipt_requires_identity_and_exact_surface(monkeypatch):
    receipt = {
        "schema": "ai-geopolitic.publisher.video-publication-receipt.v1",
        "episode": EP, "date_sast": DAY.isoformat(),
        "surface": "threads-video", "status": v.SUCCESS["threads-video"],
    }
    monkeypatch.setattr(car, "get_repo_json", lambda *_: (receipt, "x" * 40))
    assert v.read_video_receipt(TOKEN, "threads-video", EP, DAY) == receipt
    receipt["episode"] = "Ep153"
    with pytest.raises(car.AutoBlocked, match="identity"):
        v.read_video_receipt(TOKEN, "threads-video", EP, DAY)


def test_state_identity_and_phase_are_strict(monkeypatch):
    rec = {"schema": v.STATE_SCHEMA, "date_sast": DAY.isoformat(),
           "episode": EP, "phase": "INSTAGRAM_REEL_DISPATCHED"}
    monkeypatch.setattr(car, "get_repo_json", lambda *_: (rec, "x" * 40))
    assert v.get_video_state(TOKEN, DAY, EP)[0] == rec
    rec["phase"] = "INVALID"
    with pytest.raises(car.AutoBlocked):
        v.get_video_state(TOKEN, DAY, EP)
    rec["phase"] = "INSTAGRAM_REEL_DISPATCHED"
    with pytest.raises(car.AutoBlocked):
        v.get_video_state(TOKEN, DAY, "Ep153")


def test_before_start_date_never_contacts_external_api(monkeypatch):
    monkeypatch.setattr(v, "verified_carousel_episode", lambda *_:
                        pytest.fail("MUST NOT CONTACT CAROUSEL"))
    assert v.should_process_day(TOKEN, date(2026, 11, 21), probe=False) is False


def test_process_waits_for_both_carousels(monkeypatch):
    monkeypatch.setattr(v, "verified_carousel_episode", lambda *_: None)
    monkeypatch.setattr(car, "detect_ready", lambda *_:
                        pytest.fail("MUST NOT READ DRIVE"))
    v.process(TOKEN, DAY, probe=False)


def test_probe_checks_reel_but_cannot_write_or_post(monkeypatch):
    monkeypatch.setattr(v, "verified_carousel_episode", lambda *_: None)
    monkeypatch.setattr(car, "detect_ready", lambda *_: {"episode": EP})
    calls = []
    monkeypatch.setattr(v, "detect_video_ready", lambda *args: calls.append(args))
    monkeypatch.setattr(v, "get_video_state", lambda *_: None)
    monkeypatch.setattr(v, "read_video_receipt", lambda *_: None)
    monkeypatch.setattr(car, "put_repo_json", lambda *a, **k:
                        pytest.fail("NO CLAIMS ALLOWED ON PROBE"))
    monkeypatch.setattr(v, "dispatch", lambda *a:
                        pytest.fail("NO DISPATCH ALLOWED ON PROBE"))
    v.process(TOKEN, DAY, probe=True)
    assert calls == [(EP, DAY)]


def test_exact_date_and_episode_mismatch_blocks_all_writes(monkeypatch):
    monkeypatch.setattr(v, "verified_carousel_episode", lambda *_: EP)
    monkeypatch.setattr(car, "detect_ready", lambda *_: {"episode": "Ep155"})
    monkeypatch.setattr(car, "put_repo_json", lambda *a, **k:
                        pytest.fail("NO CLAIM ALLOWED"))
    with pytest.raises(car.AutoBlocked, match="differs"):
        v.process(TOKEN, DAY, probe=False)


def setup_sequence(monkeypatch):
    record = {}
    receipts = {}
    writes = []
    dispatches = []
    monkeypatch.setattr(v, "verified_carousel_episode", lambda *_: EP)
    monkeypatch.setattr(car, "detect_ready", lambda *_: {"episode": EP})
    monkeypatch.setattr(v, "detect_video_ready", lambda *args: None)
    def get_state(token, day, episode):
        assert (token, day, episode) == (TOKEN, DAY, EP)
        return (dict(record), "a" * 40) if record else None
    monkeypatch.setattr(v, "get_video_state", get_state)
    monkeypatch.setattr(v, "read_video_receipt", lambda _, s, ep, d: receipts.get(s))
    def save(path, token, value, sha=None):
        assert path == v.state_path(DAY) and token == TOKEN
        record.clear()
        record.update(value)
        writes.append((value["phase"], sha))
        return "a" * 40
    monkeypatch.setattr(car, "put_repo_json", save)
    monkeypatch.setattr(v, "dispatch", lambda s, e, d, t:
                        dispatches.append((s, e, d, t)))
    return record, receipts, writes, dispatches


def test_sequential_at_most_once_three_video_surfaces(monkeypatch):
    state, receipts, writes, dispatched = setup_sequence(monkeypatch)
    v.process(TOKEN, DAY, probe=False)
    assert [x[0] for x in dispatched] == ["instagram-reel"]
    assert writes[:2] == [
        ("INSTAGRAM_REEL_CLAIMED_BEFORE_DISPATCH", None),
        ("INSTAGRAM_REEL_DISPATCHED", "a" * 40),
    ]
    assert v.should_process_day(TOKEN, DAY, probe=False) is False
    v.process(TOKEN, DAY, probe=False)
    assert len(dispatched) == 1  # queued job or uncertain claim, never retry

    receipts["instagram-reel"] = {"status": v.SUCCESS["instagram-reel"]}
    v.process(TOKEN, DAY, probe=False)
    assert [x[0] for x in dispatched] == ["instagram-reel", "threads-video"]
    assert state["phase"] == "THREADS_VIDEO_DISPATCHED"

    receipts["threads-video"] = {"status": v.SUCCESS["threads-video"]}
    v.process(TOKEN, DAY, probe=False)
    assert [x[0] for x in dispatched] == list(v.SURFACES)
    assert state["phase"] == "INSTAGRAM_STORY_DISPATCHED"

    receipts["instagram-story"] = {"status": v.SUCCESS["instagram-story"]}
    v.process(TOKEN, DAY, probe=False)
    assert state["phase"] == "ALL_VIDEOS_VERIFIED"
    assert v.should_process_day(TOKEN, DAY, probe=False) is False
    assert len(dispatched) == 3


def test_failed_or_ambiguous_video_claim_never_dispatches_next(monkeypatch):
    state, receipts, writes, launched = setup_sequence(monkeypatch)
    v.process(TOKEN, DAY, probe=False)
    receipts["instagram-reel"] = {"status": "CLAIMED_NO_AUTOMATIC_RETRY"}
    v.process(TOKEN, DAY, probe=False)
    assert [x[0] for x in launched] == ["instagram-reel"]
    assert len(writes) == 2


def test_claim_is_durable_before_any_dispatch_and_stays_if_api_fails(monkeypatch):
    state, receipts, writes, launched = setup_sequence(monkeypatch)
    def uncertain(surface, episode, day, token):
        assert state["phase"] == "INSTAGRAM_REEL_CLAIMED_BEFORE_DISPATCH"
        raise car.AutoBlocked("dispatch outcome uncertain")
    monkeypatch.setattr(v, "dispatch", uncertain)
    with pytest.raises(car.AutoBlocked):
        v.process(TOKEN, DAY, probe=False)
    assert len(writes) == 1
    assert state["phase"] == "INSTAGRAM_REEL_CLAIMED_BEFORE_DISPATCH"
    assert v.should_process_day(TOKEN, DAY, probe=False) is False


def test_manually_successful_video_receipt_skips_duplicate(monkeypatch):
    state, receipts, writes, launched = setup_sequence(monkeypatch)
    receipts["instagram-reel"] = {"status": v.SUCCESS["instagram-reel"]}
    v.process(TOKEN, DAY, probe=False)
    assert [x[0] for x in launched] == ["threads-video"]


def test_exact_dispatch_confirmation_and_workflow(monkeypatch):
    seen = []
    monkeypatch.setattr(car, "endpoint_request", lambda token, path, **kw:
                        seen.append((path, kw)) or (204, None))
    v.dispatch("instagram-reel", EP, DAY, TOKEN)
    assert seen[0][0].endswith("/ai-geopolitic-instagram-reel.yml/dispatches")
    assert seen[0][1]["payload"]["inputs"] == {
        "mode": "publish", "episode": EP, "date_sast": DAY.isoformat(),
        "publish_confirmation": "PUBLISH_INSTAGRAM_REEL_EP154_20261122",
    }


def set_trusted_env(monkeypatch, workflow, event="workflow_dispatch"):
    for key, value in {
        "GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": car.REPO,
        "GITHUB_REF": "refs/heads/main", "GITHUB_EVENT_NAME": event,
        "GITHUB_WORKFLOW": workflow, "MODE": "publish",
        "EPISODE": EP, "DATE_SAST": DAY.isoformat(),
        "APPROVAL": v.approval_for(v.SOURCE_WORKFLOWS[workflow], EP, DAY),
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(car, "current_sast_date", lambda: DAY)


@pytest.mark.parametrize("name", list(v.SOURCE_WORKFLOWS))
def test_only_exact_successful_main_workflow_may_handoff(monkeypatch, name):
    set_trusted_env(monkeypatch, name)
    v.verify_event(probe=False, handoff=True, episode=EP, day=DAY)
    monkeypatch.setenv("MODE", "plan")
    with pytest.raises(car.AutoBlocked):
        v.verify_event(probe=False, handoff=True, episode=EP, day=DAY)
    monkeypatch.setenv("MODE", "publish")
    monkeypatch.setenv("APPROVAL", "FAKE")
    with pytest.raises(car.AutoBlocked):
        v.verify_event(probe=False, handoff=True, episode=EP, day=DAY)


def test_other_events_cannot_claim_live_video_authority(monkeypatch, tmp_path):
    set_trusted_env(monkeypatch, next(iter(v.SOURCE_WORKFLOWS)), event="push")
    v.verify_event(probe=True)
    with pytest.raises(car.AutoBlocked):
        v.verify_event(probe=False)
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"workflow_run": {
        "event": "pull_request", "conclusion": "success", "head_branch": "main",
        "head_repository": {"full_name": car.REPO},
        "name": next(iter(v.SOURCE_WORKFLOWS)),
    }}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_run")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    with pytest.raises(car.AutoBlocked):
        v.verify_event(probe=False)
    raw = json.loads(event.read_text())
    raw["workflow_run"]["event"] = "workflow_dispatch"
    event.write_text(json.dumps(raw))
    v.verify_event(probe=False)


def test_handoff_before_start_never_reads_drive_or_dispatches(monkeypatch):
    set_trusted_env(monkeypatch, next(iter(v.SOURCE_WORKFLOWS)))
    monkeypatch.setattr(car, "current_sast_date", lambda: DAY)
    monkeypatch.setattr(v, "should_process_day", lambda token, day, probe: False)
    monkeypatch.setattr(v, "process", lambda *a, **k: pytest.fail("MUST NOT PROCESS"))
    monkeypatch.setenv("GH_ACTION_TOKEN", TOKEN)
    assert v.main(["handoff", "--episode", EP, "--date-sast", DAY.isoformat()]) == 0
