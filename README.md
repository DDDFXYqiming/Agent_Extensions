# Agent_Extensions

> ## 📦 DSH 插件已拆分为独立仓库
>
> 本仓库 `dsh-plugins/` 下的 DSH 插件已迁移为独立 GitHub 仓库，推荐直接安装独立仓库：
>
> | 插件 | 独立仓库 |
> |---|---|
> | dsh-vision-skill | https://github.com/DDDFXYqiming/dsh-vision-skill |
> | dsh-layered-memory | https://github.com/DDDFXYqiming/dsh-layered-memory |
> | dsh-annotation-patched | https://github.com/DDDFXYqiming/dsh-annotation-patched |
> | dsh-side-panel-patched | https://github.com/DDDFXYqiming/dsh-side-panel-patched |
> | dsh-ocr1-memory | https://github.com/DDDFXYqiming/dsh-ocr1-memory |
>
> 安装示例：
> ```bash
> dsh plugin --profile web add github:DDDFXYqiming/dsh-ocr1-memory
> ```
>
> 本仓库**不再维护 dsh 插件**，仅保留历史快照与说明；后续更新请以独立仓库为准。

**DeepSeek Harness（DSH）插件与 AI Agent 技能集合** —— 面向 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 的原生插件（走官方扩展接缝，零框架补丁）+ 跨框架通用 Skill + Hermes 插件，开箱即用。

![repo](https://img.shields.io/badge/agent-skills-4B8BBE) ![dsh](https://img.shields.io/badge/deepseek--harness-plugin-7A4FBF) ![license](https://img.shields.io/badge/license-MIT-green)

本仓库收集、翻译并**自包含封装** AI Agent 相关的技能资源，并面向 **DeepSeek Harness（DSH）** 提供标准插件形式的扩展。所有内容均为**自包含**（技能/插件内自带脚本、模板与文档，不依赖仓库外文件），克隆即可用。

## ✨ 内容总览

### 1️⃣ DSH 原生插件（dsh-plugins）—— 零框架补丁

面向 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 官方扩展接缝（`ctx.skills` / `ctx.tools` / `ctx.credentials` / `ctx.slots` / `ctx.layout`），可随 DSH 版本升级：

| 插件 | 能力 | 依赖 |
|---|---|---|
| `dsh-vision-skill` v0.4.4 | 识图插件：8 个工具（含渐进式暴露激活工具）+ Credential 化 + 路径围栏 | Node.js + DSH（`dsh-tools` / `dsh-credentials`）、Python 3 + Pillow、视觉模型 API Key |
| `dsh-layered-memory` v0.4 | 跨会话长期记忆：命名空间隔离 + L1 索引注入（存在性编码、KV 缓存友好）+ L2 环境事实 + L3 任务经验 + 自动蒸馏候选 + 溯源/归档/回滚 + 自动维护 | Node.js + DSH（`dsh-tools`） |
| `dsh-annotation-patched` | 选中批注/引用插件（fork 增强）：选中助手回复文字 → 批注（可空）或一键「引用」→ 回车随消息发送，回复按 `Annotation N` 逐条对照；增强：Codex 式「引用」按钮（显式确认制）+ 幽灵引用修复 | Node.js + DSH（纯浏览器端 bundle，零 Node 逻辑） |
| `dsh-side-panel-patched` | 右侧工作区面板（fork 增强）：文件树/多文件 tab/预览/编辑（CodeMirror）+ Git 审查 + 终端；增强：绕开官方 520px 宽度上限、头部像素级对齐、Codex 风格梭形拖拽把手、文件 tab 栈 + 会话跟踪、Windows 终端防崩溃 | Node.js + DSH（文件/Git/终端 API + 浏览器 bundle） |
| `dsh-ocr1-memory` v0.1.0 | 光学压缩记忆：文本渲染为 SoM 图像存储 + 年龄衰减 + active recall + OCR 驱动召回 | Node.js + DSH（`dsh-tools` / cordis / schemastery）、Python 3 + Pillow、可选 DeepSeek-OCR 后端 |

### 2️⃣ 通用技能（General_skills）—— 跨框架可用

任何智能体框架（Claude Code / Codex / opencode / DSH / Hermes 等）均可把目录作为 Skill 挂载：

| 技能 | 能力 | 依赖 |
|---|---|---|
| `vision-skill` | 识图：本地图片 → 视觉模型描述（Qwen 动态分辨率方法，OpenAI 兼容接口） | Python 3 + 视觉模型 API Key |
| `video-notes-generator` | 视频 URL → 结构化 Markdown 笔记（时间戳 / 抽取帧 / 多模态图像观察 / AI 总结），支持 Bilibili / YouTube / 抖音 / 快手 / 本地文件 | Python 3 + 依赖（见 `scripts/install_deps.sh`） |
| `ppt-master` | 源文档（PDF / DOCX / URL / Markdown）→ 多角色协作生成 SVG 页面 → 导出 PPTX | Python 3（标准库为主，可选依赖见 `requirements.txt`） |
| `markitdown-skill` | 微软 MarkItDown：PDF / DOCX / PPTX / XLSX / HTML / EPUB 等 → 统一 Markdown | Python 3 + `pip install -r requirements.txt` |
| `generic-agent-code-run` | GenericAgent 风格 `code_run`：Windows 桌面应用 / 真实浏览器自动化（Win32 / UIA / OCR / 截图 / CDP）+ 观察-行动-验证循环 | Python 3 + 对应库 |

> 所有技能均内置 `SKILL.md`（agent 运行时加载的指令），部分附 `scripts/`、`templates/`、`references/`。

### 3️⃣ Hermes 插件（hermes_plugins）

| 插件 | 能力 | 依赖 |
|---|---|---|
| [`language-router`](hermes_plugins/language-router/README.md) v5.0 | 自适应语言路由：Planner-first → Worker → 可选 Verifier → Digest 流程（NousResearch / Diana 出品），hooks 挂载 `pre_llm_call` / `pre_api_request` / `post_api_request` | Hermes 框架 |

## 📁 目录结构

```
Agent_Extensions/
├── dsh-plugins/               # DeepSeek Harness（DSH）原生插件
│   ├── dsh-vision-skill/      # 识图插件 v0.4.4（8 工具 + 渐进式暴露 + Credential 化）
│   ├── dsh-layered-memory/    # 分层长期记忆（v0.4：命名空间/自动蒸馏/自动维护）
│   ├── dsh-annotation-patched/ # 选中批注/引用插件（fork 增强，Codex 式选中即引用）
│   ├── dsh-side-panel-patched/ # 右侧工作区面板（fork 增强，多文件 tab + 会话跟踪）
│   └── dsh-ocr1-memory/        # 光学压缩记忆（SoM 图像 + active recall）

├── General_skills/            # 通用智能体技能（跨框架，挂载即用）
│   ├── vision-skill/          # 识图
│   ├── video-notes-generator/ # 视频转结构化笔记
│   ├── ppt-master/            # 文档 → SVG → PPTX
│   ├── markitdown-skill/      # 任意文档 → Markdown
│   └── generic-agent-code-run/ # Windows 桌面/浏览器自动化
├── hermes_plugins/            # Hermes 框架插件
│   └── language-router/       # 语言路由（planner-first）
└── README.md
```

## 🚀 快速开始

### 方式一：安装 DSH 插件（以 `dsh-vision-skill` 为例）

DSH 插件已拆分为独立仓库，推荐直接安装独立仓库：

```bash
# 1. 从独立仓库安装（自带 cordis.patch.yml，自动贡献 id: vision-skill）
dsh plugin --profile web add github:DDDFXYqiming/dsh-vision-skill

# 2. 配置 Credential（$DSH_HOME/.credentials.yaml）
VISION_API_KEY: sk-xxxx
```

> 本仓库 `dsh-plugins/` 下保留的是历史快照；各插件最新文档见对应独立仓库。


> ⚠️ bundle 安装后**不要**在 profile 的 `cordis.patch.yml` 里再 `insert` 同名条目，否则会触发 `duplicate loader entry id` 启动崩溃；需要自定义配置时用裸条目按 id 覆盖（见插件 README）。

### 方式二：挂载通用技能（任何框架）

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

### 方式三：安装 Hermes 插件

将 `hermes_plugins/language-router` 目录放入 Hermes 插件目录即可（`plugin.yaml` 声明了全部 hooks 与版本信息）。

## 🧩 DSH 插件能力一览

### dsh-vision-skill v0.4.4（8 工具 + 1 运行时 skill）

| 工具 | 能力 |
|---|---|
| `vision_analyze` | 识图（5 模式 + `mega` 超高清 16M 像素预算） |
| `vision_ocr` / `vision_long_screenshot_ocr` | 独立 OCR / 超长截图分块 OCR（带重叠切块 → 逐块识别 → 合并） |
| `vision_ground` / `vision_detect` | 目标定位 / 元素枚举（像素坐标框 + 归一化坐标） |
| `vision_dominant_colors` | 主色分析（本地像素算法，无需 API） |
| `vision_clipboard` | 剪贴板图片兜底（应对"当前模型不支持图片"粘贴拦截） |
| `vision_activate` | 渐进式暴露兜底：skill 加载后工具未自动出现时调用一次 |

工程化特性：**渐进式工具暴露**（全局只挂 1 个轻量激活工具，省上下文）、**密钥 Credential 化**（`credential: VISION_API_KEY` 引用，每操作解析）、**路径围栏**（realpath 校验防穿越）、**超时与并发门控**、**严格 JSON Schema 结构化输出**。

### dsh-layered-memory v0.4（分层长期记忆）

| 组件 | 说明 |
|---|---|
| `memory:index` 注入 | 通过 `ctx.systemPrompt.context` 每轮实时注入 L1 索引（存在性编码，读文件即生效，KV 缓存友好） |
| `memory`（运行时 skill） | 触发语义：何时读 / 何时写 / 何时同步索引 |
| `memory_activate` | 渐进式暴露兜底：skill 加载后工具未自动出现时调用一次 |
| `memory_list` / `memory_read` | 列出 / 读取记忆（index / fact / sop，含溯源 meta） |
| `memory_write` | 写入记忆（fact/sop，**evidence 必填** = 行动验证公理） |
| `memory_index` | 重建 L1 索引自动段（保留 `[RULES]` 手动段） |
| `memory_pending` / `memory_accept` | 自动蒸馏候选区：查看 / 确认入正式记忆 |
| `memory_update` / `memory_archive` / `memory_rollback` | 更新（supersede 保留历史）/ 归档 / 回滚 |
| `memory_expand` | 通过 `sessionQuery` 展开 sourceSession/sourceSeqs 原始事件 |
| `memory_stats` / `memory_maintain` | 统计 / 自动维护（去重、压缩索引、合并候选） |

核心特性：**命名空间隔离**（`<memoryDir>/<namespace>/...`，默认 workspace 目录 + git 分支）、**自动蒸馏**（turn/end 成功工具调用 → `pending/`，确认后才入正式记忆）、**自动维护**（`maintainEveryTurns` 默认 20）、**渐进式工具暴露**（`progressive: false` 可回退全局注册）。
核心公理：**行动验证**（No Execution, No Memory）、**神圣不可删改**（已验证事实可压缩迁移、严禁丢弃）、**禁易变状态**（时间戳/PID/临时路径不存）、**最小充分指针**（L1 只写存在性）。注入走 user-role 快照，**不破坏 DSH 的 KV 缓存命中率**（设计细节见插件 README）。

### dsh-annotation-patched（选中批注/引用，fork 增强）

| 能力 | 说明 |
|---|---|
| 选中批注 | 选中助手回复文字 → 批注（可留空）→ 回车随消息发送；自己的气泡不显示批注块（零闪烁隐藏） |
| 逐条对照 | 模型按 `Annotation 1: …` 逐条回应，回复中为可悬停芯片（回看原文+批注） |
| **Codex 式「引用」按钮**（增强①） | 选中文字 → 工具栏「引用」按钮 → 回车即带（空批注纯引用），显式确认制，复制/阅读选中不会误触发 |
| **幽灵引用修复**（增强②） | 拼稿即清待发送集（原版依赖装饰扫描轮询清理存在竞态残留） |

来源：[omdsh-dev/dsh-annotation](https://github.com/omdsh-dev/dsh-annotation) v1.3.13（MIT），全部改动带 `PATCH(2026-08-14)` 标记，详见目录内 `README.md`。

### dsh-side-panel-patched（右侧工作区面板，fork 增强）

| 能力 | 说明 |
|---|---|
| 文件树 + 多文件 tab | 文件树点文件 → 独立 tab（同时打开多个文件，切换/单关/查重激活），**树单例跟随**激活 tab、滚动位置跨 tab 保持 |
| 会话跟踪 | 切换工作区 → 树重载当前工作区；文件 tab **按会话分组**（各自保留、切换显示、互不串扰） |
| Git 审查 / 终端 | 工作区变更审查（stage/unstage）；终端 Windows 友好降级（Unix PTY 限制不崩溃） |
| 布局增强 | 绕开官方 520px 宽度上限（420~60% 视口自由拖宽）、头部与官方 header 像素级对齐、Codex 风格梭形拖拽把手、放大按钮全宽切换 |

来源：[ccq1/dsh-side-panel](https://github.com/ccq1/dsh-side-panel) v0.2.0（BSD-3-Clause），全部改动带 `PATCH(2026-08-14)` 标记，详见目录内 `README.md`。

## ⚙️ 环境要求

| 使用场景 | 要求 |
|---|---|
| DSH 插件 | Node.js + DSH（`@deepseek-ai/dsh-tools`、`@deepseek-ai/dsh-credentials`） |
| dsh-vision-skill / vision-skill | 额外需要 Python 3 + Pillow，以及**任意 OpenAI 兼容多模态模型** API Key（Qwen-VL / MiniMax-M3 / Gemini / GPT-4o，默认 MiniMax-M3） |
| 通用技能（vision / video / ppt / markitdown / automation） | Python 3.x + 各技能列出的 pip 依赖 |
| Hermes 插件 | Hermes 框架 |

## ❓ FAQ

**Q：通用技能和 DSH 插件怎么选？**
A：通用技能跨框架，任何 agent 都能挂载；DSH 插件是 DSH 原生扩展，走官方接缝（工具注册 / Credential / 上下文注入 / 布局插槽），能力更强但只适用于 DSH。两者能力互通——`dsh-vision-skill` 就是把 `General_skills/vision-skill` 包装成 DSH 原生插件。

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
