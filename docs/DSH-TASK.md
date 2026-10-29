# DSH 任务卡 — overseas-program-dataset

> 本文件给 DeepSeek Harness（dsh）读。WorkBuddy 负责定稿、commit message、CHANGELOG 与 PR 文本；dsh 负责探索、跑校验、改数据、留证据。
> 启动方式：在 dsh 里把工作区设为 `F:\2026-09-17-20-35-22\overseas-program-dataset`，然后说「读 docs/DSH-TASK.md，执行 T1」。

---

## 0. 工作区唯一性（先确认，不确认不干活）

- **唯一活副本**：`F:\2026-09-17-20-35-22\overseas-program-dataset`（`382f590`，与 `origin/main` 同头，实测 2026-10-28）。
- 已废弃副本：`F:\2026-10-16-16-35-46\repo\overseas-program-dataset`（`eefd35f`，其 HEAD 已被活副本包含，无独有提交）。**不要读、不要改、不要从那拷贝文件。**
- 开工前先跑 `git status -sb` 与 `git rev-parse --short HEAD`，HEAD 不是 `382f590` 就停下报告。

## 1. 环境基线（实测 2026-10-28）

| 项 | 值 |
|---|---|
| `python`（默认 PATH） | 3.13.14 — `C:\Users\16256\.workbuddy\binaries\python\versions\3.13.12\python.exe` |
| `F:\python.exe` | 3.14.6 — **该版本的 `openssl_cafile` 指向不存在的 `C:\Program Files\Common Files\SSL\cert.pem`，跑 `--check-links` 会产生 4 条假警报**（详见 `docs/audit/2026-10-28-links.md` §2.1） |
| `python scripts/validate.py` | 通过，12 文件 / 11 项目，0 错误 0 警告 |
| `pytest` | 已安装（2026-10-29）；`python -m pytest -q` → **41 passed, 8 subtests passed** |

任何改动后必须重跑 `python scripts/validate.py`，要求仍为 0 错误。

## 2. 允许 / 禁止

**允许改**
- `data/programs/*.json`（数据内容）
- `scripts/validate.py`、`tests/test_validate.py`（仅当修 bug 或新增检查项，且要先说明为什么）

**禁止改（除非当次明确要求）**
- `README.md`、`CHANGELOG.md`、`CONTRIBUTING.md`、`docs/` 下的文案
- `LICENSE`、`.github/` 下任何文件
- `data/schema.json`（改字段等于破坏下游兼容，必须先单独提方案）

**禁止行为**
- 用二手来源（中介站、公众号、论坛、AI 生成内容）当依据
- 新增没有官方 URL 的资格判定
- 一次提交里混入多个不相关项目的改动
- 自行 `git commit` / `git push`（提交由 WorkBuddy 统一写）

## 3. 首个任务 T1：来源与链接全量审计（只读，不改任何文件）

目标：给出可复现的证据，证明当前数据集的来源质量与链接存活状态。

步骤：

1. `python scripts/validate.py --check-links --json > /tmp/t1-links.json`（网络检查，耗时可能数分钟，允许后台跑）
2. `python scripts/validate.py --strict --json > /tmp/t1-strict.json`
3. 汇总输出到 `docs/audit/2026-10-28-links.md`，结构固定为四段：
   - **汇总**：检查项目数、失败链接数、按国家分组
   - **失败链接**：`program_id | 字段路径 | URL | HTTP 状态 | 错误类型`
   - **降级来源**：非官方域名（按 `classify_source` 的判定）逐条列出，标注它支撑的是哪条资格判定
   - **未能核实**：无法判断的条目单独列出，不并入结论
4. 全程不得修改 `data/` 下任何文件。

验收标准：报告四段齐全；每条失败项都有具体 HTTP 状态或异常类型，不接受"疑似失效"这类表述；每条判断能对应到某次命令输出。

## 4. 后续任务 T2：数据修正与新增（T1 完成后另开）

- 每个项目一个 JSON，字段结构以 `data/schema.json` 为准。
- 每条资格判定必须带 `sources[]` 条目：官方 URL + `last_verified`（YYYY-MM-DD）+ 核实人。
- 官方 = 移民局官网、驻华使领馆、项目官方页面。域名不符的一律标 `secondary` 并在报告里声明。
- 政策类字段（年龄上限、名额、费用、开放日）必须当次联网核实，不得沿用旧值。
- 改动后跑 `python scripts/validate.py` 与 `pytest`（若已装），两者都过才算完成。

## 5. 交付格式（每次回复都按这个来）

1. 一句话结论（做了什么 / 卡在哪）
2. 改动清单：`文件 → 改了什么 → 依据的 URL`
3. 命令与输出：贴关键行，不贴全量日志
4. 未核实项：单列，写清为什么没核到
5. 下一步一个动作

## 6. 与 WorkBuddy 的交接点

dsh 完成后交给 WorkBuddy 的内容：改动清单 + 证据链接 + 未核实项。由 WorkBuddy 负责：
- `CHANGELOG.md` 条目
- commit message（Conventional Commits）
- PR 描述与对外文本（去 AI 痕迹）
- 最终验收（重跑校验、比对 diff 范围是否只含约定文件）
