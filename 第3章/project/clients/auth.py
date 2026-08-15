from __future__ import annotations

import hashlib
import hmac
import threading
import time
import uuid
from typing import Protocol

from .base import ApiRequest, ApiResponse, IClient


class AuthStrategy(Protocol):
    """认证策略：取令牌、是否可刷新、刷新。"""

    def acquire(self) -> str: ...

    def can_refresh(self) -> bool: ...

    def refresh(self) -> str: ...


class JwtStrategy:
    """JWT 登录态：登录接口换 token，带过期预刷新。

    sketch-store 示例：POST /api/login 返回 {"code":0, "data":{"token","expires_in"}}
    """

    def __init__(self, client: IClient, username: str, password: str, expire_skew: int = 60):
        self._client, self._user, self._pwd = client, username, password
        self._skew = expire_skew
        self._exp_ts: float = 0.0

    def acquire(self) -> str:
        resp = self._client.request(ApiRequest(
            "/api/login", "POST",
            body={"username": self._user, "password": self._pwd},
        ))
        data = resp.body or {}
        if data.get("code") != 0:
            raise PermissionError(f"登录失败: {data}")
        expires_in = data["data"].get("expires_in", 3600)
        self._exp_ts = time.time() + expires_in - self._skew
        return data["data"]["token"]

    def can_refresh(self) -> bool:
        return time.time() < self._exp_ts

    def refresh(self) -> str:
        return self.acquire()


class OAuth2Strategy:
    """OAuth2 client_credentials：令牌缓存 + 并发锁。"""

    def __init__(self, client: IClient, token_url: str, client_id: str, client_secret: str):
        self._client = client
        self._url = token_url
        self._cid, self._csec = client_id, client_secret
        self._token: str | None = None
        self._lock = threading.Lock()

    def acquire(self) -> str:
        with self._lock:
            if self._token:
                return self._token
            resp = self._client.request(ApiRequest(self._url, "POST", body={
                "grant_type": "client_credentials",
                "client_id": self._cid,
                "client_secret": self._csec,
            }))
            self._token = f"Bearer {resp.body['access_token']}"
            return self._token

    def can_refresh(self) -> bool:
        return False

    def refresh(self) -> str:
        self._token = None
        return self.acquire()


class AkSkStrategy:
    """AK/SK 签名：HMAC-SHA256 计算签名放入 header。

    规范约定（示例）：`Authorization: AK ${access_key}:${signature}`
    signature = base64(hmac_sha256(secret, timestamp + "\n" + method + "\n" + body_hash))
    """

    def __init__(self, access_key: str, secret_key: str):
        self._ak, self._sk = access_key, secret_key

    def acquire(self) -> str:
        return f"{self._ak}:{self._sk}"

    def can_refresh(self) -> bool:
        return False

    def refresh(self) -> str:
        return self.acquire()

    def sign_request(self, req: ApiRequest) -> ApiRequest:
        ts = str(int(time.time()))
        body_hash = hashlib.sha256(
            (req.body or "").encode() if isinstance(req.body, str) else b""
        ).hexdigest()
        signing = f"{ts}\n{req.method}\n{body_hash}"
        sig = hmac.new(self._sk.encode(), signing.encode(), hashlib.sha256).hexdigest()
        req.headers["X-Timestamp"] = ts
        req.headers["X-Request-Id"] = uuid.uuid4().hex
        req.headers["Authorization"] = f"AK {self._ak}:{sig}"
        return req


class AuthManager:
    """认证链：注入凭据 + 401 自动刷新重试一次。"""

    def __init__(self, strategy: AuthStrategy):
        self._strategy = strategy
        self._token: str | None = None

    def ensure(self, req: ApiRequest) -> ApiRequest:
        if self._token is None:
            self._token = self._strategy.acquire()
        req.headers.setdefault("Authorization", self._token)
        return req

    def retry_with_refresh(self) -> bool:
        """401 后尝试刷新令牌，返回是否可重试。"""
        if self._strategy.can_refresh():
            self._token = self._strategy.refresh()
            return True
        self._token = None
        return False
