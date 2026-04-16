"""健康检查接口"""
from fastapi import APIRouter

from core.response import success

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return success(data={"status": "running"})
