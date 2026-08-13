"""真机样例用例：登录 → 加购（需 Android 真机/模拟器，无设备自动 skip）。

说明：包名、控件文案按你被测 App 实际替换。
"""

import pytest

u2 = pytest.importorskip("uiautomator2")   # 未安装时跳过整个模块


def test_login_error(d: u2.Device):
    """坏密码登录 → 断言错误提示。"""
    d(text="用户名").set_text("u_1001")
    d(text="密码").set_text("wrong-pass")
    d(text="登录").click()
    assert d(text="密码错误").exists(timeout=3)


def test_add_to_cart(d: u2.Device):
    """登录 → 加购 → 购物车数量为 1。"""
    d(text="用户名").set_text("u_1001")
    d(text="密码").set_text("pass_1001")
    d(text="登录").click()
    d(text="商品A").click()
    d(text="加入购物车").click()
    assert d(text="购物车(1)").exists(timeout=3)
