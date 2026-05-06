"""技能安全扫描器 — 对标 Hermes skills_guard

信任级别：
  - builtin: 随产品发布，不扫描
  - trusted: 已知可靠来源，扫描但仅阻止 critical
  - community: 未知来源，扫描发现 critical/high 都阻止
  - agent_created: Agent 自己创建，默认不扫描

威胁模式库覆盖：数据泄露、注入攻击、破坏性操作、持久化、网络通信、混淆
同时支持正则扫描 + Python AST 扫描。
"""
import ast
import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class TrustLevel(str, Enum):
    BUILTIN = "builtin"
    TRUSTED = "trusted"
    COMMUNITY = "community"
    AGENT_CREATED = "agent_created"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ── 旧版兼容接口（供 test_skill_scanner.py 和 skill_installer.py 使用） ────

@dataclass
class ScanRule:
    rule_id: str
    severity: str
    pattern: re.Pattern
    description: str


@dataclass
class ScanFinding:
    rule_id: str
    severity: str
    file_path: str
    line_number: int
    line_content: str
    description: str


@dataclass
class ScanReport:
    safe: bool
    findings: list[ScanFinding] = field(default_factory=list)
    scanned_files: int = 0
    total_lines: int = 0


# ── 增强版数据结构 ──────────────────────────────────────────

@dataclass
class Finding:
    rule_id: str
    severity: Severity
    message: str
    file: str = ""
    line: int = 0
    match_text: str = ""


@dataclass
class ScanResult:
    safe: bool = True
    findings: list[Finding] = field(default_factory=list)
    trust_level: TrustLevel = TrustLevel.COMMUNITY
    scanned_files: int = 0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)


# ── 威胁模式库 ──────────────────────────────────────────────

_REGEX_PATTERNS: list[tuple[str, str, Severity, str]] = [
    # 数据泄露
    (r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD)', "exfil_curl_vars", Severity.CRITICAL, "通过 curl 泄露密钥变量"),
    (r'requests\.(get|post|put|patch)\s*\([^)]*(?:api_key|token|secret)', "exfil_http_secret", Severity.CRITICAL, "通过 HTTP 请求泄露密钥"),
    (r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']+["\']', "hardcoded_password", Severity.CRITICAL, "硬编码密码"),
    # 注入攻击
    (r'ignore\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions?|rules?)', "prompt_injection_ignore", Severity.HIGH, "prompt 注入：忽略指令"),
    (r'(?:disregard|forget|override)\s+(?:all\s+)?(?:previous|your)\s+(?:instructions?|rules?)', "prompt_injection_disregard", Severity.HIGH, "prompt 注入：覆盖指令"),
    (r'you\s+are\s+now\s+(?:a|an)\s+(?:unrestricted|unlimited|uncensored)', "prompt_injection_role", Severity.HIGH, "prompt 注入：角色篡改"),
    (r'(?:system|assistant|user)\s*:\s*["\']', "role_injection", Severity.MEDIUM, "角色标签注入"),
    # 破坏性操作
    (r'rm\s+-rf\s+/', "destructive_rm", Severity.CRITICAL, "递归删除根目录"),
    (r'shutil\.rmtree\s*\(\s*["\']/?["\']', "destructive_rmtree", Severity.CRITICAL, "递归删除根目录"),
    (r'format\s+[a-zA-Z]:', "destructive_format", Severity.CRITICAL, "格式化磁盘"),
    # 持久化
    (r'crontab\s+-r', "persist_crontab", Severity.HIGH, "清空 crontab"),
    # 网络通信
    (r'requests\.(get|post|put)\s*\(\s*["\']https?://', "network_request", Severity.MEDIUM, "外部网络请求"),
    (r'urllib\.request\.urlopen', "network_urllib", Severity.MEDIUM, "urllib 网络请求"),
    (r'socket\.connect', "network_socket", Severity.MEDIUM, "socket 连接"),
    # 混淆
    (r'exec\s*\(\s*(?:base64|decode|unhexlify)', "obfuscation_exec", Severity.HIGH, "exec + 解码混淆"),
    (r'eval\s*\(\s*(?:base64|decode|unhexlify)', "obfuscation_eval", Severity.HIGH, "eval + 解码混淆"),
    # 动态代码执行（保留旧规则兼容）
    (r'(?:eval\(|__import__|compile\()', "dynamic_code", Severity.CRITICAL, "动态代码执行"),
    (r'(?:exec\(|spawn|subprocess\.)', "dangerous_exec", Severity.CRITICAL, "子进程执行调用"),
    # 加密货币挖矿
    (r'(?:stratum|xmrig|coinhive|cryptonight)', "crypto_mine", Severity.CRITICAL, "加密货币挖矿"),
    # 环境变量收集+网络
    (r'os\.environ\[.+\]\s*(?:\+|f\"|\.format).*?(?:requests\.(?:post|put)|urllib)', "env_harvest", Severity.CRITICAL, "环境变量泄露到网络请求"),
    # 文件外泄
    (r'(?:open|read_file).*(?:requests\.post|fetch|urllib)', "exfiltration", Severity.HIGH, "文件读取+网络发送"),
    # 网络 shell
    (r'(?:socket\.socket|nc\s+-|netcat)', "network_shell", Severity.HIGH, "网络 shell 连接"),
]


def _scan_file_regex(filepath: str) -> list[Finding]:
    """对单个文件执行正则扫描"""
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return findings

    rel = os.path.basename(filepath)
    for line_no, line in enumerate(content.split("\n"), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # SKILL.md 中列表项跳过
        if filepath.endswith(".md") and stripped.startswith("-"):
            continue
        for pattern, rule_id, severity, desc in _REGEX_PATTERNS:
            if re.search(pattern, stripped, re.IGNORECASE):
                findings.append(Finding(
                    rule_id=rule_id,
                    severity=severity,
                    message=desc,
                    file=rel,
                    line=line_no,
                    match_text=stripped[:100],
                ))
    return findings


def _scan_python_ast(filepath: str) -> list[Finding]:
    """AST 级扫描：检测危险函数调用"""
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except Exception:
        return findings

    rel = os.path.basename(filepath)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name in ("exec", "eval") and node.args:
                arg = node.args[0]
                if isinstance(arg, (ast.Call, ast.BinOp)):
                    findings.append(Finding(
                        rule_id=f"ast_{func_name}_complex",
                        severity=Severity.HIGH,
                        message=f"AST: {func_name}() 参数包含复杂表达式",
                        file=rel,
                        line=node.lineno,
                    ))

            if func_name == "__import__":
                findings.append(Finding(
                    rule_id="ast_dynamic_import",
                    severity=Severity.MEDIUM,
                    message="AST: 动态 __import__() 调用",
                    file=rel,
                    line=node.lineno,
                ))

    return findings


# ── 增强版扫描入口 ─────────────────────────────────────────

def scan_skill_dir(
    skill_dir: str,
    trust_level: TrustLevel = TrustLevel.COMMUNITY,
    rules: list[ScanRule] = None,
) -> ScanReport:
    """扫描技能目录（兼容旧 ScanReport 接口 + 新信任级别）

    返回 ScanReport 以兼容 skill_installer.py 的调用。
    """
    result = ScanResult(trust_level=trust_level)

    if not os.path.isdir(skill_dir):
        result.safe = False
        result.findings.append(Finding(
            rule_id="dir_missing",
            severity=Severity.CRITICAL,
            message=f"技能目录不存在: {skill_dir}",
        ))
        return _result_to_report(result)

    # builtin 和 agent_created 级别不扫描
    if trust_level in (TrustLevel.BUILTIN, TrustLevel.AGENT_CREATED):
        return ScanReport(safe=True)

    scan_extensions = {".py", ".md", ".txt", ".yaml", ".yml", ".json", ".sh", ".bat", ".js", ".ts"}
    skip_dirs = {".archive", "tests", "__pycache__", ".git"}

    for root, dirs, files in os.walk(skill_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            _, ext = os.path.splitext(fname)
            if ext.lower() not in scan_extensions and fname not in ("SKILL.md",):
                continue
            filepath = os.path.join(root, fname)
            result.scanned_files += 1

            result.findings.extend(_scan_file_regex(filepath))

            if ext == ".py":
                result.findings.extend(_scan_python_ast(filepath))

    # 根据信任级别决定 safe
    if trust_level == TrustLevel.TRUSTED:
        result.safe = result.critical_count == 0
    elif trust_level == TrustLevel.COMMUNITY:
        result.safe = result.critical_count == 0 and result.high_count == 0
    else:
        result.safe = True

    return _result_to_report(result)


def _result_to_report(result: ScanResult) -> ScanReport:
    """将 ScanResult 转换为旧版 ScanReport"""
    report = ScanReport(safe=result.safe, scanned_files=result.scanned_files)
    for f in result.findings:
        report.findings.append(ScanFinding(
            rule_id=f.rule_id,
            severity=f.severity.value,
            file_path=f.file,
            line_number=f.line,
            line_content=f.match_text,
            description=f.message,
        ))
    return report


# ── 旧版兼容函数 ────────────────────────────────────────────

def scan_file(file_path: str, rules: list[ScanRule] = None) -> list[ScanFinding]:
    """扫描单个文件（旧版接口）"""
    if rules is None:
        rules = RULES
    findings = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return findings

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for rule in rules:
            if rule.pattern.search(stripped):
                if file_path.endswith(".md") and stripped.startswith("-"):
                    continue
                findings.append(ScanFinding(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    file_path=file_path,
                    line_number=line_num,
                    line_content=stripped[:120],
                    description=rule.description,
                ))
    return findings


# 旧版规则列表（保留兼容）
RULES: list[ScanRule] = [
    ScanRule("dangerous-exec", "critical", re.compile(r"(?:exec\(|spawn|subprocess\.)", re.IGNORECASE), "子进程执行调用"),
    ScanRule("dynamic-code", "critical", re.compile(r"(?:eval\(|__import__|compile\()", re.IGNORECASE), "动态代码执行"),
    ScanRule("env-harvest", "critical", re.compile(r'os\.environ\[.+\]\s*(?:\+|f\"|\.format).*?(?:requests\.(?:post|put)|urllib)', re.IGNORECASE), "环境变量泄露到网络请求"),
    ScanRule("crypto-mine", "critical", re.compile(r"(?:stratum|xmrig|coinhive|cryptonight)", re.IGNORECASE), "加密货币挖矿"),
    ScanRule("exfiltration", "high", re.compile(r"(?:open|read_file|file_get_contents).*(?:requests\.post|fetch|urllib)", re.IGNORECASE), "文件读取+网络发送"),
    ScanRule("network-shell", "high", re.compile(r"(?:socket\.socket|nc\s+-|netcat)", re.IGNORECASE), "网络 shell 连接"),
]


def format_report(report) -> str:
    """格式化扫描报告（兼容 ScanReport 和 ScanResult）"""
    if isinstance(report, ScanResult):
        return _format_scan_result(report)
    # 旧版 ScanReport
    if not report.findings:
        return f"扫描完成：{report.scanned_files} 个文件，未发现安全问题"
    lines = [f"扫描完成：{report.scanned_files} 个文件，发现 {len(report.findings)} 个问题"]
    lines.append(f"安全状态：{'通过' if report.safe else '不安全'}")
    lines.append("")
    for f in report.findings:
        lines.append(
            f"[{f.severity.upper()}] {f.rule_id}: {f.description}\n"
            f"  文件: {f.file_path}:{f.line_number}\n"
            f"  内容: {f.line_content}"
        )
    return "\n".join(lines)


def _format_scan_result(result: ScanResult) -> str:
    """增强版报告格式"""
    lines = [
        f"安全扫描结果: {'通过' if result.safe else '未通过'}",
        f"信任级别: {result.trust_level.value}",
        f"扫描文件: {result.scanned_files}",
        f"发现问题: {len(result.findings)} (critical={result.critical_count}, high={result.high_count})",
        "",
    ]
    for finding in result.findings:
        lines.append(
            f"  [{finding.severity.value}] {finding.rule_id}: {finding.message}"
        )
        if finding.file:
            lines.append(f"    文件: {finding.file}:{finding.line}")
            if finding.match_text:
                lines.append(f"    匹配: {finding.match_text}")
    return "\n".join(lines)


# ── 内容哈希工具 ────────────────────────────────────────────

def compute_content_hash(skill_dir: str) -> str:
    """计算技能目录的内容哈希（SKILL.md + run.py 的 MD5）"""
    hashes = []
    for fname in ("SKILL.md", "run.py"):
        fpath = os.path.join(skill_dir, fname)
        if os.path.isfile(fpath):
            with open(fpath, "rb") as f:
                hashes.append(hashlib.md5(f.read()).hexdigest())
    return "_".join(hashes) if hashes else ""
