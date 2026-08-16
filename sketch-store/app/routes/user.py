from fastapi import APIRouter, Depends, Header, Request

from .. import latency_sim, metrics
from .. import models
from ..auth import make_token
from .deps import get_auth_token

router = APIRouter(prefix="/api", tags=["user"])


@router.post("/login")
def login(request: Request, body: dict):
    username = (body or {}).get("username", "")
    password = (body or {}).get("password", "")

    # SQL 注入演示点（全书第 11 章安全测试用）：
    # sql_injection 开关打开时，用字符串拼接构造查询（可被注入）；
    # 关闭后走参数化查询。生产环境务必关闭。
    if latency_sim.get("sql_injection"):
        import hashlib
        pwd = hashlib.sha256(password.encode()).hexdigest()
        with models.get_conn() as c:
            row = c.execute(
                f"SELECT * FROM users WHERE username = '{username}' AND password = '{pwd}'"
            ).fetchone()
    else:
        user = models.get_user_by_username(username)
        import hashlib
        pwd = hashlib.sha256(password.encode()).hexdigest()
        row = None
        if user and user["password"] == pwd:
            row = user

    if not row:
        return {"code": 1, "msg": "用户名或密码错误"}
    token = make_token(row["id"], row["username"])
    metrics.inc_business("login")
    return {"code": 0, "data": {"token": token, "username": row["username"]}}


@router.post("/switch")
def set_switch(request: Request, body: dict):
    """瓶颈开关管理接口（测试用）：
    {"switch": "latency_sim", "on": true}
    {"switch": "cache_path", "on": true}
    {"switch": "sql_injection", "on": false}
    {"switch": "latency_ms", "value": 1500}
    """
    name = (body or {}).get("switch")
    if name == "latency_ms":
        latency_sim.set_latency_ms((body or {}).get("value", 800))
    elif name:
        latency_sim.set(name, (body or {}).get("on", True))
    return {"code": 0, "data": latency_sim.switch_summary()}