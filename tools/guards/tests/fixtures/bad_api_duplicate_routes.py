# Fixture for check_api_inventory.py negative test.
# 包含重复 effective path：两个 GET /api/duplicate。
# 扫描期望 exit 1。
#
# 注意：这是 fixture，不会被真正挂载到 FastAPI 应用。
from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/duplicate")
def first():
    pass


@router.get("/duplicate")
def second():
    pass


@router.get("/unique")
def unique():
    pass
