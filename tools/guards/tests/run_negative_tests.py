#!/usr/bin/env python3
"""
P0-T1 验证脚本 · 6 条负面场景
============================
每条场景调用对应 guard，期望 exit 1。全部通过 → 本脚本 exit 0。

场景清单（对应 00_v3_execution_order.md P0-T1 验证清单）:
    1. 故意改宪法 → check_contract_hash.py 拒绝
    2. 故意加第 13 列 → check_canonical_schema.py 拒绝
    3. 故意 import pandas → check_primitives_whitelist.py 拒绝
    4. 故意漏绑占位符 → check_placeholder_binding.py 拒绝
    5. 故意超 42 端点 → check_api_inventory.py 拒绝
    6. 缺 contracts.lock → check_contract_hash.py 拒绝
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools" / "guards"
FIXTURES = Path(__file__).parent / "fixtures"
PY = sys.executable


def run_guard(script: str, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [PY, str(TOOLS / script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout, proc.stderr


def expect(name: str, condition: bool, details: str = "") -> bool:
    if condition:
        print(f"  [PASS] {name}")
        return True
    print(f"  [FAIL] {name}")
    if details:
        for line in details.splitlines():
            print(f"         | {line}")
    return False


def case_1_constitution_drift() -> bool:
    """故意篡改宪法 → guard 拒绝。"""
    print("Case 1 · 篡改宪法（改动 §C1 任一字符）→ check_contract_hash 拒绝")
    constitution = ROOT / "docs" / "00_governance" / "00_project_constitution.md"
    lock = ROOT / "contracts.lock"
    original = constitution.read_bytes()
    try:
        # 追加一个空字符改变 SHA256
        constitution.write_bytes(original + b"\n# __test_drift__\n")
        code, out, err = run_guard("check_contract_hash.py", "--repo-root", str(ROOT), "--lock", str(lock))
        ok = expect("被 check_contract_hash 拒绝（exit != 0）", code != 0, out + err)
        ok &= expect("stderr 指向 §ChangeFlow 修复步骤", "ChangeFlow" in err, err)
    finally:
        constitution.write_bytes(original)
    return ok


def case_2_canonical_13col() -> bool:
    print("Case 2 · fund_events 第 13 列 → check_canonical_schema 拒绝")
    bad = FIXTURES / "bad_canonical_13col.py"
    code, out, err = run_guard("check_canonical_schema.py", "--target", str(bad))
    ok = expect("exit != 0", code != 0, out + err)
    ok &= expect("stderr 报 CANONICAL_12 不符", "CANONICAL_12" in err or "多余" in err, err)
    return ok


def case_3_primitives_escape() -> bool:
    print("Case 3 · Artifact 里 import pandas / open / eval → check_primitives_whitelist 拒绝")
    bad = FIXTURES / "bad_artifact_pandas.py"
    code, out, err = run_guard("check_primitives_whitelist.py", str(bad))
    ok = expect("exit != 0", code != 0, out + err)
    ok &= expect("stderr 列出 pandas 违规", "pandas" in err, err)
    ok &= expect("stderr 列出 open 违规", "open" in err, err)
    return ok


def case_4_placeholder_missing() -> bool:
    print("Case 4 · Rule 少绑占位符 → check_placeholder_binding 拒绝")
    bad = FIXTURES / "bad_rule_17.json"
    code, out, err = run_guard("check_placeholder_binding.py", str(bad))
    ok = expect("exit != 0", code != 0, out + err)
    ok &= expect("stderr 列出『月末余额』为缺失", "月末余额" in err, err)
    return ok


def case_5_api_over_42() -> bool:
    print("Case 5 · API 43 条 → check_api_inventory 拒绝")
    bad_dir = FIXTURES  # fixtures/ 下只有 1 个 FastAPI 文件，含 43 条路由
    # 为隔离：复制到临时目录（避免 fixtures 里其它非路由文件干扰，此处实际仅 .py fixture 全是纯函数或 bad_artifact_pandas.py 含 0 路由）
    code, out, err = run_guard("check_api_inventory.py", "--target", str(bad_dir))
    ok = expect("exit != 0（43 > 42）", code != 0, out + err)
    ok &= expect("stderr 报超限", "42" in err, err)
    return ok


def case_6_missing_lock() -> bool:
    print("Case 6 · contracts.lock 缺失 → check_contract_hash 拒绝")
    with tempfile.TemporaryDirectory() as tmp:
        fake_repo = Path(tmp)
        # 伪造 docs/00_governance/00_project_constitution.md
        const_dir = fake_repo / "docs" / "00_governance"
        const_dir.mkdir(parents=True)
        (const_dir / "00_project_constitution.md").write_text("# fake", encoding="utf-8")
        # 不创建 contracts.lock
        code, out, err = run_guard(
            "check_contract_hash.py",
            "--repo-root", str(fake_repo),
            "--lock", str(fake_repo / "contracts.lock"),
        )
        ok = expect("exit != 0", code != 0, out + err)
        ok &= expect("stderr 提示 --update", "--update" in err, err)
    return ok


POSITIVE = [
    ("Positive · ok_canonical 12 列通过", "check_canonical_schema.py", ["--target", str(FIXTURES / "ok_canonical.py")]),
    ("Positive · ok_artifact 白名单通过", "check_primitives_whitelist.py", [str(FIXTURES / "ok_artifact.py")]),
    ("Positive · ok_rule_18 绑定通过", "check_placeholder_binding.py", [str(FIXTURES / "ok_rule_18.json")]),
    ("Positive · contracts.lock 现状通过", "check_contract_hash.py", ["--repo-root", str(ROOT), "--lock", str(ROOT / "contracts.lock")]),
]


def run_positives() -> bool:
    print("\n--- Positive sanity checks ---")
    all_ok = True
    for name, script, args in POSITIVE:
        code, out, err = run_guard(script, *args)
        passed = code == 0
        all_ok &= expect(name, passed, (out + err) if not passed else "")
    return all_ok


def main() -> int:
    print("=" * 60)
    print("P0-T1 · 6 条负面场景 + 4 条正面场景")
    print("=" * 60)

    results: list[bool] = []
    for fn in [
        case_1_constitution_drift,
        case_2_canonical_13col,
        case_3_primitives_escape,
        case_4_placeholder_missing,
        case_5_api_over_42,
        case_6_missing_lock,
    ]:
        results.append(fn())
        print()

    results.append(run_positives())

    total = len(results)
    passed = sum(1 for r in results if r)
    print()
    print("=" * 60)
    print(f"  RESULT · {passed}/{total} groups passed")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
