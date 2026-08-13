"""失败用例重跑队列：先判定真失败，再排队重跑，避免 flaky 误报。"""

from __future__ import annotations


class Rerunner:
    def __init__(self, max_retry: int = 2):
        self._max_retry = max_retry

    def rerun(self, failed_case: str, collector):
        """对失败用例重跑；重跑通过则标记 passed_on_retry。

        collector 需提供 `run(case_id) -> Result`（Result.passed: bool）。
        """
        for attempt in range(1, self._max_retry + 1):
            result = collector.run(failed_case)
            if result.passed:
                return {"case": failed_case, "status": "passed_on_retry", "attempt": attempt}
        return {"case": failed_case, "status": "failed", "attempt": self._max_retry}
