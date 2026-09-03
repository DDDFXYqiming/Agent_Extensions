简体中文 | [English](README.en.md)

# Agent_Extensions

跨框架的 **Agent Skills** 合集。仓库里有两类东西：通用技能（`General_skills/`）不绑框架，任何智能体都能把目录当 Skill 挂载；Hermes 插件（`hermes_plugins/`）给 Hermes 框架用。每一项都自包含，脚本、模板和文档就在各自目录里，克隆下来以后要哪个目录拿哪个，单独就能用。

> **DSH 插件不在本仓库**。DeepSeek Harness（DSH）插件已全部拆分为独立仓库，直接装独立仓库即可：
>
> | 插件 | 独立仓库 |
> |---|---|
> | dsh-vision-skill | https://github.com/DDDFXYqiming/dsh-vision-skill |
> | dsh-layered-memory | https://github.com/DDDFXYqiming/dsh-layered-memory |
> | dsh-annotation-patched | https://github.com/DDDFXYqiming/dsh-annotation-patched |
> | dsh-side-panel-patched | https://github.com/DDDFXYqiming/dsh-side-panel-patched |
> | dsh-ocr1-memory | https://github.com/DDDFXYqiming/dsh-ocr1-memory |
>
> 本仓库不再收录 DSH 插件源码与快照。

## 内容总览

### 1️⃣ 通用技能（`General_skills/`，跨框架）

任何智能体框架（Claude Code / Codex / opencode / DSH / Hermes 等）都能把这里的目录作为 Skill 挂载。

| 技能 | 一句话能力 | 依赖 |
|---|---|---|
| [`vision-skill`](General_skills/vision-skill/) | 识图：本地图片 → 视觉模型描述（Qwen 动态分辨率，OpenAI 兼容接口） | Python 3 + Pillow + 视觉模型 API Key |
| [`video-notes-generator`](General_skills/video-notes-generator/) | 视频 → 结构化 Markdown 笔记（字幕/转写、时间戳、抽帧、多模态观察），支持 B 站 / YouTube / 抖音 / 快手 / 本地文件 | Python 3 + yt-dlp + ffmpeg，见 `scripts/install_deps.sh` |
| [`generic-agent-code-run`](General_skills/generic-agent-code-run/) | Windows 桌面应用与真实浏览器自动化（Win32 / UIA / OCR / 截图 / CDP），observe-act-verify 循环 | Python 3 + 对应库，Windows |

> 每个技能都有 `SKILL.md`（智能体运行时加载的指令），按需附 `scripts/`、`templates/`、`references/`。
>
> 本仓库只收录自己写的技能。上游公开项目（如 [microsoft/markitdown](https://github.com/microsoft/markitdown)、[hugohe3/ppt-master](https://github.com/hugohe3/ppt-master)）不在此镜像，请直接装上游。

### 2️⃣ Hermes 插件（`hermes_plugins/`）

| 插件 | 一句话能力 | 依赖 |
|---|---|---|
| [`language-router`](hermes_plugins/language-router/) v5.0 | 自适应语言路由，流程为 Planner-first → Worker → 可选 Verifier → Digest（hooks 挂载 `pre_llm_call` 等） | Hermes 框架 |

## 目录结构

```
Agent_Extensions/
├── General_skills/            # 通用技能（跨框架，挂载即用）
│   ├── vision-skill/
│   ├── video-notes-generator/
│   └── generic-agent-code-run/
├── hermes_plugins/            # Hermes 框架插件
│   └── language-router/
└── README.md
```

## 🚀 快速开始

### 挂载通用技能（任何框架）

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

其他技能用法详见各目录内 `SKILL.md`。`video-notes-generator` 还需要 `yt-dlp` 与 `ffmpeg` 在 PATH 上。

### 安装 Hermes 插件

把 `hermes_plugins/language-router` 目录放进 Hermes 的插件目录即可。`plugin.yaml` 里声明了全部 hooks 与版本信息。

### 用 DSH？

DSH 插件走独立仓库，安装方式见上表各仓库的 README。本仓库的通用技能也能在 DSH 里当 Skill 挂载；`vision-skill` 的 DSH 接入步骤（含框架补丁说明）见 [General_skills/vision-skill/references/dsh-integration.md](General_skills/vision-skill/references/dsh-integration.md)。

## ⚙️ 环境要求

| 使用场景 | 要求 |
|---|---|
| vision-skill | Python 3 + Pillow，以及**任意 OpenAI 兼容多模态模型** API Key（Qwen-VL / MiniMax-M3 / Gemini / GPT-4o，默认 MiniMax-M3） |
| video-notes-generator | Python 3 + `yt-dlp` + `ffmpeg`；无字幕时走 faster-whisper 本地转写（可选独显加速，自动探测） |
| generic-agent-code-run | Windows + Python 3，按需装 pywin32 / Pillow / uiautomation / pyperclip |
| Hermes 插件 | Hermes 框架 |

## ❓ FAQ

**通用技能和 DSH 插件怎么选？**

通用技能跨框架，克隆目录挂载即用。DSH 插件走官方扩展接缝，能力更强（Credential 化、渐进式工具暴露等），但仅限 DSH，且各自有独立仓库。两者同源互通：`dsh-vision-skill` 就是本仓库 `General_skills/vision-skill` 的 DSH 原生封装。

**我的模型不支持图片，能识图吗？**

能。把图片的本地路径交给技能，`vision-skill` 会调用你配置的多模态接口拿回文字描述，再基于描述回答；先整体读一遍，对小字和报错区域用 `--crop` 放大复读。

**视觉 API 用哪家？**

任意 OpenAI 兼容多模态接口都行，通过 `VISION_API_URL` / `VISION_MODEL` / `VISION_API_KEY` 注入，不写死厂商。

**子目录之间有关联吗？**

没有。每个子目录都是**独立的自包含单元**，可以单独使用、发布或删除。

## 🤝 贡献

- 每个子目录是独立的自包含单元，欢迎以 **PR** 提交新技能，或提 **Issue** 反馈问题
- 贡献要求
  - 内容自包含，自带脚本、模板与文档
  - 许可证清晰，建议 MIT
  - 不写死密钥与本机绝对路径
  - 入口文档为 `SKILL.md`，符合 [Agent Skills 规范](https://agentskills.io/specification)：`name` 与目录同名，`description` 说清「做什么 + 何时用」，正文只放智能体执行时会照做的指令，人类向文档与版本历史拆到 `references/` 与 `CHANGELOG.md`
- DSH 插件请开独立仓库，不进本仓库

## 📄 许可

本仓库全部内容以 **MIT License** 分发。社区来源内容保留原作者署名（见各子目录 `SKILL.md` 头部）。
