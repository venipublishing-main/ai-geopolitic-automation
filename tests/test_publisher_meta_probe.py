"""Offline, no-token/no-network Meta Unified Login read-only probe regression."""
from __future__ import annotations

import json

import pytest

from src.publisher_meta_probe import (
    ProbeBlocked, REQUIRED_PERMISSIONS, check_connection, graph_get, main
)

DUMMY_TOKEN = "TOP_SECRET_TEST_TOKEN_NOT_REAL"
ME = {"id": "100000000001", "client_business_id": "200000000002"}
ASSIGNED = {"data": [{"id": "178400000000001", "username": "Ai_Geopolitic"}]}
PERMS = {"data": [
    {"permission": "instagram_basic", "status": "granted"},
    {"permission": "instagram_content_publish", "status": "granted"},
    {"permission": "instagram_manage_messages", "status": "granted"},
]}


def getter(overrides=None):
    result = {"me": ME, "me/assigned_instagram_accounts": ASSIGNED,
              "me/permissions": PERMS}
    result.update(overrides or {})
    calls = []
    def fake(token, path, params):
        calls.append((token, path, params))
        item = result[path]
        if isinstance(item, Exception):
            raise item
        return item
    return fake, calls


def test_valid_account_and_scopes_connected_without_mutations():
    fake, calls = getter()
    result = check_connection(DUMMY_TOKEN, fake)
    assert result.status == "CONNECTED"
    assert result.account_verified and result.publishing_scope_verified
    assert [c[1] for c in calls] == [
        "me", "me/assigned_instagram_accounts", "me/permissions"
    ]
    assert set(REQUIRED_PERMISSIONS) == {
        "instagram_basic", "instagram_content_publish"
    }
    assert DUMMY_TOKEN not in json.dumps(result.public_dict())
    assert result.public_dict()["published"] is False


@pytest.mark.parametrize("identity", [
    {"data": []},
    {"data": [{"id": "178400000000001", "username": "Veni_Faithful"}]},
    {"data": [{"id": "not_an_id", "username": "ai_geopolitic"}]},
    {"data": [{"id": "178400000000001", "username": "Ai_Geopolitic"}] * 2},
    {"data": [{"id": "178400000000001", "username": "Ai_Geopolitic"}],
     "paging": {"next": "https://example.com/untrusted"}},
])
def test_missing_wrong_duplicate_or_ambiguous_instagram_account_blocks(identity):
    fake, calls = getter({"me/assigned_instagram_accounts": identity})
    result = check_connection(DUMMY_TOKEN, fake)
    assert result.status == "BLOCKED"
    assert result.blocker in (
        "EXPECTED_INSTAGRAM_ACCOUNT_NOT_ASSIGNED", "ASSIGNED_ACCOUNTS_PAGINATED"
    )
    assert result.system_user_verified and not result.account_verified
    assert "me/permissions" not in [p for _, p, _ in calls]


@pytest.mark.parametrize("perms", [
    {"data": [{"permission": "instagram_basic", "status": "granted"}]},
    {"data": [
        {"permission": "instagram_basic", "status": "granted"},
        {"permission": "instagram_content_publish", "status": "declined"},
    ]},
    {"data": []}, {},
])
def test_missing_or_unobserved_content_publish_grant_blocks(perms):
    fake, _ = getter({"me/permissions": perms})
    result = check_connection(DUMMY_TOKEN, fake)
    assert result.status == "BLOCKED"
    assert not result.publishing_scope_verified
    assert result.account_verified


def test_user_identity_is_not_treated_as_ig_account():
    # The subject may have a username but that does NOT prove which
    # Instagram asset the portfolio granted.
    fake, _ = getter({
        "me": {"id": "SYSTEM_USER_ALIAS", "username": "Ai_Geopolitic"},
        "me/assigned_instagram_accounts": {"data": []},
    })
    result = check_connection(DUMMY_TOKEN, fake)
    assert result.status == "BLOCKED"
    assert result.blocker == "EXPECTED_INSTAGRAM_ACCOUNT_NOT_ASSIGNED"


def test_unified_login_system_id_is_not_required_to_be_numeric():
    fake, _ = getter({"me": {"id": "SYSTEM_USER_ALIAS"}})
    assert check_connection(DUMMY_TOKEN, fake).status == "CONNECTED"


def test_empty_system_user_id_fails_closed():
    fake, _ = getter({"me": {"id": ""}})
    result = check_connection(DUMMY_TOKEN, fake)
    assert result.status == "BLOCKED"
    assert result.blocker == "UNVERIFIED_SYSTEM_USER"


def test_meta_errors_are_sanitized():
    fake, _ = getter({"me": RuntimeError(DUMMY_TOKEN)})
    result = check_connection(DUMMY_TOKEN, fake)
    assert result.status == "BLOCKED"
    assert DUMMY_TOKEN not in json.dumps(result.public_dict())


def test_query_is_https_get_and_bearer_header_not_url():
    class Reply:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, max_bytes): return b'{"id":"100000000001"}'
    requests = []
    def opener(request, timeout):
        requests.append((request, timeout))
        return Reply()
    result = graph_get(DUMMY_TOKEN, "me", {"fields": "id,client_business_id"},
                       opener=opener)
    assert result["id"] == "100000000001"
    assert requests[0][0].get_method() == "GET"
    assert requests[0][0].get_header("Authorization") == "Bearer " + DUMMY_TOKEN
    assert DUMMY_TOKEN not in requests[0][0].full_url
    assert requests[0][1] == 15


def test_unapproved_graph_paths_block():
    with pytest.raises(ProbeBlocked):
        graph_get(DUMMY_TOKEN, "123/media_publish", {})
    with pytest.raises(ProbeBlocked):
        graph_get(DUMMY_TOKEN, "me/accounts", {})


def test_missing_secret_cli_outputs_only_sanitized_result(monkeypatch, capsys):
    monkeypatch.delenv("AI_GEO_IG_ACCESS_TOKEN", raising=False)
    assert main() == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "BLOCKED"
    assert payload["blocker"] == "MISSING_TOKEN"
    assert not payload["published"] and not payload["media_created"]


def test_client_business_identity_alone_allows_separate_asset_verification():
    fake, calls = getter({"me": {"client_business_id": "200000000002"}})
    result = check_connection(DUMMY_TOKEN, fake)
    assert result.status == "CONNECTED"
    assert result.account_verified and result.publishing_scope_verified
    assert [x[1] for x in calls] == [
        "me", "me/assigned_instagram_accounts", "me/permissions"
    ]
