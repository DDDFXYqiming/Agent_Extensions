// dsh-vision-skill — 标准 DSH 插件版 vision skill（v2：工程化增强）。
//
// 注册内容：
//   1. 运行时 skill `vision`（内容 = SKILL.md，模型按需加载）
//   2. 渐进式工具暴露（默认开启）：skill 加载成功后，为当前 Agent 挂载
//      vision_analyze / vision_ocr / vision_ground / vision_clipboard；
//      配置 progressive:false 或 agents 服务不可用时回退为全局注册。
//   3. 模型配置走插件 config（apiUrl / model / apiKey 或 credential 引用），
//      默认 MiniMax-M3，思考关闭；密钥支持 DSH Credential 引用（推荐），
//      不再强制明文写在配置文件里。
//   4. 工程化：路径围栏（工作区 / 附件目录 / allowedDirs）、超时、并发门控、
//      结构化输出、失败安全（配置缺失不炸插件加载，调用时报清晰错误）。
//
// 识图核心方法不变：vision.py 的 Qwen 动态分辨率预处理 + OpenAI 兼容 VLM。
import { execFile } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, realpathSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineTool } from "@deepseek-ai/dsh-tools";
import { credentialRef } from "@deepseek-ai/dsh-credentials";
import Schema from "@deepseek-ai/schemastery";

const name = "vision-skill";
// [spec-audit 2026-08-14 修订] credentials/agents 必须声明 inject：
// 实测 cordis ctx.get() 只查插件隔离层已登记的服务（未 inject 恒返回 undefined，
// 导致 VISION_API_KEY 解析失败），可选依赖模式在本版本 cordis 不成立。
const inject = ["skills", "tools", "credentials", "agents"];

const PLUGIN_DIR = dirname(fileURLToPath(import.meta.url));
const SKILL_MD = join(PLUGIN_DIR, "..", "SKILL.md");
const VISION_PY = join(PLUGIN_DIR, "..", "scripts", "vision.py");

/**
 * Schemastery 配置 schema（官方 config 约定：Cordis 在加载时校验配置并填充默认值）。
 * 校验失败会让插件加载失败并给出明确错误；progressive 接受 string 以兼容 'false' 写法。
 */
export const Config = Schema.object({
	apiUrl: Schema.string().default("https://api.minimaxi.com/v1/chat/completions"),
	model: Schema.string().default("MiniMax-M3"),
	apiKey: Schema.string().default(""),
	credential: Schema.string().default("VISION_API_KEY"),
	python: Schema.string().default("python"),
	pwsh: Schema.string().default("powershell.exe"),
	timeoutMs: Schema.number().default(180000),
	// [spec-audit 2026-08-14] 边界写入 schema：非法配置在加载期响亮失败，删除运行期静默钳制
	concurrency: Schema.number().min(1).max(8).default(2),
	// [spec-audit 2026-08-14] 纯 boolean：不再容忍字符串 'false'
	progressive: Schema.boolean().default(true),
	allowedDirs: Schema.array(Schema.string()).default([]),
});

/** 与 templates/.env.example 同语义的默认值（可被插件 config 覆盖）。 */
const DEFAULTS = {
	apiUrl: "https://api.minimaxi.com/v1/chat/completions",
	model: "MiniMax-M3",
	apiKey: "",
	credential: "VISION_API_KEY",
	python: "python",
	pwsh: "powershell.exe",
	timeoutMs: 180000,
	concurrency: 2,
	progressive: true,
	allowedDirs: [],
};

function resolveConfig(config = {}) {
	return {
		apiUrl: config.apiUrl ?? DEFAULTS.apiUrl,
		model: config.model ?? DEFAULTS.model,
		apiKey: config.apiKey ?? DEFAULTS.apiKey,
		credential: config.credential ?? DEFAULTS.credential,
		python: config.python ?? DEFAULTS.python,
		pwsh: config.pwsh ?? DEFAULTS.pwsh,
		timeoutMs: config.timeoutMs ?? DEFAULTS.timeoutMs,
		// [spec-audit 2026-08-14] schema 已限 1..8，此处不再静默钳制
		concurrency: config.concurrency ?? DEFAULTS.concurrency,
		progressive: config.progressive !== false,
		allowedDirs: Array.isArray(config.allowedDirs) ? config.allowedDirs : [],
	};
}

/** 每插件进程的轻量信号量（并发门控）。 */
class Semaphore {
	constructor(limit) {
		this.limit = limit;
		this.active = 0;
		this.queue = [];
	}
	async acquire() {
		if (this.active < this.limit) {
			this.active++;
			return;
		}
		await new Promise((resolvePromise) => this.queue.push(resolvePromise));
		this.active++;
	}
	release() {
		this.active--;
		const next = this.queue.shift();
		if (next) next();
	}
}

/** 子进程运行（stdout/stderr 按 UTF-8 收集，非零退出码抛错，支持超时与取消）。
 * [spec-audit 2026-08-14] 转发 exec.signal：上层取消回合时中止子进程（tools 执行契约）。 */
function run(command, args, options) {
	return new Promise((resolvePromise, reject) => {
		execFile(command, args, {
			encoding: "utf8",
			maxBuffer: 16 * 1024 * 1024,
			timeout: options.timeoutMs ?? 180000,
			signal: options.signal,
		}, (error, stdout, stderr) => {
			if (error) {
				if (options.signal?.aborted) {
					reject(new Error(`${command} 已被取消`));
					return;
				}
				const detail = (stderr ?? "").trim() || String(error.message);
				reject(new Error(`${command} 失败: ${detail}`));
				return;
			}
			resolvePromise({ stdout: stdout ?? "", stderr: stderr ?? "" });
		});
	});
}

/** 密钥解析：config.apiKey 优先；否则按操作解析 DSH Credential；最后看环境变量。
 * [spec-audit 2026-08-14] credentials 为可选服务：ctx.get() 查询，缺失时跳过。 */
async function resolveApiKey(ctx, cfg) {
	if (cfg.apiKey) return cfg.apiKey;
	const creds = ctx.get("credentials");
	try {
		if (creds) {
			const hit = await creds.resolve(credentialRef(cfg.credential));
			if (hit && hit.value) return hit.value;
		}
	} catch {
		// credentials 服务异常时继续尝试环境变量
	}
	return process.env.VISION_API_KEY ?? "";
}

/**
 * 路径围栏：解析并校验图片路径必须位于工作区 / DSH 附件目录 / allowedDirs 之一。
 * 附件目录默认放行，保证"输入框贴图 → 附件路径 → 识图"核心链路不受影响。
 */
function resolveImagePath(workspace, allowedDirs, raw) {
	if (!raw || typeof raw !== "string") {
		throw new Error("vision-skill: 缺少图片路径（image_path）");
	}
	const candidate = isAbsolute(raw) ? raw : resolve(workspace, raw);
	let real;
	try {
		real = realpathSync(candidate);
	} catch {
		throw new Error(`vision-skill: 图片不存在或不可读: ${raw}`);
	}
	const bases = [workspace, ...allowedDirs];
	// DSH_HOME 在宿主进程中可能被清理（已知行为），用 homedir() 回退：
	// C:\Users\<user>\.dsh\attachments
	const dshAtt = process.env.DSH_HOME
		? join(process.env.DSH_HOME, "attachments")
		: join(homedir(), ".dsh", "attachments");
	if (dshAtt && existsSync(dshAtt)) bases.push(dshAtt);
	for (const base of bases) {
		if (!base) continue;
		let baseReal;
		try {
			baseReal = realpathSync(base);
		} catch {
			continue;
		}
		const rel = relative(baseReal, real);
		if (rel !== "" && !rel.startsWith("..") && !isAbsolute(rel)) return real;
	}
	throw new Error(`vision-skill: 路径超出允许范围（工作区 / allowedDirs / 附件目录）: ${raw}`);
}

/** 会话工作区（与第一方工具一致）。 */
function sessionWorkspace(exec) {
	return exec.agent?.session?.header?.cwd ?? process.cwd();
}

/** 从 vision.py 的 stderr 日志解析图片信息（零侵入，核心输出不受影响）。 */
function parseImageInfo(stderr) {
	const info = {};
	const orig = stderr.match(/orig=(\d+)x(\d+)/);
	if (orig) info.original = { width: Number(orig[1]), height: Number(orig[2]) };
	const resized = stderr.match(/resized=([^\n]+)/);
	if (resized) info.resized = resized[1].trim();
	return info;
}

/** 共享参数 schema：识别模式/提示词/裁剪/预算（mega=4096² 超高清）。 */
function visionParams() {
	return {
		mode: {
			type: "string",
			enum: ["general", "ocr", "table", "code", "error"],
			description: "识别模式：general 描述 / ocr 纯文字 / table 表格转 Markdown / code 代码报错 / error 报错分析，默认 general"
		},
		prompt: {
			type: "string",
			description: "自定义识别要求（可选）"
		},
		crop: {
			type: "string",
			description: "先裁剪再识别：x1,y1,x2,y2（原图像素坐标，可选）"
		},
		budget: {
			type: "string",
			enum: ["small", "normal", "large", "mega"],
			description: "分辨率预算：small≈512² / normal≈1024² / large≈1448² / mega≈4096²（超高清，约 16M 像素），默认 normal"
		}
	};
}

/** 调打包的 vision.py 识别一张图片，返回文字描述（核心方法不变）。 */
async function runVision(ctx, cfg, sem, imagePath, { mode = "general", prompt, crop, budget = "normal" }, signal) {
	const apiKey = await resolveApiKey(ctx, cfg);
	if (!apiKey) throw new Error("vision-skill: 未配置 apiKey（插件 config 的 apiKey、credential 引用或 VISION_API_KEY 环境变量）");
	const args = [VISION_PY, imagePath];
	if (prompt) args.push(prompt);
	if (mode) args.push("--mode", mode);
	if (crop) args.push("--crop", crop);
	if (budget) args.push("--budget", budget);
	await sem.acquire();
	try {
		const { stdout, stderr } = await run(cfg.python, args, {
			cwd: dirname(VISION_PY),
			env: {
				...process.env,
				VISION_API_URL: cfg.apiUrl,
				VISION_MODEL: cfg.model,
				VISION_API_KEY: apiKey
			},
			timeoutMs: cfg.timeoutMs,
			signal
		});
		const text = stdout.trim();
		if (!text) throw new Error(`vision.py 无输出${stderr ? `: ${stderr.trim()}` : ""}`);
		return { text, imageInfo: parseImageInfo(stderr) };
	} finally {
		sem.release();
	}
}

/** 调 vision.py 定位（grounding）：返回结构化匹配（label + 像素/归一化 bbox）。 */
async function runGround(ctx, cfg, sem, imagePath, target, { crop, budget = "normal", output } = {}, signal) {
	const apiKey = await resolveApiKey(ctx, cfg);
	if (!apiKey) throw new Error("vision-skill: 未配置 apiKey（插件 config 的 apiKey、credential 引用或 VISION_API_KEY 环境变量）");
	if (!target || typeof target !== "string") {
		throw new Error("vision-skill: 缺少定位目标（target），例如「所有按钮」「微信图标」");
	}
	const args = [VISION_PY, imagePath, "--ground", target];
	if (crop) args.push("--crop", crop);
	if (budget) args.push("--budget", budget);
	if (output) args.push("--draw", output);
	await sem.acquire();
	try {
		const { stdout, stderr } = await run(cfg.python, args, {
			cwd: dirname(VISION_PY),
			env: {
				...process.env,
				VISION_API_URL: cfg.apiUrl,
				VISION_MODEL: cfg.model,
				VISION_API_KEY: apiKey
			},
			timeoutMs: cfg.timeoutMs,
			signal
		});
		const text = stdout.trim();
		if (!text) throw new Error(`vision.py 无输出${stderr ? `: ${stderr.trim()}` : ""}`);
		let parsed;
		try {
			parsed = JSON.parse(text);
		} catch {
			throw new Error(`vision-skill: grounding 输出不是有效 JSON: ${text.slice(0, 300)}`);
		}
		if (parsed.imageInfo) parsed.imageInfo = parseImageInfo(stderr);
		return parsed;
	} finally {
		sem.release();
	}
}

/** 通用：跑 vision.py 并解析 stdout 为 JSON（供 detect/colors/long_ocr 复用）。 */
async function runJsonScript(ctx, cfg, sem, args, { needKey = true, signal } = {}) {
	let apiKey = "";
	if (needKey) {
		apiKey = await resolveApiKey(ctx, cfg);
		if (!apiKey) throw new Error("vision-skill: 未配置 apiKey（插件 config 的 apiKey、credential 引用或 VISION_API_KEY 环境变量）");
	}
	await sem.acquire();
	try {
		const { stdout, stderr } = await run(cfg.python, [VISION_PY, ...args], {
			cwd: dirname(VISION_PY),
			env: {
				...process.env,
				VISION_API_URL: cfg.apiUrl,
				VISION_MODEL: cfg.model,
				VISION_API_KEY: apiKey
			},
			timeoutMs: cfg.timeoutMs,
			signal
		});
		const text = stdout.trim();
		if (!text) throw new Error(`vision.py 无输出${stderr ? `: ${stderr.trim()}` : ""}`);
		let parsed;
		try {
			parsed = JSON.parse(text);
		} catch {
			throw new Error(`vision-skill: 脚本输出不是有效 JSON: ${text.slice(0, 300)}`);
		}
		return parsed;
	} finally {
		sem.release();
	}
}

/** 枚举元素（detect）：与 grounding 同源，提示词改为枚举一类元素。 */
async function runDetect(ctx, cfg, sem, imagePath, category, { crop, budget = "normal", output } = {}, signal) {
	const args = [imagePath, "--detect"];
	if (category) args.push(category);
	if (crop) args.push("--crop", crop);
	if (budget) args.push("--budget", budget);
	if (output) args.push("--draw", output);
	return runJsonScript(ctx, cfg, sem, args, { signal });
}

/** 主色分析（本地算法，无需视觉 API）。 */
async function runColors(ctx, cfg, sem, imagePath, { region, top = 8 } = {}, signal) {
	const args = [imagePath, "--colors", String(top)];
	if (region) args.push("--crop", region);
	return runJsonScript(ctx, cfg, sem, args, { needKey: false, signal });
}

/** 长截图分块 OCR。 */
async function runLongOcr(ctx, cfg, sem, imagePath, { targetHeight = 2000, overlap = 100, budget = "normal", prompt } = {}, signal) {
	const args = [imagePath, "--long-ocr", "--target-height", String(targetHeight), "--overlap", String(overlap)];
	if (budget) args.push("--budget", budget);
	if (prompt) args.push("--prompt", prompt);
	return runJsonScript(ctx, cfg, sem, args, { signal });
}

/** 用 Windows PowerShell 5.1（STA + WinForms）把剪贴板图片保存为 PNG。 */
async function saveClipboardImage(cfg, dest, signal) {
	const escaped = dest.replace(/'/g, "''");
	const script = [
		"Add-Type -AssemblyName System.Windows.Forms",
		"Add-Type -AssemblyName System.Drawing",
		"$img = [System.Windows.Forms.Clipboard]::GetImage()",
		"if ($null -eq $img) { Write-Error 'CLIPBOARD_NO_IMAGE'; exit 3 }",
		`$img.Save('${escaped}', [System.Drawing.Imaging.ImageFormat]::Png)`,
		"Write-Output 'SAVED'"
	].join("; ");
	const { stderr } = await run(cfg.pwsh, ["-NoProfile", "-NonInteractive", "-Command", script], {
		env: process.env,
		timeoutMs: 60000,
		signal
	});
	if (stderr.includes("CLIPBOARD_NO_IMAGE")) throw new Error("vision-skill: 剪贴板里没有图片（先复制/截屏一张图片到剪贴板）");
}

/** 完整工具集（渐进暴露时按 Agent 挂载，兜底时全局注册）。 */
function createToolDefinitions(ctx, cfg, sem) {
	const analyze = defineTool({
		name: "vision_analyze",
		description: "用配置的视觉模型（默认 MiniMax-M3，思考关闭）识别一张本地图片，返回文字描述。支持绝对路径或相对会话工作区的路径，以及模式/裁剪/分辨率预算参数。",
		parameters: {
			image_path: {
				type: "string",
				required: true,
				description: "图片文件路径（png/jpg/jpeg/webp/gif）"
			},
			...visionParams()
		},
		output: {
			schema: {
				type: "object",
				additionalProperties: false,
				properties: {
					text: { type: "string", required: true },
					mode: { type: "string", required: true },
					image_info: {
						type: "object",
						additionalProperties: true,
						properties: {
							original: {
								type: "object",
								additionalProperties: true,
								properties: {
									width: { type: "integer" },
									height: { type: "integer" }
								}
							},
							resized: { type: "string" }
						}
					}
				}
			},
			render: (_args, value) => [{ type: "text", text: value.text }]
		},
		timeoutMs: cfg.timeoutMs,
		async execute(args, exec) {
			const workspace = sessionWorkspace(exec);
			const imagePath = resolveImagePath(workspace, cfg.allowedDirs, args.image_path);
			const { text, imageInfo } = await runVision(ctx, cfg, sem, imagePath, {
				mode: args.mode ?? "general",
				prompt: args.prompt,
				crop: args.crop,
				budget: args.budget ?? "normal"
			}, exec.signal);
			return { text, mode: args.mode ?? "general", image_info: imageInfo };
		},
		presentCall(args) {
			return { card: "generic", title: "识图", kind: "read", rawInput: args.image_path };
		}
	});

	const ocr = defineTool({
		name: "vision_ocr",
		description: "对图片做 OCR 文字识别（默认 MiniMax-M3，思考关闭）：提取全部可见文字，保持原始排版。独立于 vision_analyze 的专用 OCR 工具。",
		parameters: {
			image_path: {
				type: "string",
				required: true,
				description: "图片文件路径（png/jpg/jpeg/webp/gif）"
			},
			prompt: {
				type: "string",
				description: "附加 OCR 要求（可选），默认原样转述全部文字"
			},
			crop: {
				type: "string",
				description: "先裁剪再识别：x1,y1,x2,y2（原图像素坐标，可选）"
			},
			budget: {
				type: "string",
				enum: ["small", "normal", "large", "mega"],
				description: "分辨率预算，默认 normal；超清小字用 large 或 mega"
			}
		},
		output: {
			schema: {
				type: "object",
				additionalProperties: false,
				properties: {
					text: { type: "string", required: true },
					mode: { type: "string", const: "ocr", required: true },
					image_info: {
						type: "object",
						additionalProperties: true,
						properties: {
							original: {
								type: "object",
								additionalProperties: true,
								properties: {
									width: { type: "integer" },
									height: { type: "integer" }
								}
							},
							resized: { type: "string" }
						}
					}
				}
			},
			render: (_args, value) => [{ type: "text", text: value.text }]
		},
		timeoutMs: cfg.timeoutMs,
		async execute(args, exec) {
			const workspace = sessionWorkspace(exec);
			const imagePath = resolveImagePath(workspace, cfg.allowedDirs, args.image_path);
			const { text, imageInfo } = await runVision(ctx, cfg, sem, imagePath, {
				mode: "ocr",
				prompt: args.prompt,
				crop: args.crop,
				budget: args.budget ?? "normal"
			}, exec.signal);
			return { text, mode: "ocr", image_info: imageInfo };
		},
		presentCall(args) {
			return { card: "generic", title: "OCR 识图", kind: "read", rawInput: args.image_path };
		}
	});

	const ground = defineTool({
		name: "vision_ground",
		description: "在图片中定位指定目标（如「所有按钮」「微信图标」），返回每个目标的像素坐标框（bbox_pixel）与归一化坐标（bbox_normalized，0-1000）。坐标可直接用于 crop 或后续图像操作。",
		parameters: {
			image_path: {
				type: "string",
				required: true,
				description: "图片文件路径（png/jpg/jpeg/webp/gif）"
			},
			target: {
				type: "string",
				required: true,
				description: "要定位的目标描述，如「所有按钮」「搜索框」「微信图标」"
			},
			crop: {
				type: "string",
				description: "只在指定区域（x1,y1,x2,y2，原图像素）内搜索，可选"
			},
			budget: {
				type: "string",
				enum: ["small", "normal", "large", "mega"],
				description: "分辨率预算，默认 normal；小目标/复杂图建议 large"
			},
			output: {
				type: "string",
				description: "可选：把带标注框的预览图保存到该路径（相对工作区或绝对路径），返回 annotated_path"
			}
		},
		output: {
			schema: {
				type: "object",
				additionalProperties: false,
				properties: {
					target: { type: "string", required: true },
					image: {
						type: "object",
						additionalProperties: true,
						properties: {
							path: { type: "string" },
							width: { type: "integer" },
							height: { type: "integer" },
							bytes: { type: "integer" }
						}
					},
					matches: {
						type: "array",
						required: true,
						items: {
							type: "object",
							additionalProperties: false,
							properties: {
								label: { type: "string", required: true },
								bbox_pixel: { type: "array", items: { type: "integer" }, required: true },
								bbox_normalized: { type: "array", items: { type: "integer" }, required: true }
							}
						}
					},
					annotated_path: { type: "string" }
				}
			},
			render: (_args, value) => {
				const lines = value.matches.map((m, i) =>
					`${i + 1}. ${m.label}: 像素框 [${m.bbox_pixel.join(",")}] (归一化 [${m.bbox_normalized.join(",")}])`);
				return [{ type: "text", text: `定位「${value.target}」共 ${value.matches.length} 处：\n${lines.join("\n")}` }];
			}
		},
		timeoutMs: cfg.timeoutMs,
		async execute(args, exec) {
			const workspace = sessionWorkspace(exec);
			const imagePath = resolveImagePath(workspace, cfg.allowedDirs, args.image_path);
			let output;
			if (args.output) {
				const outPath = isAbsolute(args.output) ? args.output : resolve(workspace, args.output);
				mkdirSync(dirname(outPath), { recursive: true });
				output = outPath;
			}
			const result = await runGround(ctx, cfg, sem, imagePath, args.target, {
				crop: args.crop,
				budget: args.budget ?? "normal",
				output
			}, exec.signal);
			const { raw, ...clean } = result;
			return clean;
		},
		presentCall(args) {
			return { card: "generic", title: `定位 ${args.target}`, kind: "search", rawInput: args.image_path };
		}
	});

	const detect = defineTool({
		name: "vision_detect",
		description: "枚举图片中某一类元素（默认所有 UI 元素：按钮、链接、输入框、图标、标签、标题等），逐个编号并返回像素坐标框。与 vision_ground（找某个目标）互补：ground 找一个，detect 数一类。",
		parameters: {
			image_path: {
				type: "string",
				required: true,
				description: "图片文件路径（png/jpg/jpeg/webp/gif）"
			},
			category: {
				type: "string",
				description: "要枚举的元素类别，如「所有按钮」「所有输入框」「所有图标」；默认所有 UI 元素"
			},
			crop: {
				type: "string",
				description: "只在指定区域（x1,y1,x2,y2，原图像素）内枚举，可选"
			},
			budget: {
				type: "string",
				enum: ["small", "normal", "large", "mega"],
				description: "分辨率预算，默认 normal；元素多/小字建议 large"
			},
			output: {
				type: "string",
				description: "可选：把带编号标注框的预览图保存到该路径（相对工作区或绝对路径），返回 annotated_path"
			}
		},
		output: {
			schema: {
				type: "object",
				additionalProperties: false,
				properties: {
					category: { type: "string", required: true },
					image: {
						type: "object",
						additionalProperties: true,
						properties: {
							path: { type: "string" },
							width: { type: "integer" },
							height: { type: "integer" }
						}
					},
					elements: {
						type: "array",
						required: true,
						items: {
							type: "object",
							additionalProperties: false,
							properties: {
								index: { type: "integer", required: true },
								label: { type: "string", required: true },
								bbox_pixel: { type: "array", items: { type: "integer" }, required: true },
								bbox_normalized: { type: "array", items: { type: "integer" }, required: true }
							}
						}
					},
					annotated_path: { type: "string" }
				}
			},
			render: (_args, value) => {
				const lines = value.elements.map((e) =>
					`${e.index}. ${e.label}: 像素框 [${e.bbox_pixel.join(",")}]`);
				return [{ type: "text", text: `枚举「${value.category}」共 ${value.elements.length} 个元素：\n${lines.join("\n")}` }];
			}
		},
		timeoutMs: cfg.timeoutMs,
		async execute(args, exec) {
			const workspace = sessionWorkspace(exec);
			const imagePath = resolveImagePath(workspace, cfg.allowedDirs, args.image_path);
			let output;
			if (args.output) {
				const outPath = isAbsolute(args.output) ? args.output : resolve(workspace, args.output);
				mkdirSync(dirname(outPath), { recursive: true });
				output = outPath;
			}
			const result = await runDetect(ctx, cfg, sem, imagePath, args.category, {
				crop: args.crop,
				budget: args.budget ?? "normal",
				output
			}, exec.signal);
			const { raw, ...clean } = result;
			return clean;
		},
		presentCall(args) {
			return { card: "generic", title: `枚举 ${args.category ?? "UI 元素"}`, kind: "search", rawInput: args.image_path };
		}
	});

	const colors = defineTool({
		name: "vision_dominant_colors",
		description: "提取图片（或指定区域）的主要颜色：本地像素算法（降采样 + 中位切分量化 + 近色合并），无需视觉 API。返回颜色列表（#RRGGBB）与占比，用于取主题色/配色分析。",
		parameters: {
			image_path: {
				type: "string",
				required: true,
				description: "图片文件路径（png/jpg/jpeg/webp/gif）"
			},
			region: {
				type: "string",
				description: "只分析指定区域（x1,y1,x2,y2，原图像素），可选"
			},
			top: {
				type: "integer",
				description: "返回的主色数量（1-16），默认 8"
			}
		},
		output: {
			schema: {
				type: "object",
				additionalProperties: false,
				properties: {
					image: {
						type: "object",
						additionalProperties: true,
						properties: {
							path: { type: "string" },
							width: { type: "integer" },
							height: { type: "integer" },
							region: { type: "string" }
						}
					},
					colors: {
						type: "array",
						required: true,
						items: {
							type: "object",
							additionalProperties: false,
							properties: {
								color: { type: "string", required: true },
								share_pct: { type: "number", required: true }
							}
						}
					},
					sampled_pixels: { type: "integer" }
				}
			},
			render: (_args, value) => {
				const lines = value.colors.map((c) => `${c.color}  ${c.share_pct}%`);
				return [{ type: "text", text: `主色分析（${value.image.region ?? "全图"}）：\n${lines.join("\n")}` }];
			}
		},
		timeoutMs: cfg.timeoutMs,
		async execute(args, exec) {
			const workspace = sessionWorkspace(exec);
			const imagePath = resolveImagePath(workspace, cfg.allowedDirs, args.image_path);
			return runColors(ctx, cfg, sem, imagePath, {
				region: args.region,
				top: Math.max(1, Math.min(16, args.top ?? 8))
			}, exec.signal);
		},
		presentCall(args) {
			return { card: "generic", title: "主色分析", kind: "read", rawInput: args.image_path };
		}
	});

	const longOcr = defineTool({
		name: "vision_long_screenshot_ocr",
		description: "超长截图（聊天记录、整个网页等）分块 OCR：自动切块（带重叠）→ 逐块识别 → 合并全文，返回带块边界的 Markdown 文本。单次 API 塞不下的长图用这个。",
		parameters: {
			image_path: {
				type: "string",
				required: true,
				description: "图片文件路径（png/jpg/jpeg/webp/gif）"
			},
			target_height: {
				type: "integer",
				description: "每块目标高度（像素），默认 2000"
			},
			overlap: {
				type: "integer",
				description: "相邻块重叠高度（像素），默认 100"
			},
			budget: {
				type: "string",
				enum: ["small", "normal", "large", "mega"],
				description: "每块的分辨率预算，默认 normal"
			},
			prompt: {
				type: "string",
				description: "附加 OCR 要求（可选），默认原样提取每块文字"
			}
		},
		output: {
			schema: {
				type: "object",
				additionalProperties: false,
				properties: {
					source: {
						type: "object",
						additionalProperties: true,
						properties: {
							path: { type: "string" },
							width: { type: "integer" },
							height: { type: "integer" }
						}
					},
					chunk_count: { type: "integer", required: true },
					chunks: {
						type: "array",
						required: true,
						items: {
							type: "object",
							additionalProperties: false,
							properties: {
								index: { type: "integer" },
								top: { type: "integer" },
								bottom: { type: "integer" }
							}
						}
					},
					text: { type: "string", required: true }
				}
			},
			render: (_args, value) => [{ type: "text", text: value.text }]
		},
		timeoutMs: cfg.timeoutMs,
		async execute(args, exec) {
			const workspace = sessionWorkspace(exec);
			const imagePath = resolveImagePath(workspace, cfg.allowedDirs, args.image_path);
			return runLongOcr(ctx, cfg, sem, imagePath, {
				targetHeight: Math.max(200, Math.min(8000, args.target_height ?? 2000)),
				overlap: Math.max(0, Math.min(2000, args.overlap ?? 100)),
				budget: args.budget ?? "normal",
				prompt: args.prompt
			}, exec.signal);
		},
		presentCall(args) {
			return { card: "generic", title: "长截图分块 OCR", kind: "read", rawInput: args.image_path };
		}
	});

	const clipboard = defineTool({
		name: "vision_clipboard",
		description: "把当前剪贴板里的图片保存为会话工作区 .dsh-vision/clipboard-<时间戳>.png 并识别。当用户在输入框粘贴图片被「当前模型不支持图片」拦截时使用：用户只需把图片复制到剪贴板（如 Win+Shift+S 截屏）并说「看图」。",
		parameters: visionParams(),
		output: {
			schema: {
				type: "object",
				additionalProperties: false,
				properties: {
					text: { type: "string", required: true },
					saved_path: { type: "string", required: true }
				}
			},
			render: (_args, value) => [{ type: "text", text: `${value.text}\n\n（图片已保存: ${value.saved_path}）` }]
		},
		timeoutMs: cfg.timeoutMs,
		async execute(args, exec) {
			const workspace = sessionWorkspace(exec);
			const dir = join(workspace, ".dsh-vision");
			mkdirSync(dir, { recursive: true });
			const dest = join(dir, `clipboard-${Date.now()}.png`);
			await saveClipboardImage(cfg, dest, exec.signal);
			const { text, imageInfo } = await runVision(ctx, cfg, sem, dest, {
				mode: args.mode ?? "general",
				prompt: args.prompt,
				crop: args.crop,
				budget: args.budget ?? "normal"
			}, exec.signal);
			return { text, saved_path: dest, image_info: imageInfo };
		},
		presentCall() {
			return { card: "generic", title: "识别剪贴板图片", kind: "read", rawInput: "clipboard" };
		}
	});

	return [analyze, ocr, ground, detect, colors, longOcr, clipboard];
}

async function apply(ctx, config = {}) {
	const cfg = resolveConfig(config);
	const sem = new Semaphore(cfg.concurrency);
	const disposers = [];
	const agentStates = new Map(); // agent -> disposer[]

	// [spec-audit 2026-08-14] 注册前剥离 frontmatter（与磁盘 provider 行为一致）；
	// disposer 收集进 disposers（cordis-primer 注册可逆原则）
	const skillDisposer = ctx.skills.register({
		name: "vision",
		description: "识别图片内容。当用户发送图片、截图、报错图，或要求分析某张本地图片时使用。加载本 skill 后自动激活视觉工具（vision_analyze / vision_ocr / vision_ground / vision_detect / vision_dominant_colors / vision_long_screenshot_ocr / vision_clipboard）。",
		whenToUse: "用户要求分析图片、截图、报错图、OCR、表格截图、代码报错截图、定位/枚举图片中的目标、取色分析、超长截图文字提取等视觉任务",
		source: "runtime",
		content: readFileSync(SKILL_MD, "utf8").replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n?/, "")
	});
	if (typeof skillDisposer === "function") disposers.push(skillDisposer);

	const disposeAll = (fns) => {
		for (const fn of [...fns].reverse()) {
			try { fn(); } catch { /* 忽略清理错误 */ }
		}
	};

	const activate = (agent) => {
		if (agentStates.has(agent)) return { activated: false, tools: [] };
		const defs = createToolDefinitions(ctx, cfg, sem);
		const ds = [];
		try {
			for (const def of defs) ds.push(agent.ctx.tools.register(def));
			try {
				const hide = agent.ctx.tools.restrict({ deny: ["vision_activate"] });
				if (hide) ds.push(hide);
			} catch { /* restrict 不可用时激活工具保留（无害） */ }
			agentStates.set(agent, ds);
			return { activated: true, tools: defs.map((d) => d.name) };
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

	// [spec-audit 2026-08-14] agents 为可选服务（inject 已移除）：ctx.get() 查询，
	// 缺失时退化为全局注册（与代码意图一致，死分支消除）
	const agents = ctx.get("agents");
	const progressive = cfg.progressive && Boolean(agents);

	if (progressive) {
		// 全局只挂一个轻量激活工具 + skill；完整工具集按 Agent 渐进暴露。
		ctx.tools.register(defineTool({
			name: "vision_activate",
			description: "加载 vision skill 后，为当前 Agent 激活视觉工具（vision_analyze / vision_ocr / vision_ground / vision_detect / vision_dominant_colors / vision_long_screenshot_ocr / vision_clipboard）。skill 加载成功后通常会自动激活；仅当工具未出现时调用一次。",
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
				render: (_args, value) => [{ type: "text", text: `视觉工具已激活: ${value.tools.join(", ")}` }]
			},
			execute: (_args, exec) => {
				if (!exec.agent) throw new Error("vision_activate: 需要 Agent 会话");
				return Promise.resolve(activate(exec.agent));
			},
			presentCall: () => ({ card: "generic", title: "激活视觉工具", kind: "execute" })
		}));

		// [spec-audit 2026-08-14] 移除空监听器：工具激活已由 tools/result 监听完成，
		// agent/created 空实现是死代码（events.md：监听器应为有效逻辑）
		disposers.push(ctx.on("agent/disposed", ({ agent }) => detach(agent)));
		disposers.push(ctx.on("tools/result", (exec, result) => {
			if (!result.isError
				&& exec.name === "skill"
				&& exec.agent
				&& exec.arguments
				&& exec.arguments.name === "vision") {
				activate(exec.agent);
			}
			return undefined;
		}));
	} else {
		// 兜底：无 agents 服务或配置 progressive:false → 全局注册（v1 行为）。
		for (const def of createToolDefinitions(ctx, cfg, sem)) {
			ctx.tools.register(def);
		}
	}

	return () => {
		for (const agent of [...agentStates.keys()]) detach(agent);
		disposeAll(disposers);
	};
}

export { apply, inject, name };
