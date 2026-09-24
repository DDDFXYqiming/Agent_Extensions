# 质量工具与证据判定

## 指标的用途

测试、静态检查和度量描述不同性质。一个分数概括不了工程质量，测试全绿也证明不了业务规格没有遗漏。记录工具版本、调用参数、目标范围、源码指纹、退出码和原始报告，才能比较不同迭代。

CRAP = C² × (1 − c)³ + C，C 是函数圈复杂度，c 是该函数覆盖比例。用 coverage.py 的逐行执行信息与 radon 的函数区间配对计算时，明确标为行覆盖口径，不与分支覆盖口径混比。默认门槛 30 只是起点（Bob 的 Cleaner 提示词用 10 并带情境例外），应按项目实际缺陷校准，不把任一值当普遍标准。

## 报告格式契约

`bobflow.py` 的 parser 按下表校验。命令由项目按实际工具链填入 `.bob/config.json`，引擎不自动下载任何东西。

| parser | 输入 | 失败条件 |
| --- | --- | --- |
| junit | 含 testcase 的 JUnit XML | 有失败/错误、零用例、全跳过 |
| coverage | coverage.py JSON 的 totals | 无语句、比例无效、低于 coverage_min |
| crap | 函数数组 `[{id, complexity, coverage, crap}]` | 空数组、无覆盖样本、超 crap_max |
| mutation | `{"mutants":[{"status"}]}` 或 `{"kill_score"}` | 未达 mutation_min、零可评估样本；ignored/unknown 一律不算 killed |
| exitcode | 命令退出码 | 非零；零只证明进程成功，不证明测试真跑过，能上 junit 就上 |

没有对应解析器的语言，先用工具自带的 `--fail-under`/退出码门槛，再留完整报告；不要手搓一个 `passed=true` JSON。

Python 参考命令：`python -m pytest -q --junitxml=...`、`python -m coverage run -m pytest -q && python -m coverage json -o ...`、`radon cc -j .`；CRAP 需要把 radon 函数区间与 coverage 逐函数覆盖配对后输出 crap 契约 JSON。JS/TS 参考命令：`npm test`、jest 的 junit reporter、`npx stryker run` 后转 mutation 契约。

## 验收防止误报

- 运行前后对源码做指纹比较。检查过程修改了产品源码，该轮报告作废。
- `decide` 复查配置、当前代码和报告的时效；报告缺失或陈旧一律 BLOCKED。
- required_checks 必须非空并指向实际启用的检查项。
- 该机制用于发现过期、遗漏和误用，不是能抵御同权限恶意篡改的密码学签名系统。

报告写在 `.bob/reports`，证据包（含各检查日志）写在 `.bob/evidence/<时间戳>-<profile>`。基线失败要同时保留旧版本与当前版本的结果，差分门槛由确定性命令输出比较结果与新增失败集合后接入。

## 防止指标优化损害产品

禁止为变绿删断言、降低覆盖要求、无理由 skip、缩小源码范围、把幸存变异批量标 ignored。反作弊基线会对比断言数、skip 数和门槛值，命中即要求 `docs/bob/waivers/` 下的书面豁免并由用户批准。等价变异需要独立证据（逻辑证明或反例搜索），不会被"看起来像等价"消除。

范围不适用时在实现前调整检查配置并说明理由。存量大项目用改动范围与基线差分逐步提升质量，不在小修复里重构全仓库或追求全仓 100%。

最后检查交付路径：配置脚本、打包产物、导出文件要验证"真实文件可打开/可解压/命令可执行"，README 里的路径文字不构成文件存在的证据。

## 已知的兜不住与缓解

git hooks 可被 `--no-verify` 绕过；完全不触发本流程的直接改码也无法物理拦截。缓解按强度排序：

1. 远程仓库加分支保护 + required checks（唯一不依赖本机配合的硬门）。
2. `pre-push` 门禁跑全量检查，推送前最后拦截。
3. 人工抽查 `decision.json` 与证据包的一致性（对照 timestamps 与指纹）。
