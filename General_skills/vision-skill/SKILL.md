---
name: vision-skill
description: 识别图片内容。当用户发送图片、截图、报错图，或要求分析某张本地图片时使用。先定位图片文件路径，再运行 vision.py 脚本获取文字描述。
license: MIT
compatibility: 需要 Python 3 + Pillow，以及任意 OpenAI 兼容多模态模型的 API Key（通过环境变量注入，技能不硬编码）。
---

# 识图技能

当主模型不支持直接读取图片时，图片不会进入对话上下文，但用户消息中通常会附带图片的本地路径（形如剪贴板截图或附件路径）。

## 配置（首次使用）

1. 复制 `templates/.env.example` 为技能目录下的 `.env`（脚本启动时自动加载，无需额外依赖），填入：
   - `VISION_API_URL`：视觉模型 OpenAI 兼容**完整接口地址**（含路径，如 `https://api.example.com/v1/chat/completions`）
   - `VISION_MODEL`：模型名
   - `VISION_API_KEY`：API Key

   也可以直接导出同名环境变量；**环境变量优先级高于 `.env` 文件**（便于 CI/容器注入）。
2. 运行 `python scripts/vision.py --check` 自检，确认配置生效。

## 使用步骤

1. 从用户消息中找到图片路径；路径不明确时先找最近的剪贴板截图：

   ```powershell
   Get-ChildItem $env:TEMP\codex-clipboard-*.png | Sort-Object LastWriteTime -Descending | Select-Object -First 3 FullName,Length
   ```

2. 运行脚本识别图片：

   ```powershell
   cd <技能目录>; python scripts/vision.py "<图片绝对路径>" "（可选）具体识图要求"
   ```

3. 基于脚本输出的文字描述回答用户；描述中的重要文字、报错信息要原样转述。

## 常用选项（按场景选择）

| 场景 | 命令 |
|---|---|
| 一般识图 | `vision.py "<图>"` |
| 提取所有文字（OCR，保持排版） | `vision.py "<图>" --mode ocr` |
| 表格/数据截图转 Markdown 表格 | `vision.py "<图>" --mode table` |
| 代码/日志/报错截图 | `vision.py "<图>" --mode code` 或 `--mode error` |
| 小字看不清：先全图定位，再裁局部放大读 | `vision.py "<图>" --crop x1,y1,x2,y2 --budget large` |
| 多张图对比 / 批量读 | `vision.py "a.png" --images "b.png" "c.png" --prompt "对比这两张"` |
| 高分辨率细节（4K 截图小字） | `vision.py "<图>" --budget large` |
| 原图直发（不缩放） | `vision.py "<图>" --no-resize` |
| 环境自检（配置/PIL/接口） | `vision.py --check` |

## 高质量识图工作流

1. **先整体**：用默认参数读一遍，拿到全局描述并定位疑点（小字、报错、表格局部）。
2. **再局部**：对疑点区域用 `--crop x1,y1,x2,y2` 裁出来，配合 `--budget large` 放大后再读，直到信息足够。
3. **关键内容原样转述**：报错码、数字、代码、日志必须逐字转述，不概括、不脑补。

`--crop` 坐标为原图像素坐标（左上角为原点）；`--save-crop 路径` 可把实际发送的裁切图存下来复核。

## 注意

- 不要假装看到了图片，必须先运行脚本拿到描述再回答。
- 脚本报错（文件不存在、超过大小限制、未配置、API 失败）时如实转述错误并给出建议。
- 多张图一起发送时，`--crop` 只作用于第一张主图。
- 脚本默认关闭模型思考（`thinking: disabled`，识图更快）；模型不支持该参数时删掉对应字段，或改为 `adaptive` 开启。
- 输出乱码（旧版控制台代码页 936）时先执行 `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $env:PYTHONIOENCODING='utf-8'` 再跑脚本；脚本本身已对交互终端/管道分别处理编码。
- 脚本重定向到文件时产物是 UTF-8，读取用 `Get-Content -Encoding UTF8`，否则中文会花。

## 安装到具体宿主

- DSH 接入（含框架补丁步骤，人类安装者才需要）：[references/dsh-integration.md](references/dsh-integration.md)
