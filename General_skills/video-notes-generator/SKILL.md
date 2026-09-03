---
name: video-notes-generator
description: "Use when user wants to summarize, analyze, or generate notes from a video URL. Converts video content into structured Markdown notes with timestamps, extracted visual frames, native multimodal image observations, and AI summaries. Supports Bilibili, YouTube, Douyin, Kuaishou, and local files."
license: MIT
compatibility: 需要 yt-dlp 与 ffmpeg 二进制（脚本自动探测，从不自动安装）。转写默认 faster-whisper，可选 whisper.cpp。
metadata:
  version: "1.2.2"
  author: Diana (extracted from BiliNote v2.4.0 by JefferyHcool)
  platforms: linux, macos, windows
  hermes:
    tags: [video, notes, bilibili, youtube, transcription, summarization]
    related_skills: [youtube-content, gif-search]
---

# video-notes-generator

把视频 URL 或本地视频加工成结构化笔记素材：下载 → 字幕/转写 → 抽帧 → 五类产物；最终笔记由 Agent 基于产物综合生成。脚本零 pip 设计，只依赖 `yt-dlp` 与 `ffmpeg` 二进制。

## 触发场景

- 用户说"视频笔记 / 视频总结 / video notes / summarize video"
- 分享 Bilibili / YouTube / 抖音 / 快手 URL 并要求笔记或总结
- 要求转写或总结本地视频文件

## Quick Start

```bash
# B站视频（无字幕时自动转写）
python3 <skill>/scripts/video_to_notes.py "https://www.bilibili.com/video/BV1xxxxx"

# YouTube + 自定义输出目录
python3 <skill>/scripts/video_to_notes.py "https://www.youtube.com/watch?v=xxxxx" -o ./my_notes

# 本地文件（默认抽帧做多模态分析）
python3 <skill>/scripts/video_to_notes.py "/path/to/video.mp4" --frame-interval 30 --max-frames 3

# 紧急纯文本模式（仅当下载/抽帧失败或用户明确不要图）
python3 <skill>/scripts/video_to_notes.py "<url>" --no-frames
```

## 流水线

1. 依赖预检 → 2. 平台检测（bilibili/youtube/douyin/kuaishou/local）→ 3. 元数据（yt-dlp --dump-json，B站失败走公开 API fallback）→ 4. 字幕优先（B站/YouTube）→ 5. 无字幕则音频下载 + faster-whisper / whisper.cpp 转写 → 6. 下载 ≤720p H.264 视频抽代表帧（20%/50%/80%）→ 7. 输出产物。

## 产物五件套

| 文件 | 用途 |
|---|---|
| `*_final_notes.md` | 用户可见笔记（**先读这个**） |
| `*_chunk_summaries.md` | 分块摘要（第二顺位读） |
| `*_transcript.json` | 完整转写档案（仅在用户要求原始细节时读） |
| `*_visual_manifest.json` | 帧索引：timestamp / image_path / nearby_transcript |
| `*_frames/` | 关键帧图片 |

## 配置

环境变量（可放 `<runtime>/.env`，runtime 默认 `~/.cache/video-notes-generator`）：

| 变量 | 默认 | 说明 |
|---|---|---|
| `YTDLP` / `FFMPEG` | 自动探测 | 二进制路径 |
| `TRANSCRIBER_TYPE` | `faster-whisper` | 转写引擎；`whisper.cpp` 可选（有 git/编译器时自动编译） |
| `WHISPER_MODEL` | `base` | 转写模型。嘈杂音频建议 `large-v3-turbo`（首次需下载模型）；内置别名 tiny/base/small/medium/large-v1/v2/v3/v3-turbo |
| `WHISPER_DEVICE` / `WHISPER_COMPUTE_TYPE` | 留空 = 自动探测 | 显式设值最优先；取值与降级行为见「转写算力」小节 |
| `VIDEO_NOTES_CUDA_BIN` | 自动搜索 | 含 `cublas64_12.dll` 的目录，供借用 CUDA 运行库时指定 |
| `VIDEO_NOTES_PROXY` | 标准 proxy env | yt-dlp/网络代理；也可用 `<runtime>/config/proxy.json` `{"enabled":true,"url":"..."}` |
| `VIDEO_NOTES_MAX_AGENT_FRAMES` | `3` | 默认最大抽帧数 |
| `VIDEO_NOTES_FRAME_MAX_WIDTH` | `640` | 帧宽上限 |

CLI 参数：位置参数 `url` 必填；`-o/--output`（默认 `./notes`）；`--no-subtitle`、`--transcribe`、`--model`、`--frame-interval`、`--max-frames`、`--no-frames`、`--print-full-json`（勿在 Agent 场景使用）。已废弃：`--url/--file/--style/--format/--quality`。

## 转写算力

脚本自己探测，**不要先查硬件再决定**：可用则 `cuda`/`float16`，否则 `cpu`/`int8`；cuda 中途失败自动降级重试，转写不会中断。

- 日志 `cublas64_12.dll is not found` = 本机没有可借的 CUDA 运行库，已自动降级，属预期，不要干预或重跑
- 要把算力腾给别的任务：设 `WHISPER_DEVICE=cpu`
- AMD / Intel / Apple 显卡 faster-whisper 用不上 → 换 whisper.cpp 后端，见 [references/platform-support.md](references/platform-support.md) 的 Transcription compute 小节
- 装依赖由你执行，脚本从不 pip

## 终稿 Markdown 强制规范

1. **必须以横向 Mermaid 思维导图开头**（`flowchart LR`），再接正文
2. 按需追加 diagram：流程 `flowchart`、时间线 `timeline`、交互 `sequenceDiagram`、对比 `quadrantChart`、数值趋势 `xychart-beta`——不得编造数据画图
3. 有视觉帧时必须有截图小节：每张嵌入图需 时间戳 + 相对图片路径 + 视觉观察 + 附近转写 + 来源标注（`native multimodal` / `OCR fallback` / `pending visual review`）

## 多模态视觉工作流

- 抽帧是默认要求；`frame_count=0` 时不得静默继续，先重试，实在不行才 `--no-frames` 并明确报告
- 模型支持读图时：逐帧打开真实图片做原生视觉观察（一次一帧，禁止多帧+转写打包发送），把观察写回 final_notes 替换 pending
- 不支持读图才允许 OCR fallback，且必须标注 OCR 来源
- 不得虚构画面细节；视觉观察须与 nearby_transcript 互相印证

## Context-Safe 阅读顺序

final_notes → chunk_summaries → （仅按需）单段 transcript 或单帧。API 上下文报错时从 chunk_summaries 重试，不要重发全量转写+OCR+帧。

## 平台支持

| 平台 | 字幕 | 下载 | 备注 |
|---|---|---|---|
| Bilibili | ✅ 优先 | yt-dlp + 公开 API fallback（HTTP 412 时自动走 view/playurl DASH 直下 + ffmpeg 合并） | 受限视频建议配 cookies |
| YouTube | ✅ 优先 | yt-dlp | 需要代理时配 `VIDEO_NOTES_PROXY` |
| 抖音 | ❌ | yt-dlp（ABogus 内置） | — |
| 快手 | ✅ | yt-dlp + helper | — |
| 本地文件 | — | 直接处理 | ffmpeg 支持的任意格式 |

UP 主全集任务先读 `references/bilibili-uploader-discovery.md`；精确投稿列表另读 `references/bilibili-uploader-exact-space-api.md`；批量视觉增强流程见 `references/bulk-visual-enrichment.md`。

## 常见坑

1. 缺 ffmpeg/yt-dlp 是最常见失败原因（安装：`apt install ffmpeg`；`pip install -U yt-dlp` 或官方 release 单文件）
2. B站 HTTP 412 → 脚本自动走 API fallback，无需干预；Windows SSL EOF 属 fallback 场景而非主路径
3. 无字幕视频转写质量取决于 WHISPER_MODEL：嘈杂户外音频 base 会出繁体/错字，重要内容用 large-v3-turbo
4. 长视频（>2h）自动分块合并，耗时显著
5. 产物为中文导向，其他语言由 Agent 手动转换
6. 本脚本不启动浏览器；Agent 浏览器工具残留的 `agent-browser-chrome-*` 僵尸进程由脚本启动时自动清理，也可手动 `pkill -f agent-browser-chrome`
7. 转写算力自动选路，见「转写算力」小节；缺 CUDA 运行库会静默降级到 CPU，属预期，不要因此重跑。

## 验收清单

- [ ] `*_final_notes.md` 存在，以 `flowchart LR` mermaid 开头
- [ ] transcript.json / chunk_summaries.md 存在
- [ ] 正常跑必有帧：frames/ 目录有图、manifest 指向存在的文件、final_notes 有嵌入与观察
- [ ] 无 pending visual review 遗留（除非用户接受纯文本并明确记录）
- [ ] 终端无错误输出
