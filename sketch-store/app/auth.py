import base64
import hashlib
import hmac
import json
import os
import time

SECRET = os.environ.get("SKETCH_SECRET", "sketch-store-dev-secret")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_token(user_id: int, username: str, ttl_sec: int = 3600) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"uid": user_id, "sub": username, "exp": int(time.time()) + ttl_sec}
    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}"
    sig = hmac.new(SECRET.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(sig)}"


def parse_token(token: str):
    try:
        h, p, sig = token.split(".")
        signing_input = f"{h}.{p}"
        expect = hmac.new(SECRET.encode(), signing_input.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expect, _b64url_decode(sig)):
            return None
        payload = json.loads(_b64url_decode(p))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def get_current_user(token: str):
    """从 Authorization 头解析。返回 payload dict 或 None。"""
    if not token:
        return None
    return parse_token(token.replace("Bearer ", ""))