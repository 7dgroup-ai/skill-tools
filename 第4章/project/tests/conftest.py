"""pytest 全局：把 project 根目录放入 sys.path，便于 `import selection / coverage / priority`。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))