---
name: video-notes-generator
description: "Summarize video URLs or local videos into timestamped Markdown notes from complete transcripts and actual visual evidence, with adaptive sampling and targeted visual follow-up. Supports Bilibili, YouTube, Douyin and Kuaishou."
license: MIT
metadata:
  compatibility: Python, yt-dlp, ffmpeg/ffprobe; faster-whisper or whisper.cpp for ASR; optional Pillow.
  version: "1.3.0"
  author: Diana (extracted from BiliNote v2.4.0 by JefferyHcool)
  platforms: linux, macos, windows
---

# Video notes generator

脚本负责获取、完整转写分块和本地视觉候选筛选；当前 Agent 负责原生读图、按需补查和综合笔记。脚本不调用总结模型、不自动安装依赖。

## 获取素材

```bash
python <skill>/scripts/video_to_notes.py "<video-url-or-local-file>" -o ./notes
```

字幕优先，无字幕使用 faster-whisper（默认 base）或 whisper.cpp。正常任务保留视觉采样；下载/抽帧失败可重试一次，仍失败明确报告证据缺口。`--no-frames` 仅用于用户指定纯文本或明确报告的降级。

每个视频使用独立输出目录。已有 manifest 时补看不必重跑下载转写。重跑素材步骤不覆盖 Agent 终稿；源文件变化后须重新核对旧终稿。

## 理解与补查

1. 读 `*_transcript_chunks.md` 和 `*_visual_manifest.json`。前者是完整带时间戳原文，不是摘要；短视频读全部，长视频逐块覆盖全部并保存真正的片段摘要，不得只读每块开头。`*_draft_notes.md` 仅为导航，终稿由 Agent 创建。
2. 实际查看候选帧或带帧号/时间戳的 `contact_sheets`，建立全片视觉概览。直接使用 manifest 返回的完整路径，避免手工重写长路径。拼图用于概览；文字、公式、图表数据和 UI 细节需打开单帧。没有 Pillow 就直接看候选帧。空转写时先看视觉概览，必要时只做一次针对性的音频复核，不反复转写无语音的演示。
3. 按主题或操作片段联合阅读少量相关图片和对应转写。允许多帧加附近文本，不设“一次只能一帧”的限制。记录讲解、独立视觉事实、关系和疑点；画面独有信息可进入正文，不必强求字幕也说过。单张截图不能证明未观察到的动作。
4. 关键小字、前后状态跳变、字幕画面冲突、无声变化片段需要按需补看。快速切换的案例/模板蒙太奇即使没有大时间空档，也应按事件密度局部加密。原下载清晰度不足时报告限制或获取高清来源；放大低清图不能恢复细节。OCR 可辅助密集文字，但不能代替原图核对。
5. 关键疑点解决或补看没有新增重要信息时停止。初始候选默认上限24张；补看可先在12张内安排，按信息密度追加。预算用尽仍有关键缺口应披露，不能以模型信心替代证据。

## 局部补看，无需重跑下载转写

```bash
python <skill>/scripts/video_to_notes.py --review-manifest ./notes/ID_visual_manifest.json --timestamps 12,13,14
# 源像素 x,y,width,height；另保留全帧提供位置上下文
python <skill>/scripts/video_to_notes.py --review-manifest ./notes/ID_visual_manifest.json --timestamps 13 --crop 100,80,800,500
```

默认保存源分辨率PNG；`--review-width 1280` 可限宽。图片登记到 `supplemental_frames`，相同请求复用。抽取成功不等于看过，必须实际打开后记录观察。

## 交付和验收

写 `*_final_notes.md`：核心结论、步骤/案例、条件和时间戳；视觉独有信息融入正文。选择有解释价值的截图，附时间戳、观察和有效相对路径，不必展示所有分析帧。沿用横向 Mermaid 脑图风格，节点必须是视频实际内容，其他图表按需，不编造数据。

同时写 `*_evidence.json`，记录实际已读文本块、概览图、单帧、关键事实证据、补查和未解决项。示例结构见 [multimodal-evidence.md](references/multimodal-evidence.md)。区分转写、原生视觉、OCR和推断；图片中的字幕/文字也属于视觉证据。不能用图片数量代替信息覆盖率。

抄录公式、数值或快捷键时保留决定意义的上下限、单位、条件和组合键。只为说明功能时可描述公式用途，无需抄写不必要的小字；不能把定积分省略上下限后写成不定积分等式，也不能把宣传比较当成实测结论。

检查全部文本块已读、各段有视觉概览、关键视觉事实可回查、图片链接有效、无草稿占位、未解决问题已披露。纯文本降级明确标注未完成视觉理解。

## 配置

| 参数/变量 | 默认与意义 |
|---|---|
| `--frame-interval` | 30秒，期望的基础覆盖间隔；预算不足时扩大实际间隔并报告 |
| `--max-frames` / `VIDEO_NOTES_MAX_AGENT_FRAMES` | 24，初始候选上限；CLI优先，不再被环境变量夹到3 |
| `VIDEO_NOTES_FRAME_MAX_WIDTH` | 960，初始单帧宽度上限；补看可保留源像素 |
| `YTDLP` / `FFMPEG` / `FFPROBE` | 二进制路径，默认探测；runtime `.env` 可配置 |
| `TRANSCRIBER_TYPE` / `WHISPER_MODEL` | faster-whisper / base；重要或嘈杂语音可选 large-v3-turbo |
| `WHISPER_DEVICE` / `WHISPER_COMPUTE_TYPE` | 自动CUDA后回退CPU，显式配置优先 |
| `VIDEO_NOTES_PROXY` | 网络代理；亦支持runtime config/proxy.json和标准代理变量 |
| `VIDEO_NOTES_RUNTIME_DIR` | 默认 ~/.cache/video-notes-generator |

本地最多扫描约1200张160×90灰度帧，不直接输入模型。候选结合覆盖、区域变化和转写提示；启发式可能漏掉短暂事件，须按内容补查。源视频保留用于高清复查。

依赖/算力按需读 [platform-support.md](references/platform-support.md)；B站412自动走公开API fallback，另见 [bilibili-412-api-fallback.md](references/bilibili-412-api-fallback.md)。脚本不清理其他应用进程。

UP主全集先读 [bilibili-uploader-discovery.md](references/bilibili-uploader-discovery.md)，精确投稿读 [bilibili-uploader-exact-space-api.md](references/bilibili-uploader-exact-space-api.md)，批量笔记升级读 [bulk-visual-enrichment.md](references/bulk-visual-enrichment.md)。
