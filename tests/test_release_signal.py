import json
from datetime import date

import pytest

from src.release_signal import SCHEMA, validate_signal


def signal(platform="instagram", mode="plan", episode="Ep146", confirmation=""):
    return {
        "schema": SCHEMA,
        "episode": episode,
        "date_sast": "2026-11-14",
        "platform": platform,
        "mode": mode,
        "confirmation": confirmation,
    }


def path(platform="instagram", mode="plan", attempt="01"):
    return f"publisher_signals/launch-ep146-20261114-{platform}-{mode}-{attempt}.json"


@pytest.mark.parametrize("platform", ["instagram", "threads", "instagram-reel", "threads-video", "instagram-story"])
def test_plan_validation(platform):
    req = signal(platform=platform)
    assert validate_signal(path(platform=platform), json.dumps(req), today_sast=date(2026, 11, 14)) == req


@pytest.mark.parametrize("platform", ["instagram", "threads", "instagram-reel", "threads-video", "instagram-story"])
def test_publish_confirmation(platform):
    req = signal(platform, "publish", confirmation=f"PUBLISH_{platform.upper().replace('-', '_')}_EP146_20261114")
    assert validate_signal(path(platform, "publish"), json.dumps(req), today_sast=date(2026, 11, 14)) == req


@pytest.mark.parametrize("mutator", [
    lambda r: r.update(confirmation="PUBLISH_INSTAGRAM_EP145_20261113"),
    lambda r: r.update(confirmation="PUBLISH_THREADS_EP146_20261114"),
    lambda r: r.update(episode="Ep145"),
    lambda r: r.update(date_sast="2026-11-15"),
    lambda r: r.update(platform="threads"),
    lambda r: r.update(mode="plan"),
    lambda r: r.update(unexpected="anything"),
])
def test_tampered_release_rejected(mutator):
    req = signal(mode="publish", confirmation="PUBLISH_INSTAGRAM_EP146_20261114")
    mutator(req)
    with pytest.raises(ValueError):
        validate_signal(path(mode="publish"), json.dumps(req), today_sast=date(2026, 11, 14))


def test_invalid_path_rejected():
    with pytest.raises(ValueError):
        validate_signal("docs/launch-ep146-20261114-instagram-plan-01.json", json.dumps(signal()))


def test_future_date_rejected():
    with pytest.raises(ValueError):
        validate_signal(path(), json.dumps(signal()), today_sast=date(2026, 11, 13))


def test_plan_cannot_carry_publish_confirmation():
    with pytest.raises(ValueError):
        validate_signal(path(), json.dumps(signal(confirmation="PUBLISH_INSTAGRAM_EP146_20261114")), today_sast=date(2026, 11, 14))


def test_video_surface_approval_cannot_be_reused_for_another_surface():
    req = signal("instagram-reel", "publish",
                 confirmation="PUBLISH_INSTAGRAM_REEL_EP146_20261114")
    assert validate_signal(path("instagram-reel", "publish"), json.dumps(req),
                           today_sast=date(2026, 11, 14)) == req
    for surface in ("instagram-story", "threads-video", "instagram"):
        with pytest.raises(ValueError):
            validate_signal(path(surface, "publish"), json.dumps(req),
                            today_sast=date(2026, 11, 14))


def test_unknown_video_surface_is_not_a_release_trigger():
    req = signal("facebook-story", "publish",
                 confirmation="PUBLISH_FACEBOOK_STORY_EP146_20261114")
    with pytest.raises(ValueError):
        validate_signal(path("facebook-story", "publish"), json.dumps(req),
                        today_sast=date(2026, 11, 14))
