"""P1e 翻转归因表：把当前 audit() 与 p1e 基线（3a2d819 / rules_version 10）逐条比对。

输出每一处 (项目 × 画像) 的三态变化与**前置维**的 code 变化，并逐条给出归因。
需要可复算 —— 回执 §4 引用本脚本路径。

用法：
    python scripts/p1e_flip_audit.py            # 用默认基线路径
    python scripts/p1e_flip_audit.py <base.json>

基线怎么来的（可重现，不依赖工作区外的快照）：
    git worktree add <tmp> 3a2d819 --detach
    python <repo>/scripts/p1e_flip_audit.py --dump <tmp> <base.json>
"""
import io
import json
import os
import sys

sys.path.insert(0, "scripts")
import match_readiness as mr  # noqa: E402

DEFAULT_BASE = r"C:\Users\16256\work\.legs\p1e-before.json"

# 本单接地的两族。翻转只有由这两族驱动才算「本单因果」；其余一律报为可疑。
FAMILIES = ("pre_outside_country", "pre_home_residence")


def dump(root: str, out: str) -> None:
    """对任意一棵树 dump (项目 × 画像) 的 {state, cls, dims}。"""
    root = os.path.abspath(root)
    sys.path.insert(0, os.path.join(root, "scripts"))
    payload = {
        "root": root,
        "rules_version": mr.RULES_VERSION,
        "judge": {
            doc["program"]["id"]: {
                name: {
                    "state": pr_state,
                    "dims": [[d["dim"], d["kind"], d["code"]] for d in dims],
                }
                for name, (pr_state, dims) in {
                    n: mr.judge(doc, p) for n, p in mr.SAMPLES.items()
                }.items()
            }
            for doc in mr.load_programs()
        },
    }
    with io.open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print("dumped %s (rules_version %d)" % (out, mr.RULES_VERSION))


def family_of(code: str) -> str | None:
    for fam in FAMILIES:
        if code.startswith(fam):
            return fam
    return None


def main() -> int:
    if len(sys.argv) >= 4 and sys.argv[1] == "--dump":
        dump(sys.argv[2], sys.argv[3])
        return 0

    base_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE
    base = json.load(io.open(base_path, encoding="utf-8"))
    docs = {d["program"]["id"]: d for d in mr.load_programs()}
    print("# 基线：%s（rules_version %s）" % (base_path, base.get("rules_version")))
    print("# 当前：rules_version %d\n" % mr.RULES_VERSION)

    state_flips, dim_flips = [], []
    for pid, per_sample in base["judge"].items():
        for name in ("A", "B", "C"):
            b = per_sample.get(name)
            if not b:
                continue
            state, dims = mr.judge(docs[pid], mr.SAMPLES[name])
            now = [[d["dim"], d["kind"], d["code"]] for d in dims]
            bpre = [d for d in b["dims"] if d[0] == "precondition"]
            npre = [d for d in now if d[0] == "precondition"]
            if state != b["state"]:
                state_flips.append({"pid": pid, "sample": name,
                                    "before": b["state"], "after": state,
                                    "bpre": bpre, "npre": npre})
            elif bpre != npre:
                dim_flips.append({"pid": pid, "sample": name, "state": state,
                                  "bpre": bpre, "npre": npre})

    def changed_codes(b, n):
        bc = {d[2] for d in b}
        nc = {d[2] for d in n}
        return sorted(bc - nc), sorted(nc - bc)

    print("## 一、三态翻转（%d 条）\n" % len(state_flips))
    if state_flips:
        print("| 画像 | 项目 | 改前 | 改后 | 消失的前置码 | 新增的前置码 | 归因 |")
        print("|---|---|---|---|---|---|---|")
        for f in sorted(state_flips, key=lambda x: (x["sample"], x["pid"])):
            gone, new = changed_codes(f["bpre"], f["npre"])
            fams = {family_of(c) for c in gone + new} - {None}
            attr = (
                "**%s 接地驱动**" % " / ".join(sorted(fams))
                if fams
                else "!! 非本单两族驱动，必须逐条解释"
            )
            print("| %s | %s | %s | **%s** | %s | %s | %s |" % (
                f["sample"], f["pid"], f["before"], f["after"],
                ", ".join("`%s`" % c for c in gone) or "—",
                ", ".join("`%s`" % c for c in new) or "—",
                attr,
            ))
        bad = [
            f for f in state_flips
            if not ({family_of(c) for c in
                     changed_codes(f["bpre"], f["npre"])[0] +
                     changed_codes(f["bpre"], f["npre"])[1]} - {None})
        ]
        print("\n非两族驱动的翻转：%d 条%s" % (len(bad), "" if not bad else " ← 必须解释"))
    else:
        print("（无）")

    print("\n## 二、前置维变化但三态不变（%d 条）\n" % len(dim_flips))
    if dim_flips:
        print("| 画像 | 项目 | 三态 | 消失的前置码 | 新增的前置码 | 为什么三态没变 |")
        print("|---|---|---|---|---|---|")
        for f in sorted(dim_flips, key=lambda x: (x["sample"], x["pid"])):
            gone, new = changed_codes(f["bpre"], f["npre"])
            print("| %s | %s | %s | %s | %s | 别的维仍挡着（见 §4 逐条） |" % (
                f["sample"], f["pid"], f["state"],
                ", ".join("`%s`" % c for c in gone) or "—",
                ", ".join("`%s`" % c for c in new) or "—",
            ))
    else:
        print("（无）")

    rep = mr.audit()
    print("\n## 三、三画像计数（当前）")
    for n, v in rep["samples"].items():
        print(
            "- %s：能申 %d / 不能申 %d / 差什么 %d / 不可判 %d ｜ 乙类 %d(%.4f, 闸门 %s) "
            "｜ 全口径 %.4f ｜ 甲类 %d"
            % (n, v["can"], v["cannot"], v["gap"], v["unknown"],
               v["unknown_class_b"], v["ratio_class_b"], mr.ratio_text(rep["stop_line_ratio"]),
               v["unknown_ratio"], v["unknown_by_design"])
        )
    print("\nC 乙 ids：%s" % (rep["samples"]["C"]["class_b_ids"],))
    # 停工判定按真实用户口径（2026-11-20 裁决）：夹具口径只作回归参照。
    print("停工线停不停（真实口径）：%s（阈值 %s，最高乙类 %.4f / 画像 %s）" % (
        "停" if rep["gate_ratio_class_b"] > rep["stop_line_ratio"] else "不停",
        mr.ratio_text(rep["stop_line_ratio"]), rep["gate_ratio_class_b"],
        rep["gate_worst_sample"],
    ))
    print("对照：夹具口径最高乙类 %.4f（回归参照，不判停）" % rep["max_ratio_class_b"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
