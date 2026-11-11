#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把复核台账变成一张 GitHub issue——让「该核了」真的会喊到人。

为什么要有这个脚本：
    track.py --check 已经能让 CI 变红，但红一次不产生待办：没人订阅构建状态，
    而 GitHub 的失败通知默认只发给最后一个推送者。于是「半年没核的项目」
    每周红一次，红到被无视为止。issue 是仓库里唯一「有人会真的看到」的位置。

幂等的做法（这是本脚本唯一需要小心的地方）：
    固定标题 + 固定标签 → 先搜同名 open issue → 有就原地更新，没有才新建。
    因此每周跑一次不会长出新 issue，也不会把历史评论刷掉。
    **不许**用日期或运行号拼标题——那等于每周刷一张新的，比不做还吵。

权限：
    workflow 里只给 issues: write（外加 contents: read 供 checkout），
    不给 pull-requests / packages 等任何其余写权限。

用法（CI 里由 GITHUB_TOKEN 驱动）：
    python scripts/sync_issue.py --dry-run     # 打印将要写入的正文，不发请求
    python scripts/sync_issue.py               # 真发（需要 GH_TOKEN + GITHUB_REPOSITORY）

退出码：0 = 同步成功（含「无需处理，且已无 open issue」）；1 = 失败。
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
TRACKING_PATH = os.path.join(REPO_ROOT, "data", "tracking.json")

# 固定标题是幂等的锚点。改标题等于放掉所有旧 issue，所以这里写成常量并加注释。
ISSUE_TITLE = "复核台账：有记录需要重新核实"
ISSUE_LABEL = "data-freshness"
MARKER = "<!-- quota-freshness-ledger -->"

API = "https://api.github.com"


def load_tracking():
    try:
        with open(TRACKING_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise SystemExit(f"找不到 {TRACKING_PATH}，先跑 python scripts/track.py")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{TRACKING_PATH} 不是合法 JSON：{exc}")


def needs_attention(tracking):
    """哪些记录该进 issue 的「待复核」表。

    三类都要：已过期（必须核）、即将到期（提前给窗口）、缺核实日期（不知道新旧）。
    fresh 不进——issue 里塞满「一切正常」的行会让真正要处理的那几条被淹掉。
    """
    out = []
    for r in tracking.get("programs", []):
        if r.get("state") in ("overdue", "due_soon", "unknown"):
            out.append(r)
    return out


def has_open_work(tracking, pending):
    """issue 该不该存在。

    注意这里比 needs_attention 多一类：**配额待核实也算未完成的活**。
    否则会出现「仅有 2 条配额缺口、但没有任何过期记录」时把 issue 自动关掉，
    而那 2 条缺口正好是唯一还没人处理的事——等于刚建好就自己关。
    """
    return bool(pending) or bool(tracking.get("quota_unverified"))


def render_body(tracking, pending):
    s = tracking.get("summary", {})
    baseline = tracking.get("generated_for", "—")
    pol = tracking.get("policy", {})

    L = [MARKER, ""]
    L.append("> 本 issue 由 `scripts/sync_issue.py` 自动维护：**标题与标签固定，"
             "每次运行原地更新，不会新建第二条。**")
    L.append("> 数据源 `data/programs/*.json`；判定规则见 `scripts/track.py` 与 "
             "`data/review-policy.json`。")
    L.append("")
    L.append(f"基准日 **{baseline}** —— 共 {s.get('total', 0)} 条记录："
             f"已过期 **{s.get('overdue', 0)}** / 即将到期 {s.get('due_soon', 0)} / "
             f"缺日期 {s.get('unknown', 0)}。")
    L.append("")
    L.append(f"复核周期：窗口写死到具体日期的项目 {pol.get('interval_dated_window_days', '?')} 天，"
             f"其余 {pol.get('interval_default_days', '?')} 天。"
             f"剩余不足周期的 {int(float(pol.get('due_soon_ratio', 0.25)) * 100)}% 时提前提醒。")
    L.append("")

    if pending:
        L.append("## 待复核清单")
        L.append("")
        L.append("| 状态 | 项目 | 国家 | 上次核实 | 已过天数 | 下次复核 | 剩余 |")
        L.append("| --- | --- | --- | --- | --- | --- | --- |")
        label = {"overdue": "已过期", "due_soon": "即将到期", "unknown": "缺核实日期"}
        for r in pending:
            age = "—" if r.get("age_days") is None else f"{r['age_days']} 天"
            left = "—" if r.get("days_left") is None else f"{r['days_left']} 天"
            L.append(f"| {label.get(r['state'], r['state'])} | `{r['id']}` {r.get('name', '')} | "
                     f"{r.get('country', '')} | {r.get('last_verified') or '—'} | {age} | "
                     f"{r.get('due') or '—'} | {left} |")
        L.append("")
    else:
        L.append("## 待复核清单")
        L.append("")
        L.append("没有需要复核的记录。")
        L.append("")

    # 配额待核实：与「过期」不同，它不随时间变化，但同样是缺口。
    # 放在同一张 issue 里而不是另开一张，是为了不让维护者订阅两个地方。
    qp = tracking.get("quota_unverified") or []
    if qp:
        L.append("## 配额待核实")
        L.append("")
        L.append(f"{len(qp)} 个项目知道官方可能设限额，但没查到具体数字。"
                 f"这些**不阻断构建**，但递交前须自行确认：")
        L.append("")
        L.append("| 项目 | 国家 | 缺什么 |")
        L.append("| --- | --- | --- |")
        for q in qp:
            note = (q.get("quota_note") or "").replace("|", "\\|")
            L.append(f"| `{q['id']}` {q.get('name', '')} | {q.get('country', '')} | {note} |")
        L.append("")

    L.append("---")
    L.append("")
    L.append("## 核完怎么关")
    L.append("")
    L.append("按顺序核这四件事，任何一项对不上就改数据，**不要只改日期**：")
    L.append("")
    L.append("1. 资格条件是否仍成立（年龄上限、学历门槛、语言分数、资金数额）")
    L.append("2. 费用是否变动（申请费、保险费、服务费）")
    L.append("3. 窗口日期是否已公布新的一年（抽签制尤其要盯）")
    L.append("4. 链接是否还在原地址（官方站改版会把旧 URL 变成 404）")
    L.append("")
    L.append("把 `last_verified` 改成当天，跑 `python scripts/track.py` 重算台账并提交。"
             "下一次定时任务发现没有待复核项时，会**自动关闭本 issue**——不需要手工关。")
    L.append("")
    return "\n".join(L)


def gh(method, path, token, payload=None):
    url = API + path
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "overseas-program-dataset-freshness-bot")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return resp.getcode(), (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        # 404 在「找不到 issue」的语义下是正常分支，交给调用方判断；
        # 422 由 ensure_label 自己识别为「标签已存在」。
        # 其余状态码原样抛出 HTTPError，让调用方能按 code 分支，
        # 同时在被吞之前的最后一层（main）统一转成可读的报错。
        if exc.code in (404, 422):
            return exc.code, {}
        raise SystemExit(f"GitHub API {method} {path} 失败：HTTP {exc.code}\n{body}")


def find_open_issue(repo, token):
    """按固定标题找 open issue。用 search 而不是 list：后者要翻页且会带上已关闭的。"""
    q = f'repo:{repo} is:issue is:open in:title "{ISSUE_TITLE}"'
    from urllib.parse import quote
    code, data = gh("GET", f"/search/issues?q={quote(q)}&per_page=10", token)
    for item in data.get("items", []):
        if item.get("title") == ISSUE_TITLE:
            return item
    return None


def ensure_label(repo, token):
    """标签不存在就建。已存在时 GitHub 返回 422，属正常分支。

    走 gh() 而不是另写一份 urllib 调用：否则测试替换了 gh 也拦不住这条路径，
    「标签失败不阻断建 issue」这个分支就只能靠线上试。
    """
    payload = {
        "name": ISSUE_LABEL,
        "color": "d4c5f9",
        "description": "数据复核到期 / 配额待核实，由定时任务自动维护",
    }
    try:
        gh("POST", f"/repos/{repo}/labels", token, payload)
        return "created"
    except SystemExit:
        raise
    except urllib.error.HTTPError as exc:
        if exc.code == 422:
            return "exists"
        # 权限不足时建标签会 403；此时不阻断主流程——issue 正文里照样写清楚，
        # 只是少一个标签。让 issue 先开出来比因标签失败而什么都不做要好。
        print(f"WARN 建标签失败（HTTP {exc.code}）", file=sys.stderr)
        return "failed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只打印正文，不调 API")
    ap.add_argument("--today", help="覆盖基准日，仅用于本地演示")
    args = ap.parse_args()

    tracking = load_tracking()
    if args.today:
        tracking["generated_for"] = args.today

    pending = needs_attention(tracking)
    body = render_body(tracking, pending)

    if args.dry_run:
        print(body)
        return 0

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("缺少 GH_TOKEN / GITHUB_TOKEN 或 GITHUB_REPOSITORY，"
              "本地只做 --dry-run。", file=sys.stderr)
        return 1

    existing = find_open_issue(repo, token)
    want_issue = has_open_work(tracking, pending)

    if not want_issue:
        # 既没有待复核、也没有配额缺口：有 issue 就关掉，没有就什么都不做。
        # 「关掉」比「留着空表」好——一张写着「没有需要复核」的 issue 只会训练人忽略它。
        if existing:
            gh("PATCH", f"/repos/{repo}/issues/{existing['number']}", token,
               {"state": "closed", "state_reason": "completed"})
            print(f"closed #{existing['number']}（没有待复核项，也没有配额缺口）")
        else:
            print("没有待办，也没有 open issue，无需操作。")
        return 0

    if existing:
        gh("PATCH", f"/repos/{repo}/issues/{existing['number']}", token, {"body": body})
        print(f"updated #{existing['number']}（{len(pending)} 条待复核 / "
              f"{len(tracking.get('quota_unverified') or [])} 条配额待核实）")
        return 0

    label_state = ensure_label(repo, token)
    payload = {"title": ISSUE_TITLE, "body": body}
    if label_state != "failed":
        payload["labels"] = [ISSUE_LABEL]
    code, data = gh("POST", f"/repos/{repo}/issues", token, payload)
    print(f"created #{data.get('number')}（{len(pending)} 条待复核 / "
          f"{len(tracking.get('quota_unverified') or [])} 条配额待核实，label={label_state}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
