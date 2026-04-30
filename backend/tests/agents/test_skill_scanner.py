"""技能安全扫描器测试

按 python-testing 技能规范编写
"""
import os
import tempfile
import pytest
from agents.skill_scanner import scan_file, scan_skill_dir, format_report, ScanRule, RULES


class TestScanRule:
    """验证扫描规则定义"""

    def test_至少有4条规则(self):
        assert len(RULES) >= 4

    def test_每条规则有id和severity(self):
        for rule in RULES:
            assert rule.rule_id
            assert rule.severity in ("critical", "high", "medium", "low")


class TestScanFile:
    """验证单文件扫描"""

    def test_安全文件通过(self, tmp_path):
        safe_file = tmp_path / "safe.py"
        safe_file.write_text("def hello():\n    return 'world'\n", encoding="utf-8")
        findings = scan_file(str(safe_file))
        assert len(findings) == 0

    def test_检测到eval(self, tmp_path):
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("result = eval(user_input)\n", encoding="utf-8")
        findings = scan_file(str(bad_file))
        assert any(f.rule_id == "dynamic-code" for f in findings)

    def test_检测到subprocess(self, tmp_path):
        bad_file = tmp_path / "bad2.py"
        bad_file.write_text("import subprocess\nsubprocess.run(['rm', '-rf', '/'])\n", encoding="utf-8")
        findings = scan_file(str(bad_file))
        assert any(f.rule_id == "dangerous-exec" for f in findings)

    def test_注释中的代码不误报(self, tmp_path):
        comment_file = tmp_path / "comments.py"
        comment_file.write_text("# 不要使用 eval()\nprint('safe')\n", encoding="utf-8")
        findings = scan_file(str(comment_file))
        # 注释行应该被跳过
        eval_findings = [f for f in findings if f.rule_id == "dynamic-code"]
        assert len(eval_findings) == 0


class TestScanSkillDir:
    """验证目录级扫描"""

    def test_扫描skill_creator目录(self):
        from agents.skill_creator import get_skill_creator_dir
        creator_dir = get_skill_creator_dir()
        if os.path.isdir(creator_dir):
            report = scan_skill_dir(creator_dir)
            assert report.safe
            assert report.scanned_files >= 1

    def test_格式化报告可读(self):
        from agents.skill_scanner import ScanReport, ScanFinding
        report = ScanReport(safe=True, scanned_files=3, total_lines=50)
        text = format_report(report)
        assert "3" in text  # 文件数
        assert "通过" in text or "PASS" in text or "未发现" in text


class TestScanFormat:
    """验证报告格式"""

    def test_有问题时标记不安全(self, tmp_path):
        bad_file = tmp_path / "evil.py"
        bad_file.write_text("eval(input())\n", encoding="utf-8")
        report = scan_skill_dir(str(tmp_path))
        assert not report.safe
