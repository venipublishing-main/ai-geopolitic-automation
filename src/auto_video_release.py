"""Standing-authority, exact-day video dispatcher; never calls Meta itself.

After BOTH carousel publication receipts are verified, launch one of three
separately claimed video workflows at a time: Instagram Reel, Threads video,
Instagram Story. Each downstream workflow independently verifies Drive QC,
the approved VS001 recording, account identity, immutable MP4 and Meta result.

A durable GitHub day-level pre-dispatch claim is written before each launch.
Uncertain dispatches and existing publisher claims are NEVER automatically
retried. The controller can be probed without any GitHub or Meta writes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from src import auto_release as carousel

CONFIG_PATH = Path("publisher_config/auto_video_release.json")
POLICY_SCHEMA = "ai-geopolitic.publisher.automatic-video-policy.v1"
STATE_SCHEMA = "ai-geopolitic.publisher.automatic-video-day.v1"
SURFACES = ("instagram-reel", "threads-video", "instagram-story")
FILES = {
    "instagram-reel": "ai-geopolitic-instagram-reel.yml",
    "threads-video": "ai-geopolitic-threads-video.yml",
    "instagram-story": "ai-geopolitic-instagram-story.yml",
}
SUCCESS = {
    "instagram-reel": "PUBLISHED_AI_INFO_VERIFIED",
    "threads-video": "PUBLISHED_VERIFIED",
    "instagram-story": "PUBLISHED_STORY_AI_INFO_VERIFIED",
}
SOURCE_WORKFLOWS = {
    "AI Geopolitic Threads — ten-image carousel (human gate)": "threads",
    "AI Geopolitic Instagram — Reel video (human gate)": "instagram-reel",
    "AI Geopolitic Threads — Reel video (human gate)": "threads-video",
    "AI Geopolitic Instagram — Story video (human gate)": "instagram-story",
}
CAROUSEL_RECEIPTS = {
    "instagram": ("ai-geopolitic.instagram.publication-receipt.v1",
                  carousel.INSTAGRAM_SUCCESS, "instagram_account"),
    "threads": ("ai-geopolitic.threads.publication-receipt.v1",
                carousel.THREADS_SUCCESS, "threads_account"),
}
PHASES = tuple(
    f"{surface.upper().replace('-', '_')}_{suffix}"
    for surface in SURFACES
    for suffix in ("CLAIMED_BEFORE_DISPATCH", "DISPATCHED")
) + ("ALL_VIDEOS_VERIFIED",)


def validate_policy(value: dict) -> dict:
    if (not isinstance(value, dict)
            or set(value) != {"schema", "enabled", "start_date_sast",
                              "surfaces_in_order", "require_both_carousels"}
            or value["schema"] != POLICY_SCHEMA
            or type(value["enabled"]) is not bool
            or value["require_both_carousels"] is not True
            or value["surfaces_in_order"] != list(SURFACES)):
        raise carousel.AutoBlocked("Automatic video policy has invalid locked fields")
    try:
        raw = value["start_date_sast"]
        if not isinstance(raw, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            raise ValueError
        date.fromisoformat(raw)
    except ValueError as exc:
        raise carousel.AutoBlocked("Automatic video start date is invalid") from exc
    return value


def load_policy() -> dict:
    return validate_policy(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))


def approval_for(surface: str, episode: str, day: date) -> str:
    if surface not in (*SURFACES, "threads") or not carousel.EP_RE.fullmatch(episode):
        raise carousel.AutoBlocked("Video handoff surface or episode is invalid")
    return (f"PUBLISH_{surface.upper().replace('-', '_')}_"
            f"{episode.upper()}_{day.strftime('%Y%m%d')}")


def video_receipt_path(surface: str, episode: str, day: date) -> str:
    if surface not in SURFACES:
        raise carousel.AutoBlocked("Unknown video surface")
    return carousel.receipt_path(surface, episode, day)


def state_path(day: date) -> str:
    return f"publisher_state/auto-video-day-{day.strftime('%Y%m%d')}.json"


def get_video_state(token: str, day: date, episode: str) -> tuple[dict, str] | None:
    result = carousel.get_repo_json(state_path(day), token)
    if result is not None:
        record = result[0]
        if (record.get("schema") != STATE_SCHEMA
                or record.get("date_sast") != day.isoformat()
                or record.get("episode") != episode
                or record.get("phase") not in PHASES):
            raise carousel.AutoBlocked("Existing video day claim has inconsistent identity")
    return result


def read_video_receipt(token: str, surface: str, episode: str, day: date) -> dict | None:
    value = carousel.get_repo_json(video_receipt_path(surface, episode, day), token)
    if value is None:
        return None
    record = value[0]
    if (record.get("schema") != "ai-geopolitic.publisher.video-publication-receipt.v1"
            or record.get("episode") != episode
            or record.get("date_sast") != day.isoformat()
            or record.get("surface") != surface
            or not isinstance(record.get("status"), str)):
        raise carousel.AutoBlocked("Video receipt identity is inconsistent")
    return record


def verified_carousel_episode(token: str, day: date) -> str | None:
    state = carousel.get_state(token, day)
    if state is None:
        print("WAITING_AUTOMATIC_CAROUSEL: no same-day controller claim")
        return None
    episode = state[0]["episode"]
    for surface, (schema, success, account_field) in CAROUSEL_RECEIPTS.items():
        record = carousel.get_repo_json(carousel.receipt_path(surface, episode, day), token)
        if record is None:
            print(f"WAITING_CAROUSEL_RECEIPT {surface} {episode}")
            return None
        value = record[0]
        if (value.get("schema") != schema
                or value.get("episode") != episode
                or value.get("date_sast") != day.isoformat()
                or value.get(account_field) != "ai_geopolitic"):
            raise carousel.AutoBlocked("Carousel receipt identity is inconsistent")
        if value.get("status") != success:
            print(f"BLOCKED_UNVERIFIED_CAROUSEL {surface} {episode}; no video dispatch")
            return None
    return episode


def next_unverified(token: str, day: date, episode: str,
                    state: tuple[dict, str] | None) -> str | None:
    last_claimed = -1
    if state:
        phase = state[0]["phase"]
        if phase == "ALL_VIDEOS_VERIFIED":
            return None
        last_claimed = next(i for i, surface in enumerate(SURFACES)
                            if phase.startswith(surface.upper().replace("-", "_") + "_"))
    for i, surface in enumerate(SURFACES):
        receipt = read_video_receipt(token, surface, episode, day)
        if receipt is not None:
            if receipt["status"] != SUCCESS[surface]:
                print(f"BLOCKED_EXISTING_VIDEO_CLAIM {surface}: manual reconciliation required")
                return None
            continue
        if i <= last_claimed:
            print(f"WAITING_OR_UNCERTAIN_VIDEO_DISPATCH {surface}: never retry automatically")
            return None
        if i < last_claimed:
            raise carousel.AutoBlocked("Video state advanced without verified earlier release")
        return surface
    print(f"ALL_VIDEOS_VERIFIED {episode} {day.isoformat()}")
    return None


def should_process_day(token: str, day: date, *, probe: bool) -> bool:
    policy = load_policy()
    if probe:
        print("READ_ONLY_VIDEO_PROBE: no dispatch permitted")
        return True
    if not policy["enabled"] or day < date.fromisoformat(policy["start_date_sast"]):
        print("AUTO_VIDEO_DISABLED_OR_BEFORE_START: no dispatch")
        return False
    episode = verified_carousel_episode(token, day)
    if episode is None:
        return False
    state = get_video_state(token, day, episode)
    if state and state[0]["phase"] == "ALL_VIDEOS_VERIFIED":
        print("AUTO_VIDEO_ALREADY_COMPLETE")
        return False
    return next_unverified(token, day, episode, state) is not None


def detect_video_ready(episode: str, day: date) -> None:
    # The caller has installed Pillow/rclone and configured a read-only Drive.
    from src.reel_media import ReelBlocked, read_reel_archive

    try:
        plan, _ = read_reel_archive(episode, day.isoformat())
    except ReelBlocked as exc:
        print(f"WAITING_VERIFIED_REEL_QC {episode}: {exc}")
        raise carousel.AutoBlocked("Verified Reel QC or approved audio is not yet ready") from None
    if (plan.get("episode") != episode or plan.get("date_sast") != day.isoformat()
            or plan.get("frame_count") != 6
            or plan.get("carousel_handoff_passed") is not True
            or plan.get("approved_for_reel_publication") is not False
            or plan.get("audio_status") != "VS001_VERSION_B_APPROVED_MASTER_SHA_VERIFIED"):
        raise carousel.AutoBlocked("Verified Reel plan differs from exact approved production")
    print(f"VIDEO_ARCHIVE_READY {episode} {day.isoformat()} six frames; locked VS001 PASS")


def dispatch(surface: str, episode: str, day: date, token: str) -> None:
    status, _ = carousel.endpoint_request(
        token, f"actions/workflows/{FILES[surface]}/dispatches",
        method="POST",
        payload={"ref": "main", "inputs": {
            "mode": "publish", "episode": episode, "date_sast": day.isoformat(),
            "publish_confirmation": approval_for(surface, episode, day),
        }})
    if status != 204:
        raise carousel.AutoBlocked("Unexpected video dispatch response; no automatic retry")
    print(f"AUTO_VIDEO_DISPATCHED {surface} {episode} {day.isoformat()}")


def process(token: str, day: date, *, probe: bool, expected_episode: str | None = None) -> None:
    verified_episode = verified_carousel_episode(token, day)
    if verified_episode is None and not probe:
        return
    plan = carousel.detect_ready(day)
    if plan is None:
        return
    episode = plan["episode"]
    if (verified_episode is not None and episode != verified_episode) or (
            expected_episode is not None and episode != expected_episode):
        raise carousel.AutoBlocked("Video dispatch episode differs from verified carousel")
    if probe:
        detect_video_ready(episode, day)
        state = get_video_state(token, day, episode)
        surface = next_unverified(token, day, episode, state)
        print(f"VIDEO_PROBE_COMPLETE_NO_PUBLICATION next={surface}")
        return

    state = get_video_state(token, day, episode)
    surface = next_unverified(token, day, episode, state)
    if surface is None:
        if state and state[0]["phase"] != "ALL_VIDEOS_VERIFIED":
            record = {**state[0], "phase": "ALL_VIDEOS_VERIFIED"}
            carousel.put_repo_json(state_path(day), token, record, sha=state[1])
        return
    detect_video_ready(episode, day)
    phase = f"{surface.upper().replace('-', '_')}_CLAIMED_BEFORE_DISPATCH"
    record = dict(state[0]) if state else {
        "schema": STATE_SCHEMA, "episode": episode,
        "date_sast": day.isoformat(),
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    record["phase"] = phase
    record[f"{surface}_claimed_utc"] = datetime.now(timezone.utc).isoformat()
    sha = carousel.put_repo_json(state_path(day), token, record,
                                 sha=state[1] if state else None)
    dispatch(surface, episode, day, token)
    record["phase"] = f"{surface.upper().replace('-', '_')}_DISPATCHED"
    record[f"{surface}_dispatched_utc"] = datetime.now(timezone.utc).isoformat()
    carousel.put_repo_json(state_path(day), token, record, sha=sha)


def verify_event(*, probe: bool, handoff: bool = False, episode: str | None = None,
                 day: date | None = None) -> None:
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("GITHUB_REPOSITORY") != carousel.REPO
            or os.environ.get("GITHUB_REF") != "refs/heads/main"):
        raise carousel.AutoBlocked("Video automation requires main-branch GitHub Actions")
    event = os.environ.get("GITHUB_EVENT_NAME")
    if handoff:
        workflow = os.environ.get("GITHUB_WORKFLOW")
        source = SOURCE_WORKFLOWS.get(workflow or "")
        if (event != "workflow_dispatch" or not source
                or episode is None or day is None
                or day != carousel.current_sast_date()
                or os.environ.get("MODE") != "publish"
                or os.environ.get("EPISODE") != episode
                or os.environ.get("DATE_SAST") != day.isoformat()
                or os.environ.get("APPROVAL") != approval_for(source, episode, day)):
            raise carousel.AutoBlocked("Untrusted video direct handoff")
        return
    if probe:
        if event not in ("push", "workflow_dispatch"):
            raise carousel.AutoBlocked("Video probe event must be read-only")
        return
    if event == "schedule":
        return
    if event == "workflow_run":
        try:
            data = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
            run = data["workflow_run"]
            if (run["event"] == "workflow_dispatch"
                    and run["conclusion"] == "success"
                    and run["head_branch"] == "main"
                    and run["head_repository"]["full_name"] == carousel.REPO
                    and run["name"] in SOURCE_WORKFLOWS):
                return
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            pass
    raise carousel.AutoBlocked("Untrusted automatic video trigger")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("precheck", "process", "handoff"))
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--episode")
    parser.add_argument("--date-sast")
    args = parser.parse_args(argv)
    try:
        token = os.environ.get("GH_ACTION_TOKEN", "")
        if args.stage == "handoff":
            if args.probe or not args.episode or not args.date_sast:
                raise carousel.AutoBlocked("Video handoff requires explicit episode and date")
            day = date.fromisoformat(args.date_sast)
            verify_event(probe=False, handoff=True, episode=args.episode, day=day)
            if should_process_day(token, day, probe=False):
                process(token, day, probe=False, expected_episode=args.episode)
            return 0
        if args.episode or args.date_sast:
            raise carousel.AutoBlocked("Only verified handoff can provide an explicit date")
        verify_event(probe=args.probe)
        day = carousel.current_sast_date()
        if args.stage == "precheck":
            enabled = should_process_day(token, day, probe=args.probe)
            output = os.environ.get("GITHUB_OUTPUT")
            if output:
                with open(output, "a", encoding="utf-8") as f:
                    f.write(f"run_detector={'true' if enabled else 'false'}\n")
            print(f"AUTO_VIDEO_PRECHECK {day.isoformat()} continue={enabled}")
        elif should_process_day(token, day, probe=args.probe):
            process(token, day, probe=args.probe)
        return 0
    except (carousel.AutoBlocked, OSError, ValueError, TypeError, KeyError) as exc:
        print(f"AUTO_VIDEO_BLOCKED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
