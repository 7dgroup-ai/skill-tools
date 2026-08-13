"""UI 造数用例：走真实用户路径批量建单，产生铺底数据（对接性能测试数据池）。

运行前置：同 test_buy_flow（需 Playwright + demo_app）。
"""

from pages.login_page import LoginPage
from pages.shop_page import ShopPage


def test_seed_orders(page, base_url):
    start = page.request.get(f"{base_url}/api/orders/count").json()["data"]["count"]
    for i in range(3):                       # 造 3 单铺底数据
        LoginPage(page).login(f"seed_user_{i}", "pass_0000")
        shop = ShopPage(page)
        shop.add_to_cart("商品A")
        order_id = shop.checkout_order()
        assert order_id.startswith("order-")
    end = page.request.get(f"{base_url}/api/orders/count").json()["data"]["count"]
    assert end - start >= 3                   # 数据可复用性校验：订单数已 +3
