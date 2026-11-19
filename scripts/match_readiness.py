#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""画像匹配的数据就绪审计（M1）。

回答一个问题：**为了「填一次条件、算出每个项目能申/不能申/差什么」，
现有 data/programs/*.json 的字段够不够判？** 不够的，缺口在哪、能不能从
仓库里已有的 note / sources 文本可靠提取，还是只能标「不可判」。

六个维度（派单口径）：护照国籍资格 / 年龄上下限 / 学历 / 语言要求 /
预算费用 / 窗口类型与日期。前五个决定「能不能申」，最后一个只服务追踪清单。

每维给一个状态，取值刻意分成五档而不是「有/没有」——因为「有字段」和
「能判」不是一回事：

  ok       结构化字段在位，可直接比较
  partial  字段在位但语义不足以判决（如年龄上限 99 = 官方未公布）
  text     结构字段缺失，但 note / sources 里有明文，可可靠提取（附证据）
  absent   仓库里没有任何可判依据 —— 这一维只能标「不可判」，不许猜
  na       该项目这一维不设门槛（如不要求语言成绩），本来就不需要字段

判「na」和判「absent」的分界，是本审计最关键的一条判断：

  官方**根本没设可量化的门槛**（「不设分数线、由 Sponsor 面试评估」
  「资金证明无固定金额，自行证明」）→ na。它不构成「你差多少」的问题，
  只是递交时自证；用户填的值不会被这条卡住。
  官方**设了门槛但仓库没登记**（要求语言证明却不写分数线、要求资金
  证明却不给金额）→ absent。这时说「能申」是替官方担保，说「不能申」
  是替官方拒绝，两头都是编 —— 只能是「不可判」。

这条分界写在这里而不是散在探测器里，是因为它决定了停工的分子。

用法：
  python scripts/match_readiness.py             # 打印摘要 + 逐项目表
  python scripts/match_readiness.py --write      # 重写 docs/audit/ 下的审计文档
  python scripts/match_readiness.py --json       # 机器可读（CI / 测试用）
  python scripts/match_readiness.py --emit       # 重写前端用的 data/match-flags.json
                                                 # 与三样例快照 data/match-samples.json
  python scripts/match_readiness.py --check      # 校验上面两个产物与数据是否同步（CI 闸门）

为什么前端要读这里产出的 flags，而不是自己在 TypeScript 里再判一遍
「note 是不是写了未按国籍设限」「语言是不是官方不设分数线」：
那套判据（NOTE_OPEN_NATIONALITY / LANG_BY_DESIGN / FUNDS_NO_FIXED …）全文只
应该有一份。判据两份的后果是：某天有人放宽了正则，Python 审计说 41 条都能判，
网页仍按旧口径把五条标成「不可判」，而且没有任何测试会红。所以这里把「每条
项目在每一维处于什么状态」算好落盘，前端只做类型层面的比较（够不够、差多少）。

退出码恒为 0（除非 --check 发现漂移）：审计本身不是闸门，是否停工由人按报告里
的比例裁决。
"""

from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import sys
from collections import Counter, OrderedDict

# 与 build_calendar / gen_sources / track / sync_issue 保持一致：Windows 控制台
# 默认 cp936，--json 输出里的「«」等字符会抛 UnicodeEncodeError，于是 CLI 在
# Windows 上直接崩、在 Linux CI 上没事——同一份代码两种结果，最难查的一类。
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
# stderr 一起定编码：中文错误信息会变成非 UTF-8 字节，测试按 utf-8 读就崩在
# 解码而不是报错本身。
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRAMS = os.path.join(ROOT, "data", "programs")
DOC = os.path.join(ROOT, "docs", "audit", "2026-11-12-match-readiness.md")
FLAGS = os.path.join(ROOT, "data", "match-flags.json")
SAMPLES_OUT = os.path.join(ROOT, "data", "match-samples.json")

PASSPORTS = ("mainland_china", "hong_kong_china", "taiwan_china")
PASSPORT_ZH = {
    "mainland_china": "大陆护照",
    "hong_kong_china": "香港护照",
    "taiwan_china": "台湾护照",
}
# 护照 → 护照所属国家/地区代码（ISO 3166-1 alpha-2）。**只登记库里真有的三类**，
# 缺的一律不猜（P1e）：判 `home_residence`（须常驻护照所属地区）的唯一动作是
# 「现居 == 护照所属地」，两边都用同一套代码，比较就是字符串相等，不需要地名
# 归一表。表里没有的护照（将来新增、或画像写了个错值）返回 None → 判 silent，
# 而不是拿一个猜出来的国家去判 fail——那等于替官方拒绝一个可能合格的人。
PASSPORT_COUNTRY = {
    "mainland_china": "CN",
    "hong_kong_china": "HK",
    "taiwan_china": "TW",
}

# --------------------------------------------------------------------------
# 学历：从「单一总序」改成「路径谓词」（P3，2026-11-16）
#
# 病灶：过去这一维只有一条比较式 —— `EDU_RANK[have] < EDU_RANK[need]` → cannot。
# 一个单调刻度被拿来回答三个不同的问题，三个方向各错一次：
#
#   ① 「在读」是**状态**，不是层级。J-1 Intern / IAESTE / SWT 原文要求「现在
#      必须在读」，而 `bachelor_completed`(4) > `bachelor_in_progress`(3)，
#      于是**已毕业的人在判定上比在读的人更够格** —— 假 pass（batch9b §2 第 3 行）。
#   ② 「学位 **或** 经验」是**并列路径**，不是层级。J-1 Trainee 原文路径②
#      明文允许「无学历 + 5 年境外经验」，刻度里没有这个位子 —— 假 cannot，
#      全扫首个「把合格者判死」样本（batch10 §2 第 4 行）。
#   ③ 「学制 / 课程时长」是**时长**，不是层级。F-1 OPT 的「一整个学年」、
#      PGWP 的「8 个月」、NZ 的「30 周」在刻度里连字段都没有（batch9a §2 第 6 行）。
#
# 现在判定由三族谓词组成（见 `edu_paths()` / `edu_path_eval()`）：
#   在读状态 / 学位-或-经验组合 / 时长。
# `EDU_RANK` 这个总序**不再出现在判定路径上**，只剩 `EDU_LEVEL_ORDER` 给报告做
# 展示排序（回执附 grep 读点清单证明 judge() 不消费它）。
#
# 层级比较本身没有被取消 —— 它只是降级成**路径里的一个谓词**：`EDU_LEVEL_QUALIFIES`
# 用显式集合表达「持有 have 是否满足 need」，而不是拿两个数字比大小。集合写全
# 的好处是「vocation 不等于『比本科差』，它是另一类」这句话在代码里看得见。
# --------------------------------------------------------------------------

# 展示排序用的唯一一处（报告里把学历从低到高排）。判定不读它。
EDU_LEVEL_ORDER = (
    "high_school",
    "vocational",
    "bachelor_in_progress",
    "bachelor_completed",
    "master",
    "doctorate",
)

_DOCTORATE = frozenset({"doctorate"})
_MASTER_PLUS = frozenset({"master", "doctorate"})
_BACHELOR_PLUS = frozenset({"bachelor_completed", "master", "doctorate"})
_IN_PROGRESS_PLUS = frozenset(
    {"bachelor_in_progress", "bachelor_completed", "master", "doctorate"}
)
_VOCATIONAL_PLUS = frozenset(
    {"vocational", "bachelor_in_progress", "bachelor_completed", "master", "doctorate"}
)
_ANY_LEVEL = frozenset(EDU_LEVEL_ORDER)

# 「持有 have 是否满足 need」。显式集合，不是 `have >= need`。
EDU_LEVEL_QUALIFIES = {
    "any": _ANY_LEVEL,
    "high_school": _ANY_LEVEL,
    "vocational": _VOCATIONAL_PLUS,
    "bachelor_in_progress": _IN_PROGRESS_PLUS,
    "bachelor_completed": _BACHELOR_PLUS,
    "master": _MASTER_PLUS,
    "doctorate": _DOCTORATE,
}


def edu_level_rank(level: str | None) -> int | None:
    """展示用的层级序号；`any` 与未知值返回 None。

    **不是判定**：判定读 `EDU_LEVEL_QUALIFIES`（显式集合）。这里只给报告排序、
    以及「结构化字段是否真的写了一个层级」这类扫描用 —— 拿它比大小就是把本单
    拆掉的错因装回去。
    """
    try:
        return EDU_LEVEL_ORDER.index(level or "")
    except ValueError:
        return None


def edu_level_ok(need: str | None, have: str | None) -> bool:
    """层级路径：持有 `have` 是否满足 `need`。

    未知取值（None / 拼错 / 老数据里的 `phd`）一律 False —— 不认识的值不构成
    达标证据。调用方在 `need` 缺失时自己决定要不要走这条路径。
    """
    allowed = EDU_LEVEL_QUALIFIES.get(need or "any")
    if allowed is None:
        return False
    return (have or "") in allowed


# 数据里「官方未公布年龄」的统一写法：note 以 ⚠️ 开头（sync-data.mjs 与
# validate.py 也认这一个判据，三处不能各写一套）。
UNVERIFIED_PREFIX = re.compile(r"^\s*⚠️")

# 「官方未按国籍设限」的明文。命中它 = 该护照没有单独登记，但 note 本身
# 就是资格结论，可据此判，不属「不可判」。这是全仓唯一判据，写宽了会误放行，
# 所以只收这几种官方原文的中文转写。
NOTE_OPEN_NATIONALITY = re.compile(
    r"未按国籍设限|不按国籍设限|不设国籍限制|所有国籍|面向所有国籍|第三国国民"
)

# 语言：官方明确「不设分数线、由 Sponsor/雇主面试评定」，或语言只计分不定资格。
# 命中它时该维是 na（不因分数卡人），不是缺字段。
LANG_BY_DESIGN = re.compile(
    r"未设分数线|不设分数线|不设等级门槛|未指定统一考试|未设雅思/托福分数线|"
    r"不列任何考试|由 Sponsor 面试评估|Sponsor 组织的面试|面试评估|雇主.*把关|"
    r"语言只影响分数|不影响资格"
)

# 语言：官方用 CLB / NCLC / CEFR 档位表述，仓内有档位、但要把雅思分数按
# 公开对照表折算。判为 text：可可靠换算，但用户在界面上看到的是换算值。
LANG_CEFR_LADDER = re.compile(r"CEFR|CLB|NCLC")

# 语言：数据里用「一条 test=none、min_score=0」表示「官方不要求任何标准化考试」。
#
# 目前只有 us-j1-summer-work-travel 这么写：`required: true`（它确实要求英语沟通
# 能力）+ `tests: [{test: "none", min_score: 0}]` + note「无需雅思/托福成绩，
# 但必须具备足以在英语工作环境中沟通的能力。须通过项目方英语测试及美方雇主面试」。
#
# 不认这个哨兵时，tests 里筛不出 IELTS 条目、note 也命中不了 LANG_BY_DESIGN
# （那条正则收的是「未设分数线 / 面试评估」等措辞，这条原文是「无需雅思/托福成绩」），
# 于是落到 lang_no_score：一个写明「无需雅思托福」的项目被判「语言维度不可判」，
# 用户会以为自己在语言上还有未知缺口。
#
# 判 na 而不是 pass：官方确实要求英语沟通能力，只是不用标准化考试证明，
# 因此这一维不构成「够不够」的可比门槛 —— 与 funds_by_design 同一处理逻辑。
LANG_NO_STANDARD_TEST = re.compile(r"无需雅思|无需托福|不需要雅思|不要求雅思|无需提供雅思")

# 资金：官方明文「不设固定金额 / 未写死金额」，金额由外管局或按指标计算。
# 收的写法都很具体，因为一旦放宽就会把「要求 3 万但没登记」这种真缺口
# 误判成「不设门槛」——那正好是最该暴露给用户的一类缺失。
FUNDS_NO_FIXED = re.compile(
    r"未写死金额|未设固定金额|不设固定金额|未在法规中写死|未给出固定数字|"
    r"不填猜测值|未列资金门槛|未设固定金额门槛|按当期.*指标计算|"
    r"没有全国统一数额|未给数额|未设统一金额|不设固定金额门槛|"
    r"官方不设固定金额门槛|法规未设统一金额"
)

# 资金的口径：金额是「年收入」还是「存款/资金证明」。
#
# 这两者不能拿同一个预算数字去比：马耳他数字游民要求的是年毛收入 ≥ €42,000，
# 而用户填的是「可动用的资金证明」。拿 5 万人民币存款去比 33 万的年收入门槛，
# 会判出「差 28 万」——数字算得出来，但结论是错的：一个有远程工作的人年收入
# 达标、存款不足，他其实符合；反过来存款多但无收入的人不符合。
# 判据只能落在金额的 note 上（数据里没有独立字段），所以放这里与其它口径同处。
FUNDS_INCOME = re.compile(r"年收入|年毛收入|年度收入|gross yearly income|annual income|月收入")

# 资金：金额是按「每月」计的，不是一次性总额。
#
# 这一条是本轮验收修正（2026-11-13 §4-1）补的。`de-16e-internship` 写「每月至少
# 752 欧元」、`cny_estimate` 记的是单月 5,900；判定却拿画像的 3 万可动用资金直接
# 比这个 5,900，判「够」。真相是「资金须覆盖整个实习期」（最长 6 个月），6×5,900
# 才是要证明的总额。拿月额当总额比，方向永远是「偏松」——这正是本产品最危险的
# 假「能申」。
#
# 处理：能从 timeline/work_conditions 拿到期限上限的，按月数折算成总额再比；
# 拿不到期限的，判 silent（不可判）并写明「不知道要覆盖几个月」。
FUNDS_MONTHLY = re.compile(
    r"每月|每个月|/月|月均|按月|per month|/month|monthly|per-month", re.IGNORECASE
)

# 资金：金额本身是「按学生口径沿用 / 归类推定」，不是这条许可的独立规定。
#
# `is-job-search-after-graduation` 原文：「官方未在本续签的专门说明里单独列出该
# 数字，因此本字段标注为『按学生口径沿用』，不是本许可的独立规定」。这类数字可以
# 用来算「大概差多少」，但不能当成官方门槛判「你够/不够」——那是替移民局担保一个
# 它没为本项目写过的金额。命中时判不可判，写明数字来源存疑。
# 注意只收「该数字本身是推定」的措辞；「人民币估算仅供参考」是汇率免责声明，
# 不是金额存疑，单独放在 EXCHANGE_DISCLAIMER 里排除。
FUNDS_INFERRED = re.compile(
    r"归类推定|属推定值|是推定值|并非本许可的独立规定|不是本许可的独立规定|按.{0,12}口径沿用"
)
EXCHANGE_DISCLAIMER = re.compile(r"人民币估算.{0,20}仅供参考|汇率.{0,12}仅供参考")

# 学历：note 里另写的「完成不少于 N 年高等教育」，且明说不足 N 年不满足。
#
# 只有**严格**写法才算额外门槛：若 note 把「N 年」写成与学位并列的备选条件
# （如澳洲 462「①高等教育学历；②已完成至少 2 年本科」），那不是额外要求，
# 硬套会把一个已经毕业的人误判成「差年数」。所以要求同一段 note 里同时出现
# 「不满足 / 不达 / 不符合」，才认为年限是硬门槛。
EDU_YEARS_STRICT = re.compile(
    r"(?:不少于|至少|不低于)\s*([一二三四五六七八九十两\d]+)\s*个?\s*(?:学年|年)"
)
EDU_YEARS_DISQUALIFY = re.compile(r"不满足|不达|不符合")

# 学历：note 里另写的**就读时长**下限（「至少一整个学年」「不少于 8 个月」
# 「至少 30 周」「至少 1 个学期」）。与 EDU_YEARS_STRICT 分开，理由有两条：
#
#   ① 单位不同：EDU_YEARS_STRICT 只认「年 / 学年」，把「8 个月」「30 周」
#      「1 个学期」整类漏掉（batch6 §2 第 4 行、batch9b §2 第 4 行记过四次）；
#   ② 语义不同：「读了几年」是学制，判的是学历层级够不够；「读了多久」是
#      这道项目的准入门槛，判的是你在这段学历里实际待了多长。两者可以同时
#      存在（澳洲 485：2 学年 + 16 个月），把两件事压进一个正则就会互相覆盖。
#
# 与 EDU_YEARS_STRICT 共用 `EDU_YEARS_DISQUALIFY` 成对闸：并列路径里的
# 「至少 2 年」（au-462 的路径②）不算额外门槛，只有原文另说「不足即不满足」
# 时才算。这一条是旧代码注释里已经定下的规则，本单不放松。
EDU_DURATION_IN_NOTE = re.compile(
    r"(?:不少于|至少|不低于|不低于)\s*([一二三四五六七八九十两\d]+)\s*个?\s*(学年|年|个月|周|学期)"
)

# 学历：note 另写的「须在申请日/递交日之前 N 年内完成学业或取得学位」这类
# **毕业时限**（P2-0 nl-orientation-year）。
#
# 这与上面 EDU_YEARS_STRICT 是两件不同的事：那条说的是「读了几年」，这条说的是
# 「什么时候毕业」。结构化 education 里只有层级与学制年数，没有任何字段能表达
# 「毕业日在申请日往前 N 年之内」——补一个 `graduation_within_years` 字段也只是
# 把 note 的话抄一遍，画像不采集毕业年份，一样判不了。所以按站规降到不可判，
# 而不是判达标。
#
# 锚点必须是「申请日 / 递交日」而不是笼统的「申请前」，末尾必须落到「完成学业 /
# 完成研究 / 从事过科研 / 取得学位」这类**毕业或科研结束时点**。两条限制都是为了
# 不误伤同库里另两种「N 年内」写法：
#   de-16e-internship「②在申请前 2 年内已取得学历」——①在读 / ②毕业两条是**或**
#     的关系，不是硬门槛，按硬门槛判会把在读的人误降级；
#   uk-hpi-visa「学位须在申请前 5 年内授予」——已由 EDU_PLACE（edu_place_unknown）
#     覆盖，这里再命中一次就是同一个缺口报两遍。
EDU_RECENCY = re.compile(
    r"(?:申请日|递交(?:申请)?之?日)(?:之?前|起)?[^。；\n]{0,10}?"
    r"([一二三四五六七八九十两\d]+)\s*年(?:内|以内)"
    r"[^。；\n]{0,30}?(?:完成学业|完成研究|从事过科研|取得[^。；\n]{0,40}?(?:学位|硕士))"
)

# 学历：学位必须在**指定国家/指定名单内院校**完成。结构化字段只有层级，没有
# 「在哪读的」「读了多少个月」，因此这一维在画像缺院校信息时只能判不可判。
EDU_PLACE = re.compile(
    r"须在[^，。；]{0,30}(?:完成|取得|读满|修读)[^，。；]{0,20}(?:课程|学历|学位|学业|文凭|项目)|"
    r"须由[^，。；]{0,24}(?:授予|出具|认证)|"
    r"认可名单|指定学习机构|PGWP ?合格|CRICOS|合格.{0,6}院校|"
    r"授予机构须为|须为.{0,12}大学"
)

# 学历：结构化字段比 note 更严（note 明说「法规未规定具体学位层级 / 由 Sponsor
# 判断」）。这类冲突以 note 为准：结构化字段不能拿来判「学历不够」。
EDU_BY_SPONSOR = re.compile(
    r"未规定具体学位层级|未设具体学位层级|未规定学位层级|不设具体学位层级|"
    r"由\s*Sponsor\s*判断|由赞助方判断"
)

# 前置身份 / 在地要求：这类项目只对「已经在该国持学生/居留身份（并在当地完成
# 学业）」的人开放，或要求「递交时人就在该国境内」，不是一张面向所有人开放的表。
# §4-3 / §4-4 的全部偏差都来自这一条从未进入判定。
#
# 2026-11-15（P1c，批次 9a 裁决 1 + P1a 待核 C）：**身份与在地拆成两个独立类别**。
# 过去二者共用一个 `local_status` 出口，靠 `PRE_LOCAL_STATUS` 末支的
# 「(必须|须)在…境内」兜底把在地要求吞成身份要求。那条兜底有两个错：
#   ① 方向错：把「你必须人在英国才能递交」说成「你差一段留学经历」——前者是
#      时点/在地门槛，后者是可补的经历，两类不同；
#   ② 吞并错：us-f1-opt 同时有身份条与在地条，兜底让在地那条借身份条的 code
#      发声，看起来「已判」，实际那条要求没有任何读点（batch9a 裁决 2「借接的
#      code 不算兜住」）。
# 现在：身份归 `residency_requirement`（type）+ 身份支；在地归
# `location_requirement`（type）+ 在地支。两者各自独立可读、互不吞并。
#
# 类别与处置：
#   local_status   须先在该国持学生签/居留（或在当地完成学业）→ gap（差这一项前提）
#   inside         递交时人须在该国境内 → 画像不采集现居地，silent
#   outside        递交时人须在该国境外 → 画像不采集现居地，silent
#   home_residence 须常驻护照所属地区 → 画像不采集现居地，silent
PRE_LOCAL_STATUS = re.compile(
    # 锚点扩到「（须|且）持」「（须|且）已持」两式（批次 9a 裁决 1 原文）。
    # 原锚点只有「须已持 / 须持」，读不到「…且该身份在递交当日仍未失效」这类
    # 用「且」起头的并列写法；us-f1-opt 的身份条正是这种写法，而它恰恰是本单
    # 拆出的两条里必须先保住的那一条。
    r"(?:须|且)已持|"
    r"(?:须|且)持[^。；]{0,30}(?:学习居留|学生居留|学生许可|学生签证|Stamp\s*2|F-1|居留许可)|"
    # 「人在法国——须持 carte de séjour étudiant」这类两路径写法：原文是外语
    # 证件名，中文正则抓不到，会整条落空。§4-3 要的是「读得到」，不是「读得准
    # 一处」，所以把常见的外语学生证件名也收进来。
    r"(?:必须|须)持[^。；]{0,20}(?:carte de séjour|séjour étudiant|student pass|study permit|"
    r"residence permit|居留许可|长期学习居留)|"
    r"曾持[^。；]{0,24}(?:居留|许可|签证)|"
    r"在此身份下完成学业|并在此身份下"
)
# 在地：递交时人须在该国境内。**独立类别，不是 local_status 的末支**。
# 与 PRE_OUTSIDE 互为镜像——两个方向相反的条件必须各占一个 code，否则「境外
# 递交」与「境内递交」在报告里长得一模一样（batch8 的立项理由）。
PRE_INSIDE = re.compile(r"(?:必须|须)在[^。；]{0,6}(?:境内|国内)|人在[^。；]{0,6}(?:境内|国内)")
PRE_OUTSIDE = re.compile(r"(?:必须|须)在[^。；]{0,10}境外|人在[^。；]{0,8}境外")
PRE_HOME_RESIDENCE = re.compile(r"居住于其国籍国|须居住且常驻|常驻其护照|常驻中国|居住且常驻")

# 其余两类 required: true 的前置要求 —— 都不构成「身份前置」：
#   citizenship  原文说的是「须为参与国公民」。那是护照条件，passport 维已经在判，
#                这里再报一条就是同一个缺口说两遍。
#   document     原文说的是「须持有效租约 / 购房合同」。这是递交时自行取得的文件，
#                不是「你得先在该国读过书」，不构成可判的身份门槛。
# 分开登记（而不是笼统落 None）是为了让「全库顺查」的结果里，每一条 required
# 的前置要求都能指到处置理由，而不是一片无法区分的空白。
PRE_CITIZENSHIP = re.compile(r"参与国公民|协议国公民|须为[^。；]{0,12}国民")
PRE_DOCUMENT = re.compile(r"租房或购房合同|租赁合同|租房合同|购房合同|租约")

# 两族 type：身份族与在地族。`precondition_kind()` 对二者**显式双映射**，
# 不再靠「凡是 required 的前置条都进同一条优先级链」——那正是把在地读成身份
# 的结构性原因。
REQ_TYPE_RESIDENCY = "residency_requirement"
REQ_TYPE_LOCATION = "location_requirement"
REQ_TYPES_PRECONDITION = (REQ_TYPE_RESIDENCY, REQ_TYPE_LOCATION)

# 岗位前置：原文要求「必须先落实岗位/录取，Sponsor 才能办后续」的项目
# （P2-0 us-j1-camp-counselor 的「须落实营地岗位」）。
#
# 这与 residency_requirement 不是一回事：那条说的是「你人在哪 / 你持什么身份」，
# 这条说的是「你得先拿到一个具体岗位」。J-1 营地辅导员法规原文是 `Under no
# circumstance facilitate the entry into the United States of a participant for
# whom a camp placement has not been pre-arranged`——不存在「先入境再找营地」，
# 所以画像填了学历年龄语言也说明不了这一条成立。
#
# 读 documents（条款落在哪一张材料上）与 other_requirements.internship_contract
# 两处：us-j1-camp-counselor 把它写成 documents 里的一条「预先落实的营地岗位」，
# us-j1-intern / us-j1-trainee 写成 internship_contract（DS-7002）。两类都判
# gap 而非 silent——「你还没落实岗位」是能补的一步（去报名、面试、拿 placement），
# 与「数据里没写这一条」不同。
#
# P4 Sponsor 包（2026-11-17）扩围：原词表只认营地辅导员那一句英文直译
# （`pre-arranged` / 「预先落实」），对同一件事的另外三种官方写法全 MISS，
# 而注释早就写着「us-j1-intern / us-j1-trainee 两类都判 gap」——注释即承诺、
# 实测零输出（batch9a §2.2①、batch10 §1.2①）。补的四族写法都是**同一条法规
# 事实的不同表述**，不是新增语义：
#   ① 「落实/安排/安置 + 岗位」（SWT 的「须先由 Sponsor 落实暑期岗位」、
#      intern 的「落实实习岗位」）；
#   ② 「全部签字 / 三方签字」（DS-7002 三方签署即 placement 已落实的证据形态）；
#   ③ 「签署 / 出具 DS-7002」；
#   ④ 「通过 / 参加雇主面试」（SWT 拿 Job Offer 的唯一路径）；
#   ⑤ 「出具 / 签发 DS-2019」（Sponsor 只对已落实 placement 者签发）；
#   ⑥ 「拿到接收机构的邀请与 Sponsorship」（研究学者的 Sponsor 入口）。
# 只扩词表、不改判定语义：依旧是「必填材料命中即 gap」，依旧不判 silent。
JOB_PLACEMENT = re.compile(
    r"预先落实|事先落实|pre-arranged|prearranged|"
    r"岗位必须(?:预先)?落实|未落实(?:营地)?岗位|尚未落实|"
    r"(?:落实|安排|安置)[^。；\n]{0,10}岗位|"
    r"(?:全部|三方)[^。；\n]{0,4}签字|"
    r"(?:签|出)署[^。；\n]{0,12}DS-?7002|"
    r"(?:通过|参加|接受)[^。；\n]{0,12}雇主[^。；\n]{0,6}面试|"
    r"(?:出具|签发)[^。；\n]{0,8}DS-?2019|"
    r"(?:拿到|获得|取得)[^。；\n]{0,16}(?:邀请|Sponsorship)"
)

# government_support_letter 这个 type 名不表示同一种东西（P4 §2 盘点，39 条漏网
# 行逐条核过）：五个 required=true 的成员分别是政府支持信 / 官方求职登记 /
# 学历认证 / 院校推荐 / Sponsor 出具的 DS-2019。按 type 名一刀切接线会把四种
# 无关语义读成同一条缺口——那正是 P1a 得出的结论（「按名字接线会判错」）。
#
# 所以接成**语义分型**的 typed 读点：type 只用来定位条目，判定看 note 落在
# 哪一型。只有 sponsorship 型（Sponsor / DS-2019 / 接收机构邀请）是 P4 的
# 「岗位前置」，其余四型各有归属（见各分支注释），本单不接线但必须读出类型、
# 不许留在枚举里当摆设。
REQ_TYPE_GSL = "government_support_letter"

GSL_KINDS = (
    # ① Sponsor 出具的 DS-2019：个人无法自行申请，须先被接收机构选中。
    #    这是 J-1 体系唯一入口，缺它就是「没有入口」，判 gap（P4 本单接线）。
    ("sponsorship", re.compile(
        r"Sponsorship|接收机构[^。；\n]{0,10}邀请|"
        r"Sponsor[^。；\n]{0,14}(?:出具|签发)[^。；\n]{0,8}DS-?2019"
    )),
    # ② 官方求职登记（it-ricerca 的 DID）：属「在地办事手续」，与 P1 在地族同源。
    #    锚点必须带「就业中心 / DID / Centro」——裸词「登记」会把任何提到「材料登记」
    #    的 note 误分到这一型（分型错会让审计把一条别族的要求记到本族名下）。
    ("official_registration", re.compile(
        r"DID|Centro per l'?Impiego|就业中心[^。；\n]{0,12}(?:登记|声明)"
    )),
    # ③ 学历认证（uk-hpi 的 Ecctis）：属教育族，已由 EDU_PLACE 覆盖。
    #    裸词「认证」会把「学历须经认证翻译」这类材料要求拉进来，故只用专名。
    ("credential_check", re.compile(r"Ecctis|anabin|学历认证|资格认定")),
    # ④ 院校推荐（us-f1-opt 的 DSO / I-20）：属学籍族，与 enrollment 同源。
    ("institutional_recommendation", re.compile(r"DSO\b|I-20")),
    # ⑤ 政府支持信（au-462 的 CICETE）：属国籍/双边安排族。
    ("government_letter", re.compile(r"CICETE|政府支持信|支持信")),
)


def government_support_letter_kind(doc: dict) -> tuple[str, bool] | None:
    """读出 `government_support_letter` 条目的语义分型与是否必填。

    返回 (kind, required)；没有该 type 的条目时返回 None。kind 取 GSL_KINDS
    里第一个命中的；一个都不命中返回 "unclassified"（诚实留痕，不猜）。
    """
    for r in (doc.get("eligibility") or {}).get("other_requirements") or []:
        if r.get("type") != REQ_TYPE_GSL:
            continue
        note = r.get("note") or ""
        for name, rx in GSL_KINDS:
            if rx.search(note):
                return name, r.get("required") is True
        return "unclassified", r.get("required") is True
    return None


def _gsl_flag(doc: dict) -> dict | None:
    """`flags_of()` 用的形状：`{"kind": ..., "required": ...}` 或 None。

    单列一个小函数而不是在 flags 里内联：`government_support_letter_kind()`
    每次调用都要扫一遍 other_requirements，内联写法会调两次（条件 + 构造），
    既慢又容易在「两次调用之间状态不同」时写出自相矛盾的产物。
    """
    got = government_support_letter_kind(doc)
    if not got:
        return None
    kind, required = got
    return {"kind": kind, "required": required}


# 四种表述（P4 §3）：同一条 code `pre_job_placement`，但 need 文案必须按项目取。
# Muse 2026-11-14 裁决 2（batch9b §4 + batch10 §4 采纳）把文案表定为四种，
# 理由是 four 个 J-1 子类的「落实」链条根本不同：营地是「先有营地岗位才准入境」，
# 研究学者是「先有接收机构与 DS-2019」，SWT 是「Sponsor 落实暑期岗位 + 雇主面试」，
# intern/trainee 是「DS-7002 三方签字文件链」。用营地文案去讲研究学者，等于
# 修了一处漏网、引入一处错文案。
JOB_PLACEMENT_FLAVORS = (
    ("camp", re.compile(r"营地[^。；\n]{0,10}岗位|pre-arranged camp|营地\s*placement")),
    ("ds7002", re.compile(r"DS-?7002|三方签字|全部签字")),
    ("summer_job", re.compile(r"暑期岗位|雇主[^。；\n]{0,6}面试|Job Offer")),
    ("sponsor_ds2019", re.compile(
        r"Sponsorship|接收机构[^。；\n]{0,10}邀请|"
        r"Sponsor[^。；\n]{0,14}(?:出具|签发)[^。；\n]{0,8}DS-?2019"
    )),
)

JOB_PLACEMENT_NEED = {
    "camp": "预先落实的营地岗位（Sponsor 不得为未落实营地岗位者办理入境）",
    "sponsor_ds2019": (
        "国务院指定 Sponsor 出具的 DS-2019（须先拿到接收机构的邀请与 Sponsorship，"
        "个人无法自行申请）"
    ),
    "summer_job": (
        "Sponsor 已落实并审查过的暑期岗位 + 通过美方雇主面试拿到的 Job Offer"
        "（美国国务院授权 Sponsor 统一办理，无法自主申请）"
    ),
    "ds7002": (
        "雇主签署的 DS-7002 培训/实习安置计划（申请人、雇主、Sponsor 三方签字后，"
        "Sponsor 才签发 DS-2019）"
    ),
}

# 一个都没命中时的兜底：沿用营地那条（最严的一份法规原文），
# 但 flavor 会返回 None，flags 里留痕，测试钉住「当前全库无 None」。
JOB_PLACEMENT_NEED_FALLBACK = JOB_PLACEMENT_NEED["camp"]


def _job_placement_texts(doc: dict) -> list[str]:
    """岗位前置的判读面：必填 documents + 必填 internship_contract +
    sponsorship 型的必填 government_support_letter。

    `government_support_letter` 只有 sponsorship 型进这一族（P4 §2）：其余四型
    是政府支持信 / 求职登记 / 学历认证 / 院校推荐，接进来会造出假缺口。
    """
    texts = []
    for d in doc.get("documents") or []:
        if d.get("required") is True:
            texts.append((d.get("name") or "") + " " + (d.get("note") or ""))
    for r in (doc.get("eligibility") or {}).get("other_requirements") or []:
        if r.get("required") is not True:
            continue
        if r.get("type") == "internship_contract":
            texts.append(r.get("note") or "")
        elif r.get("type") == REQ_TYPE_GSL:
            kind, required = government_support_letter_kind(doc) or (None, False)
            if required and kind == "sponsorship":
                texts.append(r.get("note") or "")
    return texts


def job_placement_required(doc: dict) -> bool:
    """原文是否把「岗位须预先落实」写成硬性前提。

    只看必填项：documents 里 required 为真的条目、other_requirements 里
    required 为真的 internship_contract，以及 sponsorship 型的
    government_support_letter。可选材料里出现同样措辞不算门槛。
    """
    return any(JOB_PLACEMENT.search(t) for t in _job_placement_texts(doc))


def job_placement_flavor(doc: dict) -> str | None:
    """这条岗位前置属于四种表述里的哪一种（P4 §3）；一个都不命中返回 None。

    顺序即优先级：camp 最具体（营地专属词），ds7002 次之（文件链），
    再是 summer_job（雇主面试），最后 sponsor_ds2019（研究机构的 DS-2019）。
    """
    texts = _job_placement_texts(doc)
    for name, rx in JOB_PLACEMENT_FLAVORS:
        if any(rx.search(t) for t in texts):
            return name
    return None


# 参与人身份类别：原文把资格写成「须属于某几类身份之一」，而结构化 education 只有
# 学历层级（P2-0 us-j1-camp-counselor 的四类身份）。
#
# 画像采集的是「学历层级」，不是「你现在是在读学生 / 在职青年 / 教师 / 有专门技能」。
# 一个本科毕业的在职者可能是 youth worker，也可能哪种都不算——这一维判不了。
# 且原文自己写明「由 Sponsor 判断是否成立」，各机构口径可能不同。
PARTICIPANT_CATEGORY = re.compile(
    r"四类|bona fide youth workers|"
    # 「身份须属于…类」：锚点必须落在「身份」，否则会把 au-407 的「培训项目须属于
    # 三类之一」误认成参与人身份门槛——那三类是培训类型，不是申请人身份。
    r"身份[^。；]{0,12}(?:属于|为)[^。；]{0,10}类|"
    r"youth workers?[，,、].{0,20}students?[，,、].{0,20}teachers?"
)


def participant_category_required(doc: dict) -> bool:
    """原文是否要求参与人先属于某个身份类别（而不是只看学历层级）。"""
    edu = (doc.get("eligibility") or {}).get("education") or {}
    return bool(PARTICIPANT_CATEGORY.search(edu.get("note") or ""))


# 学历/职业资格须经**主管机构认定**（P2-0 de-chancenkarte）。
#
# 德国机会卡原文（eligibility.passport_types.note）：「两条硬门槛：①学历或职业
# 资格被德国主管机构认定（学历一般通过 anabin 数据库核验）；②满足「专业人士」
# 条件或积分达到 6 分。」结构化 education 只有一个 `bachelor_completed`，含义是
# 「你的最高学历层级是本科」，与「你这份学历被德国 ZAB/anabin 认定为等效」是两件
# 事——后者要跑一次学历认定，结论可以是「不等效」。画像也不采集认定结果。
#
# 于是「层级到了 = 达标」在这里是最典型的静默判过：一个学历不被 anabin 承认的
# 人，在画像里与一个被承认的人长得一模一样。
CREDENTIAL_RECOGNITION = re.compile(
    r"(?:学历|职业资格|资格)[^。；\n]{0,16}被[^。；\n]{0,12}主管机构[^。；\n]{0,6}(?:认定|认可)"
)

# 积分门槛的分数。只被上面的认定分支引用（见 judge()）：单看「有积分制」不足以
# 降级——奥地利红白红卡也写「积分达到 70 分」，但它的资格认定口径不同，属本腿
# 范围外，硬接进来会把一条无关项目一起改判。
#
# 数字前的通配必须排除数字本身（`\d`），否则「积分达到 70 分」会被吃成 7 + 0，
# 取出 0 分——一个真门槛被读成「0 分就够」。
POINTS_THRESHOLD = re.compile(
    r"积分[^。；\n]{0,10}(?:达到|须达|至少|最低)[^。；\n\d]{0,6}(\d+)\s*分"
)


def _recognition_texts(doc: dict) -> list[str]:
    """读认定要求的三处：education.note、passport_types.note、必填材料。

    只读 required 为真的材料：可选材料里出现同样措辞不构成硬门槛。
    """
    el = doc.get("eligibility") or {}
    texts = [
        ((el.get("education") or {}).get("note") or ""),
        ((el.get("passport_types") or {}).get("note") or ""),
    ]
    for d in doc.get("documents") or []:
        if d.get("required") is not True:
            continue
        texts.append((d.get("name") or "") + " " + (d.get("note") or ""))
    return texts


def credential_recognition_required(doc: dict) -> bool:
    """原文是否把「资格须经主管机构认定」写成硬门槛。"""
    return any(CREDENTIAL_RECOGNITION.search(t) for t in _recognition_texts(doc))


def points_threshold(doc: dict) -> int | None:
    """同一批文本里若写了积分门槛，取出分数；读不到返回 None。

    返回 N 只说明「原文有这个分数」，不代表画像能算分——积分项里有一半（语言
    等级、经验年限、紧缺职业、在德居留史）画像都没采集。
    """
    for text in _recognition_texts(doc):
        m = POINTS_THRESHOLD.search(text)
        if m:
            return int(m.group(1))
    return None


# 岗位前置（第二类）：原文要求「先有一份具体雇主给的、工时与资格都够格的聘用」
# （P2-0 no-skilled-worker）。
#
# 与上面的 JOB_PLACEMENT 分开：那条是「Sponsor 不得为未落实岗位者办入境」的
# 项目制前置（营地 placement），这条是雇主担保类项目的通用门槛——没有 offer
# 连申请表都填不了。三条要求（具体雇主 / ≥80% 岗位 / 岗位与资格对应）写在
# 三处不同的原文里（other_requirements.internship_contract、documents、
# education.note），但它们是同一件东西的三个属性：一份合格聘用。所以合成一个
# 探测器、一个 code，不拆成三条重复缺口。
EMPLOYER_OFFER = re.compile(
    r"具体雇主的具体聘用|concrete job offer from one specific employer|one specific employer|"
    r"(?:至少|不低于)\s*80\s*%|80\s*%\s*(?:的)?(?:岗位|工时|position)"
)


def employer_offer_required(doc: dict) -> bool:
    """原文是否把「具体雇主的合格聘用」写成硬性前提（必须有一份 offer）。

    读必填材料 + 必填的 internship_contract + education.note 三处：no-skilled-worker
    把「具体聘用」写成 other_requirements、把「≥80%」写成 documents 的一条、
    把「岗位须与学历对应」写成 education.note 的末句。
    """
    el = doc.get("eligibility") or {}
    for d in doc.get("documents") or []:
        if d.get("required") is not True:
            continue
        if EMPLOYER_OFFER.search((d.get("name") or "") + " " + (d.get("note") or "")):
            return True
    for r in el.get("other_requirements") or []:
        if r.get("required") is not True:
            continue
        if EMPLOYER_OFFER.search(r.get("note") or ""):
            return True
    return bool(EMPLOYER_OFFER.search((el.get("education") or {}).get("note") or ""))


CN_NUM = {
    "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}


def cn_int(text: str) -> int | None:
    """把「四」「六」「十二」这类中文数字转成 int；已是阿拉伯数字就直取。"""
    text = (text or "").strip()
    if text.isdigit():
        return int(text)
    if text in CN_NUM:
        return CN_NUM[text]
    if text.startswith("十") and len(text) == 2 and text[1] in CN_NUM:
        return 10 + CN_NUM[text[1]]
    if text.endswith("十") and len(text) == 2 and text[0] in CN_NUM:
        return CN_NUM[text[0]] * 10
    if len(text) == 3 and text[1] == "十" and text[0] in CN_NUM and text[2] in CN_NUM:
        return CN_NUM[text[0]] * 10 + CN_NUM[text[2]]
    return None


def edu_years_required(doc: dict) -> int | None:
    """note 里另写的硬性年限门槛（结构化 `years_completed` 缺失时用）。

    **P3 去掉了 `years >= 3` 的硬下限。** 那条下限的原始动机是防「三年制本科」
    这类写法被误读成门槛，但防线已经有两条更准的：
      ① 同段必须出现「不满足 / 不达 / 不符合」（`EDU_YEARS_DISQUALIFY`）；
      ② 年限在判定里不再是独立门槛，而是**路径的时长谓词**（见 `edu_paths()`）——
         路径成立与否由「你有没有 2 年」回答，不是由「门槛数字够不够大」回答。

    下限的真实代价是 documented 的：batch9b §2 第 4 行「至少 1 个学期」（1 学期
    < 1 年）、au-462「至少 2 年」、de-16e「2 年」全被吞成 None → 判 edu_ok 放行。
    去掉后这些项目不再默认 pass，而是走时长谓词判 pass/fail，或数据缺失时落
    `edu_duration_unknown`（silent）。翻档造成的乙类上升属如实暴露，不回滚。
    """
    edu = (doc.get("eligibility") or {}).get("education") or {}
    note = edu.get("note") or ""
    m = EDU_YEARS_STRICT.search(note)
    if not m or not EDU_YEARS_DISQUALIFY.search(note):
        return None
    years = cn_int(m.group(1))
    if years and years >= 1:
        return years
    return None


def edu_recency_years(doc: dict) -> int | None:
    """note 里另写的「须在申请日前 N 年内完成学业/取得学位」的毕业时限。

    读的是 `education.note` 与 `age.note` 两处：nl-orientation-year 把这条时限
    写在 education.note（七类路径里两处「申请日前 3 年内」），同时在 age.note 里
    复述了一遍——它被塞进年龄维是因为结构上没有别的字段可放，不代表它属于年龄。
    两处都读，是为了不明显依赖某一条 note 的措辞位置。

    只读、不推断：拿不到 N 或读不懂就返回 None，由调用方决定是否降级。返回 N
    只说明「原文有这么一条时限」，不代表画像能判它。
    """
    edu = (doc.get("eligibility") or {}).get("education") or {}
    age = (doc.get("eligibility") or {}).get("age") or {}
    for note in (edu.get("note") or "", age.get("note") or ""):
        m = EDU_RECENCY.search(note)
        if m:
            years = cn_int(m.group(1))
            if years and years >= 1:
                return years
    return None


# —— 教育路径谓词（P3 的核心）——
#
# 一条项目的教育要求被读成**一组并列路径**：任一路径成立 → 达标；全部不成立
# → 不达标；某条路径缺数据判不了 → 不可判。这与旧代码的差别不是「更宽松」，
# 是「能表达 or」：旧代码只有单刻度，`or` 一律被压成 and 的补集。

# 路径规格里允许出现的键。schema 侧有同名的 `paths` 数组，两处词表须一致。
EDU_PATH_KEYS = frozenset(
    {
        "level",              # 该路径要求的最低学历层级（None = 不限）
        "min_years_experience",  # 该路径要求的相关工作经验年限（None = 不要求）
        "experience_region",  # 经验须在何处取得：outside（境外）/ any
        "enrollment",         # 该路径要求的在读状态：enrolled / graduated
        "graduated_within_months",  # 毕业后多少个月内仍算符合（None = 无此限）
        "min_months",         # 课程/就读时长下限（月，已折算好的原值）
        "min_duration",       # 同上但保留官方单位 {value, unit}，由引擎折算
        "experience_label",   # 报告里的可读标签（可选）
        "note",               # 该路径的官方依据摘录（可选，仅供人读）
    }
)

# 一学期按 5 个月计。**这是本仓的显式换算假设，不是官方数字。**
# 依据：一学年 = 2 学期，而美国国务院/SEVP 对学年与学期未给统一月数；
# 10 个月/学年的口径与「一学年 = 9–10 个月」的通行学制一致。
# 之所以不在数据里写「5」，是因为官方原文说的是「1 个学期」——写 5 就等于
# 把换算结果冒充成官方值。数据保留官方单位，换算只在这里发生一次。
_SEMESTER_MONTHS = 5.0

# 时长单位 → 月。只收 schema 允许的三种单位，避免「周」「学期」各写一套隐式换算。
EDU_DURATION_UNITS = {"months", "weeks", "semesters", "academic_years"}
_WEEKS_PER_MONTH = 52 / 12  # 52 周 / 12 月

# —— 单位换算：本仓的**显式假设**，不是官方数字 ——
#
# 这两个常数是本仓唯一做单位换算的地方。之所以必须有它们：官方原文用的单位
# 是「学年 / 学期」，而画像填的是月；不换算就永远判不了，硬填一个「9 个月」
# 进数据又是把推算冒充官方值。折中是：**数据保留官方单位**，换算是常量 + 注释。
#
# 依据与边界：
#   · 一学年 = 2 学期：美国学制的通行划分（fall + spring），也与 SEVP 对
#     「one full academic year」的用法一致（学年由学校定义，联邦未给月数）。
#   · 一学期 = 5 个月：由上式反推（10 / 2）。USCIS、8 CFR 214.2 与 SEVP
#     Help Hub 均未给出「一学年 = 几个月」的统一数字，所以这里不声明官方性。
#   · 这两个值只影响「够不够」的判定，不影响数据的官方来源链 —— 数据里存的是
#     `{value: 1, unit: "academic_years"}`，任何读者都能看到官方原话的形态。
_SEMESTER_MONTHS = 5.0
_ACADEMIC_YEAR_MONTHS = _SEMESTER_MONTHS * 2  # 10.0


def edu_duration_months(spec: dict | None) -> float | None:
    """把 `{value, unit}` 形态的时长规约换算成月。

    单位不在表内、缺 value、value 非正数 → None（调用方据此判 silent，
    绝不猜一个数字）。不做「四舍五入到最近的常见值」——那是替官方改数字。
    """
    if not isinstance(spec, dict):
        return None
    value = spec.get("value")
    unit = spec.get("unit")
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    if unit == "months":
        return float(value)
    if unit == "weeks":
        return float(value) / _WEEKS_PER_MONTH
    if unit == "semesters":
        return float(value) * _SEMESTER_MONTHS
    if unit == "academic_years":
        return float(value) * _ACADEMIC_YEAR_MONTHS
    return None


def edu_min_duration_months(doc: dict) -> float | None:
    """项目侧的**就读时长下限**（月）：结构化 `min_duration` 优先，note 兜底。

    这是「一整个学年 / 8 个月 / 30 周」这类要求的唯一读点。返回 None 有两层
    含义，调用方必须分开处理：
      · 项目**没有**时长要求（`edu_duration_required()` 为 False）→ 不构成门槛；
      · 项目**有**时长要求但拿不到数字 → `edu_duration_unknown`（silent）。
    """
    edu = (doc.get("eligibility") or {}).get("education") or {}
    months = edu_duration_months(edu.get("min_duration"))
    if months is not None:
        return months
    # note 兜底：只认「不少于 / 至少 / 不低于 N 个? (学年|年|个月|周|学期)」，
    # 且要求同段出现不合格措辞 —— 与 EDU_YEARS_STRICT 同一套成对规则。
    note = edu.get("note") or ""
    hit = EDU_DURATION_IN_NOTE.search(note)
    if not hit or not EDU_YEARS_DISQUALIFY.search(note):
        return None
    value = cn_int(hit.group(1))
    if not value or value <= 0:
        return None
    unit = hit.group(2)
    if unit in ("年", "学年"):
        return float(value) * 12
    if unit == "个月":
        return float(value)
    if unit == "周":
        return float(value) / _WEEKS_PER_MONTH
    if unit == "学期":
        return float(value) * _SEMESTER_MONTHS
    return None


def edu_duration_required(doc: dict) -> bool:
    """原文是否提出了就读时长要求（读得到数字，或明说有这条但没给数）。

    `duration_required: true` 而 `min_duration` 缺失，是「有要求、无数字」的
    显式登记 —— 这种情况必须判 silent（`edu_duration_unknown`），不许默认 pass。
    """
    edu = (doc.get("eligibility") or {}).get("education") or {}
    if edu.get("duration_required") is True:
        return True
    if edu_min_duration_months(doc) is not None:
        return True
    return False


def edu_paths(doc: dict) -> list[dict]:
    """项目的教育资格路径列表。结构化 `education.paths` 优先，缺失时合成单一路径。

    合成路径（老数据 / 只有 `minimum_level` 的项目）包含：
      · level        = `minimum_level`
      · enrollment   = `enrollment_required`（若有）
      · min_years_experience = `min_years_experience`（若有，单路径项目用它表达
                       「学位 + N 年」而不是「学位 or N 年」）
    这样老项目的判定与改造前**语义等价**（层级比较 + 在读状态 + 时长），
    行为差异只来自本单显式修的三处病灶，不会顺带改别的项目。
    """
    edu = (doc.get("eligibility") or {}).get("education") or {}
    declared = edu.get("paths")
    if isinstance(declared, list) and declared:
        out = []
        for raw in declared:
            if not isinstance(raw, dict):
                continue
            path = {k: raw.get(k) for k in EDU_PATH_KEYS if k in raw}
            # 路径没写 level 时按 any（= 该路径不限学历），不是继承项目级——
            # 继承会让「②无学历要求 + 5 年经验」那条被项目级的 bachelor 污染。
            path.setdefault("level", "any")
            out.append(path)
        return out
    synth = {"level": edu.get("minimum_level") or "any"}
    if edu.get("enrollment_required"):
        synth["enrollment"] = edu.get("enrollment_required")
    if isinstance(edu.get("min_years_experience"), (int, float)):
        synth["min_years_experience"] = edu.get("min_years_experience")
    if isinstance(edu.get("graduated_within_months"), (int, float)):
        synth["graduated_within_months"] = edu.get("graduated_within_months")
    return [synth]


def edu_path_eval(path: dict, pr: dict, doc: dict) -> dict:
    """判一条路径。返回 {verdict: pass|fail|unknown, need, have, blocked, why}。

    三态而不是布尔：路径里的某个谓词缺数据时，这条路径**既不能算成立也不能算
    不成立**，而整组路径的结论要按「有没有一条确定成立 / 是否全部确定不成立 /
    其余情况」来合（见 `judge_education()`）。把 unknown 折成 fail 会让
    「数据没登记」变成「你不能申」；折成 pass 就是本单要消灭的假 pass。

    `blocked` 记录**是哪一类谓词缺数据**（experience / duration / enrollment /
    level），调用方据此选 silent code：`edu_duration_unknown` 只该在时长真的
    缺数时出现，不能因为经验年限没填就冒出来。
    """
    need_bits: list[str] = []
    have_bits: list[str] = []
    # 每条路径自带的判定结果：缺数据记 unknown，硬性不符记 fail
    statuses: list[str] = []
    blocked: list[str] = []
    failed: list[str] = []

    level = path.get("level") or "any"
    has_level = level != "any"
    if has_level:
        need_bits.append(f"学历 {level}")
        have_bits.append(f"你的学历 {pr.get('education')}")

    enroll = path.get("enrollment")
    if enroll == "enrolled":
        need_bits.append("当前在读")
    elif enroll == "graduated":
        need_bits.append("已毕业")

    min_exp = path.get("min_years_experience")
    if isinstance(min_exp, (int, float)) and min_exp > 0:
        region = path.get("experience_region") or "any"
        where = "境外相关" if region == "outside" else "相关"
        need_bits.append(f"{where}工作经验 {min_exp:g} 年")

    min_months = path.get("min_months")
    # 官方单位优先：`min_duration` 保留原文的「1 个学期」，换算在这里做一次。
    # `min_months` 是已折算好的月数直给，两处都写时以 min_duration 为准。
    spec_months = edu_duration_months(path.get("min_duration"))
    if spec_months is not None:
        min_months = spec_months
    if isinstance(min_months, (int, float)) and min_months > 0:
        need_bits.append(f"就读时长 ≥ {min_months:g} 个月")

    # —— 谓词 ①：层级 ——
    if has_level:
        if not pr.get("education"):
            statuses.append("unknown")
            blocked.append("level")
        elif not edu_level_ok(level, pr.get("education")):
            statuses.append("fail")
            failed.append("level")

    # —— 谓词 ②：在读状态 ——
    if enroll:
        actual = pr.get("enrollment_status")
        if actual is None:
            statuses.append("unknown")
            blocked.append("enrollment")
        elif enroll == "enrolled":
            if actual == "enrolled":
                statuses.append("pass")
            else:
                statuses.append("fail")
                failed.append("enrollment")
        elif enroll == "graduated":
            if actual == "completed":
                statuses.append("pass")
            else:
                statuses.append("fail")
                failed.append("enrollment")

    # —— 谓词 ③：毕业宽限期（intern 的「毕业不超过 12 个月」）——
    within = path.get("graduated_within_months")
    if isinstance(within, (int, float)) and within > 0:
        actual = pr.get("enrollment_status")
        months_since = pr.get("months_since_graduation")
        if actual == "enrolled":
            statuses.append("pass")  # 在读走的是另一条腿，不受宽限期约束
        elif isinstance(months_since, (int, float)):
            if months_since <= within:
                statuses.append("pass")
            else:
                statuses.append("fail")
                failed.append("graduation_recency")
            have_bits.append(f"你毕业 {months_since:g} 个月")
        else:
            statuses.append("unknown")
            blocked.append("graduation_recency")

    # —— 谓词 ④：经验年限 ——
    if isinstance(min_exp, (int, float)) and min_exp > 0:
        years = pr.get("work_experience_years")
        if isinstance(years, (int, float)):
            if years >= min_exp:
                statuses.append("pass")
            else:
                statuses.append("fail")
                failed.append("experience")
            have_bits.append(f"你的经验 {years:g} 年")
        else:
            statuses.append("unknown")
            blocked.append("experience")

    # —— 谓词 ⑤：就读时长 ——
    if isinstance(min_months, (int, float)) and min_months > 0:
        done = pr.get("study_months")
        if isinstance(done, (int, float)):
            if done >= min_months:
                statuses.append("pass")
            else:
                statuses.append("fail")
                failed.append("duration")
            have_bits.append(f"你已读 {done:g} 个月")
        else:
            statuses.append("unknown")
            blocked.append("duration")

    if "fail" in statuses:
        verdict = "fail"
    elif "unknown" in statuses:
        verdict = "unknown"
    else:
        verdict = "pass"
    return {
        "verdict": verdict,
        "need": " 且 ".join(need_bits) or "无额外条件",
        "have": " / ".join(have_bits) or "已满足",
        "blocked": blocked,
        "failed": failed,
        "path": path,
    }


def judge_education(paths: list[dict], pr: dict, doc: dict) -> dict:
    """按「任一成立」合并各路径结论。

    合并规则（顺序不能换）：
      1. 有一条确定 pass  → pass（官方明文允许，且你的条件是成立的）
      2. 没有 pass，但有 unknown → unknown（说不清，绝不判死）
      3. 全部 fail → fail

    第 2 条是本单最重要的一行：J-1 Trainee 的两条路径里，若画像既没有学位
    也没有经验年限，两条都 unknown —— 结论必须是「不可判」，不是「不能申」。
    旧代码在这种情况下直接判 `edu_low`（假 cannot）。
    """
    evals = [edu_path_eval(p, pr, doc) for p in paths] or [
        edu_path_eval({"level": "any"}, pr, doc)
    ]
    if any(e["verdict"] == "pass" for e in evals):
        return {"verdict": "pass", "evals": evals}
    if any(e["verdict"] == "unknown" for e in evals):
        return {"verdict": "unknown", "evals": evals}
    return {"verdict": "fail", "evals": evals}


def stay_months(doc: dict) -> int | None:
    """许可/停留期的月数上限：优先结构化 `work_conditions.max_stay_months`，
    退化时读 `timeline.quota_note` 的「最长 N 个月」。都没有则返回 None。"""
    wc = doc.get("work_conditions") or {}
    m = wc.get("max_stay_months")
    if isinstance(m, int) and m > 0:
        return m
    tl = doc.get("timeline") or {}
    text = " ".join(str(tl.get(k) or "") for k in ("quota_note", "processing_time"))
    hit = re.search(r"最长\s*([一二三四五六七八九十两\d]+)\s*个?月", text)
    if hit:
        return cn_int(hit.group(1))
    return None


def _precondition_notes(doc: dict, req_type: str) -> list[str]:
    """取某一族（身份 / 在地）里 required 为真条目的 note。"""
    reqs = (doc.get("eligibility") or {}).get("other_requirements") or []
    return [
        r.get("note") or ""
        for r in reqs
        if r.get("required") is True and r.get("type") == req_type
    ]


def _classify_identity(notes: list[str]) -> str | None:
    """身份族 → 一个类别。优先级链照旧：「已经持过该身份」比国籍/文件更靠近门槛。

    **空族返回 None（= 没有这一类要求）**，与「有要求但读不懂」的 unclassified
    严格区分：混起来会让全库顺查把每条项目都报成「有一条没读懂的要求」。
    """
    if not notes:
        return None
    joined = " ".join(notes)
    if PRE_LOCAL_STATUS.search(joined):
        return "local_status"
    if PRE_HOME_RESIDENCE.search(joined):
        return "home_residence"
    if PRE_CITIZENSHIP.search(joined):
        return "citizenship"
    if PRE_DOCUMENT.search(joined):
        return "document"
    # 读不懂就是读不懂：返回 "unclassified" 而不是 None，这样「全库顺查」能把它
    # 单独列出来。落 None 会让「没有前置要求」和「有要求但我们没读懂」长得一样。
    return "unclassified"


def _classify_location(notes: list[str]) -> str | None:
    """在地族 → 一个类别。

    三个方向互斥且必须分开：境内（inside）/ 境外（outside）/ 常驻护照国
    （home_residence）。**这里没有 fallback 到身份支的分支**——那正是要拆掉的
    东西。读不懂同样落 unclassified，空族落 None。
    """
    if not notes:
        return None
    joined = " ".join(notes)
    if PRE_INSIDE.search(joined):
        return "inside"
    if PRE_OUTSIDE.search(joined):
        return "outside"
    if PRE_HOME_RESIDENCE.search(joined):
        return "home_residence"
    if PRE_CITIZENSHIP.search(joined):
        return "citizenship"
    if PRE_DOCUMENT.search(joined):
        return "document"
    return "unclassified"


def precondition_kinds(doc: dict) -> list[str]:
    """读出**全部**前置类别（身份族 + 在地族），按固定顺序返回。

    过去只返回一个字符串，因为两类共用一条链；现在两族各出各的结论：
    us-f1-opt 会同时得到 ["local_status", "inside"]，两条要求各自留痕，
    任何一条都不再借另一条的 code 发声（batch9a 裁决 2）。

    顺序：身份族在前、在地族在后——与 judge() 里前身分支的先后一致，前端
    verdict.ts 必须逐一镜像（smoke-test 比的是 (dim,kind,code) 整串）。
    """
    out: list[str] = []
    ident = _classify_identity(_precondition_notes(doc, REQ_TYPE_RESIDENCY))
    if ident:
        out.append(ident)
    loc = _classify_location(_precondition_notes(doc, REQ_TYPE_LOCATION))
    if loc:
        out.append(loc)
    return out


def precondition_kind(doc: dict) -> str | None:
    """单值版本：两族里**最靠前**的那个类别，没有前置要求时返回 None。

    保留它是因为三处调用方只关心「有没有读到一条前置要求」这件事：
    `p21_worksheets.rule_holds()`（判「这段原文已处置」）、`flags_of()` 的历史
    形状契约、以及测试里的单点断言。需要逐族细节的地方请用
    `precondition_kinds()`——本单新增的在地分支只在那条路径上出现。
    """
    kinds = precondition_kinds(doc)
    return kinds[0] if kinds else None


def precondition_text(doc: dict) -> str:
    """报告用：前置条件原文首句（只截取，不改写）。"""
    for t in REQ_TYPES_PRECONDITION:
        for note in _precondition_notes(doc, t):
            return note.strip()[:120]
    return ""


# --------------------------------------------------------------------------
# P1b-2：把 P1b-1 迁好的 typed 值接进判定（三个家族）
#
# P1b-1 把原来「一个 type 名装十种语义」的三个值拆成了 13 个具体值，但引擎
# 一个字节都没读——`other_requirements` 里除了 residency_requirement，其余
# 全都进不了判定面。于是「这个项目不许带家属」「一生只能参加一次」这类**原文
# 写得很清楚的硬条件**，在画像页上完全看不见。
#
# 本节的接线原则（照设计稿 §1.13 / §2.13 / §3.3 的判定表逐值实现）：
#
#   ① 引擎按 `type` 接线，不读 note 散文（batch8 裁决 4）。所以这里的每个分支
#      只比较 type 集合，不对中文做正则。
#   ② 画像缺对应信息 → 判 silent（不可判），**绝不默认 pass**。这是本单最容易
#      出错的地方：一句「默认满足」就能让所有存量用户看到虚假的「能申」。
#   ③ 方向必须与原文一致。三个家族里各有一条方向相反的（须持过签证 / 须已毕业 /
#      家属被允许），照 type 名字猜方向会判反——见 tests 的方向回归组。
#
# 值的语义归属（设计稿逐条判定表的结论，不是按名字推的）：
#   禁令类（做不到就不满足）：no_child_dependents / no_other_dependents /
#     dependents_cannot_work / program_once_in_lifetime / program_once_per_project /
#     prior_same_category_visa / program_participation_cap /
#     prior_specific_visa_required / enrollment_proof / degree_completed_proof /
#     enrollment_or_degree_proof
#   非闸门类（只作材料呈现，判 na 留痕）：dependents_allowed /
#     dependents_separate_application / declaration_document / credential_scoring_input
# --------------------------------------------------------------------------

# 家属禁令：两个值的边界不同，不能合成一个布尔。
#   no_child_dependents  只禁「受抚养子女」（au-462 / nz-china-whv /
#                        uk-youth-mobility-scheme 三条）
#   no_other_dependents  禁「其他家属」统称，含配偶与子女（kr-h1 / uk-short-term-study-visa）
#
# 「受抚养子女」**不设年龄上限**（P1c §0.2，Muse 待裁②裁决）。
# 官方原文是 `not be accompanied by dependent children`——按**受抚养关系**定义，
# 不按年龄定义。18 岁以上仍在校且受抚养者，照样在禁内。P1b-1 之前 au-462 的
# note 把这条收窄成「未成年子女」，是记法造成的偏差，不是原文的边界（该 note
# 已在 1b5552d 按官方原文改回）。
#
# 引擎侧怎么落地这条：画像的 `dependents` 只有 none / children / partner / other
# 四档，**没有年龄粒度**，而 `children` 这一档本身就是「有受抚养子女」这个
# 与年龄无关的事实——所以「成年受抚养子女」在这里不另设分支，它落的就是
# `children`，判定结果是禁（fail）。**不要**为了「看起来支持成年子女」再加一档
# `adult_children`：那会把一个以受抚养关系定义的桶按年龄切两半，切出来的两半
# 都不再是原文的那个桶。若将来画像真要加年龄粒度，判断依据必须是「是否受抚养」
# 而不是「是否满 18 岁」。
DEP_FORBID_CHILD = "no_child_dependents"
DEP_FORBID_OTHER = "no_other_dependents"
DEP_CANNOT_WORK = "dependents_cannot_work"
DEP_SEPARATE = "dependents_separate_application"
DEP_ALLOWED = "dependents_allowed"
DECLARATION_ONLY = "declaration_document"

# 既往参加史：按「计账单位」分成三个值，判定方向一致（参加过 = 不满足）。
# 计数单位（按人/按项目段/按次数）写在 type 名里，本单不做账本运算——那是 P2。
HIST_ONCE_LIFETIME = "program_once_in_lifetime"
HIST_ONCE_PER_PROJECT = "program_once_per_project"
HIST_PARTICIPATION_CAP = "program_participation_cap"
HIST_SAME_CATEGORY_VISA = "prior_same_category_visa"
# 正向：须**持过**某类签证（au-485-graduate）。与上面几条方向相反。
HIST_SPECIFIC_VISA_REQUIRED = "prior_specific_visa_required"

# 学籍/学历证明：三个值的方向各不相同，这是 §3 的核心陷阱。
ENROLL_ENROLLED = "enrollment_proof"  # 须当前在册（只有 IAESTE / J-1 SWT 两条）
ENROLL_DEGREE = "degree_completed_proof"  # 须已毕业（5 条）
ENROLL_EITHER = "enrollment_or_degree_proof"  # 在读或毕业，二者其一（J-1 intern）
SCORING_INPUT = "credential_scoring_input"  # 只是打分/材料输入，不是资格闸


def requirement_types(doc: dict, required_only: bool = True) -> set[str]:
    """读出 `other_requirements` 里的 type 集合。

    `required_only=True` 时只取 required 为真的条目——可选材料不构成门槛。
    非闸门类（dependents_allowed 等）在数据里是 required: false，需要显式放宽。
    """
    out = set()
    for r in (doc.get("eligibility") or {}).get("other_requirements") or []:
        if required_only and r.get("required") is not True:
            continue
        t = r.get("type")
        if t:
            out.add(t)
    return out


def _dependents_of(pr: dict):
    """画像里的家属构成；取不到返回 None（= 未知，不是「没有」）。"""
    return pr.get("dependents")


def p1b2_precondition_dims(doc: dict, pr: dict) -> list[dict]:
    """按 typed 值产出前置条件维的新条目（P1b-2）。

    顺序即输出顺序，前端 verdict.ts 必须逐一镜像——两侧比对是逐条 (dim,kind,code)
    的字符串相等，顺序也要一致。
    """
    need = requirement_types(doc, required_only=True)
    anyv = requirement_types(doc, required_only=False)
    dep = _dependents_of(pr)
    part = pr.get("prior_participation")
    visa = pr.get("prior_same_category_visa")
    enroll = pr.get("enrollment_status")
    edu = pr.get("education")
    out: list[dict] = []

    def add(code: str, kind: str, why: str, **extra):
        d = {"dim": "precondition", "kind": kind, "code": code, "why": why}
        d.update(extra)
        out.append(d)

    # —— 家属禁令 ——
    # 判 fail 而不是 gap：家属构成是申请人自己的事实，不是「差一步能补的手续」。
    if DEP_FORBID_CHILD in need:
        if dep is None:
            add("pre_dependents_unknown", "silent", "原文禁止携带受抚养子女，画像未采集家属构成，无法判定")
        elif dep == "children":
            add("pre_dependents_child_present", "fail", "原文禁止携带受抚养子女，你填了有受抚养子女",
                need="无受抚养子女随行", have="有受抚养子女")
        elif dep == "other":
            # 「其他」可能包含子女，也明确不含子女，画像这一档切不出来。
            add("pre_dependents_unknown", "silent",
                "原文禁止携带受抚养子女；你填的家属类型未区分是否含子女，无法判定")
        else:
            add("pre_dependents_none", "pass", "原文禁止携带受抚养子女，你填了无受抚养子女")
    if DEP_FORBID_OTHER in need:
        if dep is None:
            add("pre_dependents_unknown", "silent", "原文禁止携带家属，画像未采集家属构成，无法判定")
        elif dep == "none":
            add("pre_dependents_none", "pass", "原文禁止携带家属，你填了无家属随行")
        else:
            add("pre_dependents_other_present", "fail",
                "原文禁止携带家属（统称，含配偶与子女），你填了有家属随行",
                need="无家属随行", have="有家属随行")

    # —— 家属不得工作（us-f1-opt）：禁的是「就业」，不是「同行」 ——
    # 家属可以跟着去，但不能凭这个身份工作。所以有家属时不能判 fail——
    # 那是把「同行」当成「就业」；也不能判 pass——那等于替家属保证不工作。
    if DEP_CANNOT_WORK in need:
        if dep is None:
            add("pre_dependents_unknown", "silent", "原文规定家属不得就业，画像未采集家属构成，无法判定")
        elif dep == "none":
            add("pre_dependents_none", "pass", "原文规定家属不得就业；你填了无家属随行，此项不适用")
        else:
            add("pre_dependents_work_unknown", "silent",
                "原文允许家属随行但不得就业；你是否打算让家属工作未采集，无法判定")

    # —— 家属须各自单独申请（nz-china-whv）：程序约束，不是资格闸 ——
    if DEP_SEPARATE in need:
        add("pre_dependents_separate", "na",
            "原文要求家属同行须各自单独递交申请；这是办理程序，不构成资格门槛")

    # —— 明确允许家属（au-485-vocational / uk-graduate-visa）——
    # 设计稿 §1.13 配套决定 1：这两个值在数据里是 required: false，若照旧跳过，
    # 用户看不到「本项目允许带家属」这个**正向信息**（它正是这几个项目与其他短期
    # 签证的区别点）。所以按「只作展示、不进判定」处理：判 na 并留一条痕。
    if DEP_ALLOWED in anyv:
        add("pre_dependents_allowed", "na", "原文明确允许家属随行（本条只作材料呈现，不构成资格闸）")

    # —— 声明文件（fr-recherche-emploi 的非一夫多妻声明）：同样是材料呈现 ——
    if DECLARATION_ONLY in anyv:
        add("pre_declaration_only", "na",
            "原文材料清单里有一份声明文件；这是递交材料，不构成资格门槛")

    # —— 既往参加史（按人 / 按项目段 / 按次数）——
    # 三者判定方向一致：参加过就不满足。计账单位的差别（一生一次 vs 换项目重置
    # vs 有次数上限）落在 note 里，本单不做账本运算（P2 账本维）。
    if need & {HIST_ONCE_LIFETIME, HIST_ONCE_PER_PROJECT, HIST_PARTICIPATION_CAP}:
        if part is None:
            add("pre_participation_unknown", "silent",
                "原文对既往参加过本项目/同类项目设有限制，画像未采集既往参加史，无法判定")
        elif part == "used":
            add("pre_participation_used", "fail",
                "原文限制已参加过本项目/同类项目者再次申请，你填了参加过",
                need="未曾参加过本项目/同类项目", have="已参加过")
        else:
            add("pre_participation_none", "pass",
                "原文限制既往参加过者，你填了未参加过")

    # —— 同类别签证史（au-462 / kr-h1 / nz-china-whv / uk-hpi-visa）——
    # 与「参加史」是两个维度：持过 WHV 签证 ≠ 参加过该项目，所以单独一个画像字段。
    if HIST_SAME_CATEGORY_VISA in need:
        if visa is None:
            add("pre_prior_visa_unknown", "silent",
                "原文限制曾持同类签证者，画像未采集同类签证史，无法判定")
        elif visa == "used":
            add("pre_prior_visa_used", "fail",
                "原文限制曾持同类签证者再次申请，你填了持过",
                need="未曾持过同类签证", have="曾持过")
        else:
            add("pre_prior_visa_none", "pass", "原文限制曾持同类签证者，你填了未持过")

    # —— 正向：须持过某类签证（au-485-graduate）——
    #
    # **这是本单最重要的一条方向回归。** 该条在 P1b-1 之前挂的是 `no_prior_visa`
    # （未持过任何签证），语义与原文完全相反：原文是 `have held a Student visa in
    # the last 6 months`——**须持过**。若照 type 名接线，会把「持过学签」的正常
    # 申请人判成不满足，把「没持过」的人判成满足，两类人都判反。
    #
    # 判 silent：画像不采集签证史，补一条就能判（P2 的时效维会连 6 个月窗口一起做）。
    if HIST_SPECIFIC_VISA_REQUIRED in need:
        add("pre_prior_visa_required", "silent",
            "原文要求**须持过**指定类别签证（正向要求，不是「未持过」）；画像未采集签证史，无法判定")

    # —— 学籍 / 学历证明（§3 的同名异义陷阱）——
    #
    # 原值 enrollment_proof 的中文标签是「需在读证明」，但 11 条里只有 2 条真是
    # 在读。三个新值各按自己的方向判，绝不共用一个分支。
    if ENROLL_ENROLLED in need:
        if enroll is None:
            add("pre_enrollment_unknown", "silent",
                "原文要求当前在册/全程保持学籍，画像未采集在读状态，无法判定")
        elif enroll == "enrolled":
            add("pre_enrolled_ok", "pass", "原文要求当前在册，你填了在读")
        else:
            add("pre_not_enrolled", "fail",
                "原文要求当前在册（在读期间保持注册），你填了已毕业",
                need="当前在读", have="已毕业")

    if ENROLL_DEGREE in need:
        # 只判「是否已完成某段学业」，**不判层级**：层级由 education 维负责。
        # 两条一起判会让 au-485-vocational 这类「文凭即可」的项目重复扣一次。
        if edu == "bachelor_in_progress":
            add("pre_degree_missing", "fail",
                "原文要求已取得学位/文凭（须已毕业），你填了本科在读",
                need="已毕业（取得学位/文凭）", have="本科在读")
        else:
            add("pre_degree_ok", "pass", "原文要求已取得学位/文凭，你填了已完成学历")

    if ENROLL_EITHER in need:
        if edu == "bachelor_in_progress" or enroll == "enrolled":
            add("pre_degree_ok", "pass", "原文接受在读证明或毕业证明，你填了在读")
        elif enroll == "completed" or edu in ("bachelor_completed", "master", "vocational", "high_school"):
            add("pre_degree_ok", "pass", "原文接受在读证明或毕业证明，你填了已完成学历")
        else:
            add("pre_enrollment_unknown", "silent",
                "原文接受在读证明或毕业证明，画像未采集在读状态，无法判定")

    # —— 学历只作打分/评估输入（sg-employment-pass / sg-s-pass）——
    # 原文明确「不是在读要求」「是支撑材料」，不构成资格闸。判 na 留痕，
    # 不判 silent——否则一个本来能申的项目会因为「我们把材料当成了门槛」变不可判。
    if SCORING_INPUT in anyv:
        add("pre_scoring_input_only", "na",
            "原文该项是学历/资质作为打分或材料审核的输入，不是资格门槛")

    return out


def load_programs() -> list[dict]:

    out = []
    for path in sorted(glob.glob(os.path.join(PROGRAMS, "*.json"))):
        with io.open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        out.append(doc)
    return out


# --------------------------------------------------------------------------
# 每维一个探测器：返回 (status, reason, evidence)
# --------------------------------------------------------------------------


def probe_passport(doc: dict, key: str) -> tuple[str, str, str]:
    pt = (doc.get("eligibility") or {}).get("passport_types") or {}
    val = passport_value(pt, key)
    if val is not None:
        return ("ok", f"字段已登记 = {val}", f"eligibility.passport_types.{key}")
    note = pt.get("note") or ""
    if NOTE_OPEN_NATIONALITY.search(note):
        return ("text", "未单独登记，但 note 明文「官方未按国籍设限」", note[:90])
    if note:
        return ("absent", "未登记，且 note 未给出可判结论", note[:90])
    return ("absent", "未登记，且无 note", "")


def probe_age(doc: dict) -> tuple[str, str, str]:
    age = (doc.get("eligibility") or {}).get("age") or {}
    note = (age.get("note") or "").strip()
    lo, hi = age.get("min"), age.get("max")
    if lo is None or hi is None:
        return ("absent", "min/max 缺失", "")
    if UNVERIFIED_PREFIX.match(note):
        return ("partial", f"占位 {lo}-{hi}，note 标「未核实」", note[:90])
    if lo == 0 and hi == 99:
        return ("ok", "0-99 = 无年龄限制（note 已说明）", note[:60])
    return ("ok", f"{lo}-{hi}", note[:60])


def probe_education(doc: dict) -> tuple[str, str, str]:
    edu = (doc.get("eligibility") or {}).get("education") or {}
    lvl = edu.get("minimum_level")
    if not lvl:
        return ("absent", "minimum_level 缺失", "")
    years = edu.get("years_completed")
    if years:
        return ("ok", f"{lvl}（另要求已完成 {years} 年本科）", "")
    return ("ok", str(lvl), "")


def has_none_sentinel(lang: dict) -> bool:
    """tests 里是否有 `test: "none"` 这个「不要求任何标准化考试」的哨兵。"""
    return any(str(t.get("test") or "").lower() == "none" for t in (lang.get("tests") or []))


def has_standard_test(lang: dict) -> bool:
    """tests 里是否有真正可比分的标准化考试条目。

    `test: "none"` 是本仓约定的哨兵（见 LANG_NO_STANDARD_TEST 的说明），
    它带 min_score 0，若按「有 min_score 就算登记了分数线」去认，会把
    「不要求任何考试」读成「雅思门槛 0 分」——那是替官方宣布人人达标。
    """
    if has_none_sentinel(lang):
        return False
    for t in lang.get("tests") or []:
        if t.get("test") in ("IELTS", "TOEFL_iBT", "PTE", "Cambridge") and isinstance(
            t.get("min_score"), (int, float)
        ):
            return True
    return False


def probe_language(doc: dict) -> tuple[str, str, str]:
    lang = (doc.get("eligibility") or {}).get("language") or {}
    if lang.get("required") is not True:
        return ("na", "官方不要求语言成绩", (lang.get("note") or "")[:80])
    tests = [
        t
        for t in (lang.get("tests") or [])
        if t.get("test") in ("IELTS", "TOEFL_iBT", "PTE", "Cambridge")
        and isinstance(t.get("min_score"), (int, float))
    ]
    if tests and has_standard_test(lang):
        # 以雅思为口径，没有雅思条目时退回任一有数值的考试
        pick = next((t for t in tests if t.get("test") == "IELTS"), tests[0])
        return (
            "ok",
            f"{pick['test']} ≥ {pick['min_score']}（另有 {len(tests) - 1} 种等效考试）",
            "",
        )
    note = lang.get("note") or ""
    if LANG_NO_STANDARD_TEST.search(note) or has_none_sentinel(lang):
        return (
            "na",
            "要求英语沟通能力，但官方不要求任何标准化考试（由项目方测试/雇主面试把关）",
            note[:90],
        )
    if LANG_BY_DESIGN.search(note):
        return ("na", "要求英语能力，但官方明确不设分数线（面试/自证/仅计分）", note[:90])
    if LANG_CEFR_LADDER.search(note):
        return (
            "text",
            "官方用 CEFR/CLB/NCLC 档位表述，须按官方对照表折算，结构字段未登记分数",
            note[:90],
        )
    return ("absent", "要求语言证明，但未登记任何分数线", note[:90])


def probe_funds(doc: dict) -> tuple[str, str, str]:
    funds = (doc.get("eligibility") or {}).get("funds") or {}
    if funds.get("required") is not True:
        return ("na", "官方不要求资金证明", (funds.get("note") or "")[:80])
    amount = funds.get("amount") or {}
    cny = amount.get("cny_estimate")
    if isinstance(cny, (int, float)):
        return ("ok", f"约 {int(cny):,} 元（{amount.get('local_amount')} {amount.get('currency')}）", "")
    note = funds.get("note") or ""
    if FUNDS_NO_FIXED.search(note):
        # 官方要求「资金有保障」但不给可比数字：递交时自证，不构成「预算够不够」
        # 的可比门槛，因此不判不可判 —— 但界面必须说清「这条要看你的存款证明，
        # 没有固定金额」。
        return ("na", "要求资金证明，但官方不设固定金额（自证，不可与预算比对）", note[:90])
    return ("absent", "要求资金证明，但未登记金额与折算", note[:90])


def probe_window(doc: dict) -> tuple[str, str, str]:
    sch = (doc.get("timeline") or {}).get("schedule") or {}
    typ, status = sch.get("type"), sch.get("status")
    conf = sch.get("date_confidence")
    if not typ:
        return ("absent", "schedule.type 缺失", "")
    if typ == "rolling":
        return ("ok", "rolling / 常年可申（本就没有日期，非缺字段）", "")
    if typ == "no_window":
        return ("ok", "no_window（官方不设申请窗口）", "")
    has_dates = bool(sch.get("open_date") or sch.get("close_date"))
    if conf == "confirmed" and has_dates:
        return ("ok", f"{typ} / confirmed / {sch.get('open_date')}–{sch.get('close_date')}", "")
    if conf == "inferred":
        return (
            "partial",
            f"{typ} / inferred：只有推算日期，不许当官方日期展示"
            + ("" if has_dates else "（仓内无具体日期）"),
            sch.get("cycle_note") or "",
        )
    if has_dates:
        return ("ok", f"{typ} / {status} / {conf}", "")
    return ("partial", f"{typ} / {status} / {conf}：结构在位但日期未公布", "")


PROBES = OrderedDict(
    [
        ("passport", None),
        ("age", probe_age),
        ("education", probe_education),
        ("language", probe_language),
        ("funds", probe_funds),
        ("window", probe_window),
    ]
)


# --------------------------------------------------------------------------
# 画像判决：与前端 web/src/lib/eligibility.ts 同一套规则（M2 落地后由
# tests 双向钉住：同三个样例画像必须给出同一组条数）
# --------------------------------------------------------------------------

# 画像里新增的三组字段（P1b-2）。它们与 passport / age / education 同级：都是
# 「这个人是谁」的一部分，不是「引擎猜出来的结论」。
#
# 为什么必须补在夹具上而不是留在引擎里判 silent：
#   三张样例画像本来就是一个**具体的人**（A=21 岁在读生、B=28 岁本科毕业、
#   C=25 岁本科毕业）。家属构成、既往参加史、在读/毕业状态，与年龄学历同属这个
#   人设本身。留着不填，等于夹具欠定义，却把由此产生的 silent 记成引擎的债 ——
#   那是度量错位（债在夹具，不在引擎）。
#
# 而「缺省即未知」的语义**没有被取消**：下面每个字段在 judge() 里取不到时仍然
# 一律判 silent，绝不默认 pass。tests 里有专门的用例
# （test_missing_profile_fields_stay_silent）把这条钉住，防止将来有人拿
# 「夹具填了值」去冒充「引擎能判」。
#
# 字段取值（缺省键 = 未知，与显式写 None 等价）：
#   dependents             none | children | partner | other
#                          —— 「你是否有受抚养/随行家属」
#   prior_participation    none | used
#                          —— 「你是否参加过该项目/该类项目」
#   prior_same_category_visa  none | used
#                          —— 「你是否持过同类别签证」（与上一条不同：参加史 ≠ 签证史）
#   enrollment_status      enrolled | completed
#                          —— 「你现在是在读还是已毕业」
#   current_location       ISO 3166-1 alpha-2 大写（CN / TW / AU …）
#                          —— 「你现在人在哪个国家/地区」（P1d）
#   work_experience_years  number|null
#                          —— 「你共有多少年与目标岗位相关的境外工作经验」（P3）
#   months_since_graduation number|null
#                          —— 「距你最近一次毕业过了多少个月」（P3，判毕业宽限期）
#   study_months           number|null
#                          —— 「你在这段最高学历里已实际就读多少个月」（P3，判时长门槛）
#
# P3 新加的三个字段，取值必须有 persona 依据（回执 §3 逐条列出），不许为了让
# 数字好看反向调夹具。三者的共同点是：它们都是那个**具体的人**的既有事实，
# 不是引擎的推断 —— 与 enrollment_status / current_location 同一性质。
#
# current_location 为什么用国家代码而不是自由文本：
#   判在地要求（「递交时人须在该国境内」）的唯一动作是**与项目所在国比较**，
#   而项目侧的国别已经有一套受 schema 管着的代码体系（program.country_code，
#   validate.py 用 `^[A-Z]{2}$` 卡）。画像这一侧用同一套代码，比较就是字符串
#   相等——不需要地名归一表、不需要模糊匹配，也不可能出现「澳洲 / Australia /
#   AU」三种写法互相认不出。取值缺失或不是两位大写即判 unknown（silent），
#   绝不猜测、绝不默认 pass。
CURRENT_LOCATION_RE = re.compile(r"^[A-Z]{2}$")

# 三张画像都是 **prospective applicant**（正在挑项目、还没出去的人），不是「已经
# 在目标国读书/工作的人」。所以现居地 = 护照所属地：A/B 大陆（CN）、C 台湾（TW）。
# 这个取值不是随手填的——它直接决定在地要求的翻转方向（详见 P1d 回执 §3：
# 现居=护照地时，五个「须在该国境内」的项目对三人全部判 cannot，因为三人都不在
# 那些国家；换成任何一个已经在该国的人，同一批项目会翻成 pass）。
SAMPLES = OrderedDict(
    [
        (
            "A",
            {
                "passport": "mainland_china",
                "age": 21,
                "education": "bachelor_in_progress",
                "ielts": 6.0,
                "budget_cny": 30000,
                # 21 岁在读本科生：无家属、无既往参加史、无同类签证史、在读
                "dependents": "none",
                "prior_participation": "none",
                "prior_same_category_visa": "none",
                "enrollment_status": "enrolled",
                "current_location": "CN",
                # P3 教育路径属性（依据见回执 §3）：
                #   21 岁、本科在读 —— 按 18 岁入学、四年制推算已读 3 年 = 36 个月，
                #   正好是大三（与「在读」而非「应届」一致）。这个值不取边角：
                #   取 36 而非 24/48，是因为 21-18=3 年是年龄本身给出的唯一读数。
                "study_months": 36,
                #   在读生没有「毕业多久」这件事，显式写 None 而不是省略键：
                #   省略与 None 在引擎里等价（都判 unknown），写出来是为了让
                #   「这个人没毕业」这件事在夹具上看得见，而不是像漏填。
                "months_since_graduation": None,
                #   在校生没有全职工作经历（实习不算「相关工作经验」——
                #   J-1 Trainee 原文说的是 occupational field 的 work experience）。
                #   取 0 而不是 None：0 是**已知的事实**，None 是「没问过」。
                #   这个区分直接决定 trainee 判 fail 还是 unknown。
                "work_experience_years": 0,
            },
        ),
        (
            "B",
            {
                "passport": "mainland_china",
                "age": 28,
                "education": "bachelor_completed",
                "ielts": None,
                "budget_cny": 80000,
                # 28 岁已毕业：同样无家属、无既往史，但已不在读
                "dependents": "none",
                "prior_participation": "none",
                "prior_same_category_visa": "none",
                "enrollment_status": "completed",
                "current_location": "CN",
                # P3：28 岁本科毕业、预算 8 万、正在找路径出国的境内青年。
                #   毕业月数取 60（毕业 5 年）——28 岁本科毕业的常见情形（22 岁毕业）；
                #   这个值 > 12，使 intern 的「毕业不超过 12 个月」这条对 B 不成立，
                #   正是本单要抓的假 pass（B 原先被判 can）。
                "months_since_graduation": 60,
                #   就读时长取 48 个月 = 四年制本科读满（中国大陆本科标准学制）。
                "study_months": 48,
                #   工作经验取 3 年：毕业 5 年、其中工作 3 年（含 gap 与考研），
                #   是 28 岁境内求职者的常见读数。这个值 ≥ trainee 路径①的 1 年、
                #   但 < 路径②的 5 年，所以 B 对 trainee 走的是「学位 + 1 年」这条，
                #   而不是「无学位 + 5 年」那条 —— 两条路径各被一个画像覆盖，
                #   夹具才有区分力。
                "work_experience_years": 3,
            },
        ),
        (
            "C",
            {
                "passport": "taiwan_china",
                "age": 25,
                "education": "bachelor_completed",
                "ielts": 6.5,
                "budget_cny": 50000,
                "dependents": "none",
                "prior_participation": "none",
                "prior_same_category_visa": "none",
                "enrollment_status": "completed",
                "current_location": "TW",
                # P3：25 岁台湾本科毕业，刚出校门（22 岁毕业 → 毕业 36 个月）。
                #   36 > 12，所以 intern 的宽限期对 C 也不成立（与 B 同向，
                #   但原因不同：B 是「毕业久 + 有工作经验」，C 是「毕业较近但仍超期」）。
                "months_since_graduation": 36,
                "study_months": 48,  # 台湾本科标准学制四年
                #   工作经验取 1 年：25 岁毕业 3 年、其中工作 1 年（其余为备考/服役/
                #   待业）。取 1 而不是 2，是为了让它正好落在 trainee 路径①的
                #   「≥1 年」边界上 —— 边界成立是 pass 的必要证据。
                "work_experience_years": 1,
            },
        ),
    ]
)


# --------------------------------------------------------------------------
# 采集面契约（2026-11-20 01:56 工单）
#
# 这个模块量的是「引擎能从画像里读什么」，而网页表单只问用户其中一部分。
# 两者不一致时，审计用 13 字段夹具量出线内，真实用户拿 6 字段却越线——
# 闸量错了对象。下面两个常量把「差异」变成可断言的数字，而不是靠人记。
#
# FORM_FIELDS = 网页表单真的问了的字段
#   （web/src/components/VerdictView.tsx 的 pfield；EMPTY_VERDICT_PROFILE 同）
# PROFILE_FIELDS = 引擎真的读了的字段（judge() 里 pr.get / pr[]）
#
# 两者之差 = 采集缺口。tests 里 test_profile_fields_are_all_collectable
# 咬住「缺口为空」：将来谁在引擎里加一个画像字段而没加表单口，那条测试当场红。
# 这比「再写一篇报告说明缺口」有用——报告不会拦下一个人。
#
# 注意：这里登记的是**字段是否被问过**，不是「必须填」。用户不填仍是未知，
# 引擎老老实实判 silent；本契约只要求「有这么个输入口可以填」。
# --------------------------------------------------------------------------

FORM_FIELDS = (
    "passport",
    "age",
    "education",
    "ielts",
    "budget_cny",
    "current_location",
    # —— 本单补齐的 7 项（条件显示，见 web/src/lib/profileFields.ts）——
    "dependents",
    "enrollment_status",
    "months_since_graduation",
    "prior_participation",
    "prior_same_category_visa",
    "study_months",
    "work_experience_years",
)

PROFILE_FIELDS = (
    "passport",
    "age",
    "education",
    "ielts",
    "budget_cny",
    "current_location",
    "dependents",
    "enrollment_status",
    "months_since_graduation",
    "prior_participation",
    "prior_same_category_visa",
    "study_months",
    "work_experience_years",
)


def collection_gap() -> list[str]:
    """引擎读了、但表单没有输入口的字段。空表示采集面跟上了判定面。"""
    return sorted(set(PROFILE_FIELDS) - set(FORM_FIELDS))


# --------------------------------------------------------------------------
# 不可判的两分法（P2-1，2026-11-14 Muse 裁决）
#
# 「不可判」不是同一种东西，混在一个分子里量出来的比率会同时惩罚两件事：
# 数据债，和诚实地说「这件事得由 Sponsor 判断」。所以按 code 分两类：
#
#   甲类（设计性不可判）—— 补字段也判不了：原文把结论交给第三方主体判断，
#     或官方根本没有阈值。补进去的只能是某个 Sponsor 的口头答复，冒充成项目
#     规则正是 P2-0 站规禁止的事。准入语义只有两种（见下 BY_DESIGN_CODES 注释）。
#   乙类（可避免不可判）—— 现有字段或一条能明确定义的新字段就能表达，判不了
#     只是因为数据没登记 / 画像没采集 / 换算表没建。每一项都写得出「补什么能判」。
#
# 停工线仍然只绑**乙类**，阈值 1/3 一个数字没动：闸门防的是债，不是表达力。
# 全口径（乙+甲混算）继续输出但只许不增，作为历史可比与防洗白的第二道尺子。
# 甲类不设硬闸，只设一条软线（≥5 项在报告里要求人工解释），理由：甲类膨胀
# 说明的是 note 读不懂，该停下来看，不该让 CI 代替评审。
#
# 每一个甲类 code 必须在 docs/audit/2026-11-14-P2-1-不可判拆分提案.md §1.2
# 找得到「为什么补字段也判不了」的那一行，否则不许加。
# --------------------------------------------------------------------------


# 甲类白名单。准入语义只有两种，二者皆不满足的不许进来：
#   ① 原文把结论交给第三方主体逐人判断（edu_by_sponsor：法规未规定学位层级，
#      由 Sponsor 判断「同等经历」是否存在，没有任何字段能表达这件事）；
#   ② 官方无阈值，逐项目/逐 Sponsor 各不相同（age_unknown：正文无年龄条款，
#      下限由各 Sponsor 自行规定；登记一个数字即等于替某个 Sponsor 立法）。
#
# 反例备忘：edu_credential_unknown 的「认定」部分形态上属①，但它与可算的积分制
# 打包在同一个 code 里，按混合项规则（undecidable_class）整体归乙——不进来。
BY_DESIGN_CODES = frozenset(
    {
        "edu_by_sponsor",  # 法规未规定学位层级，由 Sponsor 判断「同等经历」
        "age_unknown",  # 官方正文无年龄条款，下限由各 Sponsor 自行规定
    }
)

# 乙类：其余所有 silent code，逐个显式登记。未登记即测试红——
# 这是「不许把乙塞进甲以绕闸」的那道机械闸（按 code 登记，不按项目）。
CLASS_B_CODES = frozenset(
    {
        "passport_conditional",  # 有条件开放，note 未给当年结论
        "passport_missing",  # 该护照未登记，note 无可判结论（数据债）
        "passport_unknown",  # 双边安排未核实（数据债）
        "edu_years_unknown",  # 学制年数未采集（画像债）
        "edu_recency_unknown",  # 毕业年份未采集（画像债）
        "edu_credential_unknown",  # 认定结论无字段 + 无 CEFR 换算（混合项，按债计）
        "edu_category_unknown",  # 参与人身份类别无字段（可与 Sponsor 判断拆开）
        "edu_place_unknown",  # 院校/名单数据未登记（数据债）
        "lang_no_score",  # 有分数线但仓内未逐项登记（数据债）
        "lang_cefr",  # 官方给 CEFR/CLB 档位，仓内无换算表（缺口可补）
        "funds_unknown",  # 要求资金证明但未登记金额（数据债）
        "funds_income_basis",  # 门槛是年收入，画像只采集可动用资金（画像债）
        "funds_amount_inferred",  # 金额为同类口径沿用，属登记债
        "funds_term_unknown",  # 月额门槛缺停留期上限（数据债）
        "pre_outside_country",  # 画像不采集现居地（画像债）
        # P1c：在地（递交时须在该国境内）。与 pre_outside_country 同为画像债，
        # 补一个 current_location 字段就能判——按 P2-1 判据属乙类。
        "pre_inside_country",
        "pre_home_residence",  # 画像不采集现居地（画像债）
        "pre_unclassified",  # 有必填前置要求但类别未识别（识别能力债）
        # —— P1b-2 新增：三个家族接进判定后暴露的不可判面 ——
        # 这几条全是「画像没采集那个人自己的事实」，按 P2-1 判据属乙类：
        # 补一条画像字段就能判，不是「原文交给第三方判断」。
        "pre_dependents_unknown",  # 画像不采集家属构成（画像债）
        "pre_dependents_work_unknown",  # 家属可随行但不得就业：不知你是否打算让家属工作（画像债）
        "pre_participation_unknown",  # 画像不采集既往参加史（画像债）
        "pre_prior_visa_unknown",  # 画像不采集同类签证史（画像债）
        "pre_prior_visa_required",  # 正向：须持过某类签证，画像不采集签证史（画像债）
        "pre_enrollment_unknown",  # 画像不采集在读/毕业状态（画像债）
        # —— P3 新增：教育路径化后暴露的不可判面 ——
        # 这几条全是「画像没采集那个人自己的事实」，按 P2-1 判据属乙类：
        # 补一条画像字段就能判，不是「原文交给第三方判断」。
        "edu_duration_unknown",  # 就读时长未采集 / 项目时长无数字（画像债 + 数据债）
        "edu_enrollment_unknown",  # 在读状态或毕业距今天数未采集（画像债）
        "edu_experience_unknown",  # 相关工作年限未采集（画像债）
    }
)

# 两条线的数值：停工线（硬，只看乙类）与甲类软线（只报警、不红）。
STOP_LINE_RATIO = 1 / 3
BY_DESIGN_ALERT_COUNT = 5

# --------------------------------------------------------------------------
# 停工线的双口径（Muse 2026-11-20 01:58 裁决，INBOX:1487）
#
# 裁决原文：即日起双口径并行，停工线以「真实用户画像口径」为准，夹具口径降为
# 回归参照。理由是这条闸的用途是保护真实用户，量夹具画像等于虚假保证。
#
# 为什么必须分两个口径：SAMPLES 每个样例给了 13 个字段，而当时的网页表单只有
# 6 个输入口。判定面（P1b-2 / P1c / P3）一直在扩，采集面没跟，于是普通用户
# 拿不到那 7 个事实，项目从「能申」掉成「不可判」——而只量夹具的闸显示线内。
# 闸量错了对象，越线就看不见。
#
# 真实口径 = 当时表单能采集的 6 字段原样 + 其余 7 字段置 None，跑同一个 audit()。
# 置 None 而不是删键：引擎里「缺键」与「显式 None」等价（都判 unknown），写出来
# 是为了让「这个人没被问过这件事」在夹具上看得见，而不是像漏填。
#
# **两个常量的分工（2026-11-20 02:xx 表单补齐后更新）**：
#   LEGACY_FORM_FIELDS —— 表单补齐**之前**能采集的 6 项。永不再变。
#     它的作用是保留「旧的真实口径」这条基线，好让「补齐字段带来了多少改善」
#     这个数字以后还能复算。改名而不是删掉：删了那段历史就无从复算。
#   REAL_PROFILE_NULLED_FIELDS —— 相对 LEGACY_FORM_FIELDS 置空的那 7 项。
#
# 补齐之后，真实口径（用当前的 FORM_FIELDS，13 项）与夹具口径**已经重合**，
# 所以现在这条闸报的两个数会一样。这不是闸失效了——相反，它说明采集面终于
# 追上了判定面：`collection_gap()` 为空就是这件事的机械证明。
# 若将来有人在引擎里加字段而没加表单口，缺口会重新出现，双口径会再次分叉，
# 而 test_profile_fields_are_all_collectable 会先红。
#
# LEGACY_FORM_FIELDS 与 REAL_PROFILE_NULLED_FIELDS 必须覆盖 SAMPLES 的全部字段键，
# 两侧一起改才不漏；漏一个字段的后果是那个字段仍带夹具值，旧口径被悄悄放宽
# （tests 里的 test_legacy_form_fields_cover_every_sample_field 咬住这条）。
# --------------------------------------------------------------------------
LEGACY_FORM_FIELDS = ("passport", "age", "education", "ielts", "budget_cny", "current_location")

REAL_PROFILE_NULLED_FIELDS = (
    "dependents",
    "enrollment_status",
    "months_since_graduation",
    "prior_participation",
    "prior_same_category_visa",
    "study_months",
    "work_experience_years",
)

# 停工线以真实口径为准（裁决第二条）。夹具口径保留输出，但只作回归参照。
STOP_LINE_CALIBER = "real"

# 在案债务上限：表单补齐**之前**，真实口径下 HEAD 的 C 画像乙类 = 15/41 = 0.3659，
# 已越 1/3。裁决第三条把那次越线记为在案债务，不阻塞 PR、也不许靠改阈值消掉。
#
# **补齐字段后这个数字降下来了**（15 → 8，见 tests 的 test_debt_ceiling_tracks_actual）。
# 裁决要求「只许降不许升、降下来必须回来把上限改小」，所以这里是 8 而不是 15：
# 留着 15 就等于给下一次新债留了 7 条免费额度，而封顶本身不会报警。
REAL_CLASS_B_DEBT_CEILING = 8


def real_profile(pr: dict) -> dict:
    """把一个夹具画像压成「网页表单真能采集到的那一份」。

    判据是**当前的** FORM_FIELDS：表单能问的字段原样保留，问不到的置 None。
    不做任何补默认值——补默认值等于替用户承认一个事实（如把 dependents
    默认成 none），那会把「没问过」洗成「已知」，真实口径立刻偏乐观。

    2026-11-20 表单补齐后 FORM_FIELDS 已是 13 项，于是这个函数返回的就是
    原画像，两口径重合。这不是函数失效：`collection_gap()` 为空正是它的
    **成功状态**。将来引擎加字段而表单没跟，FORM_FIELDS 不再覆盖它，
    这里会自动重新开始置 None，双口径重新分叉——不需要改这个函数。
    """
    out = dict(pr)
    for f in out:
        if f not in FORM_FIELDS:
            out[f] = None
    return out


def legacy_profile(pr: dict) -> dict:
    """表单补齐**之前**的口径：只留 6 项，其余 7 项置 None。

    存在的唯一理由是可复算：Muse 01:58 裁决那次越线（15/41）就是按这个口径
    量出来的，留着它才能验证「补齐字段把这 7 条债务清掉了几个」。
    它**不随后续补字段而变**（判据是固定的 LEGACY_FORM_FIELDS），
    所以它度量的是历史，不是现状。现状用 real_profile()。
    """
    out = dict(pr)
    for f in REAL_PROFILE_NULLED_FIELDS:
        out[f] = None
    return out


def measure_caliber(docs: list[dict], profiles: dict) -> dict:
    """按给定画像集合量一次乙类（停工线分子），不写任何全局状态。"""
    per = OrderedDict()
    for name in SAMPLES:
        pr = profiles[name]
        ids = []
        design = 0
        unknown = 0
        for doc in docs:
            state, dims = judge(doc, pr)
            if state != "unknown":
                continue
            unknown += 1
            cls = undecidable_class(dims, doc)
            if cls == "avoidable":
                ids.append(doc["program"]["id"])
            elif cls == "design":
                design += 1
        per[name] = {
            "unknown": unknown,
            "unknown_class_b": len(ids),
            "ratio_class_b": round(len(ids) / len(docs), 4),
            "class_b_ids": sorted(ids),
            "unknown_by_design": design,
        }
    return per

# age_unknown 归甲是**有条件**的（Muse 裁决 1）：note 必须同时给出「官方无阈值 /
# 由 Sponsor 自行规定」的证据，并且标了 ⚠️ 未核实。缺证据的 age_unknown 不是
# 设计性不可判，而是「没去查」的数据债 —— 甲类豁免不成立，按乙类计，并要求
# 单独出现在 audit()["design_exemptions_missing"] 里（改数据是另一单事，本腿
# 只把它照实报出来，不许顺手改项目数据）。
AGE_NO_THRESHOLD_EVIDENCE = re.compile(
    r"未出现[^。]{0,24}(?:年龄|years of age)|无年龄限制条款|年龄限制条款|Sponsor"
)


def design_exemption_holds(code: str, doc: dict) -> bool:
    """甲类豁免的语义复核：白名单只写 code，证据在数据里，两者都要成立。

    - edu_by_sponsor：judge() 只有命中 EDU_BY_SPONSOR（原文写明由 Sponsor 判断）
      才会发出这个 code，证据由探测器本身保证。
    - age_unknown：judge() 只看 ⚠️ 前缀，不看为什么未核实。所以这里补一道：
      note 必须写明「官方正文无年龄条款」或「由各 Sponsor 自行规定」。
    """
    if code == "age_unknown":
        note = ((doc.get("eligibility") or {}).get("age") or {}).get("note") or ""
        return bool(UNVERIFIED_PREFIX.match(note.strip())) and bool(
            AGE_NO_THRESHOLD_EVIDENCE.search(note)
        )
    return True


def undecidable_class(dims: list[dict], doc: dict | None = None) -> str | None:
    """返回 None / "design"（甲）/ "avoidable"（乙）。

    混合项只要有一条乙因就算 avoidable：同一项目里还有一条可修的债，它仍欠
    一次修复。反向规则（主因是甲就算甲）会让 de-chancenkarte 把一条明显可修
    的 CEFR 缺口洗成设计性——那正是 R2 要堵的口子。

    传了 doc 时额外做甲类语义复核（design_exemption_holds）：code 在白名单里
    不等于豁免成立，证据还得在数据里。
    """
    silent = {d.get("code") for d in dims if d.get("kind") == "silent"}
    if not silent:
        return None
    if not silent <= BY_DESIGN_CODES:
        return "avoidable"
    if doc is not None and not all(design_exemption_holds(c, doc) for c in silent):
        return "avoidable"
    return "design"


def passport_value(pt: dict, key: str):
    """读一条项目的某护照结论，兼容两种历史写法。

    数据里台湾护照有 `taiwan_china` 与 `tw_china` 两种键：validate.py 的 schema
    只枚举前者，但 12 个文件登记的是后者（au-407-training、au-485-vocational、
    dk-working-holiday 等）。只认 `taiwan_china` 会让这 12 条对台湾护照的
    结论变成「未登记」——`judge()` 落到 passport_missing，判 silent。

    影响是**真实且不对称**的：这 12 条项目的 note 大多写着「官方未按国籍设限」，
    于是未知护照会走 NOTE_OPEN_NATIONALITY 判 pass；唯独台湾护照因为键名对不上
    被判 silent，一个明明写明可申的项目变成「不可判」。

    修在读取端而不是批量改数据：两种键表达的是同一件事，读取时归一即可；
    直接改 12 个文件的数据本体属于「为了让判定好看而去动被审计的对象」。
    真正的收敛（统一成 `taiwan_china`）应由 validate.py 升级为错误来完成，
    那是一次独立的数据修订，不混进判定逻辑的修复里。
    """
    if key in pt:
        return pt[key]
    if key == "taiwan_china":
        return pt.get("tw_china")
    if key == "tw_china":
        return pt.get("taiwan_china")
    return None


def current_location_of(pr: dict) -> str | None:
    """画像里的现居地国家代码；取不到**合法值**时返回 None（= 未知）。

    「取不到」的判断必须严：ISO 3166-1 alpha-2 是两位大写字母。空串、None、
    小写 `cn`、中文「中国」、拼错的 `CHINA` 全部返回 None，让调用方落 silent。

    为什么不宽容一点（比如把小写转大写、把「中国」映射成 CN）：
    在地要求判错方向的代价是把一个**能申的人判成不能申**（或反之），而且这种
    错误在界面上看起来完全正常。宽容匹配一旦写错，错误会静默传播到每一条项目。
    宁可让格式不对的值落 unknown、让人看见「无法判定」，也不替用户猜他填的是哪国。
    """
    v = pr.get("current_location")
    if isinstance(v, str) and CURRENT_LOCATION_RE.match(v.strip()):
        return v.strip()
    return None


def passport_country_of(pr: dict) -> str | None:
    """画像护照所属国家/地区代码；表里没有该护照时返回 None（= 不可判）。

    与 `current_location_of()` 同一套严格度，但**未知形态不同**：护照是一个受
    枚举约束的存储值（`PASSPORTS`），所以这里不做格式宽容，只查表。查不到就是
    「这张护照的所属地我们没登记」，落 silent——不拿 `current_location` 顶替，
    也不从别的字段推一个出来。`home_residence` 判的是「现居 == 护照所属地」，
    两边任一缺失都判不了，硬凑一边就是替官方下结论。
    """
    return PASSPORT_COUNTRY.get(pr.get("passport"))


def judge(doc: dict, pr: dict) -> tuple[str, list[dict]]:
    """返回 (can|cannot|gap|unknown, 逐维结论)。

    维结论 kind：pass / fail / gap（差多少可知）/ silent（数据不表态）/ na

    每个 dim 还带一个 `code`。code 是与前端 src/lib/verdict.ts 的**契约**：
    两边都产出同一组 (dim, kind, code)，smoke-test 拿 data/match-samples.json
    逐条比对。界面文案按 code 查表，所以文案与判定语言无关，判定与文案互不牵连。
    """
    dims: list[dict] = []

    # 护照
    pt = (doc.get("eligibility") or {}).get("passport_types") or {}
    val = passport_value(pt, pr["passport"])
    if val == "not_eligible":
        dims.append({"dim": "passport", "kind": "fail", "code": "passport_no", "why": "该护照明确不可申"})
    elif val == "eligible":
        dims.append({"dim": "passport", "kind": "pass", "code": "passport_ok", "why": "护照已登记可申"})
    elif val == "conditional":
        dims.append({"dim": "passport", "kind": "silent", "code": "passport_conditional", "why": "有条件开放，需查当年公告"})
    elif val == "unknown":
        dims.append({"dim": "passport", "kind": "silent", "code": "passport_unknown", "why": "官方未核实"})
    elif NOTE_OPEN_NATIONALITY.search(pt.get("note") or ""):
        dims.append(
            {
                "dim": "passport",
                "kind": "pass",
                "code": "passport_open",
                "why": "note 明文「官方未按国籍设限」",
                "inferred": True,
            }
        )
    else:
        dims.append({"dim": "passport", "kind": "silent", "code": "passport_missing", "why": "该护照未登记，note 无可判结论"})

    # 年龄
    age = (doc.get("eligibility") or {}).get("age") or {}
    lo, hi = age.get("min"), age.get("max")
    if UNVERIFIED_PREFIX.match((age.get("note") or "").strip()):
        dims.append({"dim": "age", "kind": "silent", "code": "age_unknown", "why": "官方未公布年龄限制"})
    elif lo == 0 and hi == 99:
        dims.append({"dim": "age", "kind": "na", "code": "age_none", "why": "官方无年龄限制"})
    elif pr["age"] < lo or pr["age"] > hi:
        dims.append(
            {
                "dim": "age",
                "kind": "fail",
                "code": "age_low" if pr["age"] < lo else "age_high",
                "need": f"{lo}-{hi} 岁",
                "have": f"{pr['age']} 岁",
                "why": f"年龄超出 {lo}-{hi} 岁",
            }
        )
    else:
        dims.append({"dim": "age", "kind": "pass", "code": "age_ok", "why": f"在 {lo}-{hi} 岁内"})

    # 学历（P3 路径化）
    #
    # 判定顺序与旧代码不同，改动理由逐条写在下面。**核心不变式**：
    #   · 有一条路径确定成立 → pass；
    #   · 全部路径确定不成立 → fail；
    #   · 其余（含缺数据）→ silent，且 code 指名缺的是哪一类谓词。
    # 旧代码的 `if need and by_sponsor → ... elif have < need → fail` 链条
    # 把「层级不够」当成第一判决，于是在有并列路径的项目上必然判死（假 cannot）。
    edu = (doc.get("eligibility") or {}).get("education") or {}
    edu_note = edu.get("note") or ""
    recency_need = edu_recency_years(doc)
    credential_need = None
    if credential_recognition_required(doc):
        # 认定 + 积分是同一组硬门槛，合成一句话写进 need：两者都表达不了，拆开
        # 报两遍就是同一个缺口说两次。
        pts = points_threshold(doc)
        credential_need = "学历或职业资格须被主管机构认定"
        if pts:
            credential_need += f"，且积分达到 {pts} 分"

    paths = edu_paths(doc)
    result = judge_education(paths, pr, doc)
    evals = result["evals"]
    # 时长是**路径之外**的一条独立门槛：它约束的是「这段学历里你待了多久」，
    # 与「哪条路径成立」正交（澳洲 485 的 2 学年 + 16 个月就是两条同时成立）。
    # 所以它不折进 paths，而在路径给出 pass 之后再判一次。
    dur_need = edu_min_duration_months(doc)
    dur_required = edu_duration_required(doc)
    dur_have = pr.get("study_months")

    if EDU_BY_SPONSOR.search(edu_note) and any(
        e["path"].get("level") not in (None, "any") for e in evals
    ):
        # 结构化的 minimum_level 比 note 更严：note 明说法规没规定学位层级、
        # 由 Sponsor 判断。这时拿结构化字段判 fail 是替官方拒绝（§4-5）。
        # 判在最前，因为它是「结构化字段不该被采信」，与路径成不成立无关。
        dims.append(
            {
                "dim": "education",
                "kind": "silent",
                "code": "edu_by_sponsor",
                "why": "结构化字段记了最低学位，但原文写明「法规未规定学位层级、由 Sponsor 判断」，以原文为准",
            }
        )
    elif result["verdict"] == "fail":
        # 全部路径都不成立 → 这是唯一该判 fail 的情形。need 把各路径条件并列
        # 写出（用「或」），读的人才看得出「过的是哪一条」。code 按**共同失败的
        # 谓词**选：层级不够是 edu_low，在读状态不符是 edu_not_enrolled ——
        # 「你毕业了」与「你学历低了」是两件事，共用一个 code 会让修法无从下手。
        first = evals[0]
        failed = {f for e in evals for f in e["failed"]}
        levels = [e["path"].get("level") for e in evals if e["path"].get("level") not in (None, "any")]
        need_text = " 或 ".join(e["need"] for e in evals)
        if "level" not in failed and failed & {"enrollment", "graduation_recency"}:
            dims.append(
                {
                    "dim": "education",
                    "kind": "fail",
                    "code": "edu_not_enrolled",
                    "need": need_text,
                    "have": f"{pr.get('enrollment_status')}",
                    "why": (
                        "原文把「当前在读 / 毕业不超过 N 个月」写成本项目的第一道门槛，"
                        "你的状态不满足（学历层级本身并不低）"
                    ),
                }
            )
        else:
            dims.append(
                {
                    "dim": "education",
                    "kind": "fail",
                    "code": "edu_low",
                    "need": need_text,
                    "have": pr["education"],
                    "why": (
                        f"学历门槛 {edu.get('minimum_level')}"
                        if len(evals) == 1 and levels
                        else f"{len(evals)} 条官方路径全部不成立（{first['need']}）"
                    ),
                }
            )
    elif result["verdict"] == "pass" and dur_required:
        # 路径成立，但另有就读时长门槛 —— 时长是硬条件，缺数字就不可判。
        if dur_need is None:
            dims.append(
                {
                    "dim": "education",
                    "kind": "silent",
                    "code": "edu_duration_unknown",
                    "need": "就读时长（原文有要求，仓内无数字）",
                    "why": (
                        "原文把「就读时长」写成硬门槛（一整个学年 / 若干个月 / 若干周），"
                        "但仓内未登记具体数字，你的就读时长也未采集，无法判定"
                    ),
                }
            )
        elif isinstance(dur_have, (int, float)) and dur_have >= dur_need:
            dims.append(
                {
                    "dim": "education",
                    "kind": "pass",
                    "code": "edu_ok",
                    "why": f"就读 {dur_have:g} 个月 ≥ 要求的 {dur_need:g} 个月",
                }
            )
        elif isinstance(dur_have, (int, float)):
            dims.append(
                {
                    "dim": "education",
                    "kind": "fail",
                    "code": "edu_duration_short",
                    "need": f"就读 ≥ {dur_need:g} 个月",
                    "have": f"{dur_have:g} 个月",
                    "why": f"就读时长差 {dur_need - dur_have:g} 个月",
                }
            )
        else:
            dims.append(
                {
                    "dim": "education",
                    "kind": "silent",
                    "code": "edu_duration_unknown",
                    "need": f"就读 ≥ {dur_need:g} 个月",
                    "why": (
                        f"原文要求就读不少于 {dur_need:g} 个月，你的就读时长未采集，无法判定"
                    ),
                }
            )
    elif result["verdict"] == "pass" and recency_need:
        # note 另写「须在申请日之前 N 年内完成学业或研究」（P2-0）。结构化
        # education 里只有层级与学制年数，没有「毕业年份」；画像也不采集毕业
        # 时间，因此不能默认「层级到了 = 达标」。
        #
        # 判 silent 而非 fail：毕业超过 N 年确实不满足，但画像只知道学历层级，
        # 一个刚毕业的人与一个毕业十年的人在画像里长得一样——替他判「不能申」
        # 同样是替官方拒绝。
        dims.append(
            {
                "dim": "education",
                "kind": "silent",
                "code": "edu_recency_unknown",
                "need": f"申请日前 {recency_need} 年内完成学业或研究",
                "why": (
                    f"原文另要求「申请日前 {recency_need} 年内完成学业/取得学位」，"
                    "你的毕业时间未采集，无法判定是否在时限内"
                ),
            }
        )
    elif result["verdict"] == "unknown":
        # 判不了，但要分清缺的是哪一类谓词 —— 不同 code 指向不同补法，
        # 合成一个 silent 会让「补哪个字段能判」这件事从报告里消失。
        blocked = {b for e in evals if e["verdict"] == "unknown" for b in e["blocked"]}
        if "duration" in blocked:
            dims.append(
                {
                    "dim": "education",
                    "kind": "silent",
                    "code": "edu_duration_unknown",
                    "need": " 或 ".join(e["need"] for e in evals),
                    "why": "该路径要求一定的就读时长，你的就读时长未采集，无法判定",
                }
            )
        elif blocked & {"enrollment", "graduation_recency"}:
            # 在读状态 / 毕业距今天数：两者都是「你现在是什么状态」，
            # 补一条画像字段就能判，故归乙类（pre_enrollment_unknown 同一口径）。
            dims.append(
                {
                    "dim": "education",
                    "kind": "silent",
                    "code": "edu_enrollment_unknown",
                    "need": " 或 ".join(e["need"] for e in evals),
                    "why": "该路径要求特定的在读/毕业状态，你的就读状态或毕业时间未采集，无法判定",
                }
            )
        elif "experience" in blocked:
            dims.append(
                {
                    "dim": "education",
                    "kind": "silent",
                    "code": "edu_experience_unknown",
                    "need": " 或 ".join(e["need"] for e in evals),
                    "why": "该路径接受「学位 + 工作经验」或纯经验替代，你的相关工作年限未采集，无法判定",
                }
            )
        else:
            # 落到这里只剩「画像没填学历」这类基础缺口，用原有的学制年数码不
            # 合适（那说的是学时长短），改用与在读状态同族的通用码。
            dims.append(
                {
                    "dim": "education",
                    "kind": "silent",
                    "code": "edu_years_unknown",
                    "need": " 或 ".join(e["need"] for e in evals),
                    "why": "该路径的某一项条件无法用你已填的信息判定",
                }
            )
    elif edu.get("years_completed") and pr["education"] == "bachelor_in_progress":
        dims.append(
            {
                "dim": "education",
                "kind": "silent",
                "code": "edu_years_unknown",
                "why": f"另要求已完成 {edu['years_completed']} 年本科，在读无法从他填的信息判定",
            }
        )
    elif participant_category_required(doc):
        # education.note 把资格写成「须属于四类身份之一」，并明说由 Sponsor 判断
        # 是否成立（P2-0 us-j1-camp-counselor）。结构化 minimum_level 是 any ——
        # 判 edu_ok 等于说「学历层级任何值都达标」，那句话与该条原文不是一回事：
        # 原文卡的是「你现在是在读学生 / 在职青年 / 教师 / 有专门技能」这个身份。
        #
        # 判 silent 而不是 gap：与 §4-5 的 edu_by_sponsor 同一口径——「由 Sponsor
        # 判断是否成立」的事，我们没有判据；画像也只采集学历层级。判 gap 会说成
        # 「你差这一项材料」，而真相是「你属于哪一类，得 Sponsor 认」。
        dims.append(
            {
                "dim": "education",
                "kind": "silent",
                "code": "edu_category_unknown",
                "why": "原文把资格限定为若干类参与人身份之一，是否成立由 Sponsor 判断；画像只采集学历层级，无法判定",
            }
        )
    elif credential_need:
        # 原文把「资格须被主管机构认定」写成本项目的第一条硬门槛，并另设积分制
        # （P2-0 de-chancenkarte）。结构化 education 只有 `bachelor_completed`——
        # 那说的是「你最高读到本科」，与「你这份学历被德国 ZAB/anabin 认定为等
        # 效」是两件事：后者要跑一次学历认定，结论可以是「不等效」。
        #
        # 判 silent 而不是 gap：与 EDU_PLACE 同一口径——认定结论是对你已持有学历
        # 的一次评价，不是一项还能补交的材料（画像也不采集认定结果）。判 gap 会说
        # 成「你差一张认定书」，把「可能根本认定不了」伪装成一个待办动作。
        dims.append(
            {
                "dim": "education",
                "kind": "silent",
                "code": "edu_credential_unknown",
                "need": credential_need,
                "why": (
                    "原文把「学历或职业资格被主管机构认定」与积分门槛都写成硬门槛；"
                    "结构化字段只记了学历层级，认定结果与积分总分都未采集，无法判定"
                ),
            }
        )
    elif EDU_PLACE.search(edu_note):
        # 学位须在指定国家/名单内院校完成（英国毕业生签证的「在英国以学生
        # 签证完成课程」、PGWP 的「合格 DLI 完成 ≥8 个月」、HPI 的「认可名单
        # 院校 + 5 年内授予」）。结构化字段只有层级，画像不采集院校与学制，
        # 因此这一维不能判 pass（§4-3 / §4-4 / §4-6）。
        dims.append(
            {
                "dim": "education",
                "kind": "silent",
                "code": "edu_place_unknown",
                "why": "原文要求学位在指定国家/名单内院校完成（另有时长或授予时点条件），院校与毕业年份未采集",
            }
        )
    else:
        dims.append({"dim": "education", "kind": "pass", "code": "edu_ok", "why": "达到学历门槛"})

    # 语言
    lang = (doc.get("eligibility") or {}).get("language") or {}
    if lang.get("required") is not True:
        dims.append({"dim": "language", "kind": "na", "code": "lang_none", "why": "不要求语言成绩"})
    else:
        tests = [
            t
            for t in (lang.get("tests") or [])
            if t.get("test") == "IELTS" and isinstance(t.get("min_score"), (int, float))
        ]
        note = lang.get("note") or ""
        # 哨兵优先于 tests：`test: "none"` 带 min_score 0，不能被当成「雅思门槛 0 分」
        if has_none_sentinel(lang) or LANG_NO_STANDARD_TEST.search(note):
            dims.append(
                {
                    "dim": "language",
                    "kind": "na",
                    "code": "lang_no_test",
                    "why": "官方不要求任何标准化语言考试（由项目方测试/雇主面试把关）",
                }
            )
        elif tests:
            need_score = tests[0]["min_score"]
            if pr["ielts"] is None:
                dims.append(
                    {
                        "dim": "language",
                        "kind": "gap",
                        "code": "lang_missing",
                        "need": f"雅思 {need_score}",
                        "have": "未提供语言成绩",
                        "why": f"需要雅思 {need_score} 及以上，你没填语言成绩",
                    }
                )
            elif pr["ielts"] < need_score:
                dims.append(
                    {
                        "dim": "language",
                        "kind": "gap",
                        "code": "lang_low",
                        "need": f"雅思 {need_score}",
                        "have": f"雅思 {pr['ielts']}",
                        "why": f"雅思差 {round(need_score - pr['ielts'], 1)} 分",
                    }
                )
            else:
                dims.append(
                    {
                        "dim": "language",
                        "kind": "pass",
                        "code": "lang_ok",
                        "why": f"雅思 {pr['ielts']} ≥ {need_score}",
                    }
                )
        elif LANG_BY_DESIGN.search(note):
            dims.append(
                {"dim": "language", "kind": "na", "code": "lang_by_design", "why": "官方不设分数线（面试/自证/仅计分）"}
            )
        elif pr["ielts"] is None:
            # 关键的不对称：用户**没填**语言成绩时，「这条要求语言、你没成绩」
            # 是确定的事实，不依赖仓内有没有登记分数线 —— 判 gap（差一项）。
            # 反过来，用户**填了**成绩而项目没登记分数线时，无法说够或不够，
            # 那句才是 silent（不可判）。两个方向都判 silent 会把「没考雅思」
            # 藏进「数据不可判」，等于用数据缺口替用户掩盖真实缺口。
            dims.append(
                {
                    "dim": "language",
                    "kind": "gap",
                    "code": "lang_missing",
                    "need": "语言成绩（项目要求）",
                    "have": "未提供",
                    # 措辞不能一律说「仓内未登记分数线」：CLB/CEFR 类项目是
                    # **登记了档位**（如 PGWP 的 CLB 7 / CLB 5），只是没有雅思
                    # 数字。一句话盖成「未登记」会让用户以为数据缺失，而真相是
                    # 单位不同、需按官方对照表折算——那正是界面 lang_cefr 要说的事。
                    "why": (
                        "该项目要求语言成绩，你没填；官方以 CLB/CEFR 档位表述，"
                        "需按官方对照表折算后再自评"
                        if LANG_CEFR_LADDER.search(note)
                        else "该项目要求语言成绩，你没填；具体分数线仓内未登记，需查官网"
                    ),
                }
            )
        elif LANG_CEFR_LADDER.search(note):
            dims.append(
                {
                    "dim": "language",
                    "kind": "silent",
                    "code": "lang_cefr",
                    "why": "官方用 CEFR/CLB 档位表述，仓内无对照表，无法与雅思分数直接比",
                }
            )
        else:
            dims.append(
                {
                    "dim": "language",
                    "kind": "silent",
                    "code": "lang_no_score",
                    "why": "项目要求语言证明但仓内未登记分数线，无法判断你的成绩是否达标",
                }
            )

    # 预算
    funds = (doc.get("eligibility") or {}).get("funds") or {}
    if funds.get("required") is not True:
        dims.append({"dim": "funds", "kind": "na", "code": "funds_none", "why": "不要求资金证明"})
    else:
        amount = funds.get("amount") or {}
        cny = amount.get("cny_estimate")
        note = funds.get("note") or ""
        amount_note = amount.get("note") or ""
        income_based = bool(FUNDS_INCOME.search(amount_note + " " + note))
        # 金额是否按月计；期限上限能拿到多少个月。两者合力决定能不能比。
        monthly = bool(FUNDS_MONTHLY.search(amount_note + " " + note))
        months = stay_months(doc) if monthly else None
        inferred_amount = bool(
            FUNDS_INFERRED.search(
                EXCHANGE_DISCLAIMER.sub("", amount_note + " " + note)
            )
        )
        if not isinstance(cny, (int, float)):
            if FUNDS_NO_FIXED.search(note):
                dims.append(
                    {
                        "dim": "funds",
                        "kind": "na",
                        "code": "funds_by_design",
                        "why": "要求资金证明但官方不设固定金额，递交时自证",
                    }
                )
            else:
                dims.append(
                    {"dim": "funds", "kind": "silent", "code": "funds_unknown", "why": "要求资金证明但未登记金额"}
                )
        elif income_based:
            # 门槛是「年收入」，用户填的是「可动用资金」——两个口径，不能相减。
            # 说够（一个存款数字够不着收入门槛）与说不够（有收入但没存款）都会
            # 把符合的人挡掉或把不符合的人放行，所以判 silent，请他看官网。
            dims.append(
                {
                    "dim": "funds",
                    "kind": "silent",
                    "code": "funds_income_basis",
                    "need": f"年收入约 {int(cny):,} 元",
                    "why": "该项要求的是年收入而非存款，无法与你填的可动用资金直接比较",
                }
            )
        elif inferred_amount:
            # 数字在仓内被标注为「按学生口径沿用 / 归类推定」，不是本许可的
            # 独立规定。可以用它估算差多少，但不能据此判「够」或「不够」。
            dims.append(
                {
                    "dim": "funds",
                    "kind": "silent",
                    "code": "funds_amount_inferred",
                    "need": f"每年约 {int(cny):,} 元" if monthly else f"约 {int(cny):,} 元",
                    "why": "该金额在仓内标注为按同类口径沿用/归类推定，不是本项目的独立规定，不作达标判断",
                }
            )
        elif monthly and not months:
            # 金额按「每月」计，但仓内拿不到期限上限 → 不知道要覆盖几个月，
            # 既不能说够也不能说差多少。判不可判并写明缺的是期限（§4-1）。
            dims.append(
                {
                    "dim": "funds",
                    "kind": "silent",
                    "code": "funds_term_unknown",
                    "need": f"每月约 {int(cny):,} 元",
                    "why": "该门槛是每月金额，须乘以停留月数才是要证明的总额；仓内未登记停留期上限，无法折算",
                }
            )
        elif monthly and pr["budget_cny"] < cny * months:
            # 月额门槛：按月数折算成总额再比（§4-1，de-16e 的 6 个月口径）
            total = cny * months
            dims.append(
                {
                    "dim": "funds",
                    "kind": "gap",
                    "code": "funds_short",
                    "need": f"约 {int(total):,} 元（每月 {int(cny):,} × {months} 个月）",
                    "have": f"{pr['budget_cny']:,} 元",
                    "why": f"资金证明差约 {int(total) - pr['budget_cny']:,} 元",
                }
            )
        elif monthly:
            total = cny * months
            dims.append(
                {
                    "dim": "funds",
                    "kind": "pass",
                    "code": "funds_ok",
                    "why": f"预算 ≥ 约 {int(total):,} 元（每月 {int(cny):,} × {months} 个月）",
                }
            )
        elif pr["budget_cny"] < cny:
            dims.append(
                {
                    "dim": "funds",
                    "kind": "gap",
                    "code": "funds_short",
                    "need": f"约 {int(cny):,} 元",
                    "have": f"{pr['budget_cny']:,} 元",
                    "why": f"资金证明差约 {int(cny) - pr['budget_cny']:,} 元",
                }
            )
        else:
            dims.append(
                {"dim": "funds", "kind": "pass", "code": "funds_ok", "why": f"预算 ≥ 约 {int(cny):,} 元"}
            )

    # 前置身份 / 在地要求（§4-3、§4-4、P1c）
    #
    # 这一段过去不存在：judge() 只读五处结构化字段，`other_requirements` 一个字
    # 没读。于是「只对已在英留学生开放」的毕业生签证被判成「谁都能申」。
    # 现在按原文类别分档，宁可不可判，也不静默判过。
    #
    # P1c：两族各出各的结论（见 precondition_kinds 的说明）。身份族与在地族不再
    # 共用一条 if/elif 链——us-f1-opt 同时有两个 source，过去只有一条能发声。
    for pre in precondition_kinds(doc):
        if pre == "local_status":
            dims.append(
                {
                    "dim": "precondition",
                    "kind": "gap",
                    "code": "pre_local_status",
                    "need": "先在该国持学生/居留身份并完成学业",
                    "have": "未采集该项经历",
                    "why": "原文把「已在该国持学生签/居留并完成学业」写成本项目的前置身份，这是能补的一项（先走留学路径）",
                }
            )
            if EDU_PLACE.search(edu_note):
                # 同一件事在教育维已经判过 silent，两处都报会让用户看到两条重复缺口
                dims = [d for d in dims if d["code"] != "edu_place_unknown"]
        elif pre == "inside":
            # 在地（batch8 立项、batch9a 裁决 1 定形）：与 outside 互为镜像，
            # 但**不并进 outside**——方向相反的两条要求共用一个 code 会让
            # 「必须人在境外」与「必须人在境内」在报告里长得一模一样。
            #
            # P1d 接地：这一条现在是**可判的**——画像有 current_location。
            #   与项目所在国相同 → pass（人已经在境内，这条不构成障碍）
            #   有值但不同     → fail（人不在境内 → 整体 cannot）
            #   缺失/非法      → silent（维持 P1c 的诚实结论，缺省绝不判 pass）
            # 三者各占一个 code：`pre_inside_country` 仍是「画像不采集」的原码，
            # 语义一个字节没动（P1c 的乙类登记与测试照旧按它读）。
            loc = current_location_of(pr)
            cc = (doc.get("program") or {}).get("country_code")
            if loc is None or not cc:
                # 两种「比不了」：画像没填现居地，或项目侧没有国别代码。
                # 后者在库里暂无实例（两条全球项目 global-aiesec / global-iaeste
                # 根本没有在地要求），但少了这一支，`loc == cc` 会把画像值与
                # None 比较、恒不等 → 恒判 fail，等于替官方拒绝。
                dims.append(
                    {
                        "dim": "precondition",
                        "kind": "silent",
                        "code": "pre_inside_country",
                        "why": "原文要求在递交时人位于该国境内，画像不采集现居地，无法判定",
                    }
                )
            elif loc == cc:
                dims.append(
                    {
                        "dim": "precondition",
                        "kind": "pass",
                        "code": "pre_inside_country_ok",
                        "need": f"递交时人在 {cc} 境内",
                        "have": f"你现在在 {loc}",
                        "why": f"你现居 {loc}，与项目所在国一致，这条在地要求已满足",
                    }
                )
            else:
                dims.append(
                    {
                        "dim": "precondition",
                        "kind": "fail",
                        "code": "pre_inside_country_no",
                        "need": f"递交时须身在 {cc} 境内",
                        "have": f"你现在在 {loc}",
                        "why": (
                            f"原文要求在递交时人位于 {cc} 境内，你填的现居地是 {loc}；"
                            "这条要求不是补材料能满足的，须先合法进入该国"
                        ),
                    }
                )
        elif pre == "outside":
            # 在地的镜像方向（P1e 接地）：递交时人须在该国**境外**。
            # `au-407-training`（`you must be outside Australia when you apply …
            # and when we grant it`）与 `se-look-for-work`（`You must currently be
            # located outside of Sweden`）是仅有的两条。
            #
            # 判法就是 inside 的镜像，比的是同一个 current_location 与同一个
            # country_code，只是方向相反：
            #   现居 != 项目国 → pass（人在境外，这条不构成障碍）
            #   现居 == 项目国 → fail（人在境内，申请本身无效）
            #   缺失/非法/项目国缺失 → silent（维持原码，绝不默认 pass）
            #
            # 为什么不能拿 inside 的 code 复用它：方向相反的两条要求共用一个 code
            # 会让「必须人在境外」与「必须人在境内」在报告里长得一模一样
            # （batch8 立项理由、P1c 用例 ⑤）。所以三个 code 各占一件事，原码
            # `pre_outside_country`（silent）的语义一个字节没动。
            loc = current_location_of(pr)
            cc = (doc.get("program") or {}).get("country_code")
            if loc is None or not cc:
                dims.append(
                    {
                        "dim": "precondition",
                        "kind": "silent",
                        "code": "pre_outside_country",
                        "why": "原文要求在递交时人位于该国境外，画像不采集现居地，无法判定",
                    }
                )
            elif loc != cc:
                dims.append(
                    {
                        "dim": "precondition",
                        "kind": "pass",
                        "code": "pre_outside_country_ok",
                        "need": f"递交时人须在 {cc} 境外",
                        "have": f"你现在在 {loc}",
                        "why": f"你现居 {loc}，不在项目所在国 {cc}，这条「境外递交」要求已满足",
                    }
                )
            else:
                dims.append(
                    {
                        "dim": "precondition",
                        "kind": "fail",
                        "code": "pre_outside_country_no",
                        "need": f"递交时人须在 {cc} 境外",
                        "have": f"你现在在 {loc}",
                        "why": (
                            f"原文要求递交时人位于 {cc} 境外，你填的现居地正是 {cc}；"
                            "在该国境内递交会被判无效，须先离境再递"
                        ),
                    }
                )
        elif pre == "home_residence":
            # 常驻护照所属地区（P1e 接地）。两条：`jp-working-holiday`
            # （须为协议国国民，且目前居住于其国籍国/地区）、`nz-china-whv`
            # （申请时须居住且常驻中国；其 passport_types note 自己写明
            # 「申请人须常驻其护照所属地区」）。
            #
            # **判据是「现居 == 护照所属地」，不是「现居 == 项目国」**——这是
            # P1d §8 定性的接法，方向搞反会把全部目标人群判错：JP 项目在 JP，
            # 但要求的「国籍国」是台湾/香港，不是日本。所以比的是
            # `current_location` 与 `PASSPORT_COUNTRY[passport]`，项目国不参与。
            #
            # 两条之一拿不到就判 silent，不硬凑：护照不在映射表里（将来新增的
            # 护照类型）、或现居地缺失/非法，都表示「这两边我们有一条不知道」。
            #
            #  citizenship 那一半（须为协议国国民）不在这里判：它由 passport 维
            # 覆盖（`jp-working-holiday` 对大陆护照是 `passport_no`），见 PRE_CITIZENSHIP
            # 的 na 分支说明。两处都判会让同一个缺口说两遍。
            loc = current_location_of(pr)
            home = passport_country_of(pr)
            if loc is None or home is None:
                dims.append(
                    {
                        "dim": "precondition",
                        "kind": "silent",
                        "code": "pre_home_residence",
                        "why": "原文要求常驻护照所属地区，画像不采集现居地，无法判定",
                    }
                )
            elif loc == home:
                dims.append(
                    {
                        "dim": "precondition",
                        "kind": "pass",
                        "code": "pre_home_residence_ok",
                        "need": f"常驻护照所属地区（{PASSPORT_ZH.get(pr.get('passport'), home)} → {home}）",
                        "have": f"你现在在 {loc}",
                        "why": f"你现居 {loc}，与护照所属地 {home} 一致，这条「常驻护照国」要求已满足",
                    }
                )
            else:
                dims.append(
                    {
                        "dim": "precondition",
                        "kind": "fail",
                        "code": "pre_home_residence_no",
                        "need": f"常驻护照所属地区（{PASSPORT_ZH.get(pr.get('passport'), home)} → {home}）",
                        "have": f"你现在在 {loc}",
                        "why": (
                            f"原文要求申请人常驻其护照所属地区（{home}），"
                            f"你填的现居地是 {loc}；这条要求补材料满足不了，"
                            "须回到护照所属地区再申请"
                        ),
                    }
                )
        elif pre == "citizenship":
            # 原文这一条是「须为参与国公民」——国籍条件，passport 维已经在判同一件事。
            # 报 na（不构成新缺口），但必须留痕：落空不让它看起来「这条要求不存在」。
            dims.append(
                {
                    "dim": "precondition",
                    "kind": "na",
                    "code": "pre_citizenship_basis",
                    "why": "原文该项是国籍条件，已由护照维判定，不另算缺口",
                }
            )
        elif pre == "document":
            # 「须持有效租约/购房合同」是递交时自行取得的文件，不是身份前置。
            # 它与「你得先在该国读过书」不是一回事：前者人人可办，后者决定了这条
            # 路对你开不开。判 na，不让它变成一条假缺口。
            dims.append(
                {
                    "dim": "precondition",
                    "kind": "na",
                    "code": "pre_document_basis",
                    "why": "原文该项是递交时自备的材料（租约等），不是身份前置条件",
                }
            )
        elif pre == "unclassified":
            # 有 required 的前置要求，但原文类别没认出来。**不能落 pass**：
            # §4-3 的错就是从这里来的。判 silent 并写明「有这条、我们没读懂」。
            dims.append(
                {
                    "dim": "precondition",
                    "kind": "silent",
                    "code": "pre_unclassified",
                    "why": "该项目有一条必填的前置身份/在地要求，原文类别未能识别，无法判定",
                }
            )

    # 岗位前置（P2-0 us-j1-camp-counselor）
    #
    # 「须落实营地岗位」不在 residency_requirement 里，而在 documents 的一条必交
    # 材料上（`Under no circumstance ... for whom a camp placement has not been
    # pre-arranged`），于是「岗位还没落实」被当成「能申」。判 gap 而不是 silent：
    # 岗位可以补（去报名、拿 placement），不是「数据不表态」。
    # 身份类别那条落在教育维里判（见上），与岗位是两件事，各占一维不重复。
    #
    # P4 §3：need 文案按项目取四种表述（营地 / 研究机构 DS-2019 / 暑期岗位+雇主
    # 面试 / DS-7002 三方文件链）。硬编码一条营地文案会让研究学者页显示
    # 「Sponsor 不得为未落实营地岗位者办理入境」——修一处漏网、引入一处错文案
    # （batch2 §4.2④ / batch4 §219 / batch9b §1.2② 先后记过三次）。
    if job_placement_required(doc):
        flavor = job_placement_flavor(doc)
        dims.append(
            {
                "dim": "precondition",
                "kind": "gap",
                "code": "pre_job_placement",
                # flavor 落进 dim 里，前端按它取同一条 code 的对应文案；
                # 取不到时由 py_have_flavor 测试当场红，不靠默认值兜。
                "flavor": flavor or "camp",
                "need": JOB_PLACEMENT_NEED.get(flavor, JOB_PLACEMENT_NEED_FALLBACK),
                "have": "未采集岗位落实情况",
                "why": "原文把「岗位须预先落实」写成硬性前提：没有落实的岗位/没有接收机构，Sponsor 不能签发后续文件、也不能办入境",
            }
        )

    # 岗位前置之二：雇主担保类项目的「具体雇主的合格聘用」（P2-0 no-skilled-worker）
    #
    # 挪威技术工人原文三条要求写在三处：other_requirements 写「必须有具体雇主的
    # 具体聘用（`You must have received a concrete job offer from one specific
    # employer in Norway.`）」、documents 写「岗位须全职或至少 80%」、
    # education.note 末尾写「岗位须与学历或资格对应」。三处合起来是同一个前提：
    # 你得先有一份合格聘用。过去这三处一个字节没读，于是「还没 offer」被判能申。
    #
    # 判 gap 而不是 silent：offer 是可以去争取的（投简历、面试、签约），属「差
    # 什么」，与「数据没写这一条」不是一回事。与上面的 pre_job_placement 分开登记：
    # 那个是 Sponsor 制项目的 placement 前置，这个是雇主担保项目的聘用前置，两者
    # 不会同时成立（命中集合互斥，见 Phase2P0 的 scoped 断言）。
    if employer_offer_required(doc):
        dims.append(
            {
                "dim": "precondition",
                "kind": "gap",
                "code": "pre_employer_offer",
                "need": "具体雇主的具体聘用（全职或至少 80% 岗位，且岗位与你的学历/资格对应）",
                "have": "未采集 offer 情况",
                "why": "原文把「先拿到具体雇主的合格聘用」写成硬性前提：没有 offer，雇主无法在系统里提交聘用确认，申请表也填不下去",
            }
        )

    # P1b-2：把 P1b-1 迁好的 typed 值接进判定（家属 / 签证史 / 学籍三个家族）。
    #
    # 这一段过去不存在：`other_requirements` 只有 residency_requirement 进过判定面，
    # 其余 type 全都没读。于是「本项目不许带家属」「一生只能参加一次」「须已毕业」
    # 这些**原文写明的硬条件**在画像页上完全看不见，所有项目看起来都比实际宽松。
    #
    # 放在 employer_offer 之后：新增维度只追加，不改既有六维的相对顺序，前端
    # verdict.ts 的镜像顺序也必须与这里一致（smoke-test 逐条比对 dims 串）。
    dims.extend(p1b2_precondition_dims(doc, pr))

    kinds = {d["kind"] for d in dims}
    if "fail" in kinds:
        return "cannot", dims
    if "gap" in kinds:
        return "gap", dims
    if "silent" in kinds:
        return "unknown", dims
    return "can", dims


# --------------------------------------------------------------------------
# 前端契约产物（--emit / --check）
#
# 两个文件，一个用途：
#   data/match-flags.json    每条项目每一维的**判定状态**（不是原文），供
#                            web/src/lib/verdict.ts 做纯比较。前端不再写任何
#                            「note 里有没有『未按国籍设限』」这类正则。
#   data/match-samples.json  三个样例画像 + Python 算出的逐项目结论（只留
#                            dim/kind/code，不留中文解释），供 smoke-test 把
#                            Python 与 TypeScript 两侧钉死：两边任何一边改了
#                            判定口径而另一边没跟上，测试立刻红。
#
# rules_version 是这套口径的版本号。改了 judge() 的判定逻辑就要 +1，并同时
# 更新前端 verdict.ts —— smoke-test 会比对两边的版本号，防止一边改一边忘。
#
# 版本轨迹：
#   7  P1b-2 家属/签证史/学籍三家族接线
#   8  P1c 在地从身份拆出（location_requirement + pre_inside_country）
#   9  P1d current_location 接地，inside 三态可判
#   10 P3 教育路径化：路径谓词替代 EDU_RANK 总序、去 >=3 下限、
#      doctorate 入枚举、新增 edu_duration_unknown / edu_enrollment_unknown /
#      edu_experience_unknown / edu_duration_short / edu_not_enrolled
#   11 P1e 两码接地：pre_outside_country（au-407 / se）与 pre_home_residence
#      （jp / nz）可判；home_residence 判据是「现居 == 护照所属地」，不是项目国，
#      新增 PASSPORT_COUNTRY 映射表（只登记库里真有的三类护照）
#   12 P4 Sponsor 包：JOB_PLACEMENT 词表扩围（六族官方写法）、
#      government_support_letter 接成语义分型的 typed 读点（只有 sponsorship
#      型进岗位族）、pre_job_placement 的 need 文案项目化为四种表述
RULES_VERSION = 12


def profile_readers(doc: dict) -> dict:
    """这条项目**读哪些画像字段**——由引擎自己算，不靠前端另抄一份。

    （2026-11-20 01:56 工单：表单关键字段补齐）

    为什么要在引擎里算而不是让前端按 p1b2 的布尔量自己推：
      推法写两遍就一定会漂。本单第一版让前端按 flags 的布尔量复推，
      两侧各有一份「dependents 读 forbid_child|forbid_other|cannot_work」，
      改引擎的一个分支时前端不知道。变异测试当场抓到了这个洞：
      把前端规则改错，Python 侧测试仍全绿——它验的是它自己的副本。

    所以口径只留这一份：这里给出布尔量，前端只读不推。

    判据是**实测**而不是读代码：把该字段从 None 换成一个可能的真值，
    看 (dim,kind,code) 整串会不会变。变 = 这条项目读它。
    这比按分支名匹配可靠——`edu_ok` 这种 pass code 在很多项目上都会出现，
    按名字查会把一大堆项目误算成「读 study_months」。

    代价是这个文件要跑 41 项目 × 7 字段 × 2 次 judge()。实测约 0.1 秒，
    可接受；换了更重的判据时再看要不要缓存。
    """
    out = {}
    for field, probe in PROFILE_FIELD_PROBES.items():
        positive = False
        for variant in (probe,):
            pr = dict(SAMPLES["C"])
            pr[field] = None
            _, before = judge(doc, pr)
            pr2 = dict(pr)
            pr2[field] = variant
            _, after = judge(doc, pr2)
            if _dim_signature(before) != _dim_signature(after):
                positive = True
        out[field] = positive
    return out


def _dim_signature(dims: list[dict]) -> str:
    return "|".join("%s:%s:%s" % (d["dim"], d["kind"], d["code"]) for d in dims)


# 实测每个字段「在场 vs 缺席」用的代表真值。
# 取的是夹具 C 的取值（每个字段在夹具里都有定义），所以这不是编的数字。
# 换一个真值可能翻出别的项目（例如 dependents 填 children 会多触发 fail 分支），
# 但那不影响「读不读」这个布尔——布尔只需要证明「换了会变」。
PROFILE_FIELD_PROBES = {
    "dependents": "none",
    "enrollment_status": "enrolled",
    "months_since_graduation": 6,
    "prior_participation": "none",
    "prior_same_category_visa": "none",
    "study_months": 48,
    "work_experience_years": 1,
}


def flags_of(doc: dict) -> dict:
    """把一条项目的六个维度压成前端够用的**状态量**。

    刻意只放状态量与数字阈值，不放 note 原文：note 是中文散文，放进索引会
    让前端重新长出「读中文猜结论」的逻辑，那正是 M1 要消灭的东西。
    """
    el = doc.get("eligibility") or {}
    pt = el.get("passport_types") or {}
    age = el.get("age") or {}
    edu = el.get("education") or {}
    lang = el.get("language") or {}
    funds = el.get("funds") or {}
    amount = funds.get("amount") or {}
    sch = (doc.get("timeline") or {}).get("schedule") or {}

    passport = {k: (passport_value(pt, k) or "missing") for k in PASSPORTS}
    passport["note_open"] = bool(NOTE_OPEN_NATIONALITY.search(pt.get("note") or ""))

    ielts = [
        t["min_score"]
        for t in (lang.get("tests") or [])
        if t.get("test") == "IELTS" and isinstance(t.get("min_score"), (int, float))
    ]
    no_test = has_none_sentinel(lang) or bool(LANG_NO_STANDARD_TEST.search(lang.get("note") or ""))
    if no_test:
        # 哨兵在时不能把 min_score 0 当成分数线传出去：前端拿到 ielts_min=0
        # 会判「人人达标」，那是替官方宣布条件。
        ielts = []
    lang_note = lang.get("note") or ""
    funds_note = funds.get("note") or ""
    cny = amount.get("cny_estimate")
    amount_note = amount.get("note") or ""
    # 月额门槛的期限上限：没有期限时前端要判 funds_term_unknown（§4-1）
    monthly = bool(FUNDS_MONTHLY.search(amount_note + " " + funds_note))
    months = stay_months(doc) if monthly else None

    return {
        # 项目所在国（ISO 3166-1 alpha-2）。P1d 起前端要用它判在地要求：
        # 画像的 current_location 与它相等 → 人已在境内。放进 flags 而不是让前端
        # 从 index.json 另取，是为了让「判在地」所需的**全部**输入都在同一个文件里，
        # 两侧比对时不会因为一个取自 A 文件、一个取自 B 文件而产生漂移。
        "country_code": (doc.get("program") or {}).get("country_code"),
        "passport": passport,
        "age": {
            "min": age.get("min"),
            "max": age.get("max"),
            "unverified": bool(UNVERIFIED_PREFIX.match((age.get("note") or "").strip())),
        },
        "education": {
            "level": edu.get("minimum_level"),
            "years_completed": edu.get("years_completed"),
            # note 另写的硬性年限门槛（§4-2）。结构化字段没有它时，靠它把
            # 「本科毕业」判成不可判，而不是直接判达标。
            "years_required": edu_years_required(doc),
            # —— P3：路径谓词所需的项目侧输入 ——
            #
            # 前端 verdict.ts 拿这组数据重演 judge_education()，与 Python 逐条比对。
            # 路径在这里**算好形态**（月数已折算）再传，不传原始 `{value, unit}`：
            # 单位换算只该在 Python 侧发生一次，前端再算一遍就是两份口径。
            "paths": [
                {
                    "level": p.get("level") or "any",
                    "enrollment": p.get("enrollment"),
                    "graduated_within_months": p.get("graduated_within_months"),
                    "min_years_experience": p.get("min_years_experience"),
                    "experience_region": p.get("experience_region"),
                    "min_months": (
                        edu_duration_months(p.get("min_duration"))
                        if p.get("min_duration") is not None
                        else p.get("min_months")
                    ),
                }
                for p in edu_paths(doc)
            ],
            # 项目侧就读时长门槛（月，已折算）。None 且 duration_required 为真
            # = 「有要求、无数字」→ 判 edu_duration_unknown（silent）。
            "min_duration_months": edu_min_duration_months(doc),
            "duration_required": edu_duration_required(doc),
            # note 另写的「须在申请日前 N 年内完成学业」毕业时限（P2-0）。
            # 与 years_required 是两件事：那条说读了几年，这条说什么时候毕业。
            "recency_required": edu_recency_years(doc),
            # 原文把资格写成「须属于某几类参与人身份之一」（P2-0）。结构化只有
            # 学历层级，画像也只有学历层级——两处都表达不了身份类别。
            "category_required": participant_category_required(doc),
            # 原文把「资格须被主管机构认定 + 积分达 N 分」写成硬门槛（P2-0）。
            # 结构化只记了层级，认定结果与积分总分都没有字段可放。
            "credential_required": (
                "学历或职业资格须被主管机构认定"
                + (f"，且积分达到 {points_threshold(doc)} 分" if points_threshold(doc) else "")
                if credential_recognition_required(doc)
                else None
            ),
            # 学位须在指定国家/名单内院校完成（§4-3/§4-4/§4-6）：结构化只有层级。
            "place_constrained": bool(EDU_PLACE.search(edu.get("note") or "")),
            # 结构化字段比 note 严：以 note 为准（§4-5）。
            # P3 起不再用 EDU_RANK 判「结构化字段是否真的写了一个层级」——
            # 判定路径不许消费总序。改为问 edu_paths()：路径里有没有任何一条
            # 声明了非 any 的层级。这既覆盖老项目（合成路径来自 minimum_level），
            # 也覆盖新项目（层级写在 paths[i].level 里）。
            "by_sponsor": bool(
                any(
                    (p.get("level") or "any") != "any"
                    for p in edu_paths(doc)
                )
                and EDU_BY_SPONSOR.search(edu.get("note") or "")
            ),
        },
        "language": {
            "required": lang.get("required") is True,
            "ielts_min": ielts[0] if ielts else None,
            # 两个「不设分数线」的判据分开存，不合成一个布尔：by_design 是
            # 「官方明说不设」，cefr 是「官方给了档位但仓内没折算表」，前者
            # 判 na（不挡人）、后者判 silent（不可判），合并会把后者误放行。
            "by_design": bool(LANG_BY_DESIGN.search(lang_note)),
            "cefr": bool(LANG_CEFR_LADDER.search(lang_note)),
            # 第三个也是 na 但原因不同：官方不要求任何标准化考试（test=none
            # 哨兵或 note 明写「无需雅思/托福」）。前端按它判 lang_no_test，
            # 不再落到「要求语言但没登记分数线」的 silent。
            "no_test": no_test,
        },
        "funds": {
            "required": funds.get("required") is True,
            "cny_estimate": cny if isinstance(cny, (int, float)) else None,
            "by_design": bool(FUNDS_NO_FIXED.search(funds_note)),
            # 门槛是「年收入」而非存款：前端不能拿可动用资金与之相减
            "income_basis": bool(
                FUNDS_INCOME.search((amount.get("note") or "") + " " + funds_note)
            ),
            # 月额门槛：前端必须乘月数再比，不知道月数就判不可判（§4-1）
            "monthly": monthly,
            "months": months,
            # 金额被标注为「按同类口径沿用 / 归类推定」：不作达标判断
            "amount_inferred": bool(
                FUNDS_INFERRED.search(EXCHANGE_DISCLAIMER.sub("", amount_note + " " + funds_note))
            ),
        },
        # 前置身份 / 在地要求（§4-3、P1c）。`kinds` 取值与 Python judge() 的
        # precondition 分支一一对应：local_status / inside / outside /
        # home_residence / citizenship / document / unclassified，无要求时为空数组。
        #
        # 为什么是数组而不是单值：身份族与在地族各自独立出结论，一个项目可以同时
        # 有两者（us-f1-opt）。单值时前端只能画一条，且第二条要么被吞掉、要么得
        # 靠借别条的 code 发声——那正是本单拆掉的错。
        # `kind` 保留单值形状（取第一项），因为 p21_worksheets 与历史断言仍按单值读；
        # 前端按 `kinds` 判，不按 `kind` 判。
        "precondition": {
            "kind": precondition_kind(doc),
            "kinds": precondition_kinds(doc),
            # 原文要求「岗位须预先落实」（P2-0）。与 kind 分开存：job_placement 是
            # 材料/流程前提，不是身份类别，两者可以同时成立（camp counselor 就是）。
            "job_placement": job_placement_required(doc),
            # P4 §3：四种表述之一（camp / sponsor_ds2019 / summer_job / ds7002），
            # 前端按它取 need 文案。null 表示「有要求但四种都不像」——测试当场红。
            "job_placement_flavor": job_placement_flavor(doc),
            # P4 §2：government_support_letter 的语义分型（sponsorship /
            # official_registration / credential_check / institutional_recommendation /
            # government_letter / unclassified）+ 是否必填。type 名不表示同一种东西，
            # 前端与审计都按 kind 读，不按 type 名猜。
            "government_support_letter": _gsl_flag(doc),
            # 原文要求「具体雇主的合格聘用」（P2-0 no-skilled-worker）：雇主担保
            # 类项目的 offer 前置，与上一条互斥（命中集合不重叠）。
            "employer_offer": employer_offer_required(doc),
            # P1b-2：家属 / 签证史 / 学籍三个家族的 typed 值。
            #
            # 这里只放**项目侧的布尔量**（原文有没有要求）。画像侧的取值
            # （dependents / prior_participation / ...）由前端从它自己持有的
            # 画像对象里读，不写进 flags——flags 是「项目数据」，样本画像是
            # 「用户输入」，两者混在一个文件里会让每一份用户画像都要重生成产物。
            #
            # 前端 verdict.ts 的 p1b2 块按这些布尔 + 自己的画像逐条重演，两条
            # 路径的 (dim,kind,code) 由 smoke-test 逐条比对。
            "p1b2": p1b2_project_flags(doc),
        },
        "window": {
            "type": sch.get("type"),
            "status": sch.get("status"),
            "confidence": sch.get("date_confidence"),
            "open": sch.get("open_date"),
            "close": sch.get("close_date"),
        },
    }


def p1b2_project_flags(doc: dict) -> dict:
    """项目侧的 P1b-2 布尔量：原文对每个家族有没有提出要求。

    只回答「这个项目有没有这一条」，不回答「这个人满不满足」——后者要画像，
    由前端拿它自己的画像在这组布尔上重演（见 verdict.ts 的 p1b2 块）。
    """
    need = requirement_types(doc, required_only=True)
    anyv = requirement_types(doc, required_only=False)
    return {
        # 家属
        "forbid_child": DEP_FORBID_CHILD in need,
        "forbid_other": DEP_FORBID_OTHER in need,
        "cannot_work": DEP_CANNOT_WORK in need,
        "separate": DEP_SEPARATE in need,
        "allowed": DEP_ALLOWED in anyv,
        "declaration": DECLARATION_ONLY in anyv,
        # 签证史 / 参加史
        "participation": bool(
            need & {HIST_ONCE_LIFETIME, HIST_ONCE_PER_PROJECT, HIST_PARTICIPATION_CAP}
        ),
        "same_category_visa": HIST_SAME_CATEGORY_VISA in need,
        "specific_visa_required": HIST_SPECIFIC_VISA_REQUIRED in need,
        # 学籍 / 学历
        "enrollment": ENROLL_ENROLLED in need,
        "degree_completed": ENROLL_DEGREE in need,
        "either": ENROLL_EITHER in need,
        "scoring_input": SCORING_INPUT in anyv,
        # —— 本单：这条项目读哪些画像字段（用于表单的条件显示）——
        #
        # 上方那些布尔量是**为什么**读（语义），这一项是**读不读**（事实）。
        # 前端只读这一项，不按上方布尔自己推：同一条规则写两遍必然漂，
        # 而「门悄悄关掉」在界面上看起来完全正常。
        "reads": profile_readers(doc),
    }


def build_flags() -> dict:
    docs = load_programs()
    return {
        "rules_version": RULES_VERSION,
        "total": len(docs),
        "programs": {doc["program"]["id"]: flags_of(doc) for doc in docs},
    }


def build_samples() -> dict:
    """三样例画像的逐项目结论。dims 只留 (dim, kind, code)。"""
    docs = load_programs()
    out = {}
    for doc in docs:
        per = {}
        for name, pr in SAMPLES.items():
            state, dims = judge(doc, pr)
            per[name] = {
                "state": state,
                "dims": [
                    {"dim": d["dim"], "kind": d["kind"], "code": d["code"]} for d in dims
                ],
            }
        out[doc["program"]["id"]] = per
    return {
        "rules_version": RULES_VERSION,
        "samples": SAMPLES,
        "verdicts": out,
    }


def _dump(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=False) + "\n"


def write_artifacts() -> list[str]:
    payloads = [(FLAGS, _dump(build_flags())), (SAMPLES_OUT, _dump(build_samples()))]
    written = []
    for path, text in payloads:
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        written.append(os.path.relpath(path, ROOT).replace("\\", "/"))
    return written


def check_artifacts() -> int:
    payloads = [(FLAGS, _dump(build_flags())), (SAMPLES_OUT, _dump(build_samples()))]
    stale = []
    for path, text in payloads:
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        if not os.path.isfile(path):
            stale.append("%s 不存在" % rel)
            continue
        with io.open(path, encoding="utf-8") as fh:
            cur = fh.read()
        if cur != text:
            stale.append("%s 与数据不一致" % rel)
    if stale:
        print("FAIL 前端契约产物过期，请运行 python scripts/match_readiness.py --emit")
        for s in stale:
            print("  - %s" % s)
        return 1
    print(
        "OK data/match-flags.json 与 data/match-samples.json 与数据一致（rules_version %d）"
        % RULES_VERSION
    )
    return 0


# --------------------------------------------------------------------------
# 报告
# --------------------------------------------------------------------------


def audit() -> dict:
    docs = load_programs()
    rows = []
    dim_counter: dict[str, Counter] = {k: Counter() for k in PROBES}
    # 甲类白名单里、但数据拿不出证据的豁免（应为空）。非空即说明有人拿
    # 「没去查」冒充「设计性不可判」——那是数据债，必须单独列出来报，不许
    # 顺手改数据洗掉（Muse 裁决 1）。
    unproven_exemptions = []

    for doc in docs:
        pid = doc["program"]["id"]
        cells = OrderedDict()
        for dim, probe in PROBES.items():
            if dim == "passport":
                # 三个护照分别探；项目级取最差（absent > text > partial > ok）
                per = {k: probe_passport(doc, k) for k in PASSPORTS}
                order = {"ok": 0, "na": 0, "partial": 1, "text": 2, "absent": 3}
                worst = max(per.values(), key=lambda x: order[x[0]])
                cells[dim] = {
                    "status": worst[0],
                    "reason": worst[1],
                    "evidence": worst[2],
                    "per_passport": {k: {"status": v[0], "reason": v[1]} for k, v in per.items()},
                }
            else:
                st, reason, ev = probe(doc)
                cells[dim] = {"status": st, "reason": reason, "evidence": ev}
            dim_counter[dim][cells[dim]["status"]] += 1

        verdicts = OrderedDict()
        for name, pr in SAMPLES.items():
            state, dims = judge(doc, pr)
            verdicts[name] = {
                "state": state,
                "dims": dims,
                # 甲 / 乙 / None —— 只有 unknown 的项才有类
                "cls": undecidable_class(dims, doc) if state == "unknown" else None,
            }
            if state == "unknown":
                for d in dims:
                    if (
                        d["kind"] == "silent"
                        and d["code"] in BY_DESIGN_CODES
                        and not design_exemption_holds(d["code"], doc)
                    ):
                        unproven_exemptions.append("%s/%s/%s" % (pid, name, d["code"]))
        rows.append({"id": pid, "name": doc["program"]["name"], "cells": cells, "verdicts": verdicts})

    per_sample = OrderedDict()
    for name in SAMPLES:
        c = Counter(r["verdicts"][name]["state"] for r in rows)
        cls = Counter(r["verdicts"][name]["cls"] for r in rows)
        undecidable = c["unknown"]
        per_sample[name] = {
            "can": c["can"],
            "cannot": c["cannot"],
            "gap": c["gap"],
            "unknown": undecidable,
            "unknown_ratio": round(undecidable / len(rows), 4),
            # 甲：设计性不可判（补字段也判不了，见 BY_DESIGN_CODES）
            "unknown_by_design": cls["design"],
            "by_design_ratio": round(cls["design"] / len(rows), 4),
            # 乙：可避免不可判 —— 停工线只看这一列
            "unknown_class_b": cls["avoidable"],
            "ratio_class_b": round(cls["avoidable"] / len(rows), 4),
            # 加总自检：甲 + 乙 必须等于 unknown，任何一类漏登记都会在这里露馅
            "class_b_ids": sorted(
                r["id"] for r in rows if r["verdicts"][name]["cls"] == "avoidable"
            ),
            "by_design_ids": sorted(
                r["id"] for r in rows if r["verdicts"][name]["cls"] == "design"
            ),
        }

    any_gap = 0
    for r in rows:
        bad = [d for d, c in r["cells"].items() if c["status"] in ("absent", "partial")]
        r["gaps"] = bad
        if bad:
            any_gap += 1

    # 真实用户口径（裁决第二条）：同一个引擎、同一份数据，只换画像定义域。
    # 这一份是停工线的判据；上面那份（夹具）降为回归参照。
    real_per_sample = measure_caliber(docs, {k: real_profile(v) for k, v in SAMPLES.items()})

    return {
        "total": len(rows),
        "rows": rows,
        "dimension_counts": {k: dict(v) for k, v in dim_counter.items()},
        "programs_with_gap": any_gap,
        "program_gap_ratio": round(any_gap / len(rows), 4),
        "samples": per_sample,
        # 全口径（甲+乙混算）：保留输出，但**不是闸门**，只作历史可比与防洗白。
        "max_unknown_ratio": max(v["unknown_ratio"] for v in per_sample.values()),
        # 乙类全口径：夹具口径（回归参照，不再是闸门判据）
        "max_ratio_class_b": max(v["ratio_class_b"] for v in per_sample.values()),
        # 甲类全口径：软线，报警但不变红
        "max_by_design_count": max(v["unknown_by_design"] for v in per_sample.values()),
        "max_by_design_ratio": max(v["by_design_ratio"] for v in per_sample.values()),
        "stop_line_ratio": STOP_LINE_RATIO,
        "by_design_alert_count": BY_DESIGN_ALERT_COUNT,
        # 白名单里但证据不成立的豁免（应为空；非空是数据债，见 audit() 注释）
        "design_exemptions_missing": unproven_exemptions,
        # —— 双口径（2026-11-20 裁决）——
        # real_samples 是停工线判据；samples 是夹具回归参照。
        "real_samples": real_per_sample,
        "stop_line_caliber": STOP_LINE_CALIBER,
        # 闸门口径下的最高乙类占比与对应画像（停工判定只看这两个值）
        "gate_ratio_class_b": max(v["ratio_class_b"] for v in real_per_sample.values()),
        "gate_worst_sample": max(real_per_sample, key=lambda k: real_per_sample[k]["ratio_class_b"]),
        "real_class_b_debt_ceiling": REAL_CLASS_B_DEBT_CEILING,
        "real_class_b_excess": max(
            0, max(v["unknown_class_b"] for v in real_per_sample.values()) - REAL_CLASS_B_DEBT_CEILING
        ),
        "form_fields": list(FORM_FIELDS),
        "real_nulled_fields": list(REAL_PROFILE_NULLED_FIELDS),
    }


MARK = {"ok": "在位", "partial": "语义不足", "text": "可从文本提取", "absent": "缺失", "na": "不适用"}
STATE_ZH = {"can": "能申", "cannot": "不能申", "gap": "差什么", "unknown": "不可判"}
CLASS_ZH = {"design": "甲", "avoidable": "乙"}


def ratio_text(x: float) -> str:
    """把 1/3 这类阈值显示成它本来的样子，而不是像 33.3% 那样被舍入过的文案。

    写死「33.3%」的后果是文案与常量各自漂移：改了阈值忘了改文案，报告会
    指着一条已经不在管事的线说「越线了」。所以阈值只从常量取，只在这一处
    做显示格式化。
    """
    for denom in (2, 3, 4, 5, 6, 8, 10):
        if abs(x * denom - round(x * denom)) < 1e-9:
            return "%d/%d" % (round(x * denom), denom)
    return "%.1f%%" % (x * 100)


def metric_line(rep: dict, name: str, caliber: str = "fixture") -> str:
    """三口径同行打印（P2-1 R6）。

    必须一直是**同一行**：分成三行贴出去，读者会挑最顺眼的那行引用；写在一行
    里，「闸门 1/3 只看乙类」这层关系就没法被断章取义。全口径标「仅记录」、
    甲类标「软线 N 项」，是为了让人一眼看出哪个数字会停工、哪个只是提醒。

    caliber：fixture = 夹具口径（13 字段，回归参照）；real = 真实用户口径
    （表单 6 字段，停工线判据）。两个口径都按同一格式打印，读者才能左右对比。
    """
    src = rep["real_samples"] if caliber == "real" else rep["samples"]
    v = src[name]
    tag = "真实口径" if caliber == "real" else "夹具口径"
    return (
        "%s 乙类 %.1f%%（闸门 %s）｜全口径 %.1f%%（仅记录）｜甲类 %d 项（软线 %d）"
        % (
            tag,
            v["ratio_class_b"] * 100,
            ratio_text(rep["stop_line_ratio"]),
            v["unknown"] / rep["total"] * 100,
            v["unknown_by_design"],
            rep["by_design_alert_count"],
        )
    )


# 缺口处置建议：按维度给，写在这里而不是逐项目手写，是为了新增项目时
# 报告自动带上建议，不会出现「新项目列进缺口表却没有处置口径」。
ADVICE = {
    "language": "该条要求语言证明但仓内无分数线：M2 界面判为「需自行核对官网」，不显示虚假的分数达标；补数据需人工回官网登记分数线。",
    "passport": "该护照资格未登记且 note 无结论：M2 判「不可判」，不许默认放行。补数据需查该地区双边文件。",
    "age": "官方未公布年龄限制：M2 判「不可判」，不按 0–99 当无限制，也不当超龄。",
    "funds": "要求资金证明但无金额：M2 判「不可判」，不与预算比对。",
    "window": "日期未公布或仅有推算：追踪清单显示「下一轮未公布／参考日期（未确认）」，绝不显示为官方日期。",
    "education": "学历字段齐全，无需处理。",
}

# (维度, 状态, 数量, 可否提取, 建议) —— 数量在 render 时按实际统计填
ADVICE_TABLE_LABEL = [
    ("language", "absent", "不可直接提取：官方页有分数线但仓库未逐项登记，需人工回官网补录"),
    ("funds", "absent", "不可提取：官方未给固定金额，任何数字都属编造"),
    ("passport", "absent", "不可提取：note 未给结论，需查双边文件"),
    ("age", "partial", "不可提取：官方明说未公布"),
    ("window", "partial", "部分可提取：inferred 类有推算日期，但按仓库纪律不得当官方日期展示"),
    ("passport", "text", "可提取：note 明文「官方未按国籍设限」，M2 按此判可申并标注为推断"),
    ("language", "text", "可提取：官方用 CEFR/CLB 档位，需官方对照表折算"),
]


def render_markdown(rep: dict) -> str:
    L = []
    L.append("# 画像匹配数据就绪审计（M1）")
    L.append("")
    L.append("> 本文由 `python scripts/match_readiness.py --write` 生成，不要手工编辑。")
    L.append("> 生成日期：2026-11-12 ｜ 数据：`data/programs/*.json` 共 %d 个项目" % rep["total"])
    L.append("")
    L.append("## 1. 结论")
    L.append("")
    L.append(
        "- **字段级**：%d/%d 个项目（%.1f%%）至少有一个维度不是「结构化可直接判」。"
        % (rep["programs_with_gap"], rep["total"], rep["program_gap_ratio"] * 100)
    )
    L.append(
        "- **项目级不可判率**（三样例画像，全口径 = 甲 + 乙）：A %.1f%% / B %.1f%% / C %.1f%%。"
        % tuple(
            rep["samples"][k]["unknown_ratio"] * 100 for k in ("A", "B", "C")
        )
    )
    worst = rep["gate_worst_sample"]
    gate_ratio = rep["gate_ratio_class_b"]
    L.append(
        "- **停工线只看乙类（可避免不可判），阈值 %s 一个数字未动**。判据口径 = **真实用户画像**"
        "（表单 6 字段 + 其余 %d 字段置 null，见裁决 2026-11-20）。实测最高为画像 %s 的"
        " %.1f%%（%d/%d，门槛 %d 条）；**%s**。全口径与甲类数字见下表，它们不参与停工判定。"
        % (
            ratio_text(rep["stop_line_ratio"]),
            len(rep["real_nulled_fields"]),
            worst,
            gate_ratio * 100,
            rep["real_samples"][worst]["unknown_class_b"],
            rep["total"],
            int(rep["total"] * rep["stop_line_ratio"]),
            "已越过停工线，记为在案债务（成因 = 表单采集面未跟上判定面），须降不许升"
            if gate_ratio > rep["stop_line_ratio"]
            else "未越过停工线，可继续",
        )
    )
    L.append(
        "- **夹具口径（13 字段）降为回归参照**：实测最高 %.1f%%（%s）。它不再决定停工，"
        "但仍在报告里，用来分辨「引擎变差」与「画像变瘦」。"
        % (
            rep["max_ratio_class_b"] * 100,
            "；".join(
                "%s %.1f%%" % (k, v["ratio_class_b"] * 100) for k, v in rep["samples"].items()
            ),
        )
    )
    L.append(
        "- 甲类软线 %d 项：实测最高 %d 项；%s。甲类只要求人工解释，不使 CI 变红。"
        % (
            rep["by_design_alert_count"],
            rep["max_by_design_count"],
            "**已触及软线，须在报告里解释甲类构成**"
            if rep["max_by_design_count"] >= rep["by_design_alert_count"]
            else "未触及软线",
        )
    )
    L.append("")
    L.append(
        "> **闸门只看乙类。** 甲类 = 补字段也判不了（原文交由 Sponsor 等第三方主体判断、"
        "或官方根本无阈值）；乙类 = 数据/画像补上就能判的债。混算口径继续输出，但只许不增。"
    )
    if rep["design_exemptions_missing"]:
        L.append("")
        L.append(
            "> ⚠️ 以下甲类豁免拿不出证据（按乙类计，属数据债）：%s"
            % "、".join(rep["design_exemptions_missing"])
        )
    L.append("")
    L.append("### 各维度状态分布")
    L.append("")
    L.append("| 维度 | " + " | ".join(MARK.values()) + " |")
    L.append("|---|" + "---|" * len(MARK))
    for dim, cnt in rep["dimension_counts"].items():
        L.append(
            "| %s | %s |"
            % (dim, " | ".join(str(cnt.get(k, 0)) for k in MARK))
        )
    L.append("")
    L.append("## 2. 三样例画像的判定分布")
    L.append("")
    L.append("| 画像 | 能申 | 不能申 | 差什么 | 不可判 | 全口径占比 | 乙类（%s 闸门） | 乙类占比 | 甲类 | 甲类占比 |"
             % ratio_text(rep["stop_line_ratio"]))
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for k, v in rep["samples"].items():
        L.append(
            "| %s | %d | %d | %d | %d | %.1f%% | %d | %.1f%% | %d | %.1f%% |"
            % (
                k,
                v["can"],
                v["cannot"],
                v["gap"],
                v["unknown"],
                v["unknown_ratio"] * 100,
                v["unknown_class_b"],
                v["ratio_class_b"] * 100,
                v["unknown_by_design"],
                v["by_design_ratio"] * 100,
            )
        )
    L.append("")
    L.append("三口径同行（闸门只看乙类）：")
    L.append("")
    for k in ("A", "B", "C"):
        L.append("- 画像 %s：%s" % (k, metric_line(rep, k, "real")))
    L.append("")
    L.append("### 2.1 双口径对照（真实口径 = 闸门判据｜夹具口径 = 回归参照）")
    L.append("")
    L.append("| 画像 | 真实口径乙类 | 真实占比 | 夹具口径乙类 | 夹具占比 | 差（真实 − 夹具） |")
    L.append("|---|---|---|---|---|---|")
    for k in ("A", "B", "C"):
        r_, f_ = rep["real_samples"][k], rep["samples"][k]
        L.append(
            "| %s | %d | %.1f%% | %d | %.1f%% | %+d |"
            % (
                k,
                r_["unknown_class_b"],
                r_["ratio_class_b"] * 100,
                f_["unknown_class_b"],
                f_["ratio_class_b"] * 100,
                r_["unknown_class_b"] - f_["unknown_class_b"],
            )
        )
    L.append("")
    L.append(
        "> 真实口径 = 表单能采集的 %s（%d 项，含条件显示的补充字段）；"
        "夹具多带的 %s 在表单补齐前无输入口，那一版口径见 LEGACY_FORM_FIELDS。"
        "两列现在相同，说明采集面已追上判定面（collection_gap 为空）；"
        "不同则差额即「用户没被问到的事实」造成的不可判，不是引擎退化。"
        % (
            "、".join(rep["form_fields"]),
            len(rep["form_fields"]),
            "、".join(rep["real_nulled_fields"]),
        )
    )
    L.append("")
    L.append("## 3. 逐项目缺口表")
    L.append("")
    cols = ["passport", "age", "education", "language", "funds", "window"]
    L.append("| 项目 id | " + " | ".join(cols) + " | 画像 A/B/C | 不可判归类 A/B/C |")
    L.append("|---|" + "---|" * (len(cols) + 2))
    for r in rep["rows"]:
        cells = " | ".join(
            "%s%s" % (MARK[r["cells"][c]["status"]], "" if r["cells"][c]["status"] in ("ok", "na") else "⚠")
            for c in cols
        )
        vs = "/".join(STATE_ZH[r["verdicts"][k]["state"]] for k in ("A", "B", "C"))
        cls = "/".join(CLASS_ZH.get(r["verdicts"][k]["cls"], "—") for k in ("A", "B", "C"))
        L.append("| `%s` | %s | %s | %s |" % (r["id"], cells, vs, cls))
    L.append("")
    L.append("## 4. 缺口明细（缺什么、能不能从已有文本提取）")
    L.append("")
    for r in rep["rows"]:
        bad = [c for c in cols if r["cells"][c]["status"] in ("absent", "partial")]
        if not bad:
            continue
        L.append("### `%s` — %s" % (r["id"], r["name"]))
        L.append("")
        for c in bad:
            cell = r["cells"][c]
            L.append(
                "- **%s**（%s）：%s%s"
                % (
                    c,
                    MARK[cell["status"]],
                    cell["reason"],
                    ("｜证据：%s" % cell["evidence"]) if cell.get("evidence") else "",
                )
            )
            advice = ADVICE.get(c)
            if advice:
                L.append("  - 处置：%s" % advice)
        L.append("")
    L.append("## 5. 缺口处置建议（逐类）")
    L.append("")
    L.append("| 维度 / 状态 | 数量 | 能否从已有文本可靠提取 |")
    L.append("|---|---|---|")
    counts = rep["dimension_counts"]
    for dim, status, note in ADVICE_TABLE_LABEL:
        n = counts.get(dim, {}).get(status, 0)
        if n:
            L.append("| %s / %s | %d | %s |" % (dim, status, n, note))
    L.append("")
    L.append("## 6. 判定模型的关键取舍（为什么不是全部标不可判）")
    L.append("")
    L.append(
        "本审计对「不可判」采取**不对称**口径，方向不同结果不同，这不是漏洞而是刻意的："
    )
    L.append("")
    L.append(
        "1. **用户没填语言成绩 + 项目要求语言** → 判「差什么」。这是确定的事实"
        "（你没这项证明），不依赖仓内有没有登记分数线。"
    )
    L.append(
        "2. **用户填了语言成绩 + 项目没登记分数线** → 判「不可判」。此时说够或不够"
        "都是替官方担保，只能请用户去详情页核对。"
    )
    L.append(
        "3. **官方不设可比门槛**（不设分数线 / 资金证明无固定金额 / 无年龄限制）→ "
        "判「不适用」，不占不可判名额。这类条目递交时自证，不构成本人条件与门槛的差距。"
    )
    L.append("")
    L.append(
        "若把第 3 条也计入不可判，全口径会升到 A 22.0% / B 39.0% / C 43.9%；"
        "这类新增全是「口径/登记」债，按 P2-1 的分法会落进乙类，于是 B、C 将越过 "
        "1/3 停工线（甲类不占分子，救不了这条）。所以这条口径必须先讲清再谈结论 —— "
        "**若 Muse 认为「不设门槛」也应算作「不可判」，本单应停工等裁决**。"
    )
    L.append("")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="画像匹配数据就绪审计")
    ap.add_argument("--write", action="store_true", help="重写 docs/audit/ 下的审计文档")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument(
        "--emit",
        action="store_true",
        help="重写 data/match-flags.json 与 data/match-samples.json（前端契约产物）",
    )
    ap.add_argument("--check", action="store_true", help="校验前端契约产物是否与数据同步（CI）")
    args = ap.parse_args()

    if args.check:
        return check_artifacts()

    rep = audit()

    if args.json:
        json.dump(rep, sys.stdout, ensure_ascii=False, indent=1)
        sys.stdout.write("\n")
        return 0

    print("项目总数 %d，至少缺一维 %d（%.1f%%）" % (
        rep["total"], rep["programs_with_gap"], rep["program_gap_ratio"] * 100))
    for dim, cnt in rep["dimension_counts"].items():
        print("  %-10s %s" % (dim, " ".join("%s=%d" % (k, cnt.get(k, 0)) for k in MARK)))
    print("样例画像不可判占比（真实口径 = 闸门判据｜夹具口径 = 回归参照）：")
    for k in rep["samples"]:
        print(
            "  口径对照 %s：真实 %.1f%% / 夹具 %.1f%%（乙类 %d/%d vs %d/%d）"
            % (
                k,
                rep["real_samples"][k]["unknown"] / rep["total"] * 100,
                rep["samples"][k]["unknown_ratio"] * 100,
                rep["real_samples"][k]["unknown_class_b"],
                rep["total"],
                rep["samples"][k]["unknown_class_b"],
                rep["total"],
            )
        )
    for k in rep["samples"]:
        print("  %s  %s" % (k, metric_line(rep, k, "real")))
    for k in rep["samples"]:
        print("  %s  %s" % (k, metric_line(rep, k, "fixture")))
    print(
        "停工线 %s（只看乙类）：真实口径最高 %.1f%%（画像 %s），夹具口径最高 %.1f%%（回归参照，不判停）"
        "｜最高甲类 %d 项（软线 %d）"
        % (
            ratio_text(rep["stop_line_ratio"]),
            rep["gate_ratio_class_b"] * 100,
            rep["gate_worst_sample"],
            rep["max_ratio_class_b"] * 100,
            rep["max_by_design_count"],
            rep["by_design_alert_count"],
        )
    )
    if rep["gate_ratio_class_b"] > rep["stop_line_ratio"]:
        print(
            "  停工：真实口径乙类 %d/%d 已越过 %s（在案债务上限 %d 条），须降不许升；"
            "新增越线须停工报 Muse 裁决"
            % (
                rep["real_samples"][rep["gate_worst_sample"]]["unknown_class_b"],
                rep["total"],
                ratio_text(rep["stop_line_ratio"]),
                rep["real_class_b_debt_ceiling"],
            )
        )
    if rep["real_class_b_excess"] > 0:
        print(
            "  债务上升：真实口径乙类已破在案上限 %d 条（超出 %d 条），须先解释新增哪几条"
            % (rep["real_class_b_debt_ceiling"], rep["real_class_b_excess"])
        )
    if rep["max_by_design_count"] >= rep["by_design_alert_count"]:
        print("  报警：甲类已达软线 %d 项，须在报告里解释甲类构成（不使 CI 变红）"
              % rep["by_design_alert_count"])
    if rep["design_exemptions_missing"]:
        print("  数据债：以下甲类豁免拿不出证据，已按乙类计 —— %s"
              % "、".join(rep["design_exemptions_missing"]))

    if args.write:
        os.makedirs(os.path.dirname(DOC), exist_ok=True)
        with io.open(DOC, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(render_markdown(rep))
        print("已写入 %s" % os.path.relpath(DOC, ROOT))

    if args.emit:
        for rel in write_artifacts():
            print("已写入 %s" % rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
