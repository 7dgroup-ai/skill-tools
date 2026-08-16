#!/usr/bin/env python3
"""ZAP Baseline 扫描脚本（对齐设计手稿 security/zap-baseline.py）。
依赖：本地已有 ZAP（docker: owasp/zap2docker-stable）或 standalone 命令。
用法: python security/zap-baseline.py -t http://localhost:8000 -r reports/zap.html
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"


def run_docker(target: str, report: Path) -> int:
    """用 Docker 跑 ZAP baseline（最省事，无需本机 Java/GUI）。"""
    cmd = [
        "docker", "run", "--rm", "-t",
        "owasp/zap2docker-stable",
        "zap-baseline.py", "-t", target,
        "-r", "/zap/wrk/zap_baseline.html",
    ]
    print("[zap] " + " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"[zap] 报告已生成在容器内，本机需挂载卷：")
    print(f"      docker run --rm -v {REPORT_DIR}:/zap/wrk -t owasp/zap2docker-stable \\\n"
          f"        zap-baseline.py -t {target} -r /zap/wrk/zap_baseline.html")
    return 0


def run_standalone(target: str, report: Path) -> int:
    if shutil.which("zap-baseline.py") is None:
        print("[zap] 未找到 zap-baseline.py，请安装 ZAP 或使用 docker 模式。")
        return 2
    cmd = ["zap-baseline.py", "-t", target, "-r", str(report)]
    return subprocess.call(cmd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-t", "--target", default="http://localhost:8000")
    ap.add_argument("-r", "--report", default=str(REPORT_DIR / "zap_baseline.html"))
    ap.add_argument("--engine", choices=["docker", "standalone"], default="docker")
    args = ap.parse_args()

    REPORT_DIR.mkdir(exist_ok=True)
    report = Path(args.report)

    if not __import__("urllib.request", fromlist=["urlopen"]).request.urlopen(args.target, timeout=3):
        print(f"[zap] 目标 {args.target} 不可达，请先 make up")
        return 1

    if args.engine == "docker":
        return run_docker(args.target, report)
    return run_standalone(args.target, report)


if __name__ == "__main__":
    sys.exit(main())