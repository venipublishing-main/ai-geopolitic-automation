"""Read-only Meta Unified Login connection probe for Ai_Geopolitic.

No Meta POST/PUT/DELETE requests, Graph mutations, account linking, or
publication. Uses only a Bearer header, never puts a token into URLs or logs.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GRAPH_BASE = "https://graph.facebook.com/v26.0"
EXPECTED_USERNAME = "ai_geopolitic"
REQUIRED_PERMISSIONS = frozenset({"instagram_basic", "instagram_content_publish"})
ACCOUNT_ID = re.compile(r"^[0-9]{5,30}$")
MAX_RESPONSE_BYTES = 128 * 1024


class ProbeBlocked(Exception):
    """A sanitized blocker that never includes provider response bodies."""


def graph_get(token: str, path: str, params: dict[str, str],
              opener: Callable = urlopen) -> dict:
    """Bounded, allowlisted GET; intentionally not a general Graph client."""
    if path not in ("me", "me/permissions", "me/assigned_instagram_accounts"):
        raise ProbeBlocked("INVALID_PROBE_PATH")
    if not isinstance(token, str) or not token.strip():
        raise ProbeBlocked("MISSING_TOKEN")
    query = urlencode(params)
    url = f"{GRAPH_BASE}/{path}" + (f"?{query}" if query else "")
    request = Request(
        url, headers={"Authorization": "Bearer " + token}, method="GET"
    )
    try:
        with opener(request, timeout=15) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ProbeBlocked("RESPONSE_TOO_LARGE")
            doc = json.loads(raw.decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError):
        raise ProbeBlocked("GRAPH_READ_FAILED") from None
    except (UnicodeError, json.JSONDecodeError):
        raise ProbeBlocked("GRAPH_INVALID_RESPONSE") from None
    if not isinstance(doc, dict) or "error" in doc:
        raise ProbeBlocked("GRAPH_READ_FAILED")
    return doc


@dataclass(frozen=True)
class ProbeResult:
    status: str
    system_user_verified: bool
    account_verified: bool
    publishing_scope_verified: bool
    blocker: str | None = None

    def public_dict(self) -> dict:
        return {
            "status": self.status,
            "connection": "Meta Unified Login (read-only)",
            "expected_instagram_username": EXPECTED_USERNAME,
            "system_user_verified": self.system_user_verified,
            "instagram_account_verified": self.account_verified,
            "publishing_scope_verified": self.publishing_scope_verified,
            "media_created": False,
            "published": False,
            "blocker": self.blocker,
        }


def check_connection(token: str, getter: Callable = graph_get) -> ProbeResult:
    """Conservatively verify the token and exactly one assigned IG account.

    A system-user /me result is not an Instagram profile. Do not use it as an
    Instagram ID or infer that the token can publish to a specific profile.
    """
    if not token or not isinstance(token, str):
        return ProbeResult("BLOCKED", False, False, False, "MISSING_TOKEN")
    valid_system_user = False
    matched_account = False
    scopes_ok = False
    try:
        me = getter(token, "me", {"fields": "id,client_business_id"})
        if not ACCOUNT_ID.fullmatch(str(me.get("id", ""))):
            raise ProbeBlocked("UNVERIFIED_SYSTEM_USER")
        valid_system_user = True

        assigned = getter(
            token, "me/assigned_instagram_accounts",
            {"fields": "id,username", "limit": "100"},
        )
        profiles = assigned.get("data")
        if not isinstance(profiles, list):
            raise ProbeBlocked("ASSIGNED_ACCOUNTS_UNAVAILABLE")
        if assigned.get("paging", {}).get("next"):
            raise ProbeBlocked("ASSIGNED_ACCOUNTS_PAGINATED")
        targets = [
            entry for entry in profiles if isinstance(entry, dict)
            and str(entry.get("username", "")).casefold() == EXPECTED_USERNAME
            and ACCOUNT_ID.fullmatch(str(entry.get("id", "")))
        ]
        if len(targets) != 1:
            raise ProbeBlocked("EXPECTED_INSTAGRAM_ACCOUNT_NOT_ASSIGNED")
        matched_account = True

        grants = getter(token, "me/permissions", {})
        entries = grants.get("data")
        if not isinstance(entries, list):
            raise ProbeBlocked("GRANTED_PERMISSIONS_UNAVAILABLE")
        active = {
            item.get("permission") for item in entries if isinstance(item, dict)
            and item.get("status") == "granted"
        }
        if not REQUIRED_PERMISSIONS.issubset(active):
            raise ProbeBlocked("REQUIRED_PUBLISHING_PERMISSIONS_NOT_GRANTED")
        scopes_ok = True
    except ProbeBlocked as exc:
        return ProbeResult("BLOCKED", valid_system_user, matched_account, scopes_ok,
                           str(exc))
    except Exception:
        # Never print an exception, request, token or Meta response body.
        return ProbeResult("BLOCKED", valid_system_user, matched_account, scopes_ok,
                           "UNEXPECTED_VERIFICATION_FAILURE")
    return ProbeResult("CONNECTED", True, True, True)


def main() -> int:
    result = check_connection(os.environ.get("AI_GEO_IG_ACCESS_TOKEN", ""))
    print(json.dumps(result.public_dict(), indent=2))
    return 0 if result.status == "CONNECTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
