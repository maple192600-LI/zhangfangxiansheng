"""fund 包 · §C5 基元库与 Agent 引擎 (v3)

禁止在本包内放 artifacts 代码（artifacts 由 Agent 产出，位于 backend/fund/artifacts/）。
本包仅提供：
  - primitives/    §C5 基元库白名单（37 函数固定）
  - artifacts/     存放 Agent 产出的 Parser/Rule 代码（后续 P0-T4 引入）
  - 以及 P0-T5 起的 agent harness、sandbox、artifact_service
"""
