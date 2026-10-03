"""Opt-in discovery smoke checks; actual inference requires the explicit CLI."""
import os

import pytest

from src.phase_c import load_workers

pytestmark = pytest.mark.skipif(os.environ.get("AI_GEOPOLITIC_PHASE_C_LIVE") != "1",
                                reason="Opt-in real localhost worker discovery; no models launched by normal pytest.")


def test_reviewed_local_workers_are_reachable():
    path = os.environ.get("AI_GEOPOLITIC_PHASE_C_PROFILES")
    assert path, "Set the external reviewed profile path before opting in."
    workers = load_workers(path)
    assert workers
    for worker in workers:
        assert worker.available(), f"{worker.provider_id} runtime discovery did not pass."
