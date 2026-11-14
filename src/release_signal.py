"""GitHub Actions-only, explicit, one-shot bridge for carousel release requests.

The connected GitHub app can create a reviewed launch file but does not expose
workflow_dispatch. A main-branch push of exactly one new request invokes this
script with the short-lived GitHub Actions token. No Meta API is called here.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPOSITORY = "venipublishing-main/ai-geopolitic-automation"
SCHEMA = "ai-geopolitic.publisher.launch-signal.v1"
WORKFLOWS = {
    "instagram": "ai-geopolitic-instagram-carousel.yml",
    "threads": "ai-geopolitic-threads-carousel.yml",
}
SIGNAL_PATTERN = re.compile(
    r"publisher_signals/launch-(ep[1-9][0-9]{0,5})-([0-9]{8})-"
    r"(instagram|threads)-(plan|publish)-([0-9]{2})\.json\Z"
)
EPISODE_PATTERN = re.compile(r"Ep[1-9][0-9]{0,5}\Z")
EXPECTED_KEYS = {"schema", "episode", "date_sast", "platform", "mode", "confirmation"}


def validate_signal(path: str, contents: str, *, today_sast: date | None = None) -> dict[str, str]:
    """Validate exact file identity, request schema, one-time approval, and date."""
    match = SIGNAL_PATTERN.fullmatch(path)
    if not match:
        raise ValueError("Unexpected release signal path")
    try:
        signal = json.loads(contents)
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid release signal JSON") from exc
    if not isinstance(signal, dict) or set(signal) != EXPECTED_KEYS:
        raise ValueError("Release signal keys do not match locked schema")
    if not all(isinstance(value, str) for value in signal.values()):
        raise ValueError("All release signal values must be strings")
    if signal["schema"] != SCHEMA:
        raise ValueError("Unexpected release signal schema")

    episode, day_token, platform, mode, _attempt = match.groups()
    if not EPISODE_PATTERN.fullmatch(signal["episode"]):
        raise ValueError("Invalid episode")
    try:
        production_day = date.fromisoformat(signal["date_sast"])
    except ValueError as exc:
        raise ValueError("Invalid production date") from exc
    if (
        signal["episode"].lower() != episode
        or production_day.strftime("%Y%m%d") != day_token
        or signal["platform"] != platform
        or signal["mode"] != mode
    ):
        raise ValueError("Release signal filename and contents disagree")
    current_day = today_sast or (datetime.now(timezone.utc) + timedelta(hours=2)).date()
    if production_day > current_day:
        raise ValueError("Future production date cannot be dispatched")

    approval = (
        f"PUBLISH_{platform.upper()}_{signal['episode'].upper()}_{day_token}"
        if mode == "publish"
        else ""
    )
    if signal["confirmation"] != approval:
        raise ValueError("Missing or incorrect per-episode publishing authorization")
    return signal


def single_added_signal() -> tuple[str, dict[str, str]]:
    """Reject any multi-file, modified, deleted, or non-release push."""
    changed = subprocess.check_output(
        ["git", "diff-tree", "--no-commit-id", "--name-status", "-r", "HEAD"],
        text=True,
    ).strip().splitlines()
    if len(changed) != 1 or not changed[0].startswith("A\t"):
        raise ValueError("Release trigger requires exactly one newly added signal")
    path = changed[0][2:]
    request = validate_signal(path, Path(path).read_text(encoding="utf-8"))
    return path, request


def api_request(endpoint: str, token: str, *, payload: dict | None = None) -> int:
    url = f"https://api.github.com/repos/{REPOSITORY}/{endpoint}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(
        url,
        data=body,
        method="POST" if payload is not None else "GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=20) as response:
            return response.status
    except HTTPError as exc:
        if payload is None and exc.code == 404:
            return 404
        # Deliberately omit HTTP response bodies and credentials from logs.
        raise RuntimeError(f"GitHub API returned HTTP {exc.code} for {endpoint}") from exc
    except URLError as exc:
        raise RuntimeError("GitHub API request failed; manual reconciliation required") from exc


def run() -> None:
    for key, expected in (
        ("GITHUB_REPOSITORY", REPOSITORY),
        ("GITHUB_REF", "refs/heads/main"),
        ("GITHUB_EVENT_NAME", "push"),
        ("GITHUB_ACTOR", "venipublishing-main"),
    ):
        if os.environ.get(key) != expected:
            raise ValueError(f"GitHub event identity check failed: {key}")
    token = os.environ.get("GH_ACTION_TOKEN")
    if not token:
        raise ValueError("No short-lived Actions token available")
    path, signal = single_added_signal()
    if signal["mode"] == "publish":
        episode_slug = signal["episode"].lower()
        date_slug = signal["date_sast"].replace("-", "")
        receipt = f"publisher_state/{signal['platform']}-{episode_slug}-{date_slug}.json"
        if api_request(f"contents/{receipt}?ref=main", token) != 404:
            raise ValueError("Release claim/receipt already exists; no duplicate dispatch")
    workflow = WORKFLOWS[signal["platform"]]
    payload = {
        "ref": "main",
        "inputs": {
            "mode": signal["mode"],
            "episode": signal["episode"],
            "date_sast": signal["date_sast"],
            "publish_confirmation": signal["confirmation"],
        },
    }
    status = api_request(f"actions/workflows/{workflow}/dispatches", token, payload=payload)
    if status != 204:
        raise RuntimeError(f"Unexpected workflow dispatch status {status}")
    print(f"DISPATCHED {signal['platform']} {signal['mode']} {signal['episode']} "
          f"{signal['date_sast']} via {path}; watch downstream Actions for result.")


if __name__ == "__main__":
    try:
        run()
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
