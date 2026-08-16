"""精准选测子包（Skill-09）：git diff + AST 方法级变更分析 + 调用链用例推荐。

模块：
- ast_diff.py     : 方法级变更分析（git diff 行号 ∩ AST 函数体行号）→ method_changes.json
- recommender.py  : 变更方法集 → impact_map 查询 → 合并冒烟集 → test_list.txt
"""