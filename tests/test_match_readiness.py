"""scripts/match_readiness.py 的回归测试（M1/M2）。

重心与 test_track.py 一致：验证「该红的会红」。

这个脚本同时承担两件事，所以两组断言各守一半：

  1. 审计（人读）—— 报告里的不可判比例必须由真实数据算出来，
     而不是写死在文案里。停工的判定是「超过 1/3 项目不可判」，
     如果分子算错，停工线就形同虚设。

  2. 契约（机器读）—— data/match-flags.json 与 data/match-samples.json
     被网页的资格判定页直接读取，判定口径只有 Python 一份。
     所以必须钉住：产物与数据同步（--check 会红）、
     每个项目都被覆盖、以及几条语义规则（不设门槛 ≠ 不可判、
     没填语言成绩 ≠ 不可判、未公布年龄 ≠ 不限年龄）。

运行：
    python -m unittest discover -s tests -v
"""

import io
import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "match_readiness.py")
PROGRAMS = os.path.join(ROOT, "data", "programs")

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import match_readiness as mr  # noqa: E402


def run_cli(*args):
    """跑一次 CLI，返回 (退出码, 标准输出)。"""
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
    )


class ArtifactSync(unittest.TestCase):
    """产物与数据必须同步——这是 CI 闸门本身。"""

    def test_check_passes_on_current_data(self):
        r = run_cli("--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("一致", r.stdout)

    def test_flags_cover_every_program(self):
        flags = mr.build_flags()
        ids = {d["program"]["id"] for d in mr.load_programs()}
        self.assertEqual(set(flags["programs"]), ids)
        self.assertEqual(flags["total"], len(ids))

    def test_samples_cover_every_program(self):
        samples = mr.build_samples()
        ids = {d["program"]["id"] for d in mr.load_programs()}
        self.assertEqual(set(samples["verdicts"]), ids)
        self.assertEqual(set(samples["samples"]), {"A", "B", "C"})

    def test_flags_carry_every_dimension(self):
        """缺一维就等于判定页少一条依据，而且不会报错，只会静默按默认值走。"""
        flags = mr.build_flags()
        for pid, f in flags["programs"].items():
            for dim in ("passport", "age", "education", "language", "funds", "window"):
                self.assertIn(dim, f, f"{pid} 缺 {dim}")

    def test_detects_stale_artifact(self):
        """把 --check 指向一个过期产物时，必须返回 1 而不是静默通过。
        没有这条，闸门可能永远返回 0，等于不存在。"""
        flags = mr.build_flags()
        flags["programs"].pop(next(iter(flags["programs"])))
        original = mr.build_flags
        mr.build_flags = lambda: flags
        try:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(mr.check_artifacts(), 1)
        finally:
            mr.build_flags = original


class VerdictSemantics(unittest.TestCase):
    """判定语义：这几条是所有结论的地基，写错的方向都很隐蔽。"""

    @classmethod
    def setUpClass(cls):
        cls.docs = {d["program"]["id"]: d for d in mr.load_programs()}

    def judge(self, pid, **override):
        pr = dict(mr.SAMPLES["A"])
        pr.update(override)
        return mr.judge(self.docs[pid], pr)

    def codes(self, pid, **override):
        _, dims = self.judge(pid, **override)
        return {d["code"] for d in dims}

    # —— 1. 「官方没设门槛」不能被算成不可判 ——
    def test_no_fixed_funds_is_na_not_silent(self):
        """德国 20 条找工作签证：要求资金有保障但官方不写金额。
        这类判 na（不挡人），不是 silent（不可判）。判错会把
        「官方不设固定金额」变成「数据缺失」，用户看到一条假缺口。"""
        kinds = {d["dim"]: d["kind"] for d in self.judge("de-20-job-search")[1]}
        self.assertEqual(kinds["funds"], "na")

    def test_language_by_design_is_na(self):
        """J-1 Intern / IAESTE 这类：要求英语能力，但官方明确不设分数线
        （由 Sponsor 面试或项目方测试评估）。判 na —— 这一维不挡人。"""
        for pid in ("us-j1-intern", "global-iaeste", "us-j1-camp-counselor"):
            kinds = {d["dim"]: d["kind"] for d in self.judge(pid)[1]}
            self.assertEqual(kinds["language"], "na", pid)

    def test_swt_language_is_not_silently_passed(self):
        """美方 SWT 是个反例，值得单独钉住：官方写的是「无需雅思/托福，
        但须通过项目方英语测试及美方雇主面试」。

        它不属于「不设门槛」（na）——确实有一道测试；也不属于「有分数线但
        没登记」（absent）——分数线这个概念不适用。当前实现判 silent
        （要求语言证明但仓内无分数线）。这是一个已知的保守选择：
        对用户表现为「这一维不可判，请查官网」，而不是假装通过。
        写成测试是为了让它可见，避免有人在补数据时把这条静默改成 can。"""
        kinds = {d["dim"]: d["kind"] for d in self.judge("us-j1-summer-work-travel")[1]}
        self.assertEqual(kinds["language"], "silent")

    def test_no_age_limit_is_na(self):
        kinds = {d["dim"]: d["kind"] for d in self.judge("de-16e-internship")[1]}
        self.assertEqual(kinds["age"], "na")

    # —— 2. 「官方未公布」不许被当成「无限制」 ——
    def test_unverified_age_is_silent_not_na(self):
        """AIESEC：0–99 是占位，note 以 ⚠️ 开头。当成 na 就等于
        替官方担保「不限制年龄」，而官方只是没写。"""
        for pid in ("global-aiesec-global-talent", "us-j1-summer-work-travel"):
            kinds = {d["dim"]: d["kind"] for d in self.judge(pid)[1]}
            self.assertEqual(kinds["age"], "silent", pid)
            state = mr.judge(self.docs[pid], mr.SAMPLES["A"])[0]
            self.assertNotEqual(state, "can", f"{pid} 不应判能申")

    # —— 3. 语言上的不对称：没填 ≠ 不可判 ——
    def test_missing_language_is_gap_when_threshold_known(self):
        """澳洲 462 有雅思 4.5 的门槛，用户没填 → 差什么（能补），不是不可判。"""
        pr = dict(mr.SAMPLES["B"])
        self.assertIsNone(pr["ielts"])
        state, dims = mr.judge(self.docs["au-462-work-holiday"], pr)
        self.assertEqual(state, "gap")
        self.assertIn("lang_missing", {d["code"] for d in dims})

    def test_missing_language_is_gap_even_without_threshold(self):
        """门槛没登记时，用户没填语言仍是「差一项」这个确定事实。
        判 silent 会把「你没考雅思」藏进「数据不可判」，替用户掩盖真实缺口。"""
        pr = dict(mr.SAMPLES["B"])
        state, dims = mr.judge(self.docs["uk-hpi-visa"], pr)
        self.assertEqual(state, "gap")
        self.assertIn("lang_missing", {d["code"] for d in dims})

    def test_provided_language_without_threshold_is_silent(self):
        """反过来：用户给了成绩、仓内没分数线 → 不可判。
        说够或不够都是替官方担保。"""
        pr = dict(mr.SAMPLES["C"])
        state, dims = mr.judge(self.docs["uk-hpi-visa"], pr)
        self.assertEqual(state, "unknown")
        self.assertIn(
            {d["code"] for d in dims},
            [{"passport_ok", "age_none", "edu_ok", "lang_no_score", "funds_ok"}],
        )

    # —— 4. 状态优先级 ——
    def test_fail_beats_gap(self):
        """超龄 + 缺语言：结论必须是「不能申」，不是「差什么」。
        顺序错了会让一个超龄的人先去考雅思，考完照样不能申。"""
        state, dims = self.judge("au-462-work-holiday", age=40)
        self.assertEqual(state, "cannot")
        self.assertIn("age_high", {d["code"] for d in dims})

    def test_passport_veto(self):
        """台湾护照对澳洲 462 明确 not_eligible。"""
        state, dims = mr.judge(self.docs["au-462-work-holiday"], mr.SAMPLES["C"])
        self.assertEqual(state, "cannot")
        self.assertEqual(dims[0]["code"], "passport_no")

    # —— 5. 每维必须带 code ——
    def test_every_dim_has_code(self):
        """没有 code 的维在界面上会露出裸 key，而且两侧比对会静默跳过。"""
        for pid in self.docs:
            for name in mr.SAMPLES:
                _, dims = mr.judge(self.docs[pid], mr.SAMPLES[name])
                for d in dims:
                    self.assertIn("code", d, f"{pid}/{name} 的 {d['dim']} 没有 code")

    # —— 6. 不可判率必须由数据算出，且停工线判定不能被绕开 ——
    def test_unknown_ratio_matches_counts(self):
        rep = mr.audit()
        total = rep["total"]
        for name, v in rep["samples"].items():
            self.assertAlmostEqual(v["unknown_ratio"], v["unknown"] / total, places=4, msg=name)

    def test_stop_line_is_one_third(self):
        """阈值 1/3 是派单写死的。这里钉住它的数值，防止有人为了让单子
        不被停工而悄悄把 1/3 改成 2/5。"""
        rep = mr.audit()
        self.assertLessEqual(rep["max_unknown_ratio"], 1.0)
        # 当前数据未越线；越线时这里会红，提醒先看报告再改代码
        self.assertLessEqual(
            rep["max_unknown_ratio"],
            1 / 3,
            "不可判率已越过 1/3 停工线，按派单要求应停工报 Muse 裁决",
        )


class CliBehaviour(unittest.TestCase):
    def test_emit_writes_both_artifacts(self):
        """--emit 必须同时写两个文件：只写一个的话，另一个会安静地过期。"""
        before = {}
        for p in (mr.FLAGS, mr.SAMPLES_OUT):
            with io.open(p, encoding="utf-8") as fh:
                before[p] = fh.read()
        r = run_cli("--emit")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for p, old in before.items():
            with io.open(p, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), old, f"{p} 重生成后内容不该变")

    def test_json_output_is_parseable(self):
        r = run_cli("--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        rep = json.loads(r.stdout)
        self.assertIn("samples", rep)
        n_programs = len([f for f in os.listdir(PROGRAMS) if f.endswith(".json")])
        self.assertEqual(rep["total"], n_programs)


if __name__ == "__main__":
    unittest.main()
