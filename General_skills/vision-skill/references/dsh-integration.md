# 在 DeepSeek Harness（DSH）中接入本技能

面向人类安装者；智能体识图时不需要读本文。DSH 的 DeepSeek 适配器是纯文本路由，默认拒绝图片块，接入需三步：

1. **安装**：把本技能放到 DSH 用户技能根目录 `~/.dsh/skills/vision-skill/`（SKILL.md + scripts/ + templates/ + .env），skill-filesystem 会自动发现并注入会话目录。
2. **框架补丁**（必需，带 `[vision-skill patch]` 标记，包升级后需重打）：
   - `@deepseek-ai/dsh-host-apiproxy`：放开 `prompt` 与 `selectModel` 的图片门禁（`inputModalities` 检查改为 `false &&`，共 2 处）
   - `@deepseek-ai/dsh-llm-deepseek`：图片块不再抛 `UNSUPPORTED_CONTENT`，`flattenText` 改为序列化成带本地路径的文本占位符，格式：`[图片附件 sha256:<hash>，本地路径 <DSH_HOME>/attachments/v1/objects/<h[:2]>/<h>，模型不支持直接读图，请用 vision skill 读取]`
   - 重打补丁脚本按本机路径自备（幂等，建议含旧版→新版升级分支）
3. **模型配置**：技能目录 `.env` 填 `VISION_API_URL`（OpenAI 兼容完整地址）、`VISION_MODEL`、`VISION_API_KEY`；主模型保持纯文本即可，图片经占位符路径交给本脚本识别。

另有 DSH 原生插件版 `dsh-vision-skill`，是本技能的插件封装，走官方接缝、能力更强，但仅限 DSH。
