# 游学类（language course / study abroad）来源规则决策

- 日期：2026-11-01
- 触发：`expansion-strategy-20261031-v1.md` 阶段 2「游学类的来源规则决策（2 周，决策 + 试点）」
- 当前状态：**待决策**。本文件只给证据与建议，不改任何数据。

---

## 一、先纠正上一轮的一个错误判断

`expansion-strategy-20261031-v1.md` 里写过「游学类没有政府官方页」。**这句是错的。**

英国为「6–11 个月纯英语课程」专门设了一张签证，2026-11-01 已核实并收录为第 12 个项目
（`data/programs/uk-short-term-study-visa.json`，`https://www.gov.uk/visa-to-study-english`）。
它的资格页、课程页、材料页、申请页四页全部有官方原文，7 条来源全部 A 级。

爱尔兰也有一条政府页面明确写「English language or a third-level course —— A range of providers
offer English language or higher education courses」（`irishimmigration.ie/coming-to-study-in-ireland/what-are-my-study-options/`，2026-11-01 取到 200）。

所以真正的结论不是「游学没有官方依据」，而是：**游学的签证环节有官方依据，游学的机构与课程本身没有。**

---

## 二、实测：私立机构域名在现有分级规则里全部是 C 级

用 `scripts/validate.py` 的 `classify_source()` 逐条跑（2026-11-01）：

| 域名 | 级别 | 说明 |
|---|---|---|
| ef.com | C | 语言学校 |
| kaplaninternational.com | C | 语言学校 |
| studygroup.com | C | 教育集团 |
| bellenglish.com | C | 语言学校 |
| stgiles.co.uk | C | 语言学校 |
| ilsc.com | C | 语言学校 |
| ecenglish.com | C | 语言学校 |
| study-abroad.cn | C | 中介站 |
| liuxue.com | C | 中介站 |
| igo.cn | C | 中介站 |
| ox.ac.uk | C | 大学官网（现状分级里没有 ac.uk） |
| ucl.ac.uk | C | 同上 |
| gov.uk | A | 对照组 |
| canada.ca | A | 对照组 |
| j1visa.state.gov | A | 对照组 |

`OFFICIAL_GOV_FRAGMENTS` 现有 23 条，`OFFICIAL_ORG_FRAGMENTS` 只有 4 条
（`iaeste.org` / `iaeste.at` / `iaeste.de` / `aiesec.org`）。

两个发现：

1. **机构与中介同级**。EF、Kaplan 这类正规语言学校和「留学中介站」在现有规则里都是 C，规则分不开二者。这不是漏配白名单，是分级维度本身不评价「机构是否合法办学」。
2. **`ox.ac.uk` 也是 C**。说明现规则对「高校官网」整体没有覆盖。这一条与游学无关，但会影响任何以后想引用大学页面（例如「实习是否算学分」）的记录。

---

## 三、三个选项与证据

### A. 不收录游学，站内明说只收有政府官方依据的项目

- 现状：README 第 37 行自述「面向中国大陆护照持有者的**准确资格判定**」，设计原则第 3 条「护照优先」。**没有明写「只收有政府依据的」**，但现有 13 条记录的实际构成就是如此（每条至少 1 条 A 级来源，校验器强制）。
- 代价：覆盖面窄。36 岁以上、在职、不想读书的人，能申的只有 3 条。
- 收益：承诺守得住。「每条判定都能点开官方页面对上」是这个库唯一别人抄不走的东西。
- 实现成本：**约 0.5 小时**（写一段收录标准进 README）。

### B. 收录但单列「机构名录」区，标 C 级、不参与资格判定

- 需要新增 `data/directory/*.json`（与 `data/programs/` 分离），`validate.py` 出第二套较松的规则，前端加「名录」标签页。
- 成本：开发 5 天 + 内容 5 天。
- 风险：**名录区会被读者当成资格判定**。一个读者看到「EF 英国语言课程」并据此交钱，出问题时这个库要担的是「你把它列出来了」。
- 缓解（策略文档已写）：每条固定横幅「私立机构，未核实资格；本项目不为其背书」；出现 1 起投诉即整体下线该区。
- 判断：**横幅救不了**。`data/programs/` 里 13 条记录全都有护照资格字段与官方 URL；名录区没有这些字段，读者看到的是同一个站点的另一组卡片。这个库的品牌就是「可核对」，混进不可核对的内容，损失大于收益。

### C. 放宽 `classify_source()` 让私立机构页升 B

- 直接违反「一条数据判定 = 一个官方 URL，二手来源不作依据」（HANDOVER §5.2 第 1 条）。
- 不建议，且不建议讨论。

---

## 四、建议

**选 A**，理由三条：

1. 游学里唯一有官方依据的部分（签证）**已经收录了**（英国短期学习签证）。剩下没有依据的是「哪个学校好、课程值不值」，那不是这个库能回答的问题，硬答就是背书。
2. 选 B 需要一个本库不具备的能力：判断机构是否合法办学。`classify_source()` 连 `ox.ac.uk` 都判 C，让它去判 EF 与中介的区别，是把判断责任塞给一个正则。
3. 「在职可申 3 个」这个数字难看，但这个库的价值恰恰在于它敢说 3。策略文档自己也写了止损口径：*数字不好看时不改文案，改回去说清楚「为什么少」*。

如果选 A，建议同时做两件事（都在 1 小时内）：

- **README 加一段收录标准**，把「只收录有政府官方依据的项目；私立机构与中介不作为来源」写成明文。这是让 A 从「事实」变成「承诺」的那一步。README 措辞按 HANDOVER §5.1 不属于 dsh 职责，需你确认或由你改。
- ~~**`ox.ac.uk` 这类高校域名的分级单独议**~~ —— **2026-11-01 已修**，见下节。

---

## 五、已修：C 级内部再分「高校」与「其他第三方」

`ox.ac.uk` 与 `study-abroad.cn` 在旧规则里都是 C。分级本身不改（两者都不能单独支撑硬性判定），
但「大学官网」与「留学中介站」被写成同一个词，读者没法判断手上这条来源是什么。

改动（`scripts/validate.py`）：

| 新增 | 作用 |
|---|---|
| `ACADEMIC_FRAGMENTS` | `.edu` `.ac.uk` `.edu.cn` `.edu.hk` `.edu.mo` `.edu.tw` `.ac.jp` `.ac.kr` `.ac.nz` `.edu.au` `.ac.at` `.edu.sg` |
| `is_academic_source(url)` | 按**主机名后缀**匹配，不做整条 URL 子串 |
| `describe_source_grade(url)` | `C` → `C-academic`（高校）或 `C`（其他） |
| `grade_label(grade)` | 分级措辞唯一定义处，`gen_sources` 与测试共用 |

**为什么必须按主机名而不是子串**：`.edu` 这个片段的子串会命中 `education.com` 与
`educationaltesting.org`，两个都是商业站。第一版写成 `any(frag in url)`，实测这两个被判成高校官网。

分级结果不变，因此 `validate.py` 的拦截行为没有任何变化（0 错 0 警，仍在）。
变的只有 `data/sources.md` 的分级列与 README 的说明——现在四条 C 级来源里
两条标「C · 高校官网」（`um.edu.mo`、`xaut.edu.cn`），两条标「C · 其他第三方」
（`australia.com`、`opportunitynest.org`）。

测试：`TestSourceGrading` 新增 4 例（12 个 URL 的正反两面 + 分级不变 + 措辞覆盖），
unittest 66 → **70**。

## 六、未核实

| 项 | 状态 |
|---|---|
| 爱尔兰语言课程学生签证的具体要求（时长、资金、可否工作） | 页面正文由 JS 加载，curl 只拿到 2.6KB 骨架，未能取到条款原文 |
| 马耳他语言课程签证 | `gov.mt` 对应页面 403，未取到 |
| 游学的市场规模与需求 | 无公开可信的近 12 个月数据，不做估算 |
