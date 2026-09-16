from __future__ import annotations

import json
import ssl
import time
import uuid
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .config import Settings
from .rate_limit import SlidingWindowLimiter
from .signing import iso_timestamp, sign_request


@dataclass
class ApiResponse:
    http_status: int
    body: dict[str, Any] | list[Any] | None
    latency_ms: float
    retry_after: str | None = None
    transport_error: str | None = None
    rate_limit_headers: dict[str, str] | None = None

    @property
    def business_code(self) -> int | None:
        return self.body.get("code") if isinstance(self.body, dict) else None

    @property
    def ok(self) -> bool:
        return self.http_status == 200 and self.business_code == 0


class BinanceWeb3Client:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.limiter = SlidingWindowLimiter(settings.qps)

    @staticmethod
    def _query(params: Mapping[str, Any] | None) -> str:
        if not params:
            return ""
        pairs = [(str(k), str(v)) for k, v in params.items() if v is not None]
        return urlencode(pairs, doseq=False, quote_via=quote)

    def request(self, method: str, path: str, params: Mapping[str, Any] | None = None, body: Any | None = None) -> ApiResponse:
        path = "/" + path.lstrip("/")
        wire_path = path if path.startswith("/build/") else "/build" + path
        relative_path = wire_path[len("/build"):]
        query = self._query(params)
        signed_path = wire_path + ("?" + query if query else "")
        body_text = "" if body is None else json.dumps(body, separators=(",", ":"), ensure_ascii=False)
        self.limiter.wait()
        timestamp = iso_timestamp()
        headers = {
            "Accept": "application/json",
            "X-OC-APIKEY": self.settings.api_key,
            "X-OC-TIMESTAMP": timestamp,
            "X-OC-SIGN": sign_request(self.settings.secret_key, timestamp, method, signed_path, body_text if method.upper() != "GET" else ""),
            "X-OC-RECV-WINDOW": str(self.settings.recv_window_ms),
            "X-OC-NONCE": uuid.uuid4().hex,
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(self.settings.base_url + relative_path + ("?" + query if query else ""), data=body_text.encode("utf-8") if body is not None else None, headers=headers, method=method.upper())
        started = time.perf_counter()
        try:
            import certifi  # type: ignore
            tls_context = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            tls_context = ssl.create_default_context()

        def safe_headers(headers: Any) -> dict[str, str]:
            names = {"x-oc-ratelimit-limit": "X-OC-RateLimit-Limit", "x-oc-ratelimit-remaining": "X-OC-RateLimit-Remaining", "x-oc-used-weight": "X-OC-Used-Weight", "retry-after": "Retry-After"}
            values = {str(key).lower(): value for key, value in getattr(headers, "items", lambda: [])()}
            return {out: str(values[inp]) for inp, out in names.items() if inp in values}

        try:
            with urlopen(request, timeout=self.settings.timeout_s, context=tls_context) as response:
                raw = response.read().decode("utf-8", "replace")
                return ApiResponse(response.status, json.loads(raw) if raw else None, (time.perf_counter() - started) * 1000, rate_limit_headers=safe_headers(response.headers))
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                parsed = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = None
            return ApiResponse(exc.code, parsed, (time.perf_counter() - started) * 1000, retry_after=exc.headers.get("Retry-After"), rate_limit_headers=safe_headers(exc.headers))
        except (URLError, TimeoutError, OSError) as exc:
            return ApiResponse(0, None, (time.perf_counter() - started) * 1000, transport_error=f"{type(exc).__name__}: {getattr(exc, 'reason', exc)}")

