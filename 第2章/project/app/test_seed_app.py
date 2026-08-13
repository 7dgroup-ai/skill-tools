"""App 造数样例：走真实 UI 路径批量下单，生成铺底数据（需设备）。

思路：循环“登录 → 选商品 → 加购 → 结算”，复用设备会话，产生 N 单。
"""

import pytest

u2 = pytest.importorskip("uiautomator2")   # 未安装时跳过整个模块


def test_seed_orders_via_app(d: u2.Device):
    n = 2   # 造 2 单
    for i in range(n):
        d(text="用户名").set_text(f"seed_user_{i}")
        d(text="密码").set_text("pass_0000")
        d(text="登录").click()
        d(text="商品A").click()
        d(text="加入购物车").click()
        d(text="结算").click()
        assert d(text="下单成功").exists(timeout=3)
        d(text="退出").click()   # 回到登录页，进入下一轮
