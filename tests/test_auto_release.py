import json
from datetime import date, datetime, timezone

import pytest

from src import auto_release as a


def test_policy_locked_and_autonomous():
    raw = json.loads(a.CONFIG_PATH.read_text())
    assert a.validate_policy(raw)["enabled"] is True
    assert raw["start_date_sast"] == "2026-11-15"
    assert raw["platforms_in_order"] == ["instagram", "threads"]


@pytest.mark.parametrize("change", [
    {"enabled": "true"},
    {"platforms_in_order": ["threads", "instagram"]},
    {"start_date_sast": "15-11-2026"},
    {"schema": "unrecognized"},
    {"unlocked": True},
])
def test_invalid_policy_rejected(change):
    raw = json.loads(a.CONFIG_PATH.read_text())
    raw.update(change)
    with pytest.raises(a.AutoBlocked):
        a.validate_policy(raw)


def test_sast_clock():
    instant = datetime(2026, 11, 14, 22, 30, tzinfo=timezone.utc)
    assert a.current_sast_date(instant) == date(2026, 11, 15)


def test_exact_date_archive_no_latest_fallback():
    entries = [
        {"Name": "Ep145-13November2026", "IsDir": True},
        {"Name": "Ep146-14November2026", "IsDir": True},
        {"Name": "Ep147-15November2026", "IsDir": False},
    ]
    assert a.pick_exact_today_folder(entries, date(2026, 11, 15)) is None
    entries[2]["IsDir"] = True
    assert a.pick_exact_today_folder(entries, date(2026, 11, 15)) == "Ep147"


def test_ambiguous_today_archives_fail_closed():
    entries = [
        {"Name": "Ep147-15November2026", "IsDir": True},
        {"Name": "Ep148-15November2026", "IsDir": True},
    ]
    with pytest.raises(a.AutoBlocked):
        a.pick_exact_today_folder(entries, date(2026, 11, 15))


def test_invalid_or_wrong_day_folder_not_selected():
    entries = [
        {"Name": "Ep146-14November2026", "IsDir": True},
        {"Name": "EpA-15November2026", "IsDir": True},
        {"Name": "Ep147-15November2026.tmp", "IsDir": True},
    ]
    assert a.pick_exact_today_folder(entries, date(2026, 11, 15)) is None


@pytest.mark.parametrize("phase", [
    "INSTAGRAM_CLAIMED_BEFORE_DISPATCH", "INSTAGRAM_DISPATCHED",
    "THREADS_CLAIMED_BEFORE_DISPATCH", "BOTH_DISPATCHED",
])
def test_day_state_phases_validate(phase):
    day = date(2026, 11, 15)
    record = a.new_state("Ep147", day, phase)
    assert a.validate_day_state(record, day) == "Ep147"


def test_day_state_identity_mismatch_rejected():
    state = a.new_state("Ep147", date(2026, 11, 15), "BOTH_DISPATCHED")
    with pytest.raises(a.AutoBlocked):
        a.validate_day_state(state, date(2026, 11, 16))


def test_no_event_can_invent_live_authority(monkeypatch):
    for key, val in {
        "GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": a.REPO,
        "GITHUB_REF": "refs/heads/main", "GITHUB_EVENT_NAME": "push",
    }.items():
        monkeypatch.setenv(key, val)
    with pytest.raises(a.AutoBlocked):
        a.verify_event(probe=False)
    assert a.verify_event(probe=True) is None


def test_untrusted_workflow_run_rejected(monkeypatch, tmp_path):
    for key, val in {
        "GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": a.REPO,
        "GITHUB_REF": "refs/heads/main", "GITHUB_EVENT_NAME": "workflow_run",
    }.items():
        monkeypatch.setenv(key, val)
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"workflow_run": {
        "event": "pull_request", "conclusion": "success", "head_branch": "main",
        "head_repository": {"full_name": a.REPO},
        "name": "AI Geopolitic Instagram — ten-image carousel (human gate)",
    }}))
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    with pytest.raises(a.AutoBlocked):
        a.verify_event(probe=False)


def test_no_dispatch_without_ready_handoff(monkeypatch):
    monkeypatch.setattr(a, "detect_ready", lambda d: None)
    monkeypatch.setattr(a, "dispatch", lambda *args, **kw: pytest.fail("MUST NOT DISPATCH"))
    a.process(date(2026, 11, 15), "test-token", probe=False)


def test_probe_never_writes_or_dispatches(monkeypatch):
    day = date(2026, 11, 14)
    monkeypatch.setattr(a, "detect_ready", lambda d: {"episode": "Ep146"})
    monkeypatch.setattr(a, "get_state", lambda token, d: None)
    monkeypatch.setattr(a, "read_receipt", lambda platform, ep, d, token: None)
    monkeypatch.setattr(a, "put_repo_json", lambda *args, **kw: pytest.fail("MUST NOT WRITE"))
    monkeypatch.setattr(a, "dispatch", lambda *args, **kw: pytest.fail("MUST NOT DISPATCH"))
    a.process(day, "test-token", probe=True)


def test_ig_dispatch_first_and_threads_waits(monkeypatch):
    day = date(2026, 11, 15)
    marker = []
    launches = []
    monkeypatch.setattr(a, "detect_ready", lambda d: {"episode": "Ep147"})
    monkeypatch.setattr(a, "get_state", lambda token, d: None)
    monkeypatch.setattr(a, "read_receipt", lambda platform, ep, d, token: None)
    monkeypatch.setattr(a, "put_repo_json", lambda path, token, record, sha=None: marker.append(record["phase"]) or "a" * 40)
    monkeypatch.setattr(a, "dispatch", lambda platform, episode, day, token: launches.append(platform))
    a.process(day, "test-token", probe=False)
    assert launches == ["instagram"]
    assert marker == ["INSTAGRAM_CLAIMED_BEFORE_DISPATCH", "INSTAGRAM_DISPATCHED"]


def test_threads_only_after_ig_receipt_verified(monkeypatch):
    day = date(2026, 11, 15)
    marker = []
    launches = []
    monkeypatch.setattr(a, "detect_ready", lambda d: {"episode": "Ep147"})
    monkeypatch.setattr(a, "get_state", lambda token, d: (a.new_state("Ep147", day, "INSTAGRAM_DISPATCHED"), "a" * 40))
    monkeypatch.setattr(a, "read_receipt", lambda platform, ep, d, token:
                        {"status": a.INSTAGRAM_SUCCESS} if platform == "instagram" else None)
    monkeypatch.setattr(a, "put_repo_json", lambda path, token, record, sha=None: marker.append(record["phase"]) or "a" * 40)
    monkeypatch.setattr(a, "dispatch", lambda platform, episode, day, token: launches.append(platform))
    a.process(day, "test-token", probe=False)
    assert launches == ["threads"]
    assert marker == ["THREADS_CLAIMED_BEFORE_DISPATCH", "BOTH_DISPATCHED"]


def test_existing_receipts_never_dispatch(monkeypatch):
    day = date(2026, 11, 14)
    monkeypatch.setattr(a, "detect_ready", lambda d: {"episode": "Ep146"})
    monkeypatch.setattr(a, "get_state", lambda token, d: None)
    monkeypatch.setattr(a, "read_receipt", lambda p, e, d, t:
                        {"status": a.INSTAGRAM_SUCCESS if p == "instagram" else a.THREADS_SUCCESS})
    monkeypatch.setattr(a, "dispatch", lambda *args: pytest.fail("DUPLICATE DISPATCH"))
    monkeypatch.setattr(a, "put_repo_json", lambda *args, **kw: pytest.fail("DUPLICATE CLAIM"))
    a.process(day, "test-token", probe=False)


def test_unverified_ig_blocks_threads(monkeypatch):
    day = date(2026, 11, 15)
    monkeypatch.setattr(a, "detect_ready", lambda d: {"episode": "Ep147"})
    monkeypatch.setattr(a, "get_state", lambda token, d: None)
    monkeypatch.setattr(a, "read_receipt", lambda p, e, d, t:
                        {"status": "CLAIMED_NO_AUTOMATIC_RETRY"} if p == "instagram" else None)
    monkeypatch.setattr(a, "dispatch", lambda *args: pytest.fail("MUST NOT DISPATCH"))
    monkeypatch.setattr(a, "put_repo_json", lambda *args, **kw: pytest.fail("MUST NOT CLAIM"))
    a.process(day, "test-token", probe=False)


def test_precheck_respects_start_date_without_api_access(monkeypatch):
    monkeypatch.setattr(a, "get_state", lambda *args: pytest.fail("EARLY API ACCESS"))
    assert a.should_process_day("test-token", date(2026, 11, 14), probe=False) is False


def test_precheck_stops_after_both_dispatches(monkeypatch):
    day = date(2026, 11, 15)
    monkeypatch.setattr(a, "get_state", lambda token, d:
                        (a.new_state("Ep147", day, "BOTH_DISPATCHED"), "a" * 40))
    assert a.should_process_day("test-token", day, probe=False) is False


def test_precheck_waits_for_exact_ig_verification(monkeypatch):
    day = date(2026, 11, 15)
    monkeypatch.setattr(a, "get_state", lambda token, d:
                        (a.new_state("Ep147", day, "INSTAGRAM_DISPATCHED"), "a" * 40))
    monkeypatch.setattr(a, "get_repo_json", lambda path, token:
                        ({"status": "CLAIMED_NO_AUTOMATIC_RETRY"}, "b" * 40))
    assert a.should_process_day("test-token", day, probe=False) is False
    monkeypatch.setattr(a, "get_repo_json", lambda path, token:
                        ({"status": a.INSTAGRAM_SUCCESS}, "b" * 40))
    assert a.should_process_day("test-token", day, probe=False) is True


def test_no_automatic_dispatch_after_ambiguous_day_claim(monkeypatch):
    day = date(2026, 11, 15)
    monkeypatch.setattr(a, "detect_ready", lambda d: {"episode": "Ep147"})
    monkeypatch.setattr(a, "get_state", lambda token, d:
                        (a.new_state("Ep147", day, "INSTAGRAM_CLAIMED_BEFORE_DISPATCH"), "a" * 40))
    monkeypatch.setattr(a, "read_receipt", lambda platform, ep, d, token: None)
    monkeypatch.setattr(a, "dispatch", lambda *args: pytest.fail("DUPLICATE DISPATCH"))
    monkeypatch.setattr(a, "put_repo_json", lambda *args, **kw: pytest.fail("DUPLICATE CLAIM"))
    a.process(day, "test-token", probe=False)
