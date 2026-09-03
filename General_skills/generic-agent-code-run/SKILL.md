---
name: generic-agent-code-run
description: "用 GenericAgent 式 code_run 操控 Windows 原生桌面应用与真实浏览器会话时使用：动态执行 Python、Win32/UIA/OCR/截图/CDP，以及观察-执行-校验闭环。适用于操作桌面客户端、带登录态的网页、无 API 的图形界面任务。"
license: MIT
compatibility: 仅支持 Windows（依赖 Win32/UIA）。可选依赖 pywin32、Pillow、uiautomation、pyperclip；可选指向本地 GenericAgent 检出（GENERIC_AGENT_ROOT / GENERIC_AGENT_PYTHON）。
metadata:
  version: "1.0.0"
  author: Hermes Agent
  hermes:
    tags: [genericagent, code-run, windows, desktop-automation, win32, uia, ocr, cdp]
    related_skills: [hermes-agent, hermes-agent-skill-authoring, systematic-debugging]
---

# GenericAgent Code_Run

用 GenericAgent 的模式操作 Windows 原生桌面应用与真实浏览器会话：极少的固定工具、一条通用的 `code_run` 执行通道、本地能力库，外加严格的「观察-执行-校验」闭环。

核心思路不是背下一大堆固定工具，而是：针对当前任务生成一小段专用 Python，执行它，拿回 JSON 证据，再从已验证的状态决定下一步动作。

## 何时使用

- Windows 原生应用操控：窗口枚举、激活、截图、OCR、UIA、点击、输入。
- 带已有登录态的真实浏览器操控：TMWebDriver、Chrome 扩展 CDP 桥、DOM/JS/CDP 操作。
- 需要临时组合本地 Python 能力，而不是依赖预先声明好的 GUI 工具集。
- 每一次副作用之后都必须可靠地校验结果。

不要照搬 GenericAgent 的完整 agent loop、LLM 客户端或记忆系统——这些层次由宿主框架负责。

## 核心机制

```text
observe -> generate minimal code_run Python -> execute -> return JSON evidence -> verify -> next action
```

一个 `code_run` 代码块只导入当前这一步真正需要的模块：

```python
import json
# optional imports as needed:
# import win32gui, win32api, win32con
# from PIL import ImageGrab
# import pyperclip, uiautomation
# from TMWebDriver import TMWebDriver

result = {"ok": False, "action": "", "evidence": {}, "error": None}
# perform one minimal action or one observation
print(json.dumps(result, ensure_ascii=False, indent=2))
```

一律返回 JSON。

## 桌面操控流程

1. 观察：用 `win32gui.EnumWindows` 枚举窗口，用 `PIL.ImageGrab.grab` 截图，UIA/OCR 只在需要时看。
2. 锁定目标：产生任何副作用前，先核对标题、hwnd、class、进程和窗口矩形区域。
3. 执行：使用尽可能小的 Win32/UIA/剪贴板/鼠标/键盘动作。
4. 校验：动作之后用截图/OCR/UIA/窗口状态确认结果。
5. 只报告已验证的结论。

细则见 [references/windows-control.md](references/windows-control.md)、[references/code-run-core.md](references/code-run-core.md)。

## 浏览器操控流程

优先级顺序：

```text
DOM/Runtime.evaluate -> CDP Input.dispatchMouseEvent -> physical mouse click
```

需要真实登录态时，复用已有浏览器会话或持久化上下文。校验手段：URL、标题、DOM 文本、截图或接口响应。

细则见 [references/browser-control.md](references/browser-control.md)，探针脚本：`scripts/browser_cdp_probe.py`。

## 安全规则

绝不做：

- 删除文件或目录；不跑 `rm -rf`、`Remove-Item -Recurse -Force` 及等价命令。
- 批量杀进程，例如杀掉所有 `python.exe`。
- 读取或输出凭据、API Key、Cookie 或任何机密。
- 未经明确确认就提交支付或敏感个人信息。
- 在没有观察证据的情况下点击凭猜测得出的坐标。
- 未做校验就宣称成功。

必须做：

- 副作用之前先确认目标窗口。
- 每段 code_run 片段保持简短。
- 返回带证据的 JSON。
- 每次副作用之后都校验。
- 如实报告失败。

完整清单见 [references/safety-rules.md](references/safety-rules.md)。

## 环境

设计上要求可移植——绝不把本地 GenericAgent 检出路径写死。

```powershell
$env:GENERIC_AGENT_ROOT='D:\path\to\GenericAgent'
$env:GENERIC_AGENT_PYTHON='D:\path\to\GenericAgent\.venv\Scripts\python.exe'
```

`GENERIC_AGENT_PYTHON` 用于需要编译型依赖包（Pillow/pywin32）的辅助脚本。两个变量都不设时，辅助脚本使用当前 Python，并在依赖缺失时返回真实的 JSON 安装提示，而不是静默失败。

细则见 [references/environment.md](references/environment.md)。

## 本地快速探针

在本技能目录下运行：

```powershell
python .\scripts\desktop_probe.py
python .\scripts\window_ops.py --list
python .\scripts\screenshot_ocr.py --screen
python .\scripts\browser_cdp_probe.py --status
```

## 验收清单

- [ ] `SKILL.md` frontmatter 能被解析。
- [ ] 引用的 references/templates/scripts 文件都存在。
- [ ] 辅助脚本能通过语法编译。
- [ ] `desktop_probe.py` 返回 JSON。
- [ ] `window_ops.py --list` 返回 JSON。
- [ ] `screenshot_ocr.py --screen` 要么成功截图，要么返回一条真实的 JSON 错误。
- [ ] `browser_cdp_probe.py --status` 以 JSON 返回已连接/不可用，且不会崩溃。
