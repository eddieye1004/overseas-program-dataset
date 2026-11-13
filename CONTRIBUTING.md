# 贡献指南 · Contributing Guide

感谢你愿意帮助修正这个数据集。**在提交之前，请务必读完本页。**

贡献有两条路径：

- **只报告一条数据有误**：走「[数据纠错表单](#如何提交数据纠错)」，不需要改仓库；
- **直接改仓库**：按「数据文件结构 → 本地校验 → 提交规范」的顺序来，本页所有命令都标了出处。

---

## 核心原则

> ### 没有官方来源的数据，不予合并。

这是本数据集存在的唯一理由。如果我们允许二手来源，那我们就会变成我们想要消灭的那种信息污染源。

**可作为依据的官方来源：**

- ✅ 目的地国家移民局官网（如 `immi.homeaffairs.gov.au`、`immigration.govt.nz`）
- ✅ 目的地国家驻华使领馆官网
- ✅ 项目官方运营方页面（如 IAESTE 官网、美国国务院 `j1visa.state.gov`）
- ✅ 目的地国家政府法律文本（如德国《居留法》§16e）

**不可作为依据的来源：**

- ❌ 留学 / 移民中介网站
- ❌ 微信公众号、小红书、知乎
- ❌ AI 生成的内容（包括 ChatGPT、Claude 等）
- ❌ 其他攻略博客
- ❌ 维基百科（可作为线索，但必须回溯到原始来源）

---

## 数据文件结构

### 目录里放什么

| 路径 | 放什么 | 能否手改 |
|---|---|---|
| `data/programs/*.json` | 每个项目一份 JSON，是全部数据的**唯一事实源**。文件名 `{国家代码}-{项目简称}.json`，应与 `program.id` 一致 | ✅ 要改数据就改这里 |
| `data/schema.json` | 字段定义（机器可读）。`validate.py` 按同一套规则校验 | ✅ 改字段时要同步 `scripts/validate.py` 与测试 |
| `data/sources.md` | 全部官方来源清单，由 `scripts/gen_sources.py` 从各项目 `sources[]` 生成 | ❌ 脚本生成，手改会被 CI 打回 |
| `data/tracking.json`、`data/FRESHNESS.md` | 复核台账（机器读 / 人读），由 `scripts/track.py` 生成 | ❌ 脚本生成 |
| `data/calendar.json` | 窗口日历，由 `scripts/build_calendar.py` 生成 | ❌ 脚本生成 |
| `data/match-flags.json`、`data/match-samples.json` | 资格判定的前端契约产物，由 `scripts/match_readiness.py --emit` 生成 | ❌ 脚本生成 |
| `data/review-policy.json` | 复核周期的唯一来源 | ✅ 改周期改这里 |
| `web/` | 中英双语静态站；`pnpm run sync:data` 从根 `data/` 生成前端数据与 `web/public/p/*.html` | 按代码贡献流程改 |

> **关于 `data/sources`：** 本仓库没有 `data/sources/` 目录。每个项目的来源直接写在该项目 JSON 的 `sources[]` 数组里；`data/sources.md` 只是 `scripts/gen_sources.py` 汇总出来的展示清单，不是另一份可以单独编辑的数据。

### 一条项目记录包含哪些字段

以 `data/schema.json` 和 `data/programs/` 下的现有文件为准。顶层**必填 8 项**：

`schema_version` · `program` · `eligibility` · `timeline` · `documents` · `steps` · `sources` · `last_verified`

| 顶层字段 | 作用 | 关键子字段 |
|---|---|---|
| `schema_version` | 固定为 `"0.1.0"` | — |
| `program` | 项目身份信息 | `id`、`name`、`name_en`、`country`、`country_code`、`region`、`program_type`、`official_url`；可选 `visa_code`、`authority`、`summary`、`tags`、`active` |
| `eligibility` | 资格条件（判定的核心） | `passport_types`、`age`、`education`、`language`、`funds`、`other_requirements` |
| `timeline` | 申请窗口、配额、费用 | `mechanism`、`quota_status`、`quota`、`quota_note`、`schedule`、`windows`；可选 `fees`、`processing_time` |
| `documents` | 所需材料 | 每项必填 `name`、`required`；可选 `note`、`prepare_days` |
| `steps` | 申请步骤 | 每项必填 `step_no`、`title`、`description`；可选 `duration`、`official_link` |
| `sources` | 官方来源，至少 1 条 `primary` | 每条必填 `type`、`name`、`url`、`last_verified`；可选 `publisher`、`verified_by`、`claim` |
| `last_verified` | 这条记录最后被核实的日期，`YYYY-MM-DD` | — |

可选顶层字段：`work_conditions`（持证后的工作 / 学习限制）、`risks`（风险提示）、`verified_by`（核实人 GitHub 用户名）。schema 设了 `additionalProperties: false`，不要自造字段。

两条最容易写错的规则：

- **配额四态**（`timeline.quota_status`）：`capped` 必须同时给 `quota` + `quota_basis` + `quota_source`；`no_quota` / `not_published` 必须给 `quota_source`；`unverified` **不得**填 `quota_source`。`quota` 的口径固定为「中国大陆护照适用的年度名额」，其他护照的数字写进 `quota_note`。
- **窗口确定性**（`timeline.schedule.date_confidence`）：`confirmed` 才允许带具体 `open_date` / `close_date`；`inferred` 与 `unknown` 不得带具体日期，推断依据写进 `cycle_note` / `note`。

### 数据格式要求

- 文件编码：UTF-8
- JSON 缩进：2 空格
- 字符串引号：双引号
- **不得包含注释**（JSON 标准不允许）
- 金额字段统一用对象：`local_amount` + `currency`（必填），`cny_estimate` 可选

---

## 如何提交数据纠错

1. 直接打开 [数据纠错表单](https://github.com/eddieye1004/overseas-program-dataset/issues/new?template=data-correction.yml)
   （站点任意页脚也有「发现数据有误？提纠错」入口，链接到同一张表单）
2. 按表单填写。**必填**：哪个项目、哪个字段、当前数据是什么、正确说法是什么、官方来源 URL、你核实该信息的日期；
   来源发布机构、你是怎么核实的可以留空。
3. 若问题不属于任何单一项目，选「不属于下面任何一个 / 多项目」，在说明里列全。

纠错表单的字段定义在 `.github/ISSUE_TEMPLATE/data-correction.yml`，可直接对照。

---

## 如何新增一个项目

1. Fork 本仓库
2. 在 `data/programs/` 下新建 JSON 文件，命名规则：`{国家代码}-{项目简称}.json`
   - 例：`au-462-work-holiday.json`、`nz-china-whv.json`
   - `program.id` 应与文件名（去掉 `.json`）一致；不一致时 `validate.py` 会告警
3. 严格按照 [`data/schema.json`](data/schema.json) 的字段定义填写；`program.id` 在整库唯一
4. **每条资格判定都要能指向 `sources[]` 中的一条 `primary` 来源**，并用 `claim` 写明它佐证了哪条信息
5. 本地运行校验与测试，见下一节「本地校验与测试」
6. 提交 Pull Request，并按 `.github/PULL_REQUEST_TEMPLATE.md` 填写「官方来源」表：来源 URL、发布机构、核实日期、佐证的字段

---

## 字段填写规范

### `last_verified`（核实日期）

- 格式：`YYYY-MM-DD`
- 含义：你**亲自核实**该条信息的最新日期
- **不要填项目的发布日期，填你确认它准确的那一天**
- CI 运行在 UTC；本地日期比 UTC 快 1 天以内不会报错，超前超过 1 天会被判为「核实日期在未来」

### `sources`（来源）

每个项目至少包含 1 条 `primary`（官方一手）来源：

```json
"sources": [
  {
    "type": "primary",
    "name": "China Working Holiday Visa",
    "url": "https://www.immigration.govt.nz/visas/china-working-holiday-visa/",
    "publisher": "Immigration New Zealand",
    "last_verified": "2026-10-30",
    "verified_by": "eddieye1004",
    "claim": "中国大陆 WHV 的年龄、学历、语言、资金与名额要求"
  }
]
```

- `type` 只能是 `primary` / `secondary`；`secondary` 只能当线索，最终依据必须是 `primary`
- `claim` 要写清这条来源**具体**佐证了哪条信息，不要只写「官方页面」
- `timeline.quota_source` 必须与本项目 `sources[]` 中某条 `primary` 的 `url` 完全一致，否则 `validate.py` 报错
- `validate.py` 会按域名给来源分级：中介、自媒体、攻略博客（D 级）直接报错；标注为 `primary` 但不是政府 / 项目官方域名的会告警

### `passport_types`（护照类型）— **最关键字段**

值不是布尔值，而是四态枚举：`eligible`（可申请）/ `not_eligible`（不可申请）/ `conditional`（有条件）/ `unknown`（未核实）。

```json
"passport_types": {
  "mainland_china": "eligible",
  "hong_kong_china": "not_eligible",
  "taiwan_china": "not_eligible"
}
```

- `mainland_china` 必填；`hong_kong_china`、`taiwan_china` 建议也显式写出

> ⚠️ **请格外小心这个字段。** 中文互联网上最常见的错误，就是把中国台湾 / 中国香港的资格误写成「中国」。
> 如果你不确定，请填 `unknown`，**不要猜**，并在 Issue 里提出来讨论。

### 枚举值

请只使用 `schema.json` 中定义的枚举值。校验脚本会拒绝非法值。

---

## 本地校验与测试

以下命令都来自仓库现有脚本或 CI 配置，出处已逐条标注。

- Python 3.11（CI 版本）；校验器与测试只用标准库，不需要 `pip install`
- 网页部分需要 Node 20 + pnpm 9
- 仓库文档统一写 `python`；如果你的系统只有 `python3`，把命令里的 `python` 换成 `python3` 即可

### 提交前必跑（与 CI 使用同一批脚本）

| 命令 | 作用 | 出处 |
|---|---|---|
| `python scripts/validate.py` | 校验 `data/programs/*.json` 的结构与业务规则；PR / push 用 | `.github/workflows/validate.yml`「校验数据完整性（离线）」；`scripts/validate.py` 文件头 |
| `python scripts/validate.py --strict` | 警告也视为失败（CI 只在定时任务用；本地提交前建议跑，确保零告警） | `.github/workflows/validate.yml` 的 `STRICT_ON_SCHEDULE`；`scripts/validate.py --strict` |
| `python -m unittest discover -s tests -v` | 校验器、复核台账、issue 同步等 Python 测试 | `.github/workflows/validate.yml`「运行单元测试」；各 `tests/test_*.py` 文件头 |
| `python scripts/gen_sources.py --check` | `data/sources.md` 必须与 `data/programs/*.json` 一致 | `.github/workflows/validate.yml`「来源清单必须与数据一致」；`scripts/gen_sources.py` 用法 |
| `python scripts/match_readiness.py --check` | `data/match-flags.json`、`data/match-samples.json` 必须与数据一致 | `.github/workflows/validate.yml`「匹配判定产物必须与数据一致」；`scripts/match_readiness.py` 用法 |
| `python scripts/track.py --check` | 复核台账不能有过期记录（定时任务硬闸门） | `.github/workflows/validate.yml`「复核到期必须被看见」；`scripts/track.py` 用法 |

### 按需 / 本地辅助

| 命令 | 作用 | 出处 |
|---|---|---|
| `python scripts/validate.py --check-links --timeout 20` | 检查官方链接是否存活（需要网络；CI 里为 `continue-on-error`，不阻断） | `.github/workflows/validate.yml`「检查官方链接存活」 |
| `python scripts/validate.py --json > validate-report.json` | 生成 JSON 校验报告（CI 归档用） | `.github/workflows/validate.yml`「生成 JSON 报告」 |
| `python -m pytest -q` | README「本地校验」列出的测试入口；CI 实际跑的是上面的 unittest，pytest 需自行安装 | `README.md`「本地校验」 |
| `node web/scripts/smoke-test.mjs` | 前端纯逻辑断言；需先在 `web/` 执行 `pnpm install` | `README.md`「本地校验」；CI 对应 `.github/workflows/pages.yml`「Unit checks」（在 `web/` 下跑 `node scripts/smoke-test.mjs`） |
| `cd web && pnpm install --frozen-lockfile && pnpm exec tsc -b --force` | 网页 TypeScript 类型检查 | `.github/workflows/pages.yml`「Typecheck」 |
| `cd web && pnpm exec vite build` | 构建网页静态产物 | `.github/workflows/pages.yml`「Build」 |
| `python scripts/sync_issue.py --dry-run` | 预览将要写进复核 issue 的正文（不调 API） | `README.md`「本地校验」；`scripts/sync_issue.py` |

### 改了数据后要重新生成的产物

生成物必须和源数据放在**同一个 commit** 里提交。`data/sources.md` 与 `data/match-*.json` 有 CI 一致性闸门（`--check`）会逐字比对；`data/tracking.json`、`data/FRESHNESS.md`、`data/calendar.json` 目前没有逐字比对，但站点和台账会直接读旧值，改完数据仍要手动重生成并提交。

| 改动 | 还要运行 | 产物 | 出处 |
|---|---|---|---|
| `data/programs/*.json` 里的来源 / 字段 | `python scripts/gen_sources.py` | `data/sources.md` | `scripts/gen_sources.py` 用法；CI `--check` |
| 核实日期、配额 | `python scripts/track.py` | `data/tracking.json`、`data/FRESHNESS.md` | `scripts/track.py` 用法；CI 定时任务 |
| `timeline.windows` / `timeline.schedule` | `python scripts/build_calendar.py` | `data/calendar.json` | `README.md`「本地校验」；`scripts/build_calendar.py` 文件头 |
| 资格判定字段 | `python scripts/match_readiness.py --emit` | `data/match-flags.json`、`data/match-samples.json` | `scripts/match_readiness.py` 用法；CI `--check` |
| 项目数据（影响站点详情页） | `cd web && pnpm install && pnpm run sync:data` | `web/public/data/*`、`web/public/p/*.html`、`web/public/sitemap.xml` | `web/package.json` 的 `sync:data`；`.github/workflows/pages.yml`「Sync data from repo JSON」 |

---

## 提交规范

以下约定来自仓库既有提交历史（`git log --oneline`）与 `.github/PULL_REQUEST_TEMPLATE.md`。

### commit 粒度

- **一个 commit 只做一件可独立描述的事**：一次数据修正、一个功能、一次文档更新，不要混在一起。
- **数据变更与其派生文件放同一个 commit**：改完 JSON 后重生成的 `sources.md`、`tracking.json`、`FRESHNESS.md`、`calendar.json`、`match-*.json`、`web/public/...` 一并提交，保证单独检出这个 commit 时 CI 的 `--check` 也能过。
- 代码、数据、文档的变更尽量拆成不同 commit；纯格式调整也可以单独一个。
- 提交前先跑本页「本地校验与测试」里的必跑命令，别让 CI 替你发现低级错误。

### commit message

仓库历史基本沿用 Conventional Commits 形式：

```text
<type>(<scope>): <中文简述>
```

- 常见 `type`：`feat`、`fix`、`docs`、`test`、`chore`、`ci`；历史里也出现过 `audit`、`i18n`
- 常见 `scope`：`data`、`web`、`match`、`audit`、`changelog` 等；也可以省略
- 近期提交的简述以中文为主
- 历史实例：`feat(data): 补两条毕业后通道——爱尔兰 Stamp 1G 与澳洲 485 职业教育类别（39 → 41）`、
  `fix(data): ...`、`docs: ...`
- 简述写「改了什么、为什么」，不要只写 `update` / `fix bug`

### 来源引用要求

- 每一条资格判定（能否申请、年龄、学历、语言、资金、配额、费用、窗口等）都必须在 `sources[]` 里有可核对的 `primary` 来源，并用 `claim` 写明该来源具体佐证哪条信息。
- 来源引用落在**数据的 `sources[]` 和 PR 描述**里，不要求在 commit message 里贴 URL；但 commit message 要让人看出改了哪类数据、依据是什么。
- `secondary` 只能当线索，最终依据必须是 `primary`；中介、公众号、小红书、知乎、AI 生成内容、攻略博客不得作为依据。
- `last_verified` 填你亲自打开官方页面核实的那天（`YYYY-MM-DD`），不是项目发布日，也不是来源页上写的日期。
- PR 描述按 `.github/PULL_REQUEST_TEMPLATE.md` 填「官方来源」表：来源 URL、发布机构、核实日期、佐证的字段；没有一手来源的字段不要提交。

---

## Pull Request 检查清单

提交前请确认：

- [ ] 每个新增 / 修改的字段都有官方来源支撑，`sources[]` 里至少 1 条 `primary`
- [ ] `last_verified` 已更新为亲自核实的日期
- [ ] `python scripts/validate.py` 通过，且 `python scripts/validate.py --strict` 零告警
- [ ] `python -m unittest discover -s tests -v` 通过
- [ ] 改了数据：`python scripts/gen_sources.py --check`、`python scripts/match_readiness.py --check` 通过，相应生成物已提交
- [ ] 改了网页：在 `web/` 下先 `pnpm install`，再跑 `pnpm exec tsc -b --force`、`node scripts/smoke-test.mjs`、`pnpm exec vite build`，全部通过
- [ ] 没有使用二手来源作为依据
- [ ] 护照类型（`passport_types`）填写准确，不确定就填 `unknown`，不猜测
- [ ] PR 描述中说明了修改原因、来源，并填好 `.github/PULL_REQUEST_TEMPLATE.md` 的来源表

> 改动 `CONTRIBUTING.md` 本身也会触发 `validate.yml`（其 `paths` 包含该文件），所以文档 PR 同样会跑数据校验与测试。

---

## 行为准则

- 讨论对事不对人
- 对政策有不同理解时，**以官方文件为准**
- 如果你的信息被指出有误，请冷静核对，而不是争辩

---

感谢你让这个数据集更准确。你修正的每一个字段，都可能帮某个学生避免一次代价高昂的误判。
