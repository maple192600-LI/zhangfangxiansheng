"""技能自我进化系统。对标 Hermes agent/curator.py

核心不变量:
  1. 只处理 agent_created 的技能
  2. 永不删除，只归档（移动到 .archive/ 目录）
  3. pinned 技能跳过所有自动转换
  4. 运行条件: 空闲 + 距上次运行超过间隔（默认 7 天）
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from config import AGENTS_ROOT

logger = logging.getLogger(__name__)

CURATOR_INTERVAL_HOURS = 168
STALE_AFTER_DAYS = 30
ARCHIVE_AFTER_DAYS = 90


class Curator:
    """技能生命周期管理器"""

    def __init__(self, agent_code: str):
        self.agent_code = agent_code
        self.skills_dir = Path(AGENTS_ROOT) / agent_code / "skills"
        self.state_file = Path(AGENTS_ROOT) / agent_code / ".curator_state"

    def maybe_run(self, force: bool = False) -> Optional[dict]:
        """门控检查后执行一次审查"""
        state = self._load_state()
        if state.get("paused") and not force:
            return None
        last_run = state.get("last_run_at")
        if not force and last_run:
            last_dt = datetime.fromisoformat(last_run)
            if datetime.now() - last_dt < timedelta(hours=CURATOR_INTERVAL_HOURS):
                return None
        return self._run()

    def _run(self) -> dict:
        """执行一次审查"""
        counts = self._apply_transitions()

        state = self._load_state()
        state["last_run_at"] = datetime.now().isoformat()
        state["run_count"] = state.get("run_count", 0) + 1
        self._save_state(state)

        if counts["stale"] > 0 or counts["archived"] > 0:
            logger.info("Curator %s: %s", self.agent_code, counts)

        return counts

    def _apply_transitions(self) -> dict:
        """纯时间判断的状态转换"""
        now = datetime.now()
        stale_cutoff = now - timedelta(days=STALE_AFTER_DAYS)
        archive_cutoff = now - timedelta(days=ARCHIVE_AFTER_DAYS)

        counts = {"checked": 0, "stale": 0, "archived": 0, "reactivated": 0}

        if not self.skills_dir.exists():
            return counts

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            meta_file = skill_dir / ".meta.json"
            if not meta_file.exists():
                continue

            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                continue

            if meta.get("source") != "agent_created":
                continue
            if meta.get("lifecycle") == "pinned":
                continue

            counts["checked"] += 1
            lifecycle = meta.get("lifecycle", "active")
            last_used = meta.get("last_used_at")

            anchor = datetime.fromisoformat(last_used) if last_used else now
            if anchor.tzinfo:
                anchor = anchor.replace(tzinfo=None)

            if anchor <= archive_cutoff and lifecycle != "archived":
                archive_dir = self.skills_dir / ".archive"
                archive_dir.mkdir(exist_ok=True)
                dest = archive_dir / skill_dir.name
                if not dest.exists():
                    skill_dir.rename(dest)
                meta["lifecycle"] = "archived"
                counts["archived"] += 1
            elif anchor <= stale_cutoff and lifecycle == "active":
                meta["lifecycle"] = "stale"
                counts["stale"] += 1
            elif anchor > stale_cutoff and lifecycle == "stale":
                meta["lifecycle"] = "active"
                counts["reactivated"] += 1

            meta_file.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        return counts

    def _load_state(self) -> dict:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"last_run_at": None, "paused": False, "run_count": 0}

    def _save_state(self, state: dict):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
