# dsh-memory

**DeepSeek Harness（DSH）跨会话长期记忆插件** —— L1 索引注入（存在性编码）+ L2 环境事实 + L3 任务经验，借鉴 [GenericAgent](https://github.com/) 记忆系统（L0-L3 分层 + 行动验证公理），**不含自进化**（无后台调度、无自动装插件、无情绪挖掘）。

## 能力

| 组件 | 说明 |
|---|---|
| `memory:index` 注入 | 通过 `ctx.systemPrompt.context` 把 L1 索引注入每轮模型上下文（实时读文件，改动即生效） |
| `memory`（运行时 skill） | 触发语义：何时读、何时写、何时同步索引 |
| `memory_list` | 列出全部记忆（L2 facts + L3 sops + 索引行数） |
| `memory_read` | 读取指定记忆（index / fact 主题 / sop 文件名） |
| `memory_write` | 写入记忆（fact/sop，**evidence 必填** = 行动验证公理） |
| `memory_index` | 重建 L1 索引自动段（保留 [RULES] 手动段） |

## 设计（与 GenericAgent 的对应）

| GenericAgent | dsh-memory |
|---|---|
| `get_global_memory()` 启动注入 + 每 10 轮刷新 | `ctx.systemPrompt.context` 每轮实时注入 L1（更频繁，改动即时生效） |
| `start_long_term_update` 工具（模型主动蒸馏） | `memory_write` 工具（模型/用户主动，evidence 强制） |
| `global_mem_insight.txt`（L1 ≤30 行） | `index.txt`（含 `<!-- AUTO -->` 自动段 + `[RULES]` 手动段） |
| `global_mem.txt`（L2 事实） | `facts.md`（`## SECTION` upsert） |
| `../memory/*_sop.md`（L3 SOP） | `sops/*.md`（slug 文件名） |
| `file_access_stats.json` 热度 | 同款轻量热度统计 |
| `memory_management_sop.md`（L0 公理） | 同款 L0 模板（行动验证/禁易变/最小指针/不删改） |
| reflect/ 自进化调度 | ❌ **明确不做** |

## 安装

```powershell
# bundle 标准安装（自带 cordis.patch.yml，贡献 id: memory）
dsh plugin --profile web add E:\AI_Projects\dsh-plugins\dsh-memory
```

### 配置（可选，覆盖默认）

```yaml
# profile cordis.patch.yml —— 裸条目覆盖 bundle 行（勿重复 insert！）
- id: memory
  config:
    memoryDir: ''        # 默认 <home>/.dsh/memory
    maxIndexLines: 30
    progressive: true
```

## 存储布局

```
<home>/.dsh/memory/
├── memory_management_sop.md   L0 元规则
├── index.txt                  L1 索引（≤30 行）
├── facts.md                   L2 环境事实
├── sops/*.md                  L3 任务经验
└── file_access_stats.json     读取热度
```

## 核心公理（继承自 GenericAgent）

1. **行动验证**：No Execution, No Memory —— `memory_write` 的 evidence 必填，只写成功验证过的信息
2. **神圣不可删改**：已验证事实可压缩/迁移，严禁丢弃
3. **禁易变状态**：时间戳/PID/临时路径不存
4. **最小充分指针**：L1 只写存在性，细节在 L2/L3 按需取

## 相关

- 底层接缝：`ctx.systemPrompt.context` / `ctx.skills.register` / `ctx.tools.register`（全部官方 API，零框架补丁）
- 授权：MIT
