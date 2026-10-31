# 官方来源清单 · Official Sources

> **本文件由脚本生成，请勿手工编辑。**
> 生成器：`scripts/gen_sources.py`；数据源：`data/programs/*.json`。
> 改来源请改对应的 JSON，然后运行 `python scripts/gen_sources.py`。
> CI 会跑 `python scripts/gen_sources.py --check`，文件与数据不一致即失败。

**核心原则：** 数据集中每一条资格判定，都必须能追溯到下面某个来源。二手来源（中介网站、公众号、AI 生成内容）不作为依据。

---

## 概览

| 指标 | 数值 |
|---|---|
| 项目数 | 11 |
| 来源条目 | 38（primary 33 / secondary 5） |
| 去重后的 URL 数 | 38（另有 11 个 `official_url` 入口） |
| 最近一次核实 | 2026-10-31 |
| 最早一次核实 | 2026-09-17 |
| 距今最久的来源 | `global-iaeste`（2026-09-17，距最近一次核实 44 天） |

每张表里的「分级」列由 `scripts/validate.py` 的 `classify_source()` 现算，不是人工标注 —— 规则见文末。

---

## 澳大利亚

### 澳大利亚打工与度假签证（462类别）

`au-462-work-holiday` · 官方入口 <https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-462>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Work and Holiday visa (subclass 462) | Australian Department of Home Affairs | <https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-462> | A · 政府/法律 | 2026-10-16 | 基本资格（18-30 岁含、指定国家护照、不可携带子女）、停留期 12 个月、签证费 AUD 840（官方页 data-svpattribute 渲染值 AUD840.00）、中国/印度/越南护照持有人须先参加 ballot 并被随机抽中；2026-10-30 复核：AUD 670 为 2026-07-01 前旧价，页面已不含该数字 |
| 2 | primary | Work and Holiday visa (subclass 462) — First Work and Holiday visa | Australian Department of Home Affairs | <https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-462/first-work-holiday-462> | A · 政府/法律 | 2026-10-30 | 首次 462 的资格（be 18 to 30 years old inclusive、apply from outside Australia、not be accompanied by dependent children）、停留 12 个月、签证费 AUD840.00、资金 AUD5,000、中国/印度/越南护照持有人须先经 ballot 抽中、平均审理约三个月 |
| 3 | primary | New Work and Holiday (subclass 462) visa pre-application process | Australian Department of Home Affairs | <https://immi.homeaffairs.gov.au/what-we-do/whm-program/latest-news/new-work-and-holiday-subclass-462-visa-pre-application-process> | A · 政府/法律 | 2026-10-30 | 中国、印度、越南护照持有人必须先参加签证预申请（ballot）并被随机抽中，才能递交首次 462 申请；该页 2026-10-19 更新，正文由前端渲染 |
| 4 | secondary | Working Holiday Visa FAQ（澳大利亚旅游局） | Tourism Australia（澳大利亚旅游局） | <https://www.australia.com/en/youth-travel/working-holiday-visa/faq.html> | C · 可核验机构 | 2026-10-16 | 旅游推广性质的 462 / 417 类别说明与常见问题（非移民局官方页，仅作辅证） |

---

## 加拿大

### 加拿大国际经验计划（IEC 打工度假）

`ca-iec-working-holiday` · 官方入口 <https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec.html>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | International Experience Canada | Immigration, Refugees and Citizenship Canada | <https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec.html> | A · 政府/法律 | 2026-10-29 | IEC 仅对与加拿大签订青年流动协议的国家/地区开放；中国大陆不在协议名单内；2026 IEC season is closed（pools closed）；Processing fees CAN $184.75；Current processing time 6 weeks after you submit all documents and give biometrics |
| 2 | primary | IEC 参与国家/地区名单（Who can apply） | Immigration, Refugees and Citizenship Canada | <https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec/eligibility.html> | A · 政府/法律 | 2026-10-29 | IEC 参与方为与加拿大签订青年流动协议（YMA）的国家/地区；资格条件（护照、年龄 18-35、资金、保险、返程机票、不可带家属） |
| 3 | primary | IEC eligibility by country（各国 Working Holiday 条款与年龄上限） | Immigration, Refugees and Citizenship Canada | <https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec/eligibility/eligibility-by-country.html> | A · 政府/法律 | 2026-10-29 | 官方名单含 Hong Kong 与 Taiwan，不含 China（中国大陆）；Hong Kong—Working Holiday 为 up to 12 months / 18-30 岁 / CAN$2,500 / 只能参加一次；Taiwan—Working Holiday 为 up to 12 months / 18-35 岁 / CAN$2,500 / 只能参加一次；全表 36 个条目中 China 命中 0 |

---

## 德国

### 德国与学业相关实习居留许可

`de-16e-internship` · 官方入口 <https://www.make-it-in-germany.com/en/visa/kinds-of-visa/internship/>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | secondary | Internship visa — Make it in Germany | Federal Government of Germany | <https://www.make-it-in-germany.com/en/visa/kinds-of-visa/internship/> | A · 政府/法律 | 2026-10-30 | 实习签证的基本要求与官方入口 |
| 2 | primary | Apply for a residence permit for a study-related internship EU | Bundesportal (Germany) | <https://verwaltung.bund.de/leistungsverzeichnis/en/leistung/NI/409271867> | A · 政府/法律 | 2026-10-30 | 资格条件（非欧盟高校在读或毕业 2 年内）、最长 6 个月、实习须与专业相关、不得从事雇佣工作、法律依据 §16e AufenthG、费用 EUR 100 |
| 3 | primary | Students' Internship Visa — 德国驻香港总领事馆 | German Consulate General Hong Kong | <https://hongkong.diplo.de/blob/1475188/fbefe8a21616b8939186927e96dceb01/internship-visa-data.pdf> | A · 政府/法律 | 2026-10-30 | 完整材料清单、资金要求 EUR 752/月、保险保额 EUR 30,000、签证费 EUR 75、审理周期 1-2 个月 |
| 4 | primary | Trainee in Germany — EU Immigration Portal | European Commission | <https://home-affairs.ec.europa.eu/policies/migration-and-asylum/eu-immigration-portal/trainee-germany_en> | A · 政府/法律 | 2026-10-30 | Directive (EU) 2016/801 下的培训居留许可条件、培训协议内容要求、最长 6 个月、联邦就业局审批要求、未满 18 岁需监护人同意 |
| 5 | primary | §16e AufenthG — Studienbezogenes Praktikum EU（法条原文） | Bundesministerium der Justiz（德国联邦司法部） | <https://www.gesetze-im-internet.de/aufenthg_2004/__16e.html> | A · 政府/法律 | 2026-10-30 | §16e(2)：居留许可按实习协议期限签发，最长六个月（höchstens jedoch für sechs Monate）；第 3 项：须为申请前两年内取得高校学历，或正在攻读可获高校学历的学业 |

---

## 国际实习平台

### AIESEC 全球人才计划（企业实习）

`global-aiesec-global-talent` · 官方入口 <https://aiesec.org/global-talent>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | AIESEC Global Talent（官方项目页） | AIESEC International | <https://aiesec.org/global-talent> | B · 项目本体组织 | 2026-10-30 | Global Talent 平台定位、岗位领域划分与在招数量（67 个国家/地区、2,000+ 实习岗位）、4 步申请流程、提供签证与落地支持。该页**未**公布年龄、学历、费用、保险要求。 |
| 2 | secondary | AIESEC Global Talent 2026 概述 | Opportunity Nest | <https://www.opportunitynest.org/opportunity/aiesec-global-talent-global> | C · 可核验机构 | 2026-10-30 | 二手概述（2026-10-30 复核原文）：年龄 mainly people between 18 and 30（原文用 mainly，非硬性区间）；学籍条件为「我们查过的德国岗位」的个例——accepted only master's students who stay enrolled for the whole internship, or bachelor's graduates within two months of graduating，**不是全球统一门槛**；Life and health insurance is mandatory；There is no single deadline, internships are posted and filled continuously。该页同时写明 AIESEC's central pages do not mention a programme fee，即连这篇二手来源也未给费用数字，故数据里 700 USD 项目费无法追溯来源、已删除。 |

### IAESTE 国际大学生技术实习交流计划

`global-iaeste` · 官方入口 <https://www.iaeste.org/>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Student FAQs — IAESTE | IAESTE International | <https://iaeste.org/student-faqs> | B · 项目本体组织 | 2026-10-30 | 学历与学籍官方原文（2026-10-30 复核）：To undertake an IAESTE internship you must be enrolled in a degree course relating to the study field of the internship you wish to apply for. Some IAESTE countries require you to have completed 2 years of your course before undertaking an IAESTE internship；学科范围：The vast majority of our internships are in science, engineering and applied arts fields (architecture/design) but we do sometimes have internships relevant to other fields (business, marketing etc.)；时长 six weeks to a year |
| 2 | primary | IAESTE — International Association for the Exchange of Students for Technical Experience（组织介绍页） | IAESTE International | <https://www.iaeste.org/> | B · 项目本体组织 | 2026-10-30 | 组织性质与规模：100+ 国家/地区、1948 年至今累计派出 374,000+ 名学生、2,500+ 志愿者、3,000+ 接收机构；实习带薪（cost of living allowance 至少覆盖住宿、餐饮与本地交通） |
| 3 | primary | Application process — IAESTE Germany | IAESTE Germany | <https://www.iaeste.de/application-process/> | B · 项目本体组织 | 2026-10-30 | 申请流程（Exchange Platform 注册、三份必需文件、账号验证）、英语证书要求（3 年内有效）、Offer 发布节奏（11月/1月/4月国际交流会议） |
| 4 | primary | Outgoing Trainee — IAESTE Austria | IAESTE Austria | <https://www.iaeste.at?p=1254/> | B · 项目本体组织 | 2026-09-17 | 申请三步流程、必需材料（CV/成绩单/在读证明）、免费语言测试、押金 EUR 300、实习带薪且覆盖当地生存成本 |
| 5 | secondary | IAESTE 实习交流计划 — 澳门大学全球事务部 | University of Macau, Global Affairs Office | <https://gao.um.edu.mo?lang=zh-hant&p=7735/> | C · 可核验机构 | 2026-09-17 | 申请资格（全日制在校生、成绩卓越、良好英语）、无申请费、每年 1 月底至 2 月接受申请、大四学生学籍风险提示（高校官方部门来源） |
| 6 | primary | IAESTE in China, HLG（IAESTE 官网合作机构页） | IAESTE A.s.b.l. | <https://iaeste.org/member-countries/china-hlg> | B · 项目本体组织 | 2026-10-30 | 中国大陆在 IAESTE 的合作机构（Co-operating Institution）为 Archibucks 与 HLG 两家，非 National Committee（国家委员会）；官方联系域名 iaeste.learngive.cn |

---

## 爱尔兰

### 爱尔兰打工度假授权

`ie-working-holiday-authorisation` · 官方入口 <https://www.irishimmigration.ie/coming-to-work-in-ireland/what-are-my-options-for-working-in-ireland/coming-to-work-for-more-than-90-days/working-holidays-in-ireland/>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Working holidays in Ireland — Immigration Service Delivery | Immigration Service Delivery, Ireland | <https://www.irishimmigration.ie/coming-to-work-in-ireland/what-are-my-options-for-working-in-ireland/coming-to-work-for-more-than-90-days/working-holidays-in-ireland/> | A · 政府/法律 | 2026-10-30 | WHA 签约国家/地区官方名单、停留期最长 1 年（加拿大 2 年）、Places are limited、中国台湾 400 名额/年、2026 年度申请窗口与审理方式 |
| 2 | primary | Working Holiday Authorisation — Department of Foreign Affairs | Department of Foreign Affairs, Ireland | <https://www.ireland.ie/en/dfa/visas-for-ireland/working-holiday-authorisation/> | A · 政府/法律 | 2026-10-30 | 按国籍分流的递交口径：11 个签约国家/地区各自对应的受理机构（中国香港→驻港总领事馆，中国台湾→ISD，美国→驻美使领馆等） |
| 3 | primary | Working Holiday Authorisation Application 2026（WHAA1 申请表） | Immigration Service Delivery, Ireland | <https://www.irishimmigration.ie/wp-content/uploads/2025/10/WHA-2026-Application-Form-2.pdf> | A · 政府/法律 | 2026-10-30 | 必备材料清单（护照全页复印件、4 张照片、≥4,000 欧元银行流水、12 个月医疗保险、机票）、NT$3,200 代理手续费、12 个月不可延期、无犯罪记录仅以问卷形式采集 |
| 4 | primary | How to make an application — Working Holiday Programme Ireland–Taiwan 2026 | Immigration Service Delivery, Ireland | <https://www.irishimmigration.ie/wp-content/uploads/2025/10/WHP-Taiwan-How-to-make-an-application-English-2026.pdf> | A · 政府/法律 | 2026-10-30 | 年龄 18 至 30 岁（含）、资金双口径（2,500 欧元含机票 / 4,000 欧元不含机票）、须持私人医疗保险 |

---

## 日本

### 日本打工度假签证

`jp-working-holiday` · 官方入口 <https://www.mofa.go.jp/j_info/visit/w_holiday/index.html>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | The Working Holiday Programmes in Japan | Ministry of Foreign Affairs of Japan | <https://www.mofa.go.jp/j_info/visit/w_holiday/index.html> | A · 政府/法律 | 2026-10-29 | 截至 2026-04-01 的 32 个协议国家/地区名单（含中国台湾 10,000、中国香港 1,500，不含中国大陆）、各国年度签发上限、年龄 18-30（澳加韩爱为 18-25，可另议放宽至 30）、资金与返程机票要求、身体健康、未曾取得过日本打工度假签证、申请程序、工作限制（禁止酒吧/夜总会/赌博场所及影响公共道德场所）；[NB2] 两次参与放宽：2024-12-01 加拿大/英国/新西兰/丹麦/奥地利、2025-01-01 德国/爱尔兰/斯洛伐克、2025-10-01 韩国、2026-02-01 中国台湾；中国大陆不在任何放宽名单内 |
| 2 | primary | 査証手数料（日本签证手续费，令和8年6月24日公告） | Ministry of Foreign Affairs of Japan | <https://www.mofa.go.jp/mofaj/toko/visa/tetsuzuki/pagew_000001_02672.html> | A · 政府/法律 | 2026-10-29 | 「領事官の徴収する手数料に関する政令」改正自令和8年7月1日施行；同日以后在外公馆受理的申请，一次有效签证约 15,000 日元、数次有效签证约 30,000 日元（邦货换算）；渡航目的与国籍不同可能免收或金额不同 |

---

## 韩国

### 韩国 H-1 打工度假签证

`kr-h1-working-holiday` · 官方入口 <https://whic.mofa.go.kr/contents.do?contentsNo=39&menuNo=91>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Working Holiday Information Center (WHIC) | Ministry of Foreign Affairs, Republic of Korea | <https://whic.mofa.go.kr/contents.do?contentsNo=39&menuNo=91> | A · 政府/法律 | 2026-10-30 | H-1 签证资格（18-30 岁）、材料清单、申请规则（须在本国申请、一生一次、不可境内转换） |
| 2 | primary | H-1 visa (Working Holiday) — 韩国驻悉尼总领事馆 | Consulate General of the Republic of Korea in Sydney | <https://overseas.mofa.go.kr/au-sydney-en/brd/m_2367/view.do?seq=760608&page=1> | A · 政府/法律 | 2026-10-30 | H-1 签证年龄要求（2026-09-01 起部分国家放宽至 18-35 岁）、工作限制（同一雇主不超过 6 个月）、禁止职业清单、材料清单 |
| 3 | primary | Working Holiday (H-1) Visa Information by Country and Region | Working Holiday Info Center, Overseas Koreans Agency（韩国外交部海外侨胞厅） | <https://whic.mofa.go.kr/contents.do?menuNo=90&contentsNo=38> | A · 政府/法律 | 2026-10-30 |  |
| 4 | primary | 韩国打工度假官方手册（2026-2027，在外同胞厅 Working Holiday Info Center） | Overseas Koreans Agency, Republic of Korea | <https://whic.mofa.go.kr/upload/temp/kr_workingholiday_english.pdf> | A · 政府/法律 | 2026-10-30 | 韩国 H-1 打工度假签证签约国家/地区与年度名额官方名单（2026/27 更新版共 30 个国家/地区，含中国台湾 800、中国香港 1,000）；中国大陆不在名单内 |

---

## 新西兰

### 新西兰打工度假签证（中国名额）

`nz-china-whv` · 官方入口 <https://www.immigration.govt.nz/visas/china-working-holiday-visa/>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | China Working Holiday Visa | Immigration New Zealand | <https://www.immigration.govt.nz/visas/china-working-holiday-visa/> | A · 政府/法律 | 2026-10-30 | 中国大陆 WHV 全部硬条件：年龄 18-30、须为中国公民且常驻中国、申请时须在中国境内、未持过 NZ WHV、高中毕业学历、英语能力、资金 NZD 4,200、全程医疗保险、离境机票或等额资金、品行与健康要求；每年 1,000 个名额；费用 From NZD $770；审理 80% within 2 weeks；停留 12 个月；同一雇主不超过 6 个月；学习或培训合计不超过 6 个月；页面当前状态为 The China Working Holiday Visa is closed。语言部分官方只写：须能说并理解英语、递交后会被要求提供 acceptable English language test result、成绩不得超过 2 年 —— **未列具体分数线，故数据里记为未核实**。 |
| 2 | primary | 2026 opening dates for capped Working Holiday Schemes confirmed | Immigration New Zealand | <https://www.immigration.govt.nz/about-us/news-centre/2026-opening-dates-for-capped-working-holiday-schemes-confirmed> | A · 政府/法律 | 2026-10-16 | 2026 年各国家/地区开放日期与配额（中国大陆 2026-07-02 开放 1,000 个；中国香港 03-19 开放 400 个；中国台湾 05-28 开放 600 个） |

---

## 英国

### 英国青年流动计划

`uk-youth-mobility-scheme` · 官方入口 <https://www.gov.uk/youth-mobility>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Youth Mobility Scheme visa | UK Visas and Immigration | <https://www.gov.uk/youth-mobility> | A · 政府/法律 | 2026-10-30 | YMS 参与国家/地区名单、年龄要求、资金要求 GBP 2,530、停留期 24 个月、费用结构 |
| 2 | primary | Youth Mobility Scheme visa: eligible countries and territories | UK Visas and Immigration (GOV.UK) | <https://www.gov.uk/youth-mobility/eligibility> | A · 政府/法律 | 2026-10-30 | YMS 参与国家/地区名单含 Hong Kong 与 Taiwan，不含 China（中国大陆）；中国大陆护照持有人不在可申请范围内 |
| 3 | primary | Youth Mobility Scheme visa: Documents you must provide | UK Visas and Immigration (GOV.UK) | <https://www.gov.uk/youth-mobility/documents-you-must-provide> | A · 政府/法律 | 2026-10-30 | 无犯罪记录证明仅对安道尔、冰岛、圣马力诺国籍要求；中国香港/中国台湾申请人须提供内政部抽签中签邮件；签证申请费 £340 载于 Overview 页 |
| 4 | primary | Pay for UK healthcare as part of your immigration application | UK Visas and Immigration (GOV.UK) | <https://www.gov.uk/healthcare-immigration-application/how-much-pay> | A · 政府/法律 | 2026-10-31 | 移民健康附加费（IHS）原文：`£776 per year for students, their dependants, and those on a Youth Mobility Scheme visa, for example £1,552 for a 2-year visa`。即 YMS 与 IHS 同价，2 年签证 1,552 英镑。 |

---

## 美国

### 美国 J-1 暑期带薪实习项目

`us-j1-summer-work-travel` · 官方入口 <https://j1visa.state.gov/programs/summer-work-travel/>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Summer Work Travel — BridgeUSA（美国国务院） | U.S. Department of State, Bureau of Educational and Cultural Affairs | <https://j1visa.state.gov/programs/summer-work-travel/> | A · 政府/法律 | 2026-10-30 | SWT 项目规则：Sponsor 须为来自非免签国的参与者提供预先安排并已审查的岗位、须在入境前提供项目手册/24 小时紧急热线/联系人、须告知最低工资与加班义务、须每月与参与者保持联系；含 Program Exclusions 岗位排除清单（不得安排进有损项目声誉的岗位、不得进入需自购库存再销售的销售岗等）；官方另发 2024 Program Date Chart。**该页未公布年龄上限、项目费与审理时长**，官方也无独立的资格子页（/eligibility 为 404）。 |
| 2 | secondary | SWT 项目宣讲通知（西安理工大学国际合作与交流处） | 西安理工大学国际合作与交流处 | <https://oice.xaut.edu.cn/info/1146/2290.htm> | C · 可核验机构 | 2026-10-16 | 中国高校引进该项目的落地口径（18-28 周岁全日制在校本科生/研究生）、费用结构、申请流程、工作时间 6月15日-9月15日（高校官方部门来源，反映中方实际操作） |

---

## 来源可靠性分级

| 级别 | 定义 | 判定依据 |
|---|---|---|
| **A（最高）** | 目的地国家政府官网、法律文本 | `OFFICIAL_GOV_FRAGMENTS`：`.gov` `.gov.uk` `.go.jp` `.go.kr` `canada.ca` `homeaffairs.gov.au` `immigration.govt.nz` `irishimmigration.ie` `ireland.ie` `make-it-in-germany.com` `verwaltung.bund.de` `diplo.de` `gesetze-im-internet.de` `state.gov` `europa.eu` `un.org` 等 |
| **B** | 项目本体国际组织官网 | `OFFICIAL_ORG_FRAGMENTS`：`iaeste.org` `iaeste.at` `iaeste.de` `aiesec.org` |
| **C** | 高校官方部门等可核验机构 | 其余 `.edu.cn` / `.edu.mo` / `.edu.hk` 等，仅作补充说明 |
| **D（禁止使用）** | 百科、自媒体、商业博客、来源不明 | `FORBIDDEN_SOURCE_DOMAINS` |

**本数据集要求：** 每条资格数据至少由 A 或 B 级来源支撑。C 级仅作补充说明。**D 级严禁作为数据来源。**

### 这条规则是自动执行的

`scripts/validate.py` 内置同一个分级器，在 CI 中强制执行：

- 出现 D 级域名（百科、知乎、商业博客等）→ **校验失败，阻断合并**
- `publisher` 填写「公开资料」「网络资料」等含糊表述 → **校验失败**
- 某项目所有来源都不到 A/B 级 → **校验失败**
- 标注 `primary` 但域名可信度为 C 级 → **告警**，提示复核

> 设计动机：本项目的核心承诺是「每条数据可追溯至官方来源」。一旦来源里混入百科或商业博客，这个承诺就自我瓦解了 —— 而这恰恰是本项目要纠正的信息污染问题本身。因此这条规则不靠人工自觉，必须由 CI 拦截。

---

## 如何新增来源

1. 确认来源属于 A 或 B 级
2. 在对应项目 JSON 的 `sources` 数组里添加记录，填 `type` / `url` / `publisher` / `last_verified` / `verified_by` / `claim`
3. 运行 `python scripts/gen_sources.py` 重新生成本文件
4. 运行 `python scripts/validate.py` 与 `python -m unittest discover -s tests`
5. 提交 PR

**不要手工编辑本文件**：CI 的 `--check` 会把它改回来，并让你的 PR 变红。
