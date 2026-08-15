from __future__ import annotations

import jsonschema
from jsonschema import Draft7Validator

# 通用业务响应 Schema：sketch-store 类接口约定 {"code":0, "data":{...}}
BIZ_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["code"],
    "properties": {
        "code": {"type": "integer"},
        "msg": {"type": ["string", "null"]},
        "data": {},
    },
}

USER_LOGIN_SCHEMA = {
    "type": "object",
    "required": ["code", "data"],
    "properties": {
        "code": {"const": 0},
        "data": {
            "type": "object",
            "required": ["token"],
            "properties": {
                "token": {"type": "string", "minLength": 20},
                "expires_in": {"type": "integer", "minimum": 300},
            },
        },
    },
}


def assert_schema(body: dict, schema: dict, *, name: str = "response") -> None:
    """校验 body 满足 JSON Schema，不通过抛 ValidationError。"""
    Draft7Validator(schema).validate(instance=body)


def compile_validator(schema: dict) -> Draft7Validator:
    """预编译校验器（性能：批量校验时复用）。"""
    return Draft7Validator(schema)
