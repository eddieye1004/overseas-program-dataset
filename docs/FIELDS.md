# 字段词典（FIELDS）

> 本文件是 `data/programs/*.json` 的字段词典。它回答三个问题：每个字段定义是什么、在本仓库 41 个项目文件里实际怎么用、哪些字段的实测用法与定义对不上。
>
> - **数据基线**：`main@d89e19b`（2026-11-14；`data/programs` 与 `1c721f1` 相同，PR 也基于该提交），`data/programs/` 下 41 个 JSON 文件、10,804 行、6,727 个叶子值。
> - **定义来源**：`data/schema.json`（v0.1.0，437 行）与 `scripts/validate.py`（1,329 行手写校验器）。schema 是字段结构的权威定义；validator 是 CI 实际执行的规则。两者不一致之处，本文分别标注。
> - **核对范围**：41/41 个文件逐字段解析；每个字段给出出现文件数、条数、取值分布，以及至少一条真实原值示例。
> - **本文件只报告**，不改数据、不改校验器。本单只新增 `docs/FIELDS.md` 一个文件。

**阅读口径**

- `n/41`：41 个文件中有 n 个出现该键（显式 `null` 也算出现）。对数组项字段（如 `documents[].name`），指「该数组非空且项内有此键」的文件数。
- 「条」：数组元素或标量值的累计数量。「非空」：非 `null`、非空数组、非空字符串。
- 示例：给出文件名与该字段的真实原值；内联示例保留完整原值；超过 400 字符的散文/长 JSON 只截取原文前缀并标 `…（节选，原文 N 字符）`，可凭文件名回查全文。
- 枚举：`代码` = 中文含义。数组项枚举（如 `program.tags`）在字段条目下列出全部合法值。

**核对时基线（2026-11-14）**

| 检查 | 命令 | 结果 |
|---|---|---|
| 单元测试 | `python -m unittest discover -s tests` | `Ran 181 tests`，`OK` |
| 数据校验 | `python scripts/validate.py` | 0 error / 0 warning / 2 info |
| 来源清单 | `python scripts/gen_sources.py --check` | 136 条来源与数据一致 |
| 匹配判定产物 | `python scripts/match_readiness.py --check` | `rules_version 6` 一致 |
| 复核台账 | `python scripts/track.py` | 可正常生成 |

> 本单只新增 Markdown，因此不新增任何测试；上述结果是核对前的 `main` 基线。

## 目录

1. 顶层字段
2. `program`：项目基本信息
3. `eligibility`：资格条件
4. `timeline`：时间、配额与费用
5. `documents[]`：材料清单
6. `steps[]`：申请流程
7. `work_conditions`：持证后的工作与学习限制
8. `risks[]`：风险提示
9. `sources[]`：来源列表
10. 公共类型与联动规则
11. 实测与定义不一致清单
12. 核对方法与复现
- 附录 A：41 个文件清单
- 附录 B：全部字段总览

## 1. 顶层字段

顶层是必填的 JSON 对象，schema 要求 8 个必填键（`schema_version`、`program`、`eligibility`、`timeline`、`documents`、`steps`、`sources`、`last_verified`）和 3 个可选键（`work_conditions`、`risks`、`verified_by`）。实测 41/41 个文件都带全部 11 个键。其余 8 个键是容器或数组（`program`/`eligibility`/`timeline`/`documents`/`steps`/`sources` 必填，`work_conditions`/`risks` 可选），分别在后续章节展开；本节只列 3 个标量键。

### `schema_version`

- **类型 / 必填**：`string` / 是
- **定义**：schema 版本号，固定为 `0.1.0`。
- **实测**：41/41 个文件出现；共 1 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `schema_version` 原值：`0.1.0`。
- **校验器补充**：校验器还要求值必须等于 `0.1.0`。

### `last_verified`

- **类型 / 必填**：`string` / 是
- **定义**：该文件最后一次核实官方来源的日期（`YYYY-MM-DD`）。
- **实测**：41/41 个文件出现；共 6 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `last_verified` 原值：`2026-11-09`。
- **校验器补充**：校验器要求真实日期；距今超过 180 天给 warning，超前 1 天以上（本地/UTC 时区容错）给 error。

### `verified_by`

- **类型 / 必填**：`string` / 否
- **定义**：核实人 GitHub 用户名。
- **实测**：41/41 个文件出现；共 1 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `verified_by` 原值：`eddieye1004`。

## 2. `program`：项目基本信息

`program` 共 13 个键，schema 必填 8 个（`id`/`name`/`name_en`/`country`/`country_code`/`region`/`program_type`/`official_url`），可选 5 个（`visa_code`/`authority`/`summary`/`tags`/`active`）——实测全部 41 个文件都填满 13 个键。`id` 全库唯一且与文件名一致；`region` 仅使用 5 个值；`program_type` 覆盖全部 5 类；`tags` 共 164 项、19 种（枚举共 21 种）；`active=false` 出现 3 次（含义见 §11.3）。

### `program`

- **类型 / 必填**：`object` / 是
- **定义**：项目基本信息容器，必填，不允许额外键。
- **实测**：41/41 个文件出现；结构由下列子字段定义。
- **示例**：`at-rwr-card-vhq.json` 的 `program` 原文节选（对象共 13 个键，此处列前 8 个）：
  ```json
  {"id": "at-rwr-card-vhq", "name": "奥地利红白红卡（高资质）", "name_en": "Red-White-Red Card — Very Highly Qualified Workers", "country": "奥地利", "country_code": "AT", "region": "europe", "program_type": "short_term_work", "visa_code": "Rot-Weiß-Rot – Karte (VHQ) / Job Seeker Visa (D)"}
  ```
  （节选，原文 720 字符）

### `program.id`

- **类型 / 必填**：`string` / 是
- **定义**：项目唯一标识：小写连字符格式；同时是文件名（去掉 `.json`）与全库唯一键。
- **实测**：41/41 个文件出现；每个文件各不相同。
- **示例**：`at-rwr-card-vhq.json` 的 `program.id` 原值：`at-rwr-card-vhq`。
- **校验器补充**：校验器校验小写连字符正则、全库唯一；与文件名不一致只给 warning（实测 41/41 一致）。

### `program.name`

- **类型 / 必填**：`string` / 是
- **定义**：项目中文名称，用于展示与检索。
- **实测**：41/41 个文件出现；每个文件各不相同。
- **示例**：`at-rwr-card-vhq.json` 的 `program.name` 原值：`奥地利红白红卡（高资质）`。

### `program.name_en`

- **类型 / 必填**：`string` / 是
- **定义**：项目英文名称，通常取官方名称。
- **实测**：41/41 个文件出现；每个文件各不相同。
- **示例**：`at-rwr-card-vhq.json` 的 `program.name_en` 原值：`Red-White-Red Card — Very Highly Qualified Workers`。

### `program.country`

- **类型 / 必填**：`string` / 是
- **定义**：国家/地区中文名；全球性项目写作「全球（…）」。
- **实测**：41/41 个文件出现；共 23 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `program.country` 原值：`奥地利`。

### `program.country_code`

- **类型 / 必填**：`string` / 是
- **定义**：ISO 3166-1 alpha-2 国家代码；schema 规定全球性项目用 `GL`（该用法的实测问题见 §11.3）。
- **实测**：41/41 个文件出现；共 22 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `program.country_code` 原值：`AT`。

### `program.region`

- **类型 / 必填**：`string` / 是
- **定义**：项目所属地理区域。
- **取值**：`oceania`=大洋洲；`asia`=亚洲；`europe`=欧洲；`north_america`=北美洲；`south_america`=南美洲；`africa`=非洲；`global`=全球性项目
- **实测**：41/41 个文件出现；取值分布：`europe` 20、`north_america` 8、`oceania` 6、`asia` 5、`global` 2；全部取值都在 schema 枚举内。
- **示例**：`at-rwr-card-vhq.json` 的 `program.region` 原值：`europe`。

### `program.program_type`

- **类型 / 必填**：`string` / 是
- **定义**：项目类型。
- **取值**：`working_holiday`=打工度假；`paid_internship`=带薪实习；`internship_visa`=实习签证；`cultural_exchange`=文化交流；`short_term_work`=短期工作 / 求职居留
- **实测**：41/41 个文件出现；取值分布：`short_term_work` 22、`working_holiday` 9、`paid_internship` 5、`cultural_exchange` 3、`internship_visa` 2；全部取值都在 schema 枚举内。
- **示例**：`at-rwr-card-vhq.json` 的 `program.program_type` 原值：`short_term_work`。

### `program.visa_code`

- **类型 / 必填**：`string` / 否
- **定义**：签证/许可代号，例如 `462`、`J-1`、`§16e`。
- **实测**：41/41 个文件出现；共 37 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `program.visa_code` 原值：`Rot-Weiß-Rot – Karte (VHQ) / Job Seeker Visa (D)`。

### `program.official_url`

- **类型 / 必填**：`string` / 是
- **定义**：项目官方主页 URL，必须 `http(s)://`；会纳入链接存活检查。
- **实测**：41/41 个文件出现；每个文件各不相同。
- **示例**：`at-rwr-card-vhq.json` 的 `program.official_url` 原值：
  ```text
  https://www.migration.gv.at/en/types-of-immigration/permanent-immigration/very-highly-qualified-workers/
  ```

### `program.authority`

- **类型 / 必填**：`string` / 否
- **定义**：主管机构（官方机构名）。
- **实测**：41/41 个文件出现；共 33 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `program.authority` 原值：`奥地利劳动与经济部 / 联邦劳动局（AMS）/ 各地居留管理局`。

### `program.summary`

- **类型 / 必填**：`string` / 否
- **定义**：项目简介，schema 描述要求 200 字以内（实测有 5 个文件超出，见 §11.3）。
- **实测**：41/41 个文件出现；每个文件各不相同。
- **示例**：`at-rwr-card-vhq.json` 的 `program.summary` 原值：
  ```text
  奥地利的高资质人才通道：按 100 分制打分，满 70 分即可。没有工作邀请也能先申请 6 个月的找工作签证入境，期间找到对口岗位再换成 24 个月的红白红卡；持卡满 21 个月可换 unlimited 的红白红卡 plus。中国大陆护照不受国籍限制，真正的门槛是积分——学历是否属于 MINT 学科、年龄是否在 35 岁以下。
  ```
- **校验器补充**：校验器仅当长度 >500 字符时告警（schema 描述为 200 字以内），两者阈值不一致。

### `program.tags`

- **类型 / 必填**：`array（string）` / 否
- **定义**：项目标签数组，用于前端筛选与快速识别；每一项必须来自 schema 枚举。
- **取值**：`no_quota_cap`=无名额上限；`ballot_required`=需抽签；`first_come_first_served`=先到先得；`rolling`=滚动受理；`once_in_lifetime`=一生一次；`renewable`=可续签；`requires_agency`=需中介/机构；`no_agency_needed`=无需中介；`farm_work_available`=有农场工作；`high_wage`=高薪；`low_cost`=低成本；`requires_degree`=需学位；`stem_friendly`=STEM 友好；`high_demand`=高需求；`cultural_exchange`=文化交流；`engineering_friendly`=工程友好；`paid`=带薪；`unpaid`=无薪；`english_required`=需英语；`no_english_required`=无需英语；`residency_required`=需居住/户籍
- **实测**：41/41 个文件出现，41 个非空；共 164 项，去重 19 个；取值分布：`no_quota_cap` 34、`no_agency_needed` 30、`requires_degree` 26、`english_required` 11、`high_wage` 10、`stem_friendly` 9、`rolling` 9、`requires_agency` 8、`renewable` 5、`high_demand` 5。
- **示例**：`at-rwr-card-vhq.json` 的 `program.tags` 原值：`["requires_degree", "stem_friendly", "high_wage", "no_agency_needed"]`。
- **校验器补充**：校验器校验标签枚举，并与 `timeline.quota_status` 交叉检查：`no_quota_cap` 不得与 `capped`/`not_published` 同现，`no_quota` 应带 `no_quota_cap`。

### `program.active`

- **类型 / 必填**：`boolean` / 否
- **定义**：项目当前是否开放；`false` 在实测中的实际含义与 schema 描述不完全一致（见 §11.3）。
- **实测**：41/41 个文件出现；`true` 38、`false` 3。
- **示例**：`at-rwr-card-vhq.json` 的 `program.active` 原值：`true`。

## 3. `eligibility`：资格条件

`eligibility` 由 5 个必填子对象和 `other_requirements` 数组组成。实测：中国大陆护照 `eligible` 34 个、`not_eligible` 7 个；年龄 `(0,99)` 的组合 25 个（哨兵值，见 §11.3）；`language.required=true` 16 个，但只有 4 个文件列出考试；`funds.required=true` 20 个，只有 13 个文件给出金额；`other_requirements` 共 140 条、11 种类型全部用到。

### `eligibility`

- **类型 / 必填**：`object` / 是
- **定义**：资格条件容器，必填；用于匹配引擎的硬性排除。
- **实测**：41/41 个文件出现；结构由下列子字段定义。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility` 原文节选（对象共 6 个键，此处列前 1 个）：
  ```json
  {"passport_types": {"mainland_china": "eligible", "hong_kong_china": "eligible", "taiwan_china": "eligible", "note": "法规未按国籍设限，中国大陆护照持有人可申。两条硬门槛：①高等教育学历的课程时长不少于四年（三年制学历走「短缺职业技术工人」或「其他关键岗位」两条通道，门槛为 55 分）；②积分达到 70 分（满分 100）。"}}
  ```
  （节选，原文 1432 字符）

### `eligibility.passport_types`

- **类型 / 必填**：`object` / 是
- **定义**：护照资格容器；其中 `mainland_china` 是全库最关键的字段。
- **实测**：41/41 个文件出现；结构由下列子字段定义。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.passport_types` 原文节选：
  ```json
  {"mainland_china": "eligible", "hong_kong_china": "eligible", "taiwan_china": "eligible", "note": "法规未按国籍设限，中国大陆护照持有人可申。两条硬门槛：①高等教育学历的课程时长不少于四年（三年制学历走「短缺职业技术工人」或「其他关键岗位」两条通道，门槛为 55 分）；②积分达到 70 分（满分 100）。"}
  ```
- **校验器补充**：校验器额外要求必须存在 `mainland_china` 键；但只检查三个已知键，不检查 `additionalProperties`（见 §11.1）。

### `eligibility.passport_types.mainland_china`

- **类型 / 必填**：`string` / 是
- **定义**：中国大陆护照持有人能否申请。
- **取值**：`eligible`=可申请；`not_eligible`=不可申请（显式排除）；`conditional`=有条件开放；`unknown`=尚未核实
- **实测**：41/41 个文件出现；取值分布：`eligible` 34、`not_eligible` 7；全部取值都在 schema 枚举内。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.passport_types.mainland_china` 原值：`eligible`。

### `eligibility.passport_types.hong_kong_china`

- **类型 / 必填**：`string` / 否
- **定义**：中国香港护照持有人能否申请。
- **取值**：`eligible`=可申请；`not_eligible`=不可申请（显式排除）；`conditional`=有条件开放；`unknown`=尚未核实
- **实测**：41/41 个文件出现；取值分布：`eligible` 39、`not_eligible` 1、`unknown` 1；全部取值都在 schema 枚举内。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.passport_types.hong_kong_china` 原值：`eligible`。

### `eligibility.passport_types.taiwan_china`

- **类型 / 必填**：`string` / 否
- **定义**：中国台湾护照持有人能否申请；实测另有 12 个文件使用未定义的 `tw_china`（见 §11.1）。
- **取值**：`eligible`=可申请；`not_eligible`=不可申请（显式排除）；`conditional`=有条件开放；`unknown`=尚未核实
- **实测**：29/41 个文件出现；取值分布：`eligible` 27、`not_eligible` 2；全部取值都在 schema 枚举内；其余 12 个文件未填该键。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.passport_types.taiwan_china` 原值：`eligible`。

### `eligibility.passport_types.note`

- **类型 / 必填**：`string` / 否
- **定义**：护照资格的补充说明
- **实测**：41/41 个文件出现；每个文件各不相同。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.passport_types.note` 原值：
  ```text
  法规未按国籍设限，中国大陆护照持有人可申。两条硬门槛：①高等教育学历的课程时长不少于四年（三年制学历走「短缺职业技术工人」或「其他关键岗位」两条通道，门槛为 55 分）；②积分达到 70 分（满分 100）。
  ```

### `eligibility.age`

- **类型 / 必填**：`object` / 是
- **定义**：年龄条件容器。
- **实测**：41/41 个文件出现；结构由下列子字段定义。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.age` 原文节选：
  ```json
  {"min": 0, "max": 99, "note": "不设年龄上下限，只影响积分：申请时未满 35 岁得 20 分，未满 40 岁得 15 分，未满 45 岁得 10 分；45 岁及以上该项不得分，但仍可申请，只要其余项目补足 70 分。0-99 表示「无年龄门槛」，不是「未核实」。"}
  ```
- **校验器补充**：校验器额外校验 `min`/`max` 为整数且 `min <= max`。

### `eligibility.age.min`

- **类型 / 必填**：`integer` / 是
- **定义**：年龄下限（含边界）。实测 `0` 表示「不限下限」的哨兵值，不是真实年龄（见 §11.3）。
- **实测**：41/41 个文件出现；取值为 `0`、`16`、`18`。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.age.min` 原值：`0`。

### `eligibility.age.max`

- **类型 / 必填**：`integer` / 是
- **定义**：年龄上限（含边界）。实测 `99` 表示「不限上限 / 无统一上限」的哨兵值（见 §11.3）。
- **实测**：41/41 个文件出现；取值为 `25`、`30`、`34`、`35`、`99`。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.age.max` 原值：`99`。

### `eligibility.age.note`

- **类型 / 必填**：`string` / 是
- **定义**：如'递交时须未满31岁'
- **实测**：41/41 个文件出现；共 36 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.age.note` 原值：
  ```text
  不设年龄上下限，只影响积分：申请时未满 35 岁得 20 分，未满 40 岁得 15 分，未满 45 岁得 10 分；45 岁及以上该项不得分，但仍可申请，只要其余项目补足 70 分。0-99 表示「无年龄门槛」，不是「未核实」。
  ```

### `eligibility.education`

- **类型 / 必填**：`object` / 是
- **定义**：学历条件容器。
- **实测**：41/41 个文件出现；结构由下列子字段定义。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.education` 原文节选：
  ```json
  {"minimum_level": "bachelor_completed", "major_restriction": [], "note": "须完成不少于四年的高等教育课程（学士通常按四年制计；三年制本科不满足本通道的学历时长要求）。学科直接影响得分：数学、信息学、自然科学、技术（MINT）类得 30 分，其它专业得 20 分；博士或教授资格（Habilitation）得 40 分。仅「受管制职业」（医疗、公立学校教师、律师等）需要正式学历认定，其余职业按提交的材料评估，不做学历等同认证。"}
  ```

### `eligibility.education.minimum_level`

- **类型 / 必填**：`string` / 是
- **定义**：最低学历层次。
- **取值**：`high_school`=高中；`vocational`=职业教育/大专；`bachelor_in_progress`=本科在读；`bachelor_completed`=本科毕业；`master`=硕士；`any`=不限
- **实测**：41/41 个文件出现；取值分布：`bachelor_completed` 19、`any` 11、`bachelor_in_progress` 6、`master` 3、`vocational` 1、`high_school` 1；全部取值都在 schema 枚举内。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.education.minimum_level` 原值：`bachelor_completed`。

### `eligibility.education.years_completed`

- **类型 / 必填**：`integer` / 否
- **定义**：要求已完成的本科/大专年限；实测只有 1 个文件使用。
- **实测**：1/41 个文件出现；取值为 `2`；其余 40 个文件未填该键。
- **示例**：`au-462-work-holiday.json` 的 `eligibility.education.years_completed` 原值：`2`。

### `eligibility.education.major_restriction`

- **类型 / 必填**：`array（string）` / 否
- **定义**：专业限制；空数组表示不限专业（实测 40/41 为空，见 §11.2）。
- **实测**：41/41 个文件出现，1 个非空；共 4 项，去重 4 个；取值分布：`科学（Science）` 1、`工程（Engineering）` 1、`技术（Technology）` 1、`部分生物技术、生物医学专业` 1。
- **示例**：`global-iaeste.json` 的 `eligibility.education.major_restriction` 原值：`["科学（Science）", "工程（Engineering）", "技术（Technology）", "部分生物技术、生物医学专业"]`。

### `eligibility.education.note`

- **类型 / 必填**：`string` / 是
- **定义**：学历要求补充说明（常写「满足以下任一条件即可」的口径）。
- **实测**：41/41 个文件出现；每个文件各不相同。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.education.note` 原值：
  ```text
  须完成不少于四年的高等教育课程（学士通常按四年制计；三年制本科不满足本通道的学历时长要求）。学科直接影响得分：数学、信息学、自然科学、技术（MINT）类得 30 分，其它专业得 20 分；博士或教授资格（Habilitation）得 40 分。仅「受管制职业」（医疗、公立学校教师、律师等）需要正式学历认定，其余职业按提交的材料评估，不做学历等同认证。
  ```

### `eligibility.language`

- **类型 / 必填**：`object` / 是
- **定义**：语言条件容器。
- **实测**：41/41 个文件出现；结构由下列子字段定义。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.language` 原文节选：
  ```json
  {"required": true, "tests": [], "note": "德语或英语达到 CEFR A1 得 5 分，A2 得 10 分（本项上限 10 分）；法语、西班牙语、波斯尼亚/克罗地亚/塞尔维亚语 B1 各得 5 分。语言证书不得早于申请前 5 年。德语证书认可机构为 ÖSD、歌德学院、Telc、奥地利融合基金（ÖIF）；英语认可剑桥证书、TELC、IELTS、TOEIC、TOEFL。官方未指定最低等级——A1 也计分，语言只影响分数不影响资格。"}
  ```

### `eligibility.language.required`

- **类型 / 必填**：`boolean` / 是
- **定义**：是否要求语言能力证明。
- **实测**：41/41 个文件出现；`true` 16、`false` 25。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.language.required` 原值：`true`。

### `eligibility.language.tests`

- **类型 / 必填**：`array（对象）` / 否
- **定义**：可接受的语言考试列表，OR 关系：任一通过即可；空数组表示未列出具体考试（见 §11.2）。
- **实测**：41/41 个文件出现，其中 4 个非空；共 10 条，单文件 0–4 条。
- **示例**：`au-462-work-holiday.json` 的 `eligibility.language.tests[0]` 首条原文节选（该文件共 4 条）：`{"test": "IELTS", "min_score": 4.5, "validity_months": 12}`。
- **校验器补充**：校验器要求每条考试项的 `test`/`min_score`/`validity_months` 三项都存在。

### `eligibility.language.tests[].test`

- **类型 / 必填**：`string` / 是（数组项内）
- **定义**：考试类型。
- **取值**：`IELTS`=雅思；`TOEFL_iBT`=托福 iBT；`PTE`=PTE；`Cambridge`=剑桥英语；`CEFR`=CEFR 等级；`OET`=OET 职业英语；`none`=无需考试
- **实测**：4/41 个文件出现；10 条；取值分布：`IELTS` 3、`PTE` 2、`TOEFL_iBT` 2、`Cambridge` 2、`none` 1；全部取值都在 schema 枚举内；其余 37 个文件的该数组为空。
- **示例**：`au-462-work-holiday.json` 的 `eligibility.language.tests[i].test` 原值：`IELTS`。

### `eligibility.language.tests[].min_score`

- **类型 / 必填**：`number` / 是（数组项内）
- **定义**：该考试的最低分数/等级。
- **实测**：4/41 个文件出现；10 条；取值为 `0`、`4.5`、`5.5`、`6.0`、`30`、`32`、`42`、`46`、`147`、`162`；其余 37 个文件的该数组为空。
- **示例**：`au-462-work-holiday.json` 的 `eligibility.language.tests[i].min_score` 原值：`4.5`。

### `eligibility.language.tests[].validity_months`

- **类型 / 必填**：`integer` / 是（数组项内）
- **定义**：成绩有效期（月）。
- **实测**：4/41 个文件出现；10 条；取值为 `0`、`12`、`24`；其余 37 个文件的该数组为空。
- **示例**：`au-462-work-holiday.json` 的 `eligibility.language.tests[i].validity_months` 原值：`12`。

### `eligibility.language.note`

- **类型 / 必填**：`string` / 是
- **定义**：语言要求补充说明（认可的考试、分数口径、成绩时效等）。
- **实测**：41/41 个文件出现；共 40 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.language.note` 原值：
  ```text
  德语或英语达到 CEFR A1 得 5 分，A2 得 10 分（本项上限 10 分）；法语、西班牙语、波斯尼亚/克罗地亚/塞尔维亚语 B1 各得 5 分。语言证书不得早于申请前 5 年。德语证书认可机构为 ÖSD、歌德学院、Telc、奥地利融合基金（ÖIF）；英语认可剑桥证书、TELC、IELTS、TOEIC、TOEFL。官方未指定最低等级——A1 也计分，语言只影响分数不影响资格。
  ```

### `eligibility.funds`

- **类型 / 必填**：`object` / 是
- **定义**：资金条件容器。
- **实测**：41/41 个文件出现；结构由下列子字段定义。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.funds` 原文节选：
  ```json
  {"required": true, "note": "申请找工作签证时须提供「足够生计来源」证明（工资单、雇佣合同、养老金凭证、投资或自有资产等），官方未写死金额。但如果直接凭工作邀请申请红白红卡，居留法通用要求中的「住所与收入」两项被豁免——因为此时已有对口岗位与法定最低薪资。"}
  ```

### `eligibility.funds.required`

- **类型 / 必填**：`boolean` / 是
- **定义**：是否要求资金证明。
- **实测**：41/41 个文件出现；`true` 20、`false` 21。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.funds.required` 原值：`true`。

### `eligibility.funds.amount`

- **类型 / 必填**：`object` / 否
- **定义**：资金金额对象；实测有 9 个文件显式 `null`，见 §11.2/§11.3。
- **实测**：22/41 个文件出现；9 条显式 null；结构由下列子字段定义。
- **示例**：`au-462-work-holiday.json` 的 `eligibility.funds.amount` 原文节选：
  ```json
  {"local_amount": 5000, "currency": "AUD", "cny_estimate": 23500, "note": "约 5,000 澳元存款证明，用于证明初期生活能力。另需证明有足够资金购买返程机票。"}
  ```
- **校验器补充**：校验器对金额对象校验 `local_amount` 为非负数字、`currency` 在币种枚举内、`cny_estimate` 为数字；`amount` 为 `null` 时直接跳过。

### `eligibility.funds.amount.local_amount`

- **类型 / 必填**：`number` / 是
- **定义**：原币金额。
- **实测**：13/41 个文件出现；取值为 `752`、`800`、`1270`、`2500`、`2530`、`4000`、`4200`、`5000`、`13000`、`42000`、`259951`、`3000000`；其余 28 个文件未填该键。
- **示例**：`au-462-work-holiday.json` 的 `eligibility.funds.amount.local_amount` 原值：`5000`。

### `eligibility.funds.amount.currency`

- **类型 / 必填**：`string` / 是
- **定义**：币种 ISO 代码。
- **取值**：`AUD`、`NZD`、`JPY`、`KRW`、`USD`、`EUR`、`GBP`、`CNY`、`HKD`、`TWD`、`SGD`、`PLN`、`DKK`、`SEK`、`NOK`、`CAD`、`CHF`、`THB`、`MYR`、`VND`、`IDR`、`ILS`、`TRY`、`ISK`
- **实测**：13/41 个文件出现；取值分布：`EUR` 4、`NZD` 2、`GBP` 2、`AUD` 1、`CAD` 1、`ISK` 1、`KRW` 1、`SEK` 1；全部取值都在 schema 枚举内；其余 28 个文件未填该键。
- **示例**：`au-462-work-holiday.json` 的 `eligibility.funds.amount.currency` 原值：`AUD`。

### `eligibility.funds.amount.cny_estimate`

- **类型 / 必填**：`number` / 否
- **定义**：人民币估算值，仅供参考。
- **实测**：13/41 个文件出现；取值 5900–330000，共 13 种；其余 28 个文件未填该键。
- **示例**：`au-462-work-holiday.json` 的 `eligibility.funds.amount.cny_estimate` 原值：`23500`。

### `eligibility.funds.amount.note`

- **类型 / 必填**：`string` / 否
- **定义**：该金额的口径说明（如是否含机票、是否按官方最低值）。
- **实测**：13/41 个文件出现；每个文件各不相同；其余 28 个文件未填该键。
- **示例**：`au-462-work-holiday.json` 的 `eligibility.funds.amount.note` 原值：`约 5,000 澳元存款证明，用于证明初期生活能力。另需证明有足够资金购买返程机票。`。

### `eligibility.funds.note`

- **类型 / 必填**：`string` / 是
- **定义**：资金要求补充说明（官方是否写死金额、可用哪些资金证明）。
- **实测**：41/41 个文件出现；每个文件各不相同。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.funds.note` 原值：
  ```text
  申请找工作签证时须提供「足够生计来源」证明（工资单、雇佣合同、养老金凭证、投资或自有资产等），官方未写死金额。但如果直接凭工作邀请申请红白红卡，居留法通用要求中的「住所与收入」两项被豁免——因为此时已有对口岗位与法定最低薪资。
  ```

### `eligibility.other_requirements`

- **类型 / 必填**：`array（对象）` / 是
- **定义**：其他资格要求数组，逐项标注是否强制。
- **实测**：41/41 个文件出现，其中 41 个非空；共 140 条，单文件 1–7 条。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.other_requirements[0]` 首条原文节选（该文件共 3 条）：
  ```json
  {"type": "health_check", "required": true, "note": "须持覆盖全部风险的医疗保险（法定保险或等效保单），且在递交申请时即须提供。旅行医疗保险可被接受，条件是保额远高于 3 万欧元并包含救援与送返费用的担保。"}
  ```

### `eligibility.other_requirements[].type`

- **类型 / 必填**：`string` / 是（数组项内）
- **定义**：其他要求类型。
- **取值**：`health_check`=体检；`criminal_record`=无犯罪记录；`insurance`=保险；`no_dependents`=不得携带受养人；`return_ticket`=返程机票/资金；`government_support_letter`=政府支持信；`enrollment_proof`=在读证明；`internship_contract`=实习/培训合同；`blocked_account`=封闭账户；`no_prior_visa`=无同类签证史；`residency_requirement`=居住/户籍要求
- **实测**：41/41 个文件出现；140 条；取值分布：`insurance` 24、`residency_requirement` 22、`criminal_record` 17、`health_check` 16、`return_ticket` 12、`internship_contract` 11、`enrollment_proof` 11、`no_dependents` 10、`no_prior_visa` 10、`government_support_letter` 6、`blocked_account` 1；全部取值都在 schema 枚举内。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.other_requirements[i].type` 原值：`health_check`。

### `eligibility.other_requirements[].required`

- **类型 / 必填**：`boolean` / 是（数组项内）
- **定义**：该项是否强制。
- **实测**：41/41 个文件出现；140 条；`true` 110、`false` 30。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.other_requirements[i].required` 原值：`true`。

### `eligibility.other_requirements[].note`

- **类型 / 必填**：`string` / 是（数组项内）
- **定义**：该项的具体说明。
- **实测**：41/41 个文件出现；140 条；共 139 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `eligibility.other_requirements[i].note` 原值：`须持覆盖全部风险的医疗保险（法定保险或等效保单），且在递交申请时即须提供。旅行医疗保险可被接受，条件是保额远高于 3 万欧元并包含救援与送返费用的担保。`。

## 4. `timeline`：时间、配额与费用

`timeline` 是必填对象，含配额四态、窗口数组、窗口日历、费用与审理时长。实测：`mechanism` 滚动 33 个、抽签 3 个、预约 3 个、先到先得 2 个；`quota_status` 为 `no_quota` 34 个、`capped` 4 个、`unverified` 2 个、`not_published` 1 个；`windows[]` 共 72 条（每文件 1–3 条）；`schedule` 41/41 存在；`fees[]` 共 56 条（5 个文件为空数组）；`processing_time` 41/41 有值。

### `timeline`

- **类型 / 必填**：`object` / 是
- **定义**：时间窗口与配额容器，必填。
- **实测**：41/41 个文件出现；结构由下列子字段定义。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline` 原文节选（对象共 8 个键，此处列前 3 个）：`{"mechanism": "rolling", "quota_status": "unverified", "quota": null}`。

### `timeline.mechanism`

- **类型 / 必填**：`string` / 是
- **定义**：名额分配机制。
- **取值**：`ballot`=抽签；`first_come_first_served`=先到先得；`rolling`=滚动受理；`appointment`=预约制；`annual_negotiation`=年度协商制
- **实测**：41/41 个文件出现；取值分布：`rolling` 33、`ballot` 3、`appointment` 3、`first_come_first_served` 2；全部取值都在 schema 枚举内。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.mechanism` 原值：`rolling`。

### `timeline.quota_status`

- **类型 / 必填**：`string` / 是
- **定义**：配额四态，必填；不同状态对 `quota` / `quota_basis` / `quota_source` 有联动约束（见 §10.4）。
- **取值**：`capped`=有具体配额；`no_quota`=无配额；`not_published`=设限但未公布数字；`unverified`=尚未核实
- **实测**：41/41 个文件出现；取值分布：`no_quota` 34、`capped` 4、`unverified` 2、`not_published` 1；全部取值都在 schema 枚举内。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.quota_status` 原值：`unverified`。
- **校验器补充**：四态联动规则见 §10.4；`quota_note` 至少 8 个字符；`quota_source` 必须出现在本项目 `sources[]` 且该来源为 `primary`。

### `timeline.quota`

- **类型 / 必填**：`integer | null` / 是
- **定义**：配额数字，口径固定为「中国大陆护照适用的年度名额」；仅 `capped` 时填正整数，其余状态必须 `null`。
- **实测**：41/41 个文件出现；其中 37 条显式 null；取值为 `1`、`1000`、`2000`、`5000`。
- **示例**：`au-462-work-holiday.json` 的 `timeline.quota` 原值：`5000`。

### `timeline.quota_basis`

- **类型 / 必填**：`string` / 否
- **定义**：配额口径；仅 `capped` 时必填。
- **取值**：`annual`=年度发放上限；`concurrent`=同时在册人数上限
- **实测**：4/41 个文件出现；取值分布：`annual` 2、`concurrent` 2；全部取值都在 schema 枚举内；其余 37 个文件未填该键。
- **示例**：`au-462-work-holiday.json` 的 `timeline.quota_basis` 原值：`annual`。

### `timeline.quota_source`

- **类型 / 必填**：`string` / 否
- **定义**：支撑配额结论的官方来源 URL，必须与本项目 `sources[]` 中某条 `url` 完全一致；`unverified` 时不得填写。
- **实测**：39/41 个文件出现；每个文件各不相同；其余 2 个文件未填该键。
- **示例**：`au-407-training.json` 的 `timeline.quota_source` 原值：`https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/training-407`。

### `timeline.quota_note`

- **类型 / 必填**：`string` / 是
- **定义**：配额说明，必填且不得为空。capped 写清数字口径与适用护照/地区；not_published 写清官方如何表述限额；unverified 写清缺的是哪一条信息、该向谁确认。
- **实测**：41/41 个文件出现；每个文件各不相同。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.quota_note` 原值：
  ```text
  奥地利按《定居与居留法》（NAG）设有联邦最高限额（Bundeshöchstzahl）制度，部分居留类别受年度配额约束；但 very highly qualified（红白红卡高资质档）是否被列入、当年数字多少，仍未从官方一手来源确认。已逐页排查（2026-11-11）：① migration.gv.at 的高资质人才页（含积分表全文）；② 同站 FAQ 页；③ 同站「永久居留」总览页——三页均未出现 quota / Bundeshöchstzahl / contingent 一类表述；④ BMI（内政部）的居留事务页亦无配额内容。⑤ 权威法律数据库 ris.bka.gv.at 本次访问被 Myra 安全验证拦截（HTTP 503 挑战页），无法读取 NAG 条文原文，故未能从法条侧确证。卡点：需读到当年 NAG 的 Bundeshöchstzahl 条例（Verordnung）原文，或将
  ```
  （节选，原文 460 字符）

### `timeline.windows`

- **类型 / 必填**：`array（对象）` / 是
- **定义**：申请窗口数组，按年份记录；实测对滚动项目也至少写 1 条（见 §11.3）。
- **实测**：41/41 个文件出现，其中 41 个非空；共 72 条，单文件 1–3 条。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.windows[0]` 首条原文节选（该文件共 2 条）：
  ```json
  {"year": 2027, "status": "unknown", "note": "全年可申请，无固定开放窗口。配额与短缺职业清单按年度更新（短缺职业清单 2026 年版已公布），需在递交前复核。"}
  ```
- **校验器补充**：校验器要求至少 1 条；`status` 枚举；日期真实；同一年份重复只给 warning。

### `timeline.windows[].year`

- **类型 / 必填**：`integer` / 是（数组项内）
- **定义**：窗口所属年份。
- **实测**：41/41 个文件出现；72 条；取值为 `2025`、`2026`、`2027`。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.windows[i].year` 原值：`2027`。

### `timeline.windows[].status`

- **类型 / 必填**：`string` / 是（数组项内）
- **定义**：该年窗口状态。
- **取值**：`upcoming`=未开放；`open`=开放中；`closed`=已关闭；`unknown`=未核实
- **实测**：41/41 个文件出现；72 条；取值分布：`open` 33、`unknown` 24、`upcoming` 8、`closed` 7；全部取值都在 schema 枚举内。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.windows[i].status` 原值：`unknown`。

### `timeline.windows[].open_date`

- **类型 / 必填**：`string` / 否（数组项内）
- **定义**：该年窗口开放日期（`YYYY-MM-DD`）。
- **实测**：3/41 个文件出现；4 条；共 4 个不同值；其余 38 个文件中部分数组项未填该键；该数组共 72 条，本字段缺失 68 条。
- **示例**：`au-462-work-holiday.json` 的 `timeline.windows[i].open_date` 原值：`2026-06-04`。

### `timeline.windows[].close_date`

- **类型 / 必填**：`string` / 否（数组项内）
- **定义**：该年窗口截止日期（`YYYY-MM-DD`）。
- **实测**：2/41 个文件出现；每个文件各不相同；其余 39 个文件中部分数组项未填该键；该数组共 72 条，本字段缺失 70 条。
- **示例**：`au-462-work-holiday.json` 的 `timeline.windows[i].close_date` 原值：`2026-06-25`。

### `timeline.windows[].draw_period_end`

- **类型 / 必填**：`string` / 否（数组项内）
- **定义**：抽签制项目的抽签期结束日；实测仅 1 条。
- **实测**：1/41 个文件出现；每个文件各不相同；其余 40 个文件中部分数组项未填该键；该数组共 72 条，本字段缺失 71 条。
- **示例**：`au-462-work-holiday.json` 的 `timeline.windows[i].draw_period_end` 原值：`2027-04-30`。

### `timeline.windows[].lodgement_window_days`

- **类型 / 必填**：`integer` / 否（数组项内）
- **定义**：中签后递交窗口（天）；实测仅 1 条。
- **实测**：1/41 个文件出现；取值为 `28`；其余 40 个文件中部分数组项未填该键；该数组共 72 条，本字段缺失 71 条。
- **示例**：`au-462-work-holiday.json` 的 `timeline.windows[i].lodgement_window_days` 原值：`28`。

### `timeline.windows[].note`

- **类型 / 必填**：`string` / 是（数组项内）
- **定义**：该年窗口的补充说明。
- **实测**：41/41 个文件出现；72 条；共 72 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.windows[i].note` 原值：`全年可申请，无固定开放窗口。配额与短缺职业清单按年度更新（短缺职业清单 2026 年版已公布），需在递交前复核。`。

### `timeline.schedule`

- **类型 / 必填**：`object` / 是
- **定义**：窗口日历的结构化模型，必填；记「时间规律」，与 `windows[]` 的「某一年具体怎样」互补。
- **实测**：41/41 个文件出现；结构由下列子字段定义。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.schedule` 原文节选（对象共 6 个键，此处列前 5 个）：
  ```json
  {"type": "rolling", "status": "always_open", "date_confidence": "unknown", "next_window_hint": "无窗口；但部分类别受年度配额（Bundeshöchstzahl）约束，配额若用尽需等下一配额年度。", "lead_time_days": 60}
  ```
- **校验器补充**：校验器额外约束：`note` 至少 8 个字符；`lead_time_days` 为 0–365 整数；`inferred`/`unknown` 不得带具体日期；`rolling` 不得标 `confirmed`；`annual_cycle` 且 `inferred` 时必须有 `cycle_note`；`rolling`/`no_window` 不得有开放/截止日；`close_date` 不得早于 `open_date`。

### `timeline.schedule.type`

- **类型 / 必填**：`string` / 是
- **定义**：时间规律类型。
- **取值**：`fixed_dates`=每年日期由官方逐次公布，不遵循固定月日；`annual_cycle`=每年在相近月份重开，可据往年推断；`rolling`=全年滚动，无窗口概念；`no_window`=项目不开放或对本护照不开放，窗口无意义
- **实测**：41/41 个文件出现；取值分布：`rolling` 32、`fixed_dates` 6、`annual_cycle` 2、`no_window` 1；全部取值都在 schema 枚举内。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.schedule.type` 原值：`rolling`。

### `timeline.schedule.status`

- **类型 / 必填**：`string` / 是
- **定义**：当前窗口状态。
- **取值**：`open`=开放中；`closed`=已关闭；`upcoming`=未开放；`always_open`=全年常开（专给 rolling 类）；`unknown`=未知
- **实测**：41/41 个文件出现；取值分布：`always_open` 32、`closed` 4、`unknown` 4、`open` 1；全部取值都在 schema 枚举内。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.schedule.status` 原值：`always_open`。

### `timeline.schedule.date_confidence`

- **类型 / 必填**：`string` / 是
- **定义**：日期确定性标记，是整块日历的可信度开关。
- **取值**：`confirmed`=官方页面明确写出日期；`inferred`=按往年规律推断；`unknown`=连规律都无从判断 / 不适用
- **实测**：41/41 个文件出现；取值分布：`unknown` 36、`confirmed` 3、`inferred` 2；全部取值都在 schema 枚举内。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.schedule.date_confidence` 原值：`unknown`。

### `timeline.schedule.open_date`

- **类型 / 必填**：`string` / 否
- **定义**：当前或下一次已知开放日；仅 `date_confidence=confirmed` 时允许填具体日期（schema 类型未声明可空，实测有 10 个 `null`，见 §11.3）。
- **实测**：13/41 个文件出现；其中 10 条显式 null；共 3 个不同值；其余 28 个文件未填该键。
- **示例**：`au-462-work-holiday.json` 的 `timeline.schedule.open_date` 原值：`2026-06-04`。

### `timeline.schedule.close_date`

- **类型 / 必填**：`string` / 否
- **定义**：当前或下一次已知截止日；仅 `date_confidence=confirmed` 时允许填具体日期（实测有 11 个 `null`，见 §11.3）。
- **实测**：13/41 个文件出现；其中 11 条显式 null；共 2 个不同值；其余 28 个文件未填该键。
- **示例**：`au-462-work-holiday.json` 的 `timeline.schedule.close_date` 原值：`2026-06-25`。

### `timeline.schedule.cycle_note`

- **类型 / 必填**：`string` / 否
- **定义**：`annual_cycle` 类的往年实际日期序列，是 `inferred` 的依据；实测仅 5 个文件使用。
- **实测**：5/41 个文件出现；每个文件各不相同；其余 36 个文件未填该键。
- **示例**：`au-462-work-holiday.json` 的 `timeline.schedule.cycle_note` 原值：
  ```text
  2026-27 财年的注册窗口为 2026-06-04 至 2026-06-25（约 3 周），中签后 28 天内须递交正式申请；抽签选择期持续到 2027-04-30。
  ```

### `timeline.schedule.next_window_hint`

- **类型 / 必填**：`string` / 否
- **定义**：下一次窗口的文字预告；schema 要求仅在有依据时填，实测 41/41 全填（见 §11.3）。
- **实测**：41/41 个文件出现；每个文件各不相同。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.schedule.next_window_hint` 原值：`无窗口；但部分类别受年度配额（Bundeshöchstzahl）约束，配额若用尽需等下一配额年度。`。

### `timeline.schedule.lead_time_days`

- **类型 / 必填**：`integer` / 是
- **定义**：建议提前准备天数：提醒日 = 开放日 − `lead_time_days`。
- **实测**：41/41 个文件出现；取值为 `0`、`14`、`30`、`45`、`60`、`90`。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.schedule.lead_time_days` 原值：`60`。

### `timeline.schedule.note`

- **类型 / 必填**：`string` / 是
- **定义**：必填。写清这个判断的依据：官方页面怎么写的、往年日期从哪来、lead_time_days 为什么取这个数。
- **实测**：41/41 个文件出现；每个文件各不相同。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.schedule.note` 原值：
  ```text
  rolling：官方无开放窗口。注意配额维度：该项目的 quota_status 仍是 unverified（没查到高资质档的具体数字），这不是窗口问题，是配额问题，两件事分开记。lead_time_days=60：需备积分材料（学历、薪资、语言、年龄证明）与雇主声明。
  ```

### `timeline.fees`

- **类型 / 必填**：`array（对象）` / 否
- **定义**：费用明细数组；实测 5 个项目为空数组（见 §11.2）。
- **实测**：41/41 个文件出现，其中 36 个非空；共 56 条，单文件 0–3 条。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.fees[0]` 首条原文节选（该文件共 2 条）：
  ```json
  {"item": "找工作签证（Job Seeker Visa，D 类）", "amount": {"local_amount": 195, "currency": "EUR", "cny_estimate": 1540, "note": "官方页面列明的 Jobseeker Visa 费用。仅在没有工作邀请、先入境找工作的路径下需要。"}, "refundable": false}
  ```

### `timeline.fees[].item`

- **类型 / 必填**：`string` / 是（数组项内）
- **定义**：费用项名称。
- **实测**：36/41 个文件出现；56 条；共 44 个不同值；其余 5 个文件的该数组为空。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.fees[i].item` 原值：`找工作签证（Job Seeker Visa，D 类）`。

### `timeline.fees[].amount`

- **类型 / 必填**：`object` / 是（数组项内）
- **定义**：费用金额对象，结构同 §10.3。
- **实测**：36/41 个文件出现；结构由下列子字段定义。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.fees[].amount` 原文节选：
  ```json
  {"local_amount": 195, "currency": "EUR", "cny_estimate": 1540, "note": "官方页面列明的 Jobseeker Visa 费用。仅在没有工作邀请、先入境找工作的路径下需要。"}
  ```
- **校验器补充**：金额对象规则同 §10.3。

### `timeline.fees[].amount.local_amount`

- **类型 / 必填**：`number` / 是（数组项内）
- **定义**：原币金额（与 §10.3 的 `money.local_amount` 同义）。
- **实测**：36/41 个文件出现；56 条；取值 0–70000，共 40 种；其余 5 个文件的该数组为空。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.fees[i].amount.local_amount` 原值：`195`。

### `timeline.fees[].amount.currency`

- **类型 / 必填**：`string` / 是（数组项内）
- **定义**：币种 ISO 代码（与 §10.3 的 `money.currency` 同义）。
- **取值**：`AUD`、`NZD`、`JPY`、`KRW`、`USD`、`EUR`、`GBP`、`CNY`、`HKD`、`TWD`、`SGD`、`PLN`、`DKK`、`SEK`、`NOK`、`CAD`、`CHF`、`THB`、`MYR`、`VND`、`IDR`、`ILS`、`TRY`、`ISK`
- **实测**：36/41 个文件出现；56 条；取值分布：`EUR` 16、`GBP` 10、`AUD` 7、`USD` 7、`SGD` 4、`CAD` 3、`NZD` 3、`TWD` 1、`ISK` 1、`JPY` 1、`NOK` 1、`SEK` 1、`CNY` 1；全部取值都在 schema 枚举内；其余 5 个文件的该数组为空。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.fees[i].amount.currency` 原值：`EUR`。

### `timeline.fees[].amount.cny_estimate`

- **类型 / 必填**：`number` / 否（数组项内）
- **定义**：人民币估算值，仅供参考
- **实测**：26/41 个文件出现；43 条；取值 120–27000，共 35 种；其余 15 个文件中部分数组项未填该键；该数组共 56 条，本字段缺失 13 条。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.fees[i].amount.cny_estimate` 原值：`1540`。

### `timeline.fees[].amount.note`

- **类型 / 必填**：`string` / 否（数组项内）
- **定义**：费用说明，如'不含体检费'
- **实测**：31/41 个文件出现；43 条；共 43 个不同值；其余 10 个文件中部分数组项未填该键；该数组共 56 条，本字段缺失 13 条。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.fees[i].amount.note` 原值：`官方页面列明的 Jobseeker Visa 费用。仅在没有工作邀请、先入境找工作的路径下需要。`。

### `timeline.fees[].refundable`

- **类型 / 必填**：`boolean` / 否（数组项内）
- **定义**：该费用是否可退；实测 56/56 为 `false`。
- **实测**：36/41 个文件出现；56 条；`false` 56；其余 5 个文件的该数组为空。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.fees[i].refundable` 原值：`false`。

### `timeline.processing_time`

- **类型 / 必填**：`string` / 否
- **定义**：审理时长说明（schema 示例是「4-8 周」这类短语，实测多为长段解释，见 §11.3）。
- **实测**：41/41 个文件出现；每个文件各不相同。
- **示例**：`at-rwr-card-vhq.json` 的 `timeline.processing_time` 原值：
  ```text
  官方未公布统一审理时限。流程是：受理机关（使领馆或境内居留管理局）收件后转联邦劳动局（AMS）审核积分、学历与薪资，AMS 出具意见后由居留机关签发。实际耗时取决于使领馆预约排期与 AMS 审核，实务上以月计，官方没有可引用的天数。
  ```

## 5. `documents[]`：材料清单

`documents` 是必填数组，至少 1 项。实测 41/41 个文件、共 267 条，单文件 1–11 条；`note` 与 `prepare_days` 在 267 条中 100% 填写。

### `documents`

- **类型 / 必填**：`array（对象）` / 是
- **定义**：所需材料清单，必填且至少 1 项。
- **实测**：41/41 个文件出现，其中 41 个非空；共 267 条，单文件 1–11 条。
- **示例**：`at-rwr-card-vhq.json` 的 `documents[0]` 首条原文节选（该文件共 10 条）：`{"name": "有效护照", "required": true, "note": "有效期覆盖计划居留期", "prepare_days": 30}`。
- **校验器补充**：校验器要求至少 1 项；`required` 必须是布尔值。

### `documents[].name`

- **类型 / 必填**：`string` / 是（数组项内）
- **定义**：材料名称。
- **实测**：41/41 个文件出现；267 条；共 182 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `documents[i].name` 原值：`有效护照`。

### `documents[].required`

- **类型 / 必填**：`boolean` / 是（数组项内）
- **定义**：该材料是否必需。
- **实测**：41/41 个文件出现；267 条；`true` 246、`false` 21。
- **示例**：`at-rwr-card-vhq.json` 的 `documents[i].required` 原值：`true`。

### `documents[].note`

- **类型 / 必填**：`string` / 否（数组项内）
- **定义**：材料说明，如公证、翻译、有效期要求。
- **实测**：41/41 个文件出现；267 条；共 256 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `documents[i].note` 原值：`有效期覆盖计划居留期`。

### `documents[].prepare_days`

- **类型 / 必填**：`integer` / 否（数组项内）
- **定义**：建议提前准备天数。
- **实测**：41/41 个文件出现；267 条；取值为 `0`、`1`、`3`、`7`、`14`、`21`、`30`、`31`、`45`、`60`、`90`。
- **示例**：`at-rwr-card-vhq.json` 的 `documents[i].prepare_days` 原值：`30`。

## 6. `steps[]`：申请流程

`steps` 是必填数组，至少 1 步。实测 41/41 个文件、共 217 条，单文件 2–8 条；`step_no` 全部从 1 连续递增；`duration` 与 `official_link` 在 217 条中 100% 填写。

### `steps`

- **类型 / 必填**：`array（对象）` / 是
- **定义**：申请流程步骤数组，必填且至少 1 步。
- **实测**：41/41 个文件出现，其中 41 个非空；共 217 条，单文件 2–8 条。
- **示例**：`at-rwr-card-vhq.json` 的 `steps[0]` 首条原文节选（该文件共 5 条）：
  ```json
  {"step_no": 1, "title": "先自算积分，确认够 70 分", "description": "特殊资格与技能上限 40 分（四年制高等教育毕业 20、MINT 学科 30、博士或教授资格 40；上一年在上市公司或经奥地利外贸机构认可的企业任高管的税前年薪 5-6 万欧 20 分、6-7 万欧 25 分、7 万欧以上 30 分；科研与创新活动 20 分；获奖 20 分）＋工作经验上限 20 分（每满半年 1 分，在奥地利每半年 2 分）＋语言上限 10 分＋年龄上限 20 分＋在奥地利的学习经历上限 10 分。总分 100，门槛 70。", "duration": "30 分钟", "official_link": "https://www.migration.gv.at/en/types-of-immigration/permanent-immigration/ver
  ```
  （节选，原文 429 字符）
- **校验器补充**：校验器要求至少 1 步；`step_no` 必须是整数且从 1 连续递增；`official_link` 必须是以 `http(s)://` 开头的 URL。

### `steps[].step_no`

- **类型 / 必填**：`integer` / 是（数组项内）
- **定义**：步骤序号，必须从 1 连续递增。
- **实测**：41/41 个文件出现；217 条；取值为 `1`、`2`、`3`、`4`、`5`、`6`、`7`、`8`。
- **示例**：`at-rwr-card-vhq.json` 的 `steps[i].step_no` 原值：`1`。

### `steps[].title`

- **类型 / 必填**：`string` / 是（数组项内）
- **定义**：步骤标题。
- **实测**：41/41 个文件出现；217 条；共 211 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `steps[i].title` 原值：`先自算积分，确认够 70 分`。

### `steps[].description`

- **类型 / 必填**：`string` / 是（数组项内）
- **定义**：步骤说明。
- **实测**：41/41 个文件出现；217 条；共 217 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `steps[i].description` 原值：
  ```text
  特殊资格与技能上限 40 分（四年制高等教育毕业 20、MINT 学科 30、博士或教授资格 40；上一年在上市公司或经奥地利外贸机构认可的企业任高管的税前年薪 5-6 万欧 20 分、6-7 万欧 25 分、7 万欧以上 30 分；科研与创新活动 20 分；获奖 20 分）＋工作经验上限 20 分（每满半年 1 分，在奥地利每半年 2 分）＋语言上限 10 分＋年龄上限 20 分＋在奥地利的学习经历上限 10 分。总分 100，门槛 70。
  ```

### `steps[].duration`

- **类型 / 必填**：`string` / 否（数组项内）
- **定义**：该步骤的参考耗时。
- **实测**：41/41 个文件出现；217 条；共 80 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `steps[i].duration` 原值：`30 分钟`。

### `steps[].official_link`

- **类型 / 必填**：`string` / 否（数组项内）
- **定义**：该步骤对应的官方链接。
- **实测**：41/41 个文件出现；217 条；共 98 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `steps[i].official_link` 原值：
  ```text
  https://www.migration.gv.at/en/types-of-immigration/permanent-immigration/very-highly-qualified-workers/
  ```

## 7. `work_conditions`：持证后的工作与学习限制

`work_conditions` 在 schema 中可选，实测 41/41 个文件都存在。它没有必填键；`max_stay_months` 与 `max_same_employer_months` 41/41 出现，`max_study_months` 32/41 出现；`max_same_employer_months=0` 18 个、`max_study_months=0` 25 个（哨兵值含义见 §11.3）。

### `work_conditions`

- **类型 / 必填**：`object` / 否
- **定义**：持证后的工作与学习限制容器。
- **实测**：41/41 个文件出现；结构由下列子字段定义。
- **示例**：`at-rwr-card-vhq.json` 的 `work_conditions` 原文节选（对象共 6 个键，此处列前 5 个）：
  ```json
  {"max_stay_months": 24, "max_same_employer_months": 24, "renewable": true, "renewal_condition": "红白红卡一般签发 24 个月，与申请中指定的雇主绑定。换雇主须重新申请一份带劳动力市场准入的居留许可；在申请提交后满 45 天即可先上岗，前提是审核所需材料已完整提交，材料不全时 45 天起算日相应顺延。按资格条件受雇满 21 个月（过去 24 个月内，由 AMS 核定）后可申请红白红卡 plus，获得不受限的就业与定居权。", "restricted_occupations": []}
  ```
  （节选，原文 476 字符）
- **校验器补充**：校验器只检查它是否为对象、`restricted_occupations` 是否为数组；不校验各数值键的类型或语义。

### `work_conditions.max_stay_months`

- **类型 / 必填**：`integer` / 否
- **定义**：单次停留/居留上限（月）；`0` 的含义见 §11.3。
- **实测**：41/41 个文件出现；取值为 `0`、`4`、`6`、`9`、`11`、`12`、`18`、`24`、`36`、`60`。
- **示例**：`at-rwr-card-vhq.json` 的 `work_conditions.max_stay_months` 原值：`24`。

### `work_conditions.max_same_employer_months`

- **类型 / 必填**：`integer` / 否
- **定义**：为同一雇主工作的上限（月）；`0` 的含义见 §11.3。
- **实测**：41/41 个文件出现；取值为 `0`、`4`、`6`、`12`、`18`、`24`、`36`、`60`。
- **示例**：`at-rwr-card-vhq.json` 的 `work_conditions.max_same_employer_months` 原值：`24`。

### `work_conditions.max_study_months`

- **类型 / 必填**：`integer` / 否
- **定义**：允许的学习时长上限（月）；`0` 的含义见 §11.3。
- **实测**：32/41 个文件出现；取值为 `0`、`4`、`6`、`11`、`36`；其余 9 个文件未填该键。
- **示例**：`au-407-training.json` 的 `work_conditions.max_study_months` 原值：`0`。

### `work_conditions.renewable`

- **类型 / 必填**：`boolean` / 否
- **定义**：是否可续签/延长。
- **实测**：41/41 个文件出现；`true` 14、`false` 27。
- **示例**：`at-rwr-card-vhq.json` 的 `work_conditions.renewable` 原值：`true`。

### `work_conditions.renewal_condition`

- **类型 / 必填**：`string` / 否
- **定义**：续签/延长的条件与路径。
- **实测**：41/41 个文件出现；每个文件各不相同。
- **示例**：`at-rwr-card-vhq.json` 的 `work_conditions.renewal_condition` 原值：
  ```text
  红白红卡一般签发 24 个月，与申请中指定的雇主绑定。换雇主须重新申请一份带劳动力市场准入的居留许可；在申请提交后满 45 天即可先上岗，前提是审核所需材料已完整提交，材料不全时 45 天起算日相应顺延。按资格条件受雇满 21 个月（过去 24 个月内，由 AMS 核定）后可申请红白红卡 plus，获得不受限的就业与定居权。
  ```

### `work_conditions.restricted_occupations`

- **类型 / 必填**：`array（string）` / 否
- **定义**：受限职业列表；空数组表示没有已知限制或未列出（实测 29/41 为空，见 §11.2）。
- **实测**：41/41 个文件出现，12 个非空；共 46 项，去重 43 个；取值分布：`职业运动员（professional sportsperson，含教练）` 2、`非技术性或临时性体力劳动` 2、`涉及儿童照护、老人照护的岗位` 2、`酒吧` 1、`夜总会` 1、`赌博场所` 1、`影响公共道德的其他场所` 1、`医疗从业者（medical practitioners）` 1、`律师` 1、`教授` 1。
- **示例**：`jp-working-holiday.json` 的 `work_conditions.restricted_occupations` 原值：`["酒吧", "夜总会", "赌博场所", "影响公共道德的其他场所"]`。

### `work_conditions.note`

- **类型 / 必填**：`string` / 否
- **定义**：工作与学习限制的补充说明。
- **实测**：41/41 个文件出现；每个文件各不相同。
- **示例**：`at-rwr-card-vhq.json` 的 `work_conditions.note` 原值：
  ```text
  持红白红卡只能为申请中指定的雇主工作，可兼营自雇但须从属于受雇关系。找工作签证期间不得就业——它是 D 类签证，只给 6 个月找工作时间，找到对口岗位并提交红白红卡申请后才能开始工作。受管制职业（医疗、公立学校教师、幼教、律师等）须先完成学历认定。 官方页面未规定持证期间的学习时长上限，故不填数字；如需修课，按当地移民局对附带学习的口径确认。
  ```

## 8. `risks[]`：风险提示

`risks` 在 schema 中可选，实测 41/41 个文件都存在，共 225 条、单文件 3–8 条；级别分布为 `warning` 104、`critical` 74、`info` 47。

### `risks`

- **类型 / 必填**：`array（对象）` / 否
- **定义**：风险提示数组，帮助用户避坑。
- **实测**：41/41 个文件出现，其中 41 个非空；共 225 条，单文件 3–8 条。
- **示例**：`at-rwr-card-vhq.json` 的 `risks[0]` 首条原文节选（该文件共 6 条）：
  ```json
  {"level": "critical", "description": "70 分门槛实际上由学历分值主导。非 MINT 本科只有 20 分，须靠年龄 20 分＋语言 10 分＋工作经验 20 分全部拿满才勉强够；MINT 本科 30 分则余地大得多。专业不对，这条路基本走不通。"}
  ```

### `risks[].level`

- **类型 / 必填**：`string` / 是（数组项内）
- **定义**：风险级别。
- **取值**：`info`=提示；`warning`=警告；`critical`=严重/阻断
- **实测**：41/41 个文件出现；225 条；取值分布：`warning` 104、`critical` 74、`info` 47；全部取值都在 schema 枚举内。
- **示例**：`at-rwr-card-vhq.json` 的 `risks[i].level` 原值：`critical`。

### `risks[].description`

- **类型 / 必填**：`string` / 是（数组项内）
- **定义**：风险说明。
- **实测**：41/41 个文件出现；225 条；共 225 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `risks[i].description` 原值：
  ```text
  70 分门槛实际上由学历分值主导。非 MINT 本科只有 20 分，须靠年龄 20 分＋语言 10 分＋工作经验 20 分全部拿满才勉强够；MINT 本科 30 分则余地大得多。专业不对，这条路基本走不通。
  ```

## 9. `sources[]`：来源列表

`sources` 必填、至少 1 条 `primary`。实测 136 条来源、单文件 1–7 条；类型为 `primary` 130、`secondary` 6；按 validator 的域名分级为 A 级 125、B 级 6、C 级 3、C-academic 2，无 D 级。`publisher` 136/136 有值，`verified_by` 与 `claim` 各 135/136（缺 1 条，见 §11.2）。

### `sources`

- **类型 / 必填**：`array（对象）` / 是
- **定义**：来源列表，必填且至少 1 条 `primary`。
- **实测**：41/41 个文件出现，其中 41 个非空；共 136 条，单文件 1–7 条。
- **示例**：`at-rwr-card-vhq.json` 的 `sources[0]` 首条原文节选（该文件共 2 条）：
  ```json
  {"type": "primary", "name": "Very Highly Qualified Workers（奥地利官方移民门户）", "url": "https://www.migration.gv.at/en/types-of-immigration/permanent-immigration/very-highly-qualified-workers/", "publisher": "Republik Österreich — migration.gv.at（奥地利联邦政府官方移民门户）", "last_verified": "2026-11-09", "verified_by": "eddieye1004", "claim": "两条路径原文：`If you don't yet have a job offer, you can come to Austria on a j
  ```
  （节选，原文 1858 字符）
- **校验器补充**：校验器要求至少 1 条 `primary`；校验 URL/日期/类型枚举；按域名把来源分为 A/B/C/D 四级并拦截 D 级与含糊 publisher；`quota_source` 必须能在 `sources[]` 中找到且为 `primary`。

### `sources[].type`

- **类型 / 必填**：`string` / 是（数组项内）
- **定义**：来源类型。
- **取值**：`primary`=官方一手来源；`secondary`=二手线索（必须回溯到 primary）
- **实测**：41/41 个文件出现；136 条；取值分布：`primary` 130、`secondary` 6；全部取值都在 schema 枚举内。
- **示例**：`at-rwr-card-vhq.json` 的 `sources[i].type` 原值：`primary`。

### `sources[].name`

- **类型 / 必填**：`string` / 是（数组项内）
- **定义**：来源名称/页面标题。
- **实测**：41/41 个文件出现；136 条；共 126 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `sources[i].name` 原值：`Very Highly Qualified Workers（奥地利官方移民门户）`。

### `sources[].url`

- **类型 / 必填**：`string` / 是（数组项内）
- **定义**：来源 URL，必须 `http(s)://`。
- **实测**：41/41 个文件出现；136 条；共 126 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `sources[i].url` 原值：
  ```text
  https://www.migration.gv.at/en/types-of-immigration/permanent-immigration/very-highly-qualified-workers/
  ```

### `sources[].publisher`

- **类型 / 必填**：`string` / 否（数组项内）
- **定义**：发布机构全名。
- **实测**：41/41 个文件出现；136 条；共 55 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `sources[i].publisher` 原值：`Republik Österreich — migration.gv.at（奥地利联邦政府官方移民门户）`。
- **校验器补充**：校验器会拦截「公开资料」「网络资料」「不详」等含糊名称（含「公开资料汇编」这类包装后缀）。

### `sources[].last_verified`

- **类型 / 必填**：`string` / 是（数组项内）
- **定义**：该来源的最后核实日期。
- **实测**：41/41 个文件出现；136 条；共 10 个不同值。
- **示例**：`at-rwr-card-vhq.json` 的 `sources[i].last_verified` 原值：`2026-11-09`。

### `sources[].verified_by`

- **类型 / 必填**：`string` / 否（数组项内）
- **定义**：该来源的核实人 GitHub 用户名。
- **实测**：41/41 个文件出现；135 条；共 1 个不同值；该数组共 136 条，本字段缺失 1 条。
- **示例**：`at-rwr-card-vhq.json` 的 `sources[i].verified_by` 原值：`eddieye1004`。

### `sources[].claim`

- **类型 / 必填**：`string` / 否（数组项内）
- **定义**：该来源具体佐证了哪条信息（防止「链接挂着但没说明用途」）。
- **实测**：41/41 个文件出现；135 条；共 130 个不同值；该数组共 136 条，本字段缺失 1 条。
- **示例**：`at-rwr-card-vhq.json` 的 `sources[i].claim` 原值：
  ```text
  两条路径原文：`If you don't yet have a job offer, you can come to Austria on a job-seeker visa, valid for six months, to look for work.`；`To qualify for either the job-seeker visa or the Red-White-Red Card, you must score at least 70 points based on the following criteria`。积分表原文（上限与分值）：`Special qualifications and skills Maximum allowable points: 40`、`Graduation from an institution of higher education, mi
  ```
  （节选，原文 1529 字符）

## 10. 公共类型与联动规则

schema 里有 6 个 `definitions`，被多个字段复用；另外有几条规则写不进 JSON Schema、只由 `scripts/validate.py` 执行。读字段条目前先看本节。

### 10.1 `date`（ISO 日期）

- 类型：`string`，模式 `^\d{4}-\d{2}-\d{2}$`。
- 校验器：除格式外还要求是真实日期（如 `2026-02-30` 会报错）；`last_verified` 距今超过 180 天给 warning，超前 1 天以上给 error（容忍 UTC/本地时区差）。
- 使用位置：`last_verified`、`sources[].last_verified`、`timeline.schedule.open_date`/`close_date`、`timeline.windows[].open_date`/`close_date`/`draw_period_end`。
- 实测：日期格式全部合法；`last_verified` 范围为 2026-10-30 至 2026-11-11；来源日期范围为 2026-09-17 至 2026-11-11。

### 10.2 `url`

- 类型：`string`，模式 `^https?://`。
- 使用位置：`program.official_url`、`steps[].official_link`、`sources[].url`、`timeline.quota_source`。
- 校验器：URL 语法检查；`--check-links` 会实际访问 `program.official_url`、`sources[].url`、`steps[].official_link` 三类链接（`quota_source` 只做归属校验，不单独发请求）。

### 10.3 `money`（金额对象）

- 结构：必填 `local_amount`（number，≥0）与 `currency`（枚举）；可选 `cny_estimate`（number）与 `note`（string）。`additionalProperties: false`。
- 使用位置：`eligibility.funds.amount`（13 个对象 + 9 个显式 `null` + 19 个未填）与 `timeline.fees[].amount`（56 条）。
- 实测：共出现 69 个金额对象；14 种币种（`AUD`/`CAD`/`CNY`/`EUR`/`GBP`/`ISK`/`JPY`/`KRW`/`NOK`/`NZD`/`SEK`/`SGD`/`TWD`/`USD`），枚举内另有 10 种未使用；`cny_estimate` 在资金金额中 13/13 填写，在费用金额中 43/56 填写（缺 13 条）；`note` 在资金金额中 13/13 填写，在费用金额中 43/56 填写。
- 校验器：`local_amount` 必须是非负数字；`currency` 必须在枚举内；`cny_estimate` 若存在必须是数字。`amount` 为 `null` 时校验器跳过、不报错（见 §11.3）。

### 10.4 配额四态联动（validator 执行）

`timeline.quota_status` 是一个断言，不是一个备注；四态与其余字段的约束如下：

| `quota_status` | `quota` | `quota_basis` | `quota_source` | 含义 |
|---|---|---|---|---|
| `capped` | 必填正整数 | 必填（`annual`/`concurrent`） | 必填 | 有具体配额 |
| `no_quota` | 必须 `null` | 不得填写 | 必填 | 官方明确不设上限，或不对中国大陆护照分配名额 |
| `not_published` | 必须 `null` | 不得填写 | 必填 | 官方设限额但未公布数字 |
| `unverified` | 必须 `null` | 不得填写 | 不得填写 | 尚未核实 |

附加规则：`quota_note` 四态都必须有实质内容（至少 8 个字符）；`capped`/`no_quota`/`not_published` 的 `quota_source` 必须与 `sources[]` 中某条 `url` 完全一致，且那条来源必须是 `primary`。

实测分布：`capped` 4 个（AU 462：5000、`annual`；NZ 中国 WHV：1000、`annual`；SG S Pass：1、`concurrent`；SG Work Holiday Pass：2000、`concurrent`）；`no_quota` 34 个；`not_published` 1 个（UK HPI）；`unverified` 2 个（AT RWR、DE Chancenkarte）。39 个 `quota_source` 全部通过归属与 `primary` 校验。

### 10.5 窗口日历纪律（validator 执行）

`timeline.schedule` 的核心纪律是「具体日期只能由 `confirmed` 携带」：

- `inferred` / `unknown` 时 `open_date`、`close_date` 必须为空（实测有 10/11 个显式 `null`，见 §11.3）。
- `rolling` 不得标 `confirmed`（rolling 没有日期，不需要日期就是确定的）。
- `annual_cycle` + `inferred` 必须有 `cycle_note`，写下往年实际日期序列作为推断依据。
- `rolling` / `no_window` 不得有 `open_date` / `close_date`。
- `lead_time_days` 为 0–365 整数；`note` 至少 8 个字符；`close_date` 不得早于 `open_date`。

实测分布：`type` 为 rolling 32、fixed_dates 6、annual_cycle 2、no_window 1；`date_confidence` 为 unknown 36、confirmed 3、inferred 2；`status` 为 always_open 32、closed 4、unknown 4、open 1。

### 10.6 来源可信度分级（validator 执行）

validator 按域名把 `sources[].url` 分为四级：

- A：政府/使领馆/移民局/官方法规库（含 `migration.gv.at`、`udi.no`、`migrationsverket.se` 等点名白名单）；
- B：项目本体国际组织官网（IAESTE / AIESEC）；
- C：高校官网（记为 C-academic）与其他可核验第三方；
- D：百科、自媒体、商业博客、来源不明——出现即 error，禁止作为来源。

附加规则：每个项目至少要有一条 A/B 级来源；标为 `primary` 但域名只有 C 级会 warning；`publisher` 不得是「公开资料」「不详」等含糊名称（含「公开资料汇编」这类包装后缀）。

实测：A 125、B 6、C 3、C-academic 2，无 D；`primary` 130 条全部落在 A/B（无 C 级 primary 告警）；3 条 C 级与 2 条 C-academic 均为 `secondary`。

### 10.7 对象复用关系

| `definitions` | 被哪些字段引用 |
|---|---|
| `date` | 上列 7 个日期字段 |
| `url` | 4 个 URL 字段 |
| `money` | `eligibility.funds.amount`、`timeline.fees[].amount` |
| `passport_eligibility` | `eligibility.passport_types` |
| `eligibility_status` | `passport_types` 的三个护照键 |
| `source` | `sources[]` 的数组项 |

同一份定义在不同位置出现时，本文按使用路径分别给出现次数与示例，避免「定义相同就以为用法相同」。

## 11. 实测与定义不一致清单

本节只报告，**不改数据、不改校验器**。判定依据分三层：schema 的 `additionalProperties`/类型/枚举/描述、validator 的硬规则、字段语义。CI 当前全绿，说明下列问题不在 CI 的拦截范围内，而不是「不存在」。

### 11.1 schema 未定义但数据已使用的键（3 个）

`data/schema.json` 的所有对象都写了 `additionalProperties: false`，但 CI 不执行 JSON Schema 校验：`scripts/validate.py` 是手写校验器，只检查它认识的键。实测有 3 个 schema 未定义的键：

| 键 | 使用文件 | 实测值 | 影响 |
|---|---|---|---|
| `eligibility.passport_types.tw_china` | 12/41 | `eligible` 11 个、`unknown` 1 个；示例 `au-407-training.json` → `"eligible"`，`dk-working-holiday.json` → `"unknown"` | 这 12 个文件**没有** schema 定义的 `taiwan_china`；`taiwan_china` 只在另外 29 个文件出现，两者恰好互补。validator 只遍历 `mainland_china`/`hong_kong_china`/`taiwan_china`，所以既没报「缺少 `taiwan_china`」，也没报「多出 `tw_china`」。下游若按 `taiwan_china` 读取，这 12 个项目会读不到台湾护照资格。 |
| `sources[].note` | 3/41 | `de-16e-internship.json`（`sources[0]`）：2026-10-30 复核未能读到正文：该站启用 Radware 人机验证（HTTP 200，返回 `Secure access verification` +…（截断）<br>`nz-china-whv.json`（`sources[1]`）：2026-10-30 复核未能读到正文：该站启用 Incapsula 人机验证，curl 返回 Request unsuccessful，无头浏览器需等 20…（截断）<br>`us-j1-summer-work-travel.json`（`sources[1]`）：2026-10-30 未重抓。年龄 18-28 与项目费属于中国落地口径，不是美国国务院规定。 | 来源对象不允许额外键；这 3 条备注记录的是「本轮未能读取正文」的复核限制，删掉会丢失重要信息，保留则违反 schema。需要 schema 或来源结构的所有者决定归属（本单不处理）。 |
| `work_conditions.max_stay_months_note` | 1/41 | `no-skilled-worker.json` → `""`（空字符串） | 无定义的键且为空值；validator 对 `work_conditions` 只检查对象形状，不检查子键，因此无任何提示。 |

12 个使用 `tw_china` 的文件：`au-407-training.json`、`au-485-vocational.json`、`dk-working-holiday.json`、`es-busqueda-empleo.json`、`fi-look-for-work.json`、`fr-recherche-emploi.json`、`ie-third-level-graduate.json`、`is-job-search-after-graduation.json`、`it-ricerca-lavoro.json`、`mt-nomad-residence.json`、`sg-employment-pass.json`、`sg-s-pass.json`。

### 11.2 长期为空 / 低使用字段

「出现」按键是否出现统计；「实际使用」按非空/非空数组统计。

| 字段 | 出现 | 实际使用 | 结论 |
|---|---|---|---|
| `eligibility.education.major_restriction` | 41/41（共 4 项） | 仅 `global-iaeste.json` 1 个非空（4 项：Science/Engineering/Technology/部分生物技术、生物医学专业）；其余 40 个 `[]` | 事实上的「几乎不用」。空数组=不限专业，尚可读；但 40 个空值让该字段几乎没有区分度。 |
| `eligibility.education.years_completed` | 1/41 | `au-462-work-holiday.json` → `2` | 只在 1 个文件使用；其余 40 个没有用「已完成年限」这个粒度。 |
| `eligibility.language.tests` | 41/41（10 条） | 非空仅 4 个文件、共 10 条；25 个 `required=false`；另有 12 个 `required=true` 但 `tests=[]` | 语言要求与考试列表脱节（见 §11.5）。 |
| `eligibility.funds.amount` | 22/41（9 个显式 `null`、13 个对象、19 个未填） | 13 个有金额；7 个 `required=true` 但无金额 | 「要求资金」与「资金金额」不对齐（见 §11.5）；另有 9 个 `null` 不符合 schema 类型（见 §11.3）。 |
| `timeline.fees` | 41/41（56 条） | 36 个非空（56 条），5 个 `[]`：`dk-working-holiday.json`、`global-aiesec-global-talent.json`、`global-iaeste.json`、`kr-h1-working-holiday.json`、`us-j1-camp-counselor.json` | 5 个项目没有任何费用记录；schema 允许空数组，validator 不要求至少 1 条。 |
| `timeline.fees[].refundable` | 36/41（56 条） | `true` 0、`false` 56 | 字段存在但从未取 `true`；目前无法区分「明确不可退」与「未核实」。 |
| `timeline.windows[].draw_period_end` | 1/41（1 条） | `au-462-work-holiday.json` → `"2027-04-30"` | 只有抽签项目用得上，窄用属正常。 |
| `timeline.windows[].lodgement_window_days` | 1/41（1 条） | `au-462-work-holiday.json` → `28` | 同上。 |
| `timeline.schedule.cycle_note` | 5/41 | 2 个 `annual_cycle`（JP、NZ）必填 + 3 个 `fixed_dates` 补充 | 大部分项目没有往年日期序列可写，窄用属正常。 |
| `timeline.schedule.open_date` / `close_date` | 13/41 / 13/41 | 有具体日期各 3 / 2 个；显式 `null` 各 10 / 11 个；其余 28 个未填 | 绝大多数项目没有可确认日期；`null` 与「未填」两种空法并存，且 `null` 不符合 schema 类型（见 §11.3）。 |
| `work_conditions.restricted_occupations` | 41/41（46 项） | 12 个非空（46 项），29 个 `[]` | 与 `major_restriction` 同类：空数组含义（无限制/未列出）没有区分。 |
| `work_conditions.max_study_months` | 32/41 | 25 个 `0`、7 个正数、9 个未填 | `0` 同时承担「不允许」「无上限/未规定」两种含义（见 §11.3）。 |
| `work_conditions.max_same_employer_months` | 41/41 | 18 个 `0` | 同上；0 的含义需要结合 `note` 才能判断。 |
| `sources[].verified_by` / `sources[].claim` | 136 条中 135 条 | 缺 `kr-h1-working-holiday.json` 的 `sources[2]` | 1 条来源缺核实人与佐证说明；其余 135 条都齐。 |
| `timeline.quota_basis` | 4/41 | 仅在 4 个 `capped` 项目出现 | schema 条件必填导致的正常窄用。 |
| `timeline.quota_source` | 39/41 | 除 2 个 `unverified` 外都有 | 四态设计的正常结果。 |

### 11.3 定义与实际语义偏差

1. **`program.country_code` 用 `GL` 表示全球项目。** schema 同时写「ISO 3166-1 alpha-2 国家代码」和「全球性项目用 GL」。但 `GL` 在 ISO 3166-1 中是格陵兰，不是「全球」；2 个文件（`global-aiesec-global-talent.json`、`global-iaeste.json`）使用了它，`country` 写「全球（…）」。按 ISO 代码消费数据的下游会把这两个项目误判为格陵兰。

2. **`program.summary` 的 200 字上限与 validator 的 500 字符阈值不一致。** schema 描述「200 字以内」，validator 只在超过 500 字符时 warning。实测有 5 个文件超过 200 字：`it-ricerca-lavoro.json`（270 字）、`ie-working-holiday-authorisation.json`（264 字）、`global-iaeste.json`（264 字）、`au-485-vocational.json`（258 字）、`ie-third-level-graduate.json`（208 字）。这些文件不会让 CI 变红，但不符合 schema 描述。

3. **年龄 `0` / `99` 是哨兵值，不是真实年龄。** schema 只允许 0–99 的整数，未定义「不限」。实测 `(min,max)=(0,99)` 25 个文件，`min=0` 25 个文件，`max=99` 30 个文件；例如 `at-rwr-card-vhq.json` → `0`/`99`（积分制、无年龄上限），`au-462-work-holiday.json` → `18`/`30`。读者若直接把 0/99 当年龄，会得到「0 岁可申」的错误结论。

4. **`work_conditions` 的 `0` 含义不统一。** `max_same_employer_months=0` 18 个文件（`au-407-training.json`、`au-485-vocational.json`、`ca-iec-working-holiday.json`、`dk-working-holiday.json`、`es-busqueda-empleo.json`、`fi-look-for-work.json`、`fr-recherche-emploi.json`、`ie-third-level-graduate.json` 等 18 个），`max_study_months=0` 25 个文件，`max_stay_months=0` 仅 `dk-working-holiday.json` 1 个。`dk-working-holiday.json` 的 `renewal_condition` 明确写「0 表示『未获取到该数据』，不是『不允许』」；其他文件的 `0` 多表示「无此限制 / 不适用」，也有「不允许学习」的读法。同一个数值至少承载两种相反语义，schema 没有定义哨兵值。

5. **`program.active=false` 被用来表示「对中国大陆护照不可申」，不是「项目当前不开放」。** schema 描述是「当前是否开放」。实测 3 个 `false`：`jp-working-holiday.json`、`kr-h1-working-holiday.json`、`sg-work-holiday-programme.json`；三者的 `mainland_china` 都是 `not_eligible`，而项目对其他国家/地区仍在运行（例如 JP 打工度假对 33 个国家和地区开放，见其 `summary`）。按 `active` 做「项目是否停办」筛选会把这三个项目误判为停办。

6. **`timeline.windows[]` 对滚动/无窗口项目也被迫填写。** schema 定义 `windows` 是「申请窗口」，而 `schedule.type=rolling/no_window` 表示没有窗口；但 validator 要求 `windows` 至少 1 条。实测 33 个 rolling/no_window 文件仍写了 59 条 `windows`（状态：`open` 31、`unknown` 18、`upcoming` 8、`closed` 2）。这些条目实际记录的是「某年的状态」，不是「申请窗口」；字段语义被 validator 的必填规则撑大了。

7. **`timeline.schedule.date_confidence=unknown` 被同时用于「无法判断」与「不需要日期」。** schema 定义 `unknown` 是「连规律都无从判断」。实测 36 个 `unknown`，其中 32 个是 rolling、1 个是 no_window；这些项目的 `schedule.note` 明确写「不是没查清，而是不需要日期」。同一枚举值承担「未核实」与「不适用」两种含义。

8. **`timeline.schedule.next_window_hint` 41/41 全填，超出「仅在有依据时填」的定义。** 对 32 个 rolling 与 1 个 no_window 项目，它写的是「无窗口概念，全年可递交」这类说明，而不是「下一次窗口预告」。它已被当作 `schedule` 的通用备注使用。

9. **`timeline.processing_time` 不是 schema 示例暗示的短句。** schema 示例是「4-8 周」，实测长度为 5–214 字符，很多是整段解释（为什么官方不给天数、受什么影响）。字段名与类型没变，但按短句消费的下游（如直接展示一行）会遇到长文本。

10. **schema 的类型声明没覆盖实际的 `null` 用法。** `timeline.quota` 显式声明 `["integer","null"]` 是唯一允许 `null` 的数值键；但实测还有 9 个 `eligibility.funds.amount: null`、10 个 `timeline.schedule.open_date: null`、11 个 `timeline.schedule.close_date: null`。后三者 schema 类型分别是 `money`（object）与 `date`（string），不允许 `null`。更矛盾的是 `schedule.open_date` 的 schema 描述自己写着「inferred 与 unknown 必须为 null」——描述要求 `null`，类型却禁止 `null`。validator 对这三处都放行（`amount` 非对象则跳过；`open_date`/`close_date` 显式把 `null` 当合法空值），所以数据与 CI 都不报错。

### 11.4 枚举值使用情况

schema 定义的全部枚举值与实测使用情况（「使用」按字段出现次数计）：

| 枚举 | 定义值 | 实测使用 | 未使用 / 说明 |
|---|---|---|---|
| `program.region` | 7 | 5（europe 20、north_america 8、oceania 6、asia 5、global 2） | `south_america`、`africa` 未使用 |
| `program.program_type` | 5 | 5（short_term_work 22、working_holiday 9、paid_internship 5、cultural_exchange 3、internship_visa 2） | — |
| `program.tags` | 21 | 19（164 项） | `no_english_required`、`unpaid` 未使用 |
| `eligibility` 护照状态 | 4 | 3（eligible 111、not_eligible 10、unknown 2） | `conditional` 未使用 |
| `eligibility.education.minimum_level` | 6 | 6 | — |
| `eligibility.language.tests[].test` | 7 | 5（IELTS 3、PTE 2、TOEFL_iBT 2、Cambridge 2、none 1） | `CEFR`、`OET` 未使用 |
| `eligibility.other_requirements[].type` | 11 | 11 | — |
| `timeline.mechanism` | 5 | 4（rolling 33、ballot 3、appointment 3、first_come_first_served 2） | `annual_negotiation` 未使用 |
| `timeline.quota_status` | 4 | 4 | — |
| `timeline.quota_basis` | 2 | 2 | — |
| `timeline.windows[].status` | 4 | 4 | — |
| `timeline.schedule.type` | 4 | 4 | — |
| `timeline.schedule.status` | 5 | 5 | — |
| `timeline.schedule.date_confidence` | 3 | 3 | — |
| `risks[].level` | 3 | 3（warning 104、critical 74、info 47） | — |
| `sources[].type` | 2 | 2（primary 130、secondary 6） | — |
| 币种 | 24 | 14 | `CHF`、`DKK`、`HKD`、`IDR`、`ILS`、`MYR`、`PLN`、`THB`、`TRY`、`VND` 未使用 |

「未使用」本身不是错误：这些值是为未来项目预留的。列出来是为了让新增数据时能区分「确实没有这种项目」与「忘了用某个枚举」。

### 11.5 跨字段 / 依赖关系中的不一致

- **`program.tags` 的 `renewable` 与 `work_conditions.renewable` 不同步。** 9 个文件的 `work_conditions.renewable=true` 但 `program.tags` 没有 `renewable`：`at-rwr-card-vhq.json`、`de-chancenkarte.json`、`ie-third-level-graduate.json`、`no-skilled-worker.json`、`us-f1-opt.json`、`us-j1-intern.json`、`us-j1-research-scholar.json`、`us-j1-summer-work-travel.json`、`us-j1-trainee.json`；反向（有标签但 `renewable=false`）为 0。若「可续签」标签应按 `work_conditions.renewable` 生成，这 9 个文件会被前端的「可续签」筛选漏掉。

- **`eligibility.language.required=true` 但 `tests=[]`。** 12 个文件：`at-rwr-card-vhq.json`、`au-407-training.json`、`au-485-graduate.json`、`au-485-vocational.json`、`ca-pgwp.json`、`de-chancenkarte.json`、`global-iaeste.json`、`uk-hpi-visa.json`、`us-j1-camp-counselor.json`、`us-j1-intern.json`、`us-j1-research-scholar.json`、`us-j1-trainee.json`。这些项目要求语言能力，但没有列出可接受的考试与分数线；读者只能从 `note` 找信息。

- **`eligibility.funds.required=true` 但没有金额。** 7 个文件：`at-rwr-card-vhq.json`、`de-20-job-search.json`、`de-chancenkarte.json`、`es-busqueda-empleo.json`、`jp-working-holiday.json`、`uk-short-term-study-visa.json`、`us-j1-research-scholar.json`。schema 允许 `amount` 可选，所以不违反结构；但「要求资金」没有给出金额或计算口径，无法用于准备预算。

- **`quota_status=no_quota` 与 `mainland_china=not_eligible` 同时出现。** 6 个文件：`ca-iec-working-holiday.json`、`dk-working-holiday.json`、`ie-working-holiday-authorisation.json`、`jp-working-holiday.json`、`kr-h1-working-holiday.json`、`uk-youth-mobility-scheme.json`。schema 的四态说明明确「no_quota 包含不对中国大陆护照分配名额」，所以这不是矛盾；但「无名额」与「不可申请」在页面上容易被读成两件事，建议读者结合护照资格一起看。

- **`tw_china` 让 12 个文件缺少 `taiwan_china`。** 见 §11.1；这是本节跨字段问题的根源，也是唯一会影响真实读取路径的问题（其余多为展示/口径问题）。

- **1 条来源缺 `verified_by` / `claim`。** 见 §11.2 的 `kr-h1-working-holiday.json` 的 `sources[2]`。该来源仍是 `primary`，但无法说明它具体佐证了哪条信息。

### 11.6 校验器未覆盖的 schema 约束

| schema 约束 | validator 实际行为 | 实测影响 |
|---|---|---|
| `additionalProperties: false` | 不检查 | 3 个未定义键通过 CI（§11.1） |
| `funds.amount` 为 object、日期字段为 string | `null` 时跳过或放行 | 9 + 10 + 11 个 `null` 通过 CI（§11.3） |
| `timeline.schedule` 在 schema 的 `timeline.required` 中 | validator 的 `timeline` 必填列表没有 `schedule`；缺失时 `_check_schedule` 直接返回 | 41/41 都有，但未来新增文件可以漏掉 `schedule` 且 CI 仍绿 |
| `program.summary` 200 字 | 仅 >500 字符 warning | 5 个文件 200–270 字通过（§11.3） |
| `work_conditions` 各数值/布尔键类型 | 只检查容器是对象、`restricted_occupations` 是数组 | 0/缺失的含义问题不会被发现（§11.3） |
| `eligibility.funds.amount` 为 `null` | `if isinstance(amt, dict)` 才校验 | 9 个 `null` 不报错（§11.3） |
| `program.active` 类型 | 未显式检查 | 实测均为布尔，无问题 |

以上差异本单只登记，不修改；修改它们会改变数据/校验器行为，超出「只新增 docs/FIELDS.md」的验收口径。

## 12. 核对方法与复现

### 12.1 做了哪些核对

1. 读 `data/schema.json`（437 行），展开 6 个 `definitions` 与全部 `properties`，得到 115 个字段路径（含容器、数组项、`money` 子字段）。
2. 读 `scripts/validate.py`（1,329 行），逐段提取 schema 表达不了的联动规则（配额四态、窗口日历纪律、来源分级、`step_no` 连续、金额校验等），并在 §10 与各字段「校验器补充」中标注。
3. 逐个打开 41 个 `data/programs/*.json`（共 10,804 行），用只读脚本按字段路径统计：出现文件数、出现条数、`null` 数、类型分布、枚举分布、数值范围、数组长度、示例原值。
4. 对异常项逐个人工回看原文：`no-skilled-worker.json`（未定义键）、`dk-working-holiday.json`（`0` 哨兵）、`kr-h1-working-holiday.json`（缺 `claim`）、`global-iaeste.json`（`GL` + 专业限制）、`de-16e-internship.json` / `nz-china-whv.json` / `us-j1-summer-work-travel.json`（`sources[].note`）、`au-462-work-holiday.json`（抽签窗口）、`at-rwr-card-vhq.json`（年龄/配额 `unverified`）、`ie-working-holiday-authorisation.json`（`confirmed` 窗口）。
5. 跑核对前基线：181 个单元测试、`validate.py`、`gen_sources.py --check`、`match_readiness.py --check`、`track.py`（结果见文首）。

### 12.2 计数口径的限制

- 统计脚本是一次性只读脚本，未入库（本单验收只允许新增 `docs/FIELDS.md`）。复现时按本文的字段路径与「出现」定义重新统计即可；数据变更后 §11 的具体数字会漂移。
- 「出现」不区分「字段存在但值为空」与「字段不存在」；对 `null`、空数组、空字符串，都在对应条目里单独报数。
- 示例优先取非 `null` 值；短值内联保留完整原值，超过 400 字符的散文/长 JSON 截断并标 `…（节选，原文 N 字符）`。
- 本文不评价数据内容是否正确（如某个配额数字是否最新），只核对「字段结构与实际用法是否一致」。数据事实的时效性由 `last_verified` 与 `scripts/track.py` 负责。

### 12.3 复核命令

```bash
# 数据与校验器
python scripts/validate.py                  # 0 error / 0 warning / 2 info
python scripts/gen_sources.py --check       # 来源清单一致
python scripts/match_readiness.py --check   # 判定产物一致
python scripts/track.py                     # 复核台账

# 单元测试（CI 同款）
python -m unittest discover -s tests -v     # 181 tests OK
```

本单只新增 `docs/FIELDS.md`；CI 的 `docs/**` 路径会触发 `validate.yml`，上述测试与数据校验照常执行。

## 附录 A：41 个文件清单

本单核对了 `data/programs/` 下全部 41 个文件，无遗漏：

| 文件 | `program.id` | 国家/地区 | 类型 | 大陆护照 | 配额 | `schedule` |
|---|---|---|---|---|---|---|
| `at-rwr-card-vhq.json` | `at-rwr-card-vhq` | 奥地利 | `short_term_work` | `eligible` | `unverified` | `rolling` / `unknown` |
| `au-407-training.json` | `au-407-training` | 澳大利亚 | `internship_visa` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `au-462-work-holiday.json` | `au-462-work-holiday` | 澳大利亚 | `working_holiday` | `eligible` | `capped` | `fixed_dates` / `confirmed` |
| `au-485-graduate.json` | `au-485-graduate` | 澳大利亚 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `au-485-vocational.json` | `au-485-vocational` | 澳大利亚 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `ca-iec-working-holiday.json` | `ca-iec-working-holiday` | 加拿大 | `working_holiday` | `not_eligible` | `no_quota` | `fixed_dates` / `unknown` |
| `ca-pgwp.json` | `ca-pgwp` | 加拿大 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `de-16e-internship.json` | `de-16e-internship` | 德国 | `internship_visa` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `de-20-job-search.json` | `de-20-job-search` | 德国 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `de-chancenkarte.json` | `de-chancenkarte` | 德国 | `short_term_work` | `eligible` | `unverified` | `rolling` / `unknown` |
| `dk-working-holiday.json` | `dk-working-holiday` | 丹麦 | `working_holiday` | `not_eligible` | `no_quota` | `no_window` / `unknown` |
| `es-busqueda-empleo.json` | `es-busqueda-empleo` | 西班牙 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `fi-look-for-work.json` | `fi-look-for-work` | 芬兰 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `fr-recherche-emploi.json` | `fr-recherche-emploi` | 法国 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `global-aiesec-global-talent.json` | `global-aiesec-global-talent` | 全球（120+ 国家和地区） | `paid_internship` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `global-iaeste.json` | `global-iaeste` | 全球（100+ 国家/地区） | `paid_internship` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `ie-third-level-graduate.json` | `ie-third-level-graduate` | 爱尔兰 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `ie-working-holiday-authorisation.json` | `ie-working-holiday-authorisation` | 爱尔兰 | `working_holiday` | `not_eligible` | `no_quota` | `fixed_dates` / `confirmed` |
| `is-job-search-after-graduation.json` | `is-job-search-after-graduation` | 冰岛 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `it-ricerca-lavoro.json` | `it-ricerca-lavoro` | 意大利 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `jp-working-holiday.json` | `jp-working-holiday` | 日本 | `working_holiday` | `not_eligible` | `no_quota` | `annual_cycle` / `inferred` |
| `kr-h1-working-holiday.json` | `kr-h1-working-holiday` | 韩国 | `working_holiday` | `not_eligible` | `no_quota` | `fixed_dates` / `unknown` |
| `mt-nomad-residence.json` | `mt-nomad-residence` | 马耳他 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `nl-orientation-year.json` | `nl-orientation-year` | 荷兰 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `no-skilled-worker.json` | `no-skilled-worker` | 挪威 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `nz-china-whv.json` | `nz-china-whv` | 新西兰 | `working_holiday` | `eligible` | `capped` | `annual_cycle` / `inferred` |
| `nz-post-study-work.json` | `nz-post-study-work` | 新西兰 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `se-look-for-work.json` | `se-look-for-work` | 瑞典 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `sg-employment-pass.json` | `sg-employment-pass` | 新加坡 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `sg-s-pass.json` | `sg-s-pass` | 新加坡 | `short_term_work` | `eligible` | `capped` | `rolling` / `unknown` |
| `sg-work-holiday-programme.json` | `sg-work-holiday-programme` | 新加坡 | `working_holiday` | `not_eligible` | `capped` | `fixed_dates` / `unknown` |
| `uk-graduate-visa.json` | `uk-graduate-visa` | 英国 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `uk-hpi-visa.json` | `uk-hpi-visa` | 英国 | `short_term_work` | `eligible` | `not_published` | `rolling` / `unknown` |
| `uk-short-term-study-visa.json` | `uk-short-term-study-visa` | 英国 | `cultural_exchange` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `uk-youth-mobility-scheme.json` | `uk-youth-mobility-scheme` | 英国 | `working_holiday` | `not_eligible` | `no_quota` | `fixed_dates` / `confirmed` |
| `us-f1-opt.json` | `us-f1-opt` | 美国 | `short_term_work` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `us-j1-camp-counselor.json` | `us-j1-camp-counselor` | 美国 | `cultural_exchange` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `us-j1-intern.json` | `us-j1-intern` | 美国 | `paid_internship` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `us-j1-research-scholar.json` | `us-j1-research-scholar` | 美国 | `cultural_exchange` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `us-j1-summer-work-travel.json` | `us-j1-summer-work-travel` | 美国 | `paid_internship` | `eligible` | `no_quota` | `rolling` / `unknown` |
| `us-j1-trainee.json` | `us-j1-trainee` | 美国 | `paid_internship` | `eligible` | `no_quota` | `rolling` / `unknown` |

## 附录 B：全部字段总览

共 115 个字段路径（含容器与数组项）。详细定义、实测与示例见正文对应章节。

| 字段 | 类型 | 必填 | 出现 |
|---|---|---|---|
| `schema_version` | `string` | 是 | 41/41 |
| `program` | `object` | 是 | 41/41 |
| `program.id` | `string` | 是 | 41/41 |
| `program.name` | `string` | 是 | 41/41 |
| `program.name_en` | `string` | 是 | 41/41 |
| `program.country` | `string` | 是 | 41/41 |
| `program.country_code` | `string` | 是 | 41/41 |
| `program.region` | `string` | 是 | 41/41 |
| `program.program_type` | `string` | 是 | 41/41 |
| `program.visa_code` | `string` | 否 | 41/41 |
| `program.official_url` | `string` | 是 | 41/41 |
| `program.authority` | `string` | 否 | 41/41 |
| `program.summary` | `string` | 否 | 41/41 |
| `program.tags` | `array<string>` | 否 | 41/41（164 项） |
| `program.active` | `boolean` | 否 | 41/41 |
| `eligibility` | `object` | 是 | 41/41 |
| `eligibility.passport_types` | `object` | 是 | 41/41 |
| `eligibility.passport_types.mainland_china` | `string` | 是 | 41/41 |
| `eligibility.passport_types.hong_kong_china` | `string` | 否 | 41/41 |
| `eligibility.passport_types.taiwan_china` | `string` | 否 | 29/41 |
| `eligibility.passport_types.note` | `string` | 否 | 41/41 |
| `eligibility.age` | `object` | 是 | 41/41 |
| `eligibility.age.min` | `integer` | 是 | 41/41 |
| `eligibility.age.max` | `integer` | 是 | 41/41 |
| `eligibility.age.note` | `string` | 是 | 41/41 |
| `eligibility.education` | `object` | 是 | 41/41 |
| `eligibility.education.minimum_level` | `string` | 是 | 41/41 |
| `eligibility.education.years_completed` | `integer` | 否 | 1/41 |
| `eligibility.education.major_restriction` | `array<string>` | 否 | 41/41（4 项） |
| `eligibility.education.note` | `string` | 是 | 41/41 |
| `eligibility.language` | `object` | 是 | 41/41 |
| `eligibility.language.required` | `boolean` | 是 | 41/41 |
| `eligibility.language.tests` | `array<object>` | 否 | 41/41（10 条） |
| `eligibility.language.tests[].test` | `string` | 是（项内） | 4/41（10 条） |
| `eligibility.language.tests[].min_score` | `number` | 是（项内） | 4/41（10 条） |
| `eligibility.language.tests[].validity_months` | `integer` | 是（项内） | 4/41（10 条） |
| `eligibility.language.note` | `string` | 是 | 41/41 |
| `eligibility.funds` | `object` | 是 | 41/41 |
| `eligibility.funds.required` | `boolean` | 是 | 41/41 |
| `eligibility.funds.amount` | `object` | 否 | 22/41 |
| `eligibility.funds.amount.local_amount` | `number` | 是 | 13/41 |
| `eligibility.funds.amount.currency` | `string` | 是 | 13/41 |
| `eligibility.funds.amount.cny_estimate` | `number` | 否 | 13/41 |
| `eligibility.funds.amount.note` | `string` | 否 | 13/41 |
| `eligibility.funds.note` | `string` | 是 | 41/41 |
| `eligibility.other_requirements` | `array<object>` | 是 | 41/41（140 条） |
| `eligibility.other_requirements[].type` | `string` | 是（项内） | 41/41（140 条） |
| `eligibility.other_requirements[].required` | `boolean` | 是（项内） | 41/41（140 条） |
| `eligibility.other_requirements[].note` | `string` | 是（项内） | 41/41（140 条） |
| `timeline` | `object` | 是 | 41/41 |
| `timeline.mechanism` | `string` | 是 | 41/41 |
| `timeline.quota_status` | `string` | 是 | 41/41 |
| `timeline.quota` | `integer / null` | 是 | 41/41 |
| `timeline.quota_basis` | `string` | 否 | 4/41 |
| `timeline.quota_source` | `string` | 否 | 39/41 |
| `timeline.quota_note` | `string` | 是 | 41/41 |
| `timeline.windows` | `array<object>` | 是 | 41/41（72 条） |
| `timeline.windows[].year` | `integer` | 是（项内） | 41/41（72 条） |
| `timeline.windows[].status` | `string` | 是（项内） | 41/41（72 条） |
| `timeline.windows[].open_date` | `string` | 否（项内） | 3/41（4 条） |
| `timeline.windows[].close_date` | `string` | 否（项内） | 2/41 |
| `timeline.windows[].draw_period_end` | `string` | 否（项内） | 1/41 |
| `timeline.windows[].lodgement_window_days` | `integer` | 否（项内） | 1/41 |
| `timeline.windows[].note` | `string` | 是（项内） | 41/41（72 条） |
| `timeline.schedule` | `object` | 是 | 41/41 |
| `timeline.schedule.type` | `string` | 是 | 41/41 |
| `timeline.schedule.status` | `string` | 是 | 41/41 |
| `timeline.schedule.date_confidence` | `string` | 是 | 41/41 |
| `timeline.schedule.open_date` | `string` | 否 | 13/41 |
| `timeline.schedule.close_date` | `string` | 否 | 13/41 |
| `timeline.schedule.cycle_note` | `string` | 否 | 5/41 |
| `timeline.schedule.next_window_hint` | `string` | 否 | 41/41 |
| `timeline.schedule.lead_time_days` | `integer` | 是 | 41/41 |
| `timeline.schedule.note` | `string` | 是 | 41/41 |
| `timeline.fees` | `array<object>` | 否 | 41/41（56 条） |
| `timeline.fees[].item` | `string` | 是（项内） | 36/41（56 条） |
| `timeline.fees[].amount` | `object` | 是（项内） | 36/41 |
| `timeline.fees[].amount.local_amount` | `number` | 是（项内） | 36/41（56 条） |
| `timeline.fees[].amount.currency` | `string` | 是（项内） | 36/41（56 条） |
| `timeline.fees[].amount.cny_estimate` | `number` | 否（项内） | 26/41（43 条） |
| `timeline.fees[].amount.note` | `string` | 否（项内） | 31/41（43 条） |
| `timeline.fees[].refundable` | `boolean` | 否（项内） | 36/41（56 条） |
| `timeline.processing_time` | `string` | 否 | 41/41 |
| `documents` | `array<object>` | 是 | 41/41（267 条） |
| `documents[].name` | `string` | 是（项内） | 41/41（267 条） |
| `documents[].required` | `boolean` | 是（项内） | 41/41（267 条） |
| `documents[].note` | `string` | 否（项内） | 41/41（267 条） |
| `documents[].prepare_days` | `integer` | 否（项内） | 41/41（267 条） |
| `steps` | `array<object>` | 是 | 41/41（217 条） |
| `steps[].step_no` | `integer` | 是（项内） | 41/41（217 条） |
| `steps[].title` | `string` | 是（项内） | 41/41（217 条） |
| `steps[].description` | `string` | 是（项内） | 41/41（217 条） |
| `steps[].duration` | `string` | 否（项内） | 41/41（217 条） |
| `steps[].official_link` | `string` | 否（项内） | 41/41（217 条） |
| `work_conditions` | `object` | 否 | 41/41 |
| `work_conditions.max_stay_months` | `integer` | 否 | 41/41 |
| `work_conditions.max_same_employer_months` | `integer` | 否 | 41/41 |
| `work_conditions.max_study_months` | `integer` | 否 | 32/41 |
| `work_conditions.renewable` | `boolean` | 否 | 41/41 |
| `work_conditions.renewal_condition` | `string` | 否 | 41/41 |
| `work_conditions.restricted_occupations` | `array<string>` | 否 | 41/41（46 项） |
| `work_conditions.note` | `string` | 否 | 41/41 |
| `risks` | `array<object>` | 否 | 41/41（225 条） |
| `risks[].level` | `string` | 是（项内） | 41/41（225 条） |
| `risks[].description` | `string` | 是（项内） | 41/41（225 条） |
| `sources` | `array<object>` | 是 | 41/41（136 条） |
| `sources[].type` | `string` | 是（项内） | 41/41（136 条） |
| `sources[].name` | `string` | 是（项内） | 41/41（136 条） |
| `sources[].url` | `string` | 是（项内） | 41/41（136 条） |
| `sources[].publisher` | `string` | 否（项内） | 41/41（136 条） |
| `sources[].last_verified` | `string` | 是（项内） | 41/41（136 条） |
| `sources[].verified_by` | `string` | 否（项内） | 41/41（135 条） |
| `sources[].claim` | `string` | 否（项内） | 41/41（135 条） |
| `last_verified` | `string` | 是 | 41/41 |
| `verified_by` | `string` | 否 | 41/41 |

> 基线：`main@d89e19b`，2026-11-14（`data/programs` 与 `1c721f1` 相同）。数据变更后请同步更新本文件的计数与 §11。
