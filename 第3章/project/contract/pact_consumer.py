"""Pact 消费者驱动契约：消费者（下游）定契约，生产者（上游）履约。

依赖 pact-python（可选）。未安装时本模块仅提供契约结构示例，
不参与 `pytest` 验收，避免破坏无外部依赖的单元验收。

前置：pip install pact-python
"""

from __future__ import annotations

from typing import Any


def consumer_contract() -> dict:
    """以“订单服务”消费者视角，声明对“支付服务 /pay”的契约。"""
    return {
        "consumer": "order-service",
        "provider": "payment-service",
        "interactions": [
            {
                "description": "支付订单",
                "given": "订单存在",
                "request": {
                    "method": "POST",
                    "path": "/pay",
                    "body": {"order_id": "order-123", "amount": 19.9},
                    "headers": {"Content-Type": "application/json"},
                },
                "response": {
                    "status": 200,
                    "body": {"code": 0, "transaction_id": "tx-1"},
                },
            }
        ],
    }


def write_pact_file(contract: dict, path: str = "pacts/order-service-payment-service.json") -> None:
    """将契约写成 Pact JSON，供上传 pact-broker。"""
    import json
    import os

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(contract, f, ensure_ascii=False, indent=2)


def build_pact_with_library() -> Any:
    """使用 pact-python 库生成契约（可选依赖）。"""
    from pact import Consumer, Provider  # 可选依赖

    pact = Consumer("order-service").has_pact_with(Provider("payment-service"))
    pact.given("订单存在").upon_receiving("支付订单").with_request(
        "POST", "/pay", body={"order_id": "order-123", "amount": 19.9}
    ).will_respond_with(200, body={"code": 0, "transaction_id": "tx-1"})
    return pact
