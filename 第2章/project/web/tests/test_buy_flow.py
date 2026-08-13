"""UI 功能验证用例：登录 → 加购 → 结算 → 建单（需 Playwright + demo_app 运行中）。

运行前置：
    uvicorn demo_app.main:app --port 8080 &
    pytest project/web/tests/test_buy_flow.py
"""

from pages.login_page import LoginPage
from pages.shop_page import ShopPage


def test_login_error_shown(page):
    LoginPage(page).login("u_1001", "wrong-pass")
    assert "用户名或密码错误" in LoginPage(page).error_text()


def test_buy_flow(page):
    LoginPage(page).login("u_1001", "pass_1001")
    shop = ShopPage(page)
    shop.add_to_cart("商品A")
    shop.add_to_cart("商品B")
    order_id = shop.checkout_order()
    assert order_id.startswith("order-")
