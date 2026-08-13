"""App 用例共建设备 fixture：无设备自动 skip。"""

import pytest

from device import app_ready, connect, device_available

PACKAGE = "com.example.sketchstore"   # 替换为你被测 App 的包名


@pytest.fixture(scope="module")
def d():
    if not device_available():
        pytest.skip("无 Android 设备，跳过 App 用例")
    dev = connect()
    app_ready(dev, PACKAGE)
    yield dev
