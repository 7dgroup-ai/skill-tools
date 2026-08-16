"""优先级排序子包（Skill-12）：三维因子 F(历史失败率)+A(变更关联度)+T(执行时间)。

模块：
- scorer.py : 纯函数评分 score = 0.40*F + 0.40*A + 0.20*(1 - T/T_max)，缺数据兜底
- runner.py : 按时间预算贪心分批 P0/P1/P2 → build/queue.json；skipped 必上报
"""