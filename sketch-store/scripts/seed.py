#!/usr/bin/env python3
"""铺底数据初始化：python scripts/seed.py [--scale local|prod]"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.seeded import seed  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", default="local", choices=["local", "prod"])
    args = ap.parse_args()
    seed(args.scale)