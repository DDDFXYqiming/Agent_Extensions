# hermes_plugins / language-router

**Hermes 框架自适应语言路由插件 v5.0** —— Planner-first → Worker → 可选 Verifier → Digest 结构化推理流水线，为每次 LLM 调用自动选择**思考语言**与**推理深度**。

> **来源**：NousResearch / Diana 出品（v5.0），本仓库收集并自包含封装，MIT 许可，保留原作者署名。

## 它解决什么问题

主模型直接回答复杂问题时有两类痛点：

1. **语言选择**：技术任务（数学/编程/调试）用英语思考通常更准，创作/情感任务用用户母语思考更自然——固定一种语言两头不讨好；
2. **推理深度**：简单问题开深度推理浪费 token 和延迟，高风险问题（金融/医疗/法律）不做校验容易出错。

本插件在每次 LLM 调用前接管，产出结构化推理计划（语言 + 任务类型 + 推理模式），执行推理后把一份**内部 digest** 注入主模型上下文——主模型带着"该用什么语言、已有哪些经过验证的要点、有哪些风险"去回答，且**不暴露原始推理链**。

## 工作流程

`pre_llm_call` 钩子，每轮按需执行：

```
用户消息
  │
  ├─ 平凡回合旁路（"继续"/"好的"等 → 零开销放行）
  │
  ├─ ① Planner：任务类型 + 用户语言 + 推理模式
  │     LLM 结构化分类（JSON）为主，heuristic_first 时用关键词启发式
  │     （失败自动降级启发式，不中断流程）
  │
  ├─ ② Worker（Reasoner）：按模式执行
  │     off / hint        → 不推理 / 只给提示
  │     simple            → 单路径结构化草稿
  │     self_consistency  → 多路径独立推理 → 置信度择优 + 结论多数投票
  │     tree              → 多分支并行 → 置信度剪枝 → 合并
  │
  ├─ ③ Verifier（可选）：高风险任务（金融/医疗、法律/政策、安全敏感）
  │     或低置信度时触发；verdict: accept / revise / reject / fallback
  │     revise 会用修订要点替换草稿；reject 则降级为普通回答
  │
  └─ ④ Digest：压缩为 [language-router internal digest] 注入主模型上下文
        （任务理解 / 关键点 / 候选结论 / 风险与注意 / 答案大纲）
```

`post_api_request` 钩子：观察本次 API 请求的成败与产出，更新 **Dynamic Selector** 的性能历史（指数滑动平均），持续学习"哪种语言想哪类任务更稳"。

## 语言策略

| 场景 | 思考语言 |
|---|---|
| 技术任务（编程 / 数学 / 调试 / 研究 / 架构） | 默认英语（`en`） |
| 创作 / 情感 / 文化任务 | 默认用户语言（`user`） |
| 用户显式要求（"用中文回答" / "answer in English"） | **无条件尊重**（正则规则识别中/英/日/韩/德/法/西） |
| 输出语言 | 默认跟随用户语言，可配置 `fallback_language` |

用户语言检测覆盖 14 种语言（Unicode 脚本级：中日韩阿俄印泰 + 词汇级：德法西葡意），混合语言自动归类。

## v5.0 新特性（基于论文方法）

| 模块 | 依据 | 说明 |
|---|---|---|
| **Multilingual Explorer** 多语言思维探索 | *Could Thinking Multilingually Empower LLM Reasoning?*（GPQA ~45→~90） | tree / self_consistency 模式下并行探索多语言推理（math→zh/ja、logic→de/fr 亲和），多数投票合并 |
| **Dynamic Selector** 动态语言选择 | AdaMCoT | 四维打分：历史表现 40% + 任务-语言亲和 30% + 用户语言匹配 20% + 多样性 10%；EMA 学习率 0.1 在线更新 |
| **Code-Switch Detector** 语码转换检测 | *The Impact of Language Mixing on Bilingual LLM Reasoning* | 检测 4 种转换模式（短语 / 技术术语 / 格式匹配 / 全切换）并注入引导——研究发现强制单语解码会使准确率 **-5.6 分** |
| **Reward Evaluator** 奖励评估器 | AdaMCoT | LLM 按 accuracy 0.5 / consistency 0.3 / fluency 0.2 加权评分，低于阈值（默认 0.6）判 reject |

## 工程化特性

- **延迟预算**：默认总预算 20s，多级降级（high / medium / low / critical）——预算吃紧时自动跳过 Verifier（low）甚至 Reasoner（critical），保证交互不卡；
- **计划缓存**：LRU + TTL 300s（默认 1000 条），相同消息不重复跑 Planner，缓存命中零 LLM 开销；
- **平凡回合旁路**：`继续` / `好的` / `ok` 等短回合直接放行；
- **平台禁用**：`platforms.disabled` 列表可按平台整体关闭；
- **全链路兜底**：Planner / Reasoner / Verifier 任一步失败都走启发式降级，digest 照常注入，**不影响主流程**；
- **结构化输出**：所有 LLM 调用走 `complete_structured` JSON 模式，数据契约见 `types.py`；
- **可观测**：`get_stats()` 暴露缓存命中率、模式分布、语言分布、降级与失败次数。

## 安装与配置

将本目录放入 Hermes 框架的插件目录即可（`plugin.yaml` 已声明 `hooks: pre_llm_call / pre_api_request / post_api_request`；依赖 `hermes_cli` 的 `PluginContext` / `llm.complete_structured`）。

配置写在 Hermes 的 `config.yaml`（路径由 `get_hermes_home()` 决定），覆盖 `DEFAULT_CONFIG`（深度合并，只写要改的字段）：

```yaml
plugins:
  entries:
    language-router:
      config:
        planner:
          # provider / model 留空 = 使用当前会话模型
          heuristic_first: true   # 优先启发式，节省一次 LLM 调用
        reasoning:
          mode: auto              # off | hint | simple | verify | self_consistency | tree
        verifier:
          enabled: auto           # auto | true | false
        output:
          preserve_user_language: true
        latency_budget:
          max_total_seconds: 20
        debug:
          show_footer: false      # true 时在 digest 尾部附加调试脚注
```

常用调参建议：

- 想要**零额外 LLM 调用**：`planner.heuristic_first: true` + `reasoning.mode: simple`；
- 想要**数学/逻辑题更稳**：`reasoning.mode: auto`（tree / self_consistency 按任务自动触发）；
- 想要**省延迟**：`latency_budget.max_total_seconds` 调小，或 `skip_verifier_if_budget_low: true`。

## 目录结构

```
language-router/
├── __init__.py                # 插件主体：流水线编排 + 3 个 hooks + 延迟预算
├── plugin.yaml                # 插件清单（名称 / 版本 / 作者 / hooks）
├── classifier.py              # 任务分类器（LLM 结构化 + 启发式兜底）
├── cache.py                   # 线程安全 LRU 分类缓存（TTL 300s）
├── prompts.py                 # Planner / Reasoner / Verifier 提示词模板
├── types.py                   # 数据结构契约（ReasoningPlan / Draft / Report 等）
├── dynamic_selector.py        # 动态语言选择（AdaMCoT，EMA 在线学习）
├── multilingual_explorer.py   # 多语言思维探索（并行 + 投票合并）
├── code_switch_detector.py    # 语码转换模式检测与引导
└── reward_evaluator.py        # 推理路径奖励评估（accuracy / consistency / fluency）
```

## 授权

MIT License，保留原作者署名（Diana / NousResearch）。
