# -*- coding: utf-8 -*-
"""
识图脚本：把本地图片交给配置的视觉模型识别，输出文字描述。

用法:
  python vision.py <图片路径> [提示词]
  python vision.py <图片路径> --mode ocr
  python vision.py <图片路径> --crop 10,10,300,200 --budget large
  python vision.py a.png --images b.png c.png --prompt "对比这两张截图"
  python vision.py --check

配置（不硬编码任何模型地址/模型名/密钥）：
  通过环境变量或 .env 提供 VISION_API_URL / VISION_MODEL / VISION_API_KEY，
  模板见 templates/.env.example。

功能：
  --budget small|normal|large   动态分辨率（默认 normal，约 1024×1024）
  --crop x1,y1,x2,y2            先裁局部再识别（坐标相对原图像素）
  --mode general|ocr|table|code|error  专用提示词与参数
  --images p1 p2 ...            附加多张图片，与主图一起发送
  --max-tokens N / --temperature T      覆盖默认值
  --no-resize                   不缩放，原图直发
  --save-crop 路径               把实际发送的（裁切+缩放后）图片存下来
  --check                       自检：配置 / PIL / 接口连通
"""

import argparse
import base64
import io
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request

# ── 配置（环境变量 / .env）──────────────────────────────────────────
VISION_API_URL = os.environ.get("VISION_API_URL", "").strip()
VISION_MODEL = os.environ.get("VISION_MODEL", "").strip()

MAX_FILE_BYTES = 10 * 1024 * 1024

# 分辨率预算（像素总数）：small≈512²、normal≈1024²、large≈1448²
BUDGET_PIXELS = {
    "small": 512 * 512,
    "normal": 1024 * 1024,
    "large": 1448 * 1448,
}
MIN_PIXELS = 224 * 224
FACTOR = 28  # 吸附网格（部分 VLM 的 patch grid 惯例，对通用接口无害）

# 模式：专用提示词 + 参数
MODES = {
    "general": {
        "prompt": "请详细描述这张图片的内容，包括其中的文字、报错信息等细节。",
        "max_tokens": 2048,
        "temperature": 1.0,
    },
    "ocr": {
        "prompt": (
            "请对这张图片进行OCR文字识别，提取图片中所有可见的文字内容，"
            "保持原始排版格式。不要概括、不要翻译，原样输出文字。"
        ),
        "max_tokens": 4096,
        "temperature": 0.2,
    },
    "table": {
        "prompt": (
            "这张图片是表格/数据截图。请把表格内容原样转成 Markdown 表格，"
            "保留所有行列与数值，不要省略或估算。"
        ),
        "max_tokens": 4096,
        "temperature": 0.2,
    },
    "code": {
        "prompt": (
            "这张图片是代码/日志/报错截图。请原样转述其中的代码、日志和错误信息，"
            "保留缩进与关键内容，再简要说明问题。"
        ),
        "max_tokens": 4096,
        "temperature": 0.2,
    },
    "error": {
        "prompt": (
            "这张图片是报错/异常截图。请原样转述所有错误文本（包括错误码、堆栈、"
            "文件名），再分析可能的原因。"
        ),
        "max_tokens": 4096,
        "temperature": 0.2,
    },
}


def log(msg):
    """调试信息走 stderr，不污染 stdout 的识别结果。"""
    print(msg, file=sys.stderr)


def get_key():
    return os.environ.get("VISION_API_KEY", "").strip()


def mime_for(path):
    ext = os.path.splitext(path)[1].lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "image/png")


def smart_resize(height, width, min_pixels, max_pixels, factor=FACTOR):
    """把 (h, w) 缩放进 [min_pixels, max_pixels]，吸附到 factor 的整数倍。"""
    if height * width < min_pixels:
        scale = math.sqrt(min_pixels / (height * width))
        height, width = int(height * scale), int(width * scale)
    if height * width > max_pixels:
        scale = math.sqrt(max_pixels / (height * width))
        height, width = int(height * scale), int(width * scale)
    height = max(factor, round(height / factor) * factor)
    width = max(factor, round(width / factor) * factor)
    return height, width


def encode_image(path, budget, crop=None, no_resize=False, save_path=None):
    """读取 -> 可选裁切 -> 可选动态缩放 -> base64。返回 (b64, mime, info)。"""
    from PIL import Image

    img = Image.open(path)
    orig_w, orig_h = img.size
    info = {"orig": f"{orig_w}x{orig_h}"}

    if crop:
        x1, y1, x2, y2 = crop
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(orig_w, x2), min(orig_h, y2)
        if x2 <= x1 or y2 <= y1:
            raise ValueError(f"裁剪区域无效: ({x1},{y1})-({x2},{y2})，图片尺寸 {orig_w}x{orig_h}")
        img = img.crop((x1, y1, x2, y2))
        info["crop"] = f"({x1},{y1})-({x2},{y2})"

    if not no_resize:
        max_pixels = BUDGET_PIXELS.get(budget, BUDGET_PIXELS["normal"])
        if img.width * img.height < MIN_PIXELS or img.width * img.height > max_pixels:
            target_h, target_w = smart_resize(img.height, img.width, MIN_PIXELS, max_pixels)
            if (target_w, target_h) != (img.width, img.height):
                img = img.resize((target_w, target_h), Image.LANCZOS)
            info["resized"] = f"{target_w}x{target_h} (budget={budget})"
        else:
            info["resized"] = f"原尺寸 {img.width}x{img.height}（预算内不缩放）"
    else:
        info["resized"] = "原图直发"

    buf = io.BytesIO()
    if img.mode in ("RGBA", "LA", "PA", "P"):
        fmt, mime, save_kwargs = "PNG", "image/png", {}
    else:
        fmt, mime, save_kwargs = "JPEG", "image/jpeg", {"quality": 90}
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
    img.save(buf, format=fmt, **save_kwargs)

    if save_path:
        img.save(save_path, format=fmt, **save_kwargs)
        info["saved"] = save_path

    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return b64, mime, info


def call_api(key, content, max_tokens, temperature):
    if not VISION_API_URL:
        raise RuntimeError("未配置 VISION_API_URL（见 templates/.env.example）")
    if not VISION_MODEL:
        raise RuntimeError("未配置 VISION_MODEL（见 templates/.env.example）")
    payload = {
        "model": VISION_MODEL,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        # 默认关闭模型思考，跳过推理直接回答（识图更快）；
        # 若模型不支持该参数可删除此字段，或改为 {"type": "adaptive"} 开启
        "thinking": {"type": "disabled"},
    }
    req = urllib.request.Request(
        VISION_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"视觉模型 API {e.code}: {body[:500]}")
    try:
        msg = data["choices"][0]["message"]
    except (KeyError, IndexError):
        raise RuntimeError(f"视觉模型返回异常: {json.dumps(data, ensure_ascii=False)[:500]}")
    text = msg.get("content")
    if text is None:
        text = msg.get("reasoning_content") or ""
        if not text:
            raise RuntimeError(f"视觉模型返回异常（无 content）: {json.dumps(data, ensure_ascii=False)[:500]}")
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip() or text


def analyze(paths, prompt, mode="general", budget="normal", crop=None,
            temperature=None, max_tokens=None, no_resize=False, save_crop=None):
    if mode not in MODES:
        raise ValueError(f"未知模式: {mode}（可选 {', '.join(MODES)}）")
    cfg = MODES[mode]
    if not prompt:
        prompt = cfg["prompt"]
    if max_tokens is None:
        max_tokens = cfg["max_tokens"]
    if temperature is None:
        temperature = cfg["temperature"]

    key = get_key()
    if not key:
        raise RuntimeError("找不到 VISION_API_KEY（见 templates/.env.example）")

    content = []
    for i, p in enumerate(paths):
        if not os.path.isfile(p):
            raise FileNotFoundError(f"图片不存在: {p}")
        size = os.path.getsize(p)
        if size > MAX_FILE_BYTES:
            raise ValueError(f"图片超过 {MAX_FILE_BYTES // 1024 // 1024}MB 限制: {p} ({size / 1024 / 1024:.1f}MB)")
        # 裁切只作用于第一张主图
        cur_crop = crop if i == 0 else None
        b64, mime, info = encode_image(
            p, budget, crop=cur_crop, no_resize=no_resize,
            save_path=save_crop if i == 0 else None,
        )
        log(f"[{p}] {' | '.join(f'{k}={v}' for k, v in info.items())}")
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    content.append({"type": "text", "text": prompt})

    return call_api(key, content, max_tokens, temperature)


def check():
    """自检：配置 / PIL / 接口连通（最小文本请求）。"""
    ok = True
    key = get_key()
    log(f"[check] VISION_API_KEY: {'可用（环境变量）' if key else '缺失（见 templates/.env.example）'}")
    if not key:
        ok = False
    log(f"[check] VISION_API_URL: {'已配置' if VISION_API_URL else '未配置'}")
    if not VISION_API_URL:
        ok = False
    log(f"[check] VISION_MODEL: {'已配置' if VISION_MODEL else '未配置'}")
    if not VISION_MODEL:
        ok = False
    try:
        import PIL  # noqa: F401
        log(f"[check] PIL: 可用（{PIL.__version__}）")
    except Exception as e:
        log(f"[check] PIL: 不可用（{e}），请 pip install pillow")
        ok = False
    if key and VISION_API_URL and VISION_MODEL:
        try:
            call_api(
                key,
                [{"type": "text", "text": "回复：OK"}],
                max_tokens=8,
                temperature=0,
            )
            log("[check] API 连通正常（认证通过）")
        except Exception as e:
            log(f"[check] API 调用失败 -> {e}")
            ok = False
    return ok


def main(argv=None):
    parser = argparse.ArgumentParser(description="识图（可配置视觉模型）")
    parser.add_argument("image", nargs="?", help="主图片路径")
    parser.add_argument("prompt", nargs="?", help="（可选）提示词，兼容旧用法")
    parser.add_argument("--prompt", dest="prompt_opt", default=None,
                        help="提示词（多图场景请用此选项，避免被 --images 吞掉）")
    parser.add_argument("--images", nargs="+", default=[], help="附加图片路径（与主图一起发送）")
    parser.add_argument("--budget", choices=["small", "normal", "large"], default="normal",
                        help="分辨率预算（默认 normal≈1024²）")
    parser.add_argument("--crop", default=None,
                        help="先裁切再识别：x1,y1,x2,y2（原图像素坐标）")
    parser.add_argument("--mode", choices=list(MODES), default="general",
                        help="识别模式（默认 general）")
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--no-resize", action="store_true", help="原图直发，不缩放")
    parser.add_argument("--save-crop", default=None, help="把实际发送的（裁切+缩放后）图片存到该路径")
    parser.add_argument("--check", action="store_true", help="自检配置/PIL/接口")

    args = parser.parse_args(argv)

    sys.stdout.reconfigure(encoding="utf-8")
    if args.check:
        sys.exit(0 if check() else 1)

    if not args.image:
        parser.print_usage()
        print("用法: python vision.py <图片路径> [提示词] [选项]；python vision.py --check 自检", file=sys.stderr)
        sys.exit(2)

    crop = None
    if args.crop:
        parts = [int(v) for v in args.crop.replace("，", ",").split(",")]
        if len(parts) != 4:
            raise SystemExit("--crop 需要 4 个数字: x1,y1,x2,y2")
        crop = tuple(parts)

    paths = [args.image] + list(args.images)
    prompt = args.prompt_opt if args.prompt_opt is not None else (args.prompt or "")
    try:
        result = analyze(
            paths,
            prompt,
            mode=args.mode,
            budget=args.budget,
            crop=crop,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            no_resize=args.no_resize,
            save_crop=args.save_crop,
        )
        print(result)
    except Exception as e:
        print(f"识图失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
