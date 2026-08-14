# reapply-pi-ai-vision-patch.ps1
# [zen-ua patch] 幂等重打 dsh-llm-pi-ai 的 User-Agent 放行补丁。
# 背景：OpenCode Zen 免费层只认 `opencode/<ver>` User-Agent，其他 UA（含 DSH 的
# attribution `deepseek-harness/...`）一律 429 FreeUsageLimitError。DSH 的 pi-ai 适配器
# requestHeaders 会过滤用户配置的 user-agent 并强制覆盖为 attribution——本补丁让用户
# 显式配置的 user-agent 优先。
# 用途：dsh 包升级/重装（覆盖 node_modules）后重跑恢复。运行后需重启 dsh web 宿主。
# 注意：vision 补丁（apiproxy 图片门禁 + llm-deepseek 占位符）由
#   C:\Users\39795\.dsh\vision-patch\reapply-vision-patch.ps1 管理（旧 .bun 路径版本），
#   本脚本只负责 pi-ai 的 zen-ua 补丁（.dsh/profiles shared store 路径）。

$ErrorActionPreference = 'Stop'

$piAi = 'C:\Users\39795\.dsh\profiles\node_modules\@deepseek-ai\dsh-llm-pi-ai\lib\index.js'

if (-not (Test-Path -LiteralPath $piAi)) {
    throw "FAIL : file not found: $piAi"
}

$raw = Get-Content -LiteralPath $piAi -Raw -Encoding UTF8

if ($raw.Contains('[zen-ua patch 2026-08-14]')) {
    Write-Host "skip  pi-ai zen-ua patch (already up to date)"
} else {
    $old = @'
/** Merge deployment headers while removing case-insensitive attribution collisions. */
function requestHeaders(headers) {
	const attribution = attributionHeaders();
	const reserved = new Set(Object.keys(attribution).map((name) => name.toLowerCase()));
	return {
		...Object.fromEntries(Object.entries(headers ?? {}).filter(([name]) => !reserved.has(name.toLowerCase()))),
		...attribution
	};
}
'@
    $new = @'
/** Merge deployment headers while removing case-insensitive attribution collisions.
 * [zen-ua patch 2026-08-14] OpenCode Zen 免费层只认 `opencode/<ver>` User-Agent，
 * 其他 UA（含 DSH attribution）返回 429 FreeUsageLimitError。补丁：用户显式配置了
 * `user-agent` 时优先保留用户的（放行），未配置才回退 attribution。 */
function requestHeaders(headers) {
	const attribution = attributionHeaders();
	const reserved = new Set(Object.keys(attribution).map((name) => name.toLowerCase()));
	const merged = {
		...Object.fromEntries(Object.entries(headers ?? {}).filter(([name]) => !reserved.has(name.toLowerCase()))),
		...attribution
	};
	// [zen-ua patch] 用户显式配置的 user-agent 优先（大小写不敏感匹配）
	for (const [name, value] of Object.entries(headers ?? {})) {
		if (name.toLowerCase() === "user-agent" && typeof value === "string" && value.trim() !== "") {
			merged["user-agent"] = value;
			break;
		}
	}
	return merged;
}
'@
    if (-not $raw.Contains($old)) {
        throw "FAIL : old requestHeaders not found (package version changed?)"
    }
    $raw = $raw.Replace($old, $new)
    Set-Content -LiteralPath $piAi -Value $raw -Encoding UTF8 -NoNewline
    Write-Host "patch pi-ai zen-ua patch"
}

# 校验：确认补丁后用户 UA 放行逻辑存在
$check = Get-Content -LiteralPath $piAi -Raw -Encoding UTF8
if ($check.Contains('merged["user-agent"] = value')) {
    Write-Host "verify OK : user-agent override in place"
} else {
    throw "verify FAIL : override not found after patch"
}

Write-Host "`nDone. 重启 dsh web 宿主后生效（重启命令需用户确认执行）。"
