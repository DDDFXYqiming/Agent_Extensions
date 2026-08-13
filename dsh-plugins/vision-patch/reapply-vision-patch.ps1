# reapply-vision-patch.ps1
# [vision-skill patch] 幂等重打"图片门禁放开"补丁（v2：占位符路径支持 homedir 回退）。
# 用途：dsh 包升级（bun update / dsh plugin 重装 / npm update）会覆盖 node_modules 里的改动，
# 升级后运行本脚本即可恢复；对当前已打 v1 补丁的文件会自动升级到 v2。运行后需重启 dsh web 宿主。
# 回滚：删除三处 [vision-skill patch] 改动即可（或重新安装原包）。
#
# 用法（自动发现全局安装路径，兼容 npm 与 bun）：
#   powershell -ExecutionPolicy Bypass -File .\reapply-vision-patch.ps1
# 可选：-GlobalRoot <绝对路径> 手动指定全局 node_modules 目录。

param(
    [string]$GlobalRoot = ''
)

$ErrorActionPreference = 'Stop'

function Resolve-GlobalNodeModules {
    # 尝试常见全局安装位置
    $candidates = @()
    if ($GlobalRoot) { $candidates += $GlobalRoot }
    try { $candidates += (npm root -g 2>$null) } catch { }
    $candidates += "$env:USERPROFILE\.bun\install\global\node_modules"
    $candidates += "$env:APPDATA\npm\node_modules"
    foreach ($c in $candidates) {
        if ($c -and (Test-Path (Join-Path $c '@deepseek-ai'))) { return $c }
    }
    throw "未找到 @deepseek-ai 全局安装目录。请用 -GlobalRoot 指定（例如 bun 安装: $env:USERPROFILE\.bun\install\global\node_modules）"
}

$root = Resolve-GlobalNodeModules
$apiproxy = Join-Path $root '@deepseek-ai\dsh-host-apiproxy\lib\index.js'
$llmDeepseek = Join-Path $root '@deepseek-ai\dsh-llm-deepseek\lib\index.js'
Write-Host "全局根: $root"

function Patch-File {
    param([string]$Path, [string]$Old, [string]$New, [string]$Label, [string]$SkipMarker)
    if (-not (Test-Path $Path)) { throw "FAIL  $Label : 文件不存在 $Path" }
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if ($SkipMarker -and $raw.Contains($SkipMarker)) {
        Write-Host "skip  $Label (already up to date)"
        return
    }
    if (-not $raw.Contains($Old)) {
        throw "FAIL  $Label : old text not found (package version changed?)"
    }
    $raw = $raw.Replace($Old, $New)
    Set-Content -LiteralPath $Path -Value $raw -Encoding UTF8 -NoNewline
    Write-Host "patch $Label"
}

# 1) api-proxy prompt 门禁
Patch-File -Path $apiproxy -Label 'apiproxy prompt gate' -SkipMarker 'Image-admission gate relaxed' -Old @'
							const modelInfo = await ctx.llm.resolveModelInfo(current.provider, current.model);
							if (modelInfo.inputModalities !== void 0 && !modelInfo.inputModalities.includes("image")) return err(request, {
								code: "attachment-error",
								message: `Model "${current.model}" does not support image input.`,
								details: { reason: "MODEL_DOES_NOT_SUPPORT_IMAGES" }
							});
'@ -New @'
							const modelInfo = await ctx.llm.resolveModelInfo(current.provider, current.model);
							// [vision-skill patch] Image-admission gate relaxed: text-only models receive a
							// path-bearing text placeholder from the DeepSeek adapter (flattenText) and the
							// vision skill reads the file. Deliberately disabled; revert by removing "false &&".
							if (false && modelInfo.inputModalities !== void 0 && !modelInfo.inputModalities.includes("image")) return err(request, {
								code: "attachment-error",
								message: `Model "${current.model}" does not support image input.`,
								details: { reason: "MODEL_DOES_NOT_SUPPORT_IMAGES" }
							});
'@

# 2) api-proxy selectModel 门禁
Patch-File -Path $apiproxy -Label 'apiproxy selectModel gate' -SkipMarker 'Same relaxed gate' -Old @'
							const info = await ctx.llm.resolveModelInfo(resolved.provider, resolved.model);
							if (info.inputModalities !== void 0 && !info.inputModalities.includes("image")) return err(request, {
								code: "model-unavailable",
								message: `Model "${resolved.model}" does not accept image input, but this session already contains images; select an image-capable model.`,
								details: {
									provider,
									model
								}
							});
'@ -New @'
							const info = await ctx.llm.resolveModelInfo(resolved.provider, resolved.model);
							// [vision-skill patch] Same relaxed gate as the prompt path (see above).
							if (false && info.inputModalities !== void 0 && !info.inputModalities.includes("image")) return err(request, {
								code: "model-unavailable",
								message: `Model "${resolved.model}" does not accept image input, but this session already contains images; select an image-capable model.`,
								details: {
									provider,
									model
								}
							});
'@

# 3a) deepseek 适配器：node 内置模块导入（homedir 回退用）
Patch-File -Path $llmDeepseek -Label 'llm-deepseek node imports' -SkipMarker 'node:os' -Old @'
import { EventSourceParserStream } from "eventsource-parser/stream";
'@ -New @'
import { EventSourceParserStream } from "eventsource-parser/stream";
import { homedir } from "node:os";
import { join } from "node:path";
'@

# 3b) deepseek 适配器：图片块 -> 带路径占位符（v2，含 homedir 回退；v1 文件会被原位升级）
Patch-File -Path $llmDeepseek -Label 'llm-deepseek flatten images v2' -SkipMarker 'patch v2' -Old @'
/** [vision-skill patch] Render one block to text: text verbatim; image blocks become a
 * path-bearing placeholder so a text-only model can hand the file to the vision skill.
 * Path derivation matches the content-addressed store: DSH_HOME/attachments/v1/objects/<h[:2]>/<h>. */
function blockToText(block) {
	if (block.type === "text") return block.text;
	if (block.type === "image") {
		const ref = block.attachment;
		const id = typeof ref === "object" && ref !== null && typeof ref.attachmentId === "string" ? ref.attachmentId : "";
		const hex = id.startsWith("sha256:") ? id.slice(7) : "";
		const home = process.env.DSH_HOME ?? "";
		const path = hex !== "" && home !== "" ? `${home.replace(/[\\/]+$/, "")}/attachments/v1/objects/${hex.slice(0, 2)}/${hex}` : "(路径不可推导)";
		const name = typeof ref === "object" && ref !== null && typeof ref.name === "string" ? `，文件名 ${ref.name}` : "";
		return `[图片附件 ${id}${name}，本地路径 ${path}，模型不支持直接读图，请用 vision skill 读取]`;
	}
	return "";
}
/** Join the text blocks of a message (used for user/tool-result content). */
function flattenText(blocks) {
	return blocks.map(blockToText).join("");
}
/** [vision-skill patch] Image admission: flattening happens in flattenText; nothing to reject. */
function assertTextOnly() {}
'@ -New @'
/** [vision-skill patch v2] Render one block to text: text verbatim; image blocks become a
 * path-bearing placeholder so a text-only model can hand the file to the vision skill.
 * Path derivation matches the content-addressed store: <DSH_HOME|~/.dsh>/attachments/v1/objects/<h[:2]>/<h>. */
function blockToText(block) {
	if (block.type === "text") return block.text;
	if (block.type === "image") {
		const ref = block.attachment;
		const id = typeof ref === "object" && ref !== null && typeof ref.attachmentId === "string" ? ref.attachmentId : "";
		const hex = id.startsWith("sha256:") ? id.slice(7) : "";
		const envHome = process.env.DSH_HOME;
		const home = typeof envHome === "string" && envHome.length > 0 ? envHome.replace(/[\\/]+$/, "") : join(homedir(), ".dsh");
		const path = hex !== "" ? `${home}/attachments/v1/objects/${hex.slice(0, 2)}/${hex}` : "(路径不可推导)";
		const name = typeof ref === "object" && ref !== null && typeof ref.name === "string" ? `，文件名 ${ref.name}` : "";
		return `[图片附件 ${id}${name}，本地路径 ${path}，模型不支持直接读图，请用 vision skill 读取]`;
	}
	return "";
}
/** Join the text blocks of a message (used for user/tool-result content). */
function flattenText(blocks) {
	return blocks.map(blockToText).join("");
}
/** [vision-skill patch] Image admission: flattening happens in flattenText; nothing to reject. */
function assertTextOnly() {}
'@

Write-Host "done. Restart the dsh web host to take effect."
