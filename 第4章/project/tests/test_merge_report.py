"""单元测试：coverage/merge_report（Cobertura XML 解析与汇总）。"""
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from coverage.merge_report import merge, parse_cobertura  # noqa: E402

SAMPLE_XML = """<?xml version="1.0" ?>
<coverage line-rate="0.9" branch-rate="0.8" version="1.9" timestamp="1760000000">
  <sources><source>/repo</source></sources>
  <packages>
    <package name="app.routes" line-rate="0.9" branch-rate="0.8">
      <classes>
        <class name="app.routes.cart" filename="app/routes/cart.py" line-rate="0.9" branch-rate="0.8">
          <lines>
            <line number="12" hits="5" branch="false"/>
            <line number="19" hits="0" branch="true" condition-coverage="50% (1/2)">
              <conditions><condition number="0" type="jump" coverage="50%"/></conditions>
            </line>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""


def test_parse_cobertura_uncovered_lines():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "coverage-python.xml"
        p.write_text(SAMPLE_XML)
        classes = parse_cobertura(p)
        assert len(classes) == 1
        c = classes[0]
        assert c.filename == "app/routes/cart.py"
        assert c.uncovered_lines == [19]
        assert c.line_rate == 0.5  # 2 行中 1 行覆盖


def test_merge_weighted_summary():
    with tempfile.TemporaryDirectory() as d:
        Path(d, "coverage-python.xml").write_text(SAMPLE_XML)
        summary = merge(Path(d))
        assert summary["un_covered_total"] == 1
        assert "app.routes" not in {m["name"] for m in summary["modules"]}  # 模块名取首段
        assert summary["modules"][0]["name"] == "app"
        assert summary["modules"][0]["classes"][0]["uncovered_lines"] == [19]