# dsh-plugins / dsh-vision-skill

**DeepSeek Harness（DSH）标准插件版识图技能** —— 把本仓库 `General_skills/vision-skill`（源自 Qwen 官方动态分辨率方法）包装成 DSH 原生插件。

> 零框架补丁：插件本身只使用官方扩展接缝（`ctx.skills.register` / `ctx.tools.register` / `ctx.credentials` / `agent.ctx.tools`），可随 DSH 版本升级。仅当主模型走 pi-ai 适配器（opencode-go / 自定义 provider）且需要"直接贴图"时，需给宿主打一个幂等补丁（见下文[适配器支持矩阵](#图片投递机制与适配器支持矩阵)）。

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

Qwen 官方动态分辨率预处理（`smart_resize`：预算像素 + patch 网格吸附）→ **任意 OpenAI 兼容多模态模型**（默认 MiniMax-M3，`thinking: disabled` 关闭思考，可替换）。Grounding 采用 Qwen 官方方法：VLM 输出 0-1000 归一化 bbox → 解析 JSON / `<ref><box>` 双格式 → 映射像素坐标。

## 目录结构

```
dsh-vision-skill/
├── lib/index.js          # 插件主体（skill 注册 + 7 工具 + 渐进暴露 + 围栏）
├── scripts/vision.py     # 识图脚本（动态分辨率 / OCR / grounding / 主色 / 长图分块）
├── scripts/reapply-pi-ai-vision-patch.ps1  # pi-ai 适配器「图片→路径」幂等补丁脚本（dsh 升级后重跑）
├── SKILL.md              # 运行时 skill 内容（模型按需加载）
├── package.json          # 插件包声明（peerDependencies: dsh-tools / dsh-credentials / schemastery）
└── templates/.env.example # 脚本独立运行时的配置模板
```

## 安装

### 方式一：本地 link（开发/直装，推荐）

```powershell
# 1. 克隆仓库（或已有）
git clone https://github.com/DDDFXYqiming/Agent_Extensions.git
cd Agent_Extensions\dsh-plugins\dsh-vision-skill

# 2. （可选）本地开发依赖：peer 包由 DSH 自带（dsh-base 提供 @deepseek-ai/dsh-tools 等），
#    无需在插件目录单独安装；若脚本独立运行需要类型/工具，可临时加：
#    pnpm add -D "@deepseek-ai/dsh-tools@rc" "@deepseek-ai/dsh-credentials@rc"

# 3. 注册到 web profile（link 方式，改源码即时生效）
#    在 C:\Users\<user>\.dsh\profiles\web\package.json 的 dependencies 加：
#    "dsh-vision-skill": "link:<绝对路径>\dsh-plugins\dsh-vision-skill"
#    然后在该目录执行 pnpm install
```

### 方式二：插件命令（推荐，bundle 标准安装）

```powershell
dsh plugin --profile web add <绝对路径>\dsh-plugins\dsh-vision-skill
```

安装后插件包自带的 `cordis.patch.yml` 会自动贡献 `id: vision-skill` 条目（进 profile 的 bundles 列表），**无需手动 insert**。配置默认值由插件内置的 Schemastery Config schema 提供（`apiUrl`=MiniMax / `model`=MiniMax-M3 / `credential`=VISION_API_KEY）。

### 配置（覆盖 bundle 默认值）

⚠️ **重要**：bundle 方式安装后，**不要**在 profile 的 `cordis.patch.yml` 里再 `insert` 一个 `id: vision-skill`——重复 id 会导致 `duplicate loader entry id` 启动崩溃。需要自定义配置时，用**裸条目按 id 覆盖**（不带 `insert:` 包装）：

```yaml
# profile cordis.patch.yml —— 裸条目覆盖 bundle 行（后写者胜，config 整行替换）
- id: vision-skill
  config:
    apiUrl: '<你的多模态模型 OpenAI 兼容接口地址>'  # 如 https://api.minimaxi.com/v1/chat/completions
    model: '<模型名>'                                # 如 MiniMax-M3 / qwen-vl-plus / gemini-2.5-flash
    credential: 'VISION_API_KEY'   # 推荐：DSH Credential 引用
    # apiKey: '<明文 key>'         # 兼容旧方式（不推荐）
```

覆盖时只写要改的字段即可？——**不行**：patch 会替换目标行的**整个** config（不深合并），所以覆盖时要把需要保留的默认字段也一起写上（如上面的 apiUrl/model/credential 全量）。也可以不覆盖——直接用内置默认值（MiniMax-M3 + VISION_API_KEY 凭证引用），此时 profile 无需任何 vision-skill 行。

Credential 值存到 `$DSH_HOME/.credentials.yaml`：

```yaml
VISION_API_KEY: sk-xxxx
```

补丁层支持热重载（无需重启）；**修改插件源码（lib/index.js）后需重启宿主**。

## 依赖

- Node.js + DSH（`@deepseek-ai/dsh-tools`、`@deepseek-ai/dsh-credentials`、`@deepseek-ai/schemastery`）
- Python 3 + Pillow（`pip install pillow`；`vision.py --check` 自检）
- 视觉模型 API Key（**任意 OpenAI 兼容的多模态模型**：Qwen-VL / MiniMax-M3 / Gemini / GPT-4o 等，默认 MiniMax-M3）

## 图片怎么喂给插件（三种方式）

插件的所有工具只接收**图片的本地路径（文本）**，不接收图片本体。三种喂图方式：

| 方式 | 操作 | 适用环境 |
|---|---|---|
| ① 路径直发 | 图片已在本地（或放一份到工作区），对话框发路径文本："识别这张图 `E:\...\xxx.png`" | **所有环境** |
| ② 剪贴板 | Win+Shift+S 截屏（图片自动进剪贴板）→ 对话框说"看图"，`vision_clipboard` 自动保存到工作区 `.dsh-vision/` 再识别 | **所有环境** |
| ③ 直接贴图 | 输入框粘贴图片直接发送，适配器自动转为带路径的文本占位符 → 模型看到路径 → 自动调 `vision_analyze` | 见下方适配器支持矩阵 |

## 图片投递机制与适配器支持矩阵

**原理**：贴图时图片存入 DSH 附件库（`$DSH_HOME/attachments/v1/objects/<sha256前2位>/<sha256>`），适配器把 image 块转换为**带本地路径的文本占位符**（`[图片附件 sha256:...，本地路径 ...，请用 vision skill 读取]`）——纯文本主模型收到的是路径文本，再调用 `vision_analyze` 识别。**看图能力来自本插件（独立多模态 API），主模型只需能读文本路径 + 调工具**；转换发生在适配器层，模型本身始终收不到图片。

| 适配器 / 场景 | 直接贴图（方式③） | 说明 |
|---|---|---|
| `dsh-llm-deepseek`（deepseek-official） | ✅ 开箱即用 | DSH 新版**原生内置**图片→路径转换（源自 vision-skill patch v2，官方已采纳） |
| `dsh-llm-pi-ai`（opencode-go / 自定义 OpenAI 兼容 provider） | ⚠️ 需打补丁 | 原生逻辑会拒绝（`UNSUPPORTED_CONTENT`）；打补丁后与官方行为一致；不打补丁时用方式 ①/② 仍正常 |
| 多模态模型（`input` 含 image） | ✅ 图片直达 | 无需转换（模型原生看图） |

**零补丁环境说明**：未打补丁的 pi-ai 适配器下，直接贴图会被拒绝（`UNSUPPORTED_CONTENT`——纯文本模型的能力门禁，不是插件问题）。此时请用方式 ①/②，插件即可正常工作（社区插件 [dsh-vision-toolkit](https://github.com/Anionex/dsh-vision-toolkit) 的 FAQ 同样要求用户"把文件放进工作区以路径形式使用"）。

### pi-ai 适配器补丁（opencode-go 等）

DSH 的 pi-ai 多提供方适配器（`dsh-llm-pi-ai`，用于 opencode-go / 自定义 provider）尚未内置图片→路径转换。本插件提供**幂等补丁脚本**：

```powershell
# 在 dsh npm 升级/重装后执行一次（幂等：已打补丁自动跳过）
powershell -File scripts\reapply-pi-ai-vision-patch.ps1
# 然后重启 DSH 宿主生效
```

- 补丁内容：给 `dsh-llm-pi-ai/lib/index.js` 打两处补丁——`zen-ua`（OpenCode Zen 免费层只认 `opencode/<ver>` User-Agent）+ `image→path`（图片转路径占位符，格式与官方 `dsh-llm-deepseek` 完全一致，保证 vision 工作流格式统一）
- ⚠️ **该脚本是作者机器级维护工具**（硬编码本机 `.dsh/profiles` 路径，改的是 node_modules 里的 vendor 包），**随包分发时已从 files 白名单排除**；他机使用需先修改脚本顶部的 `$piAi` 路径
- **dsh 升级后需重跑脚本**（node_modules 被覆盖）；改 `lib/index.js` 后需重启宿主
- 补丁只影响 pi-ai 适配器的纯文本模型（`input` 不含 image）；真正多模态的模型不受影响

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
- 通用技能源：[General_skills/vision-skill](../../General_skills/vision-skill)
- ⚠️ **同名技能冲突**：本插件以 `runtime` 层注册技能名 `vision`；若同时在 `$DSH_HOME/skills`（user 层）或项目 `.dsh/skills`（project 层）安装了同名技能，按官方优先级 project > runtime > user，可能互相遮蔽——建议二选一安装
- 授权：MIT
