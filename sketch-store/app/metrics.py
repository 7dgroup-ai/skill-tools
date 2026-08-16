"""Prometheus 指标暴露（/metrics）。用简单计数，避免引入外部依赖。
指标语义对齐 Skill-15/39：请求数/延迟/错误数 + 业务指标（订单/支付）。"""
import threading
import time
from collections import defaultdict

_lock = threading.Lock()
_requests_total = defaultdict(int)          # (method, path, status) -> count
_latency_sum = defaultdict(float)           # (method, path) -> 累计耗时(ms)
_latency_count = defaultdict(int)           # (method, path) -> 请求数
_business = defaultdict(int)                # 业务指标名 -> 计数


def record_request(method, path, status, duration_ms):
    with _lock:
        _requests_total[(method, path, status)] += 1
        _latency_sum[(method, path)] += duration_ms
        _latency_count[(method, path)] += 1


def inc_business(name, n=1):
    with _lock:
        _business[name] += n


def render():
    lines = []
    ts = int(time.time())

    with _lock:
        lines.append("# HELP sketch_http_requests_total 请求总数")
        lines.append("# TYPE sketch_http_requests_total counter")
        for (method, path, status), n in sorted(_requests_total.items()):
            lines.append(
                f'sketch_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {n}'
            )

        lines.append("# HELP sketch_http_latency_sum 累计耗时毫秒")
        lines.append("# TYPE sketch_http_latency_sum counter")
        for (method, path), s in sorted(_latency_sum.items()):
            lines.append(f'sketch_http_latency_sum{{method="{method}",path="{path}"}} {round(s, 2)}')

        lines.append("# HELP sketch_http_latency_count 请求数")
        lines.append("# TYPE sketch_http_latency_count counter")
        for (method, path), n in sorted(_latency_count.items()):
            lines.append(f'sketch_http_latency_count{{method="{method}",path="{path}"}} {n}')

        lines.append("# HELP sketch_business_metric_total 业务指标")
        lines.append("# TYPE sketch_business_metric_total counter")
        for name, n in sorted(_business.items()):
            lines.append(f'sketch_business_metric_total{{name="{name}"}} {n}')

    lines.append(f"# ts {ts}")
    return "\n".join(lines) + "\n"