# sketch-store Makefile —— 一键任务入口（对齐《被测应用设计手稿》§4.1）
.PHONY: help up down seed smoke perf-baseline clean logs

HOST ?= http://localhost:8000

help:
	@echo "可用目标："
	@echo "  up            - 本地启动 (uvicorn app.main:app --port 8000)"
	@echo "  down          - 停止 uvicorn"
	@echo "  seed          - 铺底数据 (1000商品/500用户)"
	@echo "  smoke         - 冒烟：跑通 8 步链路并校验"
	@echo "  perf-baseline - 示例性能压测命令 (k6 脚本见 loadtest/)"
	@echo "  logs          - 查看运行日志 (tail)"

up:
	@mkdir -p logs data
	@nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > logs/app.log 2>&1 &
	@echo "启动中... sleep 3"
	@sleep 3
	@curl -sf $(HOST)/health || (echo "应用未就绪，看 logs/app.log"; exit 1)

down:
	@-pkill -f "uvicorn app.main:app" 2>/dev/null; echo "已停止"

seed:
	python3 scripts/seed.py

smoke:
	bash scripts/smoke.sh $(HOST)

perf-baseline:
	@echo "提示：安装 k6 后运行："
	@echo "  k6 run --env HOST=$(HOST) --env VUS=10 --env DURATION=180s loadtest/shopping_flow.js"
	@echo "或 JMeter：jmeter -n -t loadtest/shopping_flow.jmx -Jhost=$(HOST)"

logs:
	tail -f logs/app.log