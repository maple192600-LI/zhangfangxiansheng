"""认证服务 — 单用户 JWT 认证"""
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from config import SECRET_KEY, TOKEN_EXPIRE_MINUTES
from db.tables import User


def hash_password(plain: str) -> str:
    """密码哈希（bcrypt）"""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_token(user_id: int, username: str) -> str:
    """签发 JWT"""
    payload = {
        "sub": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    """解码验证 JWT，过期或无效返回 None"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_or_create_default_user(db: Session) -> User:
    """获取或创建默认 admin 用户"""
    user = db.query(User).first()
    if user:
        return user
    user = User(
        username="admin",
        password_hash=hash_password("admin123"),
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    import logging
    logging.getLogger(__name__).warning(
        "已创建默认用户 admin，首次登录后请立即修改密码"
    )
    return user


def authenticate(db: Session, username: str, password: str) -> Optional[dict]:
    """验证登录，成功返回 {token, user}，失败返回 None"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    token = create_token(user.id, user.username)
    return {
        "token": token,
        "user": {"id": user.id, "username": user.username, "must_change_password": getattr(user, "must_change_password", False)},
    }


def change_password(db: Session, user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
    """修改密码，返回 (成功标志, 消息)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False, "用户不存在"
    if not verify_password(old_password, user.password_hash):
        return False, "原密码错误"
    if old_password == new_password:
        return False, "新密码不能与原密码相同"
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.updated_at = datetime.now()
    db.commit()
    return True, "密码修改成功"


def get_user_by_id(db: Session, user_id: int) -> Optional[dict]:
    """按 ID 查用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    return {"id": user.id, "username": user.username}
