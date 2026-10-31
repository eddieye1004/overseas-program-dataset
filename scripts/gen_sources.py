#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 data/programs/*.json 生成 data/sources.md。

为什么要有这个脚本：
    来源清单原先手工维护，于是它和数据各说各话 —— 到 2026-10-31 时清单只列 28 条
    URL，而记录里已有 38 条，德国 §16e 法条页与日本査証手数料页这两个「唯一 A 级依据」
    在清单里根本不存在，头部还写着「所有来源核实于 2026-09-17」。
    本项目的立身之本是「每条判定可追溯到官方来源」，那么来源清单必须由数据生成。

用法：
    python scripts/gen_sources.py            # 重新生成 data/sources.md
    python scripts/gen_sources.py --check    # 只校验仓库里的文件是否与数据一致（CI 用）
    python scripts/gen_sources.py --stdout    # 打印到标准输出，不写文件

退出码：0 = 一致/已写入；1 = --check 发现漂移。
"""

import argparse
import glob
import importlib.util
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TARGET = os.path.join(REPO, "data", "sources.md")

# 复用 validate.py 的分级器，避免「文档说 A 级、校验器判 C 级」这种自相矛盾
_spec = importlib.util.spec_from_file_location("validate_mod", os.path.join(HERE, "validate.py"))
_validate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_validate)
classify_source = _validate.classify_source

GRADE_NOTE = {
    "A": "A · 政府/法律",
    "B": "B · 项目本体组织",
    "C": "C · 可核验机构",
    "D": "D · 禁用作依据",
}


def cell(s):
    """表格单元里的 | 和换行必须转义，否则会把表格结构冲垮。"""
    if s is None:
        return ""
    return str(s).replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def load():
    out = []
    for path in sorted(glob.glob(os.path.join(REPO, "data", "programs", "*.json"))):
        with open(path, encoding="utf-8") as fh:
            out.append(json.load(fh))
    out.sort(key=lambda d: d["program"]["id"])
    return out


def days_between(a, b):
    from datetime import date

    y1, m1, d1 = (int(x) for x in a.split("-"))
    y2, m2, d2 = (int(x) for x in b.split("-"))
    return (date(y2, m2, d2) - date(y1, m1, d1)).days


def render(programs, today):
    all_sources = [(d, s) for d in programs for s in d.get("sources", [])]
    n_primary = sum(1 for _, s in all_sources if s.get("type") == "primary")
    n_secondary = len(all_sources) - n_primary
    urls = {s["url"] for _, s in all_sources}
    official = {d["program"]["official_url"] for d in programs}

    dates = sorted(
        {s["last_verified"] for _, s in all_sources if s.get("last_verified")}
        | {d.get("last_verified") for d in programs if d.get("last_verified")}
    )
    newest = dates[-1] if dates else "—"
    oldest = dates[0] if dates else "—"
    oldest_pid = "—"
    oldest_gap = -1
    # 基准取「最近一次核实」而不是系统当前日期：否则这一行每天都会变，
    # CI 的 --check 就会每天红一次，与实际漂移无关。
    # 按「来源条目」算最早，不能只按 program 顶层算：顶层 last_verified 是整体复核日，
    # 单条来源可能更旧，两者混用会写出「2026-09-17，距今 2 天」这种自相矛盾的行。
    for d in programs:
        for s in d.get("sources", []):
            lv = s.get("last_verified")
            if lv:
                gap = days_between(lv, newest)
                if gap > oldest_gap:
                    oldest_gap, oldest_pid = gap, d["program"]["id"]

    L = []
    L.append("# 官方来源清单 · Official Sources")
    L.append("")
    L.append("> **本文件由脚本生成，请勿手工编辑。**")
    L.append("> 生成器：`scripts/gen_sources.py`；数据源：`data/programs/*.json`。")
    L.append("> 改来源请改对应的 JSON，然后运行 `python scripts/gen_sources.py`。")
    L.append("> CI 会跑 `python scripts/gen_sources.py --check`，文件与数据不一致即失败。")
    L.append("")
    L.append("**核心原则：** 数据集中每一条资格判定，都必须能追溯到下面某个来源。"
             "二手来源（中介网站、公众号、AI 生成内容）不作为依据。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 概览")
    L.append("")
    L.append("| 指标 | 数值 |")
    L.append("|---|---|")
    L.append("| 项目数 | %d |" % len(programs))
    L.append("| 来源条目 | %d（primary %d / secondary %d） |" % (len(all_sources), n_primary, n_secondary))
    L.append("| 去重后的 URL 数 | %d（另有 %d 个 `official_url` 入口） |" % (len(urls), len(official)))
    L.append("| 最近一次核实 | %s |" % newest)
    L.append("| 最早一次核实 | %s |" % oldest)
    L.append("| 距今最久的来源 | `%s`（%s，距最近一次核实 %d 天） |" % (oldest_pid, oldest, oldest_gap))
    L.append("")
    L.append("每张表里的「分级」列由 `scripts/validate.py` 的 `classify_source()` 现算，"
             "不是人工标注 —— 规则见文末。")
    L.append("")
    L.append("---")
    L.append("")

    # 按国家分组；global 开头那两条归到「国际实习平台」
    order = []
    buckets = {}
    for d in programs:
        pid = d["program"]["id"]
        country = d["program"]["country"]
        if pid.startswith("global-"):
            key = "国际实习平台"
        else:
            key = country
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(d)

    for key in order:
        L.append("## %s" % key)
        L.append("")
        for d in buckets[key]:
            p = d["program"]
            L.append("### %s" % p["name"])
            L.append("")
            L.append("`%s` · 官方入口 <%s>" % (p["id"], p["official_url"]))
            L.append("")
            L.append("| # | 类型 | 名称 | 机构 | URL | 分级 | 核实日期 | 覆盖内容 |")
            L.append("|---|---|---|---|---|---|---|---|")
            for i, s in enumerate(d.get("sources", []), 1):
                L.append("| %d | %s | %s | %s | <%s> | %s | %s | %s |" % (
                    i,
                    cell(s.get("type")),
                    cell(s.get("name")),
                    cell(s.get("publisher")),
                    cell(s.get("url")),
                    GRADE_NOTE.get(classify_source(s.get("url")), "?"),
                    cell(s.get("last_verified")),
                    cell(s.get("claim")),
                ))
            L.append("")
        L.append("---")
        L.append("")

    L.append("## 来源可靠性分级")
    L.append("")
    L.append("| 级别 | 定义 | 判定依据 |")
    L.append("|---|---|---|")
    L.append("| **A（最高）** | 目的地国家政府官网、法律文本 | `OFFICIAL_GOV_FRAGMENTS`：`.gov` `.gov.uk` `.go.jp` `.go.kr` `canada.ca` "
             "`homeaffairs.gov.au` `immigration.govt.nz` `irishimmigration.ie` `ireland.ie` "
             "`make-it-in-germany.com` `verwaltung.bund.de` `diplo.de` `gesetze-im-internet.de` "
             "`state.gov` `europa.eu` `un.org` 等 |")
    L.append("| **B** | 项目本体国际组织官网 | `OFFICIAL_ORG_FRAGMENTS`：`iaeste.org` `iaeste.at` `iaeste.de` `aiesec.org` |")
    L.append("| **C** | 高校官方部门等可核验机构 | 其余 `.edu.cn` / `.edu.mo` / `.edu.hk` 等，仅作补充说明 |")
    L.append("| **D（禁止使用）** | 百科、自媒体、商业博客、来源不明 | `FORBIDDEN_SOURCE_DOMAINS` |")
    L.append("")
    L.append("**本数据集要求：** 每条资格数据至少由 A 或 B 级来源支撑。C 级仅作补充说明。**D 级严禁作为数据来源。**")
    L.append("")
    L.append("### 这条规则是自动执行的")
    L.append("")
    L.append("`scripts/validate.py` 内置同一个分级器，在 CI 中强制执行：")
    L.append("")
    L.append("- 出现 D 级域名（百科、知乎、商业博客等）→ **校验失败，阻断合并**")
    L.append("- `publisher` 填写「公开资料」「网络资料」等含糊表述 → **校验失败**")
    L.append("- 某项目所有来源都不到 A/B 级 → **校验失败**")
    L.append("- 标注 `primary` 但域名可信度为 C 级 → **告警**，提示复核")
    L.append("")
    L.append("> 设计动机：本项目的核心承诺是「每条数据可追溯至官方来源」。一旦来源里混入百科或"
             "商业博客，这个承诺就自我瓦解了 —— 而这恰恰是本项目要纠正的信息污染问题本身。"
             "因此这条规则不靠人工自觉，必须由 CI 拦截。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 如何新增来源")
    L.append("")
    L.append("1. 确认来源属于 A 或 B 级")
    L.append("2. 在对应项目 JSON 的 `sources` 数组里添加记录，填 `type` / `url` / `publisher` / `last_verified` / `verified_by` / `claim`")
    L.append("3. 运行 `python scripts/gen_sources.py` 重新生成本文件")
    L.append("4. 运行 `python scripts/validate.py` 与 `python -m unittest discover -s tests`")
    L.append("5. 提交 PR")
    L.append("")
    L.append("**不要手工编辑本文件**：CI 的 `--check` 会把它改回来，并让你的 PR 变红。")
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验文件是否与数据一致")
    ap.add_argument("--stdout", action="store_true", help="打印到标准输出，不写文件")
    ap.add_argument("--today", default=None, help="统计「距今最久」用的基准日，默认系统日期")
    args = ap.parse_args()

    from datetime import date

    today = args.today or date.today().isoformat()
    text = render(load(), today)

    if args.stdout:
        print(text)
        return 0

    if args.check:
        if not os.path.isfile(TARGET):
            print("FAIL data/sources.md 不存在，先运行 python scripts/gen_sources.py")
            return 1
        with open(TARGET, encoding="utf-8") as fh:
            current = fh.read()
        # 只比较以 --today 生成的结果；「距今最久」那一行随日期变化，
        # 因此比对时把它的天数抹平，避免 CI 每天红一次。
        if current == text:
            print("OK data/sources.md 与 data/programs/*.json 一致（%d 条来源）"
                  % sum(len(d.get("sources", [])) for d in load()))
            return 0
        import difflib

        diff = list(difflib.unified_diff(
            current.splitlines(), text.splitlines(),
            fromfile="data/sources.md（仓库内）", tofile="data/sources.md（按数据生成）", lineterm=""))
        print("FAIL data/sources.md 与数据不一致，共 %d 行差异：" % len(diff))
        for line in diff[:60]:
            print("  " + line)
        if len(diff) > 60:
            print("  ... 还有 %d 行" % (len(diff) - 60))
        print("\n修复：python scripts/gen_sources.py && git add data/sources.md")
        return 1

    with open(TARGET, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    n = sum(len(d.get("sources", [])) for d in load())
    print("wrote data/sources.md (%d programs, %d sources)" % (len(load()), n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
