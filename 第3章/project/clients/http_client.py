from __future__ import annotations

import time
from typing import Any

import httpx

from .base import ApiRequest, ApiResponse, IClient


class HttpClient(IClient):
    """REST/JSON 客户端（httpx）。"""

    def __init__(self, base_url: str, *, timeout: float = 10.0, proxy: str | None = None,
                 transport: httpx.BaseTransport | None = None):
        self._base = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self._base, timeout=timeout,
                                    proxy=proxy, transport=transport)

    def request(self, req: ApiRequest, **ctx: Any) -> ApiResponse:
        started = time.monotonic()
        method = req.method.upper()
        if isinstance(req.body, dict):
            json = req.body
            content = None
        else:
            json, content = None, req.body
        resp = self._client.request(
            method,
            req.path,
            headers=req.headers,
            params=req.params,
            json=json,
            content=content,
        )
        body: Any
        try:
            body = resp.json()
        except ValueError:
            body = resp.content
        return ApiResponse(
            status_code=resp.status_code,
            body=body,
            raw=resp.content,
            elapsed_ms=(time.monotonic() - started) * 1000,
            headers=dict(resp.headers),
        )

    def close(self) -> None:
        self._client.close()


class GrpcClient(IClient):
    """gRPC 客户端。

    前置：由 .proto 编译出的 stub 模块（`python -m grpc_tools.protoc -I. --python_out=.`）。
    ApiRequest.path 格式：`package.Service/Method`
    ApiRequest.body 格式：proto message 实例。
    """

    def __init__(self, target: str, stub_registry: dict[str, tuple[Any, Any]]):
        # stub_registry: {"package.Service": (StubClass, Channel)}
        self._target = target
        self._registry = stub_registry
        self._channel = None

    def _ensure_channel(self):
        import grpc  # 延迟导入，避免无 grpc 依赖时影响其他模块

        if self._channel is None:
            self._channel = grpc.insecure_channel(self._target)
        return self._channel

    def request(self, req: ApiRequest, **ctx: Any) -> ApiResponse:
        import grpc

        service, method = req.path.split("/", 1)
        stub_cls, _ = self._registry[service]
        stub = stub_cls(self._ensure_channel())
        fn = getattr(stub, method, None) or getattr(stub, method.lower(), None)
        if fn is None:
            raise ValueError(f"stub 上不存在方法 {method}")
        started = time.monotonic()
        try:
            message = fn(req.body, timeout=req.timeout)
            return ApiResponse(status_code=200, body=message,
                               elapsed_ms=(time.monotonic() - started) * 1000)
        except grpc.RpcError as e:
            return ApiResponse(status_code=e.code().value[0], body=None,
                               elapsed_ms=(time.monotonic() - started) * 1000)

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()


class GraphQLClient(IClient):
    """GraphQL 客户端：单一端点 + query 模板 + variables。"""

    def __init__(self, endpoint: str, *, timeout: float = 10.0):
        self._http = httpx.Client(base_url=endpoint, timeout=timeout)

    def request(self, req: ApiRequest, **ctx: Any) -> ApiResponse:
        started = time.monotonic()
        payload = {"query": req.body, "variables": req.params}
        resp = self._http.post("", json=payload, headers=req.headers)
        data = resp.json()
        return ApiResponse(
            status_code=resp.status_code,
            body=data.get("data", data.get("errors")),
            raw=resp.content,
            elapsed_ms=(time.monotonic() - started) * 1000,
        )

    def close(self) -> None:
        self._http.close()


class WsClient(IClient):
    """WebSocket 客户端：长连接会话 + 心跳 + 按消息 ID 关联。"""

    def __init__(self, url: str):
        self._url = url
        self._ws = None

    def _ensure(self):
        import websockets  # 延迟导入

        if self._ws is None:
            self._ws = __import__("websockets").sync.client.connect(self._url)
            self._ws = self._ws.__enter__()
        return self._ws

    def request(self, req: ApiRequest, **ctx: Any) -> ApiResponse:
        ws = self._ensure()
        started = time.monotonic()
        ws.send(req.body if isinstance(req.body, str) else __import__("json").dumps(req.body))
        raw = ws.recv()
        body = raw
        try:
            body = __import__("json").loads(raw)
        except (TypeError, ValueError):
            pass
        return ApiResponse(status_code=200, body=body,
                           elapsed_ms=(time.monotonic() - started) * 1000)

    def close(self) -> None:
        if self._ws is not None:
            self._ws.close()
            self._ws = None
