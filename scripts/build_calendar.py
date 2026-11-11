#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把每个项目的 timeline.schedule 汇总成仓库级窗口日历。

为什么要有这个文件：
    单个项目的 schedule 回答「这个项目什么时候开」；但使用者的真实问题是
    「接下来三个月我该盯哪几个」。后者需要把 33 条记录放到同一条时间轴上，
    并且按「确定性」分开——否则一个推断出来的日期会和官方公布的日期并排出现，
    读者无法分辨，雷达就会把人叫错时间。

本脚本产出两份：
    data/calendar.json  机器读：每条含项目、窗口类型、确定性、提醒日、剩余天数
    （人读视图直接渲染进 data/FRESHNESS.md，由 track.py 调用本模块生成）

提醒日怎么算：
    对 confirmed 且带 open_date 的记录：remind_on = open_date − lead_time_days。
    对 inferred：不给日期，只给「该在什么时间点去看官方页面」，这个时间点用
    cycle_note 里的月份描述，不折算成具体日——推断的东西再算一层还是推断。
    对 rolling：不提醒，它随时可申。

确定性是硬分区，不合并展示：
    confirmed / inferred / unknown 三档在日历里永远是三块，不按日期排序混排。
"""

import glob
import json
import os
import sys
from datetime import date, datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PROGRAMS_DIR = os.path.join(REPO, "data", "programs")
CALENDAR_PATH = os.path.join(REPO, "data", "calendar.json")

CONFIDENCE_LABEL = {
    "confirmed": "官方已公布日期",
    "inferred": "按往年规律推断（非官方日期）",
    "unknown": "无从判断",
}
TYPE_LABEL = {
    "fixed_dates": "每年由官方逐次公布",
    "annual_cycle": "每年相近月份重开",
    "rolling": "全年滚动",
    "no_window": "无窗口（不开放）",
}


def parse_date(s):
    if not s or not isinstance(s, str):
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def build(today):
    rows = []
    for path in sorted(glob.glob(os.path.join(PROGRAMS_DIR, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        prog = doc.get("program") or {}
        pid = prog.get("id") or os.path.splitext(os.path.basename(path))[0]
        sch = (doc.get("timeline") or {}).get("schedule")

        if not isinstance(sch, dict):
            rows.append({
                "id": pid, "name": prog.get("name") or pid,
                "country": prog.get("country") or "",
                "eligible": (doc.get("eligibility") or {}).get("passport_types", {}).get("mainland_china"),
                "type": None, "status": "unknown", "date_confidence": "unknown",
                "open_date": None, "close_date": None, "lead_time_days": None,
                "remind_on": None, "days_to_open": None, "days_to_deadline": None,
                "next_window_hint": None, "cycle_note": None,
                "missing": "该项目没有 timeline.schedule",
            })
            continue

        open_d = parse_date(sch.get("open_date"))
        close_d = parse_date(sch.get("close_date"))
        lead = sch.get("lead_time_days")
        remind_on = None
        if open_d and isinstance(lead, int):
            remind_on = open_d - timedelta(days=lead)

        rows.append({
            "id": pid,
            "name": prog.get("name") or pid,
            "country": prog.get("country") or "",
            "eligible": (doc.get("eligibility") or {}).get("passport_types", {}).get("mainland_china"),
            "type": sch.get("type"),
            "status": sch.get("status"),
            "date_confidence": sch.get("date_confidence"),
            "open_date": sch.get("open_date"),
            "close_date": sch.get("close_date"),
            "lead_time_days": lead,
            "remind_on": remind_on.isoformat() if remind_on else None,
            "days_to_open": (open_d - today).days if open_d else None,
            "days_to_deadline": (close_d - today).days if close_d else None,
            "next_window_hint": sch.get("next_window_hint"),
            "cycle_note": sch.get("cycle_note"),
            "missing": None,
        })

    # 排序：按确定性分档（confirmed → inferred → unknown），档内「还没到的排前面」，
    # 已过去的关键日期沉底——已经关闭的窗口不该占据日历最上方。
    order = {"confirmed": 0, "inferred": 1, "unknown": 2}

    def sort_key(r):
        d = r["days_to_open"]
        # 三个阶段：0=窗口还开着或还没到（要关注）；1=已关闭（沉底）；2=无日期
        if r["status"] in ("open", "upcoming"):
            bucket = 0
        elif d is None:
            bucket = 2
        else:
            bucket = 1
        return (order.get(r["date_confidence"], 9), bucket,
                abs(d) if d is not None else 10 ** 6, r["id"])

    rows.sort(key=sort_key)

    counts = {"total": len(rows), "confirmed": 0, "inferred": 0, "unknown": 0}
    for r in rows:
        counts[r["date_confidence"]] = counts.get(r["date_confidence"], 0) + 1

    # 有确定日期、且还没过截止的，才算「雷达能叫醒的」
    actionable = [
        r for r in rows
        if r["date_confidence"] == "confirmed"
        and r["open_date"]
        and (r["days_to_deadline"] is None or r["days_to_deadline"] >= 0)
    ]

    return {
        "generated_for": today.isoformat(),
        "note": ("本文件由 scripts/build_calendar.py 从 data/programs/*.json 的 "
                 "timeline.schedule 派生，请勿手工编辑。三档 date_confidence "
                 "（confirmed/inferred/unknown）是硬分区：推断出来的日期永不与官方日期混排。"),
        "summary": counts,
        "actionable": [r["id"] for r in actionable],
        "programs": rows,
    }


def render_md(cal):
    """渲染进 FRESHNESS.md 的人读视图。"""
    s = cal["summary"]
    L = []
    L.append("## 窗口日历")
    L.append("")
    L.append(f"基准日 **{cal['generated_for']}** —— {s['total']} 个项目："
             f"官方已公布日期 **{s['confirmed']}** / 按规律推断 {s['inferred']} / "
             f"无从判断 {s['unknown']}。")
    L.append("")
    L.append("三档是硬分区，不按日期混排——**推断出来的日期永远不会和官方公布的日期并排出现**。")
    L.append("")

    def table(title, rows):
        L.append(f"### {title}")
        L.append("")
        if not rows:
            L.append("（无）")
            L.append("")
            return
        L.append("| 状态 | 项目 | 国家 | 窗口类型 | 开放日 | 截止日 | 建议提前 | 提醒日 | 还剩 |")
        L.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        st = {"open": "开放中", "closed": "已关闭", "upcoming": "未开始",
              "always_open": "随时可申", "unknown": "未知"}
        for r in rows:
            lead = "—" if r["lead_time_days"] is None else f"{r['lead_time_days']} 天"
            days = "—" if r["days_to_open"] is None else f"{r['days_to_open']} 天"
            L.append(f"| {st.get(r['status'], r['status'])} | `{r['id']}` {r['name']} | {r['country']} | "
                     f"{TYPE_LABEL.get(r['type'], '—')} | {r['open_date'] or '—'} | "
                     f"{r['close_date'] or '—'} | {lead} | {r['remind_on'] or '—'} | {days} |")
        L.append("")

    confirmed = [r for r in cal["programs"] if r["date_confidence"] == "confirmed"]
    inferred = [r for r in cal["programs"] if r["date_confidence"] == "inferred"]
    unknown = [r for r in cal["programs"] if r["date_confidence"] == "unknown"]

    table("① 官方已公布日期（可直接按此安排）", confirmed)
    table("② 按往年规律推断（只作参考，不是官方日期）", inferred)

    L.append("### ③ 无从判断 / 无窗口")
    L.append("")
    if unknown:
        L.append("| 状态 | 项目 | 窗口类型 | 为什么没有日期 |")
        L.append("| --- | --- | --- | --- |")
        st = {"open": "开放中", "closed": "已关闭", "upcoming": "未开始",
              "always_open": "随时可申", "unknown": "未知"}
        for r in unknown:
            hint = (r.get("next_window_hint") or r.get("missing") or "—").replace("|", "\\|")
            L.append(f"| {st.get(r['status'], r['status'])} | `{r['id']}` {r['name']} | "
                     f"{TYPE_LABEL.get(r['type'], '—')} | {hint} |")
    else:
        L.append("（无）")
    L.append("")
    return L


def main():
    today = date.today()
    if len(sys.argv) > 1 and sys.argv[1] == "--today":
        today = parse_date(sys.argv[2]) or today
    cal = build(today)
    with open(CALENDAR_PATH, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(cal, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    s = cal["summary"]
    print(f"wrote data/calendar.json ({s['total']} programs: "
          f"confirmed {s['confirmed']} / inferred {s['inferred']} / unknown {s['unknown']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
