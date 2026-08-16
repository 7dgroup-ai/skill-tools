# 精准测试工程（第 4 章）统一采集入口（对齐正文 §4.2.2）
.PHONY: help collect-python merge test-recommend test-ast test-priority all

COVERAGE_DIR := build/coverage
REPO ?= ../projects/sketch-store

help:
	@echo "可用目标："
	@echo "  collect-python    - 对 sketch-store 跑 8 步链路用例并产出 Cobertura XML"
	@echo "  merge             - 多语言 XML -> summary.json（merge_report.py）"
	@echo "  test-ast          - 单测 selection/ast_diff + recommender"
	@echo "  test-priority     - 单测 priority/scorer + runner"
	@echo "  test-python       - 全部单测（不含 8 步链路压测用例）"
	@echo "  demo-ast          - 对 sketch-store 演示 ast_diff（需 git 仓库有 diff）"
	@echo "  all               - collect-python + merge + 单测全量"

collect-python:
	mkdir -p $(COVERAGE_DIR)
	# 注意：项目内 coverage/ 子包会遮蔽 coverage 工具，用二进制入口运行
	coverage run --branch --source=$(abspath $(REPO))/app \
	  -m pytest tests/test_sketch_api.py -q
	coverage xml -o $(COVERAGE_DIR)/coverage-python.xml
	@echo "XML 已产出: $(COVERAGE_DIR)/coverage-python.xml"

merge:
	python -m coverage.merge_report --dir $(COVERAGE_DIR) --out $(COVERAGE_DIR)/summary.json

test-ast:
	python -m pytest tests/test_ast_diff.py -q

test-priority:
	python -m pytest tests/test_priority.py tests/test_merge_report.py -q

test-python:
	python -m pytest tests/ -q --ignore=tests/test_sketch_api.py

demo-ast:
	python -m selection.ast_diff --repo $(abspath $(REPO)) --src app --out build/method_changes.json

all: collect-python merge test-python
	@echo "== 全部完成 =="