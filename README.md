# Agent_Extensions

**AI Agent 技能与 DeepSeek Harness（DSH）扩展集合** —— 通用智能体 Skill + DSH 原生插件 + Hermes 插件，开箱即用。

![repo](https://img.shields.io/badge/agent-skills-4B8BBE) ![dsh](https://img.shields.io/badge/deepseek--harness-plugin-7A4FBF) ![license](https://img.shields.io/badge/license-MIT-green)

本仓库收集、翻译并**自包含封装** AI Agent 相关的技能资源，并面向 [DeepSeek Harness（DSH）](https://github.com/deepseek-ai/deepseek-harness) 提供标准插件形式的扩展。所有内容均为**自包含**（技能/插件内自带脚本、模板与文档，不依赖仓库外文件），克隆即可用。

> **来源说明**：`dsh-plugins/` 除 `dsh-annotation-patched`（fork 自 [omdsh-dev/dsh-annotation](https://github.com/omdsh-dev/dsh-annotation)）外均为本仓库原创；`General_skills/` 与 `hermes_plugins/` 为收集、翻译并自包含封装的社区开源技能/插件（作者已在各 `SKILL.md`/`plugin.yaml` 中标注），全部按 MIT 许可分发。

## ✨ 内容总览

### 1️⃣ 通用技能（General_skills）—— 跨框架可用

任何智能体框架（Claude Code / Codex / opencode / DSH / Hermes 等）均可把目录作为 Skill 挂载：

| 技能 | 能力 | 依赖 |
|---|---|---|
| `vision-skill` | 识图：本地图片 → 视觉模型描述（Qwen 动态分辨率方法，OpenAI 兼容接口） | Python 3 + 视觉模型 API Key |
| `video-notes-generator` | 视频 URL → 结构化 Markdown 笔记（时间戳 / 抽取帧 / 多模态图像观察 / AI 总结），支持 Bilibili / YouTube / 抖音 / 快手 / 本地文件 | Python 3 + 依赖（见 `scripts/install_deps.sh`） |
| `ppt-master` | 源文档（PDF / DOCX / URL / Markdown）→ 多角色协作生成 SVG 页面 → 导出 PPTX | Python 3（标准库为主，可选依赖见 `requirements.txt`） |
| `markitdown-skill` | 微软 MarkItDown：PDF / DOCX / PPTX / XLSX / HTML / EPUB 等 → 统一 Markdown | Python 3 + `pip install -r requirements.txt` |
| `generic-agent-code-run` | GenericAgent 风格 `code_run`：Windows 桌面应用 / 真实浏览器自动化（Win32 / UIA / OCR / 截图 / CDP）+ 观察-行动-验证循环 | Python 3 + 对应库 |

> 所有技能均内置 `SKILL.md`（agent 运行时加载的指令），部分附 `scripts/`、`templates/`、`references/`。

### 2️⃣ DSH 原生插件（dsh-plugins）—— 零框架补丁

面向 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 官方扩展接缝（`ctx.skills` / `ctx.tools` / `ctx.credentials`），可随 DSH 版本升级：

| 插件 | 能力 | 依赖 |
|---|---|---|
| `dsh-vision-skill` v2.1 | 识图插件：7 个工具 + 渐进式工具暴露 + Credential 化 + 路径围栏 | Node.js + DSH（`dsh-tools` / `dsh-credentials`）、Python 3 + Pillow、视觉模型 API Key |
| `dsh-memory` | 跨会话长期记忆：L1 索引注入（每轮实时、KV 缓存友好）+ L2 环境事实 + L3 任务经验，行动验证写入 | Node.js + DSH（`dsh-tools`） |
| `dsh-annotation-patched` | 选中批注/引用插件（fork 增强）：选中助手回复文字 → 批注（可空）→ 回车随消息发送，回复按 `Annotation N` 逐条对照；增强：Codex 式选中即引用 + 幽灵引用修复 | Node.js + DSH（纯浏览器端 bundle，零 Node 逻辑） |

### 3️⃣ Hermes 插件（hermes_plugins）

| 插件 | 能力 | 依赖 |
|---|---|---|
| [`language-router`](hermes_plugins/language-router/README.md) v5.0 | 自适应语言路由：Planner-first → Worker → 可选 Verifier → Digest 流程（NousResearch / Diana 出品），hooks 挂载 `pre_llm_call` / `pre_api_request` / `post_api_request` | Hermes 框架 |

## 📁 目录结构

```
Agent_Extensions/
├── General_skills/            # 通用智能体技能（跨框架，挂载即用）
│   ├── vision-skill/          # 识图
│   ├── video-notes-generator/ # 视频转结构化笔记
│   ├── ppt-master/            # 文档 → SVG → PPTX
│   ├── markitdown-skill/      # 任意文档 → Markdown
│   └── generic-agent-code-run/ # Windows 桌面/浏览器自动化
├── dsh-plugins/               # DeepSeek Harness（DSH）原生插件
│   ├── dsh-vision-skill/      # 识图插件 v2.1（7 工具 + 渐进式暴露 + Credential 化）
│   ├── dsh-memory/            # 跨会话分层长期记忆
│   └── dsh-annotation-patched/ # 选中批注/引用插件（fork 增强，Codex 式选中即引用）
├── hermes_plugins/            # Hermes 框架插件
│   └── language-router/       # 语言路由（planner-first）
└── README.md
```

## 🚀 快速开始

### 方式一：挂载通用技能（任何框架）

以 `vision-skill` 为例：

```bash
# 1. 复制技能目录到你的 agent 的 skills 目录
#    （Claude Code: ~/.claude/skills/ ；Codex: ~/.codex/skills/ ；其他框架见其文档）
cp -r General_skills/vision-skill <你的 skills 目录>/

# 2. 配置视觉模型（OpenAI 兼容接口）
cd General_skills/vision-skill
cp templates/.env.example .env   # 填入 VISION_API_URL / VISION_MODEL / VISION_API_KEY

# 3. 自检
python scripts/vision.py --check
```

其他技能用法详见各目录内 `SKILL.md`。

### 方式二：安装 DSH 插件（以 `dsh-vision-skill` 为例）

完整步骤见 [`dsh-plugins/dsh-vision-skill/README.md`](dsh-plugins/dsh-vision-skill/README.md)，推荐 **bundle 标准安装**：

```bash
# 1. 克隆仓库
git clone https://github.com/DDDFXYqiming/Agent_Extensions.git
cd Agent_Extensions/dsh-plugins/dsh-vision-skill

# 2. 安装依赖（dsh-tools / dsh-credentials）
pnpm add "@deepseek-ai/dsh-tools@rc" "@deepseek-ai/dsh-credentials@rc"

# 3. 注册到 web profile（自带 cordis.patch.yml，自动贡献 id: vision-skill）
dsh plugin --profile web add <本目录绝对路径>

# 4. 配置 Credential（$DSH_HOME/.credentials.yaml）
VISION_API_KEY: sk-xxxx
```

> ⚠️ bundle 安装后**不要**在 profile 的 `cordis.patch.yml` 里再 `insert` 同名条目，否则会触发 `duplicate loader entry id` 启动崩溃；需要自定义配置时用裸条目按 id 覆盖（见插件 README）。

### 方式三：安装 Hermes 插件

将 `hermes_plugins/language-router` 目录放入 Hermes 插件目录即可（`plugin.yaml` 声明了全部 hooks 与版本信息）。

## 🧩 DSH 插件能力一览

### dsh-vision-skill v2.1（7 工具 + 1 运行时 skill）

| 工具 | 能力 |
|---|---|
| `vision_analyze` | 识图（5 模式 + `mega` 超高清 16M 像素预算） |
| `vision_ocr` / `vision_long_screenshot_ocr` | 独立 OCR / 超长截图分块 OCR（带重叠切块 → 逐块识别 → 合并） |
| `vision_ground` / `vision_detect` | 目标定位 / 元素枚举（像素坐标框 + 归一化坐标） |
| `vision_dominant_colors` | 主色分析（本地像素算法，无需 API） |
| `vision_clipboard` | 剪贴板图片兜底（应对"当前模型不支持图片"粘贴拦截） |

工程化特性：**渐进式工具暴露**（全局只挂 1 个轻量激活工具，省上下文）、**密钥 Credential 化**（`credential: VISION_API_KEY` 引用，每操作解析）、**路径围栏**（realpath 校验防穿越）、**超时与并发门控**、**严格 JSON Schema 结构化输出**。

### dsh-memory（分层长期记忆）

| 组件 | 说明 |
|---|---|
| `memory:index` | 通过 `ctx.systemPrompt.context` 每轮实时注入 L1 索引（读文件即生效，无需重载） |
| `memory`（运行时 skill） | 触发语义：何时读 / 何时写 / 何时同步索引 |
| `memory_list` | 列出全部记忆（L2 facts + L3 sops + 索引行数） |
| `memory_read` | 读取指定记忆（index / fact 主题 / sop 文件名） |
| `memory_write` | 写入记忆（fact/sop，**evidence 必填** = 行动验证公理） |
| `memory_index` | 重建 L1 索引自动段（保留 `[RULES]` 手动段） |

核心公理：**行动验证**（No Execution, No Memory）、**神圣不可删改**（已验证事实可压缩迁移、严禁丢弃）、**禁易变状态**（时间戳/PID/临时路径不存）、**最小充分指针**（L1 只写存在性）。注入走 user-role 快照，**不破坏 DSH 的 KV 缓存命中率**（设计细节见插件 README）。

### dsh-annotation-patched（选中批注/引用，fork 增强）

| 能力 | 说明 |
|---|---|
| 选中批注 | 选中助手回复文字 → 批注（可留空）→ 回车随消息发送；自己的气泡不显示批注块（零闪烁隐藏） |
| 逐条对照 | 模型按 `Annotation 1: …` 逐条回应，回复中为可悬停芯片（回看原文+批注） |
| **Codex 式选中即引用**（增强①） | 选中文字后直接回车即自动附带引用，无需点「批注」保存；Esc 放弃快照 |
| **幽灵引用修复**（增强②） | 拼稿即清待发送集（原版依赖装饰扫描轮询清理存在竞态残留） |

来源：[omdsh-dev/dsh-annotation](https://github.com/omdsh-dev/dsh-annotation) v1.3.13（MIT），全部改动带 `PATCH(2026-08-14)` 标记，详见目录内 `README.md`。

## ⚙️ 环境要求

| 使用场景 | 要求 |
|---|---|
| 通用技能（vision / video / ppt / markitdown / automation） | Python 3.x + 各技能列出的 pip 依赖 |
| DSH 插件 | Node.js + DSH（`@deepseek-ai/dsh-tools`、`@deepseek-ai/dsh-credentials`） |
| dsh-vision-skill / vision-skill | 额外需要 Python 3 + Pillow，以及**任意 OpenAI 兼容多模态模型** API Key（Qwen-VL / MiniMax-M3 / Gemini / GPT-4o，默认 MiniMax-M3） |
| Hermes 插件 | Hermes 框架 |

## ❓ FAQ

**Q：通用技能和 DSH 插件怎么选？**
A：通用技能跨框架，任何 agent 都能挂载；DSH 插件是 DSH 原生扩展，走官方接缝（工具注册 / Credential / 上下文注入），能力更强但只适用于 DSH。两者能力互通——`dsh-vision-skill` 就是把 `General_skills/vision-skill` 包装成 DSH 原生插件。

**Q：我的模型不支持图片，能识图吗？**
A：能。直接贴图会被框架拒绝（`MODEL_DOES_NOT_SUPPORT_IMAGES`），改用两种方式：① 发图片的本地路径文本；② 截图后说"看图"，`vision_clipboard` 自动保存到工作区再识别。这是纯文本模型的能力门禁，不是插件问题。

**Q：视觉 API 用哪家？**
A：任意 OpenAI 兼容的多模态模型接口，通过 `VISION_API_URL` / `VISION_MODEL` / `VISION_API_KEY` 注入，不写死任何厂商。

**Q：子目录之间有关联吗？**
A：没有。每个子目录是**独立的自包含单元**，可单独使用、单独发布、单独删除。

## 🤝 贡献

- 每个子目录是独立的自包含单元，欢迎以 **PR** 提交新技能/插件，或提 **Issue** 反馈问题。
- 贡献要求：自包含（自带脚本/模板/文档）、许可证清晰（建议 MIT）、不写死密钥与本机绝对路径。
- 新增技能的入口文档统一为 `SKILL.md`，DSH 插件另附 `cordis.patch.yml` 与 `package.json`。

## 📄 许可

本仓库全部内容以 **MIT License** 分发。社区来源内容保留原作者署名（见各子目录 `SKILL.md` / `plugin.yaml` 头部）。
