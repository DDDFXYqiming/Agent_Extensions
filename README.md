# Agent_Extensions

**AI Agent 技能与 DeepSeek Harness（DSH）扩展集合** —— 通用智能体 Skill 与 DSH 标准插件，开箱即用。

![repo](https://img.shields.io/badge/agent-skills-4B8BBE) ![dsh](https://img.shields.io/badge/deepseek--harness-plugin-7A4FBF)

本仓库收集、翻译并自包含封装 AI Agent 相关的技能资源，并面向 [DeepSeek Harness（DSH）](https://github.com/deepseek-ai/deepseek-harness) 提供标准插件形式的扩展。所有内容均为**自包含**（技能/插件内自带脚本、模板与文档），克隆即可用。

## 目录结构

```
Agent_Extensions/
├── General_skills/          # 通用智能体技能（Skill，跨框架可用）
│   └── vision-skill/        # 识图技能：MiniMax-M3 视觉模型，Qwen 动态分辨率方法
├── dsh-plugin/              # DeepSeek Harness（DSH）标准插件
│   └── dsh-vision-skill/    # 识图插件 v2.1：7 个工具 + 渐进式暴露 + Credential 化
├── hermes_plugins/          # Hermes 框架插件
│   └── language-router/     # 语言路由（planner-first）
└── README.md
```

## 快速开始

### 通用 Skill（General_skills）

任何智能体框架（Claude Code / Codex / opencode / DSH 等）都可以把 `General_skills/<skill>` 目录作为 Skill 挂载：

```powershell
# 示例：vision-skill（识图）
# 复制目录到你的 agent 的 skills 目录，按 skill 内 README/.env.example 配置视觉模型
```

### DSH 标准插件（dsh-plugin）

面向 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 的官方扩展接缝（`ctx.skills` / `ctx.tools` / `ctx.credentials`），**零框架补丁**：

```powershell
# 1. 克隆本仓库
git clone https://github.com/DDDFXYqiming/Agent_Extensions.git

# 2. 安装 dsh-vision-skill 插件（详见 dsh-plugin/README.md）
cd dsh-plugin
pnpm add "@deepseek-ai/dsh-tools@rc" "@deepseek-ai/dsh-credentials@rc"

# 3. link 进 web profile 并在 cordis.patch.yml 配置（credential 引用推荐）
```

插件能力一览（`dsh-vision-skill` v2.1）：

| 工具 | 能力 |
|---|---|
| `vision_analyze` | 识图（5 模式 + mega 超高清预算） |
| `vision_ocr` / `vision_long_screenshot_ocr` | 独立 OCR / 超长截图分块 OCR |
| `vision_ground` / `vision_detect` | 目标定位 / 元素枚举（像素坐标框） |
| `vision_dominant_colors` | 主色分析（本地算法，无需 API） |
| `vision_clipboard` | 剪贴板图片兜底 |

## 说明

- 每个子目录是独立的自包含单元，可单独使用、单独发布。
- 全部内容 MIT 许可。
- 欢迎提交技能/插件：见各子目录的 README 或直接提 PR。
