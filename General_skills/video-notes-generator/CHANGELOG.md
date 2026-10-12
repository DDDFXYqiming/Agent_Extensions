# CHANGELOG

SKILL.md 只保留给智能体的执行指令；版本历史与实测数据放这里。

## 1.4.1

SKILL.md 新增「来源与更新」小节，frontmatter 增加 `source_repo` / `source_subdir` / `install_path`：写明源仓库 DDDFXYqiming/Agent_Extensions 与仓库内路径 `General_skills/video-notes-generator`、本地 clone 位置、运行副本路径和 robocopy 同步流程，避免后续更新时找不到来源或误改运行副本。

## 1.4.0

转写模型从“写死模型名”改为“逻辑档位 + 集中映射 + 失败降级”，解决 skill 文本随模型换代过时、以及单模型下载失败整条链路卡死两个问题。

- `WHISPER_MODEL` 接受档位名（`default`/`high`）或具体模型名；档位映射集中在 runtime `config/whisper_models.json` 的 `tiers` 键（有序候选链），新增 `templates/whisper_models.json` 示例。新模型出现只改该 JSON，SKILL.md 保持零模型名。
- 联网刷新触发写进 SKILL.md：选用 high 档且 `tiers_updated` 超过 6 个月或缺失时，先联网查 faster-whisper 当前推荐模型、更新映射再运行；检索结果只写映射文件。
- faster-whisper 与 whisper.cpp 两条后端都按候选链逐个尝试，解析/下载/设备失败自动降级并在 stderr 报告；实际使用模型与首个失败原因写入输出 JSON 的 `source_note`，SKILL.md 要求终稿披露。
- 自定义映射向后兼容：原有扁平 `{"别名": "repo"}` 与新增 `models` 键均可；`tiers` 为保留键。

实测（RTX 2070，15s 中文 TTS 视频）：自定义 tiers 首候选为不存在模型 → 解析失败即降级 tiny 转写 3 段且 `source_note` 携带降级说明；无配置 `default` 档回归 base 正常；`HF_HUB_OFFLINE=1` 下 high 档命中本机已缓存的档顶模型时直接使用、不误报降级（档位名不等于降级，以候选链首个元素为基准）。

## 1.3.0

- 完整带时间戳 transcript_chunks 取代截断冒充的分块摘要；旧 chunk_summaries 文件保留为导航指针。脚本输出 draft_notes，Agent 完成图文理解后创建 final_notes，素材重试不覆盖终稿。
- 新增 visual_sampling.py：有预算的低分辨率区域变化扫描、全片覆盖、转写提示及重复候选过滤；CLI 帧预算优先，frame-interval 参与覆盖选择，manifest 报告实际最大采样间隔。
- 初始帧默认宽960、上限24；保留源视频；新增 --review-manifest/--timestamps/--crop，按需源分辨率PNG补看并缓存。Pillow可选生成有时间戳的概览拼图。
- 统一原生图文联合阅读、视觉独有事实进入正文、证据来源与局部补查规范；取消一次只能一帧限制。
- 保留下载/ASR后端，提升可用视频清晰度选择；去除无关进程清理和安装脚本中未使用的SDK依赖。空转写诊断入档，视觉失败仍保留文本。
- 添加8项行为检查，覆盖完整文本、预算/间隔、无声变化、重复候选、实际ffmpeg抽帧/缓存/裁剪、补查记录保留、草稿和失败恢复。

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
