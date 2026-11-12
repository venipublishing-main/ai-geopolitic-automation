"""Offline release-handshake tests. No Drive or social API access."""
import copy
from datetime import date

import pytest

from src.publisher_archive import Episode, PublisherBlocked
from src.publisher_handoff import example_handoff, verify_final_handoff

EP = Episode(145, date(2026, 11, 13), "Ep145-13November2026",
             "1TEST_EP145_ARCHIVE_FOLDER_ID_ABCD")


def passed():
    state = example_handoff(EP)
    state["status"] = "PRODUCTION PASSED"
    state["component_results"] = {key: "PASS" for key in state["component_results"]}
    state["unresolved_blockers"] = []
    return state


def test_complete_sisyphus_production_pass_is_accepted_only_for_the_day():
    verify_final_handoff(EP, passed(), production_day=EP.day)


@pytest.mark.parametrize("field,value", [
    ("status", "PRODUCTION COMPLETE — PENDING IAN REVIEW"),
    ("status", "PRODUCTION COMPLETE"),
    ("status", "BUILD_READY"),
    ("publish_target", "INSTAGRAM_CAROUSEL"),
    ("archive_folder_id", "DIFFERENT_FOLDER"),
    ("production_date_sast", "2026-11-12"),
    ("episode_id", "Ep144"),
    ("carousel_items", 9),
    ("reel_frames", 0),
    ("author", "Not Sisyphus"),
])
def test_unapproved_handoff_never_releases(field, value):
    state = passed()
    state[field] = value
    with pytest.raises(PublisherBlocked):
        verify_final_handoff(EP, state, production_day=EP.day)


def test_missing_handoff_blocks():
    with pytest.raises(PublisherBlocked):
        verify_final_handoff(EP, None, production_day=EP.day)


def test_component_blocker_prevents_release():
    state = passed()
    state["component_results"]["carousel_caption"] = "FAIL"
    with pytest.raises(PublisherBlocked):
        verify_final_handoff(EP, state, production_day=EP.day)
    state = passed()
    state["unresolved_blockers"] = ["bad image"]
    with pytest.raises(PublisherBlocked):
        verify_final_handoff(EP, state, production_day=EP.day)


def test_handoff_is_not_reusable_the_next_day():
    with pytest.raises(PublisherBlocked):
        verify_final_handoff(EP, passed(), production_day=date(2026, 11, 14))


def test_example_is_explicitly_waiting_not_passed():
    with pytest.raises(PublisherBlocked):
        verify_final_handoff(EP, example_handoff(EP), production_day=EP.day)
