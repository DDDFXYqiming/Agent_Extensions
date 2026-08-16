# @dsh-external/dsh-ocr1-memory

基于 **DeepSeek-OCR: Contexts Optical Compression**（arXiv:2510.18234）思想实现的 DSH 光学记忆系统。

记忆不再只存文本——它被**渲染成图像（SoM 编号分段）并保留下来**；按年龄把旧记忆**降分辨率（越久远越模糊）**；检索命中低清记忆后通过 **active recall 恢复高清**；最终返回**原始 verbatim 片段**（Locate-and-Transcribe），避免生成式幻觉。

## 能力

| 工具 | 说明 |
|---|---|
| `ocr1_mem_status` | 状态：存储目录 / OCR 后端 / 条目数 / 渲染依赖 / 层级 |
| `ocr1_mem_store` | 文本 → 自动分段 → 渲染 SoM 图像 → 存入记忆库 |
| `ocr1_mem_update` | 更新已有记忆，替换为新内容并重置为 vivid（冲突消解） |
| `ocr1_mem_retrieve` | 按查询检索，OCR 读回图像 + 分段召回；命中低清记忆自动 active recall |
| `ocr1_mem_list` | 列出记忆条目（id / 来源 / 段数 / 层级 / 命中数） |
| `ocr1_mem_metrics` | 查看压缩比指标：文本 token 数 / 视觉 token 数 / 实测 prompt_tokens |
| `ocr1_mem_calibrate` | 校准 OCR 文本基线 prompt_tokens，用于更准确的视觉 token 估算 |
| `ocr1_mem_forget` | 按 id 删除记忆 |
| `ocr1_mem_render_test` | 渲染管线自测 |
| `ocr1_mem_embed_test` | 视觉 embedding 自测：返回真实 1280 维 DeepSeek-OCR embedding 与直接视觉 token 数 |

## 设计（对应 OCR1 论文）

| OCR1 概念 | 本插件实现 |
|---|---|
| 长文本 → 光学 2D 映射 | 文本按段落自动分段，渲染为图像 |
| visual tokens 承载信息 | 分辨率模式对应 OCR1 官方设计：`vivid 1280(≈400) → normal 1024(≈256) → fuzzy 640(≈100)`；会记录接口级视觉 token 数 |
| 记忆随时间模糊 | 按 `createdAt` 年龄衰减，旧记忆降到低分辨率 |
| 人类记忆的 vivid-to-fuzzy | 越旧越低清，但保留语义 gist |
| 记忆刷新 | 命中低清记忆 → active recall 恢复高清，并在一段时间内豁免再衰减 |
| 避免幻觉 | Locate-and-Transcribe 风格：返回原始 verbatim 片段；当前定位由文本打分 + OCR 证据完成，不是模型直接输出 SoM 编号 |
| OCR 驱动召回 | 原始 token 未命中但 DeepSeek-OCR 从图像读到关键词 → 仍按 OCR 证据召回并取回原文 |
| 视觉 embedding | 存储真实 DeepSeek-OCR 1280 维视觉向量（`visualMemory.embedding`）；当前作为持久化视觉特征，不参与主检索打分 |
| 渲染缓存 | AgentOCR 式分段哈希缓存，相同分段集合+分辨率直接复用图像 |

## 配置

在 profile 的 cordis.patch.yml 中覆盖（裸条目）：

```yaml
- id: dsh-ocr1-memory
  config:
    storeDir: ''                 # 默认 <home>/.dsh/ocr1-memory
    ocrBaseUrl: ''               # DeepSeek-OCR vLLM/OpenAI 兼容端点；留空则跳过 OCR 读回
    ocrApiKey: ''
    ocrModel: 'deepseek-ai/DeepSeek-OCR'
    pythonPath: 'python'
    renderScript: '<插件目录>/scripts/render_memory.py'
    requireOcr: false            # true 时 OCR 不可用会直接报错
    useMockRenderer: false       # true 时跳过 Python 渲染（仅测试）
    autoStartOcrServer: false    # true 时插件加载后自动确保 llama-server 在线
    ocrServerPath: ''            # llama-server.exe 路径；留空用默认值
    ocrModelDir: ''              # DeepSeek-OCR GGUF 目录；留空用默认值
    ocrServerPort: 18080         # OCR 服务端口
    ocrEmbeddingBaseUrl: ''      # DeepSeek-OCR embeddings 端点（llama-server --embeddings --pooling mean）
    ocrEmbeddingApiKey: ''
    ocrEmbeddingModel: ''        # 留空则使用 ocrModel
    ocrEmbeddingTimeoutMs: 120000
    ocrEmbeddingEmptyPromptTokens: 1  # 空文本 embedding 的 prompt_tokens 基线
    ocrEmbeddingAutoStart: false       # true 时自动拉起 embeddings 专用 llama-server
    ocrEmbeddingPort: 18084            # embeddings 专用服务端口
    ocrEmbeddingUbatchSize: 2048       # 必须 >= 单图视觉 token 数（默认 512 会拒大图）
    ocrEmbeddingServerPath: ''         # embeddings 用的 llama-server.exe 路径
    ocrEmbeddingModelDir: ''           # embeddings 用的 GGUF 目录
    sharedStore: false                 # true 时每次操作前重读 memories.json，支持多 Agent 共享同一 store
```

## 安装

```bash
# headless（自测）
dsh plugin --profile headless add <本目录>

# web（长期使用）
dsh plugin --profile web add <本目录>
```

运行时注入（免重启，开发用）：

```text
dev_inject_plugin <本目录>
```

## 接上真正的 DeepSeek-OCR

本插件把 OCR 后端抽象成 OpenAI 兼容的 `/v1/chat/completions`（vLLM 已支持 DeepSeek-OCR）。

```bash
# 例：用 vLLM 起 DeepSeek-OCR 服务
python -m vllm.entrypoints.openai.api_server \
  --model deepseek-ai/DeepSeek-OCR \
  --max-model-len 16384
```

然后把 `ocrBaseUrl` 配成 `http://127.0.0.1:8000/v1` 即可让检索真正走光学读回路径。

本机 AMD 路线（llama.cpp）：

```bash
# 一键启动/确保 DeepSeek-OCR llama-server 在线
node scripts/ensure-ocr-server.mjs 18080
# 或手动
powershell -File scripts/start-ocr-server.ps1
```

默认后端地址：`http://127.0.0.1:18080/v1`，模型默认为 `deepseek-ocr-Q4_K_M.gguf`（`DeepSeek-OCR-Q8_0.gguf` 也可通过 `ocrModelDir`/脚本参数覆盖）。

### 真实视觉 embedding（DeepSeek-OCR embeddings 端点）

llama.cpp 的 `/v1/embeddings` 支持多模态输入（`prompt_string` + `multimodal_data`）。用以下命令启动 embeddings 专用服务（需 `-ub` 大于单图视觉 token 数，默认 512 会拒绝大图）：

```bash
# 方式一：使用 start-ocr-server.ps1 的 -Embeddings 开关
powershell -File scripts/start-ocr-server.ps1 -Embeddings -Port 18084

# 方式二：手动启动
llama-server.exe --host 127.0.0.1 --port 18084 --embeddings --pooling mean \
  -m <model_dir>\deepseek-ocr-Q4_K_M.gguf \
  --mmproj <model_dir>\mmproj-deepseek-ocr-q8_0.gguf \
  --alias deepseek-ocr -c 8192 -n 1024 -b 2048 -ub 2048
```

然后把 `ocrEmbeddingBaseUrl` 配成 `http://127.0.0.1:18084/v1`。插件会为每条记忆存储 **1280 维真实视觉 embedding**，并报告“直接视觉 token 数”（仅用 media marker 请求，`prompt_tokens - 空文本基线`）。

## 与 DeepSeek OCR1 论文的差距

当前实现是 **OCR1 思想的工程近似**，不是论文内部机制的完整复刻：

1. **DeepEncoder 内部压缩未复刻**
   - 论文：DeepEncoder 把文档图像真正压缩成少量 visual tokens，再交给 DeepSeek-3B 解码。
   - 当前：使用 llama.cpp 的 OCR/embeddings 接口做光学读回和视觉向量存储；视觉 token 数来自接口统计，不是 DeepEncoder 内部张量输出。

2. **Locate-and-Transcribe 是工程近似**
   - 论文/OCR-Memory：模型直接输出 SoM 编号（Locate），再取回原文（Transcribe）。
   - 当前：定位靠文本 token 重叠打分 + OCR 证据；返回原始 verbatim 片段，避免生成幻觉，但不是“模型输出编号”。
   - LoRA 微调让模型输出 SoM 编号这部分按目标要求**不做**。

3. **视觉 embedding 已存储，但不是主检索信号**
   - 当前 `visualMemory.embedding` 已存储 1280 维真实视觉向量；
   - 但检索主信号仍是文本打分 + OCR 证据，尚未用 embedding 相似度作为主检索。

4. **视觉 token 数是接口级直接测量**
   - 通过 embeddings 端点 marker-only 请求得到 `visualTokensDirect`；
   - 不是 DeepEncoder 内部逐层显式输出。

## 开发与测试

```bash
npm run build        # node --check
npm test             # 46 项测试（含复杂隔离测试 + 真实 OCR/embedding + robustness，若后端在线）
npm run test:smoke   # 本地端到端冒烟（真实 Python 渲染 + mock OCR）
node scripts/compare-memory.mjs  # 对比 dsh-ocr1-memory vs dsh-memory（隔离临时环境）
dsh --profile headless --dump-config   # 检查插件层已装配
```

## 测试与对比结果

- `npm test`：**46/46 通过**。
- Robustness：多 Agent 共享 store、图像缺失/缓存损坏恢复、超长输入边界均通过。
- 对比基准（`scripts/compare-memory.mjs`，隔离 headless + 官方原装 DSH）：
  - dsh-ocr1-memory：R1–R6 全部 PASS。
  - dsh-memory：本次 R1–R6 全部 PASS；但 R5 此前手动验证曾 FAIL（`memory_archive` 后仍可被 `memory_read` 读到），行为不稳定。
  - 结论：dsh-ocr1-memory 未出现落后于 dsh-memory 的情况。

## Roadmap

- [ ] LoRA 微调 DeepSeek-OCR decoder 做 SoM 检索（OCR-Memory 方案），把检索真正变成“模型输出编号”而非文本打分
- [x] AgentOCR 式 segment optical caching（哈希分段缓存，降低渲染成本；已实现 `.render-cache` 复用）
- [x] 压缩比指标与 OCR 文本基线校准（`ocr1_mem_metrics` / `ocr1_mem_calibrate`）
- [x] 显式记忆更新（`ocr1_mem_update`，冲突消解）
- [x] 自动确保 OCR 服务在线（`autoStartOcrServer`）
- [x] 对比 dsh-memory 的隔离基准（R1–R6 已用修正后脚本完整重跑；dsh-ocr1-memory 全部 PASS）
- [x] 真实 DeepSeek-OCR 视觉 embedding 存储（1280 维，`visualMemory.embedding`）
- [x] 直接视觉 token 测量（embeddings 端点 marker-only 请求，`visualMemory.visualTokensDirect`）
- [x] 多 Agent 共享 store（`sharedStore` + reload + 原子保存）
- [x] 图像缺失 / 渲染缓存损坏自动恢复
- [x] 超长输入边界测试
- [ ] 记忆命中热度驱动的动态衰减策略
- [ ] 自动注入 `/context` 让 Agent 每轮看到记忆摘要

## 相关参考

- DeepSeek-OCR（OCR1）：<https://arxiv.org/abs/2510.18234> · <https://github.com/deepseek-ai/DeepSeek-OCR>
- OCR-Memory（方法蓝本，未开源）：<https://arxiv.org/abs/2604.26622>
- AgentOCR（工程参考，已开源）：<https://github.com/langfengQ/AgentOCR>
