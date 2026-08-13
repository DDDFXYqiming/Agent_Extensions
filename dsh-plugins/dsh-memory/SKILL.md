---
name: memory
description: 跨会话长期记忆：读写经验 SOP 与环境事实。当任务涉及本机环境、工具配置、以前踩过的坑，或任务完成发现值得沉淀的验证经验时使用。
---

# 记忆管理（DSH 版）

跨会话长期记忆：L1 索引注入（每轮可见）+ L2 环境事实 + L3 任务经验。

## 触发时机

### 读取（什么时候查记忆）
- **新任务开始时**：若任务涉及本机环境、工具配置、特定技术栈、以前做过的类似事 → 先 `memory_list` 看有什么，再 `memory_read` 取相关条目
- **遇到困难/踩坑时**：`memory_read` 查是否有相关 SOP（关键词匹配 sops/ 文件名或 facts section）
- **模型提示词中的记忆索引（memory:index）**：每轮可见的 L1 存在性索引——看到相关触发词就应主动 `memory_read`/`memory_list` 取细节

### 写入（什么时候沉淀记忆）
任务完成（或阶段完成）且存在**行动验证成功**的信息时，调用 `memory_write`：

**可以写的**（必须带 evidence 证据）：
- 环境特异性事实：路径、配置、实测参数、工具行为（→ `entry_type: fact`）
- 复杂任务经验：多次重试才成功的坑点、隐藏前置条件、稳定步骤（→ `entry_type: sop`）
- 通用红线规律（→ 也可通过 memory_write sop 或直接建议维护 [RULES]）

**禁止写的**（写了就是污染）：
- ❌ 没有验证证据的信息（无行动，不记忆）
- ❌ 模型固有知识、推理猜测、未验证假设
- ❌ 易变状态：时间戳、PID、临时路径、一次性 ID
- ❌ 通用常识、日志记录、推理过程细节

### 索引同步
- `memory_write` 已自动同步 L1 索引，通常无需手动操作
- 手动改动过 facts.md / sops/ 文件后 → `memory_index` 重建索引
- 索引超 30 行时：精简 [RULES]（词级修改，禁 overwrite 全文）

## 存储布局

```
<home>/.dsh/memory/
├── memory_management_sop.md   L0 元规则（怎么管记忆）
├── index.txt                  L1 索引（≤30 行：L2/L3 存在性列表 + RULES）
├── facts.md                   L2 环境事实（## SECTION）
├── sops/*.md                  L3 任务经验
└── file_access_stats.json     读取热度统计
```

## 工具

| 工具 | 用途 |
|---|---|
| `memory_list` | 列出全部记忆（facts + sops + 索引行数） |
| `memory_read` | 读取指定记忆（index / fact 主题 / sop 文件名） |
| `memory_write` | 写入记忆（fact/sop，**evidence 必填**） |
| `memory_index` | 重建 L1 索引自动段 |

## 原则

1. **行动验证**：No Execution, No Memory. 只写成功验证过的信息。
2. **最小充分**：内容尽可能短；只记"遗忘会导致高成本重试"的信息。
3. **不删改验证事实**：可以压缩、迁移，严禁丢弃。
4. **主动写入**：记忆写入永远由模型/用户主动发起，不会自动修改配置或安装插件。
