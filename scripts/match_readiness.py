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
    need = EDU_RANK.get(edu.get("minimum_level") or "any", 0)
    have = EDU_RANK.get(pr["education"], 0)
    if have < need:
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
    elif edu.get("years_completed") and pr["education"] == "bachelor_in_progress":
        dims.append(
            {
                "dim": "education",
                "kind": "silent",
                "code": "edu_years_unknown",
                "why": f"另要求已完成 {edu['years_completed']} 年本科，在读无法从他填的信息判定",
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
        income_based = bool(FUNDS_INCOME.search((amount.get("note") or "") + " " + note))
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

RULES_VERSION = 3


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
        },
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
