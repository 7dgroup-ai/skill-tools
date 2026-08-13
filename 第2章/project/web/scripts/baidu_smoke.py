"""真实站点冒烟验证（第 2 章 Web 自动化，可选的网络用例）。

目标：打开 https://www.baidu.com/ → 输入框输入"什么是智能测试" → 提交 →
断言结果页返回数据（#content_left 有结果条目）。用于证明"打开首页 → 输入 → 提交
→ 断言"链路在真实站点上可用，并产出截图作为实测证据。

注意：百度对无头浏览器有反爬校验，需加
--disable-blink-features=AutomationControlled 并覆写 navigator.webdriver。

运行：
    python project/web/scripts/baidu_smoke.py [关键词] [截图路径]
"""

import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

KEYWORD = sys.argv[1] if len(sys.argv) > 1 else "什么是智能测试"
SHOT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/baidu_result.png"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36")
STEALTH = "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome", headless=True,
            args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(viewport={"width": 1280, "height": 900},
                                  user_agent=UA, locale="zh-CN")
        ctx.add_init_script(STEALTH)
        page = ctx.new_page()

        page.goto("https://www.baidu.com/", timeout=30000,
                  wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=30000)
        page.fill("#kw", KEYWORD, force=True)
        page.keyboard.press("Enter")
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(1500)

        if "wappass" in page.url or "captcha" in page.url:
            print("FAIL: 被百度安全验证拦截（换 IP / 网络环境重试）")
            browser.close()
            return 2

        results = page.locator("#content_left h3, #content_left .result")
        count = results.count()
        print(f"[1] 提交后 URL：{page.url[:100]}")
        print(f"[2] 页面标题：{page.title()}")
        print(f"[3] 返回结果条数：{count}")
        for i in range(min(count, 5)):
            text = re.sub(r"\s+", " ",
                          results.nth(i).inner_text().strip())
            print(f"      {i + 1}. {text[:80]}")
        Path(SHOT).parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=SHOT, full_page=False)
        print(f"[4] 截图已保存：{SHOT}")

        ok = count > 0
        browser.close()
        print("RESULT:", "PASS" if ok else "FAIL")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
