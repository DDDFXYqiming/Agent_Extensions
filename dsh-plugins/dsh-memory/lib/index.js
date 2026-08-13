// dsh-memory — DSH 跨会话长期记忆插件（v0.2）。
//
// 分层记忆（L0 元规则 / L1 索引 / L2 事实 / L3 SOP）+ 行动验证公理，
// 写入永远由模型/用户主动发起。
//
// 存储布局（默认 <home>/.dsh/memory/）：
//   memory_management_sop.md   L0 元规则（怎么管记忆）
//   index.txt                  L1 索引（≤30 行，存在性编码 + RULES）
//   facts.md                   L2 环境事实库（## SECTION）
//   sops/*.md                  L3 任务 SOP
//   file_access_stats.json     读取热度统计（轻量）
//
// 注入（存在性编码：L1 索引每轮可见）：
//   ctx.systemPrompt.context({ name: 'memory:index', order: 10,
//     text: () => readIndex() }) —— 每次组装请求实时读 L1，模型每轮都"知道有什么记忆可用"，
//   需要细节时通过 memory_read/memory_list 取 L2/L3。
//
// 写入触发（GA 的 start_long_term_update 等价物）：
//   memory_write 工具，由模型/用户在任务完成且【行动验证成功】时主动调用；
//   evidence 必填（行动验证公理：无行动，不记忆）。
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { defineTool } from "@deepseek-ai/dsh-tools";
import Schema from "@deepseek-ai/schemastery";

const name = "memory";
const inject = ["skills", "tools", "systemPrompt", "agents"];

const PLUGIN_DIR = dirname(fileURLToPath(import.meta.url));
const SKILL_MD = join(PLUGIN_DIR, "..", "SKILL.md");

/** Schemastery 配置 schema（官方 config 约定：加载期校验 + 默认值填充）。 */
export const Config = Schema.object({
	memoryDir: Schema.string().default(""),
	maxIndexLines: Schema.number().default(30),
	progressive: Schema.union([Schema.boolean(), Schema.string()]).default(true),
});

const L0_TEMPLATE = `# Memory Management SOP (L0)
## 核心公理
1. 行动验证原则：任何写入 L1/L2/L3 的信息必须源自【成功的工具调用结果】（实测/验证/确认）。严禁模型固有知识、推理猜测、未验证假设。口号：无行动，不记忆。
2. 神圣不可删改性：已验证的事实可以压缩文字、迁移层级，但严禁丢弃。
3. 禁止易变状态：时间戳、PID、临时 Session ID、一次性路径等高频变化数据不存。
4. 最小充分指针：上层只留能定位下层的短标识，多一词即冗余。

## 分层
- L1 index.txt：≤30 行。两层「场景关键词→记忆定位」映射 + RULES（红线规则/高频犯错点）。只写存在性，禁写 How-to 细节。
- L2 facts.md：环境特异性事实（路径/凭证引用/配置/实测参数）。按 ## SECTION 组织。
- L3 sops/*.md：特定任务经验（关键前置 + 典型坑 + 稳定步骤），尽可能短。
- 通用常识 / 易变状态 / 日志记录：严禁存储。

## 写入决策树
"这条信息该放哪层？"
- 环境特异性事实（路径/配置/凭证引用/实测参数）→ L2 facts.md
- 复杂任务经验（坑点/前置条件/稳定步骤，多次重试才成功且未来可用）→ L3 sop
- 通用操作规律（跨任务红线）→ L1 [RULES]（一句压缩）
- 其余（常识/易变/未验证）→ 不存
`;

const INDEX_TEMPLATE = `# [Memory Index - L1]
分层记忆: L0规则(memory_management_sop.md) | L1索引(this) | L2事实(facts.md) | L3技能(sops/)
需要细节时用 memory_read / memory_list 取 L2/L3；新增经验用 memory_write（须带证据）
任务完成且【行动验证成功】时主动 memory_write 沉淀（无需等用户提醒；无验证信息则不写）
<!-- AUTO-BEGIN -->
[L2] （facts.md 的条目将在此列出）
[L3] （sops/ 的文件将在此列出）
<!-- AUTO-END -->
[RULES]
（红线规则：不提醒就会犯的错。词级维护，禁 overwrite）
`;

const FACTS_TEMPLATE = `# [Facts - L2]
按 ## SECTION 组织环境特异性事实。只写行动验证过的内容。
`;

function defaultMemDir() {
	return join(homedir(), ".dsh", "memory");
}

/** 初始化记忆目录结构（幂等，不覆盖已有内容）。 */
function ensureMemoryLayout(memDir) {
	mkdirSync(join(memDir, "sops"), { recursive: true });
	const seeds = [
		["memory_management_sop.md", L0_TEMPLATE],
		["index.txt", INDEX_TEMPLATE],
		["facts.md", FACTS_TEMPLATE],
	];
	for (const [file, content] of seeds) {
		const p = join(memDir, file);
		if (!existsSync(p)) writeFileSync(p, content, "utf8");
	}
}

function readIndex(memDir) {
	try {
		return readFileSync(join(memDir, "index.txt"), "utf8");
	} catch {
		return "";
	}
}

function slugify(topic) {
	const s = String(topic).trim().toLowerCase()
		.replace(/[^\p{L}\p{N}]+/gu, "-")
		.replace(/^-+|-+$/g, "");
	return s.slice(0, 48) || "entry";
}

/** facts.md 的 section 名列表。 */
function factSections(memDir) {
	try {
		const text = readFileSync(join(memDir, "facts.md"), "utf8");
		const out = [];
		for (const line of text.split("\n")) {
			const m = line.match(/^##\s+(.+)$/);
			if (m) out.push(m[1].trim());
		}
		return out;
	} catch {
		return [];
	}
}

/** sops/ 的文件名列表（去 .md）。 */
function sopNames(memDir) {
	try {
		return readdirSync(join(memDir, "sops"))
			.filter((f) => f.endsWith(".md"))
			.map((f) => f.replace(/\.md$/, ""))
			.sort();
	} catch {
		return [];
	}
}

/** 确保 L1 固定段含常驻规则行、表述与最新模板一致（对已存在的旧索引也生效）。 */
function ensureIndexRule(memDir) {
	const p = join(memDir, "index.txt");
	if (!existsSync(p)) return;
	let cur = readFileSync(p, "utf8");
	// 表述迁移：避免与 L0-L4 分层混淆（我们只有 L0-L3）
	cur = cur.replace("4层记忆: L0规则", "分层记忆: L0规则");
	cur = cur.replace("4层记忆", "分层记忆");
	if (cur.includes("任务完成且【行动验证成功】")) {
		if (cur !== readFileSync(p, "utf8")) writeFileSync(p, cur, "utf8");
		return;
	}
	const anchor = "新增经验用 memory_write（须带证据）";
	if (cur.includes(anchor)) {
		cur = cur.replace(anchor, anchor + "\n任务完成且【行动验证成功】时主动 memory_write 沉淀（无需等用户提醒；无验证信息则不写）");
	} else {
		cur = cur.replace("# [Memory Index - L1]", "# [Memory Index - L1]\n任务完成且【行动验证成功】时主动 memory_write 沉淀（无需等用户提醒；无验证信息则不写）");
	}
	writeFileSync(p, cur, "utf8");
}

/** 重建 index.txt 的自动段（L2 列表 + L3 列表），保留 AUTO 标记之外的 RULES 等。 */
function syncIndex(memDir, maxIndexLines = 30) {
	const p = join(memDir, "index.txt");
	let head = INDEX_TEMPLATE;
	let tail = "";
	try {
		const cur = readFileSync(p, "utf8");
		const b = cur.indexOf("<!-- AUTO-BEGIN -->");
		const e = cur.indexOf("<!-- AUTO-END -->");
		if (b >= 0 && e > b) {
			head = cur.slice(0, b);
			tail = cur.slice(e + "<!-- AUTO-END -->".length);
		} else if (cur.trim()) {
			// 无标记的老文件：全部视为手动段，仅追加自动段
			head = cur.replace(/\s*$/, "\n\n");
		}
	} catch { /* 用模板 */ }
	const facts = factSections(memDir);
	const sops = sopNames(memDir);
	const auto = "[L2] " + (facts.length ? facts.join(" | ") : "（空）")
		+ "\n[L3] " + (sops.length ? sops.map((s) => `sops/${s}.md`).join(" | ") : "（空）");
	const rebuilt = head
		+ "<!-- AUTO-BEGIN -->\n" + auto + "\n<!-- AUTO-END -->\n"
		+ tail;
	writeFileSync(p, rebuilt, "utf8");
	// 行数约束检查（仅报告，不强制截断——RULES 是手动段）
	const lines = rebuilt.split("\n").length;
	return { index_lines: lines, max_index_lines: maxIndexLines, over_limit: lines > maxIndexLines };
}

/** upsert facts.md 的 ## SECTION（基于行解析，避免正则边界坑）。 */
function upsertFact(memDir, topic, content) {
	const p = join(memDir, "facts.md");
	const text = existsSync(p) ? readFileSync(p, "utf8") : FACTS_TEMPLATE;
	const lines = text.split("\n");
	let start = -1;
	let end = lines.length;
	for (let i = 0; i < lines.length; i++) {
		if (lines[i].startsWith("## ")) {
			if (start >= 0) { end = i; break; }
			if (lines[i].slice(3).trim() === topic) start = i;
		}
	}
	if (start >= 0) {
		const updated = [...lines.slice(0, start), `## ${topic}`, content, "", ...lines.slice(end)];
		writeFileSync(p, updated.join("\n"), "utf8");
		return "updated";
	}
	writeFileSync(p, text.replace(/\s*$/, "\n") + `## ${topic}\n${content}\n\n`, "utf8");
	return "created";
}

/** 读取 facts.md 的指定 section。 */
function readFact(memDir, topic) {
	const text = existsSync(join(memDir, "facts.md")) ? readFileSync(join(memDir, "facts.md"), "utf8") : "";
	const lines = text.split("\n");
	let inSection = false;
	const out = [];
	for (const line of lines) {
		if (line.startsWith("## ")) {
			if (inSection) break;
			if (line.slice(3).trim() === topic) { inSection = true; continue; }
		}
		if (inSection) out.push(line);
	}
	return inSection ? out.join("\n").trim() : null;
}

/** 记录读取热度（GA file_access_stats 简化版）。 */
function bumpAccess(memDir, key) {
	try {
		const p = join(memDir, "file_access_stats.json");
		const stats = existsSync(p) ? JSON.parse(readFileSync(p, "utf8")) : {};
		stats[key] = (stats[key] ?? 0) + 1;
		writeFileSync(p, JSON.stringify(stats, null, 2), "utf8");
	} catch { /* 热度统计失败不影响主流程 */ }
}

async function apply(ctx, config = {}) {
	const cfg = {
		memoryDir: config.memoryDir || defaultMemDir(),
		maxIndexLines: config.maxIndexLines ?? 30,
		progressive: config.progressive !== false && config.progressive !== "false",
	};
	ensureMemoryLayout(cfg.memoryDir);
	ensureIndexRule(cfg.memoryDir);

	const disposers = [];
	const agentStates = new Map();

	// ── 记忆注入（L1 存在性索引每轮可见，缓存友好：快照追加式）──
	if (ctx.systemPrompt) {
		disposers.push(ctx.systemPrompt.context({
			name: "memory:index",
			order: 10,
			text: () => {
				const idx = readIndex(cfg.memoryDir);
				return idx.trim() ? idx : "";
			}
		}));
	}

	// ── 周期记忆提醒（GA 每 10 轮刷新/提示的等价物：按 agent 独立计数，inject 轻量通知）──
	const turnCounters = new Map();
	disposers.push(ctx.on("turn/end", ({ agent }) => {
		if (!agent || typeof agent.inject !== "function") return undefined;
		const id = String(agent.id);
		const n = (turnCounters.get(id) ?? 0) + 1;
		turnCounters.set(id, n);
		if (n % 10 === 0) {
			try {
				agent.inject({
					content: [{
						type: "text",
						text: "[记忆检查] 已完成 10 轮。本任务是否产生了【行动验证成功】且未来可复用的经验？若有请用 memory_write 沉淀（须带 evidence）；若无则忽略本提醒。"
					}],
					source: { kind: "plugin", plugin: "memory" }
				});
			} catch { /* agent 已 dispose 时忽略 */ }
		}
		return undefined;
	}));
	// agent 销毁时清理轮次计数（防 Map 无限增长）
	disposers.push(ctx.on("agent/disposed", ({ agent }) => {
		if (agent) turnCounters.delete(String(agent.id));
		return undefined;
	}));

	// ── 运行时 skill（触发语义见 SKILL.md）──
	ctx.skills.register({
		name: "memory",
		description: "跨会话长期记忆：读写经验 SOP 与环境事实。当任务涉及本机环境、工具配置、以前踩过的坑，或任务完成发现值得沉淀的验证经验时使用。",
		whenToUse: "新任务开始时需要历史经验/环境事实；任务完成且存在行动验证成功、未来可复用的信息（写入）；记忆索引需要同步",
		source: "runtime",
		content: readFileSync(SKILL_MD, "utf8")
	});

	// ── 工具定义 ──
	const readTool = defineTool({
		name: "memory_read",
		description: "读取记忆内容：支持 L1 索引全文（name=index）、L2 事实条目（name=<topic>，匹配 facts.md 的 ## section）、L3 SOP（name=<sop文件名>，匹配 sops/<name>.md）。返回内容与来源路径。",
		parameters: {
			name: {
				type: "string",
				required: true,
				description: "记忆名称：index / facts 的 section 主题 / sop 文件名（不带 .md）"
			}
		},
		output: {
			schema: {
				type: "object",
				additionalProperties: false,
				properties: {
					name: { type: "string", required: true },
					source: { type: "string", required: true },
					content: { type: "string", required: true },
					not_found: { type: "boolean" }
				}
			},
			render: (_args, value) => [{
				type: "text",
				text: value.not_found
					? `记忆「${value.name}」未找到（可用 memory_list 查看全部）`
					: `记忆「${value.name}」（来源: ${value.source}）：\n\n${value.content}`
			}]
		},
		async execute(args) {
			const key = String(args.name).trim();
			const lower = key.toLowerCase();
			if (lower === "index" || lower === "l1" || lower === "索引") {
				bumpAccess(cfg.memoryDir, "index");
				return { name: key, source: "index.txt", content: readIndex(cfg.memoryDir) };
			}
			// L3 sop 优先（精确文件名 + slug 匹配，容错中文/空格主题）
			const candidates = [key, slugify(key)];
			for (const c of candidates) {
				const sopPath = join(cfg.memoryDir, "sops", `${c}.md`);
				if (existsSync(sopPath)) {
					bumpAccess(cfg.memoryDir, `sop:${c}`);
					return { name: key, source: `sops/${c}.md`, content: readFileSync(sopPath, "utf8") };
				}
			}
			// L2 fact
			const fact = readFact(cfg.memoryDir, key);
			if (fact !== null) {
				bumpAccess(cfg.memoryDir, `fact:${key}`);
				return { name: key, source: "facts.md", content: fact };
			}
			// 支持 sops/xxx.md 形式
			if (key.includes("sops/")) {
				const p = join(cfg.memoryDir, key);
				if (existsSync(p)) return { name: key, source: key, content: readFileSync(p, "utf8") };
			}
			return { name: key, source: "", content: "", not_found: true };
		},
		presentCall(args) {
			return { card: "generic", title: `读取记忆 ${args.name}`, kind: "read" };
		}
	});

	const listTool = defineTool({
		name: "memory_list",
		description: "列出全部记忆：L2 facts 条目 + L3 SOP 文件 + L1 索引行数。用于了解当前记忆库有什么。",
		parameters: {},
		output: {
			schema: {
				type: "object",
				additionalProperties: false,
				properties: {
					index_lines: { type: "integer", required: true },
					facts: { type: "array", items: { type: "string" }, required: true },
					sops: { type: "array", items: { type: "string" }, required: true }
				}
			},
			render: (_args, value) => [{
				type: "text",
				text: `记忆库（${value.index_lines} 行索引）\nL2 事实: ${value.facts.join("、") || "（空）"}\nL3 SOP: ${value.sops.join("、") || "（空）"}`
			}]
		},
		execute() {
			const facts = factSections(cfg.memoryDir);
			const sops = sopNames(cfg.memoryDir);
			const lines = readIndex(cfg.memoryDir).split("\n").length;
			return { index_lines: lines, facts, sops };
		},
		presentCall() {
			return { card: "generic", title: "列出记忆", kind: "read" };
		}
	});

	const writeTool = defineTool({
		name: "memory_write",
		description: "写入跨会话记忆（行动验证公理：evidence 必填，只写【成功验证过】的信息）。entry_type=fact 存 L2 环境事实（路径/配置/实测参数）；entry_type=sop 存 L3 任务经验（坑点/前置条件/稳定步骤）。写入后自动同步 L1 索引。",
		parameters: {
			topic: {
				type: "string",
				required: true,
				description: "记忆主题（fact 的 section 名 / sop 的文件名，简短自解释）"
			},
			entry_type: {
				type: "string",
				enum: ["fact", "sop"],
				required: true,
				description: "fact=环境事实(L2) / sop=任务经验(L3)"
			},
			content: {
				type: "string",
				required: true,
				description: "记忆内容：fact 用要点列表；sop 用「关键前置 + 典型坑 + 稳定步骤」精简格式，尽可能短"
			},
			evidence: {
				type: "string",
				required: true,
				description: "验证证据：本次成功验证该信息的工具调用/实测结果（行动验证公理：无行动，不记忆）。没有验证证据就不要调用本工具"
			}
		},
		output: {
			schema: {
				type: "object",
				additionalProperties: false,
				properties: {
					entry_type: { type: "string", required: true },
					topic: { type: "string", required: true },
					path: { type: "string", required: true },
					action: { type: "string", required: true },
					index: {
						type: "object",
						additionalProperties: false,
						properties: {
							index_lines: { type: "integer" },
							max_index_lines: { type: "integer" },
							over_limit: { type: "boolean" }
						}
					}
				}
			},
			render: (_args, value) => [{
				type: "text",
				text: `✅ 已${value.action === "created" ? "新建" : "更新"}记忆「${value.topic}」（${value.entry_type === "fact" ? "L2 事实" : "L3 SOP"}）→ ${value.path}${value.index?.over_limit ? "\n⚠️ L1 索引超过 30 行，建议运行 memory_index 或精简 RULES" : ""}`
			}]
		},
		async execute(args) {
			const topic = String(args.topic).trim();
			const type = args.entry_type === "fact" ? "fact" : "sop";
			const content = String(args.content).trim();
			const evidence = String(args.evidence ?? "").trim();
			if (!topic || !content) throw new Error("memory_write: topic 与 content 必填");
			if (!evidence) {
				throw new Error("memory_write: evidence 必填（行动验证公理：无行动，不记忆）。请提供本次成功验证该信息的工具调用/实测证据，或取消写入。");
			}
			const body = `${content}\n\n> 证据: ${evidence}\n`;
			let path;
			let action;
			if (type === "fact") {
				path = join(cfg.memoryDir, "facts.md");
				action = upsertFact(cfg.memoryDir, topic, body.trim());
			} else {
				const slug = slugify(topic);
				path = join(cfg.memoryDir, "sops", `${slug}.md`);
				const header = `# ${topic}\n\n`;
				if (existsSync(path)) {
					writeFileSync(path, header + body, "utf8");
					action = "updated";
				} else {
					writeFileSync(path, header + body, "utf8");
					action = "created";
				}
			}
			const index = syncIndex(cfg.memoryDir, cfg.maxIndexLines);
			return { entry_type: type, topic, path, action, index };
		},
		presentCall(args) {
			return { card: "generic", title: `写入记忆 ${args.topic}`, kind: "execute" };
		}
	});

	const indexTool = defineTool({
		name: "memory_index",
		description: "重建 L1 索引的自动段（L2 facts 列表 + L3 sops 列表），保留 [RULES] 手动段。在新增/删除 facts 或 sops 后用于同步索引（memory_write 已自动调用，仅在手动改动记忆文件后使用）。",
		parameters: {},
		output: {
			schema: {
				type: "object",
				additionalProperties: false,
				properties: {
					index_lines: { type: "integer", required: true },
					over_limit: { type: "boolean", required: true },
					facts: { type: "array", items: { type: "string" }, required: true },
					sops: { type: "array", items: { type: "string" }, required: true }
				}
			},
			render: (_args, value) => [{
				type: "text",
				text: `索引已重建（${value.index_lines} 行${value.over_limit ? "，⚠️ 超过限制建议精简" : ""}）：\nL2: ${value.facts.join("、") || "（空）"}\nL3: ${value.sops.join("、") || "（空）"}`
			}]
		},
		execute() {
			const r = syncIndex(cfg.memoryDir, cfg.maxIndexLines);
			return { index_lines: r.index_lines, over_limit: r.over_limit, facts: factSections(cfg.memoryDir), sops: sopNames(cfg.memoryDir) };
		},
		presentCall() {
			return { card: "generic", title: "重建记忆索引", kind: "execute" };
		}
	});

	const allTools = [readTool, listTool, writeTool, indexTool];

	// ── 渐进式暴露（与 dsh-vision-skill 同款：skill 加载后按 Agent 挂载）──
	const disposeAll = (fns) => {
		for (const fn of [...fns].reverse()) {
			try { fn(); } catch { /* 忽略 */ }
		}
	};
	const activate = (agent) => {
		if (agentStates.has(agent)) return { activated: false, tools: [] };
		const ds = [];
		try {
			for (const def of allTools) ds.push(agent.ctx.tools.register(def));
			try {
				const hide = agent.ctx.tools.restrict({ deny: ["memory_activate"] });
				if (hide) ds.push(hide);
			} catch { /* restrict 不可用时保留激活工具 */ }
			agentStates.set(agent, ds);
			return { activated: true, tools: allTools.map((d) => d.name) };
		} catch (error) {
			disposeAll(ds);
			throw error;
		}
	};
	const detach = (agent) => {
		const ds = agentStates.get(agent);
		if (ds) {
			disposeAll(ds);
			agentStates.delete(agent);
		}
	};

	const progressive = cfg.progressive && Boolean(ctx.agents);
	if (progressive) {
		ctx.tools.register(defineTool({
			name: "memory_activate",
			description: "加载 memory skill 后，为当前 Agent 激活记忆工具（memory_read / memory_list / memory_write / memory_index）。skill 加载成功后通常会自动激活；仅当工具未出现时调用一次。",
			parameters: {},
			output: {
				schema: {
					type: "object",
					additionalProperties: false,
					properties: {
						activated: { type: "boolean", required: true },
						tools: { type: "array", items: { type: "string" }, required: true }
					}
				},
				render: (_args, value) => [{ type: "text", text: `记忆工具已激活: ${value.tools.join(", ")}` }]
			},
			execute: (_args, exec) => {
				if (!exec.agent) throw new Error("memory_activate: 需要 Agent 会话");
				return Promise.resolve(activate(exec.agent));
			},
			presentCall: () => ({ card: "generic", title: "激活记忆工具", kind: "execute" })
		}));
		disposers.push(ctx.on("agent/created", () => { /* 等 skill 加载 */ }));
		disposers.push(ctx.on("agent/disposed", ({ agent }) => detach(agent)));
		disposers.push(ctx.on("tools/result", (exec, result) => {
			if (!result.isError
				&& exec.name === "skill"
				&& exec.agent
				&& exec.arguments
				&& exec.arguments.name === "memory") {
				activate(exec.agent);
			}
			return undefined;
		}));
	} else {
		for (const def of allTools) ctx.tools.register(def);
	}

	return () => {
		for (const agent of [...agentStates.keys()]) detach(agent);
		disposeAll(disposers);
	};
}

export { apply, inject, name };
