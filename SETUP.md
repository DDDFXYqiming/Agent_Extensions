# DSH 环境完整复刻指南（SETUP）

> **目标**：在一台全新电脑上，安装并配置出一份与开发机基本一致的 DeepSeek Harness（DSH）环境：
> web 宿主 + anysearch MCP + dsh-vision-skill（识图 7 工具）+ dsh-memory（跨会话记忆）+ 图片通道补丁（纯文本模型可贴图）。
> 本文档可由任何智能体/操作者逐步执行。

---

## 0. 前置依赖（先装好）

| 依赖 | 版本 | 用途 |
|---|---|---|
| Node.js | ≥ 24 | DSH 运行时 |
| pnpm | ≥ 10 | 插件依赖管理（`dsh plugin` 内部转发） |
| Python | ≥ 3.10 | vision 插件的识图脚本 |
| Pillow | 最新 | vision 脚本图像处理（`pip install pillow`） |
| git | 任意 | 克隆本仓库 |

验证：`node -v`、`pnpm -v`、`python --version`、`python -c "import PIL"`。

---

## 1. 安装 DSH

```powershell
npx @deepseek-ai/dsh web
```

- 首次运行创建 `$DSH_HOME`（默认 `C:\Users\<user>\.dsh`）与 `web` profile
- 浏览器打开 `http://127.0.0.1:3080` 完成初始设置（模型选择等）
- 安装位置：npm 全局（`npm root -g`）或 bun 全局（`~\.bun\install\global\node_modules`）——**记住路径，补丁脚本需要**

## 2. 准备密钥（用户提供，切勿写入仓库）

| 密钥 | 用途 | 存放位置 |
|---|---|---|
| `DEEPSEEK_API_KEY` | 主模型 | `$DSH_HOME\.credentials.yaml` 或设置页 |
| `VISION_API_KEY`（MiniMax-M3） | 识图模型 | `$DSH_HOME\.credentials.yaml` |
| `ANYSEARCH_API_KEY`（as_sk_ 开头） | 联网搜索 MCP | `$DSH_HOME\profiles\web\cordis.patch.yml`（MCP headers） |

```powershell
# .credentials.yaml 示例（追加）
Add-Content "$env:USERPROFILE\.dsh\.credentials.yaml" "VISION_API_KEY: sk-xxxx"
```

## 3. 克隆插件仓库

```powershell
git clone https://github.com/DDDFXYqiming/Agent_Extensions.git
cd Agent_Extensions\dsh-plugins\dsh-vision-skill
pnpm install   # 安装 dsh-tools / dsh-credentials / schemastery
cd ..\dsh-memory
pnpm install
```

> 若 pnpm 从 registry 装到旧版本，改用 link 全局版本：`pnpm add "link:<全局 node_modules>\@deepseek-ai\dsh-tools"`（版本必须与宿主一致）。

## 4. 安装插件（bundle 标准方式）

```powershell
dsh plugin --profile web add E:\...\Agent_Extensions\dsh-plugins\dsh-vision-skill
dsh plugin --profile web add E:\...\Agent_Extensions\dsh-plugins\dsh-memory
```

验证：`dsh --profile web --dump-config` 应看到 `# == dsh-vision-skill` 与 `# == dsh-memory` 两个 layer。

## 5. 配置 anysearch MCP

编辑 `$DSH_HOME\profiles\web\cordis.patch.yml` 追加（**`<ANYSEARCH_API_KEY>` 换成你的 key**）：

```yaml
- insert:
    - id: mcp-anysearch
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        transport: streamable-http
        serverName: anysearch
        url: https://api.anysearch.com/mcp
        headers:
          Authorization: 'Bearer <ANYSEARCH_API_KEY>'
          X-Anysearch-Client: 'mcp/1.0.0'
        toolCallTimeoutMs: 60000
```

> ⚠️ 不要在 profile 的 cordis.patch.yml 里重复 insert 已在 bundles 里的插件（`dsh-vision-skill`/`dsh-memory`）——`duplicate loader entry id` 会导致启动崩溃。

## 6. 应用图片通道补丁（关键步骤，唯一源码级改动）

**为什么需要**：deepseek-v4-flash 是纯文本模型，`dsh-host-apiproxy` 会拒绝任何含图片的消息（`MODEL_DOES_NOT_SUPPORT_IMAGES`），`dsh-llm-deepseek` 适配器也会拒绝 image block。补丁让"粘贴的图片 → 自动转成带本地路径的文本占位符"，模型看到路径后由 vision 插件识图。

**前置**：补丁 old 文本基于当前 rc 版本（2026-08 公测版）。若 DSH 已升级导致 old 文本不匹配，脚本会报 `old text not found`——此时按补丁注释意图（门禁加 `false &&`、图片块转路径占位符）手动适配。

```powershell
# 方式 A（推荐）：参数化脚本自动打补丁
powershell -ExecutionPolicy Bypass -File .\dsh-plugins\vision-patch\reapply-vision-patch.ps1
# 若未自动找到全局目录：-GlobalRoot "C:\Users\<user>\.bun\install\global\node_modules"

# 验证 4 处补丁已就位（应各命中 2 处标记）
Select-String "$root\@deepseek-ai\dsh-host-apiproxy\lib\index.js" -Pattern "vision-skill patch"
Select-String "$root\@deepseek-ai\dsh-llm-deepseek\lib\index.js" -Pattern "vision-skill patch"
```

**补丁内容摘要**（脚本内含完整 old/new 文本）：
1. `dsh-host-apiproxy` prompt 门禁：`if (modelInfo.inputModalities ...)` → `if (false && ...)`（放行）
2. `dsh-host-apiproxy` selectModel 门禁：同上（放行会话含图时的模型切换）
3. `dsh-llm-deepseek`：`import { homedir } from "node:os"` + `join`（路径回退用）
4. `dsh-llm-deepseek`：`blockToText` 图片块 → `[图片附件 sha256:...，本地路径 <DSH_HOME|~/.dsh>/attachments/v1/objects/xx/xxx...，模型不支持直接读图，请用 vision skill 读取]`；`assertTextOnly()` 变空操作

**回滚**：删除 `[vision-skill patch]` 标记的三处改动（或重装原包）。

## 7. 重启宿主并验证

```powershell
# 重启 web 宿主（Ctrl+C 后重新 npx @deepseek-ai/dsh web，或复用仓库的 restart 脚本）
```

验证清单：
1. `http://127.0.0.1:3080` 设置 → 插件：应看到 `vision-skill`、`memory`、`mcp-anysearch` 已启用
2. **CLI 自测（无需 GUI）**：
   ```powershell
   dsh --profile headless "调用 skill 工具加载 memory（name=memory），然后调用 memory_list 列出记忆"
   ```
3. **贴图测试**：输入框粘贴图片发送 → 模型应收到"带路径占位符"并自动调 `vision_analyze` 识图
4. 对话中应出现 `# [Memory Index - L1]` 注入（记忆索引每轮可见）

## 8. 记忆库种子（可选）

```powershell
Copy-Item Agent_Extensions\dsh-plugins\dsh-memory\examples\*.md "$env:USERPROFILE\.dsh\memory\sops\"
# 然后在会话里调用 memory_index 同步 L1 索引
```

## 9. 常见问题（FAQ）

| 症状 | 原因 | 解决 |
|---|---|---|
| 启动崩溃 `duplicate loader entry id` | profile patch 重复 insert 了 bundle 已有插件 | 删掉重复行；覆盖配置用**裸条目**（`- id: xxx` + config） |
| 补丁脚本报 `old text not found` | DSH 包升级源码变化 | 按补丁注释意图手动适配 |
| 插件工具不出现 | 渐进暴露未触发 | 先让模型加载对应 skill（`skill` 工具 name=vision/memory），或调 `vision_activate`/`memory_activate` |
| 贴图被拒 `attachment-error` | 补丁没生效/被升级覆盖 | 重跑 reapply 脚本 + 重启 |
| pnpm 装到旧版本依赖 | registry rc 版本滞后 | 用 `link:` 指向全局同版本 |
| 修改插件 lib/index.js 不生效 | node 不热加载 | 重启宿主；改 scripts/*.py 则即时生效 |
| edit 工具报 requires reading | DSH 文件策略 | 先 read 文件再 edit（正常流程） |

## 10. 与本环境一致的最终配置快照

- web profile bundles：`@deepseek-ai/dsh-base`、`@deepseek-ai/dsh-web-app`、`dsh-vision-skill`、`dsh-memory`
- vision 插件配置（默认即可）：`apiUrl=https://api.minimaxi.com/v1/chat/completions`、`model=MiniMax-M3`、`credential=VISION_API_KEY`（Config schema 默认值，无需显式写）
- memory 插件配置（默认即可）：`memoryDir=<home>/.dsh/memory`
- 补丁 4 处（见第 6 节）；凭证 2 个（DEEPSEEK + VISION）；MCP 1 个（anysearch）

---

*仓库配套文件：`dsh-plugins/vision-patch/reapply-vision-patch.ps1`（补丁脚本）、`dsh-plugins/dsh-vision-skill/`（识图插件）、`dsh-plugins/dsh-memory/`（记忆插件，含 templates/ 与 examples/）。*
