[简体中文](README.md) | English

# Agent_Extensions

> ## 📦 DSH plugins have been split into standalone repositories
>
> The DSH plugins under `dsh-plugins/` in this repository have been migrated to standalone GitHub repositories. Installing from the standalone repos is recommended:
>
> | Plugin | Standalone repo |
> |---|---|
> | dsh-vision-skill | https://github.com/DDDFXYqiming/dsh-vision-skill |
> | dsh-layered-memory | https://github.com/DDDFXYqiming/dsh-layered-memory |
> | dsh-annotation-patched | https://github.com/DDDFXYqiming/dsh-annotation-patched |
> | dsh-side-panel-patched | https://github.com/DDDFXYqiming/dsh-side-panel-patched |
> | dsh-ocr1-memory | https://github.com/DDDFXYqiming/dsh-ocr1-memory |
>
> Install example:
> ```bash
> dsh plugin --profile web add github:DDDFXYqiming/dsh-ocr1-memory
> ```
>
> This repository **no longer maintains DSH plugins**; it keeps only historical snapshots and documentation. For future updates, refer to the standalone repositories.

**A collection of DeepSeek Harness (DSH) plugins and AI Agent skills** — native plugins for [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (using official extension seams, zero framework patches) + cross-framework general skills + Hermes plugins, ready to use out of the box.

![repo](https://img.shields.io/badge/agent-skills-4B8BBE) ![dsh](https://img.shields.io/badge/deepseek--harness-plugin-7A4FBF) ![license](https://img.shields.io/badge/license-MIT-green)

This repository collects, translates, and **self-containedly packages** AI Agent skill resources, and provides extensions in standard plugin form for **DeepSeek Harness (DSH)**. Everything is **self-contained** (skills/plugins bundle their own scripts, templates, and docs, with no dependencies on files outside the repo), so a clone is all you need to get started.

## ✨ Contents at a Glance

### 1️⃣ DSH native plugins (dsh-plugins) — zero framework patches

Built on the official extension seams of [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (`ctx.skills` / `ctx.tools` / `ctx.credentials` / `ctx.slots` / `ctx.layout`), and upgrade-safe across DSH versions:

| Plugin | Capability | Dependencies |
|---|---|---|
| `dsh-vision-skill` v0.4.4 | Vision plugin: 8 tools (including a progressive-exposure activation tool) + Credential-based secrets + path fencing | Node.js + DSH (`dsh-tools` / `dsh-credentials`), Python 3 + Pillow, vision model API key |
| `dsh-layered-memory` v0.4 | Cross-session long-term memory: namespace isolation + L1 index injection (existence encoding, KV-cache friendly) + L2 environment facts + L3 task experience + auto-distillation candidates + provenance/archive/rollback + auto maintenance | Node.js + DSH (`dsh-tools`) |
| `dsh-annotation-patched` | Selection annotation/quote plugin (fork enhancement): select assistant reply text → annotate (optional) or one-click "quote" → sent with the message on Enter, replies are matched one by one via `Annotation N`; enhancements: Codex-style "quote" button (explicit confirmation) + ghost-quote fix | Node.js + DSH (pure browser bundle, zero Node logic) |
| `dsh-side-panel-patched` | Right-side workspace panel (fork enhancement): file tree / multi-file tabs / preview / editing (CodeMirror) + Git review + terminal; enhancements: bypasses the official 520px width cap, pixel-perfect header alignment, Codex-style spindle drag handle, per-session file tab stacks, Windows terminal crash prevention | Node.js + DSH (file/Git/terminal APIs + browser bundle) |
| `dsh-ocr1-memory` v0.1.0 | Optically compressed memory: text rendered into SoM images for storage + age decay + active recall + OCR-driven retrieval | Node.js + DSH (`dsh-tools` / cordis / schemastery), Python 3 + Pillow, optional DeepSeek-OCR backend |

### 2️⃣ General skills (General_skills) — usable across frameworks

Any agent framework (Claude Code / Codex / opencode / DSH / Hermes, etc.) can mount these directories as skills:

| Skill | Capability | Dependencies |
|---|---|---|
| `vision-skill` | Vision: local image → vision model description (Qwen dynamic-resolution approach, OpenAI-compatible API) | Python 3 + vision model API key |
| `video-notes-generator` | Video URL → structured Markdown notes (timestamps / extracted frames / multimodal image observations / AI summary); supports Bilibili / YouTube / Douyin / Kuaishou / local files | Python 3 + dependencies (see `scripts/install_deps.sh`) |
| `ppt-master` | Source documents (PDF / DOCX / URL / Markdown) → multi-role collaborative SVG page generation → PPTX export | Python 3 (mostly stdlib, optional dependencies in `requirements.txt`) |
| `markitdown-skill` | Microsoft MarkItDown: PDF / DOCX / PPTX / XLSX / HTML / EPUB, etc. → unified Markdown | Python 3 + `pip install -r requirements.txt` |
| `generic-agent-code-run` | GenericAgent-style `code_run`: Windows desktop apps / real-browser automation (Win32 / UIA / OCR / screenshots / CDP) + observe-act-verify loop | Python 3 + corresponding libraries |

> All skills ship a built-in `SKILL.md` (instructions loaded by the agent runtime); some also include `scripts/`, `templates/`, and `references/`.

### 3️⃣ Hermes plugins (hermes_plugins)

| Plugin | Capability | Dependencies |
|---|---|---|
| [`language-router`](hermes_plugins/language-router/README.md) v5.0 | Adaptive language routing: Planner-first → Worker → optional Verifier → Digest flow (by NousResearch / Diana), mounts hooks on `pre_llm_call` / `pre_api_request` / `post_api_request` | Hermes framework |

## 📁 Directory Structure

```
Agent_Extensions/
├── dsh-plugins/               # DeepSeek Harness (DSH) native plugins
│   ├── dsh-vision-skill/      # Vision plugin v0.4.4 (8 tools + progressive exposure + credentialized secrets)
│   ├── dsh-layered-memory/    # Layered long-term memory (v0.4: namespaces / auto-distillation / auto maintenance)
│   ├── dsh-annotation-patched/ # Selection annotation/quote plugin (fork enhancement, Codex-style select-to-quote)
│   ├── dsh-side-panel-patched/ # Right-side workspace panel (fork enhancement, multi-file tabs + session tracking)
│   └── dsh-ocr1-memory/        # Optically compressed memory (SoM images + active recall)

├── General_skills/            # General agent skills (cross-framework, mount-and-use)
│   ├── vision-skill/          # Vision
│   ├── video-notes-generator/ # Video → structured notes
│   ├── ppt-master/            # Document → SVG → PPTX
│   ├── markitdown-skill/      # Any document → Markdown
│   └── generic-agent-code-run/ # Windows desktop/browser automation
├── hermes_plugins/            # Hermes framework plugins
│   └── language-router/       # Language routing (planner-first)
└── README.md
```

## 🚀 Quick Start

### Option 1: Install a DSH plugin (using `dsh-vision-skill` as an example)

DSH plugins have been split into standalone repositories; installing from the standalone repos is recommended:

```bash
# 1. Install from the standalone repo (bundles cordis.patch.yml, automatically contributes id: vision-skill)
dsh plugin --profile web add github:DDDFXYqiming/dsh-vision-skill

# 2. Configure the credential ($DSH_HOME/.credentials.yaml)
VISION_API_KEY: sk-xxxx
```

> What this repository keeps under `dsh-plugins/` are historical snapshots; for each plugin's latest documentation, see the corresponding standalone repo.


> ⚠️ After a bundle install, do **not** `insert` an entry with the same name in the profile's `cordis.patch.yml`, or it will trigger a `duplicate loader entry id` startup crash; for custom configuration, override by bare entry with the same id (see the plugin README).

### Option 2: Mount a general skill (any framework)

Using `vision-skill` as an example:

```bash
# 1. Copy the skill directory into your agent's skills directory
#    (Claude Code: ~/.claude/skills/ ; Codex: ~/.codex/skills/ ; other frameworks: see their docs)
cp -r General_skills/vision-skill <your skills directory>/

# 2. Configure the vision model (OpenAI-compatible API)
cd General_skills/vision-skill
cp templates/.env.example .env   # fill in VISION_API_URL / VISION_MODEL / VISION_API_KEY

# 3. Self-check
python scripts/vision.py --check
```

For usage of other skills, see the `SKILL.md` in each directory.

### Option 3: Install a Hermes plugin

Simply place the `hermes_plugins/language-router` directory into the Hermes plugin directory (`plugin.yaml` declares all hooks and version info).

## 🧩 DSH Plugin Capabilities

### dsh-vision-skill v0.4.4 (8 tools + 1 runtime skill)

| Tool | Capability |
|---|---|
| `vision_analyze` | Image understanding (5 modes + `mega` ultra-HD 16M-pixel budget) |
| `vision_ocr` / `vision_long_screenshot_ocr` | Standalone OCR / chunked OCR for very long screenshots (overlapping chunks → recognize chunk by chunk → merge) |
| `vision_ground` / `vision_detect` | Target grounding / element enumeration (pixel-coordinate boxes + normalized coordinates) |
| `vision_dominant_colors` | Dominant-color analysis (local pixel algorithm, no API needed) |
| `vision_clipboard` | Clipboard image fallback (handles the "current model does not support images" paste interception) |
| `vision_activate` | Progressive-exposure fallback: call once if tools do not appear automatically after the skill loads |

Engineering features: **progressive tool exposure** (only 1 lightweight activation tool registered globally, saving context), **credentialized secrets** (referenced via `credential: VISION_API_KEY`, resolved per operation), **path fencing** (realpath validation against traversal), **timeout and concurrency gating**, and **strict JSON Schema structured output**.

### dsh-layered-memory v0.4 (layered long-term memory)

| Component | Description |
|---|---|
| `memory:index` injection | Injects the L1 index in real time each turn via `ctx.systemPrompt.context` (existence encoding, effective as soon as a file is read, KV-cache friendly) |
| `memory` (runtime skill) | Trigger semantics: when to read / when to write / when to sync the index |
| `memory_activate` | Progressive-exposure fallback: call once if tools do not appear automatically after the skill loads |
| `memory_list` / `memory_read` | List / read memories (index / fact / sop, with provenance meta) |
| `memory_write` | Write memories (fact/sop, **evidence required** = action-verification axiom) |
| `memory_index` | Rebuild the L1 index auto section (preserving the manual `[RULES]` section) |
| `memory_pending` / `memory_accept` | Auto-distillation candidates: view / confirm into official memory |
| `memory_update` / `memory_archive` / `memory_rollback` | Update (supersede keeps history) / archive / rollback |
| `memory_expand` | Expand sourceSession/sourceSeqs raw events via `sessionQuery` |
| `memory_stats` / `memory_maintain` | Statistics / auto maintenance (dedup, index compaction, candidate merging) |

Core features: **namespace isolation** (`<memoryDir>/<namespace>/...`, defaulting to the workspace directory + git branch), **auto-distillation** (successful tool calls at turn/end → `pending/`, only confirmed entries enter official memory), **auto maintenance** (`maintainEveryTurns` defaults to 20), **progressive tool exposure** (`progressive: false` falls back to global registration).
Core axioms: **action verification** (No Execution, No Memory), **sacred and immutable** (verified facts may be compressed and migrated but must never be dropped), **no volatile state** (timestamps/PIDs/temporary paths are never stored), **minimal sufficient pointers** (L1 records existence only). Injection uses a user-role snapshot and **does not break DSH's KV cache hit rate** (design details in the plugin README).

### dsh-annotation-patched (selection annotation/quote, fork enhancement)

| Capability | Description |
|---|---|
| Selection annotation | Select assistant reply text → annotate (may be left empty) → sent with the message on Enter; your own bubbles do not show annotation blocks (zero-flicker hiding) |
| Item-by-item matching | The model responds item by item as `Annotation 1: …`, rendered in replies as hoverable chips (view original text + annotation) |
| **Codex-style "quote" button** (enhancement ①) | Select text → "quote" button in the toolbar → sent on Enter (empty annotation = pure quote); explicit confirmation, so copying or reading a selection never triggers it by accident |
| **Ghost-quote fix** (enhancement ②) | The pending-send set is cleared when the message is composed (the original relied on decoration-scan polling to clean up, which had race-condition leftovers) |

Source: [omdsh-dev/dsh-annotation](https://github.com/omdsh-dev/dsh-annotation) v1.3.13 (MIT); all changes are marked with `PATCH(2026-08-14)`, see the in-directory `README.md` for details.

### dsh-side-panel-patched (right-side workspace panel, fork enhancement)

| Capability | Description |
|---|---|
| File tree + multi-file tabs | Click a file in the tree → dedicated tab (multiple files open at once, switch/close-one/dedupe-on-activate), **tree singleton follows** the active tab, scroll position preserved across tabs |
| Session tracking | Switch workspace → tree reloads for the current workspace; file tabs are **grouped per session** (each kept separately, switched for display, no cross-talk) |
| Git review / terminal | Workspace change review (stage/unstage); Windows-friendly terminal degradation (does not crash under Unix PTY limitations) |
| Layout enhancements | Bypasses the official 520px width cap (free drag between 420px and 60% of the viewport), pixel-perfect alignment with the official header, Codex-style spindle drag handle, maximize button toggles full width |

Source: [ccq1/dsh-side-panel](https://github.com/ccq1/dsh-side-panel) v0.2.0 (BSD-3-Clause); all changes are marked with `PATCH(2026-08-14)`, see the in-directory `README.md` for details.

## ⚙️ Requirements

| Use case | Requirements |
|---|---|
| DSH plugins | Node.js + DSH (`@deepseek-ai/dsh-tools`, `@deepseek-ai/dsh-credentials`) |
| dsh-vision-skill / vision-skill | Additionally Python 3 + Pillow, plus an API key for **any OpenAI-compatible multimodal model** (Qwen-VL / MiniMax-M3 / Gemini / GPT-4o; MiniMax-M3 by default) |
| General skills (vision / video / ppt / markitdown / automation) | Python 3.x + each skill's listed pip dependencies |
| Hermes plugins | Hermes framework |

## ❓ FAQ

**Q: How do I choose between general skills and DSH plugins?**
A: General skills are cross-framework and can be mounted by any agent; DSH plugins are DSH-native extensions built on official seams (tool registration / credentials / context injection / layout slots) — more capable, but DSH-only. Their capabilities interoperate: `dsh-vision-skill` is simply `General_skills/vision-skill` wrapped as a DSH-native plugin.

**Q: My model doesn't support images — can it still do vision?**
A: Yes. Pasting an image directly will be rejected by the framework (`MODEL_DOES_NOT_SUPPORT_IMAGES`); use one of these instead: ① send the image's local path as text; ② take a screenshot and say "look at the image" — `vision_clipboard` saves it to the workspace and recognizes it automatically. This is a capability gate of text-only models, not a plugin problem.

**Q: Which vision API provider should I use?**
A: Any OpenAI-compatible multimodal model endpoint, injected via `VISION_API_URL` / `VISION_MODEL` / `VISION_API_KEY` — no vendor is hardcoded.

**Q: Are the subdirectories related to each other?**
A: No. Every subdirectory is an **independent, self-contained unit** — it can be used, published, and deleted on its own.

## 🤝 Contributing

- Every subdirectory is an independent, self-contained unit. New skills/plugins are welcome via **PRs**, and issues can be reported via **Issues**.
- Contribution requirements: self-contained (bundling your own scripts/templates/docs), a clear license (MIT recommended), and no hardcoded secrets or machine-specific absolute paths.
- New skills must use `SKILL.md` as the entry document; DSH plugins additionally ship `cordis.patch.yml` and `package.json`.

## 📄 License

All content in this repository is distributed under the **MIT License**. Content sourced from the community retains the original authors' attribution (see the header of each subdirectory's `SKILL.md` / `plugin.yaml`).
