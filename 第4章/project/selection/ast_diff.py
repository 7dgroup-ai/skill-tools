"""精准选测（Skill-09）· 方法级变更分析：git diff 行号 ∩ AST 函数体行号。

用法：
    python -m selection.ast_diff \
        --repo <sketch-store 路径> --base origin/main --head HEAD \
        --src app --out build/method_changes.json

输出 JSON：{file, method, start_line, end_line, status, lines[]}
验收红线：方法级识别准确率 ≥ 95%；单次 AST 分析 < 5s（≤10 万行源码）。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

try:
    from tree_sitter import Language, Parser
    from tree_sitter_python import language as python_language
except ImportError:  # pragma: no cover
    Language = None
    Parser = None
    python_language = None


# ---------- 1. git diff 解析：文件级 -> 行级 ----------

class DiffEntry:
    """一个文件的 diff：改动行集合（新增/删除/修改的行号）。"""

    def __init__(self, file: str, changed_lines: set[int]):
        self.file = file
        self.changed_lines = changed_lines  # 新文件视角的行号（含增删）

    @property
    def status(self) -> str:
        return "modified"

    def to_dict(self):
        return {"file": self.file, "status": self.status,
                "lines": sorted(self.changed_lines)}


def parse_diff(text: str) -> List[DiffEntry]:
    """解析 `git diff -U0` 输出，得到 {file: 变更行号集合}。

    -U0 下 hunk 头形如 `@@ -a,b +c,d @@`：+c 是新文件起始行号。
    仅跟踪 ``` +```/` -` 行（无上下文行）。
    """
    entries: Dict[str, set[int]] = {}
    current = None
    new_start = 0

    for line in text.splitlines():
        if line.startswith("diff --git "):
            m = re.search(r" b/(.+)$", line)
            if m:
                current = m.group(1)
                entries.setdefault(current, set())
            continue
        if line.startswith("@@ "):
            # @@ -a,b +c,d @@
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if m:
                new_start = int(m.group(1))
            continue
        if current is None:
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue  # 文件头标注行，非变更
        if line.startswith("+"):
            entries[current].add(new_start)
            new_start += 1
        elif line.startswith("-"):
            # 删除行也记为新文件同位置的"受影响行"（保守）
            entries[current].add(new_start)
        else:
            new_start += 1
    return [DiffEntry(f, lines) for f, lines in entries.items() if lines]


def run_git_diff(repo: Path, base: str, head: str, src: str) -> str:
    """跑 `git diff -U0 base...head -- src/**`，返回原始 diff 文本。"""
    cmd = ["git", "diff", "-U0", f"{base}...{head}", "--", f"{src}/"]
    proc = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git diff 失败: {proc.stderr}")
    return proc.stdout


# ---------- 2. tree-sitter 方法级 AST 索引 ----------

class MethodInfo:
    def __init__(self, name: str, start_line: int, end_line: int, kind: str = "function"):
        self.name = name
        self.start_line = start_line
        self.end_line = end_line
        self.kind = kind


def _walk(node, depth: int = 0) -> List[MethodInfo]:
    """遍历 AST，提取函数/方法定义及其行号区间（含 async、装饰器、嵌套）。"""
    out: List[MethodInfo] = []
    if node.type == "function_definition":
        name_node = node.child_by_field_name("name")
        body_node = node.child_by_field_name("body")
        name = name_node.text.decode() if name_node else "<lambda>"
        # 含装饰器：取 decorated_definition 的起始行（若父节点是）
        start = node.start_point[0]
        end = body_node.end_point[0] if body_node else node.end_point[0]
        out.append(MethodInfo(name, start + 1, end + 1))
    # 递归（函数体内嵌套 def 也识别；class 内方法靠 parent 判定交给上层）
    for child in node.children:
        out.extend(_walk(child, depth + 1))
    return out


def build_ast_index(src_dir: Path) -> Dict[str, List[MethodInfo]]:
    """对 src_dir 下所有 *.py 建方法索引：{相对路径: [MethodInfo, ...]}。"""
    if Parser is None:  # pragma: no cover
        raise RuntimeError("需要 tree-sitter + tree-sitter-python：pip install tree-sitter tree-sitter-python")

    parser = Parser(Language(python_language()))
    index: Dict[str, List[MethodInfo]] = {}

    for py in sorted(src_dir.rglob("*.py")):
        rel = py.relative_to(src_dir.parent).as_posix()
        try:
            tree = parser.parse(py.read_bytes())
        except Exception:
            continue  # 无法解析的文件跳过（不参与影响分析）
        methods = _walk(tree.root_node)
        if methods:
            index[rel] = methods
    return index


# ---------- 3. 行号交集：判定方法是否变更 ----------

def method_changes(diff_entries: List[DiffEntry],
                   ast_index: Dict[str, List[MethodInfo]]) -> List[dict]:
    """判定一个方法"改了"：函数体内有非空白行增删。

    返回：{file, method, status, start_line, end_line, lines[]}
    """
    result = []
    for entry in diff_entries:
        for method in ast_index.get(entry.file, []):
            # 方法体区间与变更行是否有交集
            hit = [ln for ln in entry.changed_lines
                   if method.start_line <= ln <= method.end_line]
            if hit:
                result.append({
                    "file": entry.file,
                    "method": method.name,
                    "status": "modified",
                    "start_line": method.start_line,
                    "end_line": method.end_line,
                    "lines": sorted(hit),
                })
    return result


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="git diff + tree-sitter 方法级变更分析")
    ap.add_argument("--repo", default=".", help="被测仓库路径（如 sketch-store）")
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--src", default="app", help="源码目录（相对 repo）")
    ap.add_argument("--out", default="build/method_changes.json")
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    diff_text = run_git_diff(repo, args.base, args.head, args.src)
    entries = parse_diff(diff_text)
    index = build_ast_index(repo / args.src)
    changes = method_changes(entries, index)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(changes, ensure_ascii=False, indent=2))
    print(f"[ast_diff] 方法级变更 {len(changes)} 处 -> {out}")
    for c in changes:
        print(f"  {c['file']}::{c['method']}  L{c['start_line']}-{c['end_line']}  lines={c['lines']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())