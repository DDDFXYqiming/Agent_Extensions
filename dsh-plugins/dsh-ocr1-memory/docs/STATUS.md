# dsh-ocr1-memory 状态总览

> 最后更新：第 17 轮目标推进

## 当前状态

| 项目 | 状态 |
|---|---|
| 插件目录 | `<repo_root>\dsh-plugins\dsh-ocr1-memory` |
| 测试数量 | `npm test` 40/40 通过 |
| 真实 OCR 后端 | llama-server `http://127.0.0.1:18080/v1` |
| 真实 Embedding 后端 | llama-server `http://127.0.0.1:18084/v1`（`--embeddings --pooling mean -ub 2048`） |
| 模型 | DeepSeek-OCR Q8_0 + mmproj Q8_0 |
| 自动拉起 | `lib/ocr-server.js` + `autoStartOcrServer` / `ocrEmbeddingAutoStart` 配置 |
| 对比基准 | `docs/BENCHMARK.md`、`scripts/compare-memory.mjs`（R1–R6 已实测，R5 dsh-memory FAIL） |

## 已实现功能

- `ocr1_mem_status`
- `ocr1_mem_store`
- `ocr1_mem_update`
- `ocr1_mem_retrieve`
- `ocr1_mem_list`
- `ocr1_mem_metrics`
- `ocr1_mem_calibrate`
- `ocr1_mem_forget`
- `ocr1_mem_render_test`
- `ocr1_mem_embed_test`
- 真实 DeepSeek-OCR 1280 维视觉 embedding 存储
- 直接视觉 token 数测量（marker-only embeddings 请求）
- SoM 分段渲染
- 年龄衰减（vivid/normal/fuzzy 对应 1280/1024/640）
- active recall
- Locate-and-Transcribe（返回原始 verbatim）
- 渲染缓存
- 并发安全
- OCR 文本基线校准

## 测试覆盖

- 核心单元测试：8
- 复杂隔离测试 T1–T24：24
- OCR HTTP / 渲染缓存：2
- Embedding 测试 E1–E4：4
- OCR server 生命周期：2
- 合计：40

## 对比结果（dsh-ocr1-memory vs dsh-memory）

| 任务 | 结果 |
|---|---|
| R1 准确检索 | 两者 PASS |
| R2 测试时学习 | 两者 PASS |
| R3 长程理解 | 两者 PASS |
| R4 冲突消解 | 两者 PASS |
| R5 选择性遗忘 | dsh-ocr1-memory PASS；dsh-memory FAIL（归档后仍可读到） |
| R6 跨会话持久化 | 两者 PASS |

## 已知差距（均不影响核心效果，且微调已明确不做）

1. 视觉 token 数现为“直接测量”：通过 embeddings 端点只发 media marker（无可见文本）得到 `prompt_tokens`，再减空文本基线；比之前近似更接近 DeepEncoder 纯视觉 token 数，但仍依赖 llama.cpp 的 token 统计接口，不是论文 DeepEncoder 内部的逐层输出。
2. LoRA 微调 DeepSeek-OCR 做 SoM 编号检索：按目标要求**不需要做**。
3. optical memory 已存储**真实 DeepSeek-OCR 1280 维视觉 embedding**（`visualMemory.embedding`，来源 `deepseek-ocr-embeddings`）；无 embeddings 后端时保留 64 维图像派生 embedding 作为降级。
4. DSH 级 R5/R6 完整对比已在隔离 headless 环境完成；core 层 T18/T19 亦通过。

## 安全说明

- 本环境禁止 kill 进程操作，避免影响 DSH 自身服务。
- 所有测试均在隔离临时目录执行，不污染默认 store。
