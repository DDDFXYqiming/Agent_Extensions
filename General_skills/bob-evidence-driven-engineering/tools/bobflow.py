#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bobflow — Bob 式证据驱动工程流程引擎（纯标准库，随仓库分发）。

设计要点
--------
* 流程约束落在退出码上，不落在提示词上：
  0 PASS 可继续/可交付 · 2 BLOCKED 缺前置 · 3 FAIL 检查未过 · 4 WAIVER 需人工豁免。
* 状态全部外置到 .bob/，任何 harness、任何会话读盘即可接续。
* 防作弊：源码指纹、报告时效、基线差分（断言减少 / skip 增加 / 门槛下调）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

BOB_DIR = ".bob"
DOC_DIR = "docs/bob"
WAIVER_DIR = "docs/bob/waivers"
EXIT_PASS, EXIT_BLOCKED, EXIT_FAIL, EXIT_WAIVER = 0, 2, 3, 4
TS = time.strftime("%Y%m%d-%H%M%S")

DEFAULT_EXTS = {
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs",
    ".java", ".kt", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php",
    ".swift", ".scala", ".sh", ".sql", ".vue", ".svelte",
}
EXCLUDE_DIRS = {
    ".git", BOB_DIR, "node_modules", "__pycache__", "venv", ".venv", "dist",
    "build", "coverage", ".tox", ".mypy_cache", ".pytest_cache", "vendor",
    ".idea", ".vscode", "out", "target",
}

TEST_DEF = re.compile(
    r"(^\s*def test_\w+|^\s*async def test_\w+|\bit\(\s*['\"`]|"
    r"\btest\(\s*['\"`]|^\s*func Test\w+\(|@Test|public void test\w+\()",
    re.M,
)
SKIP_MARK = re.compile(
    r"(pytest\.mark\.skip|unittest\.skip|unittest\.expectedFailure|"
    r"it\.skip\(|it\.todo\(|test\.skip\(|test\.todo\(|describe\.skip\(|"
    r"@Disabled|@Ignore|t\.Skip\(|xit\(|xdescribe\()"
)

def hook_body(stage: str, py: str) -> str:
    """git 钩子脚本。py 是 init 时探测到的解释器绝对路径，
    直接写死，避免运行时 command -v python3 命中 Windows 商店占位符。"""
    return f"""#!/bin/sh
# bobflow gate: {stage}
root=$(git rev-parse --show-toplevel) || exit 0
cd "$root" || exit 0
if [ -f tools/bobflow.py ]; then
  PY="{py}"
  if [ ! -x "$PY" ]; then PY=$(command -v python 2>/dev/null || command -v python3 2>/dev/null); fi
  "$PY" tools/bobflow.py hook {stage} || exit 1
fi
exit 0
"""


# ---------------------------------------------------------------- 基础设施

def find_root() -> Path:
    r = os.environ.get("BOB_ROOT")
    if r:
        return Path(r)
    try:
        out = subprocess.run("git rev-parse --show-toplevel", shell=True,
                             capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except Exception:
        pass
    return Path.cwd()


def read_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def sh(cmd: str, cwd: Path, timeout: int = 900):
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, shell=True, cwd=str(cwd), timeout=timeout,
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        return proc.returncode, proc.stdout, proc.stderr, round(time.time() - t0, 2)
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s", round(time.time() - t0, 2)
    except Exception as e:  # noqa: BLE001
        return 126, "", str(e), round(time.time() - t0, 2)


def load_cfg(root: Path) -> dict:
    cfg = read_json(root / BOB_DIR / "config.json")
    if cfg is None:
        die(f"BLOCKED: missing config — 先运行 python tools/bobflow.py init", EXIT_BLOCKED)
    return cfg


def die(msg: str, code: int):
    print(msg)
    sys.exit(code)


def fingerprint(root: Path, cfg: dict) -> dict:
    exts = set(cfg.get("source_exts", [])) | DEFAULT_EXTS
    h, count = hashlib.sha256(), 0
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if p.suffix.lower() not in exts:
            continue
        h.update(str(rel).replace("\\", "/").encode("utf-8"))
        h.update(hashlib.sha256(p.read_bytes()).digest())
        count += 1
    return {"digest": h.hexdigest(), "files": count, "ts": TS}


def test_stats(root: Path, cfg: dict) -> dict:
    """统计测试断言数与 skip 数，作为反作弊基线。"""
    exts = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".java"}
    tests = skips = 0
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        rel = p.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        name = p.name.lower()
        in_tests_dir = any(part.lower() in ("tests", "test", "__tests__", "spec", "specs")
                           for part in rel.parts)
        name_hit = (name.startswith("test_") or name.startswith("test.")
                    or name.endswith(("_test.py", "_test.go", "_test.java")))
        if not (in_tests_dir or name_hit or ".spec." in name or ".test." in name):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        tests += len(TEST_DEF.findall(text))
        skips += len(SKIP_MARK.findall(text))
    return {"tests": tests, "skips": skips}


def spec_files(root: Path) -> list:
    d = root / DOC_DIR
    return [d / "spec.md", d / "acceptance.feature", d / "qa-plan.md"]


def spec_hashes(root: Path) -> dict:
    out = {}
    for p in spec_files(root):
        if p.exists():
            out[str(p.relative_to(root)).replace("\\", "/")] = \
                hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def latest_evidence(root: Path):
    d = root / BOB_DIR / "evidence"
    if not d.is_dir():
        return None
    dirs = sorted([x for x in d.iterdir() if x.is_dir()])
    if not dirs:
        return None
    return read_json(dirs[-1] / "evidence.json")


def approvals(root: Path) -> list:
    d = root / BOB_DIR / "approvals"
    if not d.is_dir():
        return []
    return sorted(d.glob("spec-*.json"))


def qa_signs(root: Path) -> list:
    """独立 QA 验证签字记录（qa-*.json），与规格意图签字（spec-*.json）分开。"""
    d = root / BOB_DIR / "approvals"
    if not d.is_dir():
        return []
    return sorted(d.glob("qa-*.json"))


# ---------------------------------------------------------------- 报告校验

def validate_report(parser: str, path: Path, cfg: dict):
    """返回 (ok, note)。缺文件、格式不符、未达门槛都算失败。"""
    if not path.exists():
        return False, f"report missing: {path}"
    try:
        if parser == "exitcode":
            return True, "exitcode only"
        if parser == "junit":
            import xml.etree.ElementTree as ET
            root = ET.parse(path).getroot()
            suites = [root] if root.tag == "testsuite" else root.findall(".//testsuite")
            tests = sum(int(s.get("tests", 0)) for s in suites)
            fails = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
            skipped = sum(int(s.get("skipped", 0)) for s in suites)
            if tests <= 0:
                return False, "junit: 零用例"
            if tests - skipped <= 0:
                return False, "junit: 全部跳过"
            return (fails == 0), f"junit: {tests} tests, {fails} failed, {skipped} skipped"
        if parser == "coverage":
            data = json.loads(path.read_text(encoding="utf-8"))
            pct = float(data.get("totals", {}).get("percent_covered", -1))
            floor = float(cfg.get("thresholds", {}).get("coverage_min", 0))
            return (pct >= floor), f"coverage: {pct:.1f}% (floor {floor})"
        if parser == "crap":
            arr = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(arr, list) or not arr:
                return False, "crap: 空数组或无覆盖样本"
            worst = max(float(x.get("crap", 0)) for x in arr)
            cap = float(cfg.get("thresholds", {}).get("crap_max", 1e9))
            return (worst <= cap), f"crap: worst={worst} (cap {cap})"
        if parser == "mutation":
            data = json.loads(path.read_text(encoding="utf-8"))
            if "kill_score" in data:
                score = float(data["kill_score"])
                note = f"mutation: kill_score={score}"
            else:
                mutants = data.get("mutants", [])
                if not mutants:
                    return False, "mutation: 零可评估样本"
                killed = sum(1 for m in mutants if m.get("status") in ("killed", "Killed"))
                score = killed / len(mutants)  # ignored/unknown 一律不算 killed
                note = f"mutation: {killed}/{len(mutants)} killed"
            floor = float(cfg.get("thresholds", {}).get("mutation_min", 0))
            return (score >= floor), f"{note} (floor {floor})"
        return False, f"unknown parser: {parser}"
    except Exception as e:  # noqa: BLE001
        return False, f"report parse error: {e}"


# ---------------------------------------------------------------- 各命令

def cmd_init(root: Path, args) -> None:
    bob = root / BOB_DIR
    cfg_path = bob / "config.json"
    if cfg_path.exists() and not args.force:
        print(f"already initialized: {cfg_path} （--force 覆盖）")
    else:
        checks, probes = detect_project(root)
        write_json(cfg_path, {
            "version": 1,
            "created": TS,
            "thresholds": {"coverage_min": 80, "crap_max": 30, "mutation_min": 0.8},
            "timeout_sec": 900,
            "source_exts": sorted(DEFAULT_EXTS),
            "required_checks": [c["name"] for c in checks if c.get("required")],
            "checks": checks,
            "probes": probes,
        })
        print(f"config written: {cfg_path}")

    # 把引擎自身复制进仓库（自包含，skill 卸载后照常工作）
    tools = root / "tools"
    tools.mkdir(exist_ok=True)
    me = Path(__file__).resolve()
    dst = tools / "bobflow.py"
    if me != dst.resolve():
        shutil.copy2(me, dst)
        print(f"engine installed: {dst}")

    # git 门禁
    hooks = bob / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    py_lit = sys.executable.replace("\\", "/")
    for name in ("pre-commit", "pre-push"):
        hp = hooks / name
        hp.write_text(hook_body(name, py_lit), encoding="utf-8", newline="\n")
        try:
            os.chmod(hp, 0o755)
        except Exception:
            pass
    (root / DOC_DIR).mkdir(parents=True, exist_ok=True)
    (root / WAIVER_DIR).mkdir(parents=True, exist_ok=True)
    for sub in ("reports", "evidence", "handoffs", "approvals"):
        (bob / sub).mkdir(parents=True, exist_ok=True)

    gate = "未安装（非 git 仓库）"
    rc, _, _, _ = sh("git rev-parse --is-inside-work-tree", root, 30)
    if rc == 0:
        sh("git config core.hooksPath .bob/hooks", root, 30)
        rc3, val, _, _ = sh("git config core.hooksPath", root, 30)
        gate = f"core.hooksPath = {val.strip()}" if rc3 == 0 else "读取失败"
    print(f"git gate: {gate}")

    print("\n== gates-report ==")
    cfg = read_json(cfg_path)
    for c in cfg.get("checks", []):
        state = "ON " if c.get("enabled", True) else "OFF"
        print(f"  [{state}] {c['name']:<12} stage={c.get('profile','commit')} "
              f"required={c.get('required', False)} parser={c.get('parser','exitcode')}")
    print("  软约束残留：完全不触发本流程的直接改码无法物理拦截；有远程仓库时建议加分支保护。")
    print("\n下一步：python tools/bobflow.py spec")


def detect_project(root: Path):
    """探测语言与工具链，生成默认检查表。探不到的用占位（enabled=false）。"""
    checks, probes = [], {}
    py = sys.executable.replace("\\", "/")
    q = lambda s: '"' + s + '"'  # noqa: E731

    has_py = any((root / f).exists() for f in
                 ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt")) \
        or any(root.glob("tests/**/*.py")) or any(root.glob("**/*.py"))
    has_node = (root / "package.json").exists()

    if has_py:
        rc, _, _, _ = sh(f"{q(py)} -c \"import pytest\"", root, 60)
        probes["pytest"] = (rc == 0)
        if rc == 0:
            checks.append({
                "name": "test", "profile": "commit", "required": True,
                "parser": "junit", "report": ".bob/reports/junit.xml", "enabled": True,
                "cmd": f"{q(py)} -m pytest -q --junitxml=.bob/reports/junit.xml",
            })
        else:
            checks.append({
                "name": "test", "profile": "commit", "required": True,
                "parser": "exitcode", "enabled": True,
                "cmd": f"{q(py)} tools/bobflow.py unittests --start tests",
            })
        rc, _, _, _ = sh(f"{q(py)} -c \"import coverage\"", root, 60)
        probes["coverage"] = (rc == 0)
        checks.append({
            "name": "coverage", "profile": "push", "required": True,
            "parser": "coverage", "report": ".bob/reports/coverage.json",
            "enabled": rc == 0,
            "cmd": f"{q(py)} -m coverage run -m pytest -q && "
                   f"{q(py)} -m coverage json -o .bob/reports/coverage.json",
            "placeholder": "pip install coverage 后把 enabled 改为 true",
        })
        rc, _, _, _ = sh(f"{q(py)} -c \"import radon\"", root, 60)
        probes["radon"] = (rc == 0)
        checks.append({
            "name": "crap", "profile": "push", "required": False,
            "parser": "crap", "report": ".bob/reports/crap.json",
            "enabled": False,
            "cmd": "radon cc -j . > .bob/reports/radon.json  # 再按 references/quality.md "
                   "的 crap 契约生成 crap.json（复杂度 + 逐函数覆盖）",
            "placeholder": "pip install radon 后接好转换命令并启用",
        })
        checks.append({
            "name": "mutation", "profile": "push", "required": False,
            "parser": "mutation", "report": ".bob/reports/mutation.json",
            "enabled": False,
            "cmd": "mutmut run --paths-to-mutate=.  # 或 stryker；结果转成 "
                   ".bob/reports/mutation.json（mutants[].status），ignored/unknown 不算 killed",
            "placeholder": "安装 mutmut/stryker 后接好命令并启用；这是防假测试的核心检查",
        })
    if has_node:
        pkg = read_json(root / "package.json", {}) or {}
        scripts = pkg.get("scripts", {})
        probes["npm_test"] = "test" in scripts
        if "test" in scripts:
            checks.append({
                "name": "test", "profile": "commit", "required": True,
                "parser": "exitcode", "enabled": True, "cmd": "npm test --silent",
            })
        checks.append({
            "name": "mutation", "profile": "push", "required": False,
            "parser": "mutation", "report": ".bob/reports/mutation.json",
            "enabled": False,
            "cmd": "npx stryker run  # 报告转成 .bob/reports/mutation.json",
            "placeholder": "安装 @stryker-mutator/core 后启用",
        })
    if not checks:
        checks.append({
            "name": "smoke", "profile": "commit", "required": True,
            "parser": "exitcode", "enabled": True,
            "cmd": "python -c \"print('把这条换成你项目的真实测试命令')\"",
            "placeholder": "未识别出已知工具链，请把 cmd 换成真实测试命令",
        })
    return checks, probes


def cmd_spec(root: Path, args) -> None:
    d = root / DOC_DIR
    d.mkdir(parents=True, exist_ok=True)
    templates = {
        "spec.md": SPEC_MD,
        "acceptance.feature": ACCEPTANCE,
        "qa-plan.md": QA_PLAN,
    }
    for name, body in templates.items():
        p = d / name
        if p.exists() and not args.force:
            print(f"keep: {p}")
        else:
            p.write_text(body, encoding="utf-8", newline="\n")
            print(f"written: {p}")
    print("\n下一步：把三份规格写完（编号/示例/边界/错误行为/排除项），"
          "交用户审阅确认后运行 python tools/bobflow.py approve")


def cmd_approve(root: Path, args) -> None:
    files = spec_files(root)
    profile = getattr(args, "profile", "push")
    must = files if profile == "push" else files[:1]   # 小改动只强制 spec.md
    missing = [p for p in must if not p.exists()]
    if missing:
        die(f"BLOCKED: missing spec — {', '.join(map(str, missing))} 不存在，先运行 spec 并填写"
            f"（小改动用 approve --profile commit）", EXIT_BLOCKED)
    by = (args.by or os.environ.get("USER") or os.environ.get("USERNAME") or "agent").strip()
    note = (args.note or "").strip()
    # 规格意图确认。允许 agent 代签（用户不在线时保持全自动），但如实标注谁签的。
    # 交付质量不靠这道，靠独立 QA 签字（qa-sign）。
    human = not any(b in (by + note).lower() for b in
                    ("agent", "代签", "代拟", "机器", "bot", "自动", "模型", "ai", "子代理"))
    rec = {"ts": TS, "approved_by": by, "signer": "human" if human else "agent-unsigned",
           "note": note, "profile": profile, "spec": spec_hashes(root)}
    for a in approvals(root):            # 重新确认只留最新一条，避免旧指纹误判 stale
        try:
            a.unlink()
        except OSError:
            pass
    write_json(root / BOB_DIR / "approvals" / f"spec-{TS}.json", rec)
    print(f"approved: 规格意图已记录（{rec['approved_by']}，{rec['signer']}）")
    if not human:
        print("注意：本次为 agent 代签的无人签字版，规格意图未经理人确认，交付记录会如实标注。")
    print("下一步：实现。交付前还需独立 QA 验证签字（qa-sign）。")


def cmd_qa_sign(root: Path, args) -> None:
    """独立 QA 验证签字。实现者不得拿它给自己放行，应由干净上下文的子代理执行。"""
    cfg = load_cfg(root)
    ev = latest_evidence(root)
    if not ev:
        die("BLOCKED: 证据缺失 — 先跑 python tools/bobflow.py verify，再由独立 QA 签发",
            EXIT_BLOCKED)
    if ev["fingerprint_before"]["digest"] != ev["fingerprint_after"]["digest"]:
        die("BLOCKED: 检查过程改过源码，证据作废 — 重新 verify 再签", EXIT_BLOCKED)
    now = fingerprint(root, cfg)
    if now["digest"] != ev["fingerprint_after"]["digest"]:
        die("BLOCKED: evidence stale — 代码在 verify 后又变，重新 verify 再签", EXIT_BLOCKED)
    active = [c for c in cfg.get("checks", []) if c.get("enabled", True)]
    scope = ev.get("profile", "push")
    req = [c["name"] for c in active if c.get("required")
           and (scope == "push" or c.get("profile", "commit") == "commit")]
    names = {r["name"]: r for r in ev.get("checks", [])}
    bad = [n for n in req if n not in names or not names[n].get("ok")]
    if bad:
        die(f"FAIL: required checks 未通过 — {', '.join(bad)}。QA 不给未过的检查签发。",
            EXIT_FAIL)
    by = (args.by or "").strip() or "qa-subagent"
    role = (args.role or "qa-subagent").strip()
    note = (args.note or "").strip()
    rec = {"ts": TS, "qa": by, "role": role, "note": note,
           "evidence_ts": ev.get("ts"), "fingerprint": now["digest"],
           "independent": role != "self"}
    write_json(root / BOB_DIR / "approvals" / f"qa-{TS}.json", rec)
    tag = "独立 QA" if rec["independent"] else "降级自验（实现者自签，非独立）"
    print(f"qa-sign: 已签发（{tag}，by={by}，evidence={ev.get('ts')}）")
    if not rec["independent"]:
        print("注意：这是实现者自签，不是独立 QA。有条件时应由干净上下文的子代理重新验收签发。")
    print("下一步：python tools/bobflow.py verify（或 decide）拿最终 PASS 后交付。")


def cmd_verify(root: Path, args) -> None:
    cfg = load_cfg(root)
    profile = args.profile
    picks = [c for c in cfg.get("checks", [])
             if c.get("enabled", True) and (profile == "push" or c.get("profile", "commit") == "commit")]
    if not picks:
        die("BLOCKED: config 中没有可用检查项", EXIT_BLOCKED)

    ev_dir = root / BOB_DIR / "evidence" / f"{TS}-{profile}"
    ev_dir.mkdir(parents=True, exist_ok=True)
    (root / BOB_DIR / "reports").mkdir(parents=True, exist_ok=True)

    before = fingerprint(root, cfg)
    results = []
    print(f"== verify ({profile}) ==", flush=True)
    for c in picks:
        # 每条检查先报一句再跑，避免长命令看起来像卡死
        print(f"  [RUN ] {c['name']:<10} {c['cmd'][:72]}", flush=True)
        rc, out, err, secs = sh(c["cmd"], root, int(cfg.get("timeout_sec", 900)))
        (ev_dir / f"{c['name']}.log").write_text(
            f"$ {c['cmd']}\n[exit {rc} in {secs}s]\n\n--- stdout ---\n{out}\n--- stderr ---\n{err}",
            encoding="utf-8")
        report_ok, note = (True, "exit code only")
        if c.get("report"):
            report_ok, note = validate_report(c.get("parser", "exitcode"),
                                              root / c["report"], cfg)
        ok = (rc == 0) and report_ok
        results.append({"name": c["name"], "cmd": c["cmd"], "exit_code": rc,
                        "seconds": secs, "report": c.get("report"),
                        "report_ok": report_ok, "note": note, "ok": ok})
        print(f"  [{'PASS' if ok else 'FAIL'}] {c['name']:<10} {note} "
              f"({secs}s)", flush=True)
    after = fingerprint(root, cfg)

    ev = {"ts": TS, "profile": profile,
          "fingerprint_before": before, "fingerprint_after": after,
          "checks": results}
    write_json(ev_dir / "evidence.json", ev)

    if before["digest"] != after["digest"]:
        die("BLOCKED: source changed during checks — 检查过程修改了产品源码，本轮报告作废。"
            "把改动独立提交后重新 verify。", EXIT_BLOCKED)
    code, msg = decide(root, cfg, ev)
    die(msg, code)


def decide(root: Path, cfg: dict, ev: dict):
    msgs = []
    # 1. 配置自检（只考启用且必检的项；禁用的必检项记录在案并在 PASS 信息里提醒）
    active = [c for c in cfg.get("checks", []) if c.get("enabled", True)]
    all_req = [c for c in active if c.get("required")]
    dormant = [c["name"] for c in cfg.get("checks", [])
               if c.get("required") and not c.get("enabled", True)]
    if not all_req:
        return EXIT_FAIL, "FAIL: config 的 required_checks 为空，无法裁决"
    # 2. 规格签字
    cur = spec_hashes(root)
    apps = approvals(root)
    if not apps:
        return EXIT_BLOCKED, "BLOCKED: 规格未确认 — 运行 approve（用户不在线可由 agent 代签并标注）"
    latest = read_json(apps[-1], {}) or {}
    ap = latest.get("profile", "push")
    need = ["docs/bob/spec.md"]
    if ap == "push":
        need += ["docs/bob/acceptance.feature", "docs/bob/qa-plan.md"]
    if any(k not in cur for k in need):
        return EXIT_BLOCKED, f"BLOCKED: missing spec — 缺 {', '.join(k for k in need if k not in cur)}"
    if latest.get("spec") != {k: cur[k] for k in need}:
        return EXIT_BLOCKED, "BLOCKED: spec stale — 规格改动后重新 approve 确认意图"
    # 3. 证据时效
    if ev is None:
        ev = latest_evidence(root)
    if not ev:
        return EXIT_BLOCKED, "BLOCKED: evidence missing — 运行 python tools/bobflow.py verify"
    if ev["fingerprint_before"]["digest"] != ev["fingerprint_after"]["digest"]:
        return EXIT_BLOCKED, "BLOCKED: source changed during checks，报告作废"
    now = fingerprint(root, cfg)
    if now["digest"] != ev["fingerprint_after"]["digest"]:
        return EXIT_BLOCKED, "BLOCKED: evidence stale — 检查后源码又有改动，重新 verify"
    # 4. 检查通过性。必检范围按本次 profile：commit 只考快检，push 考全部（快检+慢检）
    scope = ev.get("profile", "push")
    req = [c["name"] for c in all_req
           if scope == "push" or c.get("profile", "commit") == "commit"]
    names = {r["name"]: r for r in ev.get("checks", [])}
    bad = [n for n in req if n not in names or not names[n].get("ok")]
    if bad:
        return EXIT_FAIL, f"FAIL: required checks 未通过 — {', '.join(bad)}（禁止改门槛凑绿，见 SKILL.md 硬规则）"
    # 4.5 独立 QA 验证签字：交付前必须有，实现者不能自签放行
    qa = qa_signs(root)
    if not qa:
        return EXIT_BLOCKED, ("BLOCKED: 缺独立 QA 签字 — 开一个干净上下文的子代理扮演 QA，"
                              "从公开入口独立核对验收、跑一次 verify，再用 qa-sign 签发。"
                              "写代码的不能给自己放行。")
    last_qa = read_json(qa[-1], {}) or {}
    if last_qa.get("fingerprint") != ev["fingerprint_after"]["digest"]:
        return EXIT_BLOCKED, "BLOCKED: QA 签字过期 — QA 签发后代码有改动，重跑独立 QA 并重新 qa-sign"
    # 5. 反作弊基线差分
    stats = test_stats(root, cfg)
    base = read_json(root / BOB_DIR / "baseline.json")
    if base:
        if stats["tests"] < base.get("tests", 0):
            msgs.append(f"断言数 {base['tests']} -> {stats['tests']} 减少")
        if stats["skips"] > base.get("skips", 0):
            msgs.append(f"skip 数 {base['skips']} -> {stats['skips']} 增加")
        if base.get("thresholds") != cfg.get("thresholds"):
            msgs.append("门槛值被修改（thresholds 变化）")
        if msgs:
            ok_waiver = False
            wd = root / WAIVER_DIR
            if wd.is_dir():
                # 只认用户批准的豁免（APPROVED-*），自动生成的 REQUESTED-* 不算数
                wavs = [w for w in wd.glob("*.md") if not w.name.startswith("REQUESTED-")]
                ok_waiver = any(w.stat().st_mtime >= base.get("ts_epoch", 0) for w in wavs)
            if not ok_waiver:
                stub = wd / f"REQUESTED-{TS}.md"
                stub.parent.mkdir(parents=True, exist_ok=True)
                stub.write_text(WAIVER_STUB.format(reasons="\n".join("- " + m for m in msgs)),
                                encoding="utf-8", newline="\n")
                return EXIT_WAIVER, (f"WAIVER: {'; '.join(msgs)} — "
                                     f"填写 {stub} 说明理由，交用户批准后重跑 verify")
    # 6. 通过：落决策与新基线
    write_json(root / BOB_DIR / "baseline.json",
               {**stats, "thresholds": cfg.get("thresholds"),
                "ts": TS, "ts_epoch": time.time()})
    decision = {"verdict": "PASS", "ts": TS, "profile": ev.get("profile"),
                "spec": cur, "evidence_ts": ev.get("ts"),
                "fingerprint": now["digest"],
                "qa_sign": last_qa,
                "checks": {r["name"]: r["note"] for r in ev.get("checks", [])}}
    write_json(root / BOB_DIR / "decision.json", decision)
    warn = f"；注意禁用的必检项：{', '.join(dormant)}，交付前应启用" if dormant else ""
    return EXIT_PASS, (f"PASS: decision.json 已更新（{len(ev.get('checks', []))} 项检查，"
                       f"断言 {stats['tests']} / skip {stats['skips']}）。可以交付。{warn}")


def cmd_decide(root: Path, args) -> None:
    cfg = load_cfg(root)
    code, msg = decide(root, cfg, None)
    die(msg, code)


def cmd_checkpoint(root: Path, args) -> None:
    cfg = load_cfg(root)
    fp = fingerprint(root, cfg)
    decision = read_json(root / BOB_DIR / "decision.json", {}) or {}
    ev = latest_evidence(root) or {}
    phase = args.phase or "unspecified"
    hd = root / BOB_DIR / "handoffs"
    hd.mkdir(parents=True, exist_ok=True)
    body = HANDOFF.format(
        phase=phase, ts=TS, fp=fp["digest"], files=fp["files"],
        ids="、".join(sorted(spec_hashes(root))) or "-",
        verdict=decision.get("verdict", "尚无 decision"),
        checks=json.dumps({r["name"]: r.get("note", "") for r in ev.get("checks", [])},
                          ensure_ascii=False) or "-",
        known="(待补：遗留问题、风险、未做的事)",
        expect="(待补：下个阶段应关注什么)",
    )
    p = hd / f"{phase}-{TS}.md"
    p.write_text(body, encoding="utf-8", newline="\n")
    print(f"handoff written: {p}")
    print("请补齐 known/expect 两节后继续。下一阶段从该交接记录重建事实。")


def cmd_next(root: Path, args) -> None:
    if not (root / BOB_DIR / "config.json").exists():
        print("当前阶段: 未初始化\n下一步: python tools/bobflow.py init")
        return
    files = spec_files(root)
    if not files[0].exists():
        print("当前阶段: spec\n下一步: python tools/bobflow.py spec 然后填写规格（小改动只需 spec.md）")
        return
    cur = spec_hashes(root)
    apps = approvals(root)
    if not apps:
        print("当前阶段: spec 审批\n下一步: 交用户确认规格后 python tools/bobflow.py approve"
              "（小改动加 --profile commit）")
        return
    ap = (read_json(apps[-1], {}) or {}).get("profile", "push")
    need = ["docs/bob/spec.md"]
    if ap == "push":
        need += ["docs/bob/acceptance.feature", "docs/bob/qa-plan.md"]
    if any(k not in cur for k in need) or (read_json(apps[-1], {}) or {}).get("spec") != {k: cur[k] for k in need}:
        print("当前阶段: spec 审批\n下一步: 补齐/确认规格后重新 approve")
        return
    decision = read_json(root / BOB_DIR / "decision.json", {}) or {}
    ev = latest_evidence(root)
    now = fingerprint(root, load_cfg(root))
    if not ev or ev.get("fingerprint_after", {}).get("digest") != now["digest"]:
        print("当前阶段: 实现/修复\n下一步: 完成后 python tools/bobflow.py verify")
        return
    qa = qa_signs(root)
    if not qa or (read_json(qa[-1], {}) or {}).get("fingerprint") != now["digest"]:
        print("当前阶段: 待独立 QA\n下一步: 开一个干净上下文子代理扮演 QA，从公开入口独立验收、\n"
              "跑 verify 后用 python tools/bobflow.py qa-sign 签发（实现者不得自签）")
        return
    if decision.get("verdict") == "PASS":
        print("当前阶段: 可交付\n下一步: python tools/bobflow.py checkpoint <阶段> 然后 commit/push")
    else:
        print("当前阶段: 待裁决\n下一步: python tools/bobflow.py decide")


def cmd_unittests(root: Path, args) -> None:
    """无 pytest 时的标准库测试入口：discover + 运行，零用例也算失败。"""
    import unittest
    start = args.start if (root / args.start).is_dir() else "."
    sys.path.insert(0, str(root))
    suite = unittest.defaultTestLoader.discover(start)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    ok = result.wasSuccessful() and result.testsRun > 0
    print(f"unittests: ran={result.testsRun} fail={len(result.failures)} "
          f"err={len(result.errors)} skipped={len(result.skipped)}")
    sys.exit(0 if ok else 1)


def cmd_hook(root: Path, args) -> None:
    stage = args.stage
    print(f"\n[bobflow gate] {stage}: 证据裁决中（这不是可跳过的提示，是交付门禁）")
    args.profile = "commit" if stage == "pre-commit" else "push"
    cmd_verify(root, args)


# ---------------------------------------------------------------- 骨架文本

SPEC_MD = """# 规格切片（spec）

> 写完交用户审阅。编号从 S1 递增；实现只允许覆盖已签字的条目。

## S1 <一句话说清要什么>

- 原始要求：<用户原话或需求编号>
- 示例：<输入 → 期望输出>
- 边界：<空值/极值/并发/编码等要考虑的边缘>
- 错误行为：<出错时的可观察表现，含退出码/提示文案>
- 明确排除项：<本切片不做什么，防止范围蔓延>
- 兼容条件：<已有行为/接口/数据格式哪些必须保持>
- 假设：<可推断就记录并推进的假设；会改变用户目的的选择才去问>
"""

ACCEPTANCE = """# language: zh-CN
# 验收（Gherkin）。Then 必须是可观察断言：真实 DOM 变化、输出内容、退出码、返回值。
# 禁止"点击后没有抛异常"式验收。每条验收覆盖适用的正常/边界/异常案例。

功能: <与 spec 编号对应>

  场景: S1 正常路径
    假如 <前置状态>
    当 <用户入口的真实操作>
    那么 <可观察断言，引用 S1 的期望输出>

  场景: S1 边界
    假如 <边界前置>
    当 <操作>
    那么 <边界下的可观察断言>

  场景: S1 错误
    假如 <出错前置>
    当 <操作>
    那么 <错误行为的可观察断言，引用 S1 的错误行为>
"""

QA_PLAN = """# QA 计划（qa-plan）

> 从用户入口描述操作。Web 查真实 DOM/显示结果；CLI 查输入、输出、退出码；
> 库代码查公开接口。直接调后端接口只能补充证据，不能替代 UI 验收。

| 编号 | 对应用例 | 前置条件 | 用户入口操作 | 预期结果 | 恢复步骤 |
| --- | --- | --- | --- | --- | --- |
| Q1 | S1 | | | | |

复用要求：QA 的操作序列要落成可执行脚本，保留在仓库里，后续每次交付直接重跑。
"""

HANDOFF = """# 交接记录：{phase}

- 时间：{ts}
- 源码指纹：{fp}（{files} 个源文件）
- 覆盖需求：{ids}
- 裁决：{verdict}
- 检查证据：{checks}

## 已知问题

{known}

## 期望接收方关注

{expect}
"""

WAIVER_STUB = """# 豁免申请（需用户批准）

## 命中原因

{reasons}

## 理由说明

<为什么这些变化是正当的：例如删掉的是重复断言、skip 的是环境不适用用例、
门槛调整有新的校准依据。禁止只为变绿申请豁免。>

## 影响范围与补偿措施

<影响哪些验收；用什么补偿：新增了哪些等价断言/替代检查。>

---
用户批准后，把本文件重命名为 `APPROVED-<日期>-<简述>.md`；未改名的 REQUESTED 文件不会被裁决认可。
"""


def main() -> None:
    ap = argparse.ArgumentParser(prog="bobflow", description="证据驱动工程流程引擎")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="初始化：探测工具链、安装引擎与 git 门禁")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("spec", help="生成规格三件套骨架")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_spec)

    p = sub.add_parser("approve", help="记录规格意图确认（用户不在可 agent 代签并标注）")
    p.add_argument("--by", default="")
    p.add_argument("--note", default="")
    p.add_argument("--profile", choices=["commit", "push"], default="push",
                   help="commit=小改动只强制 spec.md；push=三件套齐全（默认）")
    p.set_defaults(func=cmd_approve)

    p = sub.add_parser("qa-sign", help="独立 QA 验证签字（实现者不得自签放行）")
    p.add_argument("--by", default="")
    p.add_argument("--role", default="qa-subagent")
    p.add_argument("--note", default="")
    p.set_defaults(func=cmd_qa_sign)

    p = sub.add_parser("verify", help="跑检查并裁决")
    p.add_argument("--profile", choices=["commit", "push"], default="push")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("decide", help="只对最新证据重新裁决")
    p.set_defaults(func=cmd_decide)

    p = sub.add_parser("checkpoint", help="落盘阶段交接记录")
    p.add_argument("phase", nargs="?", default="")
    p.set_defaults(func=cmd_checkpoint)

    p = sub.add_parser("next", help="查看当前阶段与下一步命令")
    p.set_defaults(func=cmd_next)

    p = sub.add_parser("unittests", help="无 pytest 时的内置测试跑法（被检查表引用）")
    p.add_argument("--start", default="tests")
    p.set_defaults(func=cmd_unittests)

    p = sub.add_parser("hook", help="git 门禁入口（由 hooks 调用）")
    p.add_argument("stage", choices=["pre-commit", "pre-push"])
    p.set_defaults(func=cmd_hook)

    args = ap.parse_args()
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args.func(find_root(), args)


if __name__ == "__main__":
    main()
