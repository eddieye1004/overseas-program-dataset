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
        """美方 SWT 与三个 Sponsor 把关的项目同构，口径必须一致。

        官方写的是「无需雅思/托福成绩，但必须具备足以在英语工作环境中沟通的
        能力。须通过项目方英语测试及美方雇主面试」——要求和 J-1 Intern
        「认可考试 / 学校证明 / Sponsor 面试三选一」、Camp Counselor「由
        Sponsor 面试评估」是同一件事：有一道测试，但换算不成分数。

        本测试原先钉的是 silent，理由是「保守选择，让用户去查官网」。那让
        同一个概念在仓内落成两种结果，而分界只是措辞命中与否：
        us-j1-intern 的 note 里有「面试评估」命中 LANG_BY_DESIGN 判 na；
        SWT 写的是「无需雅思/托福」没有命中，落到 lang_no_score 判 silent。
        两个项目对用户的实际约束完全相同，一个说不挡人、一个说不可判。

        现在改钉 na（code = lang_no_test），并保住原测试真正想守的那条底线：
        **不许判 can**。语言这一维不再伪装成缺口，但整体结论仍因年龄未核实
        而不可判 —— 「不挡人」不等于「能申」。"""
        dims = self.judge("us-j1-summer-work-travel")[1]
        kinds = {d["dim"]: d["kind"] for d in dims}
        codes = {d["dim"]: d["code"] for d in dims}
        self.assertEqual(kinds["language"], "na")
        self.assertEqual(codes["language"], "lang_no_test")
        # 底线不变：语言不挡人，但整体仍不可判（年龄 ⚠️ 未核实）
        for sample in ("A", "B", "C"):
            state = mr.judge(self.docs["us-j1-summer-work-travel"], mr.SAMPLES[sample])[0]
            self.assertNotEqual(state, "can", sample)

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
        说够或不够都是替官方担保。

        HPI 另有一条（§4-6）：edu note 要求「认可名单内院校 + 学位授予 5 年内」，
        结构化字段只有 bachelor_completed，因此教育维也是 silent（edu_place_unknown）。
        这里钉住整组 code，就是为了让「教育维悄悄判过」立刻红。"""
        pr = dict(mr.SAMPLES["C"])
        state, dims = mr.judge(self.docs["uk-hpi-visa"], pr)
        self.assertEqual(state, "unknown")
        self.assertEqual(
            {d["code"] for d in dims},
            {"passport_ok", "age_none", "edu_place_unknown", "lang_no_score", "funds_ok"},
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

    def test_tw_china_alias_is_read(self):
        """台湾护照在数据里有 `taiwan_china` 与 `tw_china` 两种键，读取端必须都认。

        12 个文件登记的是 `tw_china`（au-407-training、au-485-vocational、
        dk-working-holiday、es-busqueda-empleo、fi-look-for-work、
        fr-recherche-emploi、ie-third-level-graduate、
        is-job-search-after-graduation、it-ricerca-lavoro、mt-nomad-residence、
        sg-employment-pass、sg-s-pass）。只认 `taiwan_china` 会让这 12 条对
        台湾护照判成 passport_missing，而它们的 note 大多写着「未按国籍设限」，
        于是其它护照走 NOTE_OPEN_NATIONALITY 判 pass、唯独台湾判 silent ——
        一个写明可申的项目变成「不可判」。

        这里逐条比对：字段里登记了 eligible 的，判定的 passport 维就不能是
        silent。数据本体不动，修在读取端。"""
        checked = 0
        for pid, doc in self.docs.items():
            pt = (doc.get("eligibility") or {}).get("passport_types") or {}
            if "tw_china" not in pt:
                continue
            checked += 1
            _, dims = mr.judge(doc, mr.SAMPLES["C"])
            passport = next(d for d in dims if d["dim"] == "passport")
            if pt["tw_china"] == "eligible":
                self.assertEqual(
                    passport["kind"], "pass",
                    f"{pid} 的 tw_china=eligible 未被读到（判成 {passport['code']}）",
                )
                self.assertEqual(passport["code"], "passport_ok", pid)
        self.assertGreaterEqual(checked, 12, "tw_china 的项目数变少了，确认是否已统一键名")
        # 反向别名同样要认，避免将来数据统一成 taiwan_china 后旧键读取路径失效
        self.assertEqual(mr.passport_value({"tw_china": "eligible"}, "taiwan_china"), "eligible")
        self.assertEqual(mr.passport_value({"taiwan_china": "eligible"}, "tw_china"), "eligible")
        self.assertIsNone(mr.passport_value({}, "taiwan_china"))

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


class Phase1Fixes(unittest.TestCase):
    """一期验收修正轮的 6 条回归断言（派单 2026-11-13，对应验收报告 §4-1…§4-6）。

    这 6 条守的不是「当前结论长什么样」，而是**不许再静默判过**这条底线。
    以后动 judge() 先跑这一组：每一条都能独立红，红点直接对应一项偏差。

    编号与报告 §4 一一对应，改动时不要重排。
    """

    @classmethod
    def setUpClass(cls):
        cls.docs = {d["program"]["id"]: d for d in mr.load_programs()}

    def codes(self, pid, sample):
        _, dims = mr.judge(self.docs[pid], mr.SAMPLES[sample])
        return {d["code"] for d in dims}

    def dim(self, pid, sample, dim):
        _, dims = mr.judge(self.docs[pid], mr.SAMPLES[sample])
        for d in dims:
            if d["dim"] == dim:
                return d
        return None

    # —— §4-1 funds 月额门槛：不许拿一次性预算直接比月额 ——
    def test_4_1_monthly_funds_is_multiplied_not_compared_raw(self):
        """`de-16e-internship` 每月 752 欧元（cny_estimate 记单月 5,900），
        原文「资金须覆盖整个实习期」，最长 6 个月。

        A 有 3 万：拿月额比 → 30,000 ≥ 5,900 判「够」（错）；乘 6 个月
        得 35,400 → 30,000 不够，应判「差什么」。

        这一条同时钉住两件事：月数被读到了（=6，不是 None）、且确实乘了。
        """
        self.assertEqual(mr.stay_months(self.docs["de-16e-internship"]), 6)
        d = self.dim("de-16e-internship", "A", "funds")
        self.assertEqual(d["kind"], "gap", d)
        self.assertEqual(d["code"], "funds_short", d)
        # 折算后的总额必须出现在 need 里，且等于 5,900 × 6
        self.assertIn("35,400", d["need"], d["need"])
        self.assertEqual(mr.judge(self.docs["de-16e-internship"], mr.SAMPLES["A"])[0], "gap")

    def test_4_1_monthly_without_term_is_silent_not_pass(self):
        """反面：月额拿不到期限上限时，不许折算、也不许直接比 → 不可判。

        用同名项目的深拷贝把 `max_stay_months` 与 timeline 里的「最长 N 个月」
        一起抹掉，模拟「仓内没登记停留期」的项目。若实现里漏了 months is None
        这个分支，它会落到 `budget >= cny` 判 pass —— 那正是 §4-1 的原错。
        """
        import copy

        doc = copy.deepcopy(self.docs["de-16e-internship"])
        (doc.get("work_conditions") or {}).pop("max_stay_months", None)
        tl = doc.get("timeline") or {}
        tl["quota_note"] = "未设名额限制。"
        tl.pop("processing_time", None)
        self.assertIsNone(mr.stay_months(doc))
        state, dims = mr.judge(doc, mr.SAMPLES["B"])  # B 的 8 万远高于单月 5,900
        funds = [d for d in dims if d["dim"] == "funds"][0]
        self.assertEqual(funds["code"], "funds_term_unknown", funds)
        self.assertEqual(funds["kind"], "silent", funds)
        self.assertNotEqual(state, "can")

    def test_4_1_every_monthly_funds_program_is_registered(self):
        """全库顺查：凡是金额带「每月」口径的项目，都必须在下方清单里登记
        处理结果。新增同类项目而没登记时这条会红，逼着做一次决定，而不是
        让它随默认分支悄悄判过。

        (项目, 期限月数) —— 期限为 None 表示已确认仓内拿不到，按 silent 处置。
        """
        expected = {
            "de-16e-internship": 6,
            "fi-look-for-work": 24,
            "is-job-search-after-graduation": 18,
            "se-look-for-work": 9,
        }
        found = {}
        for pid, d in self.docs.items():
            f = (d.get("eligibility") or {}).get("funds") or {}
            if f.get("required") is not True:
                continue
            a = f.get("amount") or {}
            text = (a.get("note") or "") + " " + (f.get("note") or "")
            if mr.FUNDS_MONTHLY.search(text):
                found[pid] = mr.stay_months(d)
        self.assertEqual(found, expected)
        # 期限已知的，必须真的乘过月数：任何画像下都不许出现「月额原样当总额」
        # 的 need（那会把差额算错一个数量级）。
        for pid, months in expected.items():
            for sample in ("A", "B", "C"):
                d = self.dim(pid, sample, "funds")
                if not d:
                    continue
                need = d.get("need") or ""
                if d["code"] == "funds_short":
                    self.assertIn("×", need, f"{pid}/{sample} 的差额没乘月数：{need}")
                    self.assertIn(f"{months} 个月", need, f"{pid}/{sample} 月份不对：{need}")

    # —— §4-2 奥地利红白红卡：四学年要求没有结构化 ——
    def test_4_2_four_year_requirement_not_silently_passed(self):
        """note 写「不少于四年高等教育，三年制本科不满足」，结构化只有
        `minimum_level: bachelor_completed`。B 是本科毕业但学制未采集 ——
        不许判 edu_ok，必须 silent（edu_years_unknown）并把整体降到不可判。
        反过来 A（本科在读）仍应因层级不足判 fail，不能被这条吞掉。"""
        self.assertEqual(mr.edu_years_required(self.docs["at-rwr-card-vhq"]), 4)
        d = self.dim("at-rwr-card-vhq", "B", "education")
        self.assertEqual(d["code"], "edu_years_unknown", d)
        self.assertEqual(d["kind"], "silent", d)
        self.assertEqual(mr.judge(self.docs["at-rwr-card-vhq"], mr.SAMPLES["B"])[0], "unknown")
        self.assertEqual(mr.judge(self.docs["at-rwr-card-vhq"], mr.SAMPLES["A"])[0], "cannot")

    # —— §4-3 英国毕业生签证：前置身份整类未参与判定 ——
    def test_4_3_uk_graduate_visa_precondition_is_read(self):
        """`other_requirements` 里 required 的 residency_requirement 必须进入判定。
        B（大陆本科，从未在英国读书）不许判「能申」，且必须说出差的是
        「先在英国持学生签完成课程」这一项（gap，能补），不是笼统一句不可判。"""
        self.assertEqual(mr.precondition_kind(self.docs["uk-graduate-visa"]), "local_status")
        d = self.dim("uk-graduate-visa", "B", "precondition")
        self.assertIsNotNone(d)
        self.assertEqual(d["code"], "pre_local_status", d)
        self.assertEqual(d["kind"], "gap", d)
        state = mr.judge(self.docs["uk-graduate-visa"], mr.SAMPLES["B"])[0]
        self.assertEqual(state, "gap")

    def test_4_3_no_program_with_residency_requirement_judges_can(self):
        """全库顺查（§4-3 的影响面是 17 个项目）：只要项目有 required 的
        residency_requirement，三画像下都不许判「能申」。

        这一条比单点断言更狠：它不依赖某个项目当前的具体结论，只守
        「有前置要求就不能说谁都能申」。落 None（读不懂）也算违规 ——
        读不懂必须落 unclassified/silent，不能当作「没有要求」。
        """
        checked = 0
        for pid, doc in self.docs.items():
            reqs = [
                r
                for r in ((doc.get("eligibility") or {}).get("other_requirements") or [])
                if r.get("required") is True and r.get("type") == "residency_requirement"
            ]
            if not reqs:
                continue
            checked += 1
            self.assertIsNotNone(mr.precondition_kind(doc), f"{pid} 有前置要求但没读出类别")
            for sample in ("A", "B", "C"):
                state = mr.judge(doc, mr.SAMPLES[sample])[0]
                self.assertNotEqual(state, "can", f"{pid}/{sample} 有前置身份要求却判了能申")
        self.assertEqual(checked, 17, f"带 required residency_requirement 的项目数变了：{checked}")

    # —— §4-4 加拿大 PGWP：教育维漏判 DLI / 8 个月 ——
    def test_4_4_ca_pgwp_education_is_not_edu_ok(self):
        """edu note 要求「在合格 DLI 完成 ≥8 个月课程」。B 无加拿大就读经历，
        既不能判达标，也不该替他判失败 —— 必须 silent（edu_place_unknown）。
        整体仍是「差什么」（语言维 gap 兜住），对用户可见结论不变。"""
        d = self.dim("ca-pgwp", "B", "education")
        self.assertEqual(d["code"], "edu_place_unknown", d)
        self.assertEqual(d["kind"], "silent", d)
        state = mr.judge(self.docs["ca-pgwp"], mr.SAMPLES["B"])[0]
        self.assertEqual(state, "gap")

    # —— §4-5 J-1 研究学者：结构化比 note 严，以 note 为准 ——
    def test_4_5_structured_level_conflict_defers_to_note(self):
        """结构化 `minimum_level: master`，note 说「法规未规定学位层级，由 Sponsor
        判断」。C（本科）原先被判「不能申」——比原文更严，等于替官方拒绝。
        冲突时必须按 note 降级，不许拿结构化字段判 fail。"""
        self.assertEqual(
            (self.docs["us-j1-research-scholar"]["eligibility"]["education"]["minimum_level"]),
            "master",
        )
        d = self.dim("us-j1-research-scholar", "C", "education")
        self.assertEqual(d["code"], "edu_by_sponsor", d)
        self.assertEqual(d["kind"], "silent", d)
        state = mr.judge(self.docs["us-j1-research-scholar"], mr.SAMPLES["C"])[0]
        self.assertEqual(state, "unknown")
        self.assertNotEqual(state, "cannot")

    def test_4_5_structural_note_conflict_scan_is_registered(self):
        """全库顺查「结构化字段与 note 冲突」：登记当前命中集合。

        新增命中时这条会红 —— 每一例都要人工确认是 note 说话还是结构说话，
        不许让新的冲突随默认分支判过去。
        """
        hits = {
            pid
            for pid, d in self.docs.items()
            if mr.EDU_RANK.get(
                ((d.get("eligibility") or {}).get("education") or {}).get("minimum_level")
                or "any",
                0,
            )
            and mr.EDU_BY_SPONSOR.search(
                (((d.get("eligibility") or {}).get("education") or {}).get("note") or "")
            )
        }
        self.assertEqual(hits, {"us-j1-research-scholar"})

    # —— §4-6 英国 HPI：认可名单 + 学位 5 年内未核 ——
    def test_4_6_uk_hpi_place_constraint_is_silent(self):
        """edu note 要求「认可名单内院校 + 学位授予 5 年内 + Ecctis 证明」，
        画像没有院校信息，不许默认判 edu_ok。C 整体仍不可判（语言维兜住），
        但教育维本身必须是 silent，理由写明缺的是院校与毕业年份。"""
        d = self.dim("uk-hpi-visa", "C", "education")
        self.assertEqual(d["code"], "edu_place_unknown", d)
        self.assertEqual(d["kind"], "silent", d)
        self.assertEqual(mr.judge(self.docs["uk-hpi-visa"], mr.SAMPLES["C"])[0], "unknown")
        # B（有成绩缺失）也不许在学历这一维被放行
        self.assertEqual(self.dim("uk-hpi-visa", "B", "education")["code"], "edu_place_unknown")


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
