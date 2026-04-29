# Fixture for check_api_inventory.py negative test.
# §C7 违规样例：43 条路由（上限 42）。
# 扫描期望 exit 1。
#
# 注意：这是 fixture，不会被真正挂载到 FastAPI 应用。
from fastapi import APIRouter

router = APIRouter()


@router.get("/api/r01")
def r01(): pass
@router.get("/api/r02")
def r02(): pass
@router.get("/api/r03")
def r03(): pass
@router.get("/api/r04")
def r04(): pass
@router.get("/api/r05")
def r05(): pass
@router.get("/api/r06")
def r06(): pass
@router.get("/api/r07")
def r07(): pass
@router.get("/api/r08")
def r08(): pass
@router.get("/api/r09")
def r09(): pass
@router.get("/api/r10")
def r10(): pass
@router.post("/api/r11")
def r11(): pass
@router.post("/api/r12")
def r12(): pass
@router.post("/api/r13")
def r13(): pass
@router.post("/api/r14")
def r14(): pass
@router.post("/api/r15")
def r15(): pass
@router.post("/api/r16")
def r16(): pass
@router.post("/api/r17")
def r17(): pass
@router.post("/api/r18")
def r18(): pass
@router.post("/api/r19")
def r19(): pass
@router.post("/api/r20")
def r20(): pass
@router.put("/api/r21")
def r21(): pass
@router.put("/api/r22")
def r22(): pass
@router.put("/api/r23")
def r23(): pass
@router.put("/api/r24")
def r24(): pass
@router.put("/api/r25")
def r25(): pass
@router.put("/api/r26")
def r26(): pass
@router.put("/api/r27")
def r27(): pass
@router.put("/api/r28")
def r28(): pass
@router.put("/api/r29")
def r29(): pass
@router.put("/api/r30")
def r30(): pass
@router.delete("/api/r31")
def r31(): pass
@router.delete("/api/r32")
def r32(): pass
@router.delete("/api/r33")
def r33(): pass
@router.delete("/api/r34")
def r34(): pass
@router.delete("/api/r35")
def r35(): pass
@router.delete("/api/r36")
def r36(): pass
@router.delete("/api/r37")
def r37(): pass
@router.delete("/api/r38")
def r38(): pass
@router.delete("/api/r39")
def r39(): pass
@router.delete("/api/r40")
def r40(): pass
@router.patch("/api/r41")
def r41(): pass
@router.patch("/api/r42")
def r42(): pass
@router.patch("/api/r43")  # ← 第 43 条，超限
def r43(): pass
