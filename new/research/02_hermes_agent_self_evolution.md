# Hermes Agent Self-Evolution 架构研究

> 来源：[NousResearch/hermes-agent-self-evolution](https://github.com/NousResearch/hermes-agent-self-evolution)
> 研究日期：2026-04-30

## 1. 整体架构（Phase 1-5）

这是一个**独立于 Agent 运行时的优化管道**，通过 DSPy + GEPA 自动进化 Agent 的"指令层"。

### 三个优化引擎

| 引擎 | 优化对象 | 角色 |
|------|---------|------|
| DSPy + GEPA | Skills、prompts、工具描述 | 主引擎 — 读取执行轨迹进行反思性变异 |
| DSPy MIPROv2 | Few-shot 示例、指令文本 | 备用优化器 |
| Darwinian Evolver | 代码文件、算法 | 外部 CLI，用于代码级进化 |

### Phase 架构

- **Phase 1（已实现）**：Skill 进化 — 优化 SKILL.md 文件
- **Phase 2（计划）**：工具描述优化 — 优化 tool schema 中的 description 字段
- **Phase 3（计划）**：系统提示进化 — 5 个可进化段落的系统提示
- **Phase 4（计划）**：代码进化 — 通过 Darwinian Evolver 优化 Python 源码
- **Phase 5（计划）**：持续自改进循环 — 自动检测弱项、定时优化

### 核心优化循环（6 步）

```
SELECT TARGET → BUILD EVAL DATASET → WRAP AS DSPy MODULE → RUN OPTIMIZER → EVALUATE & COMPARE → DEPLOY
```

## 2. 记忆系统设计

**不使用传统记忆存储**，而是围绕评估数据集构建的数据累积系统：

### 评估数据集（EvalDataset）

- **EvalExample**：`task_input` + `expected_behavior`（评分标准）+ `difficulty` + `category`
- **EvalDataset**：train/val/holdout 分割，JSONL 存储
- 路径：`datasets/skills/<skill-name>/`

### 四个数据源（类比记忆获取）

1. **合成生成** — 强 LLM 读取 skill 生成测试用例
2. **会话挖掘** — 从 Claude Code / Copilot / Hermes 真实使用中提取
3. **手工标注** — JSONL 文件，质量最高
4. **自动评估** — 植入 bug、运行 skill、检查测试是否通过

### 相关性过滤（类比记忆检索）

- 两阶段管线：廉价启发式预过滤 + LLM 相关性评分
- 启发式：消息与 skill 名/描述的关键词重叠
- LLM 评分：`RelevanceFilter.ScoreRelevance` 判断相关性

### 秘密检测（类比遗忘/过滤）

- `SECRET_PATTERNS` 正则匹配 API keys、tokens、密码
- 包含秘密的消息**永远不会**被纳入数据集

## 3. 自改进循环核心代码模式

### 模式 1：Skill-as-DSPy-Module

```python
class SkillModule(dspy.Module):
    class TaskWithSkill(dspy.Signature):
        skill_instructions: str = dspy.InputField()
        task_input: str = dspy.InputField()
        output: str = dspy.OutputField()

    def __init__(self, skill_text: str):
        self.skill_text = skill_text  # 这就是可优化参数
        self.predictor = dspy.ChainOfThought(self.TaskWithSkill)

    def forward(self, task_input):
        result = self.predictor(skill_instructions=self.skill_text, task_input=task_input)
        return dspy.Prediction(output=result.output)
```

### 模式 2：适应度函数（多维度评分）

```python
class FitnessScore:
    correctness: float        # 0-1
    procedure_following: float # 0-1
    conciseness: float        # 0-1
    length_penalty: float     # 0-0.3，接近限制时递增

    @property
    def composite(self):
        raw = 0.5 * correctness + 0.3 * procedure_following + 0.2 * conciseness
        return max(0.0, raw - length_penalty)
```

### 模式 3：约束门控

每个进化变体必须通过所有约束才能部署：
- 大小限制（skills ≤ 15KB）
- 增长限制（最大 +20%）
- 非空检查
- 结构完整性（有效 YAML frontmatter）
- 完整测试套件（pytest 必须 100% 通过）

### 模式 4：Frontmatter 保留（重装配模式）

```python
def reassemble_skill(frontmatter, evolved_body):
    return f"---\n{frontmatter}\n---\n\n{evolved_body}\n"
```

优化器只修改 body，metadata（name, description, version）保持不变。

## 4. Skill 进化管线（10 步）

1. 找到并加载 skill — 解析 SKILL.md 为 frontmatter + body
2. 构建评估数据集 — 合成/标注/挖掘
3. 验证基线约束 — 大小、结构、非空
4. 设置 DSPy + GEPA 优化器
5. 运行 GEPA 优化 — 反思性进化
6. 提取进化后的 skill 文本
7. 验证进化后的 skill — 所有约束必须通过
8. 在 holdout 集上评估 — 基线 vs 进化版本
9. 报告结果
10. 保存输出 — 进化 skill、基线、metrics.json

## 5. 可借鉴的设计模式

| 模式 | 描述 | 适用场景 |
|------|------|---------|
| "Operating ON, Not Inside" | 优化管道完全独立于 Agent 运行时 | 任何需要自改进但不碰核心的系统 |
| 分层优化目标（风险分级） | Tier 1-4，从文本到代码风险递增 | 多目标优化系统 |
| 多源评估数据管线 | 合成+真实+手工+自动四种互补 | 冷启动学习系统 |
| 约束门控作为硬底线 | 所有候选变体必须通过所有约束 | 安全关键的进化系统 |
| 长度惩罚渐变 | 90% 限制处开始从 0 渐增到 0.3 | 文本优化中防止冗长 |
| Benchmark-as-Gate | 基准测试是门控不是适应度函数 | 防止回归的优化系统 |
| Phase-Gated 开发 | 每阶段必须证明有效才进入下一阶段 | 不确定性高的多阶段项目 |
