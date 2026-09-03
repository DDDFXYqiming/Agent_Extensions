[简体中文](README.md) | English

# Agent_Extensions

A collection of framework-agnostic **Agent Skills**. The repo holds two kinds of things: general skills (`General_skills/`) that any agent framework can mount as a directory, and Hermes plugins (`hermes_plugins/`) for the Hermes framework. Every entry is self-contained — scripts, templates and docs live inside its own folder, so you can take one directory and use it alone.

> **DSH plugins are not in this repo.** All DeepSeek Harness (DSH) plugins have been split into standalone repositories — install them from there:
>
> | Plugin | Standalone repository |
> |---|---|
> | dsh-vision-skill | https://github.com/DDDFXYqiming/dsh-vision-skill |
> | dsh-layered-memory | https://github.com/DDDFXYqiming/dsh-layered-memory |
> | dsh-annotation-patched | https://github.com/DDDFXYqiming/dsh-annotation-patched |
> | dsh-side-panel-patched | https://github.com/DDDFXYqiming/dsh-side-panel-patched |
> | dsh-ocr1-memory | https://github.com/DDDFXYqiming/dsh-ocr1-memory |
>
> This repo no longer carries DSH plugin sources or snapshots.

## What's inside

### 1️⃣ General skills (`General_skills/`, framework-agnostic)

Any agent framework (Claude Code / Codex / opencode / DSH / Hermes, etc.) can mount these directories as Skills.

| Skill | One-liner | Dependency |
|---|---|---|
| [`vision-skill`](General_skills/vision-skill/) | Image recognition: a local image sent to a vision model for a description (Qwen dynamic resolution, OpenAI-compatible endpoint) | Python 3 + Pillow + vision model API key |
| [`video-notes-generator`](General_skills/video-notes-generator/) | Video → structured Markdown notes (subtitles/transcription, timestamps, frame extraction, multimodal observation); supports Bilibili / YouTube / Douyin / Kuaishou / local files | Python 3 + `yt-dlp` + `ffmpeg`, see `scripts/install_deps.sh` |
| [`generic-agent-code-run`](General_skills/generic-agent-code-run/) | Windows desktop and real-browser automation (Win32 / UIA / OCR / screenshot / CDP) with an observe-act-verify loop | Python 3 + matching libs, Windows |

> Every skill ships a `SKILL.md` (instructions the agent loads at runtime), plus `scripts/`, `templates/` and `references/` where needed.
>
> This repo only hosts skills we authored. Upstream public projects (e.g. [microsoft/markitdown](https://github.com/microsoft/markitdown), [hugohe3/ppt-master](https://github.com/hugohe3/ppt-master)) are not mirrored here — install them from upstream.

### 2️⃣ Hermes plugins (`hermes_plugins/`)

| Plugin | One-liner | Dependency |
|---|---|---|
| [`language-router`](hermes_plugins/language-router/) v5.0 | Adaptive language routing, running Planner-first → Worker → optional Verifier → Digest (hooks such as `pre_llm_call`) | Hermes framework |

## Directory layout

```
Agent_Extensions/
├── General_skills/            # General skills (framework-agnostic, mount-and-go)
│   ├── vision-skill/
│   ├── video-notes-generator/
│   └── generic-agent-code-run/
├── hermes_plugins/            # Hermes framework plugins
│   └── language-router/
└── README.md
```

## 🚀 Quick start

### Mount a general skill (any framework)

Using `vision-skill` as the example.

```bash
# 1. Copy the skill directory into your agent's skills directory
#    (Claude Code: ~/.claude/skills/ ; Codex: ~/.codex/skills/ ; see your framework's docs)
cp -r General_skills/vision-skill <your skills dir>/

# 2. Configure the vision model (OpenAI-compatible endpoint)
cd General_skills/vision-skill
cp templates/.env.example .env   # fill in VISION_API_URL / VISION_MODEL / VISION_API_KEY

# 3. Self-check
python scripts/vision.py --check
```

For the other skills, see the `SKILL.md` in each directory. `video-notes-generator` also needs `yt-dlp` and `ffmpeg` on PATH.

### Install a Hermes plugin

Drop `hermes_plugins/language-router` into your Hermes plugin path. The `plugin.yaml` inside declares every hook and the version info.

### Using DSH?

DSH plugins live in their own repositories — see the install notes in each repo from the table above. The general skills in this repo can still be mounted as Skills inside DSH; for `vision-skill`, the DSH integration steps (including the framework patch) are in [General_skills/vision-skill/references/dsh-integration.md](General_skills/vision-skill/references/dsh-integration.md).

## ⚙️ Requirements

| Use case | Requirement |
|---|---|
| vision-skill | Python 3 + Pillow, and an **OpenAI-compatible multimodal model** API key (Qwen-VL / MiniMax-M3 / Gemini / GPT-4o; default MiniMax-M3) |
| video-notes-generator | Python 3 + `yt-dlp` + `ffmpeg`; subtitle-less videos transcribe locally with faster-whisper (discrete GPU auto-detected, falls back to CPU) |
| generic-agent-code-run | Windows + Python 3, plus pywin32 / Pillow / uiautomation / pyperclip as needed |
| Hermes plugins | Hermes framework |

## ❓ FAQ

**General skill or DSH plugin, which should I pick?**

General skills are cross-framework: copy the directory and mount it. DSH plugins use the official extension seams and are more capable (credential handling, progressive tool exposure, and so on) but only run under DSH, and each lives in its own repository. The two share a lineage: `dsh-vision-skill` is the DSH-native wrapper around this repo's `General_skills/vision-skill`.

**My model doesn't support images. Can it still do image recognition?**

Yes. Hand the image's local path to the skill: `vision-skill` calls the multimodal endpoint you configured, returns a text description, and you answer from that. Read the whole image first, then re-read small text and error regions with `--crop`.

**Which vision API?**

Any OpenAI-compatible multimodal endpoint, injected via `VISION_API_URL` / `VISION_MODEL` / `VISION_API_KEY`. No vendor is hardcoded.

**Are the subdirectories related?**

No. Each subdirectory is an **independent, self-contained unit** that can be used, published, or deleted on its own.

## 🤝 Contributing

- Every subdirectory is a self-contained unit. New skills are welcome as **PRs**; please file an **Issue** for problems.
- Contribution requirements
  - Self-contained content, shipping its own scripts, templates and docs
  - A clear license, MIT recommended
  - No hardcoded secrets or machine-specific absolute paths
  - The entry document is `SKILL.md`, following the [Agent Skills specification](https://agentskills.io/specification): `name` matches the directory, `description` states what it does and when to use it, and the body holds only instructions the agent acts on — human-facing docs and version history belong in `references/` and `CHANGELOG.md`
- DSH plugins should get their own repository; they do not go into this one

## 📄 License

Everything in this repo is distributed under the **MIT License**. Community-derived content keeps its original attribution (see the header of each `SKILL.md`).
