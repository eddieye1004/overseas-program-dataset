#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
复核追踪：把「哪条记录该重新核了」变成机器可读的产物，而不是靠人记得。

为什么要有这个脚本：
    在此之前，数据陈旧只体现为 validate.py 的一条告警 —— 而告警不落盘、不进仓库、
    不产生待办，于是「半年前核过的项目」和「昨天核过的项目」在仓库里长得一模一样。
    CI 每周一跑一次 --strict，但它红一次也就过去了，没人知道该去核哪几条。

    本脚本产出两份东西：
      data/tracking.json  —— 每条记录、每条来源的新鲜度与下次复核日，供前端与 CI 读
      data/FRESHNESS.md   —— 同一批数据的人读版，按紧急程度排序

    并支持 --check：只要有任何一条越过复核周期就以退出码 1 结束，让定时任务变红。

复核周期怎么定（这是本脚本唯一的主观设定，写在这里以便被质疑）：
    窗口写死到具体日期的项目，一年一换窗口、错过就得等下一年，按 90 天核一次；
    其余按 180 天。评级依据是「错了会让人白等一年」的代价，不是项目热度。

用法：
    python scripts/track.py                      # 生成两份产物
    python scripts/track.py --check              # 只判定，不写文件（CI 定时任务用）
    python scripts/track.py --today 2026-12-01   # 指定基准日，便于测试与复盘
    python scripts/track.py --json               # 打印 tracking.json 到标准输出

退出码：0 = 全部在周期内；1 = 有记录已过期。
"""

import argparse
import glob
import json
import os
import sys
from datetime import date, datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
# stderr 也要一起定编码：Windows 控制台默认 cp936，中文错误信息会变成
# 非 UTF-8 字节，CI 与测试里按 utf-8 读就崩在解码而不是报错本身。
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PROGRAMS_DIR = os.path.join(REPO, "data", "programs")
TRACKING_PATH = os.path.join(REPO, "data", "tracking.json")
FRESHNESS_PATH = os.path.join(REPO, "data", "FRESHNESS.md")

POLICY_PATH = os.path.join(REPO, "data", "review-policy.json")


def load_policy():
    """复核周期从 data/review-policy.json 读，不在代码里写死。

    sync-data.mjs 也读同一份文件来算前端卡片上的「还剩几天」——
    两处各写一份 90/180，改一处忘另一处时前端和后端会各说一套。
    """
    try:
        with open(POLICY_PATH, encoding="utf-8") as fh:
            p = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise SystemExit(f"读不到复核策略 {POLICY_PATH}：{exc}")
    return p


POLICY = load_policy()

# 复核周期（天）。dated_window = 申请窗口写死到具体日期的那类，跨年后窗口就变了。
INTERVAL_DATED_WINDOW = int(POLICY["interval_dated_window_days"])
INTERVAL_DEFAULT = int(POLICY["interval_default_days"])

# 状态分档：剩余天数占比低于这些阈值时提前提示，避免「昨天还绿今天就红」。
DUE_SOON_RATIO = float(POLICY["due_soon_ratio"])


def load_programs():
    out = []
    for path in sorted(glob.glob(os.path.join(PROGRAMS_DIR, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            out.append((os.path.basename(path), json.load(fh)))
    return out


def parse_date(s):
    if not s or not isinstance(s, str):
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def has_dated_window(doc):
    """窗口里是否写了具体日期。

    只有 au-462、jp-working-holiday、nz-china-whv 这三条写了 open_date / close_date。
    其余 26 条的 windows 只有 year + status + note，跨年不产生新的可验证事实，
    所以不必按 90 天这么紧的周期追。
    """
    for w in doc.get("timeline", {}).get("windows", []) or []:
        if not isinstance(w, dict):
            continue
        if w.get("open_date") or w.get("close_date") or w.get("draw_period_end"):
            return True
    return False


def interval_for(doc):
    return INTERVAL_DATED_WINDOW if has_dated_window(doc) else INTERVAL_DEFAULT


def classify(age_days, interval_days):
    if age_days > interval_days:
        return "overdue"
    remaining = interval_days - age_days
    if remaining <= max(1, int(interval_days * DUE_SOON_RATIO)):
        return "due_soon"
    return "fresh"


def build(programs, today):
    rows = []
    for fname, doc in programs:
        prog = doc.get("program") or {}
        pid = prog.get("id") or os.path.splitext(fname)[0]
        lv = parse_date(doc.get("last_verified"))
        interval = interval_for(doc)

        # 配额四态里唯一需要跟进的是 unverified：它是一条公开的待办，
        # 而不是一个「已确认」的结论。其余三态都已经到此为止，不必再提醒。
        tl = doc.get("timeline") or {}
        quota_status = tl.get("quota_status")
        quota_pending = quota_status == "unverified"
        quota_row = {
            "quota_status": quota_status,
            "quota": tl.get("quota"),
            "quota_basis": tl.get("quota_basis"),
            "quota_note": tl.get("quota_note"),
            "quota_source": tl.get("quota_source"),
        }

        if lv is None:
            rows.append({
                "id": pid,
                "name": prog.get("name") or pid,
                "country": prog.get("country") or "",
                "file": fname,
                "last_verified": doc.get("last_verified"),
                "age_days": None,
                "interval_days": interval,
                "due": None,
                "days_left": None,
                "state": "unknown",
                "dated_window": has_dated_window(doc),
                "sources": [],
                "quota_pending": quota_pending,
                **quota_row,
            })
            continue

        age = (today - lv).days
        due = lv + timedelta(days=interval)
        sources = []
        for s in doc.get("sources", []) or []:
            if not isinstance(s, dict):
                continue
            slv = parse_date(s.get("last_verified"))
            sources.append({
                "url": s.get("url"),
                "type": s.get("type"),
                "grade": s.get("grade"),
                "last_verified": s.get("last_verified"),
                "age_days": (today - slv).days if slv else None,
                "state": classify((today - slv).days, interval) if slv else "unknown",
            })

        rows.append({
            "id": pid,
            "name": prog.get("name") or pid,
            "country": prog.get("country") or "",
            "file": fname,
            "last_verified": doc.get("last_verified"),
            "age_days": age,
            "interval_days": interval,
            "due": due.isoformat(),
            "days_left": (due - today).days,
            "state": classify(age, interval),
            "dated_window": has_dated_window(doc),
            "sources": sources,
            "quota_pending": quota_pending,
            **quota_row,
        })

    rows.sort(key=lambda r: (
        {"overdue": 0, "unknown": 1, "due_soon": 2, "fresh": 3}[r["state"]],
        r["days_left"] if r["days_left"] is not None else 10 ** 6,
        r["id"],
    ))

    summary = {"total": len(rows), "overdue": 0, "due_soon": 0, "fresh": 0, "unknown": 0}
    for r in rows:
        summary[r["state"]] = summary.get(r["state"], 0) + 1

    quota_pending = [r for r in rows if r.get("quota_pending")]
    summary["quota_unverified"] = len(quota_pending)

    return {
        "generated_for": today.isoformat(),
        "policy": {
            "interval_dated_window_days": INTERVAL_DATED_WINDOW,
            "interval_default_days": INTERVAL_DEFAULT,
            "due_soon_ratio": DUE_SOON_RATIO,
            "note": POLICY.get("why", {}).get("dated", "")
                    + " " + POLICY.get("why", {}).get("default", ""),
        },
        "summary": summary,
        "quota_unverified": [
            {
                "id": r["id"],
                "name": r["name"],
                "country": r["country"],
                "quota_note": r.get("quota_note"),
            }
            for r in sorted(quota_pending, key=lambda r: r["id"])
        ],
        "programs": rows,
    }


STATE_LABEL = {
    "overdue": "已过期",
    "due_soon": "即将到期",
    "fresh": "在周期内",
    "unknown": "缺核实日期",
}
STATE_MARK = {"overdue": "OVERDUE", "due_soon": "DUE SOON", "fresh": "OK", "unknown": "NO DATE"}


def render_md(tracking):
    L = []
    s = tracking["summary"]
    L.append("# 复核台账 · Freshness Ledger")
    L.append("")
    L.append("> **本文件由脚本生成，请勿手工编辑。**")
    L.append("> 生成器：`scripts/track.py`；数据源：`data/programs/*.json`。")
    L.append("> CI 每周一跑 `python scripts/track.py --check`，有记录超出复核周期即失败。")
    L.append("")
    L.append(f"基准日：**{tracking['generated_for']}**")
    L.append("")
    L.append(f"共 {s['total']} 条记录 —— "
             f"已过期 **{s['overdue']}** / 即将到期 {s['due_soon']} / "
             f"在周期内 {s['fresh']} / 缺日期 {s['unknown']}")
    L.append("")
    pol = tracking["policy"]
    L.append(f"复核周期：窗口写死到具体日期的项目 **{pol['interval_dated_window_days']} 天**，"
             f"其余 **{pol['interval_default_days']} 天**。"
             f"剩余不足周期的 {int(pol['due_soon_ratio'] * 100)}% 时提前标为「即将到期」。")
    L.append("")
    L.append("---")
    L.append("")

    pending = [r for r in tracking["programs"] if r["state"] in ("overdue", "due_soon", "unknown")]
    if pending:
        L.append("## 需要处理")
        L.append("")
        L.append("| 状态 | 项目 | 上次核实 | 已过天数 | 复核周期 | 下次复核 | 剩余 |")
        L.append("| --- | --- | --- | --- | --- | --- | --- |")
        for r in pending:
            left = "—" if r["days_left"] is None else f"{r['days_left']} 天"
            age = "—" if r["age_days"] is None else f"{r['age_days']} 天"
            L.append(f"| {STATE_LABEL[r['state']]} | `{r['id']}` {r['name']} | "
                     f"{r['last_verified'] or '—'} | {age} | {r['interval_days']} 天 | "
                     f"{r['due'] or '—'} | {left} |")
        L.append("")
    else:
        L.append("## 需要处理")
        L.append("")
        L.append("没有过期记录。")
        L.append("")

    L.append("## 全部记录")

    L.append("")
    L.append("| 状态 | 项目 | 国家 | 上次核实 | 已过天数 | 下次复核 | 剩余 | 来源数 |")
    L.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in tracking["programs"]:
        left = "—" if r["days_left"] is None else f"{r['days_left']} 天"
        age = "—" if r["age_days"] is None else f"{r['age_days']} 天"
        L.append(f"| {STATE_LABEL[r['state']]} | `{r['id']}` | {r['country']} | "
                 f"{r['last_verified'] or '—'} | {age} | {r['due'] or '—'} | {left} | "
                 f"{len(r['sources'])} |")
    L.append("")
    # ---- 待核实配额清单 ----
    # 这一节是「配额四态」里 unverified 那两档的落地形态：它们不是错误，
    # 但必须可见。放在复核台账里而不是单独一份手工文档，是为了让它跟着
    # track.py 的常规流程自动更新，不会变成第二份需要人记得去改的清单。
    qp = tracking.get("quota_unverified") or []
    L.append("## 待核实的配额")
    L.append("")
    if qp:
        L.append(f"共 **{len(qp)}** 个项目知道「官方可能设限额」但没查到数字，"
                 f"递交前须自行确认。这些不计入上面的超期判定——"
                 f"它们是缺口，不是过期。")
        L.append("")
        L.append("| 项目 | 国家 | 缺什么 |")
        L.append("| --- | --- | --- |")
        for q in qp:
            note = (q.get("quota_note") or "").replace("|", "\\|")
            L.append(f"| `{q['id']}` {q['name']} | {q['country']} | {note} |")
    else:
        L.append("没有待核实的配额。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 复核该做什么")
    L.append("")
    L.append("按顺序核这四件事，任何一项对不上就改数据，不要只改日期：")
    L.append("")
    L.append("1. **资格条件**是否仍成立（年龄上限、学历门槛、语言分数、资金数额）")
    L.append("2. **费用**是否变动（申请费、保险费、服务费）")
    L.append("3. **窗口日期**是否已公布新的一年（抽签制尤其要盯）")
    L.append("4. **链接**是否还在原地址（官方站改版会把旧 URL 变成 404）")
    L.append("")
    L.append("核完把 `last_verified` 改成当天，再跑 `python scripts/track.py` 重新生成本文件。")
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="生成并检查数据集复核台账")
    ap.add_argument("--check", action="store_true", help="只判定，不写文件；有过期则退出码 1")
    ap.add_argument("--today", help="基准日 YYYY-MM-DD（默认今天）")
    ap.add_argument("--json", action="store_true", help="把 tracking.json 打印到标准输出")
    ap.add_argument("--stale-limit", type=int, default=0,
                    help="允许的过期条数上限（默认 0，即不允许）")
    args = ap.parse_args()

    today = parse_date(args.today) if args.today else date.today()
    if today is None:
        print(f"基准日格式不对：{args.today}", file=sys.stderr)
        return 2

    programs = load_programs()
    if not programs:
        print(f"{PROGRAMS_DIR} 下没有找到任何记录", file=sys.stderr)
        return 2

    tracking = build(programs, today)

    if args.json:
        print(json.dumps(tracking, ensure_ascii=False, indent=2))
        return 0

    s = tracking["summary"]
    overdue = [r for r in tracking["programs"] if r["state"] == "overdue"]

    if not args.check:
        with open(TRACKING_PATH, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(tracking, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        with open(FRESHNESS_PATH, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(render_md(tracking))
        print(f"wrote data/tracking.json and data/FRESHNESS.md "
              f"({s['total']} programs, baseline {tracking['generated_for']})")

    print()
    print(f"复核台账 · 基准日 {tracking['generated_for']}")
    print(f"  共 {s['total']} 条：已过期 {s['overdue']} / 即将到期 {s['due_soon']} / "
          f"在周期内 {s['fresh']} / 缺日期 {s['unknown']}")

    if overdue:
        print()
        print(f"  超出复核周期（>{pol_interval_note(tracking)}）：")
        for r in overdue:
            print(f"    - {r['id']}  上次核实 {r['last_verified']}  已过 {r['age_days']} 天  "
                  f"周期 {r['interval_days']} 天")

    due_soon = [r for r in tracking["programs"] if r["state"] == "due_soon"]
    if due_soon:
        print()
        print("  即将到期：")
        for r in due_soon:
            print(f"    - {r['id']}  下次复核 {r['due']}  还剩 {r['days_left']} 天")

    if args.check and len(overdue) > args.stale_limit:
        print()
        print(f"结果：有 {len(overdue)} 条超出复核周期，需要重新核实官方来源。")
        return 1

    print()
    print("结果：全部在复核周期内。" if not overdue else "结果：允许范围内。")
    return 0


def pol_interval_note(tracking):
    p = tracking["policy"]
    return f"{p['interval_dated_window_days']}/{p['interval_default_days']} 天"


if __name__ == "__main__":
    sys.exit(main())
