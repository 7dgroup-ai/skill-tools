"""手机端连接管理：USB/WiFi adb + 设备就绪检查。

uiautomator2 为可选依赖，未安装或未连接设备时相关函数自动降级。
"""

from __future__ import annotations

import subprocess


def adb_devices() -> list[str]:
    """adb devices 列出已连接设备序列号（含模拟器）。"""
    try:
        out = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    return [line.split("\t")[0] for line in out.splitlines()[1:]
            if line.endswith("\tdevice")]


def device_available() -> bool:
    """是否有可用 Android 设备（测试入口的跳过判定）。"""
    return bool(adb_devices())


def connect(serial: str | None = None):
    """连接设备；serial 为空时自动选第一个在线设备。

    返回 uiautomator2.Device。未安装 uiautomator2 或无线设备时抛 RuntimeError。
    """
    import uiautomator2 as u2   # 懒加载，保持模块可导入

    serial = serial or (adb_devices() or [None])[0]
    if not serial:
        raise RuntimeError("未发现在线 Android 设备，请检查 USB/WiFi 连接")
    d = u2.connect(serial)
    d.set_orientation("natural")          # 复位方向，避免定位漂移
    return d


def app_ready(d, package: str, timeout: int = 30) -> None:
    """启动目标 App 并等待其前台可操作。"""
    d.app_start(package)
    assert d.wait_activity(d.app_current().get("activity"), timeout=timeout), "App 未就绪"


def connect_wifi(ip: str, port: int = 5555) -> None:
    """WiFi 连接：测试机与设备需同一网段。"""
    subprocess.run(["adb", "connect", f"{ip}:{port}"], check=True)
