"""Fund Agent harness_strict 调度器

步骤固定、工具白名单、产物受 Pydantic Schema 约束。
每个 skill 的执行步骤在代码中写死，AI 只填参数。
"""
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from agents.fund import memory
from agents.fund.schemas import (
    ParserInput, ParserOutput,
    RuleInput, RuleOutput,
    RuleMaintainInput,
    TemplateInferenceInput, TemplateInferenceOutput,
    PlaceholderBinding,
)

ALLOWED_SKILLS = {
    "parser.bank",
    "parser.manual",
    "rule.template_fill",
    "rule.maintain",
    "template.inference",
}


@dataclass
class SkillDraft:
    """Skill 执行结果"""
    payload: dict[str, Any]


class FundAgent:
    """Fund Agent harness_strict 调度器"""

    def __init__(self, db: Session):
        self.db = db

    def run_skill(self, skill_name: str, payload: dict[str, Any]) -> SkillDraft:
        if skill_name not in ALLOWED_SKILLS:
            raise ValueError(f"未知 skill: {skill_name}")

        handler = {
            "parser.bank": self._parser_bank,
            "parser.manual": self._parser_manual,
            "rule.template_fill": self._rule_template_fill,
            "rule.maintain": self._rule_maintain,
            "template.inference": self._template_inference,
        }[skill_name]

        return handler(payload)

    def _parser_bank(self, payload: dict) -> SkillDraft:
        """parser.bank: 生成银行流水解析器

        步骤固定：
        1. 验证输入 Schema
        2. 读取样本文件（脱敏）
        3. 加载字段字典 + 别名库
        4. 创建 Parser artifact 草稿
        """
        inp = ParserInput(**payload)

        field_dict = inp.field_dictionary_snapshot or memory.get_field_dictionary()
        alias_lib = inp.alias_library_snapshot or memory.get_alias_library()

        # V1: 创建占位 artifact（实际解析逻辑需要 AI 介入）
        artifact = memory.create_parser_draft(
            db=self.db,
            name=f"{inp.account_code}_bank_v1",
            kind="bank",
            account_code=inp.account_code,
            code="# AI 生成的银行流水解析器\n# 等待 AI 填充\n",
            primitives_imports=[],
            sample_check_log={
                "sample_rows": 0,
                "parsed_rows": 0,
                "canonical_violations": 0,
            },
            confidence=0.0,
        )

        return SkillDraft(payload={
            "artifact_id": artifact.id,
            "name": artifact.name,
            "kind": "bank",
            "account_code": inp.account_code,
            "status": "draft",
            "confidence": 0.0,
        })

    def _parser_manual(self, payload: dict) -> SkillDraft:
        """parser.manual: 生成手工流水解析器"""
        inp = ParserInput(**payload)

        field_dict = inp.field_dictionary_snapshot or memory.get_field_dictionary()

        artifact = memory.create_parser_draft(
            db=self.db,
            name=f"{inp.account_code}_manual_v1",
            kind="manual",
            account_code=inp.account_code,
            code="# AI 生成的手工流水解析器\n# 等待 AI 填充\n",
            primitives_imports=[],
            sample_check_log={
                "sample_rows": 0,
                "parsed_rows": 0,
                "canonical_violations": 0,
            },
            confidence=0.0,
        )

        return SkillDraft(payload={
            "artifact_id": artifact.id,
            "name": artifact.name,
            "kind": "manual",
            "account_code": inp.account_code,
            "status": "draft",
            "confidence": 0.0,
        })

    def _rule_template_fill(self, payload: dict) -> SkillDraft:
        """rule.template_fill: 生成报表填充规则

        步骤固定：
        1. 验证输入 Schema
        2. 解析模板占位符列表
        3. 为每个占位符匹配基元
        4. 创建 Rule artifact 草稿
        """
        inp = RuleInput(**payload)

        # V1: 创建占位 Rule artifact
        bindings = {}
        primitives = []
        for ph in inp.placeholder_list:
            bindings[ph] = {"primitive": "const", "value": ph}
            primitives.append("const")

        artifact = memory.create_rule_draft(
            db=self.db,
            name="template_rule_v1",
            template_id=inp.template_job_id,
            placeholder_bindings=bindings,
            loop_config=None,
            primitives_imports=primitives,
            sample_check_log={
                "placeholder_bound": len(bindings),
                "placeholder_unbound": 0,
                "placeholder_extra": 0,
            },
            confidence=0.0,
        )

        return SkillDraft(payload={
            "artifact_id": artifact.id,
            "name": artifact.name,
            "template_id": inp.template_job_id,
            "status": "draft",
            "confidence": 0.0,
        })

    def _rule_maintain(self, payload: dict) -> SkillDraft:
        """rule.maintain: 维护/迭代现有规则

        步骤固定：
        1. 加载现有 Rule artifact
        2. 解析修改请求
        3. 创建新版本 Rule artifact（旧版保留）
        """
        inp = RuleMaintainInput(**payload)

        from db.tables import RuleArtifact
        existing = self.db.query(RuleArtifact).filter(RuleArtifact.id == inp.rule_id).first()
        if not existing:
            raise ValueError(f"Rule artifact {inp.rule_id} 不存在")

        # V1: 创建新版本（继承旧版配置）
        new_bindings = dict(existing.placeholder_bindings or {})
        new_loop = dict(existing.loop_config or {}) if existing.loop_config else None
        new_primitives = list(existing.primitives_imports or [])

        artifact = memory.create_rule_draft(
            db=self.db,
            name=existing.name,
            template_id=existing.template_id,
            placeholder_bindings=new_bindings,
            loop_config=new_loop,
            primitives_imports=new_primitives,
            sample_check_log=existing.sample_check_log or {},
            confidence=existing.confidence or 0.0,
            created_by=inp.user_id,
        )

        return SkillDraft(payload={
            "artifact_id": artifact.id,
            "name": artifact.name,
            "version": artifact.version,
            "status": "draft",
            "change_request": inp.change_request,
        })

    def _template_inference(self, payload: dict) -> SkillDraft:
        """template.inference: 自动识别空白模板

        三阶段流水线：
        Stage A: 纯代码结构解析（无 AI）
        Stage B: AI 语义映射
        Stage C: 用户确认
        """
        inp = TemplateInferenceInput(**payload)

        # 创建推断任务
        job = memory.create_inference_job(
            db=self.db,
            template_file=inp.template_file,
            original_filename=inp.template_file.split("/")[-1] if "/" in inp.template_file else inp.template_file.split("\\")[-1],
        )

        # Stage A: 结构解析
        stage_a = self._stage_a_parse(inp.template_file)
        memory.update_inference_job(
            self.db, job.id,
            stage="b",
            stage_a_output=stage_a,
        )

        # Stage B: 占位 → 字段映射（V1 简单匹配）
        rule_draft = self._stage_b_map(stage_a, job.id)
        memory.update_inference_job(
            self.db, job.id,
            stage="c",
            stage_b_output=rule_draft,
        )

        return SkillDraft(payload={
            "job_id": job.id,
            "detected_placeholders": stage_a.get("placeholders", []),
            "confidence": rule_draft.get("confidence", 0.0),
            "rule_draft": rule_draft,
            "stage_a_output": stage_a,
        })

    def _stage_a_parse(self, template_file: str) -> dict:
        """Stage A: 纯代码结构解析"""
        import re

        placeholders = []
        merged_cells = []
        header_rows = []

        try:
            from openpyxl import load_workbook
            wb = load_workbook(template_file, read_only=True, data_only=True)
            for ws in wb.worksheets:
                # 提取占位符
                for row in ws.iter_rows():
                    for cell in row:
                        if cell.value and isinstance(cell.value, str):
                            # 匹配 ${xxx}, {{xxx}}, 【xxx】等占位符
                            found = re.findall(r'\$\{([^}]+)\}|\{\{([^}]+)\}\}|【([^】]+)】', cell.value)
                            for match in found:
                                ph = match[0] or match[1] or match[2]
                                if ph and ph not in placeholders:
                                    placeholders.append(ph)

                # 识别合并单元格
                for mc in ws.merged_cells.ranges:
                    merged_cells.append({
                        "min_row": mc.min_row,
                        "max_row": mc.max_row,
                        "min_col": mc.min_col,
                        "max_col": mc.max_col,
                    })
            wb.close()
        except Exception:
            pass

        return {
            "placeholders": placeholders,
            "merged_cells": merged_cells,
            "header_rows": header_rows,
        }

    def _stage_b_map(self, stage_a: dict, job_id: int) -> dict:
        """Stage B: 占位符 → 字段映射（V1 简单规则匹配）"""
        field_dict = memory.get_field_dictionary()
        placeholders = stage_a.get("placeholders", [])

        bindings = {}
        matched_count = 0
        for ph in placeholders:
            ph_lower = ph.lower()
            best_match = None
            best_score = 0

            for field_key, field_info in field_dict.items():
                aliases = field_info.get("aliases", [])
                cn_name = field_info.get("cn_name", "")
                all_names = [cn_name] + aliases

                for name in all_names:
                    if name in ph or ph in name:
                        score = len(name) / max(len(ph), 1)
                        if score > best_score:
                            best_score = score
                            best_match = field_key

            if best_match:
                bindings[ph] = {"primitive": "field", "value": best_match}
                matched_count += 1
            else:
                bindings[ph] = {"primitive": "const", "value": ph}

        confidence = matched_count / max(len(placeholders), 1) if placeholders else 0.0

        # 创建 Rule 草稿
        artifact = memory.create_rule_draft(
            db=self.db,
            name="auto_inference_v1",
            template_id=job_id,
            placeholder_bindings=bindings,
            loop_config=None,
            primitives_imports=list(set(b["primitive"] for b in bindings.values())),
            sample_check_log={
                "placeholder_bound": len(bindings),
                "placeholder_unbound": 0,
                "placeholder_extra": 0,
            },
            confidence=confidence,
        )

        memory.update_inference_job(
            self.db, job_id,
            rule_artifact_id=artifact.id,
        )

        return {
            "artifact_id": artifact.id,
            "name": artifact.name,
            "confidence": confidence,
            "placeholder_bindings": bindings,
        }
