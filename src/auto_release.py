"""Standing-authority daily carousel dispatcher; no Meta writes in this module.

Only a scheduled or verified Instagram-completed GitHub Actions event may
dispatch, after independent Drive QC and Sisyphus PRODUCTION PASSED checks.
An irreversible day-level GitHub marker is committed *before* each dispatch.
No automatic retry is permitted after an ambiguous dispatch or Meta claim.
"""

from __future__ import annotations

import argparse
import base64
import calendar
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

REPO = "venipublishing-main/ai-geopolitic-automation"
CONFIG_PATH = Path("publisher_config/auto_release.json")
POLICY_SCHEMA = "ai-geopolitic.publisher.automatic-release-policy.v1"
STATE_SCHEMA = "ai-geopolitic.publisher.automatic-dispatch-day.v1"
WORKFLOWS = {
    "instagram": "ai-geopolitic-instagram-carousel.yml",
    "threads": "ai-geopolitic-threads-carousel.yml",
}
INSTAGRAM_SUCCESS = "PUBLISHED_AI_INFO_VERIFIED"
THREADS_SUCCESS = "PUBLISHED_VERIFIED"
PHASES = {
    "INSTAGRAM_CLAIMED_BEFORE_DISPATCH", "INSTAGRAM_DISPATCHED",
    "THREADS_CLAIMED_BEFORE_DISPATCH", "BOTH_DISPATCHED",
}
EP_RE = re.compile(r"Ep[1-9][0-9]{0,5}\Z")
SAST = ZoneInfo("Africa/Johannesburg")


class AutoBlocked(ValueError):
    """Fail closed without accidental publication."""


def current_sast_date(now: datetime | None = None) -> date:
    return (now or datetime.now(SAST)).astimezone(SAST).date()


def validate_policy(raw: dict) -> dict:
    if (not isinstance(raw, dict)
            or set(raw) != {"schema", "enabled", "start_date_sast", "platforms_in_order"}
            or raw["schema"] != POLICY_SCHEMA
            or type(raw["enabled"]) is not bool
            or raw["platforms_in_order"] != ["instagram", "threads"]):
        raise AutoBlocked("Automatic publication policy has invalid locked fields")
    try:
        if (not isinstance(raw["start_date_sast"], str)
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw["start_date_sast"])):
            raise ValueError
        date.fromisoformat(raw["start_date_sast"])
    except ValueError as exc:
        raise AutoBlocked("Automatic release start date is invalid") from exc
    return raw


def load_policy() -> dict:
    return validate_policy(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))


def pick_exact_today_folder(entries: list[dict], day: date) -> str | None:
    """Only the sole, exact-date archive may become a publish candidate."""
    if not isinstance(entries, list):
        raise AutoBlocked("Archive parent listing must be a list")
    suffix = f"-{day.day}{calendar.month_name[day.month]}{day.year}"
    candidates = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise AutoBlocked("Malformed archive listing entry")
        name = entry.get("Name", "")
        if (entry.get("IsDir") is True and isinstance(name, str)
                and name.endswith(suffix) and EP_RE.fullmatch(name[:-len(suffix)])):
            candidates.append(name[:-len(suffix)])
    if not candidates:
        return None
    if len(candidates) != 1:
        raise AutoBlocked("Multiple episode archives have today's date; no automatic choice")
    return candidates[0]


def detect_ready(day: date) -> dict | None:
    # Import only after rclone and Pillow have been installed in Actions.
    from src.threads_media import ARCHIVE_PARENT_ID, ThreadsBlocked, _entries, read_approved_archive

    episode = pick_exact_today_folder(_entries(ARCHIVE_PARENT_ID), day)
    if episode is None:
        print(f"WAITING_ARCHIVE {day.isoformat()}: no exact-date episode folder")
        return None
    try:
        plan, _caption, _files = read_approved_archive(episode, day.isoformat())
    except ThreadsBlocked as exc:
        # Production may still be writing. Never dispatch on incomplete QC.
        print(f"WAITING_PRODUCTION_PASS {episode} {day.isoformat()}: {exc}")
        return None
    if (plan.get("production_passed") is not True
            or plan.get("carousel_items") != 10 or plan.get("episode") != episode
            or plan.get("date_sast") != day.isoformat()):
        raise AutoBlocked("Verified production plan is inconsistent")
    print(f"ARCHIVE_READY {episode} {day.isoformat()} 10 slides; Drive QC/handoff PASS")
    return plan


def endpoint_request(token: str, endpoint: str, *, method: str = "GET",
                     payload: dict | None = None) -> tuple[int, dict | None]:
    if not token or len(token) < 20 or "\n" in token:
        raise AutoBlocked("Short-lived Actions token is missing")
    url = f"https://api.github.com/repos/{REPO}/{endpoint}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(url, method=method, data=data, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    })
    try:
        with urlopen(req, timeout=25) as response:
            response_body = response.read(90_000)
            parsed = json.loads(response_body) if response_body else None
            return response.status, parsed
    except HTTPError as exc:
        if method == "GET" and exc.code == 404:
            return 404, None
        # Never print headers, secrets or API response bodies.
        raise AutoBlocked(f"GitHub API {method} failed ({exc.code}); no automatic retry") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise AutoBlocked("GitHub API outcome uncertain; manual reconciliation required") from exc


def get_repo_json(path: str, token: str) -> tuple[dict, str] | None:
    status, result = endpoint_request(token, f"contents/{path}?ref=main")
    if status == 404:
        return None
    if status != 200 or not isinstance(result, dict):
        raise AutoBlocked("Unexpected GitHub repository content response")
    try:
        raw = base64.b64decode(result["content"], validate=False)
        if len(raw) > 40_000:
            raise ValueError
        record = json.loads(raw.decode("utf-8"))
        sha = result["sha"]
    except (KeyError, ValueError, TypeError, UnicodeError) as exc:
        raise AutoBlocked("GitHub publication state is malformed") from exc
    if not isinstance(record, dict) or not isinstance(sha, str):
        raise AutoBlocked("GitHub publication state is not an object")
    return record, sha


def put_repo_json(path: str, token: str, record: dict, *, sha: str | None = None) -> str:
    body = {
        "message": f"Auto release audit {record['date_sast']} {record['phase']}",
        "content": base64.b64encode((json.dumps(record, sort_keys=True, indent=2) + "\n").encode()).decode(),
        "branch": "main",
    }
    if sha is not None:
        body["sha"] = sha
    status, response = endpoint_request(token, f"contents/{path}", method="PUT", payload=body)
    if status not in (200, 201) or not isinstance(response, dict):
        raise AutoBlocked("Could not durably save pre-dispatch claim")
    try:
        return response["content"]["sha"]
    except (KeyError, TypeError) as exc:
        raise AutoBlocked("Unconfirmed GitHub pre-dispatch claim; no dispatch") from exc


def dispatch(platform: str, episode: str, day: date, token: str) -> None:
    date_text = day.isoformat()
    approval = f"PUBLISH_{platform.upper()}_{episode.upper()}_{day.strftime('%Y%m%d')}"
    status, _ = endpoint_request(token, f"actions/workflows/{WORKFLOWS[platform]}/dispatches",
                                 method="POST", payload={
                                     "ref": "main", "inputs": {
                                         "mode": "publish", "episode": episode,
                                         "date_sast": date_text, "publish_confirmation": approval,
                                     },
                                 })
    if status != 204:
        raise AutoBlocked("Unexpected workflow dispatch response; no retry")
    print(f"AUTO_DISPATCHED {platform} {episode} {date_text}; check downstream receipt")


def receipt_path(platform: str, episode: str, day: date) -> str:
    return f"publisher_state/{platform}-{episode.lower()}-{day.strftime('%Y%m%d')}.json"


def day_state_path(day: date) -> str:
    return f"publisher_state/auto-day-{day.strftime('%Y%m%d')}.json"


def validate_day_state(record: dict, day: date) -> str:
    if (not isinstance(record, dict) or record.get("schema") != STATE_SCHEMA
            or record.get("date_sast") != day.isoformat()
            or not EP_RE.fullmatch(str(record.get("episode", "")))
            or record.get("phase") not in PHASES):
        raise AutoBlocked("Existing automatic dispatch state is inconsistent")
    return record["episode"]


def get_state(token: str, day: date) -> tuple[dict, str] | None:
    value = get_repo_json(day_state_path(day), token)
    if value is not None:
        validate_day_state(value[0], day)
    return value


def should_process_day(token: str, day: date, *, probe: bool) -> bool:
    policy = load_policy()
    if probe:
        print("READ_ONLY_PROBE: no dispatch is permitted")
        return True
    if not policy["enabled"] or day < date.fromisoformat(policy["start_date_sast"]):
        print("AUTO_DISABLED_OR_BEFORE_START: skipping without Drive access")
        return False
    state = get_state(token, day)
    if state is None:
        return True
    record = state[0]
    if record["phase"] in ("THREADS_CLAIMED_BEFORE_DISPATCH", "BOTH_DISPATCHED"):
        print("AUTO_ALREADY_DISPATCHED: never dispatch this date again")
        return False
    ig_receipt = get_repo_json(receipt_path("instagram", record["episode"], day), token)
    if ig_receipt is None or ig_receipt[0].get("status") != INSTAGRAM_SUCCESS:
        print("WAITING_FOR_VERIFIED_INSTAGRAM: one-time dispatch lock is present")
        return False
    return True


def verify_event(probe: bool) -> None:
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("GITHUB_REPOSITORY") != REPO
            or os.environ.get("GITHUB_REF") != "refs/heads/main"):
        raise AutoBlocked("Automatic publishing is restricted to main-branch GitHub Actions")
    event = os.environ.get("GITHUB_EVENT_NAME")
    if probe:
        if event not in ("push", "workflow_dispatch"):
            raise AutoBlocked("Probe must use a read-only GitHub event")
        return
    if event == "schedule":
        return
    if event == "workflow_run":
        try:
            envelope = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
            run = envelope["workflow_run"]
            if (run["event"] == "workflow_dispatch"
                    and run["conclusion"] == "success"
                    and run["head_branch"] == "main"
                    and run["head_repository"]["full_name"] == REPO
                    and run["name"] == "AI Geopolitic Instagram — ten-image carousel (human gate)"):
                return
        except (KeyError, TypeError, ValueError, OSError):
            pass
    raise AutoBlocked("No trusted automatic-release triggering event")


def read_receipt(platform: str, episode: str, day: date, token: str) -> dict | None:
    got = get_repo_json(receipt_path(platform, episode, day), token)
    if got is None:
        return None
    record = got[0]
    if (record.get("episode") != episode or record.get("date_sast") != day.isoformat()
            or record.get("carousel_items") != 10):
        raise AutoBlocked("Existing publication receipt has mismatched identity")
    return record


def new_state(episode: str, day: date, phase: str) -> dict:
    return {
        "schema": STATE_SCHEMA, "episode": episode,
        "date_sast": day.isoformat(), "phase": phase,
        "created_utc": datetime.now(SAST).astimezone(ZoneInfo("UTC")).isoformat(),
    }


def process(day: date, token: str, *, probe: bool) -> None:
    plan = detect_ready(day)
    if plan is None:
        return
    episode = plan["episode"]
    state = get_state(token, day)
    if state and validate_day_state(state[0], day) != episode:
        raise AutoBlocked("Automatic day claim points to a different episode")
    ig = read_receipt("instagram", episode, day, token)
    thr = read_receipt("threads", episode, day, token)
    print(f"RECEIPTS {episode}: instagram={ig and ig.get('status')}; threads={thr and thr.get('status')}")
    if probe:
        print("PROBE_COMPLETE_NO_PUBLICATION")
        return
    if ig and ig.get("status") != INSTAGRAM_SUCCESS:
        print("BLOCKED_INSTAGRAM_CLAIM: manual reconciliation only")
        return
    if thr and thr.get("status") != THREADS_SUCCESS:
        print("BLOCKED_THREADS_CLAIM: manual reconciliation only")
        return
    if ig and thr:
        print("ALREADY_PUBLISHED_BOTH: no further release")
        return

    path = day_state_path(day)
    if state is None:
        phase = "INSTAGRAM_DISPATCHED" if ig else "INSTAGRAM_CLAIMED_BEFORE_DISPATCH"
        record = new_state(episode, day, phase)
        sha = put_repo_json(path, token, record)
        if not ig:
            dispatch("instagram", episode, day, token)
            record["phase"] = "INSTAGRAM_DISPATCHED"
            record["instagram_dispatched_utc"] = datetime.now(SAST).isoformat()
            put_repo_json(path, token, record, sha=sha)
            return
        state = (record, sha)

    record, sha = state
    if record["phase"] in ("THREADS_CLAIMED_BEFORE_DISPATCH", "BOTH_DISPATCHED"):
        print("THREADS_ALREADY_DISPATCHED: no duplicate")
        return
    if not ig or ig.get("status") != INSTAGRAM_SUCCESS:
        print("WAITING_FOR_INSTAGRAM: no Threads release yet")
        return
    if thr:
        print("ALREADY_PUBLISHED_THREADS: no further release")
        return
    record["phase"] = "THREADS_CLAIMED_BEFORE_DISPATCH"
    sha = put_repo_json(path, token, record, sha=sha)
    dispatch("threads", episode, day, token)
    record["phase"] = "BOTH_DISPATCHED"
    record["threads_dispatched_utc"] = datetime.now(SAST).isoformat()
    put_repo_json(path, token, record, sha=sha)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("precheck", "process"))
    parser.add_argument("--probe", action="store_true", help="Read-only; never POST or claim")
    args = parser.parse_args(argv)
    try:
        verify_event(args.probe)
        token = os.environ.get("GH_ACTION_TOKEN", "")
        today = current_sast_date()
        if args.stage == "precheck":
            proceed = should_process_day(token, today, probe=args.probe)
            output = os.environ.get("GITHUB_OUTPUT")
            if output:
                with open(output, "a", encoding="utf-8") as handle:
                    handle.write(f"run_detector={'true' if proceed else 'false'}\n")
            print(f"AUTO_PRECHECK {today.isoformat()} continue={proceed}")
        else:
            # Repeat the cheap permission/policy test immediately before any write.
            if should_process_day(token, today, probe=args.probe):
                process(today, token, probe=args.probe)
        return 0
    except (AutoBlocked, OSError, ValueError, TypeError, KeyError) as exc:
        print(f"AUTO_RELEASE_BLOCKED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
