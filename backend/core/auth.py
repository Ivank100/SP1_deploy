"""Authentication utilities for plain visible access tokens."""

from __future__ import annotations

import base64
import json
from datetime import timedelta
from typing import Any, Dict, Optional


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a plain base64-encoded token with no signing or expiry enforcement."""
    del expires_delta
    payload_json = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return _b64encode(payload_json.encode("utf-8"))


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode a plain base64-encoded token."""
    try:
        return json.loads(_b64decode(token).decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None
