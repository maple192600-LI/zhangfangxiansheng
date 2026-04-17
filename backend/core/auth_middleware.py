"""认证中间件 — 拦截 /api 请求验证 JWT token"""
from starlette.requests import Request
from starlette.responses import JSONResponse

from services.auth_service import decode_token

# 不需要认证的路径
EXCLUDE_PATHS = {"/api/auth/login", "/api/health", "/api/accounts/template"}


async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # 非 /api 路径直接放行（静态资源、SPA 路由兜底）
    if not path.startswith("/api"):
        return await call_next(request)

    # 认证白名单路径放行
    if path in EXCLUDE_PATHS:
        return await call_next(request)

    # OPTIONS 预检请求放行
    if request.method == "OPTIONS":
        return await call_next(request)

    # 提取 Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"code": 6003, "message": "未提供认证令牌", "data": None},
        )

    token = auth_header[7:]
    payload = decode_token(token)
    if payload is None:
        return JSONResponse(
            status_code=401,
            content={"code": 6002, "message": "认证令牌无效或已过期", "data": None},
        )

    # 将用户信息注入 request.state 供后续使用
    request.state.user = payload
    return await call_next(request)
