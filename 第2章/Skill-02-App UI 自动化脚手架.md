# Skill-02-App UI 自动化脚手架

> **能力名称**：App UI 自动化脚手架（UiAutomator2 / Appium 2.x 选型与设备连接、最小可用工程代码、跨平台写法对比）
> **生命周期阶段**：准备/构建
> **资产来源**：第 2 章 §2.2 App 自动化；project/app 工程；自如 App 实战演示
> **文档版本**：v1.0 | 维护者：李文 | 更新日期：2026-08-06

---

## 0. 一句话定位

解决 App 自动化"设备从哪来、怎么连、怎么保证稳定"三大难题：Android 首选 UiAutomator2（Python 直连、无额外服务）、跨平台用 Appium 2.x，交付最小可用工程代码与真机实战演示，形成"连设备 → 写用例 → 造数 → 接入平台"闭环。

---

## 1. 触发场景（何时调用）

- [ ] 团队需要建立 Android/iOS App UI 自动化，需在 UiAutomator2 / Appium 2.x / Espresso / XCUITest 中选型
- [ ] 已有设备（真机/模拟器），需建立稳定的 ADB/USB/WiFi 连接链路，解决 atx-agent 断连、横竖屏、定位漂移等稳定性问题
- [ ] 需要最小可用工程代码（device.py / conftest.py / test_login.py / test_seed_app.py），支持无设备自动 skip、并发造数隔离
- [ ] 同一用例需跑 Android + iOS，需 UiAutomator2 与 Appium 2.x 跨平台写法对比，决定单端深耕还是跨平台复用

> 不需要此 Skill 的场景：纯 Web 端自动化（用 Skill-01）、仅做接口测试（用 Skill-05）、无移动端业务、无真机/模拟器环境（用 Skill-01 Web 自动化替代）。

---

## 2. 输入契约（Input Contract）

| 项 | 必备/可选 | 说明 |
|---|---|---|
| Android 真机/模拟器 | 必备 | 开启 USB 调试，`adb devices` 可见序列号；或模拟器端口（如 62001） |
| adb 环境 | 必备 | Android SDK platform-tools 在 PATH 中，`adb version` 可执行 |
| Python 环境 | 必备 | Python 3.10+，可安装 uiautomator2≥3.0、pytest≥8.0 |
| 被测 App 包名 | 必备 | 如 `com.example.sketchstore` 或 `com.ziroom.ziroomcustomer` |
| WiFi 网络（可选） | 可选 | 同一局域网，`adb tcpip 5555 && adb connect <IP>:5555` 免数据线 |

**入口检查清单**：
- [ ] `adb devices` 返回 `device` 状态（非 `unauthorized`/`offline`）
- [ ] `python -m uiautomator2 init` 完成，手机端显示 atx-agent 安装成功
- [ ] `pip install uiautomator2 pytest` 无报错
- [ ] 明确被测 App 的包名与启动 Activity（`d.app_start("pkg")` 可启动）

---

## 3. 工具链（Toolchain）

| 工具 | 版本 | 角色 | 备选 |
|---|---|---|---|
| uiautomator2 | ≥3.0 | Android 核心驱动（首选） | Appium 2.x |
| Appium | 2.x | 跨平台 WebDriver 协议 | — |
| pytest | ≥8.0 | 测试运行器 | — |
| weditor | ≥0.3 | 可视化定位器（`python -m weditor`） | — |
| adb | SDK 33+ | 设备连接/调试 | — |
| Espresso / XCUITest | — | 白盒/原生深度测试 | — |

**选型决策树**：
1. 仅 Android、追求极致稳定与速度、团队 Python 栈 → **UiAutomator2**（无 hub、直连、内置等待、weditor 可视化）
2. 必须同一套用例跑 Android + iOS、团队有 Appium 运维经验 → **Appium 2.x**（多一层 hub、跨平台一致性优先）
3. 单 App 深度白盒测试、需访问内部状态 → **Espresso (Android) / XCUITest (iOS)**
4. 游戏引擎/无控件树场景 → 见 Skill-03 (Airtest + Poco)

> 炼手建议：先跑通 `adb devices → python -m uiautomator2 init → python -m weditor` 三步，在浏览器里看到手机实时界面与控件树，再写第一个 `d(text="登录").click()`。

---

## 4. 执行步骤

### 4.1 设备连接与环境搭建（一次性）

```bash
# 1) 确认 ADB 连接
adb devices                   # 必须看到 <serial>\tdevice
# WiFi 免线模式（可选）：
# adb tcpip 5555 && adb connect 192.168.1.100:5555

# 2) 安装核心库
pip install -U --pre uiautomator2 pytest

# 3) 初始化 atx-agent（进手机，自动装 APK、开权限）
python -m uiautomator2 init

# 4) 启动可视化定位器（可选，强烈建议新手跑一次）
pip install --pre weditor
python -m weditor          # 浏览器自动打开 http://<PC_IP>:17310
```

### 4.2 最小可用工程代码（`project/app/`）

```
project/app/
├── device.py            # 设备连接管理：list_devices / connect / app_ready
├── conftest.py          # pytest fixture：device_serial / d（无设备自动 skip）
├── test_login.py        # 真机样例：坏密码报错 / 登录→加购→购物车数量
├── test_seed_app.py     # App 造数：循环“登录→加购→结算”生成 seed_count 单
├── test_ziroom_demo.py  # 实战演示：自如 App 真机用例（Tab 切换 / 登录流程）
├── requirements.txt     # uiautomator2>=3.0 pytest>=8.0
└── pyproject.toml       # pytest 配置：testpaths=["."], pythonpath=["."]
```

**关键代码片段**：

```python
# device.py —— 设备连接管理
import subprocess
import uiautomator2 as u2

def list_devices() -> list[str]:
    out = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
    return [line.split("\t")[0] for line in out.splitlines()[1:]
            if line.endswith("\tdevice")]

def connect(serial: str | None = None) -> u2.Device:
    serial = serial or (list_devices() or [None])[0]
    if not serial:
        raise RuntimeError("未发现在线 Android 设备，请检查 USB/WiFi 连接")
    d = u2.connect(serial)
    d.set_orientation("natural")       # 复位方向，避免定位漂移
    return d

def app_ready(d: u2.Device, package: str, timeout: int = 30) -> None:
    d.app_start(package)
    assert d.wait_activity(d.app_current().get("activity"), timeout=timeout), "App 未就绪"
```

```python
# conftest.py —— 设备 fixture（无设备自动 skip）
import pytest
import subprocess
import uiautomator2 as u2

def pytest_configure(config):
    config.addinivalue_line("markers", "need_device: 需要 Android 真机/模拟器")

@pytest.fixture(scope="session")
def device_serial():
    try:
        out = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
        serials = [line.split("\t")[0] for line in out.splitlines()[1:]
                   if line.endswith("\tdevice")]
        return serials[0] if serials else None
    except Exception:
        return None

@pytest.fixture(scope="session")
def d(device_serial):
    if not device_serial:
        pytest.skip("无 Android 设备，跳过 App 用例")
    dev = u2.connect(device_serial)
    dev.set_orientation("natural")
    yield dev
```

### 4.3 样例用例（可直接跑通）

```python
# test_login.py —— 真机样例（SketchStore Demo App）
import pytest
PACKAGE = "com.example.sketchstore"

@pytest.mark.need_device
def test_login_error(d):
    d(text="用户名").set_text("u_1001")
    d(text="密码").set_text("wrong-pass")
    d(text="登录").click()
    assert "密码错误" in d(text="密码错误").get_text(timeout=3)

@pytest.mark.need_device
def test_add_to_cart(d):
    d(text="用户名").set_text("u_1001")
    d(text="密码").set_text("pass_1001")
    d(text="登录").click()
    d(text="商品A").click()
    d(text="加入购物车").click()
    assert d(text="购物车(1)").exists(timeout=3)
```

```python
# test_seed_app.py —— App 造数：批量下单铺底数据
@pytest.mark.need_device
def test_seed_orders_app(d, seed_count=5):
    for i in range(seed_count):
        user = f"seed_user_{i}"
        d.app_start(PACKAGE)
        d(text="用户名").set_text(user)
        d(text="密码").set_text("pass_0000")
        d(text="登录").click()
        d(text="商品A").click()
        d(text="加入购物车").click()
        d(text="结算").click()
        assert d(textContains="订单号").exists(timeout=5), f"第 {i} 单下单失败"
```

### 4.4 跨平台写法对比：UiAutomator2 vs Appium 2.x

| 环节 | UiAutomator2 | Appium 2.x |
|---|---|---|
| 连接 | `u2.connect(serial)` | `webdriver.Remote(hub, caps)` |
| 定位 | `d(text="登录")` | `driver.find_element(By.XPATH, '//*[@text="登录"]')` |
| 输入 | `d(text="密码").set_text(...)` | `element.send_keys(...)` |
| 等待 | 内置 `timeout=` 参数 | 需显式 `WebDriverWait` |

```python
# Appium 等价写法（同一用例，供对照）
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy

caps = {"platformName": "Android", "appPackage": "com.example.sketchstore",
        "appActivity": ".MainActivity", "automationName": "UiAutomator2"}
driver = webdriver.Remote("http://127.0.0.1:4723", caps)
driver.find_element(AppiumBy.XPATH, '//*[@text="用户名"]').send_keys("u_1001")
driver.find_element(AppiumBy.XPATH, '//*[@text="登录"]').click()
```

> **结论**：Android 单端用 UiAutomator2（少一层 hub，更快更稳）；双端复用用例用 Appium（多一层服务器、跨平台一致性优先）。

### 4.5 实战演示：自如 App 真机用例

```python
# test_ziroom_demo.py
import pytest
PACKAGE = "com.ziroom.ziroomcustomer"

@pytest.mark.need_device
def test_ziroom_tab_switch(d):
    d(resourceId="com.ziroom.ziroomcustomer:id/tv_tab_jfk").click()  # 服务
    assert d(text="服务").exists(timeout=3)
    d(resourceId="com.ziroom.ziroomcustomer:id/tv_tab_mine").click()  # 我的
    assert d(text="登录/注册").exists(timeout=3)

@pytest.mark.need_device
def test_ziroom_login_flow(d):
    d(text="登录/注册").click()
    d(text="请输入用户名/手机号/邮箱").set_text("18210992070")
    d(text="获取验证码").click()
    # 此处需真实短信验证码，CI 中可用 Mock 服务或跳过
```

### 4.6 常见坑与规避

| 坑 | 症状 | 规避 |
|---|---|---|
| atx-agent 断连 | 用例中途 `ConnectionResetError` | `d.healthcheck()` 心跳；CI 前跑 `python -m uiautomator2 init` 重装 |
| 定位漂移 | 升级 App 后 `resourceId` 变 | 与研发约定关键控件 `resourceId` 不变；WEditor 导出 selector 入版本库 |
| 横竖屏切换 | 定位坐标偏移 | `d.set_orientation("natural")` 强制竖屏；fixture 中复位 |
| 并发造数冲突 | 多设备同账号下单失败 | 数据池 Provider 分配唯一账号（见 §2.4.2） |
| Toast/弹窗干扰 | 点击穿透/被遮挡 | `d(text="允许").exists(timeout=2): d(text="允许").click()` 统一处理权限弹窗 |

---

## 5. 输出契约（Output Contract）

| 产物 | 说明 |
|---|---|
| `project/app/` 工程目录 | device.py / conftest.py / test_login.py / test_seed_app.py / test_ziroom_demo.py |
| 运行证明 | 真机/模拟器跑通 `test_login.py`、`test_seed_app.py`（`-m need_device`） |
| 测试报告 | Allure/JUnit XML（CI 聚合），失败自动截图（需自行集成 `d.screenshot()`） |
| 造数数据 | `seed_user_{i}` 账号批量下单，订单号可通过接口校验 |
| 设备管理能力 | `device.py:list_devices()` 可扩展为设备池，接入平台调度（Skill-04） |

**验收前必须能当面演示**：
```bash
# 1) 确认设备在线
adb devices

# 2) 初始化 atx-agent（首次必跑）
python -m uiautomator2 init

# 3) 跑通样例用例（需真机/模拟器）
pytest project/app/test_login.py -v -m need_device
# test_login_error PASSED
# test_add_to_cart PASSED

# 4) 造数样例
pytest project/app/test_seed_app.py -v -m need_device --seed_count=10
```

---

## 6. 验收清单（Acceptance Checklist）

- [ ] `adb devices` 可见设备；`python -m uiautomator2 init` 完成 atx-agent 安装
- [ ] `pytest test_login.py -v -m need_device` 跑通"登录报错"与"登录→加购→购物车"
- [ ] `pytest test_seed_app.py -v -m need_device --seed_count=10` 批量造数成功，订单号可校验
- [ ] `pytest test_ziroom_demo.py -v -m need_device` 自如 App Tab 切换/登录流程定位通过
- [ ] 跨平台写法对比文档已落库（UiAutomator2 vs Appium 同一语义两套写法）
- [ ] 常见坑规避文档已落库（atx-agent 断连、定位漂移、横竖屏、并发冲突、Toast 干扰）
- [ ] `device.py:list_devices()` 可直接接入平台调度（Skill-04）

---

## 7. 常见坑点（Pitfalls）——详细排查表

| 现象 | 根因 | 快速修复 | 预防 |
|---|---|---|---|
| `u2.connect()` 超时 | atx-agent 未装 / 端口占用 | `python -m uiautomator2 init`；检查 7912/5037 端口 | CI 前强制重装 `init` |
| `element not found` | App 升级 `resourceId` 变更 | WEditor 重新采集 selector 入版本库 | 研发约定关键 `resourceId` 不变 |
| 横屏导致坐标偏移 | `d.click(x,y)` 绝对坐标 | 全用语义定位 `d(text="...")`；fixture 强制 `natural` | 禁止绝对坐标点击 |
| 多设备同账号下单冲突 | 唯一键约束 | 数据池 Provider 分配唯一 `seed_user_{n}` | 造数前按设备分账号池 |
| 权限弹窗遮挡点击 | `d.click()` 穿透失败 | 统一封装 `allow_if_exists(text="允许")` 前置处理 | 启动 App 后先清弹窗 |

---

## 8. 能力等级（L1-L4）

| 等级 | 表现 |
|---|---|
| L1 | 能 `adb devices`、`uiautomator2 init`、跑通 `test_login.py` 样例，理解 `d(text="...")` 语义定位 |
| L2 | 能写 `test_seed_app.py` 造数循环、处理 atx-agent 断连、配置 `-m need_device` 跳过无设备 CI、对接数据池 Provider |
| L3 | 能封装通用 `device.py`/`conftest.py` 模板给多项目复用、编写跨平台对比文档、设计 Appium 降级方案、设计设备池接入平台 |
| L4 | 能搭建企业级移动端自动化平台：设备池管理（USB Hub/云真机）、并发调度、报告聚合、与研发约定 `resourceId` 治理流程、iOS 真机云集成 |

---

## 9. 附：最小可运行示例（UI）

```bash
# 1) 确认设备在线
adb devices

# 2) 初始化 atx-agent（首次必跑）
python -m uiautomator2 init

# 3) 跑通登录+加购样例
pytest project/app/test_login.py -v -m need_device

# 4) 批量造数 10 单
pytest project/app/test_seed_app.py -v -m need_device --seed_count=10
```

---

*参考：第 2 章 §2.2 App 自动化、project/app/ 工程、被测应用设计手稿.md（8 步业务链路）、Skill-16 多协议性能脚本构建（同模板）*