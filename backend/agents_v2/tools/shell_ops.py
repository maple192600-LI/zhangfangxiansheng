"""脚本执行工具 — 受限的 Python 代码执行"""
import io
import sys
import traceback

from agents_v2.tool_registry import register_tool, ToolContext

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
    """执行一段 Python 代码并返回输出。code 为 Python 代码字符串。注意：在受限沙箱环境中运行，无法访问文件系统或外部网络。"""
    # 注入工作区路径
    from agents_v2.workspace import get_agent_root
    workspace_root = get_agent_root(ctx.agent_code)

    local_vars = {
        "workspace_root": workspace_root,
        "agent_code": ctx.agent_code,
    }

    # 捕获 stdout/stderr
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
                if not k.startswith("_") and k not in ("workspace_root", "agent_code")
            },
        }
    except Exception:
        tb = traceback.format_exc()
        return {"ok": False, "error": tb[-2000:]}
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
