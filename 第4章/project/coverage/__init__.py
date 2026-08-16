"""覆盖率采集子包（Skill-10）：各语言 Cobertura XML 统一收口 + 用例-方法映射表。

模块：
- merge_report.py : 解析 build/coverage/*.xml → summary.json（含未覆盖行清单）
- impact_map.sql  : 测试运行期 test_case → (source_file, source_func) 映射表结构
"""