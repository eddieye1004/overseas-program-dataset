#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""复核基准日的唯一 Python 侧来源。

为什么需要这个模块：
    有三份产物要回答「这条记录多久没核了」，它们各自要一个「今天」：
        scripts/track.py            → data/tracking.json、data/FRESHNESS.md
        scripts/build_calendar.py   → data/calendar.json
        web/scripts/sync-data.mjs   → web/public/data/index.json（JS 侧，口径照抄本文件）
    只要这个「今天」读系统时钟，同一份数据在不同日期跑就会产出不同字节。
    实测（2026-11-20，HEAD 48fb859）：数据零改动，跑一次
    `node scripts/sync-data.mjs` + `python scripts/track.py` 产生
    FRESHNESS.md 92 行 + tracking.json 438 行 + index.json 1 行纯日期漂移。
    假 diff 把真正的改动淹掉，也让「改完数据忘了重跑」这类真问题看不出来。

口径（沿用 gen_sources.py 早已采用的写法——它为了同一个理由把基准取成
「最近一次核实」而不是系统当前日期）：
    基准日 = 数据内最新的一次核实日：program.last_verified 与每一条
    sources[].last_verified 取最大值，只从 data/programs/*.json 读，
    **不读系统时钟**。因此「同输入数据 → 同字节输出」。

真实新鲜度语义不变（这是本模块最容易误读的地方）：
    基准日不读时钟，不等于不再判超期。
      · `python scripts/track.py --check` 默认仍按**现实日期**判定，
        CI 定时任务靠它变红——「数据该复核了」这个闸门一秒都没松。
      · CI 里的 issue（scripts/sync_issue.py）读的是 CI 当次按现实日期
        生成的台账，不是仓库里那份快照。
    本模块只管「写进仓库的产物」，那部分必须可复现；判定现实新鲜度的
    那一侧必须跟着真实日历走，两者不能共用一个日期。
"""

from datetime import date, datetime

__all__ = ["newest_verified", "parse", "baseline_for_artifacts"]


def parse(value):
    """'YYYY-MM-DD' → date；非法或缺值返回 None（不抛，也不当成 0）。"""
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def newest_verified(docs):
    """数据内最新一次核实日，返回 'YYYY-MM-DD' 字符串；一条都没有则 None。

    docs 是 program 文档（含 program / sources / last_verified 的顶层对象）的
    可迭代对象。顶层 last_verified 是整体复核日，来源条目可能更旧，两者都算——
    与 gen_sources.py 的 dates 集合同口径。
    """
    best = None
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        candidates = [doc.get("last_verified")]
        for src in doc.get("sources") or []:
            if isinstance(src, dict):
                candidates.append(src.get("last_verified"))
        for value in candidates:
            if parse(value) and (best is None or value > best):
                best = value
    return best


def baseline_for_artifacts(docs):
    """写仓库产物时用的基准日（date）。

    数据里连一个核实日期都没有时退回现实日期：此时没有「数据自身的时效」
    可依据，宁可让产物跟着日期走，也好过凭空造一个基准。
    """
    newest = newest_verified(docs)
    parsed = parse(newest)
    return parsed if parsed else date.today()
