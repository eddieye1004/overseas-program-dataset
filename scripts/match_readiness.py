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

EDU_RANK = {
    "high_school": 1,
    "vocational": 2,
    "bachelor_in_progress": 3,
    "bachelor_completed": 4,
    "master": 5,
    "any": 0,
}

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

# 前置身份：这类项目只对「已经在该国持学生/居留身份（并在当地完成学业）」的人
# 开放，不是一张面向所有人开放的表。§4-3 / §4-4 的全部偏差都来自这一条从未
# 进入判定。三类分开处理，因为「能不能补」不一样：
#   local_status   须先在该国持学生签/居留（或在当地完成学业）→ 判 gap（差这一项前提）
#   outside        递交时人须在该国境外 → 画像不采集所在地，判 silent
#   home_residence 须常驻护照所属地区 → 画像不采集现居地，判 silent
PRE_LOCAL_STATUS = re.compile(
    r"须已持|须持[^。；]{0,30}(?:学习居留|学生居留|学生许可|学生签证|Stamp\s*2|F-1|居留许可)|"
    # 「人在法国——须持 carte de séjour étudiant」这类两路径写法：原文是外语
    # 证件名，中文正则抓不到，会整条落空。§4-3 要的是「读得到」，不是「读得准
    # 一处」，所以把常见的外语学生证件名也收进来。
    r"(?:必须|须)持[^。；]{0,20}(?:carte de séjour|séjour étudiant|student pass|study permit|"
    r"residence permit|居留许可|长期学习居留)|"
    r"曾持[^。；]{0,24}(?:居留|许可|签证)|"
    r"在此身份下完成学业|并在此身份下|"
    r"(?:必须|须)在[^。；]{0,6}(?:境内|国内)"
)
PRE_OUTSIDE = re.compile(r"(?:必须|须)在[^。；]{0,10}境外|人在[^。；]{0,8}境外")
PRE_HOME_RESIDENCE = re.compile(r"居住于其国籍国|须居住且常驻|常驻其护照|常驻中国|居住且常驻")

# 其余两类 required: true 的 residency_requirement —— 都不构成「身份前置」：
#   citizenship  原文说的是「须为参与国公民」。那是护照条件，passport 维已经在判，
#                这里再报一条就是同一个缺口说两遍。
#   document     原文说的是「须持有效租约 / 购房合同」。这是递交时自行取得的文件，
#                不是「你得先在该国读过书」，不构成可判的身份门槛。
# 分开登记（而不是笼统落 None）是为了让「全库顺查」的结果里，每一条 required
# 的 residency_requirement 都能指到处置理由，而不是一片无法区分的空白。
PRE_CITIZENSHIP = re.compile(r"参与国公民|协议国公民|须为[^。；]{0,12}国民")
PRE_DOCUMENT = re.compile(r"租房或购房合同|租赁合同|租房合同|购房合同|租约")


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
    """note 里另写的硬性年限门槛（结构化 `years_completed` 缺失时用）。"""
    edu = (doc.get("eligibility") or {}).get("education") or {}
    note = edu.get("note") or ""
    m = EDU_YEARS_STRICT.search(note)
    if not m or not EDU_YEARS_DISQUALIFY.search(note):
        return None
    years = cn_int(m.group(1))
    if years and years >= 3:
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


def precondition_kind(doc: dict) -> str | None:
    """从 `other_requirements` 里读出「前置身份/在地」类要求，返回处置类别。

    只看 `required: true` 且 `type: residency_requirement` 的条目：这类条件在
    原文里写得很清楚（「须在英国以学生签证完成课程」「递交时人必须在英国境内」），
    但结构化字段里没有对应项，过去一个字节都没读（§4-3）。
    """
    reqs = (doc.get("eligibility") or {}).get("other_requirements") or []
    notes = [
        r.get("note") or ""
        for r in reqs
        if r.get("required") is True and r.get("type") == "residency_requirement"
    ]
    if not notes:
        return None
    joined = " ".join(notes)
    if PRE_LOCAL_STATUS.search(joined):
        return "local_status"
    if PRE_OUTSIDE.search(joined):
        return "outside"
    if PRE_HOME_RESIDENCE.search(joined):
        return "home_residence"
    if PRE_CITIZENSHIP.search(joined):
        return "citizenship"
    if PRE_DOCUMENT.search(joined):
        return "document"
    # 读不懂就是读不懂：返回 "unclassified" 而不是 None，这样「全库顺查」能把它
    # 单独列出来。落 None 会让「没有前置要求」和「有要求但我们没读懂」长得一样，
    # 而后者正是 §4-3 那个错误的成因。
    return "unclassified"


def precondition_text(doc: dict) -> str:
    """报告用：前置条件原文首句（只截取，不改写）。"""
    reqs = (doc.get("eligibility") or {}).get("other_requirements") or []
    for r in reqs:
        if r.get("required") is True and r.get("type") == "residency_requirement":
            return (r.get("note") or "").strip()[:120]
    return ""


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
            },
        ),
    ]
)


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

    # 学历
    edu = (doc.get("eligibility") or {}).get("education") or {}
    edu_note = edu.get("note") or ""
    need = EDU_RANK.get(edu.get("minimum_level") or "any", 0)
    have = EDU_RANK.get(pr["education"], 0)
    years_need = edu_years_required(doc)
    recency_need = edu_recency_years(doc)
    if need and EDU_BY_SPONSOR.search(edu_note):
        # 结构化的 minimum_level 比 note 更严：note 明说法规没规定学位层级、
        # 由 Sponsor 判断。这时拿结构化字段判 fail 是替官方拒绝（§4-5）。
        dims.append(
            {
                "dim": "education",
                "kind": "silent",
                "code": "edu_by_sponsor",
                "why": "结构化字段记了最低学位，但原文写明「法规未规定学位层级、由 Sponsor 判断」，以原文为准",
            }
        )
    elif have < need:
        dims.append(
            {
                "dim": "education",
                "kind": "fail",
                "code": "edu_low",
                "need": edu.get("minimum_level"),
                "have": pr["education"],
                "why": f"学历门槛 {edu.get('minimum_level')}",
            }
        )
    elif years_need:
        # note 另写「须完成不少于四年高等教育，三年制本科不满足」，而结构化
        # 字段只有层级、没有学制年数（§4-2）。画像也不采集学制，所以只要
        # note 写了这条硬门槛，就不能默认「层级到了 = 达标」。
        #
        # 判 silent 而不是 fail：三年制本科确实不满足，但画像只知道「本科毕业」，
        # 不知道你读的是三年制还是四年制——替一个四年制的人判「不能申」同样是错。
        dims.append(
            {
                "dim": "education",
                "kind": "silent",
                "code": "edu_years_unknown",
                "need": f"已完成 {years_need} 年高等教育",
                "why": f"原文另要求完成不少于 {years_need} 年高等教育（学制短于该年限不满足），你的学制年数未采集",
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
    elif recency_need:
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

    # 前置身份 / 在地要求（§4-3、§4-4）
    #
    # 这一段过去不存在：judge() 只读五处结构化字段，`other_requirements` 一个字
    # 没读。于是「只对已在英留学生开放」的毕业生签证被判成「谁都能申」。
    # 现在按原文类别分三档，宁可不可判，也不静默判过。
    pre = precondition_kind(doc)
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
    elif pre == "outside":
        dims.append(
            {
                "dim": "precondition",
                "kind": "silent",
                "code": "pre_outside_country",
                "why": "原文要求在递交时人位于该国境外，画像不采集现居地，无法判定",
            }
        )
    elif pre == "home_residence":
        dims.append(
            {
                "dim": "precondition",
                "kind": "silent",
                "code": "pre_home_residence",
                "why": "原文要求常驻护照所属地区，画像不采集现居地，无法判定",
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
        # 有 required 的前置身份要求，但原文类别没认出来。**不能落 pass**：
        # §4-3 的错就是从这里来的。判 silent 并写明「有这条、我们没读懂」。
        dims.append(
            {
                "dim": "precondition",
                "kind": "silent",
                "code": "pre_unclassified",
                "why": "该项目有一条必填的前置身份/在地要求，原文类别未能识别，无法判定",
            }
        )

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
# --------------------------------------------------------------------------

RULES_VERSION = 5


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
            # note 另写的「须在申请日前 N 年内完成学业」毕业时限（P2-0）。
            # 与 years_required 是两件事：那条说读了几年，这条说什么时候毕业。
            "recency_required": edu_recency_years(doc),
            "place_constrained": bool(EDU_PLACE.search(edu.get("note") or "")),
            # 结构化字段比 note 严：以 note 为准（§4-5）。
            "by_sponsor": bool(
                EDU_RANK.get(edu.get("minimum_level") or "any", 0)
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
        # 前置身份 / 在地要求（§4-3）。`kind` 取值与 Python judge() 的
        # precondition 分支一一对应：local_status / outside / home_residence，
        # 无要求时为 null。
        "precondition": {"kind": precondition_kind(doc)},
        "window": {
            "type": sch.get("type"),
            "status": sch.get("status"),
            "confidence": sch.get("date_confidence"),
            "open": sch.get("open_date"),
            "close": sch.get("close_date"),
        },
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
            verdicts[name] = {"state": state, "dims": dims}
        rows.append({"id": pid, "name": doc["program"]["name"], "cells": cells, "verdicts": verdicts})

    per_sample = OrderedDict()
    for name in SAMPLES:
        c = Counter(r["verdicts"][name]["state"] for r in rows)
        per_sample[name] = {
            "can": c["can"],
            "cannot": c["cannot"],
            "gap": c["gap"],
            "unknown": c["unknown"],
            "unknown_ratio": round(c["unknown"] / len(rows), 4),
        }

    any_gap = 0
    for r in rows:
        bad = [d for d, c in r["cells"].items() if c["status"] in ("absent", "partial")]
        r["gaps"] = bad
        if bad:
            any_gap += 1

    return {
        "total": len(rows),
        "rows": rows,
        "dimension_counts": {k: dict(v) for k, v in dim_counter.items()},
        "programs_with_gap": any_gap,
        "program_gap_ratio": round(any_gap / len(rows), 4),
        "samples": per_sample,
        "max_unknown_ratio": max(v["unknown_ratio"] for v in per_sample.values()),
    }


MARK = {"ok": "在位", "partial": "语义不足", "text": "可从文本提取", "absent": "缺失", "na": "不适用"}
STATE_ZH = {"can": "能申", "cannot": "不能申", "gap": "差什么", "unknown": "不可判"}

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
        "- **项目级不可判率**（三样例画像）：A %.1f%% / B %.1f%% / C %.1f%%。"
        % tuple(
            rep["samples"][k]["unknown_ratio"] * 100 for k in ("A", "B", "C")
        )
    )
    worst = max(("A", "B", "C"), key=lambda k: rep["samples"][k]["unknown_ratio"])
    L.append(
        "- 派单的停工线是「超过 1/3 项目不可判」。实测最高为画像 %s 的 %.1f%%；"
        "**%s**。"
        % (
            worst,
            rep["samples"][worst]["unknown_ratio"] * 100,
            "已越过 1/3，须停工报 Muse 裁决"
            if rep["max_unknown_ratio"] > 1 / 3
            else "未越过 1/3，可继续 M2",
        )
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
    L.append("| 画像 | 能申 | 不能申 | 差什么 | 不可判 | 不可判占比 |")
    L.append("|---|---|---|---|---|---|")
    for k, v in rep["samples"].items():
        L.append(
            "| %s | %d | %d | %d | %d | %.1f%% |"
            % (k, v["can"], v["cannot"], v["gap"], v["unknown"], v["unknown_ratio"] * 100)
        )
    L.append("")
    L.append("## 3. 逐项目缺口表")
    L.append("")
    cols = ["passport", "age", "education", "language", "funds", "window"]
    L.append("| 项目 id | " + " | ".join(cols) + " | 画像 A/B/C |")
    L.append("|---|" + "---|" * (len(cols) + 1))
    for r in rep["rows"]:
        cells = " | ".join(
            "%s%s" % (MARK[r["cells"][c]["status"]], "" if r["cells"][c]["status"] in ("ok", "na") else "⚠")
            for c in cols
        )
        vs = "/".join(STATE_ZH[r["verdicts"][k]["state"]] for k in ("A", "B", "C"))
        L.append("| `%s` | %s | %s |" % (r["id"], cells, vs))
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
        "若把第 3 条也计入不可判，三样例的不可判率会升到 A 22.0% / B 39.0% / C 43.9%，"
        "其中 B、C 越过 1/3 停工线。所以这条口径必须先讲清再谈结论 —— "
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
    print("样例画像不可判占比：", " ".join(
        "%s=%.1f%%" % (k, v["unknown_ratio"] * 100) for k, v in rep["samples"].items()))
    print("最高不可判占比 %.1f%%（停工线 33.3%%）" % (rep["max_unknown_ratio"] * 100))

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
