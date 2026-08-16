# Changelog

## 0.1.0 (current)

### Added
- 真实 DeepSeek-OCR 多模态 embedding 支持
  - `measureImageEmbedding` / `createEmbeddingHttpClient` / `measureEmptyPromptTokens`
  - 通过 llama.cpp `/v1/embeddings` 的 `prompt_string` + `multimodal_data` 请求真实 1280 维视觉 embedding
  - `visualMemory` 新增 `embeddingDim` / `embeddingSource` / `embeddingPromptTokens` / `visualTokensDirect` / `embeddingError`
  - 新增 `ocr1_mem_embed_test` 工具
  - `lib/ocr-server.js` 支持启动 `--embeddings --pooling mean -ub 2048` 专用服务
- DSH 插件骨架：`@dsh-external/dsh-ocr1-memory`
- 核心记忆引擎 `lib/core.js`
  - 文本分段
  - SoM 编号
  - 年龄衰减（vivid/normal/fuzzy：1280/1024/640）
  - active recall
  - Locate-and-Transcribe
  - 渲染缓存
  - 并发渲染锁
  - 更新记忆 `update`
  - 相同 source 的 `store` 自动更新
  - optical memory 元数据：`visualMemory`（图像路径 + prompt_tokens + 视觉 token 数 + 64 维视觉 embedding）
  - 压缩比指标 `memoryMetrics`
  - OCR 文本基线校准 `measureTextOnlyPromptTokens`
  - 视觉 token 基线可配置 `ocrTextOnlyPromptTokens`
- Python 渲染脚本 `scripts/render_memory.py`（CJK 字体支持）
- DSH 工具
  - `ocr1_mem_status`
  - `ocr1_mem_store`
  - `ocr1_mem_update`
  - `ocr1_mem_retrieve`
  - `ocr1_mem_list`
  - `ocr1_mem_metrics`
  - `ocr1_mem_calibrate`
  - `ocr1_mem_forget`
  - `ocr1_mem_render_test`
- OCR 服务生命周期
  - `scripts/start-ocr-server.ps1`
  - `scripts/ensure-ocr-server.mjs`
  - `lib/ocr-server.js`
  - `autoStartOcrServer` 配置
- 对比基准
  - `scripts/compare-memory.mjs`
  - `docs/BENCHMARK.md`

### Fixed
- 检索打分污染：片段级得分不再被整条记忆聚合分抬高
- 并发 active recall 渲染竞争（EBUSY）
- OCR 服务自动拉起：直接 spawn `llama-server.exe`，避免 PowerShell spawn 不稳定
- CJK 字体渲染：使用微软雅黑/黑体
- DSH 工具输出 schema 严格性：`ocr1_mem_store` 补 `updated` 字段，`ocr1_mem_list` 只返回 schema 声明字段，避免 headless Agent 报 invalid output

### DSH 级对比（R5/R6）
- 在隔离 headless 环境完成完整对比（dsh-ocr1-memory 使用完整 OCR + embedding 配置）：
  - R5 选择性遗忘：dsh-ocr1-memory PASS；dsh-memory FAIL（归档后 `memory_read` 仍可读到）
  - R6 跨会话持久化：两者 PASS

### Tests
- `npm test` 40/40 通过
- 核心单元测试 8
- 复杂隔离测试 T1–T24 24
- OCR HTTP / 渲染缓存 2
- Embedding 测试 E1–E4 4
- OCR server 生命周期 2

### Docs
- `README.md`
- `docs/TEST_REPORT.md`
- `docs/EXPLORATION.md`
- `docs/BENCHMARK.md`
- `docs/STATUS.md`
- `CHANGELOG.md`
