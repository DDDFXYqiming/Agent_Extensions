[简体中文](README.md) | English

# Agent_Extensions

This repo collects three kinds of things. DSH-native plugins built for [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness), going through the official extension seams with zero framework patches. General Skills that bind to no framework, and Hermes plugins for the Hermes framework. Every item is self-contained. Scripts, templates and docs live inside each directory, so once the repo is cloned you can lift any single directory out and use it on its own.

> **📦 DSH plugins have been split into standalone repositories.** The plugins under `dsh-plugins/` in this repo have moved to their own GitHub repos; install from those directly.
>
> | Plugin | Standalone repo |
> |---|---|
> | dsh-vision-skill | https://github.com/DDDFXYqiming/dsh-vision-skill |
> | dsh-layered-memory | https://github.com/DDDFXYqiming/dsh-layered-memory |
> | dsh-annotation-patched | https://github.com/DDDFXYqiming/dsh-annotation-patched |
> | dsh-side-panel-patched | https://github.com/DDDFXYqiming/dsh-side-panel-patched |
> | dsh-ocr1-memory | https://github.com/DDDFXYqiming/dsh-ocr1-memory |
>
> This repo **no longer maintains dsh plugins**. `dsh-plugins/` remains only as a historical snapshot plus notes. Follow the standalone repos for future updates.

## Contents

### 1️⃣ DSH native plugins (`dsh-plugins/`, historical snapshot)

This group is kept for the record only. For daily use, install the standalone repos listed above. What each plugin does is in the table below.

| Plugin | One-liner | Detail |
|---|---|---|
| `dsh-vision-skill` v0.4.4 | 8-tool image recognition (with progressive-exposure activation + credential indirection + path sandboxing) | [README](dsh-plugins/dsh-vision-skill/) |
| `dsh-layered-memory` v0.4 | Cross-session long-term memory (namespace isolation + L1 index injection + auto-distill candidates + provenance / archive / rollback + auto-maintenance) | [README](dsh-plugins/dsh-layered-memory/) |
| `dsh-annotation-patched` | Select-to-quote plugin (fork enhancement, Codex-style "引用" button + ghost-quote fix) | [README](dsh-plugins/dsh-annotation-patched/) |
| `dsh-side-panel-patched` | Right-side workspace panel (fork enhancement, bypass 520px cap + multi-file tabs + session tracking) | [README](dsh-plugins/dsh-side-panel-patched/) |
| `dsh-ocr1-memory` v0.1.0 | Optical-compression memory (text → SoM image storage + age decay + active recall) | [README](dsh-plugins/dsh-ocr1-memory/) |

### 2️⃣ General skills (`General_skills/`, framework-agnostic)

Any agent framework (Claude Code / Codex / opencode / DSH / Hermes, etc.) can mount these directories as Skills.

| Skill | One-liner | Dependency |
|---|---|---|
| `vision-skill` | Image recognition, a local image sent to a vision model for description (Qwen dynamic resolution, OpenAI-compatible) | Python 3 + vision model API key |
| `video-notes-generator` | Video URL → structured Markdown notes (timestamps / extracted frames / multimodal observations / AI summary); supports Bilibili / YouTube / Douyin / Kuaishou | Python 3 + see `scripts/install_deps.sh` |
| `generic-agent-code-run` | Windows desktop / real-browser automation (Win32 / UIA / OCR / screenshot / CDP) | Python 3 + matching libs |

> Every skill ships a `SKILL.md` (loaded at runtime by the agent). Some also ship `scripts/`, `templates/`, `references/`.
>
> This repo only hosts skills we authored. Upstream public projects (e.g. [microsoft/markitdown](https://github.com/microsoft/markitdown), [hugohe3/ppt-master](https://github.com/hugohe3/ppt-master)) are not mirrored here — install them from upstream.

### 3️⃣ Hermes plugins (`hermes_plugins/`)

| Plugin | One-liner | Dependency |
|---|---|---|
| [`language-router`](hermes_plugins/language-router/) v5.0 | Adaptive language routing, running Planner-first → Worker → optional Verifier → Digest (hooks such as `pre_llm_call`) | Hermes framework |

## Directory layout

```
Agent_Extensions/
├── dsh-plugins/               # DSH native plugins (historical snapshot, see top-of-README migration table)
├── General_skills/            # General skills (framework-agnostic, mount-and-go)
│   ├── vision-skill/
│   ├── video-notes-generator/
│   └── generic-agent-code-run/
├── hermes_plugins/            # Hermes framework plugins
│   └── language-router/
└── README.md
```

## 🚀 Quick start

Three ways in, matching the three groups above. Pick the one for your framework.

### Method 1. Install a DSH plugin (the standalone repo directly)

```bash
# Using dsh-vision-skill as an example
dsh plugin --profile web add github:DDDFXYqiming/dsh-vision-skill

# Configure the credential in $DSH_HOME/.credentials.yaml
VISION_API_KEY: sk-xxxx
```

> ⚠️ After a bundle install, adding another `insert: - id: <name>` entry for the same plugin in your profile's `cordis.patch.yml` triggers a `duplicate loader entry id` startup crash. To customize config, override the entry by id (without `insert:`); see each plugin's README.

### Method 2. Mount a general skill (any framework)

Using `vision-skill` as an example.

```bash
# 1. Copy the skill dir into your agent's skills directory
#    (Claude Code: ~/.claude/skills/ ; Codex: ~/.codex/skills/ ; others: see their docs)
cp -r General_skills/vision-skill <your skills dir>/

# 2. Configure the vision model (OpenAI-compatible)
cd General_skills/vision-skill
cp templates/.env.example .env   # fill in VISION_API_URL / VISION_MODEL / VISION_API_KEY

# 3. Self-check
python scripts/vision.py --check
```

Other skills, see each directory's `SKILL.md`.

### Method 3. Install a Hermes plugin

Drop the `hermes_plugins/language-router` directory into your Hermes plugin path. The `plugin.yaml` inside declares every hook and the version info.

## ⚙️ Requirements

| Use case | Requirement |
|---|---|
| DSH plugins | Node.js + DSH (`@deepseek-ai/dsh-tools`, `@deepseek-ai/dsh-credentials`) |
| dsh-vision-skill / vision-skill | additionally Python 3 + Pillow, and an **OpenAI-compatible multimodal model** API key (Qwen-VL / MiniMax-M3 / Gemini / GPT-4o; default MiniMax-M3) |
| General skills (vision / video / automation) | Python 3.x + each skill's listed pip dependencies |
| Hermes plugins | Hermes framework |

## ❓ FAQ

**General skill or DSH plugin, which should I pick?**

General skills work across frameworks. DSH plugins use the official seams and are more capable, but they only run under DSH. The two interoperate. `dsh-vision-skill` is the DSH-native wrapper around `General_skills/vision-skill`.

**My model doesn't support images. Can it still do image recognition?**

Yes. One way is sending the image's local path as plain text. Another is taking a screenshot and saying “看图”, then `vision_clipboard` saves it to the workspace and recognizes it automatically. The limit comes from the capability gate of pure-text models, not from the plugin.

**Which vision API should I use?**

Any OpenAI-compatible multimodal endpoint works. Inject it through `VISION_API_URL` / `VISION_MODEL` / `VISION_API_KEY`. No vendor lock-in.

**Are sub-directories interdependent?**

No. Each sub-directory is a **self-contained unit**. Install, publish, or delete any one independently.

## 🤝 Contributing

- Each sub-directory is an independent self-contained unit. **PRs** for new skills / plugins and **Issues** for bug reports are both welcome
- Contribution requirements
  - Self-contained (ship own scripts / templates / docs)
  - Clear license (MIT recommended)
  - No hard-coded keys or absolute local paths
- New skills go in as `SKILL.md`. New DSH plugins additionally ship `cordis.patch.yml` + `package.json`

## 📄 License

Everything in this repo is released under the **MIT License**. Community-sourced material keeps its original author attribution (see each sub-directory's `SKILL.md` / `plugin.yaml` header).
