"""技能安全扫描器

参考 OpenClaw 静态分析规则，在安装第三方 skill 前扫描安全风险。
扫描 SKILL.md、run.py、scripts/ 等所有文件。
"""
import os
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScanRule:
    rule_id: str
    severity: str  # critical, high, medium, low
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


RULES: list[ScanRule] = [
    ScanRule(
        rule_id="dangerous-exec",
        severity="critical",
        pattern=re.compile(r"(?:exec\(|spawn|subprocess\.)", re.IGNORECASE),
        description="检测子进程执行调用",
    ),
    ScanRule(
        rule_id="dynamic-code",
        severity="critical",
        pattern=re.compile(r"(?:eval\(|__import__|compile\()", re.IGNORECASE),
        description="检测动态代码执行",
    ),
    ScanRule(
        rule_id="env-harvest",
        severity="critical",
        pattern=re.compile(r"(?:os\.environ|process\.env).*(?:requests|fetch|http)", re.IGNORECASE),
        description="检测环境变量收集+网络发送",
    ),
    ScanRule(
        rule_id="crypto-mine",
        severity="critical",
        pattern=re.compile(r"(?:stratum|xmrig|coinhive|cryptonight)", re.IGNORECASE),
        description="检测加密货币挖矿",
    ),
    ScanRule(
        rule_id="exfiltration",
        severity="high",
        pattern=re.compile(r"(?:open|read_file|file_get_contents).*(?:requests\.post|fetch|urllib)", re.IGNORECASE),
        description="检测文件读取+网络发送组合",
    ),
    ScanRule(
        rule_id="network-shell",
        severity="high",
        pattern=re.compile(r"(?:socket\.socket|nc\s+-|netcat)", re.IGNORECASE),
        description="检测网络 shell 连接",
    ),
]


def scan_file(file_path: str, rules: list[ScanRule] = None) -> list[ScanFinding]:
    """扫描单个文件"""
    if rules is None:
        rules = RULES

    findings: list[ScanFinding] = []
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
                # 跳过 SKILL.md 中作为文档说明的引用
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


def scan_skill_dir(skill_dir: str, rules: list[ScanRule] = None) -> ScanReport:
    """递归扫描技能目录"""
    if rules is None:
        rules = RULES

    report = ScanReport(safe=True)
    scan_extensions = {".py", ".js", ".ts", ".md", ".yaml", ".yml", ".json", ".sh"}

    for root, _dirs, files in os.walk(skill_dir):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in scan_extensions:
                continue

            fpath = os.path.join(root, fname)
            findings = scan_file(fpath, rules)
            report.findings.extend(findings)
            report.scanned_files += 1

            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    report.total_lines += sum(1 for _ in f)
            except OSError:
                pass

    # 任何 critical 或 high 级别发现 → 不安全
    critical_or_high = [f for f in report.findings if f.severity in ("critical", "high")]
    if critical_or_high:
        report.safe = False

    return report


def format_report(report: ScanReport) -> str:
    """格式化扫描报告为可读文本"""
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
