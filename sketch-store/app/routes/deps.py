from fastapi import Header, HTTPException

from ..auth import get_current_user


def get_auth_token(authorization: str = Header(None, alias="Authorization")):
    return authorization


def require_user(authorization: str = Header(None, alias="Authorization")):
    """依赖：解析 Bearer token，无效则 401。"""
    user = get_current_user(authorization or "")
    if not user:
        raise HTTPException(status_code=401, detail="未登录或 token 失效")
    return user