[简体中文](README.md) | English

# Agent_Extensions

> **📦 DSH plugins have been split into standalone repositories** — the plugins under `dsh-plugins/` in this repo have been moved to their own GitHub repos; install from those directly:
>
> | Plugin | Standalone repo |
> |---|---|
> | dsh-vision-skill | https://github.com/DDDFXYqiming/dsh-vision-skill |
> | dsh-layered-memory | https://github.com/DDDFXYqiming/dsh-layered-memory |
> | dsh-annotation-patched | https://github.com/DDDFXYqiming/dsh-annotation-patched |
> | dsh-side-panel-patched | https://github.com/DDDFXYqiming/dsh-side-panel-patched |
> | dsh-ocr1-memory | https://github.com/DDDFXYqiming/dsh-ocr1-memory |
>
> This repo **no longer maintains dsh plugins**; only the historical snapshot + notes remain. New development happens in the standalone repos.

DSH-native plugins (zero framework patches) + cross-framework general Skills + Hermes plugins, all self-contained (scripts / templates / docs live inside each item), clone-and-use.

## Contents

### 1️⃣ DSH native plugins (`dsh-plugins/`, historical snapshot)

| Plugin | One-liner | Detail |
|---|---|---|
| `dsh-vision-skill` v0.4.4 | 8-tool image recognition (with progressive-exposure activation + credential indirection + path sandboxing) | [README](dsh-plugins/dsh-vision-skill/) |
| `dsh-layered-memory` v0.4 | Cross-session long-term memory: namespace isolation + L1 index injection + auto-distill candidates + provenance / archive / rollback + auto-maintenance | [README](dsh-plugins/dsh-layered-memory/) |
| `dsh-annotation-patched` | Select-to-quote plugin (fork enhancement: Codex-style "引用" button + ghost-quote fix) | [README](dsh-plugins/dsh-annotation-patched/) |
| `dsh-side-panel-patched` | Right-side workspace panel (fork enhancement: bypass 520px cap + multi-file tabs + session tracking) | [README](dsh-plugins/dsh-side-panel-patched/) |
| `dsh-ocr1-memory` v0.1.0 | Optical-compression memory: text → SoM images, age decay, active recall | [README](dsh-plugins/dsh-ocr1-memory/) |

### 2️⃣ General skills (`General_skills/`) — framework-agnostic

Any agent framework (Claude Code / Codex / opencode / DSH / Hermes, etc.) can mount these as Skills.

| Skill | One-liner | Dependency |
|---|---|---|
| `vision-skill` | Image recognition: local image → vision model description (Qwen dynamic resolution, OpenAI-compatible) | Python 3 + vision model API key |
| `video-notes-generator` | Video URL → structured Markdown notes (timestamps / extracted frames / multimodal observations / AI summary); Bilibili / YouTube / Douyin / Kuaishou | Python 3 + see `scripts/install_deps.sh` |
| `ppt-master` | Source document → SVG pages → PPTX | Python 3 (stdlib-first) |
| `markitdown-skill` | PDF / DOCX / PPTX / XLSX / HTML / EPUB → Markdown | Python 3 + `pip install -r requirements.txt` |
| `generic-agent-code-run` | Windows desktop / real-browser automation (Win32 / UIA / OCR / screenshot / CDP) | Python 3 + matching libs |

> Every skill ships a `SKILL.md` (loaded at runtime by the agent). Some also ship `scripts/`, `templates/`, `references/`.

### 3️⃣ Hermes plugins (`hermes_plugins/`)

| Plugin | One-liner | Dependency |
|---|---|---|
| [`language-router`](hermes_plugins/language-router/) v5.0 | Adaptive language routing: Planner-first → Worker → optional Verifier → Digest (hooks: `pre_llm_call`, etc.) | Hermes framework |

## Directory layout

```
Agent_Extensions/
├── dsh-plugins/               # DSH native plugins (historical snapshot — see top-of-README migration table)
├── General_skills/            # General skills (framework-agnostic, mount-and-go)
│   ├── vision-skill/
│   ├── video-notes-generator/
│   ├── ppt-master/
│   ├── markitdown-skill/
│   └── generic-agent-code-run/
├── hermes_plugins/            # Hermes framework plugins
│   └── language-router/
└── README.md
```

## 🚀 Quick start

### Method 1: install a DSH plugin (install the standalone repo directly)

```bash
# Using dsh-vision-skill as an example
dsh plugin --profile web add github:DDDFXYqiming/dsh-vision-skill

# Configure the credential in $DSH_HOME/.credentials.yaml
VISION_API_KEY: sk-xxxx
```

> ⚠️ After bundle install, **do not** add another `insert: - id: <name>` entry for the same plugin in your profile's `cordis.patch.yml` — duplicate ids trigger a `duplicate loader entry id` startup crash. To customize config, override the entry by id (without `insert:`); see each plugin's README.

### Method 2: mount a general skill (any framework)

Using `vision-skill` as an example:

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

Other skills: see each directory's `SKILL.md`.

### Method 3: install a Hermes plugin

Drop the `hermes_plugins/language-router` directory into your Hermes plugin path (`plugin.yaml` declares every hook and version).

## ⚙️ Requirements

| Use case | Requirement |
|---|---|
| DSH plugins | Node.js + DSH (`@deepseek-ai/dsh-tools`, `@deepseek-ai/dsh-credentials`) |
| dsh-vision-skill / vision-skill | additionally Python 3 + Pillow, and an **OpenAI-compatible multimodal model** API key (Qwen-VL / MiniMax-M3 / Gemini / GPT-4o; default MiniMax-M3) |
| General skills (vision / video / ppt / markitdown / automation) | Python 3.x + each skill's listed pip dependencies |
| Hermes plugins | Hermes framework |

## ❓ FAQ

**Q: general skill vs DSH plugin — which should I pick?**
A: General skills work across frameworks; DSH plugins use official seams and are more capable but DSH-only. They interoperate — `dsh-vision-skill` is the DSH-native wrapper around `General_skills/vision-skill`.

**Q: my model doesn't support images — can it still do image recognition?**
A: Yes. ① send a local path string of the image; ② take a screenshot, say "看图", and `vision_clipboard` saves it to the workspace and recognizes it automatically. This is a pure-text-model capability gate, not a plugin bug.

**Q: which vision API should I use?**
A: Any OpenAI-compatible multimodal endpoint, injected via `VISION_API_URL` / `VISION_MODEL` / `VISION_API_KEY`. No vendor lock-in.

**Q: are sub-directories interdependent?**
A: No. Each sub-directory is a **self-contained unit** — install, publish, or delete any one independently.

## 🤝 Contributing

- Each sub-directory is an independent self-contained unit; **PRs** for new skills / plugins and **Issues** for bug reports are both welcome
- Contribution requirements: self-contained (ship own scripts / templates / docs), clear license (MIT recommended), no hard-coded keys or absolute local paths
- New skills go in as `SKILL.md`; new DSH plugins additionally ship `cordis.patch.yml` + `package.json`

## 📄 License

Everything in this repo is released under the **MIT License**. Community-sourced material keeps its original author attribution (see each sub-directory's `SKILL.md` / `plugin.yaml` header).
