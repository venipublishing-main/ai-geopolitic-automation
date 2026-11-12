"""ONE-TIME public QA carousel release; never publishes genuine episode artwork.

This module is only invoked by the ephemeral 2026-11-13 production-handoff
workflow. It requires a separately verified Sisyphus PRODUCTION PASSED signal.
A durable GitHub state claim is committed BEFORE any Meta POST. No retries
after an uncertain Meta POST; manually reconcile instead.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .publisher_archive import Episode, PublisherBlocked, sast_today
from .publisher_handoff import verify_final_handoff
from .publisher_instagram import (
    InstagramCarouselPublisher, UrlLibGraphTransport, validate_public_urls,
)
from .publisher_meta_probe import check_connection, graph_get

DAY = date(2026, 11, 13)
EPISODE = "Ep145"
SIGNAL_SCHEMA = "ai-geopolitic.publisher.signal.v1"
STATE_FILE = Path("publisher_state/ep145-instagram-test.json")
SIGNAL_FILE = Path("publisher_signals/ep145-20261113.json")
QA_MEDIA_COMMIT = "37dac6614a6d01ae4691a5af5561735dd3f14ef1"
QA_PREFIX = (
    "https://raw.githubusercontent.com/venipublishing-main/"
    f"ai-geopolitic-automation/{QA_MEDIA_COMMIT}/media/qa-20261113/"
)
CAPTION_PREFIX = (
    "TEST ONLY — AI Geopolitic publisher QA — Ep145.\n"
    "This is a temporary technical verification carousel and will be deleted.\n\n"
)


class ReleaseBlocked(PublisherBlocked):
    """A failure that must never be retried automatically."""


def validate_signal(value: dict, *, current_day: date) -> tuple[Episode, str]:
    if not isinstance(value, dict) or value.get("schema") != SIGNAL_SCHEMA:
        raise ReleaseBlocked("Publisher signal missing or schema invalid.")
    if current_day != DAY or value.get("production_date_sast") != DAY.isoformat():
        raise ReleaseBlocked("Only Friday 13 November 2026 SAST is authorized.")
    if value.get("episode_id") != EPISODE or value.get("test_only") is not True:
        raise ReleaseBlocked("This workflow only permits the Ep145 QA test.")
    if value.get("source") != "SISYPHUS_DRIVE_VERIFIED":
        raise ReleaseBlocked("Production handoff was not verified against Drive.")
    folder=value.get("archive_folder_id", "")
    if not isinstance(folder,str) or not re.fullmatch(r"[A-Za-z0-9_-]{10,100}",folder):
        raise ReleaseBlocked("Archive folder ID is invalid.")
    ep=Episode(145,DAY,"Ep145-13November2026",folder)
    try:
        verify_final_handoff(ep,value.get("sisyphus_handoff"),production_day=DAY)
    except PublisherBlocked as exc:
        raise ReleaseBlocked(str(exc)) from None
    caption=value.get("archived_carousel_caption")
    sha=value.get("caption_sha256")
    if not isinstance(caption,str) or not 50<=len(caption)<=1800:
        raise ReleaseBlocked("Verified carousel caption is missing or too long.")
    if not isinstance(sha,str) or hashlib.sha256(caption.encode("utf-8")).hexdigest()!=sha:
        raise ReleaseBlocked("Carousel caption checksum does not match its archived readback.")
    if not caption.count("#AIGeopolitic")==1 or not caption.count("#SouthAfrica")==1:
        raise ReleaseBlocked("Archived caption missing canonical project hashtags.")
    if not caption.rstrip().endswith("The event is factual. The interpretation ideological."):
        raise ReleaseBlocked("Archived caption closing line is invalid.")
    if value.get("previously_published") is not False:
        raise ReleaseBlocked("Prior Instagram publication status is not affirmatively false.")
    published_caption=CAPTION_PREFIX+caption
    if len(published_caption)>2200:
        raise ReleaseBlocked("TEST ONLY caption exceeds Instagram limit.")
    return ep,published_caption


def image_urls() -> list[str]:
    return [QA_PREFIX+f"TEST_Slide{i:02d}of10.jpg" for i in range(1,11)]


def verify_public_images(urls: list[str], *, opener=urlopen) -> None:
    validate_public_urls(urls,allowed_hostname="raw.githubusercontent.com")
    sha_set=set()
    for url in urls:
        try:
            req=Request(url,headers={"User-Agent":"AI-Geopolitic-QA-Preflight/1"})
            with opener(req,timeout=20) as response:
                mime=response.headers.get("Content-Type","").split(";",1)[0].lower()
                if mime not in ("image/jpeg","image/jpg"):
                    raise ReleaseBlocked("Public delivery has wrong image MIME.")
                raw=response.read(8*1024*1024+1)
            if not 1000<=len(raw)<=8*1024*1024 or not raw.startswith(bytes.fromhex("ffd8ff")):
                raise ReleaseBlocked("Public image delivery is empty, oversized or not JPEG.")
            sha_set.add(hashlib.sha256(raw).hexdigest())
        except (HTTPError,URLError,OSError,TimeoutError):
            raise ReleaseBlocked("Public delivery JPEG not yet reachable; no posting.") from None
    if len(sha_set)!=10:
        raise ReleaseBlocked("TEST delivery images are duplicated.")


def verified_ig_id(token: str) -> str:
    status=check_connection(token)
    if status.status!="CONNECTED":
        raise ReleaseBlocked("Meta account and publishing permission probe failed.")
    data=graph_get(token,"me/assigned_instagram_accounts",{"fields":"id,username","limit":"100"})
    values=data.get("data")
    if not isinstance(values,list) or data.get("paging",{}).get("next"):
        raise ReleaseBlocked("Instagram assigned-account listing is ambiguous.")
    matches=[str(x.get("id","")) for x in values if isinstance(x,dict)
             and str(x.get("username","")).casefold()=="ai_geopolitic"
             and re.fullmatch(r"[0-9]{5,30}",str(x.get("id","")))]
    if len(matches)!=1:
        raise ReleaseBlocked("Correct Ai_Geopolitic IG account was not uniquely verified.")
    return matches[0]


def inspect_duplicate(token: str, ig_id: str) -> None:
    """Read recent media before publishing to catch a forgotten manual QA post."""
    url=f"https://graph.facebook.com/v26.0/{ig_id}/media?fields=id,caption,permalink&limit=25"
    req=Request(url,headers={"Authorization":"Bearer "+token},method="GET")
    try:
        with urlopen(req,timeout=25) as response:
            result=json.loads(response.read(100_000).decode("utf-8"))
    except (HTTPError,URLError,OSError,ValueError,UnicodeError):
        raise ReleaseBlocked("Could not reconcile recent posts; refusing duplicate risk.") from None
    items=result.get("data")
    if not isinstance(items,list):
        raise ReleaseBlocked("Meta recent-media response is malformed.")
    for item in items:
        if isinstance(item,dict) and "AI Geopolitic publisher QA — Ep145" in str(item.get("caption","")):
            raise ReleaseBlocked("Existing Ep145 QA post detected; do not repost.")


def safe_git(*args: str) -> str:
    try:
        out=subprocess.run(["git",*args],check=True,capture_output=True,
                           encoding="utf-8",timeout=45)
        return out.stdout.strip()
    except (OSError,subprocess.SubprocessError):
        raise ReleaseBlocked("Cannot persist GitHub release state; no Meta action.") from None


def claim_once(ep: Episode, caption: str, *, run_id: str) -> None:
    if STATE_FILE.exists():
        raise ReleaseBlocked("Release state already exists: never publish twice.")
    STATE_FILE.parent.mkdir(parents=True,exist_ok=True)
    record={
        "schema":"ai-geopolitic.publisher.ig-test-receipt.v1",
        "episode":ep.episode_id,"date":DAY.isoformat(),"archive_folder_id":ep.folder_id,
        "status":"CLAIMED_NO_AUTOMATIC_RETRY",
        "caption_sha256":hashlib.sha256(caption.encode("utf-8")).hexdigest(),
        "image_commit":QA_MEDIA_COMMIT,
        "ai_info_required":True,"test_only":True,
        "instagram_media_id":None,"permalink":None,"github_run_id":str(run_id),
    }
    STATE_FILE.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    safe_git("config","user.name","github-actions[bot]")
    safe_git("config","user.email","github-actions[bot]@users.noreply.github.com")
    safe_git("add",str(STATE_FILE))
    safe_git("commit","-m","Claim Ep145 one-time Instagram TEST publish before Meta POST")
    safe_git("push","origin","HEAD:main")


def save_receipt(media_id: str, label_status: str, permalink: str | None) -> None:
    record=json.loads(STATE_FILE.read_text(encoding="utf-8"))
    record["status"]=label_status
    record["instagram_media_id"]=media_id
    record["permalink"]=permalink
    STATE_FILE.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    safe_git("add",str(STATE_FILE))
    safe_git("commit","-m","Record Ep145 QA Instagram publish receipt")
    safe_git("push","origin","HEAD:main")


def verify_published_media(token: str, media_id: str) -> tuple[str,str|None]:
    req=Request(
        f"https://graph.facebook.com/v26.0/{media_id}?fields=id,permalink,is_ai_generated",
        headers={"Authorization":"Bearer "+token},method="GET"
    )
    try:
        with urlopen(req,timeout=20) as response:
            data=json.loads(response.read(40_000).decode("utf-8"))
        if str(data.get("id"))==media_id and data.get("is_ai_generated") is True:
            return "PUBLISHED_AI_INFO_VERIFIED",data.get("permalink")
        return "PUBLISHED_AI_INFO_UNVERIFIED",data.get("permalink")
    except (HTTPError,URLError,OSError,ValueError,UnicodeError):
        return "PUBLISHED_RECEIPT_UNVERIFIED",None


def run(signal_file: Path = SIGNAL_FILE) -> dict:
    if os.environ.get("AI_GEO_ONE_TIME_TEST_ENABLE")!="EXACTLY_ONE_EP145_QA_CAROUSEL":
        raise ReleaseBlocked("One-time QA publishing is not enabled.")
    if sast_today()!=DAY:
        raise ReleaseBlocked("Publishing date has expired.")
    try:
        signal=json.loads(signal_file.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,ValueError):
        raise ReleaseBlocked("No verified Sisyphus publisher signal file.") from None
    ep,caption=validate_signal(signal,current_day=DAY)
    urls=image_urls()
    verify_public_images(urls)
    token=os.environ.get("AI_GEO_IG_ACCESS_TOKEN","")
    if not token:
        raise ReleaseBlocked("Instagram access token is not configured.")
    ig_id=verified_ig_id(token)
    inspect_duplicate(token,ig_id)
    claim_once(ep,caption,run_id=os.environ.get("GITHUB_RUN_ID",""))
    # Once claimed, ANY ambiguous POST stops the one-time run permanently.
    client=InstagramCarouselPublisher(ig_id,"v26.0",UrlLibGraphTransport(token))
    media_id=client.publish(
        urls,caption,allowed_hostname="raw.githubusercontent.com",
        explicit_external_publish_permission=True
    )
    status,permalink=verify_published_media(token,media_id)
    save_receipt(media_id,status,permalink)
    return {"status":status,"episode":"Ep145","test_only":True,
            "posted":True,"instagram_media_id":media_id,"permalink":permalink,
            "music":"NOT_SUPPORTED_FOR_API_CAROUSELS","ai_info_status":status}


def main() -> int:
    try:
        result=run()
        print(json.dumps(result,indent=2))
        return 0
    except ReleaseBlocked as e:
        print(json.dumps({"status":"BLOCKED","reason":str(e),
                          "posted_by_this_run":"NOT_CONFIRMED",
                          "no_automatic_retry":True}))
        return 1
    except Exception:
        # No token or provider response text is ever exposed.
        print(json.dumps({"status":"BLOCKED","reason":"UNEXPECTED_PUBLISHING_FAILURE",
                          "posted_by_this_run":"NOT_CONFIRMED",
                          "no_automatic_retry":True}))
        return 1


if __name__=="__main__":
    raise SystemExit(main())
