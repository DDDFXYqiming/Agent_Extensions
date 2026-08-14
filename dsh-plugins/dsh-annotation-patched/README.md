# dsh-annotation-patched

DSH Web「选中批注」插件的本地增强版（fork 维护）。

## 来源

- 上游项目：[omdsh-dev/dsh-annotation](https://github.com/omdsh-dev/dsh-annotation)（MIT License，v1.3.13）
- 上游能力：选中助手回复文字 → 批注（可留空）→ 回车随消息发送；模型按 `Annotation N:` 逐条对照回复（回复中为可悬停芯片）；批注块不出现在自己的气泡里（零闪烁隐藏）
- 本目录为上游代码 + 2026-08-14 本地增强（client.js 内所有改动均带 `PATCH(2026-08-14)` 标记，可 `grep` 定位）

## 增强内容（相对上游 v1.3.13）

### 1. Codex 式「选中即引用」（空批注自动附带）

上游需要「选中 → 点批注 → 保存」三步才能引用；本版改为**选中助手消息文字后直接回车，即自动随消息附带**（空批注 = 纯引用，无需写任何内容）。

- 选中确认时（`onSelection`）**立即暂存选区快照** `ui.pendingCapture`，不等 settle 250ms —— 修复"选中后快速点输入框导致快照丢失"的竞态
- composer 回车时（`onKeyDown`）先 `maybeCaptureSelection()` 消费快照入批注清单，再走既有发送链路
- **Esc = 明确放弃**待消费快照；点击输入框（焦点转移）不视为放弃
- 同文本去重沿用上游规则（已在清单中的文字不重复捕获）

### 2. 幽灵引用修复（拼稿即清）

上游 `quotes`（待发送批注集）**唯一**清理路径在 `decorateAll` 装饰扫描轮询（等气泡渲染 → 切批注块 → 贴标签全部成功才清空），存在竞态窗口：气泡未渲染、标记缺失或快速连发时 `quotes` 残留，导致**之后没选中也附带旧批注**。

本版在 `attachAndSend` 拼稿成功后**立即清空** `quotes` + `pendingCapture`（草稿中的批注块即已交付的引用；防重复拼稿由上游 `draft.indexOf('我批注了以下')` 逻辑兜底）。

### 3. 维护性

- 所有改动带 `PATCH(2026-08-14)` 注释标记，上游更新时可快速定位 diff 重新套用
- 调试日志 `[annotation] Codex 式自动引用（空批注）…` / 拼稿日志带发送条数（DevTools Console 可查）

## 安装

本目录供 `Agent_Extensions` 仓库维护；本机 web profile 使用 link 依赖指向本目录：

```bash
# package.json dependencies 中：
# "@omdsh-dev/dsh-annotation": "link:C:/Users/39795/Agent_Extensions/dsh-plugins/dsh-annotation-patched"
# 或从本地目录安装：
dsh plugin --profile web add C:/Users/39795/Agent_Extensions/dsh-plugins/dsh-annotation-patched
```

## 已知边界

- 只支持选中**助手消息**（用户自己发的消息不处理）
- 自动引用仅在**回车发送**时触发（点发送按钮不触发）
- 浏览器端插件：改动 `client.js` 后需 **Ctrl+F5 强刷**（或换浏览器）才生效；**pnpm 更新会覆盖** node_modules 里的副本，须以本目录为源重新 link
- 强依赖 DSH Web DOM 结构（`[data-time-hover-root]`、`[class*="bubble"]`、`[data-composer-card]` 等），DSH UI 升级可能失效

## License

MIT（保留上游版权声明，见 LICENSE）
