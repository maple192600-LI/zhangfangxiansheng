"""认证 API — 登录/修改密码/当前用户"""
import time
from collections import defaultdict
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from core.response import success, error
from services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

# 简易登录速率限制：每 IP 每分钟最多 10 次失败尝试
_login_attempts: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_WINDOW = 60
_RATE_LIMIT_MAX = 10
_last_cleanup = time.time()
_CLEANUP_INTERVAL = 300  # 每 5 分钟清理一次过期条目


def _cleanup_stale_attempts():
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup < _CLEANUP_INTERVAL:
        return
    _last_cleanup = now
    stale = [ip for ip, ts in _login_attempts.items() if not ts or now - ts[-1] > _RATE_LIMIT_WINDOW]
    for ip in stale:
        del _login_attempts[ip]


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


def get_current_user(request: Request):
    """从 request.state 获取当前用户（由中间件注入）"""
    user = getattr(request.state, "user", None)
    if not user:
        return None
    return user


@router.post("/login")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    _cleanup_stale_attempts()
    attempts = _login_attempts[client_ip]
    _login_attempts[client_ip] = [t for t in attempts if now - t < _RATE_LIMIT_WINDOW]
    if len(_login_attempts[client_ip]) >= _RATE_LIMIT_MAX:
        return error(6005, "登录尝试过于频繁，请稍后再试")
    result = auth_service.authenticate(db, body.username, body.password)
    if not result:
        _login_attempts[client_ip].append(now)
        return error(6001, "用户名或密码错误")
    return success(result)


@router.post("/change-password")
def change_password(body: ChangePasswordRequest, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return error(6003, "未认证")
    ok, msg = auth_service.change_password(db, user["sub"], body.old_password, body.new_password)
    if not ok:
        return error(6004, msg)
    return success(None, msg)


@router.get("/me")
def get_me(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return error(6003, "未认证")
    info = auth_service.get_user_by_id(db, user["sub"])
    if not info:
        return error(6003, "用户不存在")
    return success(info)
