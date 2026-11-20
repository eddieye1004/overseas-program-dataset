"""P3 翻转归因表：把当前 audit() 与 p3_baseline.json 逐条比对。

输出每一处 (项目 × 画像) 状态变化，并给每条变化定位到「教育维的哪个 code」。
需要可复算 —— 回执里引用本脚本路径。
"""
import io, json, sys, os

sys.path.insert(0, "scripts")
import match_readiness as mr  # noqa: E402

BASE = r"C:\Users\16256\work\.legs\p3_baseline.json"


def main():
    base = json.load(io.open(BASE, encoding="utf-8"))
    docs = {d["program"]["id"]: d for d in mr.load_programs()}

    # baseline 结构：{pid: {sample: {"state":..., "dims": [[dim, kind, code], ...]}}}
    flips = []
    for pid, per_sample in base.items():
        for name in ("A", "B", "C"):
            b = per_sample.get(name)
            if not b:
                continue
            state, dims = mr.judge(docs[pid], mr.SAMPLES[name])
            if state == b["state"]:
                continue
            edu_now = next((x for x in dims if x["dim"] == "education"), None)
            bedu = next((d for d in (b.get("dims") or []) if d[0] == "education"), None)
            flips.append(
                {
                    "sample": name,
                    "pid": pid,
                    "before": b["state"],
                    "after": state,
                    "before_edu": bedu[2] if bedu else None,
                    "after_edu": (edu_now or {}).get("code"),
                }
            )

    flips.sort(key=lambda f: (f["sample"], f["pid"]))
    print(f"# 翻转条数：{len(flips)}\n")
    print("| 画像 | 项目 | 改前 | 改后 | 教育维 改前 | 教育维 改后 | 归因 |")
    print("|---|---|---|---|---|---|---|")
    for f in flips:
        same = f["before_edu"] == f["after_edu"]
        attr = (
            "**教育维 code 未变 → 非本单因果**"
            if same
            else f"教育维 `{f['before_edu']}` → `{f['after_edu']}`"
        )
        print(
            f"| {f['sample']} | {f['pid']} | {f['before']} | {f['after']} | "
            f"`{f['before_edu']}` | `{f['after_edu']}` | {attr} |"
        )

    by_edu = sum(1 for f in flips if f["before_edu"] != f["after_edu"])
    print(f"\n教育维驱动的翻转：{by_edu} / {len(flips)}")
    if by_edu != len(flips):
        print("!! 存在非教育维翻转，必须逐条解释")

    # 停工线计数
    rep = mr.audit()
    print("\n## 三画像计数（当前）")
    for n, v in rep["samples"].items():
        print(
            f"- {n}: can {v['can']} / cannot {v['cannot']} / gap {v['gap']} / "
            f"unknown {v['unknown']} / 乙 {len(v['class_b_ids'])} (ratio {v['ratio_class_b']})"
        )
    print("\nC 乙 ids:", rep["samples"]["C"]["class_b_ids"])


if __name__ == "__main__":
    main()
