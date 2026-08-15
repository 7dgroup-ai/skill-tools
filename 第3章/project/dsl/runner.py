from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from clients.base import ApiRequest, ApiResponse, IClient
from datafactory.extractors import extract
from dsl.loader import load_scenario


class ScenarioError(Exception):
    """场景执行失败。"""


@dataclass
class StepResult:
    name: str
    ok: bool
    resp: ApiResponse | None = None
    attempt: int = 1
    error: str | None = None


class ScenarioRunner:
    """YAML 场景执行引擎：上下文插值 + 关联提取 + 失败重试 + 前后置。"""

    def __init__(self, client: IClient, auth=None, context: dict | None = None):
        self._client = client
        self._auth = auth
        self._ctx: dict = dict(context or {})

    @property
    def ctx(self) -> dict:
        return self._ctx

    def run(self, scenario: dict) -> list[StepResult]:
        results: list[StepResult] = []
        self._merge_globals(scenario)
        self._run_hooks(scenario.get("setup", []))
        for step in scenario["steps"]:
            results.append(self._exec_step(step))
            if not results[-1].ok:
                raise ScenarioError(f"步骤 {results[-1].name} 失败")
        self._run_hooks(scenario.get("teardown", []))
        return results

    def run_file(self, path: str) -> list[StepResult]:
        return self.run(load_scenario(path))

    # ---- 内部 ----

    def _merge_globals(self, scenario: dict) -> None:
        base = scenario.get("base_url", "").rstrip("/")
        if base:
            self._ctx["base_url"] = base
        for k, v in (scenario.get("vars") or {}).items():
            # vars 作为“模板默认值”：外部已注入的上下文优先，不覆盖
            if k not in self._ctx:
                self._ctx[k] = self._interpolate(v)

    def _run_hooks(self, hooks: list[dict]) -> None:
        for hook in hooks or []:
            action = hook.get("action", hook)
            if "delay_ms" in action:
                time.sleep(action["delay_ms"] / 1000)

    def _exec_step(self, step: dict) -> StepResult:
        req_spec = step["request"]
        retry = step.get("retry", {})
        times = retry.get("times", 0)
        last_resp: ApiResponse | None = None
        reason: str | None = None
        for attempt in range(1 + times):
            req = self._build_request(req_spec)
            last_resp = self._client.request(req)
            passed, reason = self._pass(step.get("assert", {}), last_resp)
            if passed:
                self._extract(step.get("extract", {}), last_resp)
                return StepResult(step["name"], True, last_resp, attempt + 1)
            if last_resp.status_code in retry.get("on", []):
                continue
            break
        return StepResult(step["name"], False, last_resp, 1 + times, error=reason)

    def _interpolate(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._interp_string(value)
        if isinstance(value, dict):
            return {k: self._interpolate(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._interpolate(v) for v in value]
        return value

    def _interp_string(self, s: str) -> str:
        if s == "${token}":
            return self._ctx.get("token", s)
        out = s
        for key, val in list(self._ctx.items()):
            out = out.replace("${" + key + "}", str(val))
        return out

    def _build_request(self, spec: dict) -> ApiRequest:
        headers = dict(spec.get("headers", {}))
        token = self._ctx.get("token")
        if token:
            headers.setdefault("Authorization", f"Bearer {token}")
        req = ApiRequest(
            path=self._interp_string(spec["path"]),
            method=spec.get("method", "GET"),
            headers=headers,
            params=self._interpolate(spec.get("params", {})),
            body=self._interpolate(spec.get("body")),
            timeout=spec.get("timeout", 10.0),
        )
        return req

    def _pass(self, asserts: dict, resp: ApiResponse) -> tuple[bool, str | None]:
        from asserters.schema_validator import assert_schema

        try:
            if asserts.get("http_ok"):
                assert resp.ok, f"HTTP {resp.status_code}"
            if "http_code" in asserts:
                assert resp.status_code == asserts["http_code"], \
                    f"HTTP 期望 {asserts['http_code']}，实际 {resp.status_code}"
            if "biz_code" in asserts:
                expect = asserts["biz_code"]
                actual = (resp.body or {}).get("code") if isinstance(resp.body, dict) else None
                assert actual == expect, f"业务码期望 {expect}，实际 {actual}"
            if "schema" in asserts:
                assert_schema(resp.body, asserts["schema"])
            return True, None
        except Exception as e:      # noqa: BLE001 断言失败即步骤失败
            return False, f"{type(e).__name__}: {e}"

    def _extract(self, specs: dict, resp: ApiResponse) -> None:
        for var, spec in (specs or {}).items():
            self._ctx[var] = extract(spec["path"], resp.body, spec.get("method", "jsonpath"))


if __name__ == "__main__":
    import sys

    from clients.http_client import HttpClient

    def _main(argv: list[str]) -> None:
        if len(argv) < 2:
            print("用法: python -m dsl.runner <scenario.yaml> [base_url]")
            sys.exit(2)
        path, base = argv[1], argv[2] if len(argv) > 2 else None
        scenario = load_scenario(path)
        if base:
            scenario["base_url"] = base
        client = HttpClient(scenario.get("base_url", "http://localhost:8000"))
        runner = ScenarioRunner(client)
        try:
            results = runner.run(scenario)
        except ScenarioError as e:
            print(f"[FAIL] {e}")
            sys.exit(1)
        finally:
            client.close()
        for r in results:
            status = r.resp.status_code if r.resp else "?"
            print(f"[{'OK' if r.ok else 'FAIL'}] {r.name}  http={status}  attempt={r.attempt}")
        print(f"场景 {scenario['name']} 执行完成，通过 {sum(r.ok for r in results)}/{len(results)} 步")

    _main(sys.argv)
