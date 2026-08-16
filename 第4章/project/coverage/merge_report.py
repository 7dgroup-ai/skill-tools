"""多语言覆盖率统一采集（Skill-10）· Cobertura XML → summary.json。

用法：
    python -m coverage.merge_report --dir build/coverage --out build/coverage/summary.json

逻辑（§4.2.2）：
1. 解析 xml_dir/*.xml 的 line-rate / branch-rate / class 级明细
2. 聚合同模块多语言 class（按 filename 归属模块）
3. 按行数加权计算模块级与全局 line_rate / branch_rate
4. 输出 CoverageSummary，含未覆盖行清单（hits=0），供门禁/看板消费
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional


class ClassCoverage:
    def __init__(self, filename: str, name: str, line_rate: float,
                 branch_rate: float, uncovered_lines: List[int]):
        self.filename = filename
        self.name = name
        self.line_rate = line_rate
        self.branch_rate = branch_rate
        self.uncovered_lines = uncovered_lines

    def to_dict(self):
        return {
            "filename": self.filename,
            "name": self.name,
            "line_rate": self.line_rate,
            "branch_rate": self.branch_rate,
            "uncovered_lines": self.uncovered_lines,
        }


def parse_cobertura(xml_path: Path) -> List[ClassCoverage]:
    """解析单个 Cobertura XML → class 级明细。"""
    root = ET.parse(xml_path).getroot()
    classes = []
    for pkg in root.findall(".//package"):
        pkg_name = pkg.get("name", "")
        for cls in pkg.findall("classes/class"):
            lines_node = cls.find("lines")
            total = 0
            covered = 0
            uncovered = []
            if lines_node is not None:
                for line in lines_node.findall("line"):
                    total += 1
                    hits = int(line.get("hits", "0"))
                    if hits > 0:
                        covered += 1
                    else:
                        uncovered.append(int(line.get("number", "0")))
            filename = cls.get("filename", "")
            line_rate = covered / total if total else 1.0
            branch_rate = float(cls.get("branch-rate", line_rate))
            classes.append(ClassCoverage(
                filename=filename,
                name=cls.get("name", pkg_name),
                line_rate=round(line_rate, 4),
                branch_rate=round(branch_rate, 4),
                uncovered_lines=sorted(uncovered),
            ))
    return classes


def _weighted(classes: List[ClassCoverage], line_counts: Dict[str, int],
              field: str) -> float:
    """按行数加权的 rate。line_counts: filename -> 行数。"""
    num = den = 0
    for c in classes:
        n = line_counts.get(c.filename, 1) or 1
        num += getattr(c, field) * n
        den += n
    return round(num / den, 4) if den else 1.0


def merge(xml_dir: Path) -> dict:
    """汇总 xml_dir 下所有 Cobertura XML → CoverageSummary 结构。"""
    xml_files = sorted(Path(xml_dir).glob("*.xml"))
    classes: List[ClassCoverage] = []
    for x in xml_files:
        classes.extend(parse_cobertura(x))

    # 统计每个文件的代码行数（用于加权）
    line_counts: Dict[str, int] = {}
    for c in classes:
        line_counts[c.filename] = max(line_counts.get(c.filename, 0), len(c.uncovered_lines))

    # 按模块（首段路径）聚合
    modules: Dict[str, List[ClassCoverage]] = {}
    for c in classes:
        mod = c.filename.split("/")[0] or "root"
        modules.setdefault(mod, []).append(c)

    summary = {
        "timestamp": "",
        "line_rate": _weighted(classes, line_counts, "line_rate"),
        "branch_rate": _weighted(classes, line_counts, "branch_rate"),
        "modules": [],
        "un_covered_total": sum(len(c.uncovered_lines) for c in classes),
    }
    for mod, mod_classes in sorted(modules.items()):
        summary["modules"].append({
            "name": mod,
            "line_rate": _weighted(mod_classes, line_counts, "line_rate"),
            "branch_rate": _weighted(mod_classes, line_counts, "branch_rate"),
            "classes": [c.to_dict() for c in mod_classes],
        })
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Cobertura XML → summary.json")
    ap.add_argument("--dir", default="build/coverage")
    ap.add_argument("--out", default="build/coverage/summary.json")
    args = ap.parse_args(argv)

    summary = merge(Path(args.dir))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"[merge_report] 全局 line_rate={summary['line_rate']} "
          f"branch_rate={summary['branch_rate']} 未覆盖行={summary['un_covered_total']}")
    for m in summary["modules"]:
        print(f"  {m['name']}: line={m['line_rate']} branch={m['branch_rate']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())