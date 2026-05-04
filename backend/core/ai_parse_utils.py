"""AI 解析公共工具 — 表头映射、思考标签清理、JSON 提取"""
import json
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.ai_call import chat
from core.security import decrypt_key


def strip_thinking_tags(text: str) -> str:
    """去除模型返回的思考标签内容（<think/>、<reasoning/>、<reflection/> 等）"""
    text = re.sub(r"<think[^>]*>.*?</think\s*>", "", text, flags=re.S)
    text = re.sub(r"<reasoning[^>]*>.*?</reasoning\s*>", "", text, flags=re.S)
    text = re.sub(r"<reflection[^>]*>.*?</reflection\s*>", "", text, flags=re.S)
    return text.strip()


def extract_and_parse_json(text: str) -> Optional[dict]:
    """从 AI 返回文本中提取并解析 JSON，支持多种格式：
    1. 纯 JSON
    2. markdown 代码块包裹
    3. JSON 前后有额外文本
    4. 嵌套代码块 + "mapping" 关键字
    """
    text = text.strip()

    # 尝试1：直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试2：去掉 markdown 代码块
    code_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, flags=re.S)
    if code_match:
        try:
            return json.loads(code_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 尝试3：提取最外层 { }
    obj_match = re.search(r"\{.*\}", text, flags=re.S)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except json.JSONDecodeError:
            pass

    # 尝试4：查找 "mapping" 关键字后的 JSON 对象
    mapping_match = re.search(r'\{\s*"mapping"\s*:', text, flags=re.S)
    if mapping_match:
        start = mapping_match.start()
        sub = text[start:]
        depth = 0
        for i, ch in enumerate(sub):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(sub[: i + 1])
                    except json.JSONDecodeError:
                        break

    return None


def shorten_headers(headers: List[str]) -> List[str]:
    """将带 [xxx] 后缀的列名缩短为纯列名"""
    result = []
    for h in headers:
        bracket = h.find("[")
        result.append(h[:bracket].strip() if bracket > 0 else h)
    return result


def build_short_to_original(headers: List[str]) -> Dict[str, str]:
    """构建短列名 -> 原始列名的映射"""
    mapping = {}
    for orig in headers:
        bracket = orig.find("[")
        short = orig[:bracket].strip() if bracket > 0 else orig
        mapping[short] = orig
    return mapping


def restore_mapping_keys(
    ai_mapping: Dict[str, str], headers: List[str]
) -> Dict[str, str]:
    """将 AI 返回的短列名映射还原为原始列名"""
    s2o = build_short_to_original(headers)
    return {s2o.get(k, k): v for k, v in ai_mapping.items()}


def format_sample_text(
    sample_rows: Optional[List], max_rows: int = 3, mask_fn=None
) -> str:
    """格式化样本数据为文本，可选脱敏"""
    if not sample_rows:
        return ""
    lines = []
    for row in sample_rows[:max_rows]:
        if isinstance(row, (list, tuple)):
            if mask_fn:
                cells = [str(c).strip()[:30] for c in mask_fn(row)]
            else:
                cells = [str(c).strip()[:30] for c in row]
            lines.append(" | ".join(cells))
    if not lines:
        return ""
    return f"\n\n前几行样本数据:\n" + "\n".join(lines)


def find_active_agent(db: Session, agent_id: int = None):
    """查找活跃的 Agent，指定 ID 则精确查找，否则取第一个"""
    from db.tables import Agent

    if agent_id:
        return db.query(Agent).filter(
            Agent.id == agent_id, Agent.status == "active",
        ).first()
    return db.query(Agent).filter(
        Agent.status == "active",
    ).order_by(Agent.sort_order.desc()).first()


def build_system_prompt(agent) -> str:
    """构建 AI 调用的 system prompt"""
    system_prompt = f"你是「{agent.display_name}」，一个 AI 智能体。"
    if agent.role_prompt:
        system_prompt += f"\n\n{agent.role_prompt}"
    system_prompt += "\n\n【当前任务模式】你现在处于「列映射任务」模式，不要与用户对话，只需完成列映射并返回严格的 JSON 结果。不要输出任何 JSON 以外的内容。"
    return system_prompt


def call_agent_for_mapping(
    agent, user_message: str
) -> Dict[str, Any]:
    """调用 Agent 的 AI 配置进行列映射"""
    ai_cfg = agent.ai_config
    api_key = decrypt_key(ai_cfg.api_key_local)

    result = chat(
        provider=ai_cfg.provider,
        api_key=api_key,
        base_url=ai_cfg.base_url,
        model_name=ai_cfg.model_name,
        messages=[
            {"role": "system", "content": build_system_prompt(agent)},
            {"role": "user", "content": user_message},
        ],
        max_tokens=agent.llm_max_tokens or 4096,
        timeout=agent.llm_timeout or 90,
    )

    if not result.get("ok"):
        return {
            "ok": False,
            "error": f"AI 调用失败: {result.get('error', '未知错误')}",
            "error_code": result.get("error_code", "AI_CALL_FAILED"),
            "error_category": result.get("error_category", "unknown"),
        }

    content = result["content"].strip()
    content = strip_thinking_tags(content)
    parsed = extract_and_parse_json(content)

    if parsed is None:
        return {
            "ok": False,
            "error": "AI 返回格式异常，请重试或手动配置映射",
            "error_code": "AI_JSON_PARSE_FAILED",
            "error_category": "parse",
            "hint": "建议改用手工映射",
            "raw": content,
        }

    return {"ok": True, "parsed": parsed}


def validate_mapping_confidence(
    valid_mapping: Dict[str, str], total_columns: int
) -> str:
    """根据映射结果判断置信度"""
    has_date = any(v == "business_date" for v in valid_mapping.values())
    if has_date and len(valid_mapping) >= 3:
        return "high"
    if has_date:
        return "medium"
    return "low"
