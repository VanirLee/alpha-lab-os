from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, timezone


def iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sign_request(secret: str, timestamp: str, method: str, path_with_query: str, body: str = "") -> str:
    message = f"{timestamp}{method.upper()}{path_with_query}{body}"
    digest = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")

