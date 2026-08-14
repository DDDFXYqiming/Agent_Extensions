# reapply-pi-ai-vision-patch.ps1
# 给 dsh-llm-pi-ai 打「图片→路径占位符」补丁（vision-skill patch v2 对齐 dsh-llm-deepseek 官方行为）
# 用法: 在 dsh npm 升级/重装后执行一次: powershell -File 本脚本
# 幂等: 已打补丁时自动跳过（检测 marker 注释）
$ErrorActionPreference = 'Stop'
$target = Join-Path $env:APPDATA "npm\node_modules\@deepseek-ai\dsh\node_modules\@deepseek-ai\dsh-llm-pi-ai\lib\index.js"

if (-not (Test-Path $target)) { Write-Error "未找到 dsh-llm-pi-ai/lib/index.js: $target"; exit 1 }

$content = Get-Content $target -Raw -Encoding UTF8
$marker = '[vision-skill patch v2]'

if ($content.Contains($marker)) {
    Write-Host "补丁已存在，跳过（幂等）。"
    exit 0
}

# 1) 插入 blockToTextPi 函数（imports 之后、//#region lib/types/replay.js 之前）
$anchor = '//#region lib/types/replay.js'
if (-not $content.Contains($anchor)) { Write-Error "锚点1缺失: $anchor"; exit 1 }
$fn = @'
/** [vision-skill patch v2] Render one image block to a path-bearing text placeholder. */
function blockToTextPi(block) {
	const ref = block.attachment;
	const id = typeof ref === "object" && ref !== null && typeof ref.attachmentId === "string" ? ref.attachmentId : "";
	const hex = id.startsWith("sha256:") ? id.slice(7) : "";
	const envHome = process.env.DSH_HOME;
	const home = typeof envHome === "string" && envHome.length > 0 ? envHome.replace(/[\\/]+$/, "") : `${process.env.USERPROFILE ?? ""}/.dsh`;
	const path = hex !== "" ? `${home}/attachments/v1/objects/${hex.slice(0, 2)}/${hex}` : "(路径不可推导)";
	const name = typeof ref === "object" && ref !== null && typeof ref.name === "string" ? `，文件名 ${ref.name}` : "";
	return `[图片附件 ${id}${name}，本地路径 ${path}，模型不支持直接读图，请用 vision skill 读取]`;
}
'@
$content = $content.Replace($anchor, "$fn$anchor")

# 2) 替换图片拒绝逻辑（纯文本模型 → 图片转路径占位符）
$old = 'const containsImage = options.messages.some((message) => contentHasImage(message.content));
				if (containsImage && !model.input.includes("image")) throw new LlmError(`pi-ai model "${model.id}" does not support image input`, "UNSUPPORTED_CONTENT");
				const attachments = containsImage ? this.config.resolveAttachments?.() : void 0;
				if (containsImage && attachments === void 0) throw new LlmError("pi-ai image input requires the durable attachment service", "UNSUPPORTED_CONTENT");
				const context = attachments === void 0 ? toPiContext(options) : await toPiContext(options, attachments);'

$new = 'let messages = options.messages;
				const containsImage = messages.some((message) => contentHasImage(message.content));
				if (containsImage && !model.input.includes("image")) {
					// [vision-skill patch v2] 图片→路径占位符：纯文本模型把 image 块转为带本地路径的文本块，
					// 模型看到路径后调用 vision skill 识别（对齐 dsh-llm-deepseek 官方行为）。
					messages = messages.map((message) => ({
						...message,
						content: Array.isArray(message.content) ? message.content.map((block) => block.type === "image" ? { type: "text", text: blockToTextPi(block) } : block) : message.content
					}));
					options = { ...options, messages };
				}
				const hasImage = messages.some((message) => contentHasImage(message.content));
				if (hasImage && !model.input.includes("image")) throw new LlmError(`pi-ai model "${model.id}" does not support image input`, "UNSUPPORTED_CONTENT");
				const attachments = hasImage ? this.config.resolveAttachments?.() : void 0;
				if (hasImage && attachments === void 0) throw new LlmError("pi-ai image input requires the durable attachment service", "UNSUPPORTED_CONTENT");
				const context = attachments === void 0 ? toPiContext(options) : await toPiContext(options, attachments);'

if (-not $content.Contains($old)) { Write-Error "锚点2缺失（图片拒绝逻辑未匹配，可能 DSH 版本已变化）"; exit 1 }
$content = $content.Replace($old, $new)

Set-Content -Path $target -Value $content -Encoding UTF8 -NoNewline
Write-Host "补丁已应用: $target"
node --check $target
if ($LASTEXITCODE -ne 0) { Write-Error "补丁后语法检查失败，请恢复原文件"; exit 1 }
Write-Host "语法 OK。重启 DSH 后生效。"
