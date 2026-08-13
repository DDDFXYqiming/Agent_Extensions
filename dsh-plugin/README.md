# dsh-plugin / dsh-vision-skill

**DeepSeek Harness（DSH）标准插件版识图技能** —— 把本仓库 `General_skills/vision-skill`（源自 Qwen 官方动态分辨率方法）包装成 DSH 原生插件。

> 零框架补丁：只使用官方扩展接缝（`ctx.skills.register` / `ctx.tools.register` / `ctx.credentials` / `agent.ctx.tools`），可随 DSH 版本升级。

## 能力一览（7 工具 + 1 运行时 skill）

| 名称 | 说明 |
|---|---|
| `vision`（运行时 skill） | 模型按需加载的识图指令；加载后自动激活下列工具（渐进式暴露） |
| `vision_analyze` | 识别本地图片（5 模式 + `budget` 含 `mega` 超高清 16M 像素） |
| `vision_ocr` | 独立 OCR：提取全部可见文字，保持原始排版 |
| `vision_ground` | 定位目标（如「微信图标」），返回像素坐标框 + 归一化坐标 |
| `vision_detect` | 枚举一类元素（默认所有 UI 元素），编号 + 像素坐标框 |
| `vision_dominant_colors` | 主色分析（本地像素算法，无需视觉 API） |
| `vision_long_screenshot_ocr` | 超长截图分块 OCR：切块（带重叠）→ 逐块识别 → 合并全文 |
| `vision_clipboard` | 剪贴板图片兜底识别（应对"当前模型不支持图片"粘贴拦截） |
| `vision_activate` | 渐进式暴露兜底：skill 加载后工具未自动出现时调用一次 |

## 工程化特性

- **渐进式工具暴露**：全局只挂 1 个轻量激活工具，完整工具集在 skill 加载成功后按 Agent 挂载（省上下文）；`progressive: false` 可回退为全局注册。
- **密钥 Credential 化**：config 支持 `credential: VISION_API_KEY`（DSH Credential 引用，每操作解析，推荐）或 `apiKey`（兼容旧配置，不推荐明文）。
- **路径围栏**：图片路径必须位于会话工作区 / DSH 附件目录 / `allowedDirs` 之一（realpath 校验，防穿越）。
- **超时与并发门控**：`timeoutMs`（默认 180s）与 `concurrency`（默认 2）可配置。
- **结构化输出**：全部工具返回严格 JSON Schema 定义的结构化结果。

## 识图核心方法

Qwen 官方动态分辨率预处理（`smart_resize`：预算像素 + patch 网格吸附）→ OpenAI 兼容 VLM（默认 **MiniMax-M3**，`thinking: disabled` 关闭思考，中文优先）。Grounding 采用 Qwen 官方方法：VLM 输出 0-1000 归一化 bbox → 解析 JSON / `<ref><box>` 双格式 → 映射像素坐标。

## 目录结构

```
dsh-plugin/
├── lib/index.js          # 插件主体（skill 注册 + 7 工具 + 渐进暴露 + 围栏）
├── scripts/vision.py     # 识图脚本（动态分辨率 / OCR / grounding / 主色 / 长图分块）
├── SKILL.md              # 运行时 skill 内容（模型按需加载）
├── package.json          # 插件包声明（peerDependencies: dsh-tools / dsh-credentials）
└── templates/.env.example # 脚本独立运行时的配置模板
```

## 安装

### 方式一：本地 link（开发/直装，推荐）

```powershell
# 1. 克隆仓库（或已有）
git clone https://github.com/DDDFXYqiming/Agent_Resources.git
cd Agent_Resources\dsh-plugin

# 2. 安装依赖（dsh-tools / dsh-credentials 从 registry 或 link 全局）
pnpm add "@deepseek-ai/dsh-tools@rc" "@deepseek-ai/dsh-credentials@rc"

# 3. 注册到 web profile（link 方式，改源码即时生效）
#    在 C:\Users\<user>\.dsh\profiles\web\package.json 的 dependencies 加：
#    "dsh-vision-skill": "link:<绝对路径>\dsh-plugin"
#    然后在该目录执行 pnpm install
```

### 方式二：插件命令

```powershell
dsh plugin --profile web add <绝对路径>\dsh-plugin
```

### 配置（cordis.patch.yml）

```yaml
- insert:
    - id: vision-skill
      name: 'dsh-vision-skill'
      config:
        apiUrl: 'https://api.minimaxi.com/v1/chat/completions'
        model: 'MiniMax-M3'
        credential: 'VISION_API_KEY'   # 推荐：DSH Credential 引用
        # apiKey: '<明文 key>'         # 兼容旧方式（不推荐）
```

Credential 值存到 `$DSH_HOME/.credentials.yaml`：

```yaml
VISION_API_KEY: sk-xxxx
```

补丁层支持热重载（无需重启）；**修改插件源码（lib/index.js）后需重启宿主**。

## 依赖

- Node.js + DSH（`@deepseek-ai/dsh-tools`、`@deepseek-ai/dsh-credentials`）
- Python 3 + Pillow（`pip install pillow`；`vision.py --check` 自检）
- 视觉模型 API Key（默认 MiniMax-M3；任意 OpenAI 兼容端点均可）

## 使用示例

```
识别这张图 <路径>          → vision_analyze
OCR 这张图 <路径>          → vision_ocr
在这张图里找到 <目标>      → vision_ground（返回像素坐标框）
清点这张图的所有按钮       → vision_detect
这张图的主色是什么         → vision_dominant_colors（本地算法，不耗 API）
提取这段长聊天记录的文字   → vision_long_screenshot_ocr
看图（剪贴板截图）         → vision_clipboard
```

## 相关

- 脚本独立运行：见 `templates/.env.example`，`python scripts/vision.py <图> --check`
- 通用技能源：[General_skills/vision-skill](../General_skills/vision-skill)
- 授权：MIT
