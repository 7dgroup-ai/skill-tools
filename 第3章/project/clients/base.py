from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ApiRequest:
    """统一请求对象：所有协议共用同一语义。"""

    path: str                     # REST 路径 / gRPC method / WS 端点
    method: str = "GET"           # REST 谓词；gRPC 填 service/method
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    body: Any = None              # dict/bytes/proto message
    timeout: float = 10.0


@dataclass
class ApiResponse:
    """统一响应对象：业务断言只依赖它，与底层协议解耦。"""

    status_code: int
    body: Any = None              # 反序列化后的对象（dict/list/bytes）
    raw: bytes = b""
    elapsed_ms: float = 0.0
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


class IClient(Protocol):
    """统一协议：所有 Client 必须实现。"""

    def request(self, req: ApiRequest, **ctx: Any) -> ApiResponse: ...

    def close(self) -> None: ...
