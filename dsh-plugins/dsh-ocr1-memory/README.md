# @dsh-external/dsh-ocr1-memory

基于 **DeepSeek-OCR: Contexts Optical Compression**（arXiv:2510.18234）思想实现的 DSH 光学记忆系统。

记忆不再只存文本——它被**渲染成图像（SoM 编号分段）并保留下来**；按年龄把旧记忆**降分辨率（越久远越模糊）**；检索命中低清记忆后通过 **active recall 恢复高清**；最终返回**原始 verbatim 片段**（Locate-and-Transcribe），避免生成式幻觉。

## 能力

| 工具 | 说明 |
|---|---|
| `ocr1_mem_status` | 状态：存储目录 / OCR 后端 / 条目数 / 渲染依赖 / 层级 |
| `ocr1_mem_store` | 文本 → 自动分段 → 渲染 SoM 图像 → 存入记忆库 |
| `ocr1_mem_retrieve` | 按查询检索，OCR 读回图像 + 分段召回；命中低清记忆自动 active recall |
| `ocr1_mem_list` | 列出记忆条目（id / 来源 / 段数 / 层级 / 命中数） |
| `ocr1_mem_forget` | 按 id 删除记忆 |
| `ocr1_mem_render_test` | 渲染管线自测 |

## 设计（对应 OCR1 论文）

| OCR1 概念 | 本插件实现 |
|---|---|
| 长文本 → 光学 2D 映射 | 文本按段落自动分段，渲染为图像 |
| visual tokens 承载信息 | 图像分辨率对应 token 层级：`vivid 1024(≈256) → normal 768(≈144) → fuzzy 512(≈64)` |
| 记忆随时间模糊 | 按 `createdAt` 年龄衰减，旧记忆降到低分辨率 |
| 人类记忆的 vivid-to-fuzzy | 越旧越低清，但保留语义 gist |
| 记忆刷新 | 命中低清记忆 → active recall 恢复高清，并在一段时间内豁免再衰减 |
| 避免幻觉 | Locate-and-Transcribe：只选择编号，原文从原始日志确定性取回 |
| OCR 驱动召回 | 原始 token 未命中但 DeepSeek-OCR 从图像读到关键词 → 仍按 OCR 证据召回并取回原文 |
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

## 开发与测试

```bash
npm run build        # node --check
npm test             # 9 项单元测试（含真实 HTTP OCR 集成路径 + 渲染缓存，无 GPU 依赖）
npm run test:smoke   # 本地端到端冒烟（真实 Python 渲染 + mock OCR）
dsh --profile headless --dump-config   # 检查插件层已装配
```

## Roadmap

- [ ] LoRA 微调 DeepSeek-OCR decoder 做 SoM 检索（OCR-Memory 方案），把检索真正变成“模型输出编号”而非文本打分
- [ ] AgentOCR 式 segment optical caching（哈希分段缓存，降低渲染成本）
- [ ] 记忆命中热度驱动的动态衰减策略
- [ ] 自动注入 `/context` 让 Agent 每轮看到记忆摘要

## 相关参考

- DeepSeek-OCR（OCR1）：<https://arxiv.org/abs/2510.18234> · <https://github.com/deepseek-ai/DeepSeek-OCR>
- OCR-Memory（方法蓝本，未开源）：<https://arxiv.org/abs/2604.26622>
- AgentOCR（工程参考，已开源）：<https://github.com/langfengQ/AgentOCR>
