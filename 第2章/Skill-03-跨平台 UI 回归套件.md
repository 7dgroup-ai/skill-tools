# Skill-03-跨平台 UI 回归套件

> **能力名称**：跨平台 UI 回归套件（Airtest + Poco：图像识别 + 控件定位双模，适配 Unity/Cocos/原生 Android/iOS）
> **生命周期阶段**：构建
> **资产来源**：第 2 章 §2.3 跨平台回归；project/app/airtest_login.py；Airtest 官方文档 + Poco 多引擎驱动
> **文档版本**：v1.0 | 维护者：李文 | 更新日期：2026-08-06

---

## 0. 一句话定位

当业务跑在 Web / Android / iOS / 游戏引擎（Unity/Cocos）等多个端时，提供一个"跨引擎、跨端"的回归方案——Airtest 图像识别兜底 + Poco 控件定位优先，非主线必选，按需接入。

---

## 1. 触发场景（何时调用）

- [ ] 业务同时分发在 Web / Android / iOS / Unity / Cocos 等多端，需一套回归套件覆盖所有端
- [ ] 目标端无标准控件树（Unity/Cocos 游戏、Canvas 绘制、WebView 混合、原生绘制），常规控件定位失效
- [ ] 需要"控件优先、图像兜底"的双模策略：有控件树用 Poco，无控件树退化为 Airtest 图像识别
- [ ] 团队已有单端自动化（Skill-01/02），需补齐跨端回归能力，**非主线必选**，按需接入

> 不需要此 Skill 的场景：仅单端 Web（用 Skill-01）、仅单端 Android/iOS 原生（用 Skill-02）、所有端均有完整控件树可用 Poco 直接定位（直接用 Skill-01/02 的 Poco 模式即可）。

---

## 2. 输入契约（Input Contract）

| 项 | 必备/可选 | 说明 |
|---|---|---|
| 目标端应用包 | 必备 | `.apk` / `.ipa` / Unity/Cocos 导出包，或已安装在设备上的包名 |
| 设备/模拟器环境 | 必备 | Android（adb）、iOS（Xcode + WebDriverAgent）、Windows/macOS（Airtest 支持） |
| 基线截图素材 | 必备 | 图像识别所需的 `login_ok.png` 等基线图，需在目标分辨率真机上截取 |
| Python 环境 | 必备 | Python 3.10+，可安装 `airtest`、`pocoui`、`pocoui2` |
| Poco SDK 注入（可选） | 可选 | Unity/Cocos 原生需集成 Poco SDK 才能走控件树 |

**入口检查清单**：
- [ ] 目标设备 `adb devices` / iOS `idevice_id -l` 可见
- [ ] `pip install airtest pocoui` 无报错
- [ ] `airtest run airtest_login.py --device Android:///` 能启动应用
- [ ] 明确"何时用 Poco、何时用 Airtest"的判据（见 §3 适配策略）

---

## 3. 工具链（Toolchain）

| 工具 | 版本 | 角色 | 备选 |
|---|---|---|---|
| Airtest | ≥1.2.10 | 图像识别引擎 + 录制/回放/报告 | — |
| Poco | ≥2.0.0 | 跨引擎控件树定位（PocoSDK 注入） | — |
| pocoui / pocoui2 | — | Android/iOS 原生 Poco 驱动 | — |
| Unity/Cocos Poco SDK | — | 游戏引擎控件树注入 | — |
| adb / idevice_id | — | 设备连接 | — |
| weditor / AirtestIDE | — | 可视化录制/调试/截图 | — |

**适配策略（核心决策树）**：
| 目标端 | 是否有控件树 | 推荐方案 | 备注 |
|---|---|---|---|
| 原生 Android | 是（UIAutomator） | `AndroidUiautomationPoco` | 走控件树，稳定优先 |
| 原生 iOS | 是（XCUITest） | `PocoIOSDriver` | 需 Xcode + WebDriverAgent |
| Unity | 是（PocoSDK 注入） | `PocoUnityDriver` | 需在 Unity 工程集成 PocoSDK |
| Cocos | 是（PocoSDK 注入） | `PocoCocosDriver` | 同上 |
| WebView / Canvas / 原生绘制 / 无 SDK | 否 | **Airtest 图像识别** | 截图基线 `Template("login_ok.png")`，锁定分辨率 |

> **原则**：**控件优先、图像兜底**。只有当控件树拿不到（Canvas/视频流/第三方 SDK 内嵌 WebView/未注入 PocoSDK）才用图像识别，并锁定分辨率基线。

---

## 4. 执行步骤

### 4.1 环境准备

```bash
# 1) 安装核心库
pip install airtest pocoui

# 2) 安装 AirtestIDE（可视化录制/调试，可选）
# 下载：https://airtest.netease.com/
# 支持可视化录制、脚本编辑、报告查看

# 3) 设备连接
# Android:
adb devices
# iOS (需 Xcode + WebDriverAgent):
idevice_id -l
```

### 4.2 Airtest + Poco 脚手架搭建（`project/app/airtest_login.py`）

```python
# project/app/airtest_login.py
from airtest.core.api import connect_device, start_app, assert_exists
from poco.drivers.android.uiautomation import AndroidUiautomationPoco

# 1) 连接设备（走 adb）
connect_device("Android:///")

# 2) 启动目标 App
start_app("com.example.sketchstore")

# 3) 初始化 Poco（控件定位）
poco = AndroidUiautomationPoco()

# 4) 控件定位 + 操作（Poco 优先）
poco(text="用户名").set_text("u_1001")    # Poco：控件定位
poco(text="密码").set_text("pass_1001")
poco(text="登录").click()

# 5) 图像断言（Airtest 兜底）
# login_ok.png 需在真机上截图生成（`airtest report` 支持导出）
# 分辨率必须与录制时一致，建议锁定 1080x1920 或 720x1280
assert_exists(Template("login_ok.png"))
```

> **备注**：`login_ok.png` 等基线图需在目标分辨率真机上截图生成（`airtest report` 支持导出）。本项目提供代码骨架，图像素材按设备分辨率现场生成。

### 4.3 跨引擎适配：Unity / Cocos / 原生 Android / iOS

```python
# 不同引擎的 Poco 初始化方式
# 1) 原生 Android
from poco.drivers.android.uiautomation import AndroidUiautomationPoco
poco = AndroidUiautomationPoco()

# 2) 原生 iOS
from poco.drivers.ios import PocoIOSDriver
poco = PocoIOSDriver()

# 3) Unity（需项目集成 PocoSDK）
from poco.drivers.unity3d import PocoUnityDriver
poco = PocoUnityDriver(("localhost", 5001))  # Unity 端口

# 4) Cocos（需项目集成 PocoSDK）
from poco.drivers.cocos import PocoCocosDriver
poco = PocoCocosDriver(("localhost", 5001))

# 5) 通用写法（自动识别）
from poco.drivers.std import StdPoco
poco = StdPoco()  # 自动探测平台
```

| 引擎/平台 | Poco 驱动 | 要点 |
|---|---|---|
| Unity | `PocoUnityDriver` | 走 UI 树（Poco SDK 注入），需 Unity 项目集成 SDK |
| Cocos | `PocoCocosDriver` | 同上 |
| 原生 Android | `AndroidUiautomationPoco` | 走 UIAutomator 控件树，无需额外集成 |
| iOS | `PocoIOSDriver` | 需 Xcode 环境 + WebDriverAgent |

### 4.4 图像识别 vs 控件定位：何时选图像、何时选控件

| 判据 | 图像识别（Airtest） | 控件定位（Poco/selector） |
|---|---|---|
| 稳定性 | 受分辨率/主题/缩放影响 | 稳定（基于控件树属性） |
| 可读性 | 低（看图） | 高（看代码/selector） |
| 适用场景 | 原生绘制、无法注入的端 | 有控件树的端（原生/Unity/Cocos 注入 SDK） |
| 推荐优先级 | 兜底 | 首选 |

> **核心原则**：**控件优先、图像兜底**。只有当控件树拿不到（Canvas/视频流/第三方 SDK 内嵌 WebView/未注入 PocoSDK）才用图像识别，并锁定分辨率基线。

### 4.5 运行与报告

```bash
# 1) 命令行运行
airtest run project/app/airtest_login.py --device Android:/// --log log/

# 2) 生成 HTML 报告
airtest report project/app/airtest_login.py --log_root log/ --out report/

# 3) AirtestIDE 可视化调试（推荐新手）
# 打开 AirtestIDE，导入 airtest_login.py，连接设备，点击运行/调试
```

---

## 5. 输出契约（Output Contract）

| 产物 | 说明 |
|---|---|
| `project/app/airtest_login.py` | 跨端登录回归骨架代码 |
| 基线截图集 | `login_ok.png` 等，按分辨率目录存放（如 `1080x1920/`） |
| Airtest 报告 | HTML 报告含步骤截图、耗时、通过/失败 |
| 跨引擎适配表 | Unity/Cocos/Android/iOS 四端 Poco 初始化代码片段 |
| 选型决策表 | 图像识别 vs 控件定位判据表 |

**验收前必须能当面演示**：
```bash
# Android 原生端跑通
airtest run project/app/airtest_login.py --device Android:/// --log log/
# 报告中 assert_exists(Template("login_ok.png")) 通过

# Unity/Cocos 端（需对应环境）
airtest run project/app/airtest_unity.py --device Unity:/// --log log/
```

---

## 6. 验收清单（Acceptance Checklist）

- [ ] `airtest run airtest_login.py --device Android:///` 跑通：启动 App → 输入账号密码 → 点击登录 → 图像断言通过
- [ ] `AndroidUiautomationPoco` 控件定位成功：`poco(text="用户名").set_text(...)` 无报错
- [ ] 图像基线 `login_ok.png` 在目标分辨率真机上截制，`assert_exists` 通过
- [ ] Unity/Cocos/Android/iOS 四端 Poco 初始化代码片段已落库（见 §4.3）
- [ ] 图像识别 vs 控件定位判据表已落库（见 §4.4），新端接入时可直接对表决策
- [ ] `airtest report` 生成的 HTML 报告可查看：步骤截图、耗时、通过/失败

---

## 7. 常见坑点（Pitfalls）

| 现象 | 原因 | 排查 |
|---|---|---|
| 图像识别失败 | 分辨率/主题/缩放与基线不一致 | 锁定分辨率基线；同一设备同一分辨率下截基线；避免跨设备复用图像 |
| `Template` 匹配慢 | 图像大/全屏匹配 | 裁剪关键区域；设置 `threshold=0.8`；用 `target_pos` 限定搜索区域 |
| Poco 连接超时 | atx-agent/WD Agent 未就绪 | 先 `d.healthcheck()` 或等待 `poco.agent.alive`；重启 atx-agent |
| Unity/Cocos 无控件树 | 未集成 PocoSDK | Unity/Cocos 工程必须集成 PocoSDK 并开启调试端口 |
| 跨分辨率复用图像 | 同一图像在不同分辨率失效 | **严禁跨分辨率复用基线图**；每分辨率一套截图 |

---

## 8. 能力等级（L1-L4）

| 等级 | 表现 |
|---|---|
| L1 | 能跑通 `airtest_login.py`，理解 `connect_device`/`start_app`/`poco`/`assert_exists` 基本流程 |
| L2 | 能根据目标端选对 Poco 驱动、截制图像基线、写出跨端登录回归、生成 Airtest 报告 |
| L3 | 能设计"控件优先、图像兜底"的双模框架、封装跨引擎 Poco 初始化工厂、建立分辨率基线管理规范 |
| L4 | 能搭建企业级跨端回归平台：基线图版本管理、多端并发调度、失败自动重试+图像重识别、接入 CI/CD 门禁 |

---

## 9. 附：最小可运行示例（Airtest + Poco）

```bash
# 1) 安装依赖
pip install airtest pocoui

# 2) 连接设备，启动 App
python -c "
from airtest.core.api import connect_device, start_app
from poco.drivers.android.uiautomation import AndroidUiautomationPoco
connect_device('Android:///')
start_app('com.example.sketchstore')
poco = AndroidUiautomationPoco()
poco(text='用户名').set_text('u_1001')
poco(text='密码').set_text('pass_1001')
poco(text='登录').click()
"
```

---

*参考：第 2 章 §2.3 跨平台回归、project/app/airtest_login.py、Airtest 官方文档、Poco 多引擎驱动文档、Skill-16 多协议性能脚本构建（同模板）*