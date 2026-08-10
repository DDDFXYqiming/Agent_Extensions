---
name: vision
description: 识别图片内容。当用户发送图片、截图、报错图，或要求分析某张本地图片时使用。先定位图片文件路径，再运行 vision.py 脚本获取文字描述。
---

# 识图技能

当主模型不支持直接读取图片时，图片不会进入对话上下文，但用户消息中通常会附带图片的本地路径（形如 `C:/Users/.../codex-clipboard-*.png` 或附件路径）。

## 配置（首次使用）

1. 复制 `templates/.env.example` 为技能目录下的 `.env`（或直接导出环境变量），填入：
   - `VISION_API_URL`：视觉模型 OpenAI 兼容接口地址
   - `VISION_MODEL`：模型名
   - `VISION_API_KEY`：API Key
2. 运行 `python scripts/vision.py --check` 自检，确认配置生效。

本技能不硬编码任何模型地址、模型名或密钥，全部通过环境变量注入。

## 使用步骤

1. 从用户消息中找到图片路径；如果路径不明确，先查找最近的剪贴板截图：

   ```powershell
   Get-ChildItem $env:TEMP\codex-clipboard-*.png | Sort-Object LastWriteTime -Descending | Select-Object -First 3 FullName,Length
   ```

2. 运行脚本识别图片：

   ```powershell
   python <技能目录>/scripts/vision.py "<图片绝对路径>" "（可选）具体识图要求"
   ```

3. 脚本输出图片的文字描述（可能较长），基于描述回答用户的问题；描述中的重要文字、报错信息要原样转述。

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
- 如果脚本报错（文件不存在、超过大小限制、未配置、API 失败），如实转述错误并给出建议。
- 多张图一起发送时，`--crop` 只作用于第一张主图。
- 脚本默认关闭模型思考（`thinking: disabled`，识图更快）；若模型不支持该参数可删除对应字段，或改为 `adaptive` 开启。
