"""单元测试：selection/ast_diff（parse_diff / method_changes 纯函数）。"""
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from selection.ast_diff import DiffEntry, MethodInfo, method_changes, parse_diff  # noqa: E402


def test_parse_diff_single_hunk():
    text = """diff --git a/app/routes/cart.py b/app/routes/cart.py
index 123..456 100644
--- a/app/routes/cart.py
+++ b/app/routes/cart.py
@@ -10,7 +10,7 @@ def add_to_cart():
-    return 1
+    return 2
"""
    entries = parse_diff(text)
    assert len(entries) == 1
    assert entries[0].file == "app/routes/cart.py"
    assert 10 in entries[0].changed_lines


def test_parse_diff_added_line_shifts():
    text = """diff --git a/app/routes/cart.py b/app/routes/cart.py
--- a/app/routes/cart.py
+++ b/app/routes/cart.py
@@ -5,0 +5,3 @@
+    x = 1
+    y = 2
+    z = 3
"""
    entries = parse_diff(text)
    assert entries[0].changed_lines == {5, 6, 7}


def test_method_changes_hit_only_changed_method():
    """变更行命中 add_to_cart 方法体，不误报同文件其他方法。"""
    ast_index = {
        "app/routes/cart.py": [
            MethodInfo("list_cart", 3, 8),
            MethodInfo("add_to_cart", 12, 18),
        ]
    }
    entries = [DiffEntry("app/routes/cart.py", {14, 15})]
    result = method_changes(entries, ast_index)
    assert len(result) == 1
    assert result[0]["method"] == "add_to_cart"
    assert result[0]["lines"] == [14, 15]


def test_method_changes_no_false_positive_other_file():
    ast_index = {
        "app/routes/cart.py": [MethodInfo("add_to_cart", 12, 18)],
        "app/routes/goods.py": [MethodInfo("goods_list", 1, 10)],
    }
    entries = [DiffEntry("app/routes/cart.py", {14})]
    result = method_changes(entries, ast_index)
    files = {r["file"] for r in result}
    assert files == {"app/routes/cart.py"}