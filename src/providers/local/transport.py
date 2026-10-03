"""Bounded localhost-only HTTP and MCP Streamable HTTP control-plane clients."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from ..contracts import ProviderUnavailable


class TransportError(ProviderUnavailable):
    pass


class MalformedResponse(TransportError):
    pass


def localhost_url(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or
            parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment):
        raise ValueError("Worker endpoint must be plain HTTP on literal localhost, without credentials/query.")
    if parsed.port is not None and not 1 <= parsed.port <= 65535:
        raise ValueError("Invalid localhost port.")
    return value.rstrip("/")


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise TransportError("Worker redirects are forbidden.")


class LocalHTTP:
    def __init__(self, endpoint: str, *, timeout: float = 5):
        self.endpoint = localhost_url(endpoint)
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not 0 < timeout <= 60:
            raise ValueError("Control-plane timeout must be between zero and 60 seconds.")
        self.timeout = timeout
        # Do not send localhost traffic through machine/environment proxies.
        self._opener = build_opener(ProxyHandler({}), _NoRedirects())

    def request(self, method: str, path: str = "", payload=None, *, headers=None, limit=8 * 1024 * 1024):
        if method not in {"GET", "POST"} or (path and (not path.startswith("/") or path.startswith("//"))):
            raise ValueError("Invalid local HTTP operation.")
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(self.endpoint + path, data=body, method=method,
                          headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
                response_headers = dict(response.headers)
                if content_type == "text/event-stream":
                    chunks, size = [], 0
                    for line in response:
                        size += len(line)
                        if size > limit:
                            raise MalformedResponse("Worker response exceeds limit.")
                        chunks.append(line)
                        if line.strip() == b"":
                            event = b"".join(chunks).decode("utf-8")
                            data = "\n".join(row[5:].lstrip() for row in event.splitlines() if row.startswith("data:"))
                            if data:
                                item = json.loads(data)
                                if not isinstance(item, dict):
                                    raise MalformedResponse("MCP event is not an object.")
                                if item.get("id") == (payload or {}).get("id") and ("result" in item or "error" in item):
                                    return json.dumps(item).encode("utf-8"), response_headers
                            chunks = []
                    raise MalformedResponse("MCP event stream ended without matching response.")
                data = response.read(limit + 1)
                if len(data) > limit:
                    raise MalformedResponse("Worker response exceeds limit.")
                return data, response_headers
        except HTTPError as exc:
            raise TransportError(f"Local worker HTTP {exc.code}.") from None
        except (URLError, TimeoutError, OSError) as exc:
            raise TransportError("Local worker unreachable or control-plane request timed out.") from exc
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise MalformedResponse("Invalid worker response encoding/JSON.") from exc

    def json(self, method, path="", payload=None):
        raw, _ = self.request(method, path, payload)
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise MalformedResponse("Worker did not return JSON.") from exc
        if not isinstance(result, (dict, list)):
            raise MalformedResponse("Worker JSON must be an object or array.")
        return result


class MCPClient:
    """WanGP imports remain in its dedicated server environment, outside the app."""
    def __init__(self, endpoint: str, *, http: LocalHTTP | None = None):
        self.http = http if http is not None else LocalHTTP(endpoint)
        localhost_url(endpoint)
        self._session = None
        self._initialized = False
        self._next_id = 0

    def _rpc(self, method, params, *, notification=False):
        self._next_id += 1
        value = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            value["id"] = self._next_id
        headers = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-06-18"}
        if self._session is not None:
            headers["Mcp-Session-Id"] = self._session
        raw, response_headers = self.http.request("POST", payload=value, headers=headers)
        for key, item in response_headers.items():
            if key.lower() == "mcp-session-id":
                self._session = item  # Private transport state, never audit/log output.
        if notification:
            return None
        try:
            result = json.loads(raw)
            if result.get("jsonrpc") != "2.0" or result.get("id") != value["id"] or "error" in result:
                raise ValueError("Unexpected RPC envelope.")
            return result["result"]
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            raise MalformedResponse("Invalid or failed MCP JSON-RPC response.") from exc

    def initialize(self):
        if not self._initialized:
            result = self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                              "clientInfo": {"name": "ai-geopolitic-phase-c", "version": "1"}})
            if not isinstance(result, dict) or result.get("protocolVersion") != "2025-06-18":
                raise MalformedResponse("Unsupported MCP protocol negotiation.")
            self._rpc("notifications/initialized", {}, notification=True)
            self._initialized = True

    def list_tools(self) -> list[dict]:
        self.initialize()
        tools, cursor = [], None
        for _ in range(20):
            result = self._rpc("tools/list", {} if cursor is None else {"cursor": cursor})
            if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
                raise MalformedResponse("Invalid MCP tool inventory.")
            tools.extend(result["tools"])
            cursor = result.get("nextCursor")
            if not cursor:
                return tools
        raise MalformedResponse("MCP tool pagination exceeded bound.")

    def call_tool(self, name: str, arguments: dict) -> dict:
        self.initialize()
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        if not isinstance(result, dict) or result.get("isError") is True:
            raise TransportError("MCP tool returned an error.")
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured
        try:
            blocks = [item["text"] for item in result["content"] if item.get("type") == "text"]
            if len(blocks) != 1:
                raise ValueError("Ambiguous tool result.")
            value = json.loads(blocks[0])
            if not isinstance(value, dict):
                raise ValueError("Expected tool object.")
            return value
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise MalformedResponse("MCP tool result is not one structured JSON object.") from exc
