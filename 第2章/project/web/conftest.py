"""浏览器 fixture：懒加载 playwright，未安装时仅依赖浏览器的用例失败，不影响纯接口用例。"""

import pytest

BASE_URL = "http://127.0.0.1:8080"   # 替换为你的被测前端


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright   # 懒加载

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")   # 本机无内置 Chromium 时用系统 Chrome
        yield browser
        browser.close()


@pytest.fixture()
def page(browser, base_url: str = BASE_URL):
    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    pg = ctx.new_page()
    pg.goto(base_url)
    yield pg
    ctx.close()


@pytest.fixture()
def base_url() -> str:
    return BASE_URL
