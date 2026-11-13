"""Sisyphus-to-publisher final handoff; production completion is NOT permission.

The schema is deliberately distinct from closed editorial Manifest v2 and
EpNNN_QC_Completion.json. No media POST or storage write occurs in this module.
"""
from __future__ import annotations

from datetime import date
from typing import Mapping

from .publisher_archive import Episode, PublisherBlocked

SCHEMA = "ai-geopolitic.publisher.production-handoff.v1"
FINAL_PASS = "PRODUCTION PASSED"
REQUIRED_COMPONENTS = frozenset({
    "rnd", "slide_design", "carousel_10", "carousel_caption",
    "reel_frames_6", "reel_caption", "archive_drive_readback"
})
TARGET = "INSTAGRAM_CAROUSEL_TEST_ONLY"


def verify_final_handoff(episode: Episode, handoff: Mapping,
                         *, production_day: date) -> None:
    """Succeed only for a separately written, final, same-day Sisyphus PASS."""
    if not isinstance(handoff, dict):
        raise PublisherBlocked("Final Sisyphus production handoff is missing.")
    if handoff.get("schema") != SCHEMA:
        raise PublisherBlocked("Final Sisyphus handoff schema is not approved.")
    if handoff.get("status") != FINAL_PASS:
        raise PublisherBlocked("Sisyphus has not emitted PRODUCTION PASSED.")
    if handoff.get("episode_id") != episode.episode_id or handoff.get(
        "production_date_sast"
    ) != episode.day.isoformat() or episode.day != production_day:
        raise PublisherBlocked("Handoff episode/date does not match intended SAST day.")
    if handoff.get("archive_folder_id") != episode.folder_id:
        raise PublisherBlocked("Handoff points at an unexpected archive folder.")
    if handoff.get("publish_target") != TARGET:
        raise PublisherBlocked("Final handoff is not authorized for a TEST ONLY carousel.")
    if handoff.get("carousel_items") != 10 or handoff.get("reel_frames") != 6:
        raise PublisherBlocked("Final handoff lacks the complete 10/6 production set.")
    if handoff.get("unresolved_blockers") != []:
        raise PublisherBlocked("Final production handoff declares unresolved blockers.")
    checks = handoff.get("component_results")
    if not isinstance(checks, dict) or set(checks) != REQUIRED_COMPONENTS or any(
        value != "PASS" for value in checks.values()
    ):
        raise PublisherBlocked("Not all Sisyphus production component gates passed.")
    if handoff.get("author") != "Sisyphus":
        raise PublisherBlocked("Handoff author is not the expected production coordinator.")


def example_handoff(episode: Episode) -> dict:
    """Schema example only. NEVER write a fraudulent PASS file during testing."""
    return {
        "schema": SCHEMA,
        "episode_id": episode.episode_id,
        "production_date_sast": episode.day.isoformat(),
        "archive_folder_id": episode.folder_id,
        "status": "WAITING_FOR_PRODUCTION",  # Sisyphus changes after QC
        "author": "Sisyphus",
        "publish_target": TARGET,
        "carousel_items": 10,
        "reel_frames": 6,
        "unresolved_blockers": ["Production not yet completed"],
        "component_results": {key: "WAITING" for key in sorted(REQUIRED_COMPONENTS)},
    }
