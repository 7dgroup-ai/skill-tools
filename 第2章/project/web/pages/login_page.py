from playwright.sync_api import Page


class LoginPage:
    """登录页 PageObject。"""

    def __init__(self, page: Page):
        self.page = page
        self.username = page.get_by_placeholder("用户名")
        self.password = page.get_by_placeholder("密码")
        self.submit = page.get_by_role("button", name="登录")
        self.error = page.locator(".error")

    def login(self, username: str, password: str) -> None:
        self.username.fill(username)
        self.password.fill(password)
        self.submit.click()

    def error_text(self) -> str:
        return self.error.inner_text()
