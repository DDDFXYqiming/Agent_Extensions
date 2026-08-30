简体中文 | [English](README.en.md)

# Agent_Extensions

这个仓库收了三类东西。DSH 原生插件面向 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)，走官方扩展接缝，不打框架补丁。通用 Skill 不绑框架，Hermes 插件给 Hermes 框架用。每一项都自包含，脚本、模板和文档就在各自目录里，克隆下来以后，要哪个目录拿哪个，单独就能用。

> **📦 DSH 插件已拆分为独立仓库**。本仓库 `dsh-plugins/` 下的 DSH 插件已迁移为独立 GitHub 仓库，推荐直接安装独立仓库。
>
> | 插件 | 独立仓库 |
> |---|---|
> | dsh-vision-skill | https://github.com/DDDFXYqiming/dsh-vision-skill |
> | dsh-layered-memory | https://github.com/DDDFXYqiming/dsh-layered-memory |
> | dsh-annotation-patched | https://github.com/DDDFXYqiming/dsh-annotation-patched |
> | dsh-side-panel-patched | https://github.com/DDDFXYqiming/dsh-side-panel-patched |
> | dsh-ocr1-memory | https://github.com/DDDFXYqiming/dsh-ocr1-memory |
>
> 本仓库**不再维护 dsh 插件**，`dsh-plugins/` 只保留历史快照与说明。后续更新请以独立仓库为准。

## 内容总览

### 1️⃣ DSH 原生插件（`dsh-plugins/`，历史快照）

这一组只作留档，日常安装请用上面的独立仓库。各插件能做什么，见下表。

| 插件 | 一句话能力 | 详细 |
|---|---|---|
| `dsh-vision-skill` v0.4.4 | 8 工具识图（含渐进式暴露激活工具）+ Credential 化 + 路径围栏 | [README](dsh-plugins/dsh-vision-skill/) |
| `dsh-layered-memory` v0.4 | 跨会话长期记忆（命名空间隔离 + L1 索引注入 + 自动蒸馏候选 + 溯源/归档/回滚 + 自动维护） | [README](dsh-plugins/dsh-layered-memory/) |
| `dsh-annotation-patched` | 选中批注/引用（fork 增强，Codex 式「引用」按钮 + 幽灵引用修复） | [README](dsh-plugins/dsh-annotation-patched/) |
| `dsh-side-panel-patched` | 右侧工作区面板（fork 增强，绕开 520px 上限 + 多文件 tab + 会话跟踪） | [README](dsh-plugins/dsh-side-panel-patched/) |
| `dsh-ocr1-memory` v0.1.0 | 光学压缩记忆（文本 → SoM 图像存储 + 年龄衰减 + active recall） | [README](dsh-plugins/dsh-ocr1-memory/) |

### 2️⃣ 通用技能（`General_skills/`，跨框架）

任何智能体框架（Claude Code / Codex / opencode / DSH / Hermes 等）都能把这里的目录作为 Skill 挂载。

| 技能 | 一句话能力 | 依赖 |
|---|---|---|
| `vision-skill` | 识图，本地图片 → 视觉模型描述（Qwen 动态分辨率，OpenAI 兼容） | Python 3 + 视觉模型 API Key |
| `video-notes-generator` | 视频 URL → 结构化 Markdown 笔记（时间戳 / 抽取帧 / 多模态观察 / AI 总结），支持 B 站 / YouTube / 抖音 / 快手 | Python 3 + 见 `scripts/install_deps.sh` |
| `ppt-master` | 源文档 → SVG 页面 → PPTX | Python 3（标准库为主） |
| `markitdown-skill` | PDF / DOCX / PPTX / XLSX / HTML / EPUB → Markdown | Python 3 + `pip install -r requirements.txt` |
| `generic-agent-code-run` | Windows 桌面应用 / 真实浏览器自动化（Win32 / UIA / OCR / 截图 / CDP） | Python 3 + 对应库 |

> 所有技能均内置 `SKILL.md`（agent 运行时加载的指令），部分附 `scripts/`、`templates/`、`references/`。

### 3️⃣ Hermes 插件（`hermes_plugins/`）

| 插件 | 一句话能力 | 依赖 |
|---|---|---|
| [`language-router`](hermes_plugins/language-router/) v5.0 | 自适应语言路由，流程为 Planner-first → Worker → 可选 Verifier → Digest（hooks 挂载 `pre_llm_call` 等） | Hermes 框架 |

## 目录结构

```
Agent_Extensions/
├── dsh-plugins/               # DSH 原生插件（历史快照，已拆分为独立仓库，详见顶部迁移表）
├── General_skills/            # 通用技能（跨框架，挂载即用）
│   ├── vision-skill/
│   ├── video-notes-generator/
│   ├── ppt-master/
│   ├── markitdown-skill/
│   └── generic-agent-code-run/
├── hermes_plugins/            # Hermes 框架插件
│   └── language-router/
└── README.md
```

## 🚀 快速开始

三种装法对应上面三类内容，按你用的框架挑一种就行。

### 方式一 安装 DSH 插件（推荐直接装独立仓库）

```bash
# 以 dsh-vision-skill 为例
dsh plugin --profile web add github:DDDFXYqiming/dsh-vision-skill

# 配置 Credential（$DSH_HOME/.credentials.yaml）
VISION_API_KEY: sk-xxxx
```

> ⚠️ bundle 安装后再在 profile 的 `cordis.patch.yml` 里 `insert` 同名条目，会触发 `duplicate loader entry id` 启动崩溃。需要自定义配置时，用裸条目按 id 覆盖（见各插件 README）。

### 方式二 挂载通用技能（任何框架）

以 `vision-skill` 为例。

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

### 方式三 安装 Hermes 插件

把 `hermes_plugins/language-router` 目录放进 Hermes 的插件目录即可。`plugin.yaml` 里声明了全部 hooks 与版本信息。

## ⚙️ 环境要求

| 使用场景 | 要求 |
|---|---|
| DSH 插件 | Node.js + DSH（`@deepseek-ai/dsh-tools`、`@deepseek-ai/dsh-credentials`） |
| dsh-vision-skill / vision-skill | 额外需要 Python 3 + Pillow，以及**任意 OpenAI 兼容多模态模型** API Key（Qwen-VL / MiniMax-M3 / Gemini / GPT-4o，默认 MiniMax-M3） |
| 通用技能（vision / video / ppt / markitdown / automation） | Python 3.x + 各技能列出的 pip 依赖 |
| Hermes 插件 | Hermes 框架 |

## ❓ FAQ

**通用技能和 DSH 插件怎么选？**

通用技能跨框架。DSH 插件走官方接缝，能力更强，但仅限 DSH。两者互通，`dsh-vision-skill` 就是 `General_skills/vision-skill` 的 DSH 原生封装。

**我的模型不支持图片，能识图吗？**

能。一是发图片的本地路径文本。二是截图后说一句“看图”，`vision_clipboard` 会自动保存到工作区再识别。这个限制来自纯文本模型的能力门禁，与插件无关。

**视觉 API 用哪家？**

任意 OpenAI 兼容多模态接口都行，通过 `VISION_API_URL` / `VISION_MODEL` / `VISION_API_KEY` 注入，不写死厂商。

**子目录之间有关联吗？**

没有。每个子目录都是**独立的自包含单元**，可以单独使用、发布或删除。

## 🤝 贡献

- 每个子目录是独立的自包含单元，欢迎以 **PR** 提交新技能/插件，或提 **Issue** 反馈问题
- 贡献要求
  - 内容自包含，自带脚本、模板与文档
  - 许可证清晰，建议 MIT
  - 不写死密钥与本机绝对路径
- 新增技能的入口文档统一为 `SKILL.md`，DSH 插件另附 `cordis.patch.yml` 与 `package.json`

## 📄 许可

本仓库全部内容以 **MIT License** 分发。社区来源内容保留原作者署名（见各子目录 `SKILL.md` / `plugin.yaml` 头部）。
