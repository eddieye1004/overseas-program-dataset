# 变更记录 · Changelog

本项目的数据变更遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式。

日期格式：`YYYY-MM-DD`

---

## [未发布]

> 本次首次改动数据文件（新增 5 个项目），版本号按 v0.3.0 记。

### 新增 — 2 个项目：美国 F-1 OPT 与德国 §20 求职居留（2026-11-08）

数据从 18 个项目扩到 20 个：可申 12 → 14、不可申仍为 6，来源 72 → 78 条（A 级 62 → 68）。两项都补的是「留学之后怎么留下来」这一段，此前数据集只覆盖到「怎么出去」和「读完怎么短期留下」，缺英美两国最常用的两条桥。

- `us-f1-opt`（美国 F-1 毕业后工作许可）：12 个月基础 OPT + STEM 专业 24 个月延期，最长 36 个月。核心约束是三个日期（毕业前 90 天起可交、毕业后 60 天截止、DSO 推荐后 30 天内必须交）与失业天数硬上限（90 天，STEM 延期后 150 天）。I-765 费用 $470 在线 / $520 纸质，取自 USCIS 费用表 G-1055（2026-10-26 版）Appendix C——该表只在 PDF 里，网页版 G-1055 页面把 I-765 标为 `Varies`，必须下载 PDF 才能读到具体金额。
- `de-20-job-search`（德国毕业后求职居留）：最长 18 个月，法条明文不可延长。与已有的 `de-chancenkarte`（§20a 机会卡）分成两条记录，因为两者适用人群相反：§20 面向已在德国完成学业者，§20a 面向还在境外、想进来找工作的人。§20 求职期间可做任何工作，§20a 限定技术性就业且每周不超过 20 小时。

**取数教训**：`ind.nl` 的 orientation year 页、`gov.uk/graduate-visa/courses-eligible` 都改成问答式分流或 302 回退，静态 HTML 拿不到条件正文。荷兰毕业后求职居留因此**没有收录**——问答器里的分支条件无法在无浏览器环境下取证，与其凭印象写一条，不如留空。这条记为已知缺口。

### 新增 — 5 个项目（2026-11-03）

数据从 13 个项目扩到 18 个：可申 8 → 12、不可申 5 → 6，来源 51 → 72 条（尾数为后续复核新增的 22 CFR 22.1 与 INZ 英语分数表条目）。

| 新增项目 | 大陆护照 | 官方依据 |
|---|---|---|
| `us-j1-intern` 美国 J-1 实习 | ✅ 可申 | j1visa.state.gov 项目页 + 22 CFR 62.22 |
| `us-j1-trainee` 美国 J-1 培训 | ✅ 可申 | 同上，含 18 个月上限与「不得当作普通就业」的明文 |
| `uk-graduate-visa` 英国毕业生签证 | ✅ 可申 | GOV.UK 概览与资格页，含 2026-12-31 前后 2 年 / 18 个月的差异 |
| `de-chancenkarte` 德国机会卡 | ✅ 可申 | AufenthG §20a / §20b / Anlage 三段法条原文，6 分门槛 |
| `sg-work-holiday-programme` 新加坡打工度假 | ❌ 不可申 | MOM 资格页原文名单只含 10 地，**无 China** |

**为什么收录一条「不能申」的项目**：新加坡 WHP 的项目真实存在、资格页写得很清楚，而中文网络上有不少内容把它写成「大陆护照可申」。一条明确的 `not_eligible` 记录比只列能申的项目更有用。

**`de-chancenkarte` 的取证限制**：`make-it-in-germany.com` 全站被 Radware 反爬挡住（直取返回 115 字符中间页，无头浏览器同样被拦），该页只作为项目存在与官方定位的佐证；所有具体条款以 `gesetze-im-internet.de` 的法条原文为准，并在 `sources[3].claim` 里写明了这一点。


### 复核 — 日本打工度假主源改为可访问取得（2026-11-03）

`jp-working-holiday` 的两条主源（`www.mofa.go.jp/j_info/visit/w_holiday/index.html` 与查証手数料页）此前被 Akamai 全站拦截（curl / 无头 Edge / 无头 Chrome 一律 `Access Denied`，Reference #18.…），只靠 `docs/audit/2026-10-30-ego-independent-verify.md` 的二手记录支撑。本次改用 ego-browser 真实浏览器通道读到原文并逐条核对，三处更正：

- 协议国家/地区数 **32 → 33**（截至 2026-11-01）：新增 Malta、Italy、Panama 三个 2026 年生效的伙伴，名额分别为 100 / 500 / 100。
- 年龄条款范围更正：原文 18-25 的例外国只有 **Australia、Canada、South Korea**，此前记录多列了 Ireland（原文未把爱尔兰列入该句）。
- 页面顶部日期为 **November 1, 2026**，原记录的「截至 2026-04-01」已过期。

中国大陆不含在名单内、台湾 10,000、香港 1,500、[NB2] 两次参与放宽名单等其余结论与原文一致，未改动。同时补齐 7 条译文（`web/i18n-src/chunk-21.json`）并清掉 6 条因措辞变更而失效的旧译文键。

### 复核 — 新西兰 WHV 的英语分数线找回官方出处（2026-11-08）

`nz-china-whv` 的 `eligibility.language` 原先整段标「⚠️ 未核实」，理由是主签证页只写「须能说并理解英语 + 递交后提供 acceptable English language test result」，不列分数，于是把 IELTS 5.5 / TOEFL 46 / PTE 42 / Cambridge 162 这组数字当无据删除。实际这些数字在 INZ 的另一个页面：

- `English language requirements for some working holiday visas` 页里的 `Table 1: Test and minimum score required for the China Working Holiday Visa` 明文列出：`IELTS Overall score of 5.5 or more`、`TOEFL iBT Overall score of 46 or more`、`PTE Academic Overall score of 42 or more`、`B2 First Overall score of 162 or more`、`B2 First for Schools Overall score of 162 or more`、`OET Grade C or higher in all 4 skills`。
- 同页另两条限制：`your result must be no more than 2 years old at the time you apply`、`Tests taken remotely outside of a test centre, such as 'at home' tests are not acceptable.`
- 落盘：`eligibility.language.tests` 补 4 项数值（IELTS / TOEFL_iBT / PTE / Cambridge，`validity_months: 24`）；OET 按单项评级、无总分门槛，不塞进数值表，只在 note 说明。`documents[2]` 的英语成绩单 note 同步。新增一条 primary 来源。
- 顺带修正 `timeline.processing_time`：官方签证页标 `80% within 2.5 weeks`，原记录「2-6 周」无出处，改为官方口径。

**取证教训**：主签证页不列分数，不等于官方没有分数。INZ 把分数集中放在 `english-language-requirements-for-some-working-holiday-visas` 这个横跨多国的对照页里。查签证硬性数字时，除了项目主页，还要查该站按主题聚合的对照页。

### 复核 — 美国 J-1 三个项目的签证费改为法规原文（2026-11-03）

`us-j1-intern`、`us-j1-trainee`、`us-j1-camp-counselor` 原先都把签证费记为「未能核实」，理由是 `travel.state.gov` 对本机三个通道（curl / web_fetch / 无头 Edge / ego-browser）全部返回 403 与 Cloudflare 安全验证页。换一条法源后这条不再是缺口：

- 22 CFR 22.1 第 21(a) 项：`Non-petition-based nonimmigrant visa (except E category) $185`。J-1 属非 petition 类非移民签证，按 $185 缴纳。
- 该表是国务院领事收费的法定依据，eCFR 第 22 卷 `latest_amended_on` 为 2026-10-21、`up_to_date_as_of` 2026-10-30（`/api/versioner/v1/titles.json` 实查）。
- 三个文件各新增一条 primary 来源（`https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-22/section-22.1`），`processing_time` 与相关 `risks` 描述同步改写，不再出现「未能核实」的签证费。
- 未改动 SEVIS 费（$220 / $35），该数字来自 ICE 官方费率表，原本就有 A 级来源。

**取证教训**：`travel.state.gov` 的 Cloudflare 挑战连真实浏览器通道也过不去，遇到这类站不要继续换 UA 或加等待，改从同一制度的法规原文取数——签证费在 CFR 里有法定条目，比签证信息页更稳。

### 更正 — J-1 Camp Counselor 的 Sponsor 名单其实可读，此前结论错了（2026-11-08）

2026-11-03 曾把这份名录记为「站点自身表格失效、当前不存在可读的完整名单」。该结论是错的，本轮推翻：

- 原因不是站点坏了，是请求漏了 nonce。该表是 serverSide 分页的 wpDataTables，页面 HTML 里有隐藏字段 `wdtNonceFrontendServerSide_45`（本轮取到的值形如 `3b9baf0750`），POST 时必须一并带上。不带 nonce 直接打 `admin-ajax.php?action=get_wdtable&table_id=45` 才返回 400 / 3 字节。
- 带上 nonce 后一次取到全表：`recordsTotal: 4133`，分页 `start=0..4000`、`length=800` 共六批全部 200，合计 4,133 行，无截断。
- 按 Category 分组：Research Scholar 863 / Short-Term Scholar 833 / Student, College-University 785 / Professor 750 / Specialist 441 / Intern 110 / Trainee 94 / Teacher 72 / Student, Secondary 65 / Summer Work-Travel 37 / **Camp Counselor 26** / Government Visitor 26 / International Visitor 16 / Au Pair 14 / Alien Physician 1。
- Camp Counselor 的 26 家含 CIEE、InterExchange、Intrax、CCUSA、Camp America（AIFS）、CAMP GROUP、IENA、Alliance Abroad 等。此前「第一页 100 行里没有 CIEE、InterExchange」被当成「只能看到第一页」的证据，实际只是排序不同——这一条推断当时也错了。
- 落盘：`us-j1-camp-counselor` 的 `eligibility.passport_types.note`、`risks[2]`、`sources[5]` 全部重写，`last_verified` 改为 2026-11-08。仍未核实的是「哪家有面向中国大陆的报名入口」——名录只登记美国侧法人与其美国地址，不登记海外招募渠道。

**取证教训**：wpDataTables 的 `get_wdtable` 端点在 serverSide + nonce 模式下，无 nonce 的 400 只说明「缺参数」，不说明「表格坏了」。判「站点功能失效」前，先去页面 HTML 里找 nonce / token / hidden input，再下结论。

### 变更 — 学籍身份推导修正（2026-11-03）

`web/scripts/sync-data.mjs` 的 `toIndexEntry()` 原先按「`enrollment_proof.required === true` → `required`」优先判断，把 J-1 Intern 这类「在读**或**毕业 12 个月内」的项目误判成「必须全程保持学籍」。现在先判 `enrolled_or_recent`（`education.note` 同时出现「在读/就读/在校」与「N 年内/已取得/毕业」），再退回 `required`。

影响：`us-j1-intern` 与 `sg-work-holiday-programme` 的 `enrollment_scope` 由 `required` 改为 `enrolled_or_recent`，应届生不会被误判为不合格。

### 变更 — 三处断言不再写死条数（2026-11-03）

- `web/scripts/smoke-test.mjs`：「按地区 oceania = 2」「按类型 working_holiday = 7」改为与数据比对（`countWhere`），加项目不再变红。
- `web/scripts/smoke-test.mjs`：「亚洲 + 不可申 = jp/kr」改为断言组间 AND 生效且 jp/kr 都在结果里，不再要求恰好 2 条。
- `web/scripts/e2e-check.mjs`：「筛不可申 = 5 张」改为 `EXPECT_NOT_ELIGIBLE`，与其他断言一样从 `index.json` 派生。

### 移除 — 过期文档与排查残留（2026-11-03）

删除 5 份文件，均与本数据集无关或数字已过期（备份在 `default-workspace/backup-20261103/repo-cleanup/`）：

- `PUSH_TO_GITHUB.md`（143 行）：2026-10 关于 GitHub 写权限的对话说明，全仓零引用
- `docs/ACCEPTANCE.md`（145 行）：写于 2026-09-17，称「11 个项目」「26 条链接」
- `docs/DSH-TASK.md`（81 行）：任务卡，写「12 文件 / 11 项目」
- `docs/HANDOVER.md`（222 行）：交接基准 `382f590` v0.2.0，写「11 项目 / 41 tests」
- `web/ACCEPTANCE.md`（96 行）：A2 写 `synced 11 programs`、`PASS 76·129`

`docs/audit/` 五份审计报告与 `docs/architecture.png` 保留。

### 变更 — README 重写与 web/README 修数（2026-11-03）

`README.md` 从 203 行压到 176 行：去掉项目缘起的冗长叙事、与正文重复的三处表述、致谢段；新增「数据格式」一节，把 schema 八段与 A/B/C/D 来源分级写成表。统计口径同步为 18 / 12 / 6 / 72（A 62 / B 6 / C 4）。

`web/README.md` 修掉一批过期数字：`11 个 program JSON` → 18、`chunk-1..7` → `chunk-*.json`（现为 21 个分片）、`programs.json 62.5 KB` → 190.2 KB、`index.json 9.0 KB` → 21.0 KB、`i18n.json 623 条 88.1 KB` → 1102 条 300.5 KB、`smoke-test 65 条` → 89、`e2e 84 条` → 148、首屏体积按 dist 实测更新；删掉指向已删 `ACCEPTANCE.md` 的链接。

### 变更 — 来源清单改为从数据生成（2026-10-31）

**问题**：`data/sources.md` 一直手工维护，于是它和数据各说各话。到 2026-10-31 时
清单只列 28 条 URL，而 11 个 program JSON 里已有 38 条；德国 §16e 法条页
（`gesetze-im-internet.de`）与日本査証手数料页（`mofa.go.jp/mofaj/.../02672.html`）
这两个在前几轮复核中确立的**唯一 A 级依据**，清单里根本不存在。头部还写着
「所有来源的最后核实日期为 2026-09-17」，而实际最早 09-17、最近 10-31。

这不是排版问题：`README`、`CHANGELOG`、`docs/HANDOVER.md` 三处都把读者指向这份清单，
按它去核德国或日本的数据会找不到支撑。**一份缺证据的来源清单，比没有清单更糟**——
它让人以为已经核过了。

**修复**：

- 新增 `scripts/gen_sources.py`：从 `data/programs/*.json` 生成 `data/sources.md`，
  按国家分组、每个项目一张表，列出类型/名称/机构/URL/分级/核实日期/覆盖内容。
- **分级列现算**，直接复用 `validate.py` 的 `classify_source()`，避免出现
  「文档说 A 级、校验器判 C 级」这种自相矛盾。
- 概览新增四项统计：来源条目（primary/secondary 拆分）、去重 URL 数、
  最近与最早核实日期、距今最久的来源。基准取「最近一次核实」而非系统当天，
  否则这一行每天变化，CI 会每天红一次。
- CI 增加 `python scripts/gen_sources.py --check`：文件与数据不一致即失败，并打印
  unified diff 与修复命令。
- `tests/test_validate.py` 新增 `TestGeneratedSourcesDoc` 4 例：文件与生成结果一致、
  所有 URL 都出现在清单里、不再有「所有来源核实于某日」的笼统断言、分级列来自校验器。

**验证**：`python scripts/gen_sources.py --check` → `OK（38 条来源）`；
注入一行假数据后 → `FAIL，11 行差异`，退出码 1；`unittest` 62 → **66 例全通过**。

---

### 变更 — 让「时效承诺」真正具备强制力（2026-10-17）

**问题**：`validate.py` 早已实现 `--strict`（有告警即退出码 1），但**从未被任何地方调用**。
于是 `STALE_DAYS = 180` 的过期告警永远只是日志里的一行，CI 始终绿色——
「每条数据标注核实日期、且由 CI 强制」这个核心承诺，实际只强制了一半。

**修复**：`.github/workflows/validate.yml` 的离线校验步骤在**定时任务（cron）**时以
`--strict` 运行。每周一 UTC 01:00 的审计因此必须「零告警」收尾，数据过期会直接把构建
打红并触发失败通知。

**为什么 push / pull_request 不加 `--strict`**：数据变旧属于维护节奏问题，
不该挡住一次与数据无关的文档修改。摩擦要放在正确的那条路径上。

**保留的例外**：链接存活检查继续 `continue-on-error`。目标站点反爬或临时故障会产生误报，
让它阻断构建会迅速摧毁这个信号的可信度。

**连带修复**：`--strict` 生效时，报告正文原先仍打印「结果: 通过」——因为该结论只依据
`errors`，不看 `strict`。结果是 CI 打红、日志正文却说通过，自相矛盾。现已让正文结论与
退出码判定共用同一个 `failed` 计算，并在 `--json` 输出中新增 `strict` 与 `failed` 字段。
这个缺陷是把 `--strict` 接入 CI 之后才具备实际影响的，因此随本次一并修掉。

### 变更 — 为唯一的合并闸门补上测试（2026-10-17）

`scripts/validate.py`（970 行）此前**零测试**，却是唯一的合并闸门。
新增 `tests/test_validate.py`，**38 个用例**，用 `unittest`（标准库，不引入任何依赖）。

设计取舍：重心放在**假阴性**方向——坏数据必须被拦下，而不是好数据不被误报。
闸门漏放的代价比误挡高一个量级。因此多数用例采用**变异注入**：取一份真实数据文件，
注入一种已知违规，再断言校验器必然报错。

覆盖范围：来源分级 A/B/C/D、D 级来源拦截、含糊 `publisher`、缺 A/B 级官方来源、
必填字段与 `null` 值、schema 版本、日期格式、时效边界（含 2026-10 时区事故的回归）、
`not_eligible` 的 critical 风险一致性、以及 CLI 退出码契约。

CI 中该测试**先于**数据校验运行：校验器自身行为错了，它的「通过」就毫无意义。

### 变更 — 依赖更新自动化换用 Dependabot（2026-10-17）

`.github/renovate.json` 已存在，但**从未在仓库上安装 Renovate App**（历史 PR 数 = 0），
是一份死配置 —— 它让「自动化已配置」看起来成立，实际什么都没发生。

改为新增 `.github/dependabot.yml`：仓库内置能力、零第三方授权、覆盖 `github-actions`
生态，且能识别 action 的 SHA 固定版本注释（`# vX.Y.Z`）并同步升级 SHA 与注释。
三个 action 合并为一个 PR，避免每周开三个内容几乎相同的 PR。

`renovate.json` 已移除（内容保留在 git 历史中）。若日后决定改用 Renovate，
应先删除 `dependabot.yml`，否则同一次升级会开出两个 PR。

无需 `pip` 生态配置：`scripts/validate.py` 与 `tests/` 只用 Python 标准库。

`CONTRIBUTING.md` 同步补充测试命令、UTC 日期约定与「零告警」检查项。

### 计划中
- 增加新加坡 Work Holiday Pass 资格核实（大陆护照适用性待确认）
- 增加中国香港 / 中国台湾护照的项目资格对照表
- 增加"申请难度"与"总成本估算"派生字段
- 提供 CSV 导出以便非开发者使用

---

## [0.2.0] - 2026-10-16

### 修复 — 资格判定错误：日本、韩国应为不可申请（2026-10-16）

**问题**：`jp-working-holiday.json` 与 `kr-h1-working-holiday.json` 的 `eligibility.passport_types.mainland_china`
被标记为 `conditional`，护照说明中写为"年度协商制""未在公开名单中明确列出"，README 覆盖表标注"⚠️ 需查当年协议"。

**核实结论（A 级政府来源）**：

- 日本外务省《The Working Holiday Programmes in Japan》：截至 2026-04-01 共 32 个协议国家/地区，
  含中国台湾（10,000）、中国香港（1,500），**不含中国大陆**；中日之间未签订打工度假协议。
- 韩国外交部（在外同胞厅 WHIC）《List of Partner Countries/Regions and Annual Quota》（2026/27 更新）：
  共 30 个国家/地区，含中国台湾（800）、中国香港（1,000），**不含中国大陆**。

**风险**：`conditional` 会让读者产生"可能可以申请"的行动预期。本数据集的核心定位正是消灭"把不对大陆护照
开放的项目写成可申请"这一类错误，因此这两条属于护城河上的直接漏洞。

**修复**：两条记录的判定改为 `not_eligible`，护照说明与 critical 风险改写为确定性结论；
移除无法核实且与官方声明相悖的"指定代招渠道"表述，代之以日本外务省的官方反欺诈声明；
README 覆盖表同步改为 ❌ 不可申请。

### 修复 — 数据时效刷新（2026-10-16）

全部项目 `last_verified` 于 2026-10-16 复核。本批针对活跃窗口项目完成实质更新：

- `au-462-work-holiday.json`：处理时长由"约 4-8 周"修正为官方口径"约 3 个月"；新增 2027-28 财年
  注册窗口条目（日期待公布）。
- `us-j1-summer-work-travel.json`：移除已失效的"2026 年 9 月底前完成报名"建议，改为官方事实
  （无统一报名截止日期，由各 Sponsor 自行设定）；新增对应风险提示。
- `nz-china-whv.json`：新增 2027 年开放窗口条目（待 INZ 公布，预计 2027 年 1 月前后）。
- `jp-working-holiday.json` / `kr-h1-working-holiday.json`：来源核实日期同步更新。

### 修复 — CI 触发范围（2026-09-17）

**问题**：`validate.yml` 的 `paths` 过滤器只覆盖 `data/**`、`scripts/**` 和工作流文件本身。
仓库首次推送及后续所有 push 均**未触发**任何自动运行（实测 `runs total_count = 0`），
手动触发才首次跑通（run #1，`success`）。

**风险**：若贡献者只修改 `README.md`、`CONTRIBUTING.md`、`CHANGELOG.md` 或 `docs/**`，
CI 将被静默跳过。对于以「来源质量由 CI 强制」为核心定位的数据集，任何未被校验的合并
都是护城河的漏洞。

**修复**：把 `paths` 扩展到文档与变更日志，确保所有可能影响数据集可信度的改动都进入校验。

> 注：数据集的 CI 运行成本极低（离线校验数十秒），为省算力而收窄 `paths` 属于负收益优化。

### 修复 — 来源质量（2026-09-17）

**背景**：在一次链接复验中，发现 4 个项目的 `sources` 中混入了 D 级来源（百科、商业博客），
以及 1 处 `publisher` 含糊标注、1 处张冠李戴（韩国 H-1 的来源指向"数字游民签证"文章）。
这直接违背了本项目"每条数据可追溯至官方来源"的核心承诺。

**修复内容**：
- `ca-iec-working-holiday.json` — 删除百度百科来源，替换为 IRCC 官方 `Who can apply` 页
- `uk-youth-mobility-scheme.json` — 删除百度百科来源，替换为 GOV.UK `Youth Mobility Scheme` 资格页
- `kr-h1-working-holiday.json` — 删除指向"数字游民签证"的商业博客来源，替换为韩国官方 WHIC 逐国/地区说明页
- `global-aiesec-global-talent.json` — 删除百度百科来源，替换为 AIESEC 官方 Global Talent 项目页
- `global-iaeste.json` — 修正中国大陆合作机构标注（Archibucks 与 HLG 为 Co-operating Institution，**非** National Committee）
- `au-462-work-holiday.json` — 澳大利亚旅游局页面从 primary 降为 secondary（非移民局官方页）
- `us-j1-summer-work-travel.json` — 合并重复来源，高校来源从 primary 降为 secondary
- `jp-working-holiday.json` — 修正 publisher 与 URL 不符的来源；补充日本官方 2026-02-01 起中国台湾可参与两次的放宽说明

**新增自动化防线（关键）**：
- `scripts/validate.py` — 新增 `classify_source()` 域名分级器与 `_check_sources_quality()` 检查
  - D 级域名（百科/自媒体/商业博客）→ **校验失败，阻断合并**
  - `publisher` 含糊（"公开资料"等）→ **校验失败**
  - 项目全部来源均不足 A/B 级 → **校验失败**
  - 标注 primary 但域名可信度为 C 级 → **告警**
- 反向测试：注入 3 类违规，**3/3 全部捕获，退出码 1**

**分级标准（`data/sources.md` 同步更新）**：
| 级别 | 定义 | 示例 |
|---|---|---|
| A | 目的地国家政府官网、法律文本 | `immi.homeaffairs.gov.au`、`gov.uk`、`mofa.go.jp` |
| B | 项目本体国际组织官网 | `iaeste.org`、`aiesec.org` |
| C | 高校官方部门等可核验机构 | 高校 `.edu.cn` / `.edu.mo` 国际处 |
| D | 百科、自媒体、商业博客 — **禁止使用** | 百度百科、知乎、商业移民博客 |

### 变更 — CI 工具链升级与时区容错（2026-10-16）

**背景**：首次修复推送后 CI 失败（run #7），失败步骤为「校验数据完整性（离线）」。
根因不是数据本身错误——`validate.py` 把"核实日期在未来"判为 error，而 GitHub runner 使用 **UTC**；
维护者在 GMT+8 深夜按本地日期（2026-10-17）记录 `last_verified` 时，UTC 仍是 2026-10-16，
于是被误判为未来日期并 `exit 1`。该陷阱会稳定复现，影响所有在 GMT+8 夜间核实数据的维护者。

**修复**：
- `scripts/validate.py` — `_check_staleness()` 增加时区容错常量 `FUTURE_TOLERANCE_DAYS = 1`：
  超前 1 天以内视为正常的"本地时区 / UTC"偏移，静默通过；超前更多仍判为填写错误。
- `.github/workflows/validate.yml` — 三个 action 升级并按 **commit SHA 固定**（tag 可被移动，指向前者不安全）：

  | Action | 升级前 | 升级后 |
  |---|---|---|
  | `actions/checkout` | `@v4` | `@v7.0.1` |
  | `actions/setup-python` | `@v5` | `@v7.0.0` |
  | `actions/upload-artifact` | `@v4` | `@v7.0.2` |

  动因：CI 日志已明确告警 `Node.js 20 is deprecated`，旧版 action 正被强制运行在 Node 24 兼容垫片上。
  `python-version` 保持 `3.11` 不变——CI 只需覆盖实际支持的最低版本，无理由抬高。

**验证**：以 CI 的 UTC 基准（2026-10-16）回归测试，`last_verified` 记为 10-17 静默通过、
记为 10-18 仍报错、198 天前仍告警；本地 `scripts/validate.py` 通过（0 错误 / 0 警告）。

---

## [0.1.0] - 2026-09-17

### 新增

**核心数据（8 个可用项目）**
- `au-462-work-holiday.json` — 澳大利亚 Work and Holiday Visa (462)
- `nz-china-whv.json` — 新西兰 China Working Holiday Visa
- `jp-working-holiday.json` — 日本 Working Holiday Programme
- `kr-h1-working-holiday.json` — 韩国 H-1 Working Holiday
- `us-j1-summer-work-travel.json` — 美国 J-1 Summer Work Travel
- `de-16e-internship.json` — 德国 §16e 与学业相关实习居留许可
- `global-iaeste.json` — IAESTE 国际技术实习
- `global-aiesec-global-talent.json` — AIESEC Global Talent

**显式排除记录（3 个项目）**
- `ca-iec-working-holiday.json` — 加拿大 IEC（大陆护照不可申请）
- `uk-youth-mobility-scheme.json` — 英国 YMS（大陆护照不可申请）
- `ie-working-holiday-authorisation.json` — 爱尔兰 WHA（大陆护照不可申请）

> 记录"不可申请"的项目是本数据集的重要设计。它帮助用户避免把时间浪费在错误目标上。

**基础设施**
- `data/schema.json` — 6 表数据字段定义（program / eligibility / timeline / documents / steps / sources）
- `data/sources.md` — 官方来源清单
- `scripts/validate.py` — 数据完整性与官方链接存活校验
- `.github/workflows/validate.yml` — 每周自动校验

### 数据来源

所有数据均来自各国移民局官网、驻华使领馆及项目官方页面。
每条数据的 `sources` 字段记录了具体来源 URL 与核实日期（`2026-09-17`）。

### 已知局限

- 日本、韩国打工度假：v0.1.0 时记为"对华年度协商制"，已于 v0.2.0 依两国外交部门官方名单更正为
  **大陆护照不可申请**（中日、中韩之间均未签订打工度假协议）
- 新加坡 Work Holiday Pass 对大陆护照的适用性尚未核实
- 人名币估算金额（`cny_estimate`）按 2026-09 汇率粗略折算，仅供参考
