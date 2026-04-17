"""认证 API — 登录/修改密码/当前用户"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from core.response import success, error
from services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


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
def login(body: LoginRequest, db: Session = Depends(get_db)):
    result = auth_service.authenticate(db, body.username, body.password)
    if not result:
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
