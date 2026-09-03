# CHANGELOG

SKILL.md 只保留给智能体的执行指令；版本历史与实测数据放这里。

## 1.2.2

转写算力改为厂商无关的自动选路，不再默认写死 CPU。

- `enable_cuda_runtime()`：Windows 下从本机已有目录（`VIDEO_NOTES_CUDA_BIN` → Ollama `cuda_v12` → CUDA Toolkit v12* → nvidia pip wheel）借 `cublas64_12.dll` 塞进 PATH。必须在 import faster-whisper 之前调用——`os.add_dll_directory` 对 ctranslate2 无效，它只认 PATH。
- `whisper_device_candidates()`：探测到可用 cuda 才试 cuda，否则 cpu；显式 `WHISPER_DEVICE` 最优先（含 `auto`）。
- 转写循环改为按候选逐个尝试，cuda 中途失败自动降级重试，不再中断整条链路。
- `detect_gpus()`：三平台列出显卡清单（含核显），仅用于日志与判断降级原因。
- 新增 `VIDEO_NOTES_CUDA_BIN`；`compatibility` 收进 frontmatter，`version`/`author`/`platforms` 归入 `metadata`。

实测（RTX 2070 Max-Q，small 模型，60s 音频）：cuda/float16 = 4.3s（14.0x 实时），cpu/int8 = 22.0s（2.7x 实时）。54 分钟视频约 22 分钟 → 约 4 分钟。

## 1.2.1

修复 download_audio 缺 `--write-info-json` 导致标题/时长永远退化为 BV 号；字幕临时目录用后即清；get_video_info 失败改为显式 `[warn]`（时长缺失→抽帧退化固定间隔）；SKILL.md 移除自动灌水导读瘦身。

## 1.2.0

帧抽取默认化（20%/50%/80% 代表点）、native multimodal 工作流、B站 412 API fallback、代理三级配置。
