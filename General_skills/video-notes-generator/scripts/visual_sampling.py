"""Bounded local candidate sampling; no model calls. Pillow is optional for sheets."""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess


def source_identity(path):
    p = Path(path).resolve()
    s = p.stat()
    return {"path": str(p), "size": s.st_size, "mtime_ns": s.st_mtime_ns}


def preserve_review_history(visual, previous):
    """Material retries must not orphan supplemental IDs used by an existing final."""
    if previous.get("source_identity") == visual.get("source_identity"):
        visual["supplemental_frames"] = previous.get("supplemental_frames", [])
    if previous.get("cache_key") != visual.get("cache_key"):
        visual["sampling"]["warnings"].append(
            "Source or sampling settings changed; revalidate prior final notes and frame citations")
    return visual


def probe_duration(ffmpeg, path):
    probe = os.getenv("FFPROBE") or str(Path(ffmpeg).with_name("ffprobe" + Path(ffmpeg).suffix))
    r = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def scan_changes(ffmpeg, path, duration):
    # Stream at most ~1200 tiny grayscale samples. No full-video buffering.
    interval = max(2.0, duration / 1200)
    command = [ffmpeg, "-v", "error", "-i", str(path), "-an", "-vf",
               f"fps=1/{interval},scale=160:90", "-pix_fmt", "gray", "-f", "rawvideo", "-"]
    previous = None
    scores = []
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as proc:
        while True:
            frame = proc.stdout.read(160 * 90)
            if len(frame) != 160 * 90:
                break
            # Regional change keeps a small UI panel from being diluted by the whole screen.
            if previous is None:
                score = 0.0
            else:
                regions = [0.0] * 9
                for i, (a, b) in enumerate(zip(frame, previous)):
                    region = min(2, (i // 160) // 30) * 3 + min(2, (i % 160) // 54)
                    regions[region] += abs(a - b)
                score = max(regions) / (54 * 30 * 255)
            scores.append({"timestamp": min(duration - .05, len(scores) * interval + interval / 2),
                           "change_score": round(score, 5), "signature": list(frame[::40])})
            previous = frame
        if proc.wait() != 0:
            raise RuntimeError("Local visual scan failed")
    return interval, scores


def choose_candidates(duration, interval, budget, scores, segments):
    """Coverage first, then regional changes and language cues. Never claim semantic completeness."""
    if duration <= 0 or interval <= 0 or budget < 1:
        raise ValueError("duration, frame interval and frame budget must be positive")
    selected = []
    def add(t, reason, score=0):
        t = round(max(0, min(duration - .05, t)), 3)
        if any(abs(f["timestamp"] - t) < min(1.0, duration / 10) for f in selected):
            return
        if len(selected) < budget:
            selected.append({"timestamp": t, "selection_reason": reason, "change_score": score})
    # Explicit interval controls desired coverage, but budget always bounds model-facing files.
    desired = max(2, math.ceil(duration / interval) + 1)
    count = min(desired, max(2, math.ceil(budget * .5)), budget)
    for i in range(count):
        add(.25 + max(0, duration - .5) * i / max(1, count - 1), "coverage")
    cues = [s for s in segments if any(w in s.get("text", "").lower() for w in
            ("看这", "如图", "点击", "选择", "结果", "如下", "图表", "click", "as shown"))]
    for s in cues[:max(0, budget // 4)]:
        add(float(s["start"]) + 1, "transcript_cue")
    chosen_signatures = []
    for f in sorted(scores, key=lambda f: f["change_score"], reverse=True):
        if f["change_score"] < .025:
            break
        signature = f.get("signature", [])
        if signature and any(sum(abs(a-b) for a,b in zip(signature, prior)) / len(signature) < 3
                             for prior in chosen_signatures):
            continue
        previous_count = len(selected)
        add(f["timestamp"], "regional_change", f["change_score"])
        if signature and len(selected) > previous_count:
            chosen_signatures.append(signature)
    return sorted(selected, key=lambda f: f["timestamp"])


def extract_frame(ffmpeg, source, path, timestamp, width=960, crop=None):
    filters = []
    if crop:
        x, y, w, h = crop
        if min(x, y) < 0 or min(w, h) <= 0:
            raise ValueError("crop must be x,y,width,height with nonnegative origin and positive size")
        filters.append(f"crop={w}:{h}:{x}:{y}")
    if width > 0:
        filters.append(f"scale=min({width}\\,iw):-2")
    cmd = [ffmpeg, "-v", "error", "-y", "-ss", str(timestamp), "-i", str(source), "-frames:v", "1"]
    if filters:
        cmd += ["-vf", ",".join(filters)]
    r = subprocess.run(cmd + ["-q:v", "2", str(path)], capture_output=True)
    if r.returncode or not Path(path).is_file() or Path(path).stat().st_size == 0:
        raise RuntimeError(f"Frame extraction failed at {timestamp}: {r.stderr.decode(errors='replace')[:250]}")


def contact_sheets(frames, directory):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return []
    paths = []
    for offset in range(0, len(frames), 6):
        group = frames[offset:offset + 6]
        sheet = Image.new("RGB", (960, math.ceil(len(group) / 2) * 300), "#eeeeee")
        draw = ImageDraw.Draw(sheet)
        for i, frame in enumerate(group):
            with Image.open(frame["image_path"]) as original:
                preview = original.copy()
                preview.thumbnail((480, 270))
                x, y = (i % 2) * 480, (i // 2) * 300
                sheet.paste(preview, (x, y + 25))
            draw.text((x + 8, y + 6), f"F{frame['index']:03d}  {frame['timestamp']:.2f}s", fill="black")
        path = str(Path(directory).resolve() / f"overview_{offset // 6 + 1:02d}.jpg")
        sheet.save(path, quality=85)
        paths.append(path)
    return paths


def prepare_visuals(ffmpeg, source, directory, segments, interval=30, budget=24, width=960):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(ffmpeg, source)
    identity = source_identity(source)
    key = {"source": identity, "interval": interval, "budget": budget, "width": width,
           "segments_hash": hashlib.sha256(json.dumps(segments, ensure_ascii=False).encode()).hexdigest(),
           "version": 2}
    cache = directory / "sampling.json"
    if cache.is_file():
        old = json.loads(cache.read_text(encoding="utf-8"))
        if old.get("cache_key") == key and all(Path(f["image_path"]).is_file() for f in old["frames"]):
            return old
    warnings = []
    try:
        scan_interval, scores = scan_changes(ffmpeg, source, duration)
    except (OSError, RuntimeError) as e:
        scan_interval, scores = None, []
        warnings.append(str(e) + "; using coverage and transcript cues")
    candidates = choose_candidates(duration, interval, budget, scores, segments)
    frames = []
    for candidate in candidates:
        index = len(frames) + 1
        t = candidate["timestamp"]
        path = str(directory / f"frame_{index:03d}_{t:.3f}s.jpg")
        extract_frame(ffmpeg, source, path, t, width)
        nearby = [s for s in segments if float(s.get("start", 0)) <= t + 8 and float(s.get("end", 0)) >= t - 8]
        frames.append(dict(candidate, index=index, image_path=path,
                           timestamp_text=f"{int(t)//60:02d}:{int(t)%60:02d}",
                           nearby_transcript=" ".join(s["text"] for s in nearby),
                           visual_note="", review_status="unreviewed"))
    times = [0] + [f["timestamp"] for f in frames] + [duration]
    result = {"cache_key": key, "source_identity": identity, "source_video": identity["path"],
              "duration": duration, "frames": frames, "contact_sheets": contact_sheets(frames, directory),
              "sampling": {"candidate_scan_count": len(scores), "scan_interval_seconds": scan_interval,
                           "requested_coverage_interval": interval, "frame_budget": budget,
                           "max_sample_gap_seconds": max(b-a for a, b in zip(times, times[1:])),
                           "budget_reached": len(frames) >= budget, "warnings": warnings,
                           "limitation": "Sparse samples; brief events and changes between samples can be missed."}}
    cache.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def supplement(ffmpeg, manifest_path, timestamps, width=0, crop=None):
    manifest_path = Path(manifest_path).resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = data["source_video"]
    if source_identity(source) != data["source_identity"]:
        raise ValueError("Source video changed; regenerate manifest before supplemental review")
    duration = data["duration"]
    if any(t < 0 or t >= duration for t in timestamps):
        raise ValueError("Review timestamps must be within the video")
    folder = manifest_path.parent / (manifest_path.stem + "_review")
    folder.mkdir(exist_ok=True)
    frames = data.setdefault("supplemental_frames", [])
    for t in timestamps:
        signature = {"timestamp": t, "width": width, "crop": crop}
        if any(f.get("request") == signature and Path(f["image_path"]).is_file() for f in frames):
            continue
        path = folder / (hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()[:16] + ".png")
        extract_frame(ffmpeg, source, path, t, width, crop)
        frames.append({"id": f"R{len(frames)+1:03d}", "timestamp": t, "image_path": str(path),
                       "request": signature, "review_status": "unreviewed"})
    manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return frames
