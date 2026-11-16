#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P2-1 方案 A 第一腿：把待扫项目的裁决材料预抽成工作表（纯脚本、零 LLM）。

为什么要它
----------
全量补扫两次死在「让 LLM 逐个读 37 个项目的 JSON」这种开放形态上：一次要读的
原文、结构化字段、引擎结论、漏网模式全在，模型自己去翻，翻到第几个项目就开始
漏。这里先把每个项目的裁决材料按**固定五块**压到一页，裁决腿只读这一页、每腿
2–4 个项目。

本脚本的边界（写死，不靠自觉）
------------------------------
- 只读：不写 data/、不写 docs/、不改 docs/audit 登记表、不改引擎。
- 名单不写死：从 P2-0 登记表里读「待扫」行。读不到 37 个就停手，报实际数字与差额。
- 零 LLM、零网络、零时间戳：同一份仓库状态跑两次必须逐字节一致。
- 只产出：<root>/p21-worksheets/<id>.md × N + index.csv。

五块内容
--------
1. 项目 id / 数据文件 / 全部 note 原文（按维度分开，标出哪条 note 命中哪类要求）
2. 结构化字段现状（note 已折到 §1，其余字段原样 JSON）
3. 引擎当前判定（A/B/C 三画像 × 逐维度 verdict + reason code，只读调用 judge()）
4. 已知漏网模式命中情况（P2-0 四例沉淀的检测器必查 + 引擎内全部 note 正则全查）
5. 空白裁决区（判过有据 / 不可判-甲 / 不可判-乙 / 需改数据 + 证据行），本腿不填
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import match_readiness as mr  # noqa: E402  （只读使用，见模块头「边界」）

ROOT = mr.ROOT
PROGRAMS = mr.PROGRAMS
REGISTRY = os.path.join(ROOT, "docs", "audit", "2026-11-14-P2-0-未结构化漏网清零.md")
OUT_DIR = os.path.join(ROOT, "p21-worksheets")

ROSTER_STATE = "待扫"
ROSTER_EXPECTED = 37
ROSTER_TOTAL = 41

# §1 分组的固定顺序：先资格相关的六维，再材料/时间线/工作条件，最后背景类。
DIM_ORDER = [
    ("program", "项目元信息"),
    ("passport", "护照 / 国籍"),
    ("age", "年龄"),
    ("education", "学历 / 资格"),
    ("other_requirements", "其他要求（含前置身份）"),
    ("language", "语言"),
    ("funds", "资金 / 预算"),
    ("timeline", "时间线 / 配额 / 费用"),
    ("documents", "材料清单"),
    ("work_conditions", "工作条件"),
    ("risks", "风险"),
    ("steps", "申请步骤"),
    ("sources", "来源"),
    ("other", "其他"),
]

DIM_LABEL = dict(DIM_ORDER)

# 检测器的人读标签：只写「它认什么」，不写结论。名字对不上时退回变量名，
# 这样引擎新增一个正则不会被这张表挡住（表不是白名单）。
DETECTOR_ZH = {
    "UNVERIFIED_PREFIX": "note 以 ⚠️ 开头（官方未公布/未核实）",
    "NOTE_OPEN_NATIONALITY": "「官方未按国籍设限」类明文",
    "LANG_BY_DESIGN": "官方不设语言分数线（面试/自证/仅计分）",
    "LANG_CEFR_LADDER": "官方用 CEFR / CLB / NCLC 档位表述",
    "LANG_NO_STANDARD_TEST": "「无需雅思/托福」类明文",
    "FUNDS_NO_FIXED": "官方不设固定资金金额",
    "FUNDS_INCOME": "门槛口径是年收入（不是存款）",
    "FUNDS_MONTHLY": "资金门槛按月计",
    "FUNDS_INFERRED": "金额为同类口径沿用/推定",
    "EXCHANGE_DISCLAIMER": "汇率估算免责声明（不构成门槛）",
    "EDU_YEARS_STRICT": "学制年限硬门槛（不少于 N 年）",
    "EDU_YEARS_DISQUALIFY": "学制不足即不合格（与上一条同段才成立）",
    "EDU_RECENCY": "毕业时限（申请日前 N 年内完成学业）",
    "EDU_PLACE": "学位须在指定国家/名单内院校完成",
    "EDU_BY_SPONSOR": "法规未规定学位层级、由 Sponsor 判断",
    "PRE_LOCAL_STATUS": "须先在该国持学生/居留身份并完成学业",
    "PRE_INSIDE": "递交时人须在该国境内（P1c 新立，与 PRE_OUTSIDE 互为镜像）",
    "PRE_OUTSIDE": "递交时人须在该国境外",
    "PRE_HOME_RESIDENCE": "须常驻护照所属地区",
    "PRE_CITIZENSHIP": "该项是国籍条件（护照维已在判）",
    "PRE_DOCUMENT": "该项是递交时自备文件（租约等）",
    "JOB_PLACEMENT": "岗位须预先落实（Sponsor placement）",
    "PARTICIPANT_CATEGORY": "须属于某几类参与人身份之一",
    "CREDENTIAL_RECOGNITION": "学历/职业资格须经主管机构认定",
    "POINTS_THRESHOLD": "积分门槛分数（积分达到 N 分）",
    "EMPLOYER_OFFER": "先有具体雇主的合格聘用（job offer）",
    "AGE_NO_THRESHOLD_EVIDENCE": "年龄无阈值的证据句（配 ⚠️ 才成立甲类豁免）",
}

# P2-0 四例沉淀下来的模式检测器：裁决腿每次都要看这六条，不许跳。
P20_SEEDS = [
    ("nl-orientation-year", ["EDU_RECENCY"]),
    ("us-j1-camp-counselor", ["JOB_PLACEMENT", "PARTICIPANT_CATEGORY"]),
    ("de-chancenkarte", ["CREDENTIAL_RECOGNITION", "POINTS_THRESHOLD"]),
    ("no-skilled-worker", ["EMPLOYER_OFFER"]),
]

VERDICT_OPTIONS = ["判过有据", "不可判-甲", "不可判-乙", "需改数据"]


# --------------------------------------------------------------------------
# 名单：从 P2-0 登记表读「待扫」
# --------------------------------------------------------------------------


class RosterError(RuntimeError):
    pass


def parse_registry(path: str | None = None) -> tuple[list[str], list[str]]:
    """返回 (待扫 id 列表, 全部登记 id 列表)，两者都按表内顺序（表本身已按 id 排序）。

    只认表格行：`| \\`id\\` | 状态 | … |`。读不出 37 个由调用方停手，这里不兜底、
    不补名单——补一条就等于替登记表决定扫哪些项目。

    `path` 默认在**调用时**取 REGISTRY（不写成默认参数值）：默认参数在 def 执行时
    就绑定了，之后改 REGISTRY 会被静默忽略——一个只在换名单时才显形的坑。
    """
    path = path or REGISTRY
    with io.open(path, encoding="utf-8") as fh:
        text = fh.read()
    row = re.compile(r"^\|\s*`([a-z0-9][a-z0-9-]*)`\s*\|\s*([^|]+?)\s*\|", re.M)
    all_ids: list[str] = []
    todo: list[str] = []
    for m in row.finditer(text):
        pid, state = m.group(1), m.group(2).strip()
        if pid in all_ids:
            continue
        all_ids.append(pid)
        if state == ROSTER_STATE:
            todo.append(pid)
    return todo, all_ids


def load_doc(pid: str) -> tuple[dict, str]:
    rel = "data/programs/%s.json" % pid
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh), rel


# --------------------------------------------------------------------------
# 文本抽取：note 全文 + 检测器语料
# --------------------------------------------------------------------------


def _is_note_key(key: str) -> bool:
    return key == "note" or key.endswith("_note")


def _path_sort_key(path: str) -> tuple:
    """路径里的数字按下标排（documents[2] 在 documents[10] 前），其余按字面。"""
    return tuple(
        (0, int(tok)) if tok.isdigit() else (1, tok)
        for tok in re.split(r"(\d+)", path)
        if tok
    )


def collect_notes(node, path: str = "", out: list | None = None) -> list[tuple[str, str]]:
    """收全部 note 字段（`note` 与 `*_note`），返回 [(path, 原文)]，按路径排序。"""
    if out is None:
        out = []
    if isinstance(node, dict):
        for k, v in node.items():
            p = "%s.%s" % (path, k) if path else k
            if isinstance(v, str) and _is_note_key(k):
                out.append((p, v))
            elif isinstance(v, (dict, list)):
                collect_notes(v, p, out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            collect_notes(v, "%s[%d]" % (path, i), out)
    return out


def collect_document_names(doc: dict) -> list[tuple[str, str]]:
    return [
        ("documents[%d].name" % i, str(d.get("name") or ""))
        for i, d in enumerate(doc.get("documents") or [])
        if d.get("name")
    ]


# 结构里的字段名与 §1 分组名不完全一致（passport_types 就是 passport 维），
# 别名只做归类，不改原文路径的写法。
DIM_ALIAS = {
    "passport_types": "passport",
    "other_requirements": "other_requirements",
    "schedule": "timeline",
    "windows": "timeline",
    "fees": "timeline",
    "quota": "timeline",
}


def note_dim(path: str) -> str:
    head = path.split(".")[0].split("[")[0]
    if head == "eligibility":
        sub = path.split(".")[1].split("[")[0] if "." in path else ""
        sub = DIM_ALIAS.get(sub, sub)
        return sub if sub in DIM_LABEL else "other"
    head = DIM_ALIAS.get(head, head)
    return head if head in DIM_LABEL else "other"


def detectors() -> list[tuple[str, re.Pattern]]:
    """引擎里全部 note 模式正则，按变量名排序（不看定义顺序，保证确定性）。"""
    items = [
        (name, val)
        for name, val in vars(mr).items()
        if isinstance(val, re.Pattern)
    ]
    return sorted(items, key=lambda kv: kv[0])


def detector_hits(doc: dict) -> dict[str, list[str]]:
    """每个检测器在「引擎真正读的文本」上的命中路径（最多列 3 处，计数另给）。

    语料严格等于引擎读入面：全部 note 字段 + documents[].name。刻意不含
    program.summary / risks：那些是给人看的散文，把那里的「积分达到 70 分」
    算成命中，会造出一条原文并不存在的门槛。
    """
    corpus = collect_notes(doc)
    corpus += collect_document_names(doc)
    corpus.sort(key=lambda kv: _path_sort_key(kv[0]))
    hits: dict[str, list[str]] = {}
    for name, pat in detectors():
        got = [p for p, text in corpus if pat.search(text)]
        hits[name] = got
    return hits


# --------------------------------------------------------------------------
# §1 note 原文（按维度）
# --------------------------------------------------------------------------


def render_notes(doc: dict, hits: dict[str, list[str]]) -> str:
    notes = collect_notes(doc)
    notes.sort(key=lambda kv: _path_sort_key(kv[0]))
    buckets: dict[str, list[tuple[str, str]]] = {k: [] for k, _ in DIM_ORDER}
    for path, text in notes:
        buckets.setdefault(note_dim(path), []).append((path, text))

    lines: list[str] = ["## 1. note 原文（按维度）", ""]
    lines.append(
        "共 %d 条 note。每条标出：落在哪一维、命中了哪些已沉淀的模式检测器"
        "（检测器只说明「原文长这样」，不说明结论）。" % len(notes)
    )
    lines.append("")
    if not notes:
        lines.append("_本项目无 note 字段。_")
        lines.append("")
    for key, label in DIM_ORDER:
        items = buckets.get(key) or []
        if not items:
            continue
        lines.append("### %s" % label)
        lines.append("")
        for path, text in items:
            fired = [n for n, paths in hits.items() if path in paths]
            if fired:
                mark = "命中检测器：" + "、".join("`%s`" % n for n in fired)
            else:
                mark = "未命中任何已沉淀的模式检测器"
            lines.append("- `%s` ｜ %s" % (path, mark))
            lines.append("")
            lines.append("~~~~text")
            lines.append(text.rstrip("\n"))
            lines.append("~~~~")
            lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# §2 结构化字段现状
# --------------------------------------------------------------------------


def _strip_notes(node):
    """把 note 值换成指向 §1 的指针，其余一律不动（不做任何语义加工）。"""
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if isinstance(v, str) and _is_note_key(k):
                out[k] = "（原文见 §1）"
            else:
                out[k] = _strip_notes(v)
        return out
    if isinstance(node, list):
        return [_strip_notes(v) for v in node]
    return node


def render_structured(doc: dict) -> str:
    el = _strip_notes(doc.get("eligibility") or {})
    tl = doc.get("timeline") or {}
    tl_slim = {
        "mechanism": tl.get("mechanism"),
        "quota_status": tl.get("quota_status"),
        "quota": tl.get("quota"),
        "schedule": _strip_notes(tl.get("schedule") or {}),
    }
    docs_slim = [
        {
            "name": d.get("name"),
            "required": d.get("required"),
            "prepare_days": d.get("prepare_days"),
        }
        for d in (doc.get("documents") or [])
    ]
    wc = _strip_notes(doc.get("work_conditions") or {})
    lines = [
        "## 2. 结构化字段现状（原样，未加工）",
        "",
        "note 字段已折到 §1 并在下方以 `（原文见 §1）` 占位；其余字段逐字节原样打印，"
        "排序即文件内顺序。",
        "",
        "### eligibility",
        "",
        "~~~~json",
        json.dumps(el, ensure_ascii=False, indent=1, sort_keys=False),
        "~~~~",
        "",
        "### timeline（机制 / 配额 / 窗口）",
        "",
        "~~~~json",
        json.dumps(tl_slim, ensure_ascii=False, indent=1, sort_keys=False),
        "~~~~",
        "",
        "### documents（名称 / 是否必交 / 准备天数）",
        "",
        "~~~~json",
        json.dumps(docs_slim, ensure_ascii=False, indent=1, sort_keys=False),
        "~~~~",
        "",
        "### work_conditions",
        "",
        "~~~~json",
        json.dumps(wc, ensure_ascii=False, indent=1, sort_keys=False),
        "~~~~",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# §3 引擎当前判定
# --------------------------------------------------------------------------


STATE_ZH = {"can": "能申", "cannot": "不能申", "gap": "差什么", "unknown": "不可判"}
KIND_ZH = {"pass": "过", "fail": "否", "gap": "差", "silent": "不表态", "na": "不适用"}
CLS_ZH = {"design": "甲（设计性）", "avoidable": "乙（可避免）", None: "—（非不可判）"}

PROFILE_DESC = {
    "A": "大陆 / 21 / 本科在读 / IELTS 6.0 / 预算 3 万",
    "B": "大陆 / 28 / 本科毕业 / 无 IELTS / 预算 8 万",
    "C": "台湾 / 25 / 本科毕业 / IELTS 6.5 / 预算 5 万",
}


def judge_all(doc: dict) -> dict[str, dict]:
    out = {}
    for name, pr in mr.SAMPLES.items():
        state, dims = mr.judge(doc, pr)
        out[name] = {
            "state": state,
            "dims": dims,
            "cls": mr.undecidable_class(dims, doc) if state == "unknown" else None,
        }
    return out


def _dim_detail(d: dict) -> str:
    bits = [d.get("why") or ""]
    if d.get("need"):
        bits.append("门槛：%s" % d["need"])
    if d.get("have"):
        bits.append("你的：%s" % d["have"])
    if d.get("inferred"):
        bits.append("（文本推断）")
    return "；".join(b for b in bits if b)


def render_verdicts(verdicts: dict[str, dict]) -> str:
    lines = ["## 3. 引擎当前判定（只读调用 judge，rules_version=%d）" % mr.RULES_VERSION, ""]
    for name in mr.SAMPLES:
        v = verdicts[name]
        lines.append("### 画像 %s（%s）" % (name, PROFILE_DESC[name]))
        lines.append("")
        lines.append(
            "结论：**%s**（`%s`）｜ 不可判分类：%s"
            % (STATE_ZH.get(v["state"], v["state"]), v["state"], CLS_ZH.get(v["cls"], v["cls"]))
        )
        lines.append("")
        lines.append("| 维度 | kind | code | 说明 |")
        lines.append("|---|---|---|---|")
        for d in v["dims"]:
            lines.append(
                "| %s | %s | `%s` | %s |"
                % (
                    d.get("dim"),
                    KIND_ZH.get(d.get("kind"), d.get("kind")),
                    d.get("code"),
                    _dim_detail(d).replace("|", "\\|"),
                )
            )
        lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# §4 漏网模式命中
# --------------------------------------------------------------------------


# 检测器 → 真正把它变成判定结论的闸门函数 → 它应产出的 (dim, code)。
# 三者放一行是刻意的：写在两处就会各自漂移，而这张对账表的存在意义正是
# 「原文命中 ≠ 已兜住」。函数与 code 都直接从引擎取，不在这边复写一份。
#
# 第四列 mode：
#   gate —— 该检测器自己能把结论拉成 silent/gap/na；
#   aux  —— 只做修饰，**必须与另一条同现**才成立。目前只有 POINTS_THRESHOLD：
#           引擎注释（match_readiness.py 中 POINTS_THRESHOLD 定义处）写明它只被
#           「资格认定」分支引用，单独出现（如奥地利红白红卡 70 分）不构成缺口。
def _kind_gate(kind: str):
    """「引擎是否读出了这一类」——按 `precondition_kinds()` 的**全集**判，不按单值。

    P1c 之前只有单值 `precondition_kind()`，一行对一个 kind 还算对得上；拆成两族
    之后单值只返回最靠前的那一类，us-f1-opt / de-20-job-search 会同时有
    `local_status` 与 `inside`，用单值判会让 `PRE_INSIDE` 那一行永远报「未拉起」——
    而它其实已经兜住了。所以这里问的是「这一类在不在全集里」。
    """
    return lambda doc: kind in mr.precondition_kinds(doc)


def _family_codes(code: str) -> tuple[str, ...]:
    """一个前置码的**同族前缀**：接地后可能产出的三态码都归同一族。

    `pre_inside_country` / `pre_outside_country` / `pre_home_residence` 这三族在
    P1d / P1e 接地后各会产出 `<原码>_ok`（pass）与 `<原码>_no`（fail）。原码本身
    仍是「画像缺字段 → silent」的诚实码，**语义一个字节没动**。

    对账表若只认原码，就会在每一个接地项目上把「已判 pass」写成「闸门拉起但
    §3 无该码」——那是把**接地成功**报成**漏网**，比漏报更糟：它会训练读表的人
    忽略这张表。所以这里按族认，且只对这三族放宽——其余码（`pre_local_status`、
    `pre_dependents_*` 等）没有 <code>_ok/_no 形态，行为与改前完全一致。
    """
    if code in ("pre_inside_country", "pre_outside_country", "pre_home_residence"):
        return (code, code + "_ok", code + "_no")
    return (code,)


GATES = [
    ("EDU_RECENCY", mr.edu_recency_years, None, "education", "edu_recency_unknown", "gate"),
    ("EDU_YEARS_STRICT", mr.edu_years_required, None, "education", "edu_years_unknown", "gate"),
    ("JOB_PLACEMENT", mr.job_placement_required, None, "precondition", "pre_job_placement", "gate"),
    ("PARTICIPANT_CATEGORY", mr.participant_category_required, None, "education", "edu_category_unknown", "gate"),
    ("CREDENTIAL_RECOGNITION", mr.credential_recognition_required, None, "education", "edu_credential_unknown", "gate"),
    ("POINTS_THRESHOLD", mr.points_threshold, None, "education", "edu_credential_unknown", "aux"),
    ("EMPLOYER_OFFER", mr.employer_offer_required, None, "precondition", "pre_employer_offer", "gate"),
    ("PRE_LOCAL_STATUS", _kind_gate("local_status"), None, "precondition", "pre_local_status", "gate"),
    ("PRE_INSIDE", _kind_gate("inside"), None, "precondition", "pre_inside_country", "gate"),
    ("PRE_OUTSIDE", _kind_gate("outside"), None, "precondition", "pre_outside_country", "gate"),
    ("PRE_HOME_RESIDENCE", _kind_gate("home_residence"), None, "precondition", "pre_home_residence", "gate"),
    ("PRE_CITIZENSHIP", _kind_gate("citizenship"), None, "precondition", "pre_citizenship_basis", "gate"),
    ("PRE_DOCUMENT", _kind_gate("document"), None, "precondition", "pre_document_basis", "gate"),
]


PRE_DETS = (
    "PRE_LOCAL_STATUS",
    "PRE_INSIDE",
    "PRE_OUTSIDE",
    "PRE_HOME_RESIDENCE",
    "PRE_CITIZENSHIP",
    "PRE_DOCUMENT",
)


def read_surface(det: str, doc: dict) -> set[str]:
    """该检测器**实际被引擎读取**的路径集合。

    §4 的命中语料是「全部 note + 材料名」，比闸门的读取面宽：`PRE_*` 只作用于
    必填的 `residency_requirement` / `location_requirement`，`EDU_YEARS_STRICT`
    只读 `education.note`。
    不把这两个面分开，一份租约材料的 note 就会被报成「前置身份要求漏网」——
    那是把语料面差异说成判读缺陷。
    """
    el = doc.get("eligibility") or {}
    paths: set[str] = set()

    def add_note(prefix: str, obj) -> None:
        if isinstance(obj, dict) and obj.get("note"):
            paths.add(prefix + ".note")

    docs_surface = []
    for i, d in enumerate(doc.get("documents") or []):
        if d.get("required") is True:
            if d.get("note"):
                docs_surface.append("documents[%d].note" % i)
            if d.get("name"):
                docs_surface.append("documents[%d].name" % i)

    if det == "EDU_RECENCY":
        add_note("eligibility.education", el.get("education"))
        add_note("eligibility.age", el.get("age"))
    elif det in ("EDU_YEARS_STRICT", "PARTICIPANT_CATEGORY"):
        add_note("eligibility.education", el.get("education"))
    elif det in ("CREDENTIAL_RECOGNITION", "POINTS_THRESHOLD"):
        add_note("eligibility.education", el.get("education"))
        add_note("eligibility.passport_types", el.get("passport_types"))
        paths.update(docs_surface)
    elif det == "JOB_PLACEMENT":
        paths.update(docs_surface)
        for i, r in enumerate(el.get("other_requirements") or []):
            if r.get("required") is True and r.get("type") == "internship_contract":
                paths.add("eligibility.other_requirements[%d].note" % i)
    elif det == "EMPLOYER_OFFER":
        paths.update(docs_surface)
        for i, r in enumerate(el.get("other_requirements") or []):
            if r.get("required") is True:
                paths.add("eligibility.other_requirements[%d].note" % i)
        add_note("eligibility.education", el.get("education"))
    elif det in PRE_DETS:
        # P1c：两族都要算作判读面。只收 residency_requirement 会把改到
        # location_requirement 的在地条整条报成「面外」——那是把拆分类别之后
        # 的正常结果说成漏网。
        for i, r in enumerate(el.get("other_requirements") or []):
            if r.get("required") is True and r.get("type") in (
                "residency_requirement",
                "location_requirement",
            ):
                paths.add("eligibility.other_requirements[%d].note" % i)
    return paths


def rule_holds(det: str, doc: dict) -> bool:
    """检测器命中了、但引擎的闸门不成立——这是设计如此，还是漏网？

    只对两种真有这条区分的检测器下判断，其余一律返回 False（照「需人工看」报）：

    - `EDU_YEARS_STRICT`：引擎要求**同一段 note 里同时**出现「不满足/不达/不符合」
      （EDU_YEARS_DISQUALIFY）才认为是硬门槛，见 `edu_years_required()`。只命中
      年限、没命中不合格措辞的，是「读过 N 年」而非「不足 N 年就不行」。
    - `PRE_*` 六个检测器共用 `precondition_kinds()` 的两族分类（身份族走
      `_classify_identity`：local_status → home_residence → citizenship → document；
      在地族走 `_classify_location`：inside → outside → home_residence →
      citizenship → document）。同一族里一段原文同时命中两条时只有优先级最高的
      那条拉起闸门，其余必然不拉起：这是「同一段原文只判一次」，不是漏网。
      判据是 `precondition_kinds()` 里出现了至少一个具体类别（不含 unclassified）
      ——说明这条要求**已被处置**。
    """
    if det == "EDU_YEARS_STRICT":
        edu = (doc.get("eligibility") or {}).get("education") or {}
        return bool(mr.EDU_YEARS_STRICT.search(edu.get("note") or "")) and not bool(
            mr.EDU_YEARS_DISQUALIFY.search(edu.get("note") or "")
        )
    if det in PRE_DETS:
        return bool(set(mr.precondition_kinds(doc)) - {"unclassified"})
    return False


def classify_row(det, mode, gate, kind, key, hit_all, hit_gate, doc) -> str:
    """一行的对账结论。语料命中与判读面命中分开报，不混成一句。"""
    if mode == "aux":
        partner = bool(mr.credential_recognition_required(doc))
        if gate and not partner:
            return "辅助项：原文有分数但未与「资格认定」同现 → 按引擎设计不构成缺口，不记漏网"
        if gate and partner:
            return "辅助项：与「资格认定」同现，写入 `%s`（%s）" % (key, KIND_ZH.get(kind, kind))
        return "—"
    if gate and kind == "silent":
        return "已兜住·不可判（§3 有 `%s`）" % key
    if gate and kind == "gap":
        return "已兜住·差什么（§3 有 `%s`）" % key
    if gate and kind == "na":
        return "已归 na（§3 有 `%s`，不占不可判）" % key
    if gate and kind == "pass":
        # P1e：接地后前置维第一次可能判 pass（画像字段已采集且满足要求）。
        # 这既不是漏网也不是缺口，是「这条要求真的满足了」——必须单列一句，
        # 否则它会掉进下面的 fallback，被报成「闸门拉起但 §3 无该码」。
        return "已兜住·已满足（§3 有 `%s`）" % key
    if gate and kind == "fail":
        return "已兜住·不满足（§3 有 `%s`）" % key
    if gate:
        return "闸门拉起但 §3 无 `%s`" % key
    if hit_all and not hit_gate:
        return "原文只在**判读面外**命中（引擎不读该处，或该处不是必填前置）→ 不是漏网"
    if hit_all and rule_holds(det, doc):
        return "原文命中，但闸门按自身设计不成立（见规则备注）→ 不算漏网，裁决腿复核一句"
    if hit_all:
        return "原文命中但闸门未拉起 → 需人工看"
    return "—"


def gate_rows(doc: dict, hits: dict[str, list[str]], verdicts: dict[str, dict]) -> list[tuple[str, str, str, str]]:
    """每个检测器的三件事对上没有：原文命中 / 闸门是否拉起 / §3 里有没有对应 code。

    闸门读的是引擎的探针函数本身（job_placement_required 等），不是再写一遍正则；
    code 读的是 judge() 在三画像下的实际输出。两者任一缺失都照实报，不猜。
    """
    codes = {
        "%s:%s" % (d.get("dim"), d.get("code")): d.get("kind")
        for name in mr.SAMPLES
        for d in verdicts[name]["dims"]
    }
    rows = []
    for det, fn, expected, dim, code, mode in GATES:
        raw = fn(doc)
        gate = bool(raw == expected) if expected is not None else bool(raw)
        hit_all = bool(hits.get(det))
        surface = read_surface(det, doc)
        hit_gate = hit_all and bool(surface) and any(p in surface for p in hits.get(det, []))
        # 同族任一码在场即算「§3 有这个码」：接地后原码会细分出 _ok/_no，
        # 只认原码会把已判 pass 的项目报成漏网（见 _family_codes 的说明）。
        family = [c for c in _family_codes(code) if "%s:%s" % (dim, c) in codes]
        key = "%s:%s" % (dim, family[0] if family else code)
        # 同族多个码并存时（理论上不会，原码只在 silent 时出现）取第一个可达的，
        # 但 kind 按在场的最差取，避免「pass 掩盖 silent」。
        order = {"fail": 3, "silent": 2, "gap": 1, "na": 0, "pass": 0}
        kind = (
            max((codes["%s:%s" % (dim, c)] for c in family), key=lambda k: order.get(k, 0))
            if family
            else None
        )
        state = classify_row(det, mode, gate, kind, key, hit_all, hit_gate, doc)
        rows.append(
            (
                det,
                "命中" if hit_all else "未命中",
                "命中" if hit_gate else ("面外" if hit_all else "—"),
                "拉起" if gate else "未拉起",
                state,
            )
        )
    return rows


def render_detectors(doc: dict, hits: dict[str, list[str]], verdicts: dict[str, dict], pid: str = "") -> str:
    lines = ["## 4. 已知漏网模式命中情况", ""]
    lines.append(
        "检测器直接在引擎的只读接口上取（`vars(match_readiness)` 里的全部正则），"
        "语料 = 全部 note + `documents[].name`，不含 summary/risks 散文。"
    )
    lines.append("")
    lines.append("### 4.1 P2-0 四例沉淀的检测器（必查）")
    lines.append("")
    lines.append("| 来源项目 | 检测器 | 认什么 | 结果 | 命中处 |")
    lines.append("|---|---|---|---|---|")
    for src, names in P20_SEEDS:
        for n in names:
            paths = hits.get(n, [])
            lines.append(
                "| `%s` | `%s` | %s | %s | %s |"
                % (
                    src,
                    n,
                    DETECTOR_ZH.get(n, "—"),
                    "**命中**" if paths else "未命中",
                    "<br>".join("`%s`" % p for p in paths) or "—",
                )
            )
    lines.append("")
    lines.append("### 4.3 有闸门的检测器：原文 ↔ 闸门 ↔ §3 code 对账")
    lines.append("")
    lines.append(
        "只有能改变结论的检测器才进这张表。四列必须对上：原文命中 → 判读面命中 → "
        "闸门函数拉起 → §3 出现对应 code。**判读面**指引擎真正读的那几处"
        "（`PRE_*` 只读必填的 `residency_requirement` 与 `location_requirement`，"
        "`EDU_YEARS_STRICT` 只读 `education.note`）；只在面外命中不算漏网。"
    )
    lines.append("")
    lines.append(
        "整张表全为「未命中」不等于本项目没有未被兜住的要求：这张表只覆盖**已有检测器**"
        "认得出的写法，措辞不同的要求照样会漏。原文在 §1，判据在 §3，裁决腿不能只看这张表。"
    )
    lines.append("")
    lines.append("| 检测器 | 原文命中（全部 note） | 判读面命中 | 闸门 | 对账结论 |")
    lines.append("|---|---|---|---|---|")
    for det, hit_all, hit_gate, gate, state in gate_rows(doc, hits, verdicts):
        lines.append("| `%s` | %s | %s | %s | %s |" % (det, hit_all, hit_gate, gate, state))
    lines.append("")
    lines.append("### 4.4 引擎内全部 note 正则（%d 条，按变量名排序）" % len(hits))
    lines.append("")
    lines.append(
        "「命中」只说明原文里有这句话，**不等于**该要求已被判读入口兜住："
        "是否兜住写在 §3 的 code 里，由裁决腿对账。成对检测器"
        "（`EDU_YEARS_STRICT` + `EDU_YEARS_DISQUALIFY`、`FUNDS_INFERRED` + "
        "`EXCHANGE_DISCLAIMER`）必须同时成立才算数，单命中一条是噪声。"
    )
    lines.append("")
    lines.append("| 检测器 | 认什么 | 结果 | 命中条数 |")
    lines.append("|---|---|---|---|")
    for name, _pat in detectors():
        paths = hits.get(name, [])
        lines.append(
            "| `%s` | %s | %s | %d |"
            % (name, DETECTOR_ZH.get(name, "—"), "命中" if paths else "未命中", len(paths))
        )
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# §5 空白裁决区
# --------------------------------------------------------------------------


def render_blank(doc: dict, pid: str) -> str:
    lines = ["## 5. 裁决区（本腿留白，裁决腿填写）", ""]
    lines.append("该项目 note 载明的、结构化字段表达不了的要求是否已被判读机制兜住？")
    lines.append("")
    lines.append("选项（只勾一个）：")
    lines.append("")
    for opt in VERDICT_OPTIONS:
        lines.append("- [ ] %s" % opt)
    lines.append("")
    lines.append("| 证据行 | 填什么 |")
    lines.append("|---|---|")
    lines.append("| 要求原文位置 | `<path>`（如 `eligibility.education.note`）+ 一句原句 |")
    lines.append("| 判读入口 | 哪个 code / 哪条检测器兜住了它；没有就写「无」 |")
    lines.append("| 理由（≤2 句） | 为什么是这一档 |")
    lines.append("| 若需改数据 | 字段名 + 建议值 + 依据来源 URL |")
    lines.append("| 签字 | `<腿 ID> / <日期>` |")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 单张工作表
# --------------------------------------------------------------------------


def render_sheet(pid: str, rel: str, doc: dict) -> str:
    hits = detector_hits(doc)
    verdicts = judge_all(doc)
    name = (doc.get("program") or {}).get("name") or ""
    head = [
        "# P2-1 工作表 · `%s`" % pid,
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 项目 id | `%s` |" % pid,
        "| 项目名 | %s |" % name.replace("|", "\\|"),
        "| 数据文件 | `%s` |" % rel,
        "| 名单来源 | `docs/audit/2026-11-14-P2-0-未结构化漏网清零.md`（状态「待扫」） |",
        "| 引擎 | `scripts/match_readiness.py` rules_version=%d |" % mr.RULES_VERSION,
        "| 本页性质 | 纯脚本预抽，未做任何裁决；§5 由裁决腿填写 |",
        "",
        "五块导航：§1 note 原文 ｜ §2 结构化字段 ｜ §3 引擎判定 ｜ §4 漏网模式 ｜ §5 裁决区（空白）",
        "",
    ]
    return "\n".join(
        head
        + [
            render_notes(doc, hits),
            render_structured(doc),
            render_verdicts(verdicts),
            render_detectors(doc, hits, verdicts, pid),
            render_blank(doc, pid),
        ]
    ).rstrip("\n") + "\n"


def reason_codes(verdicts: dict[str, dict], name: str = "C") -> str:
    """C 画像的 reason codes 摘要：只留驱动结论的（silent / fail / gap），按维度顺序。"""
    out = []
    for d in verdicts[name]["dims"]:
        if d.get("kind") in ("silent", "fail", "gap"):
            out.append("%s:%s" % (d.get("dim"), d.get("code")))
    return ";".join(out)


# --------------------------------------------------------------------------
# 入口
# --------------------------------------------------------------------------


def build(out_dir: str = OUT_DIR) -> dict:
    todo, all_ids = parse_registry()
    if len(all_ids) != ROSTER_TOTAL:
        raise RosterError(
            "登记表读出 %d 行，应为 %d 行 —— 表结构变了，停手。" % (len(all_ids), ROSTER_TOTAL)
        )
    if len(todo) != ROSTER_EXPECTED:
        missing = sorted(set(all_ids) - set(todo))
        raise RosterError(
            "「待扫」读出 %d 个，应为 %d 个。非待扫（%d）：%s"
            % (len(todo), ROSTER_EXPECTED, len(missing), "、".join(missing))
        )

    if not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    rows = []
    written = []
    for pid in todo:
        doc, rel = load_doc(pid)
        text = render_sheet(pid, rel, doc)
        path = os.path.join(out_dir, "%s.md" % pid)
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        written.append(path)
        v = judge_all(doc)
        rows.append(
            [pid, v["C"]["state"], v["C"]["cls"] or "", reason_codes(v, "C")]
        )

    index = os.path.join(out_dir, "index.csv")
    with io.open(index, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["id", "c_state", "c_cls", "c_codes"])
        for r in rows:
            w.writerow(r)
    written.append(index)

    # 目录里只留本次名单的产物：多出来的 .md 会让「37/37」变成一句空话。
    expected = {"%s.md" % pid for pid in todo} | {"index.csv"}
    stale = sorted(n for n in os.listdir(out_dir) if n.endswith(".md") and n not in expected)
    return {
        "roster": todo,
        "files": written,
        "rows": rows,
        "stale": stale,
        "sheet_count": len(todo),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P2-1 工作表生成（确定性，零 LLM）")
    ap.add_argument("--out", default=OUT_DIR, help="输出目录（默认 <root>/p21-worksheets）")
    ap.add_argument("--list", action="store_true", help="只打印名单与计数，不写文件")
    args = ap.parse_args(argv)

    try:
        todo, all_ids = parse_registry()
    except RosterError as exc:  # pragma: no cover - 防御
        print("ROSTER_ERROR: %s" % exc, file=sys.stderr)
        return 2

    if args.list:
        print("登记表行数：%d" % len(all_ids))
        print("「待扫」行数：%d" % len(todo))
        for pid in todo:
            print(pid)
        return 0 if len(todo) == ROSTER_EXPECTED else 1

    try:
        rep = build(args.out)
    except RosterError as exc:
        print("ROSTER_ERROR: %s" % exc, file=sys.stderr)
        return 2

    print("名单实读：%d" % len(rep["roster"]))
    print("工作表：%d 张 + index.csv" % rep["sheet_count"])
    if rep["stale"]:
        print("目录内多余 .md（不在名单里，未删除）：%s" % "、".join(rep["stale"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
