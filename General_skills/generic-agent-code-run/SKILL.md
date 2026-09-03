---
name: generic-agent-code-run
description: "Use when controlling Windows native desktop apps or real-browser sessions with GenericAgent-style code_run: dynamic Python execution, Win32/UIA/OCR/screenshots/CDP, and observe-act-verify loops."
license: MIT
compatibility: Windows only (Win32/UIA). Optional pywin32, Pillow, uiautomation, pyperclip; optional GenericAgent checkout via GENERIC_AGENT_ROOT / GENERIC_AGENT_PYTHON.
metadata:
  version: "1.0.0"
  author: Hermes Agent
  hermes:
    tags: [genericagent, code-run, windows, desktop-automation, win32, uia, ocr, cdp]
    related_skills: [hermes-agent, hermes-agent-skill-authoring, systematic-debugging]
---

# GenericAgent Code_Run

Operate Windows native desktop apps and real-browser sessions with the GenericAgent pattern: minimal fixed tools, a universal `code_run` execution path, local capability libraries, and a strict observe-act-verify loop.

The core idea is not to memorize many fixed tools. Generate short, task-specific Python code, execute it, return JSON evidence, and decide the next action from verified state.

## When to use

- Windows native app control: window enumeration, activation, screenshots, OCR, UIA, clicks, input.
- Real browser control with existing login state: TMWebDriver, Chrome extension CDP bridge, DOM/JS/CDP actions.
- Dynamic composition of local Python capabilities instead of a predeclared GUI tool set.
- Reliable verification after every side effect.

Do not copy GenericAgent's full agent loop, LLM client, or memory system — the host framework already owns those layers.

## Core mechanism

```text
observe -> generate minimal code_run Python -> execute -> return JSON evidence -> verify -> next action
```

A `code_run` block imports only the modules the current step needs:

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

Always return JSON.

## Desktop control recipe

1. Observe: enumerate windows with `win32gui.EnumWindows`, capture screenshots with `PIL.ImageGrab.grab`, inspect UIA/OCR only as needed.
2. Select target: verify title, hwnd, class, process, and rectangle before any side effect.
3. Act: use the minimum possible Win32/UIA/clipboard/mouse/keyboard action.
4. Verify: screenshot/OCR/UIA/window state after the action.
5. Report only verified results.

Details: [references/windows-control.md](references/windows-control.md), [references/code-run-core.md](references/code-run-core.md).

## Browser control recipe

Priority order:

```text
DOM/Runtime.evaluate -> CDP Input.dispatchMouseEvent -> physical mouse click
```

For real login state, use an existing browser session or a persistent context. Verify with URL, title, DOM text, screenshot, or API response.

Details: [references/browser-control.md](references/browser-control.md), probe: `scripts/browser_cdp_probe.py`.

## Safety rules

Never:

- Delete files or directories; no `rm -rf`, `Remove-Item -Recurse -Force`, or equivalents.
- Kill broad process classes such as all `python.exe`.
- Read or output credentials, API keys, cookies, or secrets.
- Submit payments or sensitive personal data without explicit confirmation.
- Click guessed coordinates without observation evidence.
- Claim success without verification.

Always:

- Confirm the target window before side effects.
- Keep each code_run snippet small.
- Return JSON with evidence.
- Verify after every side effect.
- Report failures honestly.

Full list: [references/safety-rules.md](references/safety-rules.md).

## Environment

Portable by design — never hardcode a local GenericAgent checkout path.

```powershell
$env:GENERIC_AGENT_ROOT='D:\path\to\GenericAgent'
$env:GENERIC_AGENT_PYTHON='D:\path\to\GenericAgent\.venv\Scripts\python.exe'
```

`GENERIC_AGENT_PYTHON` is for helpers needing compiled packages (Pillow/pywin32). With neither set, helpers use the current Python and return truthful JSON setup hints when a dependency is missing.

Details: [references/environment.md](references/environment.md).

## Quick local probes

Run from this skill directory:

```powershell
python .\scripts\desktop_probe.py
python .\scripts\window_ops.py --list
python .\scripts\screenshot_ocr.py --screen
python .\scripts\browser_cdp_probe.py --status
```

## Verification checklist

- [ ] `SKILL.md` frontmatter parses.
- [ ] Linked references/templates/scripts are present.
- [ ] Helper scripts compile.
- [ ] `desktop_probe.py` returns JSON.
- [ ] `window_ops.py --list` returns JSON.
- [ ] `screenshot_ocr.py --screen` either captures an image or returns a truthful JSON error.
- [ ] `browser_cdp_probe.py --status` returns connected/unavailable as JSON without crashing.
