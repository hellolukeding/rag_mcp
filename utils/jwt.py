import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALG = "HS256"


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - (len(s) % 4)
    if padding and padding < 4:
        s = s + ("=" * padding)
    return base64.urlsafe_b64decode(s)


def create_jwt(payload: Dict[str, Any], expire_seconds: int = 3600) -> str:
    payload_copy = payload.copy()
    payload_copy.setdefault("iat", int(time.time()))
    payload_copy.setdefault("exp", int(time.time()) + expire_seconds)

    header = {"alg": JWT_ALG, "typ": "JWT"}
    header_b = _b64url_encode(json.dumps(
        header, separators=(",", ":")).encode("utf-8"))
    payload_b = _b64url_encode(json.dumps(
        payload_copy, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b}.{payload_b}".encode("utf-8")
    sig = hmac.new(JWT_SECRET.encode("utf-8"),
                   signing_input, hashlib.sha256).digest()
    sig_b = _b64url_encode(sig)

    return f"{header_b}.{payload_b}.{sig_b}"


def decode_jwt(token: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token format")
    header_b, payload_b, sig_b = parts
    signing_input = f"{header_b}.{payload_b}".encode("utf-8")
    expected_sig = hmac.new(JWT_SECRET.encode(
        "utf-8"), signing_input, hashlib.sha256).digest()
    sig = _b64url_decode(sig_b)
    if not hmac.compare_digest(sig, expected_sig):
        raise ValueError("Invalid token signature")

    payload_json = _b64url_decode(payload_b)
    payload = json.loads(payload_json)
    now = int(time.time())
    if "exp" in payload and payload["exp"] < now:
        raise ValueError("Token expired")
    return payload
