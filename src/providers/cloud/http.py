"""Bounded HTTPS for fixed official origins; errors never include remote text/secrets."""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from ..contracts import ProviderUnavailable


class CloudError(ProviderUnavailable):
    def __init__(self, code, *, status=None):
        self.code, self.status = code, status
        super().__init__(code)


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise CloudError("HTTP_REDIRECT_REJECTED")


class CloudHTTP:
    ORIGINS = {"https://api.cloudflare.com/client/v4", "https://aihorde.net/api"}

    def __init__(self, origin, timeout=30):
        if origin not in self.ORIGINS or type(timeout) not in (int, float) or not 0 < timeout <= 60:
            raise ValueError("Cloud HTTP requires a fixed official HTTPS origin and finite timeout <=60s.")
        self.origin, self.timeout = origin, timeout
        self.opener = build_opener(ProxyHandler({}), NoRedirects())

    def request(self, method, path, payload=None, *, headers=None, limit=32 * 1024 * 1024):
        if method not in {"GET", "POST", "DELETE"} or not path.startswith("/") or path.startswith("//"):
            raise ValueError("Invalid official cloud operation.")
        request = Request(self.origin + path, method=method,
                          data=None if payload is None else json.dumps(payload).encode("utf-8"),
                          headers={"User-Agent": "ai-geopolitic/phase-c1", "Content-Type": "application/json", **(headers or {})})
        started = time.monotonic()
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                chunks, size = [], 0
                while True:
                    chunk = response.read(min(65536, limit + 1 - size))
                    size += len(chunk)
                    if size > limit:
                        raise CloudError("RESPONSE_TOO_LARGE")
                    if time.monotonic() - started > self.timeout:
                        raise CloudError("HTTP_TIMEOUT")
                    if not chunk:
                        return b"".join(chunks), response.headers.get("Content-Type", "")
                    chunks.append(chunk)
        except CloudError:
            raise
        except HTTPError as exc:
            # No body, URL, headers, credential-bearing exception chain or message escapes.
            code = {401: "AUTHENTICATION_REJECTED", 403: "ENTITLEMENT_REJECTED", 429: "RATE_OR_QUOTA_LIMIT"}.get(exc.code, "HTTP_REJECTED")
            raise CloudError(code, status=exc.code) from None
        except (TimeoutError, OSError, URLError):
            raise CloudError("HTTP_TIMEOUT_OR_UNAVAILABLE") from None
        except (ValueError, UnicodeError):
            raise CloudError("HTTP_REQUEST_REJECTED") from None

    def json(self, method, path, payload=None, *, headers=None):
        raw, _ = self.request(method, path, payload, headers=headers)
        try:
            value = json.loads(raw)
            if not isinstance(value, (dict, list)):
                raise ValueError("Not an object/array.")
            return value
        except (ValueError, UnicodeError):
            raise CloudError("MALFORMED_JSON") from None
