"""脚本执行工具 — 受限的 Python 代码执行"""
import io
import sys
import traceback

from agents.tool_registry import register_tool, ToolContext

# 白名单内建函数 — 仅允许安全的操作
_SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
    "chr": chr, "dict": dict, "divmod": divmod, "enumerate": enumerate,
    "filter": filter, "float": float, "format": format, "frozenset": frozenset,
    "hash": hash, "hex": hex, "int": int, "isinstance": isinstance,
    "issubclass": issubclass, "iter": iter, "len": len, "list": list,
    "map": map, "max": max, "min": min, "next": next, "oct": oct,
    "ord": ord, "pow": pow, "print": print, "range": range, "repr": repr,
    "reversed": reversed, "round": round, "set": set, "slice": slice,
    "sorted": sorted, "str": str, "sum": sum, "tuple": tuple,
    "type": type, "zip": zip,
    "True": True, "False": False, "None": None,
    "ValueError": ValueError, "TypeError": TypeError, "KeyError": KeyError,
    "IndexError": IndexError, "RuntimeError": RuntimeError,
    "AttributeError": AttributeError, "StopIteration": StopIteration,
    "Exception": Exception,
}

_DENIED_MODULES = frozenset({
    "os", "sys", "subprocess", "socket", "http", "urllib", "requests",
    "shutil", "signal", "ctypes", "multiprocessing", "threading",
    "importlib", "pickle", "shelve", "code", "codeop", "compile",
    "builtins", "globals", "locals", "eval", "exec", "compile",
    "__import__", "open", "input", "breakpoint", "exit", "quit",
})


@register_tool(read_only=False, concurrent_safe=False)
def python_exec(code: str, ctx: ToolContext = None) -> dict:
    """在受限沙箱中执行 Python 代码并返回输出。

    使用场景：
    - 数据计算和转换（金额汇总、日期计算等）
    - 验证数据一致性（余额校验等）
    - 复杂的数据处理逻辑

    限制：
    - 无法访问文件系统（无 open、os、sys）
    - 无法访问网络（无 requests、urllib）
    - 可用标准库：math、json、datetime、re、collections 等
    - 可用第三方库：polars（如已安装）

    参数：code 必需，Python 代码字符串。
    返回：{"ok": true, "output": "标准输出", "variables": {"变量名": "值"}} 或 {"ok": false, "error": "错误信息"}
    """
    # 安全检查：拦截危险关键字
    _DANGEROUS_PATTERNS = [
        "__import__", "import os", "import sys", "import subprocess",
        "from os", "from sys", "open(", "exec(", "eval(",
        "getattr", "__class__", "__subclasses__", "__builtins__",
        "compile(", "__code__",
    ]
    code_lower = code.lower()
    for pattern in _DANGEROUS_PATTERNS:
        if pattern.lower() in code_lower:
            return {"ok": False, "error": f"沙箱拒绝执行：代码包含受限操作 '{pattern}'"}

    local_vars: dict = {}

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    sys.stdout = stdout_buf
    sys.stderr = stderr_buf

    try:
        exec(code, {"__builtins__": _SAFE_BUILTINS}, local_vars)
        output = stdout_buf.getvalue()
        error_output = stderr_buf.getvalue()
        return {
            "ok": True,
            "output": output[-3000:] if len(output) > 3000 else output,
            "stderr": error_output[-1000:] if error_output else "",
            "variables": {
                k: str(v)[:200]
                for k, v in local_vars.items()
                if not k.startswith("_")
            },
        }
    except Exception:
        tb = traceback.format_exc()
        return {"ok": False, "error": tb[-2000:]}
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
