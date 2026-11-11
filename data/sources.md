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
| 项目数 | 39 |
| 来源条目 | 134（primary 128 / secondary 6） |
| 去重后的 URL 数 | 124（另有 39 个 `official_url` 入口） |
| 最近一次核实 | 2026-11-11 |
| 最早一次核实 | 2026-09-17 |
| 距今最久的来源 | `global-iaeste`（2026-09-17，距最近一次核实 55 天） |

每张表里的「分级」列由 `scripts/validate.py` 的 `classify_source()` 现算，不是人工标注 —— 规则见文末。

---

## 奥地利

### 奥地利红白红卡（高资质）

`at-rwr-card-vhq` · 官方入口 <https://www.migration.gv.at/en/types-of-immigration/permanent-immigration/very-highly-qualified-workers/>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Very Highly Qualified Workers（奥地利官方移民门户） | Republik Österreich — migration.gv.at（奥地利联邦政府官方移民门户） | <https://www.migration.gv.at/en/types-of-immigration/permanent-immigration/very-highly-qualified-workers/> | A · 政府/法律 | 2026-11-09 | 两条路径原文：`If you don't yet have a job offer, you can come to Austria on a job-seeker visa, valid for six months, to look for work.`；`To qualify for either the job-seeker visa or the Red-White-Red Card, you must score at least 70 points based on the following criteria`。积分表原文（上限与分值）：`Special qualifications and skills Maximum allowable points: 40`、`Graduation from an institution of higher education, minimum duration of programme: four years 20`、`in the subjects mathematics, informatics, natural sciences or technology (MINT subjects) 30`、`Post-doctoral qualification (habilitation) or PhD 40`、`Work experience (per half-year) 1`、`Six months of work experience in Austria 10`、`German or English language skills for the elementary use of the language on a basic level – (A1 level) 5`、`(A2 level) 10`、`Under 35 years of age Under 40 years of age Under 45 years of age 20 15 10`、`Sum total of maximum allowable points: 100`、`Required minimum: 70`。期限与换卡原文：`The Red-White-Red Card is generally issued for a period of 24 months.`；`if you were employed in accordance with the eligibility criteria for a minimum of 21 months during the preceding 24 months` 可申请 plus。换雇主原文：`may provisionally begin their new employment after a 45-day waiting period from the date the application to change the purpose of the permit ... is submitted`。费用原文：`Jobseeker Visa: € 195 Application fee: € 218`。官方示例原文：`A 30-year old Russian informatics graduate with over 6 years of work experience and very good English language skills ... She receives 72 points`。 |
| 2 | primary | Red-White-Red Card — Frequently Asked Questions（奥地利官方移民门户 FAQ） | Republik Österreich — migration.gv.at（奥地利联邦政府官方移民门户） | <https://www.migration.gv.at/en/service/faq/> | A · 政府/法律 | 2026-11-09 | 找工作签证的性质与失效后果原文：`you may apply for a six-month residence visa for your job search (Job Seeker Visa)`；`If your visa expires before the application process is complete, you can wait for the outcome of the Red-White-Red Card application process in Austria if you submitted the application in person in Austria. Otherwise, you must leave the country and wait for the authorities' decision while abroad`。卡的性质原文：`The Red-White-Red Card is issued in the shape of a bank card and is a combination of residence permit and employment permit. It is valid for two years and entitles you as the holder to settlement and employment with a specific employer.`；换雇主原文：`If you change your employer within the first two years, you have to apply for a new Red-White-Red Card.`。plus 原文：`If you held a Red-White-Red Card for two years, you may apply for a Red-White-Red Card plus`（无限制就业，可随时换雇主）。积分计算器免责原文：`The points calculator is a tool for you to estimate your eligibility ... it does not constitute an application and does not replace the evaluation by the Austrian authorities.` 医疗保险原文：`The authorities will accept travel health insurance, provided it covers costs well above € 30,000 and includes a guarantee covering potential rescue and return costs.` |

---

## 澳大利亚

### 澳大利亚培训签证（407 类别）

`au-407-training` · 官方入口 <https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/training-407>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Training visa (subclass 407)（澳大利亚内政部官方页） | Australian Department of Home Affairs | <https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/training-407> | A · 政府/法律 | 2026-11-11 | 资格清单原文：`Have an approved sponsor`；`Your sponsor must have nominated you for a program of occupational training unless they are an Australian Commonwealth Government agency.`；`We must approve this nomination before you can apply for this visa.`；`Usually, you must be 18 years old or older at the time we decide your visa application.`；`From 12 November 2026, you must be outside Australia when you apply for the visa and when we grant it. Your application will be invalid if you apply while in Australia.`；`You must maintain adequate health cover for the whole of your stay if you are granted this visa.`；停留期 `We might grant you a visa allowing you to stay in Australia for up to 2 years.`；提名费 `AUD170.00 to nominate`；页面最后更新 2026-10-30。 |

### 澳大利亚打工与度假签证（462类别）

`au-462-work-holiday` · 官方入口 <https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-462>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Work and Holiday visa (subclass 462) | Australian Department of Home Affairs | <https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-462> | A · 政府/法律 | 2026-10-16 | 基本资格（18-30 岁含、指定国家护照、不可携带子女）、停留期 12 个月、签证费 AUD 840（官方页 data-svpattribute 渲染值 AUD840.00）、中国/印度/越南护照持有人须先参加 ballot 并被随机抽中；2026-10-30 复核：AUD 670 为 2026-07-01 前旧价，页面已不含该数字 |
| 2 | primary | Work and Holiday visa (subclass 462) — First Work and Holiday visa | Australian Department of Home Affairs | <https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-462/first-work-holiday-462> | A · 政府/法律 | 2026-10-30 | 首次 462 的资格（be 18 to 30 years old inclusive、apply from outside Australia、not be accompanied by dependent children）、停留 12 个月、签证费 AUD840.00、资金 AUD5,000、中国/印度/越南护照持有人须先经 ballot 抽中、平均审理约三个月 |
| 3 | primary | New Work and Holiday (subclass 462) visa pre-application process | Australian Department of Home Affairs | <https://immi.homeaffairs.gov.au/what-we-do/whm-program/latest-news/new-work-and-holiday-subclass-462-visa-pre-application-process> | A · 政府/法律 | 2026-10-30 | 中国、印度、越南护照持有人必须先参加签证预申请（ballot）并被随机抽中，才能递交首次 462 申请；该页 2026-10-19 更新，正文由前端渲染 |
| 4 | secondary | Working Holiday Visa FAQ（澳大利亚旅游局） | Tourism Australia（澳大利亚旅游局） | <https://www.australia.com/en/youth-travel/working-holiday-visa/faq.html> | C · 其他第三方 | 2026-10-16 | 旅游推广性质的 462 / 417 类别说明与常见问题（非移民局官方页，仅作辅证） |

### 澳洲毕业生临时签证

`au-485-graduate` · 官方入口 <https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-graduate-485/post-higher-education-work>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Temporary Graduate visa (subclass 485) — Post-Higher Education Work stream（官方签证页） | Australian Government Department of Home Affairs | <https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-graduate-485/post-higher-education-work> | A · 政府/法律 | 2026-11-08 | 资格原文：`be aged 35 years or under when you apply. *Exceptions apply`；`be in Australia when you apply for this visa`；`hold an eligible visa`；`have held a Student visa in the last 6 months`；`have a recent degree in a CRICOS-registered course`；`provide evidence of adequate health insurance for all applicants when you apply`；`provide evidence you have applied for an Australian Federal Police check when you apply`；`provide evidence of the required level of English with your application.`；`Sign the Australian values statement`；`Have no debt to the Australian Government`。停留时长原文：`Usually between 2 and 3 years, depending on your qualification.`、`Hong Kong and British National Overseas passport holders may stay for 5 years.` 费用原文：`The visa costs AUD5,750.00 for the main applicant (concessions apply in limited circumstances).`、`We cannot process your application if you do not pay the correct Visa Application Charge.` 递交地点原文：`You can be in Australia (but not in immigration clearance) when you apply for this visa.`、`All applicants can be in or outside Australia at the time of decision.` 分支不可改：`apply for your eligible stream (it is not possible to change streams after you apply)`。页面标注 `Last updated: 5 November 2026`。 |
| 2 | primary | Temporary Graduate visa (subclass 485) — About this visa（停留时长分档与二签路径） | Australian Government Department of Home Affairs | <https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-graduate-485/post-higher-education-work#About> | A · 政府/法律 | 2026-11-08 | 分档原文：`Bachelor degree (including honours) — 2 years`、`Masters (coursework and extended) — 2 years`、`Doctoral degree — 3 years`、`The default Graduate Diploma stay period is 2 years, but may be longer where previous study would have attracted a longer stay period.` 印度国籍例外：`Bachelor degree (with first class honours in STEM, including ICT) — 3 years`、`Masters (coursework, extended and research) — 3 years`、`Doctoral degrees (PhD) — 4 years.` 港/BNO：`Hong Kong and British National Overseas passport holders may stay up to 5 years.`、`Current and future Temporary Graduate visa holders from Hong Kong may have a pathway to permanent residency after 5 years.` 起算与出入境：`The visa starts on the date we grant your visa.`、`You can travel in and out of Australia while your visa is valid.` 二签提示：`You may be eligible to apply for a Second Post-Higher Education Work stream visa.` 就业自决：`You must find your own employment while on this visa.` |
| 3 | primary | Temporary Graduate visa — study requirement（2 学年 / 92 周 / 16 个自然月口径） | Australian Government Department of Home Affairs | <https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/temporary-graduate-485/meeting-the-temporary-graduate-visa-subclass-485-study-requirement> | A · 政府/法律 | 2026-11-08 | 核心原文：`you must have completed in the 6 months immediately before the day you apply for your visa, either: a single eligible qualification that requires at least 2 academic years study or more than 1 qualification that results in a total of at least 2 academic years study`；`You must have completed your study in Australia, in a total of no less than 16 calendar months, while you held a visa authorising you to study.`；`Two academic years of study equals 92 weeks that contribute towards one or more acceptable qualification.`；`Two academic years study, or 92 weeks of registered study, is based on the duration of the course as registered by CRICOS.`；`You can take longer to complete your course, but you will only be credited with the number of weeks that CRICOS determines as the standard duration.`；`Only study that you successfully completed counts towards the 2 academic years. You cannot include failed subjects.`；`Credit for prior learning may reduce the amount of study undertaken.`；`You cannot use English language proficiency courses or enabling programs to meet the Temporary Graduate visa study requirement` |
| 4 | primary | English language visa requirements（认可考试与 2025-08-07 改版） | Australian Government Department of Home Affairs | <https://immi.homeaffairs.gov.au/help-support/meeting-our-requirements/english-language> | A · 政府/法律 | 2026-11-08 | 改版原文：`On 7 August 2025, the English language tests approved for Australian visa purposes changed. If you completed a test before this date, your results may still be valid for up to 3 years.` 新版认可清单：`Cambridge C1 Advanced Test`、`Canadian English Language Proficiency Index Program General (CELPIP General)`、`International English Language Testing System Academic (IELTS Academic), including One Skill Retake (OSR)`、`IELTS General Training`、`LANGUAGECERT Academic Test`、`Michigan English Test (MET), including Single Section Retake (SSR)`、`Occupational English Test (OET)`、`Pearson Test of English Academic (PTE Academic)`、`TOEFL iBT - To ensure your TOEFL iBT result is valid for Australian visa purposes, you must select 'Taking TOEFL for Australia' when registering for your test.` 等级划分：该页把英语分为 `Functional English`、`Vocational English`、`Competent English`、`Proficient English`、`Superior English` 五档，各签证按档对应不同分数线。 |
| 5 | primary | Competent English 分数表（Table 1，2025-08-07 及之后考试） | Australian Government Department of Home Affairs | <https://immi.homeaffairs.gov.au/help-support/meeting-our-requirements/english-language/competent-english> | A · 政府/法律 | 2026-11-08 | Table 1 各项最低分原文：`IELTS Academic / General Training — In each of the 4 test components, at least: 6 for listening, 6 for reading, 6 for writing, 6 for speaking`；`PTE Academic — 47 for listening, 48 for reading, 51 for writing, 54 for speaking`；`CELPIP General — 7 for listening, 7 for reading, 7 for writing, 7 for speaking`；`Cambridge C1 Advanced — 163 for listening, 163 for reading, 170 for writing, 179 for speaking`；`MET — 56 for listening, 55 for reading, 57 for writing, 48 for speaking`；`LANGUAGECERT Academic — 57 for listening, 60 for reading, 64 for writing, 70 for speaking`；`OET — 290 for listening, 310 for reading, 290 for writing, 330 for speaking`。该页同时说明英语国家护照持有人（`The Republic of Ireland`、`The United Kingdom of Great Britain and Northern Ireland`、`The United States of America` 等）可用护照直接证明，以及旧成绩有效期上限为 `3 years`。**485 资格页只写「所需的英语等级」，未在该页给出具体等级名与分数；本记录的分数为 Home Affairs 英语等级体系下 Competent English 档的官方分数，实际适用档位须按 485 页面链接核验。** |

---

## 加拿大

### 加拿大国际经验计划（IEC 打工度假）

`ca-iec-working-holiday` · 官方入口 <https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec.html>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | International Experience Canada | Immigration, Refugees and Citizenship Canada | <https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec.html> | A · 政府/法律 | 2026-11-03 | IEC 仅对与加拿大签订青年流动协议的国家/地区开放；中国大陆不在协议名单内；官方原文 2026 IEC season is closed / The pools for the 2026 season are closed；Processing fees CAN $184.75（官方注 Additional fees may apply）；Current processing time 6 weeks after you submit all documents and give biometrics |
| 2 | primary | IEC 参与国家/地区名单（Who can apply） | Immigration, Refugees and Citizenship Canada | <https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec/eligibility.html> | A · 政府/法律 | 2026-11-03 | IEC 参与方为与加拿大签订青年流动协议（YMA）的国家/地区。资格条件原文：be between the ages of 18 and 35 (inclusive)、a minimum of CAN$2,500、health insurance、返程机票、不可带家属 |
| 3 | primary | IEC eligibility by country（各国 Working Holiday 条款与年龄上限） | Immigration, Refugees and Citizenship Canada | <https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec/eligibility/eligibility-by-country.html> | A · 政府/法律 | 2026-11-03 | Country/Territory Age limit 全表：Hong Kong SAR = 18 to 30（Working Holiday Yes / Young Professionals No / International Co-op No）；Taiwan = 18 to 35（三类全部 Yes）；全表文本 China 命中 0 次，无中国大陆条目；表末 My country isn't listed 段落只指向 recognized organization 渠道 |

### 加拿大毕业后工签

`ca-pgwp` · 官方入口 <https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation.html>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Post-graduation work permit — About（PGWP 概览与时长规则） | Immigration, Refugees and Citizenship Canada | <https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/about.html> | A · 政府/法律 | 2026-11-08 | 定义与时长原文：`The post-graduation work permit (PGWP) allows students who have graduated from eligible designated learning institutions (DLIs) to gain valuable Canadian work experience.`、`Graduating from a designated learning institution (DLI) doesn't automatically make you eligible for a PGWP.`、`The length of your PGWP depends on the level and duration of your study program, as well as the expiry date of your passport, whichever comes first.` 硕士规则：`You can apply for a 3-year PGWP, even if your master's program was less than 2 years, as long as your program was at least 8 months (or 900 hours for Quebec programs)`、`This doesn't apply to certificate or diploma programs.` 其余档位：`If your program was at least 8 months (or 900 hours for Quebec credentials), but less than 2 years — We may give you a PGWP that's valid for up to the same length as your study program.`、`If your program was 2 years or more — We may give you a PGWP that's valid for 3 years.` 一次性限制：`You can't get a PGWP if you already had one after completing an earlier program of study.` 政策生效日：`As of November 1, 2024, the eligibility requirements for a PGWP changed. Most PGWP applicants now need to give proof of language results when they apply.` 护照规则：`Your work permit will only be issued for the period your passport is valid.`、`To extend your PGWP, you must apply on paper after you get a new passport` |
| 2 | primary | Post-graduation work permit — Who can apply（资格条件与语言/专业分档） | Immigration, Refugees and Citizenship Canada | <https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility.html> | A · 政府/法律 | 2026-11-08 | 四条通用条件原文：`you completed a program of study at a PGWP-eligible designated learning institution that was at least 8 months long (or 900 hours for Quebec programs)`、`you maintained full-time status as a student in Canada during each semester of your study program`（`You may study part-time during your final semester.`）、`you apply for your PGWP within 180 days of confirmation that you completed your program of study`、`your study permit was valid at some point during the 180 days after you completed your program of study`。语言分档原文：本硕博与其他大学课程 `You must prove your English or French language skills with a minimum level of Canadian Language Benchmarks (CLB) 7 in English or Niveaux de competence linguistique canadiens (NCLC) 7 in French in all 4 language areas.`；学院/理工/非大学课程 `... CLB 5 ... NCLC 5 ...`。专业领域要求：`If you submitted your study permit application on or after November 1, 2024, you must graduate in an eligible field of study.`，而本硕博 `There are no field of study requirements for graduates with a bachelor's degree, master's degree or doctoral degree.` 排除清单含 `already received a PGWP`、`studied English or French as a second language`、`completed a non-credit program of study (except for a flight school program)`、`completed over 50% of your study program through distance learning`、`completed a study program at a non-Canadian institution located in Canada`。 |
| 3 | primary | Post-graduation work permit — How to apply（材料与缴费） | Immigration, Refugees and Citizenship Canada | <https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/apply.html> | A · 政府/法律 | 2026-11-08 | 窗口与缴费原文：`You have up to 180 days after you graduate to apply for a PGWP.`、`In most cases, you must apply online for a PGWP.`、`Make sure you pay both the open work permit holder fee and the work permit fee.`、`we'll ask you to pay your fees at the end of your application`。清单缺陷原文：`your PGWP document checklist will list the proof of language results as an optional document. You must include this proof with your application if it's a requirement for your study program.`、`Due to system limitations, the document checklist won't ask you to provide proof that you graduated from an eligible field of study. If you're required to provide proof ... you must upload it in the 「Client information」 section of your account.` |
| 4 | primary | Post-graduation work permit — After you apply（等待期间工作权限） | Immigration, Refugees and Citizenship Canada | <https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/after-you-apply.html> | A · 政府/法律 | 2026-11-08 | 等待期工作原文：`You can work full-time until we make a decision on your work permit application if you had a valid study permit at the time you submitted your application`、`were eligible to work off campus without a work permit while studying and you didn't work more hours than you were allowed to`。WP-EXT 信规则：`You can work until we make a decision on your work permit application even if the validity period of the letter expires.` 拒签后果：`If we refuse your work permit, you must stop working the day we notify you.` 出入境规则：`If you leave and re-enter Canada after applying for your post-graduation work permit, you can still work full-time while you wait for a decision.` |
| 5 | primary | Fees for citizenship and immigration services（IRCC 官方费用表） | Immigration, Refugees and Citizenship Canada | <https://ircc.canada.ca/english/information/fees/fees.asp> | A · 政府/法律 | 2026-11-08 | Work Permits 段落原文：`Work permit (including extensions) — per person 155.00`、`Open work permit holder 100.00`、`Restore your status ($246.25) and get a new work permit ($155)`。PGWP 属开放式工签，故两笔费用合计 255 加元。 |

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

### 德国毕业后求职居留许可

`de-20-job-search` · 官方入口 <https://www.gesetze-im-internet.de/aufenthg_2004/__20.html>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | AufenthG §20 — Arbeitsplatzsuche im Anschluss an Aufenthalte im Bundesgebiet（德文原文） | Bundesministerium der Justiz（德国联邦司法部，gesetze-im-internet.de） | <https://www.gesetze-im-internet.de/aufenthg_2004/__20.html> | A · 政府/法律 | 2026-11-08 | 五条适用路径原文：`nach erfolgreichem Abschluss eines Studiums im Bundesgebiet im Rahmen eines Aufenthalts nach § 16b oder § 16c`、`nach Abschluss der Forschungstätigkeit ... § 18d oder § 18f`、`nach erfolgreichem Abschluss einer qualifizierten Berufsausbildung ... § 16a`、`nach der Feststellung der Gleichwertigkeit der Berufsqualifikation oder der Erteilung der Berufsausübungserlaubnis ... § 16d`、`nach erfolgreichem Abschluss einer Assistenz- oder Helferausbildung ... im Gesundheits- und Pflegewesen`。时长原文：`Sie wird in den Fällen des Absatzes 1 Nummer 1 bis 4 für einen Zeitraum von bis zu 18 Monaten erteilt. In den Fällen des Absatzes 1 Nummer 5 wird sie für einen Zeitraum von bis zu zwölf Monaten erteilt und kann einmalig um bis zu sechs Monate verlängert werden, wenn der Lebensunterhalt gesichert ist. Die Verlängerung nach Absatz 1 über diese Zeiträume hinaus ist ausgeschlossen.` 生计保障：`Die Erteilung einer Aufenthaltserlaubnis nach Absatz 1 setzt die Lebensunterhaltssicherung voraus.` **全条未设年龄与国籍限制。** |
| 2 | primary | AufenthG §20 — Foreigners seeking employment following stays in the federal territory（官方英文对照版） | Bundesministerium der Justiz（德国联邦司法部，gesetze-im-internet.de 英文版） | <https://www.gesetze-im-internet.de/englisch_aufenthg/englisch_aufenthg.html> | A · 政府/法律 | 2026-11-08 | 英文对照确认同一口径：`In the cases covered by subsection (1) nos. 1 to 4, the temporary residence permit is granted for a period of up to 18 months. In the cases covered by subsection (1) no. 5, it is granted for a period of up to 12 months and may be extended once by up to six months if the foreigner's subsistence is secured. It may not be extended beyond these maximum periods.` 以及 `The temporary residence permit is granted pursuant to subsection (1) on the condition that the foreigner's subsistence is secured.` 该页同时提供 §20a 机会卡英文，用于区分两条路径：§20a 允许 `to pursue employment of up to 20 hours per week`。 |
| 3 | primary | AufenthV § 45 — Gebühren für die Aufenthaltserlaubnis（居留许可收费） | Bundesministerium der Justiz（德国联邦司法部，gesetze-im-internet.de） | <https://www.gesetze-im-internet.de/aufenthv/__45.html> | A · 政府/法律 | 2026-11-08 | 居留许可签发费 100 欧元，不论有效期在一年以内还是超过一年都收同一数额（原文 `für die Erteilung einer Aufenthaltserlaubnis ... a) mit einer Geltungsdauer von bis zu einem Jahr 100 Euro, b) mit einer Geltungsdauer von mehr als einem Jahr 100 Euro`）；延期视追加停留期长短为 93 或 96 欧元。§20 求职居留与 §20a 机会卡签发的都是 Aufenthaltserlaubnis，都适用这一档，不存在各外管局自行定价的空间。 |
| 4 | primary | AufenthV § 46 — Gebühren für das Visum（国家签证收费） | Bundesministerium der Justiz（德国联邦司法部，gesetze-im-internet.de） | <https://www.gesetze-im-internet.de/aufenthv/__46.html> | A · 政府/法律 | 2026-11-08 | 德国国家签证（D 类）签发费 75 欧元，多次入境同价（原文 `für die Erteilung eines nationalen Visums (Kategorie „D“), auch für mehrmalige Einreisen 75 Euro`）；在德国境内把申根签证转为国家签证延长超过 90 天为 60 欧元。人在中国先办 D 类签证入境、再在德国当地换居留卡的两段式流程，第一段就是这 75 欧元。 |

### 德国机会卡（求职居留许可）

`de-chancenkarte` · 官方入口 <https://www.make-it-in-germany.com/en/working-in-germany/visa/opportunity-card>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | § 20a AufenthG — Chancenkarte（德国居留法原文） | Bundesministerium der Justiz（德国联邦司法部，gesetze-im-internet.de 官方数据库） | <https://www.gesetze-im-internet.de/aufenthg_2004/__20a.html> | A · 政府/法律 | 2026-11-03 | 定义与权限原文：`Eine Chancenkarte ist eine Aufenthaltserlaubnis zur Suche nach einer Erwerbstätigkeit oder nach Maßnahmen zur Anerkennung ausländischer Berufsqualifikationen.` 工作限制原文：`eine Beschäftigung von durchschnittlich insgesamt höchstens 20 Stunden je Woche auszuüben` 与 `eine Probebeschäftigung für jeweils höchstens zwei Wochen`。发放条件：`er eine Fachkraft ist` 或 `nach Maßgabe der Tabelle in der Anlage zu diesem Gesetz eine ausreichende Punktzahl ... erhalten hat`；且 `der Lebensunterhalt gesichert ist`。学历门槛：外国职业资格须经来源国官方承认且培训期不少于两年，或持外国高校学历。语言门槛：`mindestens einfache deutsche Sprachkenntnisse` 或 `englische Sprachkenntnisse mindestens auf dem Niveau B2`。时长与延长：`zunächst für einen Zeitraum von bis zu einem Jahr`，凭劳动合同或具约束力录用意向可 `um bis zu zwei Jahre` 延长，`Eine über Satz 2 hinausgehende Verlängerung als Chancenkarte ist ausgeschlossen.` 配额授权：`die Zahl der Chancenkarten ... jährlich oder für einen kürzeren Zeitraum zu begrenzen`。 |
| 2 | primary | § 20b AufenthG — Punktevergabe für die Chancenkarte（积分项） | Bundesministerium der Justiz（德国联邦司法部，gesetze-im-internet.de 官方数据库） | <https://www.gesetze-im-internet.de/aufenthg_2004/__20b.html> | A · 政府/法律 | 2026-11-03 | 12 项计分事由原文（编号 1-12）：①外国职业资格被认定需适应/补偿措施或需执业许可；②良好德语；③足够德语（未因②计分时）；④基础德语（未因②③计分时）；⑤英语 C1；⑥近 7 年内有至少 5 年相关经验；⑦近 5 年内有至少 2 年相关经验且未因⑥计分；⑧职业资格属 §18g Abs.1 S.2 Nr.1 短缺职业组；⑨申请时不超过 35 岁；⑩申请时超过 35 岁且不超过 40 岁；⑪过去 5 年在德合法连续居留至少 6 个月；⑫配偶或登记伴侣同时满足条件并共同申请。 |
| 3 | primary | Anlage zu § 20a Abs. 3 Nr. 2, § 20b AufenthG（积分表与最低分） | Bundesministerium der Justiz（德国联邦司法部，gesetze-im-internet.de 官方数据库） | <https://www.gesetze-im-internet.de/aufenthg_2004/anlage.html> | A · 政府/法律 | 2026-11-03 | 分值表原文：特征 1 = 4 分、2 = 3 分、3 = 2 分、4 = 1 分、5 = 1 分、6 = 3 分、7 = 2 分、8 = 1 分、9 = 2 分、10 = 1 分、11 = 1 分、12 = 1 分；`Die Mindestpunktzahl beträgt sechs Punkte.`（最低 6 分，满分 22 分）。出处标注 `BGBl. 2023 I Nr. 217, S. 20`。 |
| 4 | primary | Opportunity Card — Make it in Germany（德国联邦政府官方门户） | Bundesministerium für Wirtschaft und Klimaschutz / Bundesregierung（德国联邦经济与气候保护部） | <https://www.make-it-in-germany.com/en/working-in-germany/visa/opportunity-card> | A · 政府/法律 | 2026-11-03 | 该页是本项目的官方政策说明页，本站对其正文的可读性有限：直接抓取返回的是 `Radware Page / Verifying your browser before proceeding...`（115 字符反爬中间页），无头浏览器通道同样被拦，因此**未能读到正文逐字原文**。上面所有具体条款均以 gesetze-im-internet.de 的法条原文为准，本页仅作为项目存在与官方定位的佐证。 |
| 5 | primary | AufenthV § 45 — Gebühren für die Aufenthaltserlaubnis（居留许可收费） | Bundesministerium der Justiz（德国联邦司法部，gesetze-im-internet.de） | <https://www.gesetze-im-internet.de/aufenthv/__45.html> | A · 政府/法律 | 2026-11-08 | 居留许可签发费 100 欧元，不论有效期在一年以内还是超过一年都收同一数额（原文 `für die Erteilung einer Aufenthaltserlaubnis ... a) mit einer Geltungsdauer von bis zu einem Jahr 100 Euro, b) mit einer Geltungsdauer von mehr als einem Jahr 100 Euro`）；延期视追加停留期长短为 93 或 96 欧元。§20 求职居留与 §20a 机会卡签发的都是 Aufenthaltserlaubnis，都适用这一档，不存在各外管局自行定价的空间。 |
| 6 | primary | AufenthV § 46 — Gebühren für das Visum（国家签证收费） | Bundesministerium der Justiz（德国联邦司法部，gesetze-im-internet.de） | <https://www.gesetze-im-internet.de/aufenthv/__46.html> | A · 政府/法律 | 2026-11-08 | 德国国家签证（D 类）签发费 75 欧元，多次入境同价（原文 `für die Erteilung eines nationalen Visums (Kategorie „D“), auch für mehrmalige Einreisen 75 Euro`）；在德国境内把申根签证转为国家签证延长超过 90 天为 60 欧元。人在中国先办 D 类签证入境、再在德国当地换居留卡的两段式流程，第一段就是这 75 欧元。 |

---

## 丹麦

### 丹麦打工度假居留（Working Holiday）

`dk-working-holiday` · 官方入口 <https://www.nyidanmark.dk/en-GB/You-want-to-apply/Working-holiday>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Working Holiday（丹麦移民局 New to Denmark 官方页） | The Danish Immigration Service / SIRI | <https://www.nyidanmark.dk/en-GB/You-want-to-apply/Working-holiday> | A · 政府/法律 | 2026-11-11 | 参与国原文：`You are a young citizen of Argentina, Australia, Canada, Chile, Japan, New Zealand or South Korea and want to apply for a Working Holiday residence permit in Denmark.` 中国大陆不在其中。页面的详细正文由前端脚本注入，本次抓取（含无头浏览器通道）只渲染出这句参与国说明与一个 `No Datasource Found` 占位，因此年龄、资金、材料等字段未能逐字核实，已在对应字段标注为待核实而非填猜测值。 |

---

## 西班牙

### 西班牙求职/创业居留（Autorización de residencia para búsqueda de empleo o inicio de proyecto empresarial）

`es-busqueda-empleo` · 官方入口 <https://www.inclusion.gob.es/web/migraciones/listado-completo>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Listado completo de autorizaciones（西班牙移民事务部委 Hoja 58） | Ministerio de Inclusión, Seguridad Social y Migraciones | <https://www.inclusion.gob.es/web/migraciones/listado-completo> | A · 政府/法律 | 2026-11-11 | 本条资格、最长 24 个月且不可延期、以及「不授权工作」的口径由事实包提供，其标注原文为 `no se está autorizado a trabajar`。本次尝试通过脚本与真实浏览器两条通道访问该页，均返回 `Acceso no permitido`（访问被拒），未能逐字复核正文；关键断言沿用事实包结论，未做改写。费用与费项编号另行用 BOE 原文交叉核对（见下条）。 |
| 2 | primary | Orden PJC/617/2025（居留与证件收费标准，BOE 官方公报） | Boletín Oficial del Estado（西班牙国家官方公报） | <https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-12056> | A · 政府/法律 | 2026-11-11 | 费项 2.1.6 原文：`Autorización de residencia para estudiante para la búsqueda de empleo o para emprender un proyecto empresarial (DA 17.ª L. 14/2013) (titular principal y sus familiares). 10,94`。已逐字核对：€10.94 对应的正是本条通道，费项编号与事实包一致。同表相邻项 2.1.2、2.1.3、2.1.5、2.1.7 亦为 10,94。 |

---

## 芬兰

### 芬兰求职/创业居留（Residence permit to look for work or to start a business）

`fi-look-for-work` · 官方入口 <https://migri.fi/residence-permit-to-look-for-work>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Residence permit to look for work or to start a business（芬兰移民局官方页） | Migri（Finnish Immigration Service） | <https://migri.fi/residence-permit-to-look-for-work> | A · 政府/法律 | 2026-11-11 | 本条关于「在芬兰完成学位或研究、曾持学习或科研许可、许可到期后 5 年内可申、最长 2 年分最多 3 段（每段 ≥6 个月）、无限制工作权、收入要求 €800/月」的口径由事实包提供。本次尝试通过脚本与真实浏览器两条通道访问 migri.fi，均被 Cloudflare 挑战页拦截（「Checking if the site connection is secure」），未能逐字复核正文；关键断言沿用事实包，未做改写。 |
| 2 | primary | Processing fees and payment methods（Migri 官方费率表） | Migri（Finnish Immigration Service） | <https://migri.fi/en/processing-fees-and-payment-methods> | A · 政府/法律 | 2026-11-11 | 首签费用 €750（在线）／€800（纸质）由事实包提供；本次同样因 Cloudflare 拦截未能逐字复核。费用为 Migri 费率表口径，且该表每年可能调整，递交前须复核。 |

---

## 法国

### 法国求职/创业居留（Carte de séjour / VLS-TS « recherche d'emploi / création d'entreprise »）

`fr-recherche-emploi` · 官方入口 <https://www.service-public.gouv.fr/particuliers/vosdroits/F17319>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Carte de séjour ou VLS-TS - recherche d'emploi/création d'entreprise（法国公共服务官方页 F17319） | Direction de l'information légale et administrative (DILA), service-public.fr | <https://www.service-public.gouv.fr/particuliers/vosdroits/F17319> | A · 政府/法律 | 2026-11-11 | 资格原文：人在法国须 `Séjourner en France avec une carte de séjour étudiant ou étudiant programme de mobilité` 且 `Avoir obtenu au cours des 12 derniers mois, une licence professionnelle, un Mastère Spécialisé, un Master of Science (labellisé par la conférence des grandes écoles) ou un autre diplôme au moins équivalent au master`；已回国者 `Faire votre demande dans le délai maximal de 4 ans à compter de l'obtention de votre diplôme`；期限与续签 `La carte de séjour ou le VLS-TS est valable 1 an. Le renouvellement n'est pas possible.`；工作权 `Pendant sa validité, cette carte vous permet de travailler en tant que salarié. L'employeur est dispensé de demander une autorisation de travail.` 两个条件 `Être en lien avec vos études`、`Être assorti d'une rémunération mensuelle brute supérieure à 2 800,53 €`，以及 `La limitation à 60 % de la durée annuelle de travail (964 heures) ne s'applique pas.`；费用 `Vous devez payer 150 € (droit de timbre de 50 € + taxe de 100 €) par timbres fiscaux.`；递交窗口 `dans les 2 mois précédant la date de fin de validité de votre carte étudiant`。 |
| 2 | primary | Recherche d'emploi / création d'entreprise（France-Visas 官方说明页） | France-Visas（法国外交部） | <https://france-visas.gouv.fr/en/web/france-visas/recherche-d-emploi-creation-d-entreprise> | A · 政府/法律 | 2026-11-11 | 本条由事实包提供并标注为官方来源。本次核实尝试通过脚本与真实浏览器两条通道访问该页均被 Cloudflare 挑战页拦截（503 / 「Checking if the site connection is secure」），未能逐字读到正文。service-public.fr 的 F17319 页（已实测可读）覆盖了同一通道的资格、期限、费用与工作权，本记录的全部关键断言均以该页原文为准。 |

---

## 国际实习平台

### AIESEC 全球人才计划（企业实习）

`global-aiesec-global-talent` · 官方入口 <https://aiesec.org/global-talent>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | AIESEC Global Talent（官方项目页） | AIESEC International | <https://aiesec.org/global-talent> | B · 项目本体组织 | 2026-10-30 | Global Talent 平台定位、岗位领域划分与在招数量（67 个国家/地区、2,000+ 实习岗位）、4 步申请流程、提供签证与落地支持。该页**未**公布年龄、学历、费用、保险要求。 |
| 2 | secondary | AIESEC Global Talent 2026 概述 | Opportunity Nest | <https://www.opportunitynest.org/opportunity/aiesec-global-talent-global> | C · 其他第三方 | 2026-10-30 | 二手概述（2026-10-30 复核原文）：年龄 mainly people between 18 and 30（原文用 mainly，非硬性区间）；学籍条件为「我们查过的德国岗位」的个例——accepted only master's students who stay enrolled for the whole internship, or bachelor's graduates within two months of graduating，**不是全球统一门槛**；Life and health insurance is mandatory；There is no single deadline, internships are posted and filled continuously。该页同时写明 AIESEC's central pages do not mention a programme fee，即连这篇二手来源也未给费用数字，故数据里 700 USD 项目费无法追溯来源、已删除。 |

### IAESTE 国际大学生技术实习交流计划

`global-iaeste` · 官方入口 <https://www.iaeste.org/>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Student FAQs — IAESTE | IAESTE International | <https://iaeste.org/student-faqs> | B · 项目本体组织 | 2026-10-30 | 学历与学籍官方原文（2026-10-30 复核）：To undertake an IAESTE internship you must be enrolled in a degree course relating to the study field of the internship you wish to apply for. Some IAESTE countries require you to have completed 2 years of your course before undertaking an IAESTE internship；学科范围：The vast majority of our internships are in science, engineering and applied arts fields (architecture/design) but we do sometimes have internships relevant to other fields (business, marketing etc.)；时长 six weeks to a year |
| 2 | primary | IAESTE — International Association for the Exchange of Students for Technical Experience（组织介绍页） | IAESTE International | <https://www.iaeste.org/> | B · 项目本体组织 | 2026-10-30 | 组织性质与规模：100+ 国家/地区、1948 年至今累计派出 374,000+ 名学生、2,500+ 志愿者、3,000+ 接收机构；实习带薪（cost of living allowance 至少覆盖住宿、餐饮与本地交通） |
| 3 | primary | Application process — IAESTE Germany | IAESTE Germany | <https://www.iaeste.de/application-process/> | B · 项目本体组织 | 2026-10-30 | 申请流程（Exchange Platform 注册、三份必需文件、账号验证）、英语证书要求（3 年内有效）、Offer 发布节奏（11月/1月/4月国际交流会议） |
| 4 | primary | Outgoing Trainee — IAESTE Austria | IAESTE Austria | <https://www.iaeste.at?p=1254/> | B · 项目本体组织 | 2026-09-17 | 申请三步流程、必需材料（CV/成绩单/在读证明）、免费语言测试、押金 EUR 300、实习带薪且覆盖当地生存成本 |
| 5 | secondary | IAESTE 实习交流计划 — 澳门大学全球事务部 | University of Macau, Global Affairs Office | <https://gao.um.edu.mo?lang=zh-hant&p=7735/> | C · 高校官网 | 2026-09-17 | 申请资格（全日制在校生、成绩卓越、良好英语）、无申请费、每年 1 月底至 2 月接受申请、大四学生学籍风险提示（高校官方部门来源） |
| 6 | primary | IAESTE in China, HLG（IAESTE 官网合作机构页） | IAESTE A.s.b.l. | <https://iaeste.org/member-countries/china-hlg> | B · 项目本体组织 | 2026-10-30 | 中国大陆在 IAESTE 的合作机构（Co-operating Institution）为 Archibucks 与 HLG 两家，非 National Committee（国家委员会）；官方联系域名 iaeste.learngive.cn |

---

## 爱尔兰

### 爱尔兰打工度假授权

`ie-working-holiday-authorisation` · 官方入口 <https://www.irishimmigration.ie/coming-to-work-in-ireland/what-are-my-options-for-working-in-ireland/coming-to-work-for-more-than-90-days/working-holidays-in-ireland/>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Working holidays in Ireland — Immigration Service Delivery | Immigration Service Delivery, Ireland | <https://www.irishimmigration.ie/coming-to-work-in-ireland/what-are-my-options-for-working-in-ireland/coming-to-work-for-more-than-90-days/working-holidays-in-ireland/> | A · 政府/法律 | 2026-11-08 | WHA 签约国家/地区官方名单（安道尔、阿根廷、澳大利亚、加拿大、智利、中国香港、日本、新西兰、韩国、美国、中国台湾）、停留期最长 1 年（加拿大 2 年）、Places are limited、中国台湾 400 名额/年、2027 年度自 2026-11-01 09:00（台北时间）开放并按收件先后受理、前 400 份合格申请 2027 年初签发 |
| 2 | primary | Working Holiday Authorisation — Department of Foreign Affairs | Department of Foreign Affairs, Ireland | <https://www.ireland.ie/en/dfa/visas-for-ireland/working-holiday-authorisation/> | A · 政府/法律 | 2026-11-08 | 按国籍分流的递交口径：11 个签约国家/地区各自对应的受理机构（中国香港→驻港总领事馆，中国台湾→ISD，美国→驻美使领馆等） |
| 3 | primary | How to apply for working holiday from Taiwan（2027 指南，EN） | Immigration Service Delivery, Ireland | <https://www.irishimmigration.ie/wp-content/uploads/2026/11/2027-EN_Guidance-Note.pdf> | A · 政府/法律 | 2026-11-08 | 八项资格条件原文：(a) be aged between 18 and 30 years inclusive at the time of application；(b) employment being an incidental, rather than the primary reason for the visit；(c) 不得携带未持 WHA 的家属；(d) 机票 + €2,500 或 €4,000 含机票；(e) 私人医疗保险须覆盖住院与遣返；(f) 未曾以打工度假身份在爱尔兰停留；(g) not have a criminal record；(h) 申请时不得已持其他身份在爱尔兰。另：There is no application fee for participation in this programme；handling fee NT 3,200 付给台北代理 Ms Corina Tsai；maximum stay ... twelve (12) months from the date of initial entry into Ireland with no possibility of extension；停留超 90 天须向 ISD 注册并缴费；WHA 在 2027 年初签发，可在 2027-12-31 前任一时点入境 |
| 4 | primary | Working Holiday Authorisation Application Form 2027（WHA 2027 申请表） | Immigration Service Delivery, Ireland | <https://www.irishimmigration.ie/wp-content/uploads/2026/11/WHA-2027-Application-Form-November-2026.pdf> | A · 政府/法律 | 2026-11-08 | 必备材料：护照全部页面彩色复印件（含空白页，护照须在行程结束后仍有 6 个月有效期）、4 张同版照片（背面写姓名）、本人名下银行流水（英文对账单 €4,000 或附翻译的 €2,500）、返程或续程机票；代理手续费 the non-refundable agent’s handling fee of NT$3,200；信息采集问句含 Have you any criminal convictions in any country?、Have you ever come to Ireland previously on a Working Holiday programme?；Extensions to the period of validity shall not be granted |

---

## 冰岛

### 冰岛毕业后求职居留（学生居留续签，special residence permit for employment-seeking after graduation）

`is-job-search-after-graduation` · 官方入口 <https://island.is/en/o/directorate-of-immigration/news/new-residence-and-work-permit-rules-take-effect>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | New residence and work permit rules take effect（冰岛移民局 2026-07-08 新规公告） | Útlendingastofnun（Directorate of Immigration, Iceland） | <https://island.is/en/o/directorate-of-immigration/news/new-residence-and-work-permit-rules-take-effect> | A · 政府/法律 | 2026-11-11 | 18 个月现行值的原文：`Foreign nationals who have completed a university degree in Iceland may now renew their student residence permit for up to 18 months after graduation to seek employment based on their qualifications. Previously, this was possible for up to three years.`；资格 `applicants must have completed a Bachelor's, Master's or Doctoral degree at an Icelandic university`；博士另途 `foreign nationals who have completed a doctoral degree in Iceland may renew a specialist residence permit for up to 12 months to seek employment`；在读生学业进度 `completing at least 75% of a full-time course load during the academic year`，且 `must now demonstrate satisfactory academic progress each time they renew their permit, rather than only at the first renewal`；学生打工 `may work in Iceland without a work permit for up to 60% of full-time employment while studying`。本页已实测可读，以上均逐字取自页面正文。 |
| 2 | primary | Increase in application fees（冰岛移民局费率公告，2026-01-01 起生效） | Útlendingastofnun（Directorate of Immigration, Iceland） | <https://island.is/en/o/directorate-of-immigration/news/increase-in-fees-for-residence-permit-and-citizenship-applications> | A · 政府/法律 | 2026-11-11 | 费率表原文：`Application for renewal of a residence permit based on studies: ISK 70.000`；`Application for renewal of other residence permits: ISK 40.000`。本记录按「学习类续签」ISK 70,000 归类，并在费用 note 中写明官方未点名「毕业后求职」这一许可、若按「其他居留」则为 ISK 40,000——这是归类口径而非官方对本许可的直接报价。该页同时说明生效日为 2026-01-01。 |

---

## 意大利

### 意大利求职/创业居留（Permesso di soggiorno per ricerca lavoro o imprenditorialità degli studenti）

`it-ricerca-lavoro` · 官方入口 <https://integrazionemigranti.gov.it/it-it/Ricerca-news/Dettaglio-news/id/3301/t/45/Conversione-del-permesso-di-soggiorno-da-studio-a-lavoro-Cosa-e-cambiato-con-il-decreto-Cutro>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Conversione del permesso di soggiorno da studio a lavoro: cosa è cambiato con il decreto Cutro（移民融合门户官方说明） | Ministero dell'Interno / Integrazione Migranti | <https://integrazionemigranti.gov.it/it-it/Ricerca-news/Dettaglio-news/id/3301/t/45/Conversione-del-permesso-di-soggiorno-da-studio-a-lavoro-Cosa-e-cambiato-con-il-decreto-Cutro> | A · 政府/法律 | 2026-11-11 | 本条关于「学习转工作脱离 flussi 年度配额、全年可申」以及「凭申请回执即可开始工作」的口径由事实包提供。本次尝试通过脚本访问该页返回 HTTPError，未能逐字复核正文；法律依据（D.Lgs. 286/1998 第 39-bis.1 条、Law 50/2023）与费用另用 portaleimmigrazione 费用表交叉核对（见下条）。关键断言沿用事实包，未做改写。 |
| 2 | primary | Tabelle Costi（意大利内政部移民门户官方费用表） | Ministero dell'Interno — Portale Immigrazione | <https://www.portaleimmigrazione.it/ITA/tabelleCosti.html> | A · 政府/法律 | 2026-11-11 | 费用表逐项原文：`Marca da bollo 16.00 €`；`Produzione del Permesso di Soggiorno 30.46 €`；`Contributo per permessi di soggiorno di durata superiore a tre mesi e fino ad un anno 40.00 €`；`Costo spedizione Poste Italiane 30.00 €`。据此：卡费 30.46 + 印花 16 + 邮局 30 = €76.46（不含贡献金）；若计入 3–12 个月档贡献金 €40，则为 €116.46。这正是本记录在费用 note 里标注的口径差异。 |

---

## 日本

### 日本打工度假签证

`jp-working-holiday` · 官方入口 <https://www.mofa.go.jp/j_info/visit/w_holiday/index.html>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | The Working Holiday Programmes in Japan | Ministry of Foreign Affairs of Japan | <https://www.mofa.go.jp/j_info/visit/w_holiday/index.html> | A · 政府/法律 | 2026-11-03 | 截至 2026-11-01 的 33 个协议国家/地区名单（含中国台湾 10,000、中国香港 1,500、意大利 500、马耳他 100、巴拿马 100，不含中国大陆）、各国年度签发上限、年龄 18-30（澳加韩为 18-25，可另议放宽至 30）、资金与返程机票要求、身体健康、未曾取得过日本打工度假签证、申请程序、工作限制（禁止酒吧/夜总会/赌博场所及影响公共道德场所）；[NB2] 两次参与放宽：2024-12-01 加拿大/英国/新西兰/丹麦/奥地利、2025-01-01 德国/爱尔兰/斯洛伐克、2025-10-01 韩国、2026-02-01 中国台湾；中国大陆不在任何放宽名单内 |
| 2 | primary | 査証手数料（日本签证手续费，令和8年6月24日公告） | Ministry of Foreign Affairs of Japan | <https://www.mofa.go.jp/mofaj/toko/visa/tetsuzuki/pagew_000001_02672.html> | A · 政府/法律 | 2026-11-03 | 「領事官の徴収する手数料に関する政令」改正自令和8年7月1日施行；同日以后在外公馆受理的申请，一次有效签证约 15,000 日元、数次有效签证约 30,000 日元（邦货换算）；渡航目的与国籍不同可能免收或金额不同 |
| 3 | primary | 日台打工度假制度簽證須知（2026 年版） | 公益財団法人日本台湾交流協会（日本台湾交流协会，台北/高雄事务所） | <https://www.koryu.or.jp/tw/visa/taipei/working/guide2026/> | A · 政府/法律 | 2026-11-08 | 资格条件与流程原文：申请时须居住在台湾、年龄 18 岁以上 30 岁以下、以度假为主要目的停留不超过一年、无被抚养者同行、持有效台湾护照、持返程票券或购票经费、持足以维持初期生活的费用、身体健康且无不良纪录或犯罪纪录、已投保在日停留期间的伤病死亡保险。签证有效期一年、不可延长。2026 年度两期受理：前期 04-20 至 04-30、后期 10-19 至 10-30（10-26 休所）；发表 06-18、12-11；领证期间 06-22 至 12-18、12-14 至 2027-06-11。另载：自 2026 年 2 月起参加次数由一生 1 次改为最多 2 次。 |
| 4 | primary | 打工度假簽證之申請所需文件（2026） | 公益財団法人日本台湾交流協会（日本台湾交流协会，台北/高雄事务所） | <https://www.koryu.or.jp/tw/visa/taipei/working/guide2026/guide-detail1/> | A · 政府/法律 | 2026-11-08 | 材料清单与规格原文：白底彩色证件照 1 张「直4.5公分×橫3.5公分，6個月內拍攝」；履历书须用 2026 年 9 月更新的最新格式，「請申請者本人以中文或日文書寫」；资金证明为「8萬台幣以上由銀行或郵局開立之存款證明書（正本，1個月內所申請的存款證明）」，并注明「存摺影本者，不予認可」；另需最终学历证明、护照影本、移民署 10 日内核发的入出国日期证明书。 |
| 5 | primary | 打工度假 Q&A（日本台湾交流协会） | 公益財団法人日本台湾交流協会（日本台湾交流协会，台北/高雄事务所） | <https://www.koryu.or.jp/tw/visa/taipei/working/FAQ/> | A · 政府/法律 | 2026-11-08 | 问答原文：签证有效期自领证期间第一日起算，停留期自入境日起算；一年期满不得延长或变更为其他在留资格；「有關工作的時間並無特定限制」；保险只要覆盖生病、受伤、死亡即可（健保除外）；「申請的手續費用是多少？免費。」；日语能力不构成拒绝理由，但申请人数多时可能作为相对考量；必须本人到窗口办理。 |

---

## 韩国

### 韩国 H-1 打工度假签证

`kr-h1-working-holiday` · 官方入口 <https://whic.mofa.go.kr/contents.do?contentsNo=39&menuNo=91>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Working Holiday Information Center (WHIC) | Ministry of Foreign Affairs, Republic of Korea | <https://whic.mofa.go.kr/contents.do?contentsNo=39&menuNo=91> | A · 政府/法律 | 2026-10-30 | H-1 签证资格（18-30 岁）、材料清单、申请规则（须在本国申请、一生一次、不可境内转换） |
| 2 | primary | H-1 visa (Working Holiday) — 韩国驻悉尼总领事馆 | Consulate General of the Republic of Korea in Sydney | <https://overseas.mofa.go.kr/au-sydney-en/brd/m_2367/view.do?seq=760608&page=1> | A · 政府/法律 | 2026-10-30 | H-1 签证年龄要求（2026-09-01 起部分国家放宽至 18-35 岁）、工作限制（同一雇主不超过 6 个月）、禁止职业清单、材料清单 |
| 3 | primary | Working Holiday (H-1) Visa Information by Country and Region | Working Holiday Info Center, Overseas Koreans Agency（韩国外交部海外侨胞厅） | <https://whic.mofa.go.kr/contents.do?menuNo=90&contentsNo=38> | A · 政府/法律 | 2026-10-30 |  |
| 4 | primary | 韩国打工度假官方手册（2026-2027，在外同胞厅 Working Holiday Info Center） | Overseas Koreans Agency, Republic of Korea | <https://whic.mofa.go.kr/upload/temp/kr_workingholiday_english.pdf> | A · 政府/法律 | 2026-11-08 | 2026-2027 官方手册原文：`Stay up to 12 months`、`maximum working hours: 25 hours/week`、`Entitled to undertake most types of temporary employment ... with the exception of certain professional jobs (doctor, language instructor, athlete, entertainer, etc)`；资格条件 `Be between the ages of 18 and 30 years (inclusive)`、`Be inside your home country when you apply and when your visa is granted`、`Have sufficient funds ... (KRW 3,000,000 minimum)`、`Not have criminal record`；材料清单 `Medical certificate`、`Criminal record check`、`Travel plans`、`Health Insurance ... (Coverage: KRW 40,000,000 minimum)`；Q&A 明确 25 小时上限与受限职业；FAQ 明确不可续签、可在有限情形转签证、加拿大与日本公民可参加两次；并声明各项要求可能因使领馆/KVAC 而异。 |

---

## 马耳他

### 马耳他数字游民居留许可（Nomad Residence Permit）

`mt-nomad-residence` · 官方入口 <https://nomad.residencymalta.gov.mt/nomad-eligibility/>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Nomad Residence Permit — Eligibility（Residency Malta Agency 官方页） | Residency Malta Agency | <https://nomad.residencymalta.gov.mt/nomad-eligibility/> | A · 政府/法律 | 2026-11-11 | 资格原文：`Applicants must also be third country nationals (non-EU, non-EEA, and non-Swiss nationals)`；三类形态 `work for an employer registered in a foreign country and have a contract of work`、`conduct business activities for a company registered in a foreign country and of which applicant is partner/shareholder`、`offer freelance or consulting services, to clients whose permanent establishments are in a foreign country`；排除项 `Persons contracted by a foreign company and giving services to the company's Maltese subsidiary are not eligible`；收入 `an applicant must have a minimum gross yearly income of €42,000`，旧标准 `Applicants who submitted their application prior to 1st April 2024 will still retain the same annual gross income requirement of €32,400`；其他 `hold a valid travel document`、`have health insurance covering risks in the European Union (including Malta) and the UK`、`hold a valid property rental or purchase agreement`、`provide a police conduct certificate`、`pass a background verification check`。 |
| 2 | primary | Nomad Residence Permit — FAQs（费用、周期、续期与家属规则） | Residency Malta Agency | <https://nomad.residencymalta.gov.mt/new-faqs/> | A · 政府/法律 | 2026-11-11 | 费用与周期原文：`a €300 non-refundable administrative fee for each applicant, via bank transfer`；`Application processing is expected to take 30 working days starting from the issuance of the receipt of funds`；资格补述 `18 years and over`、`a Third Country National, excluding EU, EEA and Switzerland`；排除名单 `Afghanistan, North Korea, Iran, Democratic Republic of Congo, Somalia, South Sudan, Sudan, Yemen and Venezuela are not eligible`，俄罗斯与白俄罗斯另有额外限制；家属 `this is not possible. However, dependants may be added when the MA is applying for renewal. Newborns are the sole exception`。 |

---

## 荷兰

### 荷兰毕业后求职居留

`nl-orientation-year` · 官方入口 <https://ind.nl/en/residence-permits/work/residence-permit-for-orientation-year>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Residence permit for orientation year — IND（含国籍分流后的完整条件） | 荷兰移民与归化局（IND） | <https://ind.nl/en/residence-permits/work/residence-permit-for-orientation-year> | A · 政府/法律 | 2026-11-08 | 页面标注 `Last update: 7 October 2026`。核心条件原文：`You completed one of the following study programmes in the 3 years before the date of application`；境外院校须 `Your educational institution is in the top 200 of the general rankings or the rankings by subject of at least 2 of the 3 publishers`；`Your educational institution is in the top 200 of these rankings on the date of your graduation or promotion`；`All foreign diplomas have to be evaluated by Nuffic before they can be accepted`；语言 `You obtained a minimum score of 6.0 on a test in the International English Language Testing System (IELTS). There are 2 versions of the IELTS: Academic and General Training. It does not matter which version you have.`；工作 `You may work freely in the Netherlands or do an internship. Your employer does not need a work permit`；期限 `The residence permit for the orientation year for highly educated persons is valid for 1 year.` 与 `You cannot extend the residence permit for the orientation year for highly educated persons.`；审理 `The IND must take a decision within 90 days.` 该页条件正文藏在国籍问答分流器里，静态 HTML 只显示引导语，须以 POST 提交 `nationality_1=Chinese (113)`、`valid_permit`、`expired_permit` 与 `form_build_id` 才能拿到完整条件。 |
| 2 | primary | Requirements that apply to everyone — IND | 荷兰移民与归化局（IND） | <https://ind.nl/en/requirements-that-apply-to-everyone> | A · 政府/法律 | 2026-11-08 | 页面标注 `Last update: 20 March 2026`。通用要求原文：`You have a valid passport or other travel document.`；`You do not pose a danger to public order or national security. Everyone over the age of 12 must completely fill in an Appendix Antecedents Certificate and enclose it with the application.`；`After you arrive in the Netherlands, you have to be tested for tuberculosis (TB).` 豁免含 `You already have a valid residence permit in the Netherlands and you are applying for a different residence permit.`、`You are 11 years of age or younger.`、`You took a TB test in the Netherlands less than 6 months ago.` 该页未列资金门槛——orientation year 类别在这一点上没有存款要求。 |
| 3 | primary | Fees: costs of an application — IND（orientation year 条目） | 荷兰移民与归化局（IND） | <https://ind.nl/en/fees-costs-of-an-application> | A · 政府/法律 | 2026-11-08 | 费用表 `Looking for a job after study, promotion or scientific research (orientation year)` 一行原文为 `First application or change in purpose of stay € 254,00`，另有 `Holder status long-term resident EU in another EU member state € 254,00`。与申请流程页 `The application costs € 254,00.` 一致。 |
| 4 | secondary | Language Test Appendix to the Code of Conduct（October 2026 版） | 荷兰国际教育合作组织（Nuffic）维护的 Code of Conduct 语言考试附录（由 IND 页面直接链接，本站非 .gov 域名，按二级来源登记） | <https://www.internationalstudy.nl/wp-content/uploads/2026/06/Language-Test-Appendix-to-the-Code-of-Conduct-October-2026.pdf> | C · 其他第三方 | 2026-11-08 | IND 页面把「其他可接受的英语考试等同 6.0」指向这份附录（`another accepted English language test that is listed in the Language tests appendix to the Code of Conduct`）。本条目只作为该指向的落点登记，具体分数换算须在递交时按当期版本核对。 |

---

## 挪威

### 挪威技术工人居留

`no-skilled-worker` · 官方入口 <https://www.udi.no/en/want-to-apply/work-immigration/skilled-workers/>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Skilled workers（挪威移民局官方页） | UDI（挪威移民局） | <https://www.udi.no/en/want-to-apply/work-immigration/skilled-workers/> | A · 政府/法律 | 2026-11-10 | 资格原文：`If you have completed higher education or have completed vocational training, you can apply for a residence permit as a skilled worker. You must normally already have received a job offer, or have your own business.`；三条路径 `a completed vocational training programme of at least three years at upper secondary school level ... There must be a corresponding vocational training programme in Norway.` / `completed education or degree from a university/ university college, for example a bachelor's degree as an engineer or nurse.` / `special qualifications are skills acquired through long professional experience ... Generally, you must have at least six years of work experience.`；聘用 `You must have received a concrete job offer from one specific employer in Norway.`、`The job must normally be full-time. If you have been offered at least an 80% position, we will accept this.`、`The pay and working conditions must not be poorer than is normal in Norway.`；期限 `you can normally get a residence permit for up to three years at a time`、`After three years, you can apply for a permanent residence permit in Norway.`；换岗与失业 `If you are later going to change employers, but work in the same type of position, you do not need to apply for a new residence permit.`、`If you lose your job, you can stay in Norway for up to six months to look for a new job. You must notify the police where you live within seven days.`；远程工作限制 `You are not allowed to work remotely unless it is part of the job you have been granted a residence permit to do.`；中国警示 `This currently applies in particular to applications for work as a chef, car mechanic, carpenter, painter, bricklayer, or hairdresser where the documentation submitted to attest to educational qualifications or the like were issued in Bangladesh, China, India, Iran, Kosovo, Nepal, Pakistan, Türkiye or Vietnam.` |
| 2 | primary | Fees（UDI 官方费用表） | UDI（挪威移民局） | <https://www.udi.no/en/word-definitions/fees/> | A · 政府/法律 | 2026-11-10 | 费用原文条目：`Residence permits for work for applicants over the age of 18 (also renewals)   NOK 6 300`；`Group permit for employers (per worker)   NOK 6 300`；`Residence permits for work for applicants under the age of 18 (also renewals)   NOK 3 150`。同页另有家庭团聚 `First-time application for family immigration for adults   NOK 11900`、永居 `Permanent residence permit for adults   NOK 4 000`。 |
| 3 | primary | Job seekers（挪威移民局官方页，说明求职居留不对境外开放） | UDI（挪威移民局） | <https://www.udi.no/en/want-to-apply/work-immigration/job-seekers/> | A · 政府/法律 | 2026-11-10 | 原文：`You must normally have received a job offer in Norway before you can apply for a residence permit for work purposes. If you are a skilled worker, you may in some exceptional cases get a residence permit to stay in Norway while you look for work.`；在挪威毕业者分支 `You must have completed your degree/education in Norway.`——即求职居留只对在挪威毕业或研究者开放。 |

---

## 新西兰

### 新西兰打工度假签证（中国名额）

`nz-china-whv` · 官方入口 <https://www.immigration.govt.nz/visas/china-working-holiday-visa/>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | China Working Holiday Visa | Immigration New Zealand | <https://www.immigration.govt.nz/visas/china-working-holiday-visa/> | A · 政府/法律 | 2026-10-30 | 中国大陆 WHV 全部硬条件：年龄 18-30、须为中国公民且常驻中国、申请时须在中国境内、未持过 NZ WHV、高中毕业学历、英语能力、资金 NZD 4,200、全程医疗保险、离境机票或等额资金、品行与健康要求；每年 1,000 个名额；费用 From NZD $770；审理 80% within 2 weeks；停留 12 个月；同一雇主不超过 6 个月；学习或培训合计不超过 6 个月；页面当前状态为 The China Working Holiday Visa is closed。语言部分官方只写：须能说并理解英语、递交后会被要求提供 acceptable English language test result、成绩不得超过 2 年 —— **未列具体分数线，故数据里记为未核实**。 |
| 2 | primary | 2026 opening dates for capped Working Holiday Schemes confirmed | Immigration New Zealand | <https://www.immigration.govt.nz/about-us/news-centre/2026-opening-dates-for-capped-working-holiday-schemes-confirmed> | A · 政府/法律 | 2026-10-16 | 2026 年各国家/地区开放日期与配额（中国大陆 2026-07-02 开放 1,000 个；中国香港 03-19 开放 400 个；中国台湾 05-28 开放 600 个） |
| 3 | primary | English language requirements for some working holiday visas（INZ 英语分数表） | Immigration New Zealand | <https://www.immigration.govt.nz/process-to-apply/applying-for-a-visa/providing-evidence-and-documents-to-support-your-visa-application/english-language-requirements/english-language-requirements-for-some-working-holiday-visas/> | A · 政府/法律 | 2026-11-08 | 中国打工度假签证的英语分数表原文：`IELTS Overall score of 5.5 or more`、`TOEFL iBT Overall score of 46 or more`、`PTE Academic Overall score of 42 or more`、`B2 First Overall score of 162 or more`、`B2 First for Schools Overall score of 162 or more`、`OET Grade C or higher in all 4 skills — listening, reading, writing and speaking.`；并规定 `your result must be no more than 2 years old at the time you apply`、`Tests taken remotely outside of a test centre, such as 'at home' tests are not acceptable.` |

### 新西兰毕业后工签

`nz-post-study-work` · 官方入口 <https://www.immigration.govt.nz/new-zealand-visas/visas/visa/post-study-work-visa>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Post Study Work Visa（新西兰移民局官方签证页） | Immigration New Zealand | <https://www.immigration.govt.nz/new-zealand-visas/visas/visa/post-study-work-visa> | A · 政府/法律 | 2026-11-08 | 总述与资格原文：`Apply for this visa if you want to work in New Zealand soon after you have completed your studies here. It allows you to stay and work in New Zealand for up to 3 years, depending on what you studied.`；`have recently finished studying in New Zealand for an approved qualification`；`have at least NZD $5,000 to pay your living expenses`。学历与就业原文：`work in New Zealand if you have a degree level 7 or higher qualification`；`a degree level 7 or higher qualification — level 8 postgraduate Diploma, level 9 masters degree or level 10 doctoral degree`；`If you have studied a degree level 7 or higher qualification, you must have studied it full-time for at least 30 weeks in New Zealand.`；非学位层级 `a non-degree level 7 or lower qualification that is on the list of qualifications eligible for a Post Study Work Visa — you must intend to work in a job that is related to what you studied`。一次性限制：`You can only have this visa once.` 申请窗口：`apply no later than 3, 6 or 12 months after your student visa expires`；`a doctoral degree, you must apply for a PSWV no later than 6 months after your student visa expires`。2026-11-16 变化：`From 16 November 2026, we will no longer accept paper applications for this visa. All applications from 16 November must be submitted online.`；`From 16 November 2026, Post Study Work Visa eligibility will be extended to applicants who have: an NZQCF level 7 graduate diploma that they studied full-time for in New Zealand, and a bachelor's degree that they completed in New Zealand or overseas.` 费用与审理：页面 `Cost` 栏 `NZD $1670`、`Processing time` 栏 `3.5 weeks`。体检与无犯罪：`If you will stay in New Zealand for more than 6 months, you must have a chest X-ray if you: are a citizen of a country that does not have a low incidence of tuberculosis (TB)`；`You must provide police certificates that are less than 6 months old when you apply if: your total time in New Zealand will be 24 months or longer.` |

---

## 瑞典

### 瑞典毕业后求职居留

`se-look-for-work` · 官方入口 <https://www.migrationsverket.se/en/you-want-to-apply/work/look-for-work/look-for-work-or-start-a-business.html>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Look for work or start a business（瑞典移民局官方页） | Migrationsverket（瑞典移民局） | <https://www.migrationsverket.se/en/you-want-to-apply/work/look-for-work/look-for-work-or-start-a-business.html> | A · 政府/法律 | 2026-11-10 | 资格与条件原文：`You have completed studies equivalent to a second-cycle qualification and want to come to Sweden to look for work or explore the possibilities for starting your own business here.`；第二周期定义 `it must correspond to either a 60-credit Master's degree, a 120-credit Master's degree, a professional degree worth 60–330 credits, or a postgraduate/PhD-level degree`；资金 `you must demonstrate that you have bank assets equivalent to at least SEK 13,000 for each month for which you are applying for a residence permit`；地点 `You must currently be located outside of Sweden`；期限 `You can be granted a residence permit for a maximum of nine months, but never for longer than your passport is valid.`；费用 `Fee: SEK 2,200`；审理 `Complete applications 75% of recently decided cases have been decided within: 5 months`；境内转工作许可 `If you get a job in Sweden during the permit period, you can apply for a work permit from within the country. You are not allowed to start working before you have applied for the new permit.` |
| 2 | primary | Employees — work permit（瑞典移民局官方页，用于转工作许可的薪资门槛） | Migrationsverket（瑞典移民局） | <https://www.migrationsverket.se/en/you-want-to-apply/work/employee-or-self-employed/employees.html> | A · 政府/法律 | 2026-11-10 | 薪资门槛原文：`you must have a monthly salary or wages of at least SEK 34,470`；同页新闻 `2026-06-16 New median salary affects the salary requirement for work permits Statistics Sweden (SCB) has now updated the median salary in Sweden. As of 16 June, the median salary is SEK 38,300, which means that you must have a salary/wages of at least SEK 34,470 (90 per cent of the median salary) a month in order to be granted a work permit.`；另有 `Certain professions are exempt from the salary requirement`，豁免后按中位薪资的 75% 计。 |
| 3 | primary | Look for work after completing your studies in Sweden（在瑞典毕业者的另一条路径） | Migrationsverket（瑞典移民局） | <https://www.migrationsverket.se/en/you-want-to-apply/work/look-for-work/look-for-work-after-completing-your-studies-in-sweden.html> | A · 政府/法律 | 2026-11-10 | 区分两条路径的原文：`If you have completed higher education studies in Sweden, you can apply for a residence permit to look for work or explore the possibilities of starting your own business.`——在瑞典毕业的人走这条，可从境内申请；本条记录收录的是「在境外完成学业、要来瑞典找工作」那条，两者条件不同。 |

---

## 新加坡

### 新加坡就业准证（Employment Pass）

`sg-employment-pass` · 官方入口 <https://www.mom.gov.sg/passes-and-permits/employment-pass/eligibility>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Eligibility for Employment Pass（新加坡人力部官方页，含薪资分档表） | Ministry of Manpower, Singapore | <https://www.mom.gov.sg/passes-and-permits/employment-pass/eligibility> | A · 政府/法律 | 2026-11-11 | 两阶段框架原文：`To qualify for EP applications, candidates will need to pass a 2-stage eligibility framework`；`Stage 1 Earn at least the EP qualifying salary, which is benchmarked to the top 1/3 of local PMET salaries by age.`；`Stage 2 Unless exempted, pass the points-based Complementarity Assessment Framework (COMPASS).`；硬性先后 `Candidates who do not meet stage 1 will not be eligible for an EP, regardless of the points they would have scored under COMPASS.`；FCF `Employers must continue to meet the Fair Consideration Framework (FCF) job advertising requirement before submitting new EP applications.`；薪资分档表（非金融业）当前 23 岁及以下 `$5,600`、45 岁及以上 `$10,700`，自 2027-01-01 起 `$6,000` 与 `$11,500`；金融服务业当前 `$6,200` 至 `$11,800`，新表 `$6,600` 至 `$12,700`；适用范围 `Minimum qualifying salary for new applications from 1 Jan 2027, and for renewal of passes expiring from 1 Jan 2028`；页面标注最后更新 2026-11-03。 |

### 新加坡 S 准证（S Pass）

`sg-s-pass` · 官方入口 <https://www.mom.gov.sg/passes-and-permits/s-pass/eligibility>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Eligibility for S Pass（新加坡人力部官方页） | Ministry of Manpower, Singapore | <https://www.mom.gov.sg/passes-and-permits/s-pass/eligibility> | A · 政府/法律 | 2026-11-11 | 面向所有国籍原文：`The S Pass is for foreign employees across all nationalities or citizenships who: Have a job offer in Singapore.`；薪资门槛 `Criteria include earning a salary of at least $3,300, which is benchmarked against the top one-third of the local associate professionals and technicians (APT) salaries by age.`；页面标注最后更新 2026-08-31。 |
| 2 | primary | Quota and levy for S Pass（配额与劳工税） | Ministry of Manpower, Singapore | <https://www.mom.gov.sg/passes-and-permits/s-pass/quota-and-levy> | A · 政府/法律 | 2026-11-11 | 配额机制原文：`You are limited by a quota and must pay the monthly foreign worker levy for each S Pass holder you employ.` 该页把配额比例与征费金额拆到下一层页面（Levy and quota requirements），本记录未抄具体比例，避免写死一个会变的数字。页面标注最后更新 2026-07-08。 |

### 新加坡打工度假计划

`sg-work-holiday-programme` · 官方入口 <https://www.mom.gov.sg/passes-and-permits/work-holiday-programme/eligibility>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Work Holiday Programme — Who is eligible（新加坡人力部） | Ministry of Manpower, Singapore | <https://www.mom.gov.sg/passes-and-permits/work-holiday-programme/eligibility> | A · 政府/法律 | 2026-11-03 | 资格原文四条：`You are aged 18 to 25 at the time of application.`；`You are an undergraduate or graduate of a university in Australia, France, Germany, Hong Kong, Japan, Netherlands, New Zealand, Switzerland, United Kingdom or United States.`；`Your university is recognised by the government of the respective ten countries or regions.`；本科生 `you have been a resident and a full-time student of the university for at least 3 months before applying for the pass`。名额与时长：`The Work Holiday Programme has a capacity of 2,000 pass holders at any one time.`、`stay and work in Singapore for up to 6 months`。**全页未出现 China（中国大陆），名单中为 Hong Kong。** |
| 2 | primary | Work Holiday Programme — How to apply（申请流程与费用） | Ministry of Manpower, Singapore | <https://www.mom.gov.sg/passes-and-permits/work-holiday-programme/apply-for-a-pass> | A · 政府/法律 | 2026-11-03 | 审理原文：`It takes around 3 weeks to process an application.`、`Within 4 weeks for most cases`。费用原文：`$175 for each pass`、`(If applicable) $30 for each Multiple Journey Visa`。材料原文：`A copy of the personal particulars page of your passport.`、`If the documents from your university are not in English, submit a copy of the original document and an official English translation certified by the university.`、`Each document's file size should not be more than 2MB.` 重复申请限制原文：`If you have held a Work Holiday Pass before, you can only reapply for another Work Holiday Pass after 12 months from the day you last held the pass.` 指纹登记：`Within 2 weeks after pass is issued (if required)`。 |
| 3 | primary | Work Holiday Programme — 概览页（项目定位与返程机票 FAQ） | Ministry of Manpower, Singapore | <https://www.mom.gov.sg/passes-and-permits/work-holiday-programme> | A · 政府/法律 | 2026-11-03 | 项目定位原文：`The Work Holiday Programme allows eligible students and young graduates to work and holiday in Singapore for 6 months.` FAQ 中出现 `Must my return travel ticket be back to my home country?`，说明返程机票属准证条件。页面标注更新日期 `26 December 2025`。 |

---

## 英国

### 英国毕业生签证

`uk-graduate-visa` · 官方入口 <https://www.gov.uk/graduate-visa>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Graduate visa — Overview（英国政府官网） | UK Visas and Immigration / GOV.UK | <https://www.gov.uk/graduate-visa> | A · 政府/法律 | 2026-11-03 | 时长原文：`A Graduate visa gives you permission to stay in the UK for at least 18 months after successfully completing an eligible course in the UK.`；`2 years if you apply on or before 31 December 2026`、`18 months if you apply on or after 1 January 2027`、`If you have a PhD or other doctoral qualification, it will last for 3 years.`；`You cannot extend your Graduate visa.` 费用原文：`pay the £937 application fee`、`pay the healthcare surcharge - this is usually £1,035 for each year you'll be in the UK`。审理原文：`you'll usually get a decision on your visa within 8 weeks`。可做与不可做：`work in most jobs`、`look for work`、`be self-employed`、`travel abroad and return to the UK`。 |
| 2 | primary | Graduate visa — Eligibility（资格条件） | UK Visas and Immigration / GOV.UK | <https://www.gov.uk/graduate-visa/eligibility> | A · 政府/法律 | 2026-11-03 | 四条须同时成立：`you're in the UK`、`your current visa is a Student visa or Tier 4 (General) student visa`、`you studied a UK bachelor's degree, postgraduate degree or other eligible course for a minimum period of time with your Student visa or Tier 4 (General) student visa`、`your education provider ... has told the Home Office you've successfully completed your course`。另：`You must apply before your Student visa or Tier 4 (General) student visa expires.` 与 `You do not have to wait until you've graduated or have been given a certificate.`。**该页与概览页均未设年龄限制、未要求单独提交语言成绩、未设存款门槛。** |

### 英国高潜力人才签证

`uk-hpi-visa` · 官方入口 <https://www.gov.uk/high-potential-individual-visa>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | High Potential Individual (HPI) visa — Overview（英国政府官网） | UK Visas and Immigration / GOV.UK | <https://www.gov.uk/high-potential-individual-visa> | A · 政府/法律 | 2026-11-08 | 时长原文：`A High Potential Individual (HPI) visa gives you permission to stay in the UK for 2 years.`、`An HPI visa lasts for 2 years. If you have a PhD or other doctoral qualification, it will last for 3 years.` 名额原文：`There is a yearly limit on applications for this visa. The application year runs between 1 November and 31 October. If the limit has been reached, you'll be told when you apply online.` 不可延期与永居不计入：`You cannot extend your HPI visa.`、`Your time on an HPI visa will not count as time spent in the UK if you apply to settle in the UK.` 审理原文：`3 weeks, if you're outside the UK`、`8 weeks, if you're inside the UK`。可做与不可做：`work in most jobs`、`look for work`、`be self-employed`、`do voluntary work`；`cannot: apply for most benefits ('public funds')`、`work as a professional sportsperson`。读书限制：`You can only study with an HPI visa if your chosen course is not eligible for a Student visa.` 递交窗口：`The earliest you can apply for a visa is 3 months before you travel.` |
| 2 | primary | High Potential Individual (HPI) visa — Eligibility（资格条件） | UK Visas and Immigration / GOV.UK | <https://www.gov.uk/high-potential-individual-visa/eligibility> | A · 政府/法律 | 2026-11-08 | 核心条件原文：`To be eligible for a High Potential Individual (HPI) visa, you must have been awarded a qualification by an eligible university.`；`UK universities are not eligible. If you're already in the UK on a student visa you may be able to apply for a Graduate visa.`；`You must have been awarded your qualification in the last 5 years.`；`You'll need to apply to Ecctis to check your qualification is valid and at the right level. Ecctis will not check if your university is eligible.`；`You do not need to have a job offer to apply.`；`You can apply for an HPI visa from inside the UK or outside the UK.`；`You can only apply for an HPI visa once.` 排除条件：`you have already been given a Graduate visa`、`you have already come to the UK as a Doctorate Extension Scheme student`。名单年度切换：`1 November 2026 to 31 October 2027` 至 `1 November 2021 to 31 October 2022` 共 6 个区间。 |
| 3 | primary | High Potential Individual (HPI) visa — How much it costs（费用与资金） | UK Visas and Immigration / GOV.UK | <https://www.gov.uk/high-potential-individual-visa/how-much-it-costs> | A · 政府/法律 | 2026-11-08 | 三笔费用原文：`pay £252 for Ecctis to check your qualification is valid (this includes VAT)`、`pay the £880 application fee`、`pay the healthcare surcharge - this is usually £1,035 for each year you'll be in the UK`；分档合计：`2 years - it will cost £2,070`、`3 years - it will cost £3,105`。资金原文：`you'll usually need to have at least £1,270 available (unless you're exempt)`、`You will need to have had the money available for at least 28 days in a row. Day 28 must be within 31 days of applying for this visa.`、`You'll usually need to show proof of this when you apply, unless you've been in the UK with a valid visa for at least 12 months.` |
| 4 | primary | High Potential Individual visa: global universities list 2026（2026 年度认可院校名单） | UK Visas and Immigration / GOV.UK | <https://www.gov.uk/government/publications/high-potential-individual-visa-global-universities-list/high-potential-individual-visa-global-universities-list-2026> | A · 政府/法律 | 2026-11-08 | 页面标注 `Updated 4 November 2026`，适用范围原文 `This list of universities relates to qualifications awarded between 1 November 2026 and 31 October 2027.` 名单共 82 所院校。中国大陆 8 所：`Fudan University`、`Harbin Institute of Technology`、`Nanjing University`、`Peking University`、`Shanghai Jiao Tong University`、`Tsinghua University`、`University of Science and Technology of China`、`Zhejiang University`。香港 5 所：`City University of Hong Kong (CityUHK)`、`The Chinese University of Hong Kong (CUHK)`、`The Hong Kong Polytechnic University`、`The Hong Kong University of Science and Technology`、`The University of Hong Kong`。榜单按字母排列并标注院校所属国家/地区，中国大陆条目全部标 `China`。 |

### 英国短期学习签证（英语课程）

`uk-short-term-study-visa` · 官方入口 <https://www.gov.uk/visa-to-study-english>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Short-term study visa: Overview — GOV.UK | UK Visas and Immigration (GOV.UK) | <https://www.gov.uk/visa-to-study-english> | A · 政府/法律 | 2026-11-01 | 总览页原文：`You may be eligible for a Short-term study visa if you're taking an English language course in the UK. To apply, your course must last longer than 6 months but not more than 11 months.`；停留 `You can stay in the UK for the length of your course plus an extra 30 days as long as your stay is no longer than 11 months.`；费用 `It costs £228 for a Short-term study visa.` + `It usually costs £776`（IHS）；禁止事项 `You cannot: ... work or carry out any business (this includes paid or unpaid work, work experience or work placements) ... extend this visa ... bring family members ('dependants') with you on this visa`。另说明 6 个月以内应申请 Visitor visa、超过 11 个月应申请 Student visa。 |
| 2 | primary | Short-term study visa: Who can apply — GOV.UK | UK Visas and Immigration (GOV.UK) | <https://www.gov.uk/visa-to-study-english/eligibility> | A · 政府/法律 | 2026-11-01 | 资格页原文：`You must be 16 or older to apply.`；须证明 `you've been accepted onto an English language course that lasts longer than 6 months and up to 11 months and includes no other subjects`、`your course is with an accredited institution`、`you have enough money to support yourself without working or help from public funds`、`you can pay for your return or onward journey`。未满 18 岁另需旅行住宿安排与父母/监护人同意。 |
| 3 | primary | Short-term study visa: Your course — GOV.UK | UK Visas and Immigration (GOV.UK) | <https://www.gov.uk/visa-to-study-english/your-course> | A · 政府/法律 | 2026-11-01 | 课程与机构认证要求原文：课程须与 `an 'accredited institution'` 合作，认证方式为持有学生担保牌照，或在 ASIC、Accreditation UK、British Accreditation Council、Education and Training Inspectorate、Estyn、Education Scotland、Independent Schools Inspectorate、Ofsted、Office for Students、QAA 名单内。另有「海外高校在英国开设部分课程」的路径，要求该机构 `hold its own national accreditation`、`offer no more than half of its educational programme in the UK`、`offer programmes that are equivalent to a UK degree`。 |
| 4 | primary | Short-term study visa: Documents you'll need — GOV.UK | UK Visas and Immigration (GOV.UK) | <https://www.gov.uk/visa-to-study-english/documents-you-must-provide> | A · 政府/法律 | 2026-11-01 | 材料清单原文：`a current passport`、`evidence that you can support yourself during your trip, for example bank statements or payslips for the last 6 months`、`details of where you intend to stay and your travel plans - you should not pay for accommodation or travel until you get your visa`、`evidence that you've paid your course fees or have enough money to pay them`、`your tuberculosis (TB) test results, if you're from a country where you have to take the TB test`、`a certified translation if any documents are not in English or Welsh`。 |
| 5 | primary | Short-term study visa: Apply — GOV.UK | UK Visas and Immigration (GOV.UK) | <https://www.gov.uk/visa-to-study-english/apply> | A · 政府/法律 | 2026-11-01 | 申请流程与审理时长原文：`The earliest you can apply is 3 months before you travel to the UK.`；`you'll usually get a decision within 3 weeks`；`You may be able to pay to get a faster decision.`；`You'll only get your fee refunded if UKVI has not started processing your application.` |
| 6 | primary | Countries where you need a TB test for your UK visa application — GOV.UK | UK Visas and Immigration (GOV.UK) | <https://www.gov.uk/tb-test-visa/countries-where-you-need-a-tb-test-to-enter-the-uk> | A · 政府/法律 | 2026-11-01 | TB 检查国家名单中 `China` 在列（名单按字母排序，China 位于 Chad、Cameroon、Congo 之后）。触发条件（TB test 总览页原文）：`you're coming to the UK for 6 months or more` 且 `you've lived in any of these listed countries for 6 months or more` 且 `you were living there (or another listed country) within the last 6 months`。证书有效期 6 个月。 |
| 7 | primary | Standard Visitor visa: permitted activities — GOV.UK | UK Visas and Immigration (GOV.UK) | <https://www.gov.uk/standard-visitor> | A · 政府/法律 | 2026-11-01 | 用于划清与访问签证的边界：访问签证可 `visit the UK ... for tourism, business, study (courses up to 6 months)`，可 `do a recreational course of up to 30 days`，但同样 `You cannot: do paid or unpaid work for a UK company`。即 6 个月以内短课程走访问签证，6–11 个月纯英语课程才走本签证，两条路径都禁止工作。 |

### 英国青年流动计划

`uk-youth-mobility-scheme` · 官方入口 <https://www.gov.uk/youth-mobility>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Youth Mobility Scheme visa | UK Visas and Immigration | <https://www.gov.uk/youth-mobility> | A · 政府/法律 | 2026-11-08 | YMS 参与国家/地区名单、年龄要求、资金要求 GBP 2,530、停留期 24 个月、费用结构 |
| 2 | primary | Youth Mobility Scheme visa: eligible countries and territories | UK Visas and Immigration (GOV.UK) | <https://www.gov.uk/youth-mobility/eligibility> | A · 政府/法律 | 2026-11-08 | 年龄分档原文：`You can apply for the visa if you're aged 18 to 35 and from: Australia, Canada, New Zealand, South Korea`；`You can apply for the visa if you're aged 18 to 30 and from: Andorra, Iceland, Japan, Monaco, San Marino, Uruguay`。判定口径：`You must be aged 18 or over when your visa starts, or 35 or under when you apply for it.` 抽签原文：`You must be selected in the Youth Mobility Scheme ballot before you can apply for your visa if you're from: Hong Kong, if you have an SAR passport; Taiwan`。排除情形：`children under the age of 18 who live with you`、`children you're financially responsible for`、`already been in the UK under the scheme`。资金原文：`You must have at least £2,530 in your bank account`、`You will need to have had the money available for at least 28 days in a row. Day 28 must be within 31 days of applying for this visa.` **全页未列 China（中国大陆）。** |
| 3 | primary | Youth Mobility Scheme visa: Documents you must provide | UK Visas and Immigration (GOV.UK) | <https://www.gov.uk/youth-mobility/documents-you-must-provide> | A · 政府/法律 | 2026-11-08 | 材料原文：`a valid passport or other document that shows your identity and nationality`、`a bank statement showing you have at least £2,530 in savings`、`your tuberculosis (TB) test results if you're from a country where you have to take the test`、`a certified translation of any documents that are not in English or Welsh`。按来源地追加：安道尔 `Andorran certificate of criminal records`、冰岛 `Icelandic criminal certificate for private use (called a Sakavottorð)`、圣马力诺外交部函、乌拉圭 `Uruguayan certificate of judicial records`，均须在申请前 6 个月内签发；中国香港/中国台湾须提供 `a valid email from the Home Office confirming you were successful in the Youth Mobility Scheme ballot`。 |
| 4 | primary | Pay for UK healthcare as part of your immigration application | UK Visas and Immigration (GOV.UK) | <https://www.gov.uk/healthcare-immigration-application/how-much-pay> | A · 政府/法律 | 2026-10-31 | 移民健康附加费（IHS）原文：`£776 per year for students, their dependants, and those on a Youth Mobility Scheme visa, for example £1,552 for a 2-year visa`。即 YMS 与 IHS 同价，2 年签证 1,552 英镑。 |

---

## 美国

### 美国 F-1 毕业后实习工作许可（OPT）

`us-f1-opt` · 官方入口 <https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors/optional-practical-training-opt-for-f-1-students>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Optional Practical Training (OPT) for F-1 Students — USCIS | U.S. Citizenship and Immigration Services (USCIS) | <https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors/optional-practical-training-opt-for-f-1-students> | A · 政府/法律 | 2026-11-08 | 时长原文：`Eligible students can apply to receive up to 12 months of OPT employment authorization before completing their academic studies (pre-completion) and/or after completing their academic studies (post-completion). However, all periods of pre-completion OPT will be deducted from the available period of post-completion OPT.` 折算规则：`If you spend one year in part-time pre-completion OPT, you will be deducted 6 months from your post-completion OPT. If you spend one year in full-time pre-completion OPT, you will be deducted 12 months ... and you will not have any remaining OPT.` 工时：pre-completion `you may work (20 hours or less per week) while school is in session. You may work full time when school is not in session.`；post-completion `you must work part time (at least 20 hours per week) or full time.` 递交窗口：`May apply up to 90 days before you complete your degree, but no later than 60 days after you complete your degree.` 与 `Must apply within 30 days after your DSO enters the recommendation`。流程：`Request that your designated school official (DSO) ... recommend the OPT`、`Properly file Form I-765, Application for Employment Authorization with USCIS`。 |
| 2 | primary | Optional Practical Training Extension for STEM Students (STEM OPT) — USCIS | U.S. Citizenship and Immigration Services (USCIS) | <https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors/optional-practical-training-extension-for-stem-students-stem-opt> | A · 政府/法律 | 2026-11-08 | 延期原文：`Certain F-1 students who receive science, technology, engineering, and mathematics (STEM) degrees may apply for a 24-month extension of their post-completion optional practical training (OPT).` 资格三条：`Have been granted OPT and currently be in a valid period of post-completion OPT`、`Have earned a bachelor's, master's, or doctoral degree from a school that is accredited by a U.S. Department of Education-recognized accrediting agency and is certified by the Student and Exchange Visitor Program (SEVP)`、雇主须 E-Verify。雇主义务：`Be enrolled in E-Verify`、`Remain a participant in good standing with E-Verify`、`Have a valid Employer Identification Number (EIN)`、`Report material changes ... by submitting a modified Form I-983 to the DSO`、`Report the STEM OPT student's termination of employment or departure to the DSO within 5 business days.`、`Provide an OPT opportunity that is commensurate with those of similarly situated U.S. workers in duties, hours, and compensation.` 查访：`DHS may, at its discretion, conduct a site visit of the employer`。培训计划：`The employer must attest to this fact by signing the Form I-983, Training Plan for STEM OPT Students.` 失业上限表：`Initial post-completion OPT only — Up to 90 days — 90 days`；`24-month extension — An additional 60 days — 150 days`。 |
| 3 | primary | 8 CFR 214.2(f) — Students in colleges, universities, and language training programs（美国联邦法规原文） | U.S. Government Publishing Office / National Archives（eCFR） | <https://www.ecfr.gov/current/title-8/chapter-I/subchapter-B/part-214/section-214.2> | A · 政府/法律 | 2026-11-08 | 失业上限原文：`Students may not accrue an aggregate of more than 90 days of unemployment during any post-completion OPT period`；`Students granted a 24-month OPT extension ... may not accrue an aggregate of more than 150 days of unemployment during a total OPT period`。工时原文：`While school is in session, provided that practical training does not exceed 20 hours a week while school is in session`。完成期限：`A student must complete all practical training within a 14-month period following the completion of study, except that a 24-month extension ... does not need to be completed within such 14-month period.` 自动终止：`Authorization to engage in optional practical training employment is automatically terminated when the student transfers to another school or begins study at another educational level.` 离境准备期：`An F-1 student who has completed a course of study and any authorized practical training will be allowed an additional 30-day period from the program end date ... to prepare for departure from the United States`。学历层级限制：`An alien who has completed a program after September 15, 2026, in the United States as an F-1 student at one educational level may not maintain, be admitted, or otherwise be provided F-1 status through a program at the same educational level or a lower educational level.` |
| 4 | primary | Form G-1055 — Fee Schedule（USCIS 费用表，2026-10-26 版） | U.S. Citizenship and Immigration Services (USCIS) | <https://www.uscis.gov/sites/default/files/document/forms/g-1055.pdf> | A · 政府/法律 | 2026-11-08 | Appendix C（I-765）原文：`General filing for initial, replacement, or renewal Employment Authorization Document (EAD), unless noted below. Fee determined based on how form is submitted. Paper Filing: $520  Online Filing: $470`。表头标 `Form G-1055  Edition 10/26/26`，共 60 页。仅适用于多数常规 EAD 情形，特定类别（如难民、庇护、TPS）另有减免或附加费，OPT 与 STEM-OPT 不适用那些例外。 |

### 美国 J-1 营地辅导员项目

`us-j1-camp-counselor` · 官方入口 <https://j1visa.state.gov/programs/camp-counselor/>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Camp Counselor — BridgeUSA（美国国务院） | U.S. Department of State, Bureau of Educational and Cultural Affairs | <https://j1visa.state.gov/programs/camp-counselor/> | A · 政府/法律 | 2026-11-03 | 项目定位与参与人资格：`The Camp Counselor Program enables post-secondary students, youth workers, and teachers to share their culture and ideas with the people of the United States in camp settings throughout the country.`；Participants 须 `Sufficiently proficient in the English language to supervise and interact with American youth`、`A foreign post-secondary student, youth worker, teacher or individual with specialized skills`、`At least 18-years-old`；Benefit 为 `pay and benefits commensurate with those offered to their American counterparts`。该页明确 `Camp Counselors will occasionally have to: Perform non-counseling duties as part of camp life, but not serve as "staff"`。**该页未公布年龄上限、签证费、项目费与审理时长。** |
| 2 | primary | 22 CFR 62.30 — Camp counselors（美国联邦法规原文） | U.S. Government Publishing Office / National Archives（eCFR） | <https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-62/subpart-B/section-62.30> | A · 政府/法律 | 2026-11-03 | 逐条原文：(b) 参与人资格 `limited to foreign nationals who: (1) Are at least 18 years of age; (2) Are bona fide youth workers, students, teachers, or individuals with specialized skills`；(c) Sponsor 须 `Conduct an in-person interview` 并向雇主或教师索取推荐；(e) 营地须为 ACA 会员、受认可非营利附属、或经 Sponsor 检查批准；(f) 薪酬须与美方同酬；(h)(2) `Not facilitate the entry of any participant for a program of more than four months duration`；(h)(3) `Under no circumstance facilitate the entry into the United States of a participant for whom a camp placement has not been pre-arranged`；(j) 参加两次以上者不得超过该 Sponsor 上年派出总数的 `ten percent`。**全文无年龄上限。** |
| 3 | primary | 22 CFR 62.14 — Insurance（保险最低额度） | U.S. Government Publishing Office / National Archives（eCFR） | <https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-62/subpart-B/section-62.14> | A · 政府/法律 | 2026-11-03 | 强制保险与最低额度：`Medical benefits of at least $100,000 per accident or illness`；`Repatriation of remains in the amount of $25,000`；`Expenses associated with the medical evacuation ... in the amount of $50,000`；`Deductibles not to exceed $500 per accident or illness`。 |
| 4 | primary | I-901 SEVIS Fee FAQ — How Much Is the I-901 SEVIS Fee? | U.S. Immigration and Customs Enforcement (ICE), Student and Exchange Visitor Program | <https://www.ice.gov/sevis/i901/faq> | A · 政府/法律 | 2026-11-03 | 费率表原文：`For exchange visitors (J-1) $220 UNLESS participating in:` … `Camp counselor program $35`。对照组：F-1/M-1 为 $350，J-2 为 None。另说明 `you must pay the I-901 SEVIS fee before going to the United States embassy or consulate for your visa interview`。 |
| 5 | primary | Camp Counselor Program Resource Page（项目时长与不可延期） | U.S. Department of State, Bureau of Educational and Cultural Affairs | <https://j1visa.state.gov/camp-counselor-program-resource-page/> | A · 政府/法律 | 2026-11-03 | `Camp Counselor participants are authorized to participate in the program for up to four months during the long break between academic years as determined by the Department of State. Extensions of program participation are not permitted.` 这是「不可延期」的直接原文依据，也是 4 个月上限的第二处佐证。 |
| 6 | primary | Designated Sponsor List By Program（官方指定 Sponsor 名录，按类别） | U.S. Department of State, Bureau of Educational and Cultural Affairs | <https://j1visa.state.gov/sponsors/designated-sponsor-list-by-program/> | A · 政府/法律 | 2026-11-08 | 官方表格共 4,133 行，按 Category 字段分组：Research Scholar 863、Short-Term Scholar 833、Student, College/University 785、Professor 750、Specialist 441、Intern 110、Trainee 94、Teacher 72、Student, Secondary 65、Summer Work/Travel 37、Camp Counselor 26、Government Visitor 26、International Visitor 16、Au Pair 14、Alien Physician 1。Camp Counselor 的 26 家为：ESF Dream Camp、CampGroup LLC、National Ramah Commission、Camp Counselors USA（CCUSA）、CHI Camp Leaders、CIEE、Concordia Language Villages、A Cultural Exchange Service、Alliance Abroad Group、Odyssey International Camp、Union for Reform Judaism Youth Division、American Institute For Foreign Study（Camp America）、Evangelical Lutheran Church in America、The Jewish Agency American Section、American Work Experience、Cultural Exchange Network、Global Educational Concepts（GEC）、LifeTRAVELED、United Studies、ELEVATE CULTURAL EXCHANGE、UNIWORLD、International Exchange of North America（IENA）、InterExchange、International Training and Exchange（Intrax）、JCC Association、LPC-US。注：该表是 serverSide 分页的 wpDataTables，前端需带页面内的 wdtNonceFrontendServerSide_45 才能取数；不带 nonce 直接请求 `admin-ajax.php?action=get_wdtable&table_id=45` 会返回 400 / 3 字节，这正是此前误判「站点表格失效、名单不可读」的原因。 |
| 7 | primary | 22 CFR 22.1 — Schedule of fees（美国领事服务收费表） | U.S. Government Publishing Office / National Archives（eCFR） | <https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-22/section-22.1> | A · 政府/法律 | 2026-11-03 | 领事服务收费表原文（22 CFR 22.1 第 21(a) 项）：`Non-petition-based nonimmigrant visa (except E category) $185`。J-1 交换访问学者签证属非 petition 类，按此费率缴纳；该表为国务院领事收费的法定依据，逐项列出护照、签证、公证等各类费用。 |

### 美国 J-1 实习项目

`us-j1-intern` · 官方入口 <https://j1visa.state.gov/programs/intern/>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Intern — BridgeUSA（美国国务院） | U.S. Department of State, Bureau of Educational and Cultural Affairs | <https://j1visa.state.gov/programs/intern/> | A · 政府/法律 | 2026-11-03 | 参与人资格原文：`Interns must be foreign nationals: Who are currently enrolled in and pursuing studies at a foreign degree- or certificate-granting post-secondary academic institution outside the United States; or Who have graduated from such an institution no more than 12 months prior to their exchange visitor program start date.` 限制原文：`Interns cannot work in unskilled or casual labor positions, in positions that require or involve childcare or elder care or in any kind of position that involves medical patient care or contact. Nor can interns work in positions that require more than 20 percent clerical or office support work.` 该页列出 10 个职业类别，并说明 Early Career STEM Research Initiative。**该页未公布年龄要求、签证费与审理时长。** |
| 2 | primary | 22 CFR 62.22 — Trainees and interns（美国联邦法规原文） | U.S. Government Publishing Office / National Archives（eCFR） | <https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-62/subpart-B/section-62.22> | A · 政府/法律 | 2026-11-03 | 时长原文：`the maximum duration of a training program is 18 months, and the maximum duration of an internship program is 12 months`，且 `Program extensions are permitted within the maximum duration ... provided that the need for an extended training or internship program is documented by the full completion and execution of a new Form DS-7002.` 选人标准原文：`Are currently enrolled full-time and pursuing studies in their advanced chosen career field at a degree- or certificate-granting post-secondary academic institution outside the United States or graduated from such an institution no more than 12 months prior to their exchange visitor program begin date.` 英语核验原文：`Sponsors must verify an applicant's English language proficiency through a recognized English language test, by signed documentation from an academic institution or English language school, or through a documented interview`。另有 DS-7002 须在签发 DS-2019 前完成全部签字的要求。**全文无年龄条款。** |
| 3 | primary | 22 CFR 62.14 — Insurance（保险最低额度） | U.S. Government Publishing Office / National Archives（eCFR） | <https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-62/subpart-B/section-62.14> | A · 政府/法律 | 2026-11-03 | 强制保险与最低额度：`Medical benefits of at least $100,000 per accident or illness`；`Repatriation of remains in the amount of $25,000`；`Expenses associated with the medical evacuation ... in the amount of $50,000`；`Deductibles not to exceed $500 per accident or illness`。 |
| 4 | primary | I-901 SEVIS Fee FAQ — How Much Is the I-901 SEVIS Fee? | U.S. Immigration and Customs Enforcement (ICE), Student and Exchange Visitor Program | <https://www.ice.gov/sevis/i901/faq> | A · 政府/法律 | 2026-11-03 | 费率表原文：`For exchange visitors (J-1) $220 UNLESS participating in:` … `Camp counselor program $35`。Intern 与 Trainee 属通则 J-1，适用 $220。另说明须在赴使领馆面签前缴纳。 |
| 5 | primary | 22 CFR 22.1 — Schedule of fees（美国领事服务收费表） | U.S. Government Publishing Office / National Archives（eCFR） | <https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-22/section-22.1> | A · 政府/法律 | 2026-11-03 | 领事服务收费表原文（22 CFR 22.1 第 21(a) 项）：`Non-petition-based nonimmigrant visa (except E category) $185`。J-1 交换访问学者签证属非 petition 类，按此费率缴纳；该表为国务院领事收费的法定依据，逐项列出护照、签证、公证等各类费用。 |

### 美国 J-1 研究学者

`us-j1-research-scholar` · 官方入口 <https://j1visa.state.gov/programs/research-scholar/>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Research Scholar（美国国务院 J-1 官方项目页） | U.S. Department of State, Bureau of Educational and Cultural Affairs | <https://j1visa.state.gov/programs/research-scholar/> | A · 政府/法律 | 2026-11-08 | 三条禁令原文：`Not be a candidate for a tenure track position`；`Not have participated in and completed a research scholar program within the last 24 months preceding the beginning date`；`Not have participated in a J-Visa program for all or part of the 12-month period immediately preceding the start date`。身份要求：`Be a professor or research scholar or someone with similar education and or experience.` 临时性：`The research scholar's appointment to a position shall be temporary, even if the position itself is permanent.` 教学许可：`A research scholar may also teach or lecture, unless disallowed by the sponsor.` Sponsor 义务：`Ensure that the exchange participants and his/her dependents, if any, are covered by health insurance`；`Ensure that exchange visitors have sufficient finances to participate in the program and to support their spouse and dependents, if any.`；`Ensure that the foreign national is successfully carrying out the responsibilities for which entry to the United States was granted` |
| 2 | primary | 22 CFR 62.20 — Professors and research scholars（联邦法规原文） | U.S. Government Publishing Office / eCFR（Electronic Code of Federal Regulations） | <https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-22?part=62&section=62.20> | A · 政府/法律 | 2026-11-08 | 5 年上限原文：`A professor or research scholar may be authorized to participate in the Exchange Visitor Program for the length of time necessary to complete his or her program, provided such time does not exceed five years. The five-year period ... is continuous and begins with the initial program begin date documented in SEVIS`。重复参加禁令：`Repeat participation ... are not eligible for participation as a professor or research scholar for a period of two years following the end date`。延长期限：`A responsible officer may not extend the period of program duration beyond the five-year period`。活动变更：`professors may freely engage in research and research scholars may freely engage in teaching and lecturing ... does not extend the exchange visitor's maximum duration` |
| 3 | primary | 22 CFR 62.10 — Program administration（英语能力核验） | U.S. Government Publishing Office / eCFR（Electronic Code of Federal Regulations） | <https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-22?part=62&section=62.10> | A · 政府/法律 | 2026-11-08 | Sponsor 须以客观方式核验英语能力，法规原文要求英语熟练度须经 `objective measurement` 确认，具体衡量方式与合格标准由 Sponsor 设定，法规未指定统一考试或分数线。 |
| 4 | primary | SEVIS I-901 Fee（美国移民与海关执法局费率页） | U.S. Immigration and Customs Enforcement (ICE), Student and Exchange Visitor Program | <https://www.ice.gov/sevis/i901/faq> | A · 政府/法律 | 2026-11-08 | 费率原文：`For exchange visitors (J-1) $220 UNLESS participating in:` … `Summer work/travel program $35`、`Au pair program $35`、`Camp counselor program $35`。学生类为 `For students (F-1, F-3, M-1 or M-3) $350`。须在面签前缴纳。 |
| 5 | primary | 22 CFR 22.1 — Schedule of fees（美国领事服务收费表） | U.S. Government Publishing Office / eCFR（Electronic Code of Federal Regulations） | <https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-22?part=22&section=22.1> | A · 政府/法律 | 2026-11-08 | 第 21 项原文：`Nonimmigrant Visa Application and Border Crossing Card Processing Fees (per person): (a) Non-petition-based nonimmigrant visa (except E category) $185 (b) H, L, O, P, Q and R category nonimmigrant visa 205 (c) E category nonimmigrant visa 315 (d) K category (fiancé) nonimmigrant visa $265`。J-1 属第 (a) 项，签证费 $185。 |

### 美国 J-1 暑期带薪实习项目

`us-j1-summer-work-travel` · 官方入口 <https://j1visa.state.gov/programs/summer-work-travel/>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Summer Work Travel — BridgeUSA（美国国务院） | U.S. Department of State, Bureau of Educational and Cultural Affairs | <https://j1visa.state.gov/programs/summer-work-travel/> | A · 政府/法律 | 2026-10-30 | SWT 项目规则：Sponsor 须为来自非免签国的参与者提供预先安排并已审查的岗位、须在入境前提供项目手册/24 小时紧急热线/联系人、须告知最低工资与加班义务、须每月与参与者保持联系；含 Program Exclusions 岗位排除清单（不得安排进有损项目声誉的岗位、不得进入需自购库存再销售的销售岗等）；官方另发 2024 Program Date Chart。**该页未公布年龄上限、项目费与审理时长**，官方也无独立的资格子页（/eligibility 为 404）。 |
| 2 | secondary | SWT 项目宣讲通知（西安理工大学国际合作与交流处） | 西安理工大学国际合作与交流处 | <https://oice.xaut.edu.cn/info/1146/2290.htm> | C · 高校官网 | 2026-10-16 | 中国高校引进该项目的落地口径（18-28 周岁全日制在校本科生/研究生）、费用结构、申请流程、工作时间 6月15日-9月15日（高校官方部门来源，反映中方实际操作） |

### 美国 J-1 培训项目

`us-j1-trainee` · 官方入口 <https://j1visa.state.gov/programs/trainee/>

| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |
|---|---|---|---|---|---|---|---|
| 1 | primary | Trainee — BridgeUSA（美国国务院） | U.S. Department of State, Bureau of Educational and Cultural Affairs | <https://j1visa.state.gov/programs/trainee/> | A · 政府/法律 | 2026-11-03 | 参与人资格原文：`Has a degree or professional certificate from a foreign post-secondary academic institution and at least one year of prior related work experience in his or her occupational field outside the United States; or Has five years of work experience outside the United States in the occupational field in which they are seeking training`。限制原文：`Trainees cannot work in unskilled or casual labor positions, in positions that require or involve childcare or elder care, or in any kind of position that involves patient care or contact.` `Use of the Exchange Visitor Program for ordinary employment or work purposes is strictly prohibited.` `the training cannot duplicate a trainee participant's prior work experience or training.` |
| 2 | primary | 22 CFR 62.22 — Trainees and interns（美国联邦法规原文） | U.S. Government Publishing Office / National Archives（eCFR） | <https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-62/subpart-B/section-62.22> | A · 政府/法律 | 2026-11-03 | 时长原文：`the maximum duration of a training program is 18 months`；`For training programs in the field of agriculture and in the occupational category of Hospitality and Tourism, the maximum duration of program participation is 12 months.`；`12-month training programs in the field of agriculture may not be extended to 18 months by adding six months of classroom participation and studies at the end of the original 12-month program duration.` 再参加条件原文：`Trainees are eligible for additional training programs after a period of at least two years residency outside the United States following completion of their training program.` |
| 3 | primary | 22 CFR 62.14 — Insurance（保险最低额度） | U.S. Government Publishing Office / National Archives（eCFR） | <https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-62/subpart-B/section-62.14> | A · 政府/法律 | 2026-11-03 | 强制保险与最低额度：医疗不低于 $100,000、遗体送返 $25,000、医疗转运 $50,000、自付额不超过 $500。 |
| 4 | primary | I-901 SEVIS Fee FAQ — How Much Is the I-901 SEVIS Fee? | U.S. Immigration and Customs Enforcement (ICE), Student and Exchange Visitor Program | <https://www.ice.gov/sevis/i901/faq> | A · 政府/法律 | 2026-11-03 | J-1 通则 $220；仅 Summer work/travel、Au pair、Camp counselor 三类为 $35，Trainee 不在减免名单内。 |
| 5 | primary | 22 CFR 22.1 — Schedule of fees（美国领事服务收费表） | U.S. Government Publishing Office / National Archives（eCFR） | <https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-22/section-22.1> | A · 政府/法律 | 2026-11-03 | 领事服务收费表原文（22 CFR 22.1 第 21(a) 项）：`Non-petition-based nonimmigrant visa (except E category) $185`。J-1 交换访问学者签证属非 petition 类，按此费率缴纳；该表为国务院领事收费的法定依据，逐项列出护照、签证、公证等各类费用。 |

---

## 来源可靠性分级

| 级别 | 定义 | 判定依据 |
|---|---|---|
| **A（最高）** | 目的地国家政府官网、法律文本 | `OFFICIAL_GOV_FRAGMENTS`：`.gov` `.gov.uk` `.go.jp` `.go.kr` `canada.ca` `homeaffairs.gov.au` `immigration.govt.nz` `irishimmigration.ie` `ireland.ie` `make-it-in-germany.com` `verwaltung.bund.de` `diplo.de` `gesetze-im-internet.de` `state.gov` `europa.eu` `un.org` 等 |
| **B** | 项目本体国际组织官网 | `OFFICIAL_ORG_FRAGMENTS`：`iaeste.org` `iaeste.at` `iaeste.de` `aiesec.org` |
| **C（高校）** | 高校官网 —— 可核验，但不单独支撑硬性判定 | `ACADEMIC_FRAGMENTS`：`.edu` `.ac.uk` `.edu.cn` `.edu.hk` `.edu.mo` `.edu.tw` `.ac.jp` `.ac.kr` `.ac.nz` `.edu.au` `.ac.at` `.edu.sg`，按主机名后缀匹配 |
| **C（其他）** | 商业站、中介站等 —— 与高校同为 C，但可信程度不同，按域名分辨 | 未命中以上任何名单 |
| **D（禁止使用）** | 百科、自媒体、商业博客、来源不明 | `FORBIDDEN_SOURCE_DOMAINS` |

**本数据集要求：** 每条资格数据至少由 A 或 B 级来源支撑。C 级仅作补充说明。**D 级严禁作为数据来源。**

> C 级为何要再分一层：2026-11-01 实测 `ox.ac.uk` 与 `study-abroad.cn` 同为 C 级，规则分不开「大学官网」与「留学中介站」。分级本身不改（两者都不能单独支撑硬性判定），但读者需要知道自己在看哪一种。

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
