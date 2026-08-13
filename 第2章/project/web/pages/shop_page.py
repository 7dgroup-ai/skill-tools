from playwright.sync_api import Page


class ShopPage:
    """商品/购物车页 PageObject。"""

    def __init__(self, page: Page):
        self.page = page
        self.add_cart_buttons = page.locator("button[data-goods]")
        self.checkout = page.get_by_role("button", name="结算")
        self.order_result = page.locator(".order_id")

    def add_to_cart(self, name: str) -> None:
        card = self.page.locator(".card", has_text=name)
        card.get_by_role("button", name="加入购物车").click()

    def checkout_order(self) -> str:
        self.checkout.click()
        return self.order_result.inner_text()
