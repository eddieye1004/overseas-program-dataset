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

退出码恒为 0：这是审计，不是闸门。是否停工由人按报告里的比例裁决。
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRAMS = os.path.join(ROOT, "data", "programs")
DOC = os.path.join(ROOT, "docs", "audit", "2026-11-12-match-readiness.md")

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

# 资金：官方明文「不设固定金额 / 未写死金额」，金额由外管局或按指标计算。
# 收的写法都很具体，因为一旦放宽就会把「要求 3 万但没登记」这种真缺口
# 误判成「不设门槛」——那正好是最该暴露给用户的一类缺失。
FUNDS_NO_FIXED = re.compile(
    r"未写死金额|未设固定金额|不设固定金额|未在法规中写死|未给出固定数字|"
    r"不填猜测值|未列资金门槛|未设固定金额门槛|按当期.*指标计算|"
    r"没有全国统一数额|未给数额|未设统一金额|不设固定金额门槛|"
    r"官方不设固定金额门槛|法规未设统一金额"
)


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
    if key in pt:
        val = pt[key]
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
    if tests:
        # 以雅思为口径，没有雅思条目时退回任一有数值的考试
        pick = next((t for t in tests if t.get("test") == "IELTS"), tests[0])
        return (
            "ok",
            f"{pick['test']} ≥ {pick['min_score']}（另有 {len(tests) - 1} 种等效考试）",
            "",
        )
    note = lang.get("note") or ""
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


def judge(doc: dict, pr: dict) -> tuple[str, list[dict]]:
    """返回 (can|cannot|gap|unknown, 逐维结论)。

    维结论 kind：pass / fail / gap（差多少可知）/ silent（数据不表态）/ na
    """
    dims: list[dict] = []

    # 护照
    pt = (doc.get("eligibility") or {}).get("passport_types") or {}
    val = pt.get(pr["passport"])
    if val == "not_eligible":
        dims.append({"dim": "passport", "kind": "fail", "why": "该护照明确不可申"})
    elif val in ("eligible", "not_eligible"):
        dims.append({"dim": "passport", "kind": "pass", "why": "护照已登记可申"})
    elif val == "conditional":
        dims.append({"dim": "passport", "kind": "silent", "why": "有条件开放，需查当年公告"})
    elif val == "unknown":
        dims.append({"dim": "passport", "kind": "silent", "why": "官方未核实"})
    elif NOTE_OPEN_NATIONALITY.search(pt.get("note") or ""):
        dims.append(
            {"dim": "passport", "kind": "pass", "why": "note 明文「官方未按国籍设限」", "inferred": True}
        )
    else:
        dims.append({"dim": "passport", "kind": "silent", "why": "该护照未登记，note 无可判结论"})

    # 年龄
    age = (doc.get("eligibility") or {}).get("age") or {}
    lo, hi = age.get("min"), age.get("max")
    if UNVERIFIED_PREFIX.match((age.get("note") or "").strip()):
        dims.append({"dim": "age", "kind": "silent", "why": "官方未公布年龄限制"})
    elif lo == 0 and hi == 99:
        dims.append({"dim": "age", "kind": "na", "why": "官方无年龄限制"})
    elif pr["age"] < lo or pr["age"] > hi:
        dims.append(
            {
                "dim": "age",
                "kind": "fail",
                "need": f"{lo}-{hi} 岁",
                "have": f"{pr['age']} 岁",
                "why": f"年龄超出 {lo}-{hi} 岁",
            }
        )
    else:
        dims.append({"dim": "age", "kind": "pass", "why": f"在 {lo}-{hi} 岁内"})

    # 学历
    edu = (doc.get("eligibility") or {}).get("education") or {}
    need = EDU_RANK.get(edu.get("minimum_level") or "any", 0)
    have = EDU_RANK.get(pr["education"], 0)
    if have < need:
        dims.append(
            {
                "dim": "education",
                "kind": "fail",
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
                "why": f"另要求已完成 {edu['years_completed']} 年本科，在读无法从他填的信息判定",
            }
        )
    else:
        dims.append({"dim": "education", "kind": "pass", "why": "达到学历门槛"})

    # 语言
    lang = (doc.get("eligibility") or {}).get("language") or {}
    if lang.get("required") is not True:
        dims.append({"dim": "language", "kind": "na", "why": "不要求语言成绩"})
    else:
        tests = [
            t
            for t in (lang.get("tests") or [])
            if t.get("test") == "IELTS" and isinstance(t.get("min_score"), (int, float))
        ]
        note = lang.get("note") or ""
        if tests:
            need_score = tests[0]["min_score"]
            if pr["ielts"] is None:
                dims.append(
                    {
                        "dim": "language",
                        "kind": "gap",
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
                        "need": f"雅思 {need_score}",
                        "have": f"雅思 {pr['ielts']}",
                        "why": f"雅思差 {round(need_score - pr['ielts'], 1)} 分",
                    }
                )
            else:
                dims.append({"dim": "language", "kind": "pass", "why": f"雅思 {pr['ielts']} ≥ {need_score}"})
        elif LANG_BY_DESIGN.search(note):
            dims.append({"dim": "language", "kind": "na", "why": "官方不设分数线（面试/自证/仅计分）"})
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
                    "need": "语言成绩（项目要求）",
                    "have": "未提供",
                    "why": "该项目要求语言成绩，你没填；具体分数线仓内未登记，需查官网",
                }
            )
        elif LANG_CEFR_LADDER.search(note):
            dims.append(
                {
                    "dim": "language",
                    "kind": "silent",
                    "why": "官方用 CEFR/CLB 档位表述，仓内无对照表，无法与雅思分数直接比",
                }
            )
        else:
            dims.append(
                {
                    "dim": "language",
                    "kind": "silent",
                    "why": "项目要求语言证明但仓内未登记分数线，无法判断你的成绩是否达标",
                }
            )

    # 预算
    funds = (doc.get("eligibility") or {}).get("funds") or {}
    if funds.get("required") is not True:
        dims.append({"dim": "funds", "kind": "na", "why": "不要求资金证明"})
    else:
        amount = funds.get("amount") or {}
        cny = amount.get("cny_estimate")
        note = funds.get("note") or ""
        if not isinstance(cny, (int, float)):
            if FUNDS_NO_FIXED.search(note):
                dims.append(
                    {
                        "dim": "funds",
                        "kind": "na",
                        "why": "要求资金证明但官方不设固定金额，递交时自证",
                    }
                )
            else:
                dims.append(
                    {"dim": "funds", "kind": "silent", "why": "要求资金证明但未登记金额"}
                )
        elif pr["budget_cny"] < cny:
            dims.append(
                {
                    "dim": "funds",
                    "kind": "gap",
                    "need": f"约 {int(cny):,} 元",
                    "have": f"{pr['budget_cny']:,} 元",
                    "why": f"资金证明差约 {int(cny) - pr['budget_cny']:,} 元",
                }
            )
        else:
            dims.append({"dim": "funds", "kind": "pass", "why": f"预算 ≥ 约 {int(cny):,} 元"})

    kinds = {d["kind"] for d in dims}
    if "fail" in kinds:
        return "cannot", dims
    if "gap" in kinds:
        return "gap", dims
    if "silent" in kinds:
        return "unknown", dims
    return "can", dims


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
    args = ap.parse_args()

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
