"""Airtest + Poco 跨平台回归样例（Skill-03）。

依赖：pip install airtest poco
备注：
  - connect_device("Android:///") 走 adb；iOS 需 Xcode 环境。
  - login_ok.png 需在真机按分辨率截图生成（airtest report 可导出素材）。
"""

from __future__ import annotations


def airtest_login_smoke():
    from airtest.core.api import connect_device, start_app, assert_exists, Template

    connect_device("Android:///")
    start_app("com.example.sketchstore")

    from poco.drivers.android.uiautomation import AndroidUiautomationPoco
    poco = AndroidUiautomationPoco()

    poco(text="用户名").set_text("u_1001")
    poco(text="密码").set_text("pass_1001")
    poco(text="登录").click()
    assert_exists(Template("login_ok.png"), "登录成功页未出现")


if __name__ == "__main__":
    airtest_login_smoke()
