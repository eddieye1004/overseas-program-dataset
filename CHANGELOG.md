# 变更记录 · Changelog

本项目的数据变更遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式。

日期格式：`YYYY-MM-DD`

---

## [未发布]

### 新增 — 五国毕业后求职居留，补上 C1 的版图缺口（34 → 39，2026-11-11）

C1 那一轮想补法/西/意/北欧，卡在「这五国的打工度假不对大陆护照开放」且官方站取不到正文。这一轮换思路：**收录它们的「毕业后求职居留」**——与已收录的英国 Graduate、爱尔兰 Stamp 1G 同类，且五条都对大陆护照开放、都是资格制。

| 项目 | 国家 | 定位 |
|---|---|---|
| `fr-recherche-emploi` | 法国 | Carte de séjour / VLS-TS « recherche d'emploi / création d'entreprise »：1 年不可续，可带条件工作 |
| `es-busqueda-empleo` | 西班牙 | Autorización de residencia para búsqueda de empleo：最长 24 个月不可延，**期间禁止工作** |
| `it-ricerca-lavoro` | 意大利 | Permesso di soggiorno per ricerca lavoro o imprenditorialità：9–12 个月，Cutro 后脱离 flussi 配额 |
| `fi-look-for-work` | 芬兰 | Residence permit to look for work or start a business：最长 2 年分 3 段，**无限制工作权** |
| `is-job-search-after-graduation` | 冰岛 | 学生居留续签求职：**18 个月**（2026-07-08 修法，旧规 3 年已废） |

- 现 **39 个项目 / 大陆护照可申 32 / 不可申 7 / 134 条来源**（A 123 / B 6 / C 5）。
- quota 四态更新为 **capped 4 / no_quota 32 / not_published 1 / unverified 2**（合计 39）。五条全记 `no_quota`：资格制，无名额与抽签（西班牙、法国、芬兰、冰岛官方明示无配额；意大利 Decreto Cutro 后转换脱离 flussi 配额）。
- 日历覆盖 **confirmed 3 / inferred 2 / unknown 34**（新增 5 条均为 unknown）：五条都无年度固定窗口，申请时点跟着学生许可到期节点走，按 C2 规则不编日期。
- 五条的共同口径写进 `eligibility.passport_types.note`：**国籍不是门槛，前置身份才是**——须在该国完成学位并持当地学生居留。没有一条写成「无条件可申」。

**三个易错点已按事实包落地**

1. **西班牙期间禁止工作**。这是五条里唯一明文禁止的，部委 Hoja 原文 `no se está autorizado a trabajar`，已写进 `work_conditions.note`、`risks[0].critical` 与 README 表格备注。对照：法国允许带条件工作（须与所学相关且月薪税前 > €2,800.53）、芬兰给无限制工作权、意大利凭转换申请回执可工作。
2. **法国命名**。用现行官方名 «recherche d'emploi / création d'entreprise»，并在 `risks` 里显式区分 **APS**（autorisation provisoire de séjour）——APS 是给与法国签有移民流动协议国家的「首次职业经验」通道，不是本条。中文资料里两者常被混为一谈。
3. **冰岛 18 个月**。官方原文 `may now renew their student residence permit for up to 18 months after graduation` 且 `Previously, this was possible for up to three years.` 已在 summary、`work_conditions`、`risks[0].critical` 三处强调旧规已废。

**本次核实的两处成本口径修正**

- 西班牙费用：费项 **2.1.6** 经 BOE Orden PJC/617/2025 原文逐字核对，条目正是 `Autorización de residencia para estudiante para la búsqueda de empleo o para emprender un proyecto empresarial (DA 17.ª L. 14/2013)`，金额 `10,94`——与事实包一致。
- 意大利费用：按事实包记 **€76.46**（卡费 30.46 + 印花 16 + 邮局 30），并在 note 里写明 **€40 贡献金是否收取存在 Questura 口径差异**（若收则合计 €116.46）。已用 portaleimmigrazione 官方费用表逐项核对。

**schema 与校验的小幅扩展**

- `money.currency` 枚举新增 **ISK**（冰岛克朗）：冰岛的生活费与申请费都以 ISK 计价，官方不折欧元。
- `validate.py` 官方域名白名单新增 5 个，均按既有先例（非 .gov 但确为该国唯一官方经办方）：`boe.es`（西班牙国家官方公报）、`portaleimmigrazione.it`（意大利内政部移民门户）、`migri.fi`（芬兰移民局）、`island.is`（冰岛政府门户下的移民局分区）。

**诚实说明核实边界**：西班牙部委页（inclusion.gob.es 返回 `Acceso no permitido`）、意大利 integrazionemigranti 页（HTTPError）、法国 France-Visas 页与芬兰 migri.fi（均被 Cloudflare 挑战页拦截）本次未能逐字复核，相关断言沿用事实包口径并在 `sources[].claim` 里逐条写明「哪一条已实测、哪一条沿用事实包」，没有把未复核的说成已复核。法国与西班牙的费用、冰岛的全部关键条款均已用可读的官方页（service-public F17319、BOE、island.is）独立逐字核对。

**门禁**

- `validate.py --strict` 40 文件 / 39 项目，错误 0 / 警告 0；`pytest -q` **135 passed**；`gen_sources.py --check` OK（134 条）；`track.py` 39 条全在周期内；`tsc -b --force` 通过；`smoke-test.mjs` 128/128；`vite build` 通过；`e2e-check.mjs` 212/212；i18n 覆盖率 100%（本轮新增 258 条译文）。

---
### 变更 — 扩覆盖到 34 个项目 + 窗口日历成为一等公民（2026-11-11）

两件事并行：补版图空白（C1），以及把「什么时候开」从一句备注变成可被机器读的结构（C2）。

**C1 · 新增 5 个项目（29 → 34）**

| 项目 | 国家 | 定位 |
|---|---|---|
| `au-407-training` | 澳大利亚 | 培训签证（407）：先有担保与提名才能递签，最长 2 年 |
| `mt-nomad-residence` | 马耳他 | 数字游民居留：年收入 €42,000、1 年期可续 |
| `sg-s-pass` | 新加坡 | S 准证：面向所有国籍，受雇主配额与劳工税约束 |
| `sg-employment-pass` | 新加坡 | 就业准证：两阶段（薪资 + COMPASS），薪资按年龄分档，2027-01-01 起上调 |
| `dk-working-holiday` | 丹麦 | 打工度假：**仅七个参与国，中国大陆不可申**——收录为排除记录 |

- 现 **34 个项目 / 大陆护照可申 27 / 不可申 7 / 124 条来源**（A 113 / B 6 / C 5）。
- quota 四态分布更新为 **capped 4 / no_quota 27 / not_published 1 / unverified 2**（合计 34）。新增的两个 capped 中，新加坡 S Pass 的 `quota_basis` 记 `concurrent`：它的配额是「雇主在职员工的比例上限」，不是年度发放数，与澳 462、新西兰 WHV 的年度名额是两种口径。
- `validate.py` 的官方域名白名单新增 `nyidanmark.dk`（丹麦移民局）与 `residencymalta.gov.mt`（马耳他居留局）。两者都是该国居留的唯一受理机构，规则与既有 `migrationsverket.se`、`udi.no` 的先例一致。
- 诚实说明缺口：本轮目标是约 11 个，实际只落了 5 个。卡点不是主题判断，是**可达性**——法国（france-visas，Cloudflare 503 挑战页）、西班牙（exteriores.gob.es，403/404）、意大利（esteri.it，Radware 验证码）、芬兰（migri.fi，Cloudflare）、冰岛（island.is，CDN 拒绝）在脚本与真实浏览器两条通道下都拿不到正文；葡萄牙与丹麦虽有打工度假/青年流动通道，但参与国名单不含中国大陆（葡萄牙为阿根廷、澳大利亚、加拿大、智利、日本、新西兰、秘鲁、韩国、美国、乌拉圭；丹麦为七国）。按「宁可少而实，不要多而注水」的纪律，没有为凑数写不可核实的条目。

**C2 · 窗口日历结构化（`timeline.schedule`）**

背景：这套数据后续要长出一个「名额雷达」——盯各项目开放窗口、提前提醒。雷达的前提是数据能区分「官方公布的日期」与「按规律推的日期」，否则会把人叫错时间。所以 C2 不是附属页面，是先补数据结构。

- schema 新增必填字段 `timeline.schedule`，含 `type`（fixed_dates / annual_cycle / rolling / no_window）、`status`、`date_confidence`（confirmed / inferred / unknown）、`open_date`、`close_date`、`cycle_note`、`next_window_hint`、`lead_time_days`。
- **一条硬纪律，由 `validate.py` 强制**：`inferred` 与 `unknown` 不许携带任何具体日期。推断值一律只写 `cycle_note`（往年实际日期序列）与 `next_window_hint`（文字预告）。`annual_cycle` + `inferred` 还必须给出往年序列，否则「规律」二字没有依据。
- 34 个项目全部回填。**覆盖率：确定日期 3 / 规律推定 2 / unknown 29**。三个确定日期是澳 462（2026-06-04～06-25）、英 YMS（2026-07-14～07-16 抽签）、爱尔兰 WHA（2026-11-01 起）；两个推断是日本 WH（每年 4 月下旬与 10 月中下旬两期）与新西兰 WHV（2025、2026 均在 7 月初开放）。
- 新增 `scripts/build_calendar.py` 派生 `data/calendar.json`：每条含提醒日（= 开放日 − `lead_time_days`）、剩余天数、确定性分档。提醒日的算法只在这一处实现，页面与台账都读它，不各算一套。
- 人读视图三处同源：`data/FRESHNESS.md` 新增「窗口日历」一节（由 `track.py` 调用 `build_calendar` 生成，跟着例行流程走）、站点新增 `#/calendar` 页（左侧导航第 3 项）、`data/calendar.json` 机器读。
- 前端 `CalendarView` 把三档做成**硬分区**：官方已公布 / 按规律推断 / 无从判断三块分开渲染，不按日期混排。e2e 有一条断言专门盯这个——推断区块里出现任何 `<time>` 就失败。
- `lead_time_days` 的取值不是拍一个万能数字，而是按材料耗时定：需考语言 60 天、需无犯罪/学历认证/资金流水 30 天、需雇主或担保方先行动 90 天、不适用（对中国护照不开放）取 0 并说明「不给人虚假的准备期」。依据逐条写进 `note`。

**门禁**

- `validate.py --strict` 35 文件 / 34 项目，错误 0 / 警告 0；`pytest -q` **135 passed**（118 + 日历 17）；`gen_sources.py --check` OK（124 条）；`track.py` 34 条全在周期内；`tsc -b --force` 通过；`smoke-test.mjs` 128/128；`vite build` 通过；`e2e-check.mjs` **212/212**（新增 9 条日历断言，侧栏数 6→7 同步）；i18n 覆盖率 100%（本轮新增 299 条译文，分三批补齐）。

---
### 新增 — 仓库门面素材与结构化纠错入口（2026-11-11）

只做仓库内能落盘的部分：推广内容不在本单，GitHub 设置本身也没有改（About / topics / social preview 只能在仓库设置页或 PATCH API 写，本机 keyring 在 session-0 读不到，gh 无法认证）。

**门面素材（B1）**

- 新增 `docs/social-preview.png`（1200×630），由 `web/scripts/social-preview.mjs` 生成。与既有 `web/scripts/og-image.mjs` 分工明确：后者产出 `web/public/og.png` 供站点分享卡片，这张供仓库门面人工上传，两者不共用一个产物路径。
- 图上四个数字（29 项目 / 23 可申 / 117 来源 / 90·180 天复核周期）全部从 `data/programs/*.json` 与 `data/review-policy.json` 派生，不写死。这延续 `og-image.mjs` 里那次事故的教训——硬编码的「11」在项目加到 26 个后还在图上，而图是二进制、grep 不到。标题只用 README 已有口径，未造新卖点。
- README 第一屏补一张四行速览表。原先「29 个项目 / 数据怎么保鲜 / 怎么纠错」要翻到第 77、158、224 行才看得到；现在第一屏就给：规模、复核周期（90/180 天、剩余 25% 提前提醒、每周一 CI）、纠错路径、数据结构。数字全部搬运自仓库已有事实，标注取数日期，未新增任何数字。
- 新增 `docs/REPO-SETTINGS.md`：只写清单不执行。含 About 描述中英两版（各带字符数与取舍）、website（强调必须带结尾斜杠）、topics 终选 10 个（逐个取舍理由，剔掉 `awesome-list`）、social preview 上传说明与重生成命令、标签缺口、其余建议项与三条无登录自检命令。

**纠错入口（B2）**

- `.github/ISSUE_TEMPLATE/data-correction.md` → `data-correction.yml`（GitHub issue form）。旧模板是自由文本框，提上来的 issue 常缺来源、缺字段路径，维护者要来回两三轮；form 用下拉与必填校验把「问不清楚」消灭在提交前。字段：项目（30 项下拉，选项由 29 个 `program.id` + `name` 生成，不是手抄）、项目 id（可选）、问题字段（11 项）、当前数据、正确说法、官方来源 URL、发布机构、核实日期、核实方式、两条提交前确认。其中项目 / 问题字段 / 当前数据 / 正确说法 / 官方来源 / 核实日期为必填。
- 新增 `config.yml`，**保留空白 issue 通道**（`blank_issues_enabled: true`）。理由：三个模板只覆盖具体数据问题，而关于数据集结构、来源分级标准、前端可用性的建议没有合适模板，强迫选一个只会把内容塞进不匹配的模板。代价由 `contact_links` 里「数据纠错（请优先用这个）」的说明承担。
- 站点页脚新增「发现数据有误？提纠错」，直连 `issues/new?template=data-correction.yml`，新窗口打开并带 `rel="noopener noreferrer"`。放页脚而非横幅：不该抢主流程，但必须每页都有——发现错误的那一页往往不是「数据说明」页。中英各一版文案，链接不随语言变。e2e 新增 [28] 一节 9 条断言（template 参数、指向本仓库、`_blank`、`noopener`、中文文案、详情页也有、英文切换后链接不变），总数 193 → 203。
- 顺带发现并记录：三个模板声明的标签 `data-correction` / `broken-link` / `new-program` **在仓库里都不存在**（只有 10 个默认标签）。GitHub 遇到不存在的标签是静默跳过、issue 照建，所以这个缺口一直没被发现，代价是模板声称的分类在 issue 列表里筛不出来。清单里已给出三条标签的 name/color/description。

**门禁**

- `validate.py --strict` 错误 0 / 警告 0；`pytest -q` **118 passed**；`gen_sources.py --check` OK（117 条）；`track.py` 29 条全在周期内；`tsc -b --force` 通过；`smoke-test.mjs` **128/128**；`vite build` 通过；`e2e-check.mjs` **203/203**；i18n 覆盖率 100%。两个 issue 表单 YAML 经 yaml@2 解析核过（id 无重复、required 齐全、下拉 30 项无重复）。
- 线上核验：push 后 `Validate Dataset` 与 `Deploy web` 在 `483e0bd` 均 success；CDP 实测线上站点页脚链接为 `.../issues/new?template=data-correction.yml`、`target=_blank`、`rel="noopener noreferrer"`。GitHub issue 表单页需登录态才能渲染，无登录实测做不到，字段渲染留给 Muse 验收。

---
### 变更 — 配额四态化、复核到期开 issue、待核实清单进台账（2026-11-11）

这一轮不加国家，只把三处「读的人分不清、维护的人也容易忘」的地方定义清楚。

**配额四态（`timeline.quota_status`）**

- 原来的 `timeline.quota` 是「整数或 null」，而 null 同时兼指三件事：无名额上限、官方设限额但未公布、还没查。29 个项目里 26 个是 null——三种完全不同的情况长得一模一样，读者无法据此规划，也排不出待办。
- 改为**必填**的四态：`capped`（有具体配额，须带 `quota` + `quota_basis` + `quota_source`）、`no_quota`（无配额：官方不设上限，或该项目对大陆护照不分配名额）、`not_published`（官方设限额但未公布数字）、`unverified`（尚未核实，不得填 `quota_source`）。分布：**capped 3 / no_quota 23 / not_published 1 / unverified 2**（合计 29）。
- 三条证据纪律写进 `validate.py` 由 CI 拦：① `quota` 口径固定为「中国大陆护照适用的年度名额」，其他护照的数字（台湾 10,000、香港 1,500）留在 `quota_note`，不许塞进 `quota`；② `quota_source` 必须指向本项目 `sources[]` 里已有的 **primary** 来源——凭空指一条 URL 等于造证据，二手来源也不足以支撑「无上限」这种排除性断言；③ 前两态与 `not_published` 必须给来源，`unverified` 必须不给。
- 顺带修正一处自相矛盾：`uk-hpi-visa` 原本挂着 `no_quota_cap` 标签，但官方明说「有年度限额、只是未公布数字」，标签与事实相反，已去掉。另有 15 条 `no_quota` 项目补齐该标签，让前端「无名额上限」筛选不漏。
- `unverified` 的两条是 `at-rwr-card-vhq`（奥地利红白红卡高资质档受《定居与居留法》年度配额约束，但 migration.gv.at 两页均未给数字）与 `de-chancenkarte`（§20a Abs.7 授权可按年限制数量，但截至复核日未见到生效公告）。用 `info` 而非 `warn`：`--strict` 下 warn 会让每周定时任务常红，把真正的「数据超期」淹没。
- **`last_verified` 一律未动**——本轮只是把空值改成显式状态，没有重新核实任何一个项目。
- 前端 `DetailView` 按四态分别渲染，「待核实」用虚线框与「确定没有」在视觉上分开；配额口径 `concurrent` 会注明「同时在册人数上限」而不是年度发放数（新加坡 2,000 属这一类）。索引层透传 `quota_status`/`quota`/`quota_basis`，i18n 补齐 26 条新 note 的英文（覆盖率回到 100%）。

**复核到期开 issue（`scripts/sync_issue.py`）**

- `track.py --check` 能让构建变红，但红由谁看见？GitHub 的失败通知默认只发给最后一个推送者，而定时任务没有人推——于是它每周红一次、红到被无视。新增 `sync_issue.py` 把同一份台账写进一张 issue。
- 幂等靠固定标题 + 固定标签 + 正文 marker：先按标题搜 open issue，有就原地更新，没有才新建；没有待办时自动关闭。`tests/test_sync_issue.py` 里有一条专门断言标题不含日期或 issue 号——那正是「每周刷一张新 issue」的起点。
- 权限最小：workflow 只加 `issues: write`。这一步用 `if: always() && schedule`，叠在「让构建红」之上而不是替代它——最该喊人的时刻恰恰是构建红了的时候。
- 一处自己踩到的坑：判定「该不该存在这张 issue」一开始只看「有没有过期待复核记录」，于是只剩配额缺口、没有过期记录时会把刚建的 issue 立刻关掉。现在由 `has_open_work()` 单独判定，配额缺口也算未完成的活。

**待核实清单进台账（A3）**

- `track.py` 把 `quota_status`/`quota`/`quota_note` 带进 `tracking.json`，新增顶层 `quota_unverified` 数组；`FRESHNESS.md` 新增「待核实的配额」一节，逐条列出缺什么。
- 它是生成物而不是第二份手工文档：跑一次 `track.py` 就跟着数据更新，issue 正文里用的也是同一份数据。

**schedule 触发核查**

- `validate.yml` 的 schedule 本来就写着且写法正确：`cron: '0 1 * * 1'`。用公开 API 核了该 workflow 最近 30 次运行，其中 **2026-11-02 与 2026-11-09 两次 `event=schedule`、`conclusion=success`**。「看起来全是 push」是因为这段时间几乎每天都有推送，cron 记录被挤出了视野。`pages.yml` 没有 schedule，这是对的：它只发布站点，不负责审计。

**门禁**

- `validate.py` 30 文件 / 29 项目，错误 0 / 警告 0（`--strict` 通过）；`pytest -q` **118 passed**（92 + 四态 11 + issue 同步 15）；`gen_sources.py --check` OK（117 条）；`track.py` 29 条全在周期内；`tsc -b --force` 通过；`smoke-test.mjs` **128/128**；`vite build` 通过；`e2e-check.mjs` **193/193**（新增 9 条四态渲染断言）。

---
### 新增 — 复核台账与看板的「下一步」，并把 29 条记录的缺口补上（2026-11-10）

这一轮不加国家，只解决两件让数据集「用起来」比「堆得高」更要紧的事：**数据会过期而没人知道该核哪几条**，以及**用户来了看一眼就走**。

**复核台账（`scripts/track.py`）**

- 新增 `data/review-policy.json` 作为复核周期的唯一来源：窗口写死日期的项目 90 天（一年一开、错过等一年），其余 180 天，剩余 25% 计为「即将到期」。策略写在数据里而不是代码里，理由是改周期不该改代码、也不该让前端另拍一个常数。
- `scripts/track.py` 产出两份：`data/tracking.json`（机器读，每条含上次核实、已过天数、下次到期日、状态）与 `data/FRESHNESS.md`（人读，按紧急度排序的待办）。`--check` 有超期记录即退出码 1。
- `.github/workflows/validate.yml` 加「复核到期必须被看见」步骤：每次都重算台账，**定时任务（每周一）跑 `--check`，超期就红**；push/PR 不阻断，免得一次与数据无关的文档修改被半年前的项目卡住。两份产物一并作为 artifact 上传。此前「陈旧」只是 `validate.py` 一条不落盘的告警，红一次就过去了，没人知道该去核哪几条。
- 边界实测（写进 `tests/test_track.py`，22 个用例）：`classify(180,180)` 返回 `due_soon` 而不是 `overdue`（到期当天不该闪红）；90 天周期的四分之一线向下取整为 22，所以 68 天算「即将到期」、67 天算「在周期内」；`--today 2027-02-15 --check` 恰好三条 90 天周期的项目转红（澳、新、日），证明策略真的生效而不只是打印。

**前端：口径只取一处**

- `sync-data.mjs` 读同一份 policy，给索引每条加 `review_state` / `review_interval` / `review_due` / `review_days_left` 四个字段。`ListView` 删掉本地写死的 `Date.now() - 90 * 86400000`，`AboutView` 删掉本地 `STALE_DAYS = 90`——**两个各自拍一个常数，迟早和台账打架**。
- 「数据说明」页 statbar 从 4 格扩到 5 格（新增「即将到期」），表格加「下次复核」列并标出剩余/超期天数，底部列出「该重新核这些了」的待办清单。

**看板：下一步该做什么**

- 新增 `web/src/lib/nextstep.ts`（纯函数，不 import React，能被 smoke-test 的 esbuild 打包）：把在跟进的项目归成 `close / prep / open / closed / idle` 五态，按紧急度排序，`prep` 由 `windows[].close_date` 减去 `documents[].prepare_days` 之和算出。
- **`closed` 与 `idle` 必须分开**：澳、日、新三国的真实窗口都已关闭，若只认「未来窗口」，它们会全落进 `idle`，界面上与「官方从不公布日期」的项目长得一样——一个该盯下一轮，一个随时可申，混成一态会让用户把两件事搞反。
- 看板顶部新增「今天先做这几件」，取紧急度前 3（跳过 `idle`）；每行右侧标出该干什么。

**数据细化（29 条的缺口）**

- 9 条缺学习时长上限的（`ca-iec`、`jp`、`us-j1-trainee`、`at-rwr-card-vhq`、`sg-work-holiday-programme`、`us-j1-intern`、`de-chancenkarte`、`us-j1-camp-counselor`、`nz-post-study-work`）：官方页面确实不写，**不填一个看起来合理的数字**，改写为「官方未规定持卡期间的学习时长上限，按当地移民局对附带学习的口径确认」。
- 7 条 `documents[].note` 为空补齐（`de-16e` 2 条、`kr-h1` 2 条、`nz-china-whv`、`global-aiesec`、`jp`）。
- `ie-working-holiday-authorisation` 的 risks 从 2 条补到 4 条：补「先办打工度假入境再转身份不成立」与「按护照签发地给额度，名单外的人学历/资金/语言一条都不会被审核」。
- `nz-post-study-work` 仍只有 1 条 primary 来源（全库最薄）。本轮试过补第二条，`immigration.govt.nz` 对 curl/urllib 返回 200 但正文 0 字符（Incapsula 壳），真浏览器打开主签证页也是 0 字符（SPA 未渲染），二级路径大量返回「Page not found — We have made updates to our website」。**没补上是事实，记在这里而不是假装补过。**

**顺手修的一处旧 bug**

- `sync-data.mjs` 的 `ageUnknown` 原本用 `/未核实/` 匹配年龄备注，而 12 个「无年龄限制」项目的备注里有「0-99 表示无年龄要求，**不是「未核实」**」——句中带那三个字，于是全被标成「未核实」，卡片上直接显示「未核实」。改为 `/^⚠️/` 匹配警告前缀后，只剩 `global-aiesec-global-talent` 与 `us-j1-summer-work-travel` 两条真未核实。

**门禁**

- `validate.py` 30 文件 / 29 项目，错误 0 / 警告 0；`gen_sources.py --check` OK（117 条）；`pytest -q` **92 passed**（原 70 + 台账 22）；`track.py` 29 条全在周期内；`sync-data.mjs` coverage 100%（1933 条）；`smoke-test.mjs` **128/128**；`tsc -b --force` 通过；`vite build` 通过；`e2e-check.mjs` **184/184**。

---
### 新增 — 瑞典毕业后求职居留与挪威技术工人居留，29 个项目（2026-11-10）

数据从 27 个项目扩到 29 个：可申 21 → 23、不可申仍为 6，来源 111 → 117 条（A 级 100 → 106）。这两个项目构成一组对照，补上了「北欧怎么去」这个缺口：瑞典给「先入境再找」，挪威只给「先有 offer 再入境」。

**瑞典：毕业后求职居留（`se-look-for-work`）**

- 第二周期学历（`it must correspond to either a 60-credit Master's degree, a 120-credit Master's degree, a professional degree worth 60–330 credits, or a postgraduate/PhD-level degree`）毕业后可申请最长 9 个月，用于找工作或调研创业。
- 硬条件三条：必须在入境前、且人在瑞典境外时递交（`You must currently be located outside of Sweden`）；按月数证明资金，每月 SEK 13,000，9 个月即 SEK 117,000（含回程开销）；综合医疗保险须覆盖急诊与其他医疗、住院、急诊牙科、医疗送返四项。
- 费用 SEK 2,200；官方只给统计不给天数：材料完整的案子 75% 在 5 个月内决定，不完整的 4 个月。
- 期间找到工作可在瑞典境内直接申请工作许可，但**递交前不得上班**（`You are not allowed to start working before you have applied for the new permit.`）。工作许可自 2026-06-16 起要求月薪不低于 SEK 34,470（当月中位薪资 SEK 38,300 的 90%），这条写进了 risks。

**挪威：技术工人居留（`no-skilled-worker`）**

- 三条资格路径：高中层级三年制职业培训（且挪威有对应项目）、大学/大学学院学位、或 6 年以上工作经验走「特殊技能」。岗位须全职或至少 80%。
- 不要求资金证明，改按「薪酬与条件不得低于挪威常规水平」审定（`The pay and working conditions must not be poorer than is normal in Norway.`）。
- 期限：大学学位层级一次 3 年、职业培训层级一次 1 年；满 3 年可申请永居。同类型岗位换雇主免重新申请；失业可留 6 个月但须 7 日内通知警察；不允许远程为境外雇主工作。
- 费用 NOK 6 300（18 岁以下 NOK 3 150）。
- **官方点名中国**：`it may be difficult to obtain a residence permit to work as a skilled worker at a vocational level ... This currently applies in particular to applications for work as a chef, car mechanic, carpenter, painter, bricklayer, or hairdresser where the documentation submitted to attest to educational qualifications or the like were issued in Bangladesh, China, India, Iran, Kosovo, Nepal, Pakistan, Türkiye or Vietnam.` 这句话放进 risks 的第一条（critical），因为它是这条路径对大陆申请人最实际的约束。

**取数与收录判断（本轮踩过的路）**

- **葡萄牙不收录**：`vistos.mne.gov.pt` 的 Skilled Job Seeker Visa 页面写着 `SKILLED JOB SEEKER VISA — NOT YET AVAILABLE AT PORTUGUESE CONSULAR OFFICES — Waiting for the necessary regulation of Article 57-A of the Foreigners' Law.` 法条有、执行未开。收录一个申不了的通道会误导，宁可空着。
- 捷克 `mzv.cz` 与 `ipc.gov.cz`、波兰 `gov.pl/web/udsc/...`（被重定向回门户首页）、丹麦 `nyidanmark.dk`（英文路径大改，子页全 404）、芬兰 `migri.fi`（403）、西班牙/意大利/卢森堡对应页（404）本轮都拿不到可落盘正文。
- **`gov.pl`、`vistos.mne.gov.pt`、`aima.gov.pt`、`migri.fi` 直连一律失败，走 `127.0.0.1:3067` 代理才 200。** 抓取脚本改成 proxy 优先、direct 兜底之后才拿到正文，这条记在这里以免下次重踩。
- `validate.py` 的 `OFFICIAL_GOV_FRAGMENTS` 新增两项：`migrationsverket.se`（瑞典所有居留许可的唯一受理机关）与 `udi.no`（挪威唯一受理机关）。两国的关键操作口径——瑞典的 9 个月上限与工作许可薪资门槛、挪威的 80% 岗位下限与对中国等九国的职业资格警示——都只写在各自移民局站点上，法条不含这些数字。

**文档与长文同步到 29 项目口径**

- `README.md` 覆盖表加 `Look for work or start a business | 瑞典` 与 `Skilled workers | 挪威`；统计句改为「29 个项目，大陆护照可申 23 / 不可申 6，共 117 条来源（A 级 106 / B 级 6 / C 级 5）」。
- `web/index.html` 三处描述、`web/README.md` 七处数字（含 385.6 KB / gzip 116.2 KB、35.9 KB / gzip 9.7 KB、1917 条 656.5 KB / gzip 217.9 KB）、`guides/misinformation.html` 两处全部改到实算值。
- `guides/age-wall.html`：年龄分档重算（16–17 岁 18 个、18–30 岁 23 个、31–35 岁 21 个、36 岁以上 20 个）；「官方明说不限」由 13 个变 15 个，名单补入瑞典与挪威；31 岁以上那张表从 19 行扩到 21 行，瑞典与挪威都标「能」；「剩下 11 个能从大陆直接申请」，其中新增两条代价说明——瑞典要先备 9 个月生活费、挪威要先拿到 offer。
- 新增 `web/i18n-src/chunk-34.json`（118 条），`i18n coverage 100%` / 1917 entries / 656.5 KB。

---

### 新增 — 奥地利红白红卡（高资质通道），27 个项目（2026-11-09）

数据从 26 个项目扩到 27 个：可申 20 → 21、不可申仍为 6，来源 109 → 111 条（A 级 98 → 100）。选奥地利是因为它与德国机会卡构成一组对照：同样是打分制求职通道，一个是「先入境找工作、每周限 20 小时」，一个是「分数门槛更高、但拿到就是可全职就业的 24 个月工作居留」。

**核心规则（全部取自 migration.gv.at 官方页面与官方 FAQ）**

- 100 分制，门槛 70 分。学历分值占大头：四年制以上高等教育 20 分，其中数学/信息学/自然科学/技术（MINT）30 分，博士或教授资格（Habilitation）40 分；上一年在上市公司或经奥地利外贸机构认可的企业任高管的税前年薪 5–6 万欧 20 分、6–7 万欧 25 分、7 万欧以上 30 分；科研与创新活动 20 分、获奖 20 分。
- 工作经验每满半年 1 分，在奥地利的工作每半年 2 分（上限 20）；语言 A1 得 5 分、A2 得 10 分（上限 10，法语/西语/波黑克塞 B1 各 5 分）；年龄未满 35 岁 20 分、未满 40 岁 15 分、未满 45 岁 10 分；在奥地利的学习经历上限 10 分。
- 两条路径：没有工作邀请可先申请 6 个月的找工作签证（D 类，195 欧）；有工作邀请可直接申请红白红卡（申请费 218 欧），也可由雇主在奥地利境内递交。红白红卡一般签发 24 个月，绑定申请时的雇主；换雇主要重新申请，提交后满 45 天可先上岗。
- 按资格条件受雇满 21 个月（过去 24 个月内，由 AMS 核定）后可换红白红卡 plus，获得无限制就业与定居权。
- 官方给的示例值得记：30 岁俄罗斯信息学毕业生，6 年以上经验、英语良好 —— MINT 30 + 经验 12 + 英语 A2 10 + 年龄 20 = 72 分，刚过线。

**取数要点**

- `migration.gv.at` 不属于 `.gv.at` 这个泛域名片段能覆盖的范围，必须在 `scripts/validate.py` 的 `OFFICIAL_GOV_FRAGMENTS` 里点名加入，否则整个项目会因「缺少 A/B 级官方来源」直接校验失败。
- 奥地利把 70 分的积分表、费用、期限全部写在这一个门户站上，法条（NAG / AuslBG）只给框架、不给分值。所以 claim 里引的是门户原文，不是法条原文 —— 这一点与德国的做法相反（德国源自 §20a + 附表）。
- 与德国机会卡的关键差别，写进了 `risks[5].description`：奥地利门槛更高（70/100 对 6 分制），但拿到的是可直接全职就业的 24 个月工作居留，不是每周 20 小时的求职许可。用户在两者之间选择时，这一条比分数本身更能决定取舍。

**文档与长文同步到 27 项目口径**

- `README.md` 覆盖表加 `Red-White-Red Card (VHQ) | 奥地利 | 求职居留 | ✅`；统计句改为「27 个项目，大陆护照可申 21 / 不可申 6，共 111 条来源（A 级 100 / B 级 6 / C 级 5）」。
- `web/index.html` 三处描述、`web/README.md` 六处数字、`web/public/guides/misinformation.html` 两处、`web/public/guides/age-wall.html` 十余处全部改到实算值。age-wall 的年龄分档重算：16–17 岁 16 个、18–30 岁 21 个、31–35 岁 19 个、36 岁以上 18 个；「官方明说不限年龄」由 12 个变 13 个；31 岁以上那张表新增奥地利一行（19 行）。
- 另一处顺手修正：age-wall 第四节原来写「18 个里 10 个要先在该国读过书」，把「当地学历」与「本国学籍」混成一类。改为 7 个要求当地学历 + 3 个卡本国学籍，分开陈述，因为对在职人士这两类的含义完全不同。

**i18n**：新增 `web/i18n-src/chunk-33.json`（59 条），`i18n coverage 100%` / 1799 entries / 602.8 KB。英文译文里不含中文（smoke 有硬断言）。

---

### 新增 — 首访引导、学籍门槛筛选、静态真路径页（2026-11-09）

三件事来自同一批用户反馈：新用户打开就看到一排卡片和一堆筛选筹码，不知道这个站到底回答什么问题。

**1. 首访引导条（`components/Onboarding.tsx` + `lib/onboarding.ts` + `onboard.css`）**

- 全新访客进入任何页面（不止列表页）在页头下方看到一条 44px 高的内联条，一句话：「这里只回答一个问题：大陆护照，你能申哪些？」
- 「展开看怎么用」展开成两列：左列六个模块各自的用途（一行一个「模块 → 你在这里做什么」），右列三步拿到第一条结论（筛资格 → 看详情核年龄学历 → 记进度）。
- 点「跳过」写 `opd.onboarded`（带版本号，升版本会重新提示）；有收藏、有申请进度、填过匹配画像的老用户不打扰。
- 「数据说明」页底部留「重看引导」入口。引导条挂在 App 上、路由切换不重挂载，所以重看靠 `opd:replay-onboarding` 事件通知，只改 localStorage 它读不到。
- 刻意不用 `role="dialog"` / `aria-modal`：它是页面内容的一部分，不该拦截焦点。
- 引导条在时，列表页那句「按国家、地区、项目类型与标签筛选…」自动隐藏（说的是同一件事，两条并存白吃 26px 首屏），其它页的说明保留。

**2. 学籍门槛筛选（`lib/filters.ts` + `components/FilterBar.tsx`）**

- 原来只有「可申 / 不可申」，但「可申」里混着「在职就能申」和「必须在读」两类，用户看不出差别。新增第四个筛选维度，取值直接来自数据里已有的 `enrollment_scope`：不要求学籍 18 / 在读或毕业不久 4 / 须在读 2 / 官方未公布 2。
- 与地区、类型、资格、标签之间是 AND，同维度内多选是 OR；写进 URL（`e=` 参数）可分享。

**3. 静态真路径详情页（`scripts/gen-pages.mjs`）**

- 为 26 个项目各生成一个 `/p/<id>.html`，外加一个 `/p/` 索引页。每页带独立 `<title>`、`<meta description>`、`canonical`、og 全套、`application/ld+json`（`@type: WebPage`，`isPartOf` 指向 Dataset）、要点表、材料、风险、来源清单，以及回交互版的 CTA。
- sitemap 的详情 URL 从 `${SITE}/#/p/${id}` 改成 `${SITE}/p/${id}.html`。依据是 Google 官方文档：「请勿使用片段更改网页内容，因为 Google 搜索通常不支持网址片段」。改之前 sitemap 29 条里有 26 条是片段 URL，等于只有 1 条能被单独收录。
- 整目录每次先清空再重建——删掉一个项目时，旧静态页必须跟着消失。

**顺带修掉一个真 bug**：`sync-data.mjs` 判断「年龄未核实」原来用 `/未核实/` 正则，但 12 个项目的 note 写的是「0-99 表示「无年龄要求」，不是「未核实」」——句中含这三个字，导致 12 个「官方不限年龄」的项目全被标成「未核实」。改成 `/^⚠️/` 前缀判定后，`age_verified=false` 只剩真正未公布的 2 条。

**测试**：smoke 89 → 106（新增学籍门槛四值校验、引导判定 11 条），e2e 148 → 165（新增引导条 21 条，含「收起态 <60px 不顶掉首屏卡片」「刷新不打扰」「重看能叫回来」）。sitemap 断言改为从数据派生 id，并新增反向断言「不再出现片段 URL」。

### 新增 — 装到手机主屏幕（PWA manifest 与图标）（2026-11-09）

站点一直能被搜索引擎收录，但用户在手机上只能靠浏览器书签找回来。这一节补上「装到桌面」的完整链路。

**做了什么**

- `web/public/manifest.webmanifest`：`display: standalone`、`start_url` 与 `scope` 都是 `./`（同一份产物既能跑 `/overseas-program-dataset/` 也能跑根路径）、三个快捷方式指向 `#/`、`#/match`、`#/track`。图标三张：192 any、512 any、512 maskable。
- `web/public/icons/`：`icon-192.png`（2043 B）、`icon-512.png`（5669 B）、`icon-maskable-512.png`（4944 B）、`apple-touch-icon.png`（1893 B，180×180）。由新增的 `web/scripts/pwa-icons.mjs` 用无头 Edge + CDP 截图生成，不引 sharp / canvas —— 仓库里已经有 `og-image.mjs` 这套骨架，多一个原生依赖不值得。maskable 那张图形缩到 52% 是因为系统裁切的安全区只有中间 80%，按 66% 画会被切掉笔画。
- `web/index.html`：补 `manifest`、`icons/apple-touch-icon.png`、`icons/icon-192.png`，以及 iOS standalone 三件套（`mobile-web-app-capable`、`apple-mobile-web-app-capable`、`apple-mobile-web-app-title`）。
- `web/scripts/gen-pages.mjs`：26 个静态真路径页与 `/p/` 索引页同样声明 manifest 与 apple-touch-icon。从搜索结果直接落到 `/p/<id>.html` 的人，不该因为少一行 `<link>` 就装不了。
- `web/package.json` 加 `icons` 脚本。

**没做 service worker（刻意的）**

数据每天都在变，装一个会缓存旧数据的壳比不给装更糟。MDN 的安装条件只要求 manifest + 图标 + `start_url` + `display` + https，离线不是必需项。

**顺手修掉分享图里的过期数字**

`web/scripts/og-image.mjs` 里「收录项目」硬编码成 `11`，项目加到 26 个之后分享图还在说 11。图是二进制，grep 不到，这类错只会出现在别人转发的时候。改为从 `public/data/index.json` 派生（现在显示 26 收录 / 20 护照可申），并把「语言」那格换成「护照可申」，信息量更大。

**测试**：e2e 165 → 179，新增 `[23b] 可安装` 14 条：manifest 是合法 JSON、有 name/short_name、`start_url`/`scope` 为相对路径、`display` 为 standalone、`theme_color` 与页面一致、192/512/maskable 三种图标齐备、四张图标都是真 PNG（比对魔数）、apple-touch-icon 指向 180px PNG、页面有 iOS standalone 声明、静态真路径页也带 manifest 与图标。

---

### 新增 — 荷兰毕业后求职居留（orientation year），26 个项目（2026-11-08）

数据从 25 个项目扩到 26 个：可申 19 → 20、不可申仍为 6，来源 105 → 109 条（A 级 95 → 98）。这是此前记为「已知缺口」的那一条——荷兰的条件正文藏在国籍问答分流器里，静态 HTML 只有一句引导语，浏览器点击又报「元素无法接收输入」，一度判定无法取证。

**突破点**：该分流器是 Drupal 表单，POST 到自身 URL 就能拿到完整条件，不需要浏览器。三个关键参数：`form_build_id`（从页面隐藏字段取）、`nationality_1`（须用国籍自动补全接口返回的 `Chinese (113)`，直接传 `China` 只会得到空数组）、`valid_permit` 与 `expired_permit`。

- 12 个月，不可延长（`You cannot extend the residence permit for the orientation year for highly educated persons.`）。
- 工作完全自由，不需要雇主申请 TWV 工作许可，也可自雇或做独立创业者。
- 两条路：荷兰院校毕业；或境外院校毕业，但院校须在 THE、QS、软科三个发布方中至少两个的前 200，排名以毕业当日为准，学历须经 Nuffic 认证。荷兰这条用的是排名口径而非固定名单，与英国 HPI 的名单制不同。
- 3 年时间窗从毕业或结束研究之日起算；申请费 254 欧元；官方承诺 90 天内作出决定。
- 与德国 §20 的关键差别：荷兰这一类**不要求**资金证明，orientation year 页与「通用要求」页都没有存款门槛。

**同时修正**：`scripts/validate.py` 的 `OFFICIAL_GOV_FRAGMENTS` 加入 `ind.nl`（荷兰执行移民法的唯一中央机构，外交部只管短期申根签）。不加这一条，这个项目会因为「没有 A/B 级官方来源」直接校验失败。

> 本次新增 10 个项目（13 → 18 → 20 → 25），版本号按 v0.3.0 记。

### 新增 — 5 个项目：四条毕业后工签路径与 J-1 研究学者（2026-11-08）

数据从 20 个项目扩到 25 个：可申 14 → 19、不可申仍为 6，来源 78 → 105 条（A 级 68 → 95）。这批补的是「毕业后能在当地留多久、留下来干什么」，四条是同一问题的四个国家答案，加一条 J-1 里唯一允许最长五年的类别。

| 新增项目 | 大陆护照 | 官方依据 | 关键数字 |
|---|---|---|---|
| `au-485-graduate` 澳洲毕业生临时签证 | ✅ 可申 | immi.homeaffairs.gov.au 485 页 + 英语成绩对照页 | 18 个月到 4 年按学位分档，年龄 35 岁或以下 |
| `ca-pgwp` 加拿大毕业后工签 | ✅ 可申 | canada.ca PGWP 页 + 语言要求页 + 专业领域页 | 8 个月到 3 年，CLB 7 / CLB 5 按学位分 |
| `nz-post-study-work` 新西兰毕业后工签 | ✅ 可申 | immigration.govt.nz PSWV 页 | 最长 3 年，须读满 30 周 |
| `uk-hpi-visa` 英国高潜力人才签证 | ✅ 可申 | gov.uk HPI 三页 + 2026 年度全球大学名单 | 2 年（博士 3 年），一次性、不可延 |
| `us-j1-research-scholar` 美国 J-1 研究学者 | ✅ 可申 | j1visa.state.gov 项目页 + 22 CFR 62.20 | 最长 5 年，须连续 |

- `au-485` 的年龄门槛是 2024 年从 50 岁下调到 35 岁的结果，官方原文为 `be aged 35 years or under when you apply. *Exceptions apply`，例外仅限香港/BNO 与印度国籍 AI-ECTA。英语分数 485 资格页只写「需达到 Competent English」不列数字，分数逐个取自专门的语言成绩对照页，已在来源 `claim` 里写明这层关系。
- `ca-pgwp` 的语言要求自 2024-11-01 起生效，大学学位类 CLB 7、学院类 CLB 5，四科都要达标；专业领域要求对本硕博豁免，且官方明说系统不会在材料清单里提示，须自行上传到 Client information。
- `uk-hpi-visa` 的院校名单按年度滚动，2026 年度（2026-11-01 至 2027-10-31）共 82 所，中国大陆 8 所、香港 5 所已逐所列进 `sources[].claim`。`Ecctis will not check if your university is eligible` 这句单独标了风险：花钱做完学历认证也不代表院校在名单内。
- `us-j1-research-scholar` 的三条时间禁令最容易踩：24 个月内完成过 research scholar 不得再参加；12 个月内以任何 J 身份在美停留过不得参加（仅三种例外）；5 年上限连续计算、不可因换项目重开。

**同时把「未能核实」清零。** 原记录里 43 处标着「未能核实」的字段，分两类处理：

1. **官方其实写了的，去把它读出来。** 日本 15 处靠 `koryu.or.jp`（日本台湾交流协会，日台无正式邦交、协会即实质使馆）的三页指南拿到：照片 4.5×3.5 公分、存款证明 8 万台币且须 1 个月内开具、2026 两期窗口 04-20 至 04-30 与 10-19 至 10-30、手续费全免、工作时段无限制。韩国 8 处靠 `whic.mofa.go.kr` 的 2026-2027 官方手册 PDF 拿到：每周 25 小时上限、KRW 300 万存款、KRW 4000 万保额、6 类不得从事的职业、2026 最低时薪 10,320 KRW。
2. **官方确实不写的，改成「官方未规定 + 该向谁确认」。** 剩下的 ca-iec / global-aiesec / global-iaeste / us-j1-camp-counselor / ie / uk-short-term / us-j1-intern / us-j1-trainee / de-20 共 16 处，性质都是「材料规格由各使领馆自定」「项目费由各 Sponsor 自定」，国家级页面本来就不写。这些字段不再留「未能核实」四个字，而是写明边界与确认渠道，**不填一个看似合理的数字**。

**费用与审理时长改用法规原文。** 德国两条把「按常规口径估算」换成 `AufenthV §45` 的 100 欧元（一年以内与超过一年同价）与 `§46` 的 D 类签证 75 欧元；美国 F-1 OPT 的加急费改为 USCIS G-1055（2026-10-26 版）第 28 页的 I-907 数字 1,780 美元。

**两篇长文随之重写。** `web/public/guides/age-wall.html` 从 13 项目口径改为 25 项目口径，并改用实算分布：18-30 岁可申 19 个、31-35 岁 17 个、36 岁以上 16 个；同时新增一节把「31 岁以后还剩 17 个」拆成「9 个必须先在该国读过书」与「8 个能从大陆直接申」，因为后者才是真正的可选项。`misinformation.html` 的 51 条来源同步为 105 条。

**取数教训**：`mofa.go.jp` 对 curl 与无头浏览器一律返回 Akamai `Access Denied`，但同一制度的台湾窗口 `koryu.or.jp` 完全可读——主源读不到时先找同一制度的其他受理方，不要直接判定「官方没写」。`whic.mofa.go.kr` 的 PDF 单次连接会被 reset，需 `curl -C -` 断点续传重试。ego-browser 的 `page.goto()` 返回值没有 `status()` 方法，别去读响应码。

### 复核 — 爱尔兰 WHA 更新到 2027 年度，无犯罪记录由问卷升为资格条件（2026-11-08）

原来的记录停在 2026 年度，ISD 已换版：站点上现在挂的是 `2027-EN_Guidance-Note.pdf` 与 `WHA-2027-Application-Form-November-2026.pdf`，旧的 2026 两份 PDF 直连返回 403。按新版重写了申请窗口、名额口径、材料清单与来源清单。

- 窗口：2027 年度自 2026-11-01 09:00（台北时间）开放，按收件先后受理，前 400 份合格申请在 2027 年初签发；获批者可在 2027-12-31 前任一时点入境开始 12 个月。
- 口径收紧一处：`not have a criminal record` 在 2027 指南里是第 (g) 项资格条件，2026 版只是申请表里的问卷题。`other_requirements` 里该条从 `required: false` 改为 `required: true`，并写明两版的差别。
- 补上原文依据的细节：工作必须是旅行的附带安排（`employment being an incidental, rather than the primary reason for the visit`）、短期课程上限 6 个月（`no longer than six months`）、停留超 90 天须注册缴费、项目本身无申请费（`There is no application fee for participation in this programme`，只有 NT$3,200 代理手续费）。
- 同时修正 `global-iaeste` 两处：`documents` 里的「CEFR C1/C2」与 `steps` 里的同一表述，改为按接收国委员会要求准备——正文早已写明 IAESTE 官方不设等级门槛，材料清单却还留着旧说法。

**取数教训**：`ireland.ie` 的 WHA 页正文全是导航菜单，真正内容（11 个签约国家/地区各自的受理机构）在一张表格里；`irishimmigration.ie` 的 PDF 直连用 curl 会 403，改用 urllib 带 Chrome UA 才拿到 200。判断「页面改版了」不能只看正文里有没有关键词，要对比 PDF 文件名里的年份。

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
