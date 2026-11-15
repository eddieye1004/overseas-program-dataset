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
        这里钉住整组 code，就是为了让「教育维悄悄判过」立刻红。

        P1b-2 起另带两条前置维：HPI 原文既禁「曾持 Graduate visa / DES 身份」
        （`prior_same_category_visa`）又限「一生一次」（`program_once_in_lifetime`）。
        画像 C 两项都填了"none"，所以它们是 pass 而不是 silent——结论仍是 unknown，
        驱动它的仍只有教育维那一条。"""
        pr = dict(mr.SAMPLES["C"])
        state, dims = mr.judge(self.docs["uk-hpi-visa"], pr)
        self.assertEqual(state, "unknown")
        self.assertEqual(
            {d["code"] for d in dims},
            {
                "passport_ok",
                "age_none",
                "edu_place_unknown",
                "lang_no_score",
                "funds_ok",
                "pre_prior_visa_none",
                "pre_participation_none",
            },
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

    def test_stop_line_binds_class_b_only(self):
        """停工线只绑乙类（可避免不可判），阈值仍是 1/3，一个数字都没动。

        2026-11-14 P2-1 裁决：原 test_stop_line_is_one_third 把甲类（设计性
        不可判：原文交由 Sponsor 判断、或官方本无阈值）也算进分子，导致
        「诚实地说不知道」与「我们欠的债」同罪，而且逼团队在「让 CI 变绿」
        与「不许硬判」之间二选一——最后一定是硬判。拆分后闸门只盯债，
        甲类单列报告（软线 5 项，不红）。

        替换而不是并存两条硬闸：两条里只要有一条红就算停工，等于口径没改。
        """
        rep = mr.audit()
        for name, v in rep["samples"].items():
            self.assertAlmostEqual(
                v["ratio_class_b"], v["unknown_class_b"] / rep["total"], places=4, msg=name
            )
        self.assertLessEqual(
            rep["max_ratio_class_b"],
            1 / 3,
            "乙类不可判率已越过 1/3 停工线（甲类不占分子），应停工报 Muse 裁决",
        )
        # 加总自检：甲 + 乙必须等于不可判总数，任何一类漏登记都在这里露馅
        for name, v in rep["samples"].items():
            self.assertEqual(
                v["unknown_by_design"] + v["unknown_class_b"],
                v["unknown"],
                f"画像 {name} 的甲+乙 与不可判总数对不上，说明有 unknown 项没归类",
            )

    def test_full_ratio_still_reported(self):
        """混算口径不删、仍输出：它不再是闸门，但仍是「甲类变多不许藏」的那把尺子。

        留着它有两个用处：① 历史可比；② 防止有人把「甲类变多」用拆分藏掉——
        甲类一多，全口径会自己顶上来。

        版本轨迹（均为实测，不是推算）：

        | 版本 | C 全口径 | 说明 |
        |---|---|---|
        | P1b-2 前 | 14/41 = 0.3415 | 家属/签证史/学籍三族还没接线 |
        | P1b-2 后 | 13/41 = 0.3171 | 三画像补齐新字段显式取值，三族判出 pass/fail |
        | P1c 后 | 16/41 = 0.3902 | 在地条拆出独立类别，原先被误判成 gap 的 3 项转成诚实 silent |
        | **P1d 后** | **13/41 = 0.3171** | 接入 current_location，在地条判出 fail（cannot），3 项离开 unknown |

        上限从 16 回调到 13 是**记录事实**，不是放宽标准：那 3 项从 silent 变
        cannot 是因为引擎终于能判（现居地有了），不是把它们藏起来——它们仍在
        报告里逐条可见，只是状态从「不可判」变成「不能申」。全口径从来不是停工
        闸门，闸门在 `test_stop_line_binds_class_b_only`，它的 1/3 一个数字没改。
        """
        rep = mr.audit()
        # 注意：unknown_ratio 是 4 位小数的舍入值，直接与分式比会因舍入假红。
        # 所以钉「项目条数」+「比率等于该条数 / 总数」，两者合起来才是断言本意。
        self.assertLessEqual(max(v["unknown"] for v in rep["samples"].values()), 13)
        self.assertEqual(
            rep["max_unknown_ratio"],
            round(13 / rep["total"], 4),
            "全口径上限被突破了：这是「甲类变多也不许藏」的那把尺子",
        )
        self.assertLessEqual(rep["max_unknown_ratio"], 13 / 41 + 1e-4)
        for name, v in rep["samples"].items():
            self.assertAlmostEqual(
                v["unknown_ratio"], v["unknown"] / rep["total"], places=4, msg=name
            )

    def test_every_silent_code_is_classified(self):
        """任何出现在 silent 维上的 code 必须登记进甲名单或乙名单，未登记即红。

        这是「把乙塞进甲以绕闸」的机械闸（提案 R1）：登记按 code 不按项目，
        要洗白一个项目得先洗白一个 code，影响面立刻可见。
        """
        seen = set()
        for pid in self.docs:
            for name in mr.SAMPLES:
                _, dims = mr.judge(self.docs[pid], mr.SAMPLES[name])
                for d in dims:
                    if d["kind"] == "silent":
                        seen.add(d["code"])
        unclassified = sorted(seen - mr.BY_DESIGN_CODES - mr.CLASS_B_CODES)
        self.assertEqual(
            unclassified,
            [],
            "以下 silent code 未登记甲乙分类：%s。甲类准入语义只有"
            "「交给第三方主体判断」「官方无阈值」两种，其余必须进 CLASS_B_CODES"
            % unclassified,
        )
        self.assertEqual(
            sorted(mr.BY_DESIGN_CODES),
            ["age_unknown", "edu_by_sponsor"],
            "甲类白名单变动须 Muse 复核（见提案 §1.2 的逐条论证）",
        )
        self.assertEqual(
            mr.BY_DESIGN_CODES & mr.CLASS_B_CODES, frozenset(), "同一个 code 不许同时在甲乙两张表里"
        )

    def test_class_b_members_are_pinned(self):
        """C 画像（停工线驱动画像）的乙类项目集合钉成当前实测清单，增删都要做一次显式决定。

        改这个清单意味着「某个项目从债变成能判」或反之，那是产品结论变化，
        不该顺带发生。以下增删逐条对得上（改前 → 改后各为实测，见
        `.legs/p1c_before_dump.out.txt` 与 `.legs/p1d_flip_audit.py` 的输出）。

        **P1c 里程碑（记录，不再复算）：C 11 → 14，净 +3，全部是新增**：

        | 项目 | 改前 | 改后 | 原因 |
        |---|---|---|---|
        | `au-485-graduate` | gap | unknown | 原文 `be in Australia when you apply` 是**在地**要求 |
        | `au-485-vocational` | gap | unknown | 原文 `You must be in Australia ... when you apply` |
        | `uk-graduate-visa` | gap | unknown | 原文 `You must be in the UK when you apply` |

        这三项改前靠 PRE_LOCAL_STATUS 末支判成 `gap / pre_local_status`
        （「你差一段在该国读书的经历」），而它们恰恰是「已经在该国读书的人」——
        那条建议对目标人群是错的。拆成独立在地类别后判 `silent /
        pre_inside_country`，整体诚实降级为 unknown。14/41 = 0.3415 **越线**，
        停工报 Muse 裁决。

        **P1d 清偿（本单，2026-11-15 裁决取丙的下半句）：C 14 → 11，净 -3，
        移除的正是 P1c 新增的那三项，一项不多一项不少**：

        | 项目 | 改前 | 改后 | 原因 |
        |---|---|---|---|
        | `au-485-graduate` | unknown | cannot | 画像现居 CN/TW ≠ AU → 在地条判 fail |
        | `au-485-vocational` | unknown | cannot | 同上 |
        | `uk-graduate-visa` | unknown | cannot | 画像现居 CN/TW ≠ GB → 在地条判 fail |

        即：P1c 欠下的这笔债**恰好就是这三条**，接入 `current_location` 后精确
        还清，没有连带洗白任何别的项目。11/41 = 0.2683 回到 1/3 以内。

        剩下的 `jp-working-holiday` / `nz-china-whv` 两项属 `pre_home_residence`
        （须常驻护照所属地区），本单按派单 §1.2 只接 `pre_inside_country`，
        因此仍留在乙类——见回执 §6「遗留待裁」。
        """
        rep = mr.audit()
        self.assertEqual(
            rep["samples"]["C"]["class_b_ids"],
            [
                "at-rwr-card-vhq",
                "au-407-training",
                "ca-pgwp",
                "de-chancenkarte",
                "dk-working-holiday",
                "jp-working-holiday",
                "mt-nomad-residence",
                "nl-orientation-year",
                "nz-china-whv",
                "nz-post-study-work",
                "uk-hpi-visa",
            ],
        )
        self.assertEqual(
            rep["samples"]["C"]["by_design_ids"],
            [
                "global-aiesec-global-talent",
                "us-j1-research-scholar",
            ],
        )

        # 甲类与画像无关：三个 code 都不读画像值，换个人不该让它们消失。
        # P1b-2 记录：接线后 A/B/C 的甲类从 3 降到 2（B、C）——因为
        # `us-j1-summer-work-travel` 在 B/C 上被新接的在读要求判成「不能申」
        # （已毕业 ≠ 在读），不再是 unknown，自然也就没有甲类。这不是甲类口径
        # 改动，是这个项目**本来就该给出的结论**终于判出来了；甲类白名单本身
        # 一个 code 都没动（test_every_silent_code_is_classified 仍钉死两个）。
        a = mr.audit()["samples"]
        self.assertEqual(a["A"]["unknown_by_design"], 3, "A")
        self.assertEqual(a["B"]["unknown_by_design"], 2, "B")
        self.assertEqual(a["C"]["unknown_by_design"], 2, "C")

    def test_mixed_cause_program_counts_as_debt(self):
        """de-chancenkarte 同时有「认定」（甲因）与「CEFR 换算」（乙因），按混合项规则
        必须整项计乙，否则那条明显可修的 CEFR 债就被「主因是甲」洗掉了（提案 R2）。
        """
        rep = mr.audit()
        row = next(r for r in rep["rows"] if r["id"] == "de-chancenkarte")
        self.assertEqual(row["verdicts"]["C"]["state"], "unknown")
        self.assertEqual(row["verdicts"]["C"]["cls"], "avoidable")
        codes = {d["code"] for d in row["verdicts"]["C"]["dims"] if d["kind"] == "silent"}
        self.assertEqual(codes, {"edu_credential_unknown", "lang_cefr"})
        # 混合判据本身：只要有一条不在甲名单里就是乙
        self.assertEqual(mr.undecidable_class([{"kind": "silent", "code": "edu_by_sponsor"},
                                               {"kind": "silent", "code": "lang_cefr"}]), "avoidable")
        self.assertEqual(mr.undecidable_class([{"kind": "silent", "code": "edu_by_sponsor"}]), "design")
        self.assertIsNone(mr.undecidable_class([{"kind": "pass", "code": "edu_ok"}]))

    def test_age_unknown_requires_sponsor_evidence(self):
        """age_unknown 归甲是**有条件**的（Muse 裁决 1）：只有当 note 带「⚠️ 未核实」
        且给出「官方无阈值 / 由 Sponsor 自行规定」的证据时才成立。

        若将来有人因为「没去查」就把项目标成未核实年龄，这个 code 会变成
        逃避核实的通用出口，甲类闸就形同虚设。这里把触发面和证据面都钉住：
        code 在白名单里 ≠ 豁免成立，证据还得在数据里。
        """
        rep = mr.audit()
        self.assertEqual(
            rep["design_exemptions_missing"],
            [],
            "有甲类豁免拿不出证据：%s 属数据债，不许按设计性不可判免责"
            % rep["design_exemptions_missing"],
        )
        hits = [
            pid
            for pid, doc in self.docs.items()
            if doc.get("eligibility", {}).get("age", {}).get("note", "").strip().startswith("⚠️")
        ]
        self.assertEqual(len(hits), 2, f"age_unknown 触发面变成 {hits}，不是既定的 2 项")
        self.assertEqual(sorted(hits), ["global-aiesec-global-talent", "us-j1-summer-work-travel"])
        for pid in hits:
            note = self.docs[pid]["eligibility"]["age"]["note"]
            self.assertTrue(
                mr.AGE_NO_THRESHOLD_EVIDENCE.search(note),
                f"{pid} 的 age.note 没有「官方无阈值 / 由 Sponsor 自行规定」的证据，不许以 age_unknown 免责",
            )
            code = {d["code"] for d in mr.judge(self.docs[pid], mr.SAMPLES["C"])[1]
                    if d["dim"] == "age"}
            self.assertEqual(code, {"age_unknown"}, pid)

        # 反例：同样是 ⚠️ 前缀，但 note 只说「没查」——必须落乙类，不许免责
        bare = {
            "eligibility": {"age": {"min": 0, "max": 99, "note": "⚠️ 未核实，尚未查官网。"}},
            "program": {"id": "synthetic", "name": "synthetic"},
        }
        dims = [{"dim": "age", "kind": "silent", "code": "age_unknown"}]
        self.assertFalse(mr.design_exemption_holds("age_unknown", bare))
        self.assertEqual(mr.undecidable_class(dims, bare), "avoidable")
        # 不传 doc 时只看 code（judge() 内部与前端契约不受影响）
        self.assertEqual(mr.undecidable_class(dims), "design")

    def test_stop_line_message_matches_threshold(self):
        """报告与终端文案里的阈值必须与常量同源（提案 R4）。

        原先 render_markdown 与 --json 各自写死「33.3%」，阈值一改就两处漂移，
        报告会指着一条已经不在管事的线说「越线了」。
        """
        rep = mr.audit()
        for text in (mr.render_markdown(rep), mr.ratio_text(mr.STOP_LINE_RATIO)):
            self.assertIn("1/3", text)
            self.assertNotIn("33.3%", text)
        r = run_cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("1/3", r.stdout)
        self.assertNotIn("33.3%", r.stdout)
        self.assertIn("只看乙类", r.stdout)
        # 三口径必须在同一行上（提案 R6）
        for name in ("A", "B", "C"):
            line = [ln for ln in r.stdout.splitlines() if ln.strip().startswith(name + " ")][0]
            self.assertIn("乙类", line)
            self.assertIn("全口径", line)
            self.assertIn("甲类", line)


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
        """`other_requirements` 里 required 的前置要求必须进入判定，且**类别要对**。

        P1c 改口径：uk-graduate-visa 的原文是 `You must be in the UK when you
        apply`——**在地**要求，不是「须先在英国持学生签完成课程」那种身份前置。
        旧断言钉的是 `local_status / pre_local_status / gap`，那正是 PRE_LOCAL_STATUS
        末支把在地吞成身份的产物（batch8 §1.2② 立项的那条错误）。

        P1d 接地后这条要求**可判了**，于是它的三态取决于画像现居地：

        | 画像 | 现居 | 判 | code |
        |---|---|---|---|
        | A / B | CN | cannot | `pre_inside_country_no` |
        | C | TW | cannot | `pre_inside_country_no` |

        三人都不在英国，所以都判 fail。这一条同时钉住两点：① 类别仍是 inside
        （不是 local_status——方向错了会让人以为补一段经历就行）；② 判出来的是
        「你不在英国」，而不是「你差一段留学经历」。
        """
        self.assertEqual(mr.precondition_kinds(self.docs["uk-graduate-visa"]), ["inside"])
        self.assertEqual(mr.precondition_kind(self.docs["uk-graduate-visa"]), "inside")
        pre = [d for d in mr.judge(self.docs["uk-graduate-visa"], mr.SAMPLES["B"])[1]
               if d["dim"] == "precondition" and d["code"].startswith("pre_inside")]
        self.assertEqual(len(pre), 1)
        self.assertEqual(pre[0]["code"], "pre_inside_country_no", pre[0])
        self.assertEqual(pre[0]["kind"], "fail", pre[0])
        # 判 fail 的理由必须指向「人不在英国」，不是「学历/经历不够」
        self.assertIn("GB", pre[0]["need"])
        self.assertIn("CN", pre[0]["have"])
        # 旧口径的三件套一个都不许再出现（方向错的 gap 会让人以为补一段经历就行）
        codes = {d["code"] for d in mr.judge(self.docs["uk-graduate-visa"], mr.SAMPLES["B"])[1]}
        self.assertNotIn("pre_local_status", codes)
        self.assertNotIn("pre_unclassified", codes)
        state = mr.judge(self.docs["uk-graduate-visa"], mr.SAMPLES["B"])[0]
        self.assertEqual(state, "cannot")

    def test_4_3_no_program_with_precondition_judges_can(self):
        """全库顺查：只要项目有 required 的**任一**前置族，三画像下都不许判「能申」。

        这一条比单点断言更狠：它不依赖某个项目当前的具体结论，只守
        「有前置要求就不能说谁都能申」。落空（读不懂）也算违规 ——
        读不懂必须落 unclassified/silent，不能当作「没有要求」。

        P1c 改口径：影响面从「17 个项目有 residency_requirement」变成
        「17 个项目有前置族中的至少一族」。**条数仍是 17**，但构成变了：
        9 个项目只剩在地族、6 个只剩身份族、2 个（de-20 / us-f1-opt）两族都有。
        所以这里按「任一前置族」取，而不是给两个 type 各写一遍（那会把
        de-20 / us-f1-opt 数两遍，17 变 19）。
        """
        PRE_TYPES = (mr.REQ_TYPE_RESIDENCY, mr.REQ_TYPE_LOCATION)
        checked = 0
        for pid, doc in self.docs.items():
            reqs = [
                r
                for r in ((doc.get("eligibility") or {}).get("other_requirements") or [])
                if r.get("required") is True and r.get("type") in PRE_TYPES
            ]
            if not reqs:
                continue
            checked += 1
            self.assertTrue(
                mr.precondition_kinds(doc), f"{pid} 有前置要求但没读出任何类别"
            )
            for sample in ("A", "B", "C"):
                state = mr.judge(doc, mr.SAMPLES[sample])[0]
                self.assertNotEqual(state, "can", f"{pid}/{sample} 有前置要求却判了能申")
        self.assertEqual(checked, 17, f"带 required 前置要求的项目数变了：{checked}")

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


class Phase2P0(unittest.TestCase):
    """二期 P2-0 第 1 腿：两条漏网的回归断言（派单 2026-11-13 全库抽查节）。

    守的仍是「不许静默判过」：原文写了、结构化字段表达不了的要求，结论必须
    降级并写明差什么，不许因为字段位在就判达标。
    """

    @classmethod
    def setUpClass(cls):
        cls.docs = {d["program"]["id"]: d for d in mr.load_programs()}

    def dim(self, pid, sample, dim):
        _, dims = mr.judge(self.docs[pid], mr.SAMPLES[sample])
        for d in dims:
            if d["dim"] == dim:
                return d
        return None

    # —— nl-orientation-year：「申请日前 3 年内完成学业/研究」——
    def test_nl_orientation_recency_window_is_not_silently_passed(self):
        """原文两处「在申请日前 3 年内于荷兰从事过科研 / 取得 Erasmus Mundus 学位」，
        age.note 另写「须在申请日之前 3 年内完成学业或研究」。

        结构化 education 只有 `bachelor_completed`，没有毕业年份；画像也只采集
        学历层级。B（本科毕业）与 C（本科毕业）原先都是 `edu_ok`——一个已毕业
        十年的人会被判「能申」。现在必须 `edu_recency_unknown`/`silent`。

        A 是在读本科，层级就不够，仍应 edu_low/fail，不能被这条吞掉。
        """
        self.assertEqual(mr.edu_recency_years(self.docs["nl-orientation-year"]), 3)
        for sample in ("B", "C"):
            d = self.dim("nl-orientation-year", sample, "education")
            self.assertEqual(d["code"], "edu_recency_unknown", d)
            self.assertEqual(d["kind"], "silent", d)
            self.assertIn("3 年", d["need"], d)
            self.assertNotEqual(
                mr.judge(self.docs["nl-orientation-year"], mr.SAMPLES[sample])[0],
                "can",
                f"{sample} 不应在毕业时限未采集时判能申",
            )
        # A 仍因学历层级不足判 fail（不能把所有画像统一降级成 silent 了事）
        a = self.dim("nl-orientation-year", "A", "education")
        self.assertEqual(a["kind"], "fail")
        self.assertEqual(a["code"], "edu_low")

    def test_recency_detector_does_not_swallow_neighbour_programs(self):
        """反例必须留在反例状态：同库另两处「N 年内」不是毕业时限硬门槛。

        - `de-16e-internship`「②在申请前 2 年内已取得学历」与「①在读」是**或**
          关系，按硬门槛判会把在读的人误降级；
        - `uk-hpi-visa`「学位须在申请前 5 年内授予」已由 edu_place_unknown 覆盖，
          再命中一次就是同一缺口报两遍。

        命中集合精确等于 {nl-orientation-year}，否则这条正则放宽了。
        """
        hits = {
            pid: mr.edu_recency_years(doc)
            for pid, doc in self.docs.items()
            if mr.edu_recency_years(doc)
        }
        self.assertEqual(hits, {"nl-orientation-year": 3})
        self.assertEqual(
            self.dim("de-16e-internship", "B", "education")["code"], "edu_ok"
        )
        self.assertEqual(
            self.dim("uk-hpi-visa", "C", "education")["code"], "edu_place_unknown"
        )

    # —— us-j1-camp-counselor：「须落实营地岗位」+「须属四类身份之一」——
    def test_camp_counselor_job_placement_is_not_silently_passed(self):
        """22 CFR 62.30(h)(3)：`Under no circumstance facilitate the entry into the
        United States of a participant for whom a camp placement has not been
        pre-arranged`。这条在数据里落在 documents 的一条必交材料上，不在
        residency_requirement 里，所以过去一个字节没读，A/B/C 全判 can。

        现在必须出 `pre_job_placement`/`gap`：岗位可以补，属「差什么」。
        """
        self.assertTrue(mr.job_placement_required(self.docs["us-j1-camp-counselor"]))
        for sample in ("A", "B", "C"):
            d = self.dim("us-j1-camp-counselor", sample, "precondition")
            self.assertIsNotNone(d, sample)
            self.assertEqual(d["code"], "pre_job_placement", d)
            self.assertEqual(d["kind"], "gap", d)
            self.assertNotEqual(
                mr.judge(self.docs["us-j1-camp-counselor"], mr.SAMPLES[sample])[0],
                "can",
                f"{sample} 在岗位未落实时判了能申",
            )

    def test_camp_counselor_participant_category_is_not_silently_passed(self):
        """`Are bona fide youth workers, students, teachers, or individuals with
        specialized skills`（22 CFR 62.30(b)(2)）被压在 education.note 里，而结构化
        `minimum_level` 是 `any` —— 判 edu_ok 等于说「学历层级任何值都达标」。

        原文还明说由 Sponsor 判断是否成立，与 §4-5 的 edu_by_sponsor 同口径，
        判 `edu_category_unknown`/`silent`。
        """
        self.assertTrue(
            mr.participant_category_required(self.docs["us-j1-camp-counselor"])
        )
        for sample in ("A", "B", "C"):
            d = self.dim("us-j1-camp-counselor", sample, "education")
            self.assertEqual(d["code"], "edu_category_unknown", d)
            self.assertEqual(d["kind"], "silent", d)

    def test_placement_and_category_detectors_are_scoped(self):
        """两条探测器都必须只命中营地辅导员，否则会把别的项目误降级。

        `au-407-training` 的「培训项目须属于三类之一」是**培训类型**不是申请人
        身份，这正是收窄锚点到「身份」二字的原因——放宽后它会假阳。
        """
        self.assertEqual(
            [p for p, d in self.docs.items() if mr.job_placement_required(d)],
            ["us-j1-camp-counselor"],
        )
        self.assertEqual(
            [p for p, d in self.docs.items() if mr.participant_category_required(d)],
            ["us-j1-camp-counselor"],
        )
        # 兄弟项目 us-j1-intern 的 DS-7002 是实习合同，不是「预先落实岗位」，不许连带降级
        self.assertFalse(mr.job_placement_required(self.docs["us-j1-intern"]))
        self.assertFalse(mr.participant_category_required(self.docs["us-j1-intern"]))

    # —— de-chancenkarte：「资格须被主管机构认定」+「积分 ≥6」——
    def test_chancenkarte_credential_recognition_is_not_silently_passed(self):
        """`eligibility.passport_types.note` 原文：「两条硬门槛：①学历或职业资格
        被德国主管机构认定（学历一般通过 anabin 数据库核验）；②满足「专业人士」
        条件或积分达到 6 分。」

        结构化 education 只有 `bachelor_completed`——那说的是「你最高读到本科」，
        与「这份学历被 ZAB/anabin 认定为等效」是两件事（认定结论可以是不等效）。
        画像也不采集积分。过去 B（本科毕业）直接判 edu_ok，于是「学历没被认定」
        「积分不够」两个都能过。现在必须 `edu_credential_unknown`/`silent`。
        """
        self.assertTrue(mr.credential_recognition_required(self.docs["de-chancenkarte"]))
        self.assertEqual(mr.points_threshold(self.docs["de-chancenkarte"]), 6)
        for sample in ("B", "C"):
            d = self.dim("de-chancenkarte", sample, "education")
            self.assertEqual(d["code"], "edu_credential_unknown", d)
            self.assertEqual(d["kind"], "silent", d)
            # need 里两项门槛都要有，少一项就是漏了半条原文
            self.assertIn("主管机构认定", d["need"], d)
            self.assertIn("6 分", d["need"], d)
            self.assertNotEqual(
                mr.judge(self.docs["de-chancenkarte"], mr.SAMPLES[sample])[0],
                "can",
                f"{sample} 在资格认定与积分未采集时判了能申",
            )
        # A 是在读本科，层级本身不够，仍应 fail——不能被这条统一吞成 silent
        a = self.dim("de-chancenkarte", "A", "education")
        self.assertEqual(a["kind"], "fail", a)
        self.assertEqual(a["code"], "edu_low", a)

    def test_credential_detector_does_not_swallow_points_only_programs(self):
        """反例：奥地利红白红卡也写「积分达到 70 分」，但它的原文没有「被主管机构
        认定」这条硬门槛（仅受管制职业需正式认定，且已在真 note 里写明）。
        本腿不扩围，命中集合必须精确等于 {de-chancenkarte}——放宽一个词就会把
        一条无关项目一起改判。
        """
        hits = [p for p, d in self.docs.items() if mr.credential_recognition_required(d)]
        self.assertEqual(hits, ["de-chancenkarte"])
        self.assertEqual(
            [p for p, d in self.docs.items() if mr.points_threshold(d)],
            ["at-rwr-card-vhq", "de-chancenkarte"],
        )        # 点数探测器只是被认定分支引用；单有积分制的项目不受它影响
        self.assertEqual(
            self.dim("at-rwr-card-vhq", "B", "education")["code"], "edu_years_unknown"
        )

    # —— no-skilled-worker：「具体雇主 offer」+「≥80%」+「岗位与资格对应」——
    def test_skilled_worker_employer_offer_is_not_silently_passed(self):
        """三处原文同属一个前提「先有一份合格聘用」：

        - `other_requirements.internship_contract`：`You must have received a
          concrete job offer from one specific employer in Norway.`
        - `documents`：`If you have been offered at least an 80% position, we
          will accept this.`（低于 80% 不接受）
        - `education.note` 末句：「岗位须与学历或资格对应」

        过去这三处一个字节没读，B/C（本科毕业）被判 can——「还没 offer」也能申。
        现在必须 `pre_employer_offer`/`gap`：offer 能争取，属「差什么」。
        """
        self.assertTrue(mr.employer_offer_required(self.docs["no-skilled-worker"]))
        for sample in ("A", "B", "C"):
            d = self.dim("no-skilled-worker", sample, "precondition")
            self.assertIsNotNone(d, sample)
            self.assertEqual(d["code"], "pre_employer_offer", d)
            self.assertEqual(d["kind"], "gap", d)
            # 三条要求都要落进 need，只写「要 offer」会漏掉 80% 与岗位匹配两条
            self.assertIn("80%", d["need"], d)
            self.assertIn("对应", d["need"], d)
            self.assertNotEqual(
                mr.judge(self.docs["no-skilled-worker"], mr.SAMPLES[sample])[0],
                "can",
                f"{sample} 在没有具体雇主 offer 时判了能申",
            )
        # B/C 不因教育维被判死：缺口只有 offer 这一条，学历层级是够的
        self.assertEqual(self.dim("no-skilled-worker", "B", "education")["code"], "edu_ok")

    def test_employer_offer_detector_is_scoped(self):
        """新加坡 EP / S Pass 也要求「有雇主 offer」，但它们要求的是**offer 本身**
        （`Have a job offer in Singapore`），没有「具体某一个雇主 + ≥80% 岗位 +
        岗位与资格对应」这三条并列。本腿不扩围：命中集合必须只有挪威这条。

        同时两条岗位前置探测器互斥——营地 placement ≠ 雇主担保 offer，任何一个
        放宽都会让另一边多报一条重复缺口。
        """
        self.assertEqual(
            [p for p, d in self.docs.items() if mr.employer_offer_required(d)],
            ["no-skilled-worker"],
        )
        self.assertFalse(mr.job_placement_required(self.docs["no-skilled-worker"]))
        self.assertFalse(mr.employer_offer_required(self.docs["us-j1-camp-counselor"]))
        # 新加坡 EP 不许被连带降级（它有自己的前置判定口径，本腿不动）
        self.assertFalse(mr.employer_offer_required(self.docs["sg-employment-pass"]))
        self.assertEqual(self.dim("sg-employment-pass", "B", "education")["code"], "edu_ok")


class P1b2TypedValues(unittest.TestCase):
    """P1b-2：把 P1b-1 迁好的 typed 值接进判定后的方向回归（派单 2026-11-15）。

    这一组守的是**判定方向**，不是「当前结论长什么样」。三个家族里各有一条
    方向相反的条目，照 type 名字猜方向会把人判反——而且反得很难发现，因为
    另一种读法在字面上也说得通。

    编号 ①–⑤ 与派单「硬规则」的方向性回归清单一一对应，改动时不要重排。
    """

    @classmethod
    def setUpClass(cls):
        cls.docs = {d["program"]["id"]: d for d in mr.load_programs()}

    def pre(self, pid, sample="B", **override):
        pr = dict(mr.SAMPLES[sample])
        pr.update(override)
        _, dims = mr.judge(self.docs[pid], pr)
        return [d for d in dims if d["dim"] == "precondition"]

    def dim(self, pid, sample, dim):
        _, dims = mr.judge(self.docs[pid], mr.SAMPLES[sample])
        return next((d for d in dims if d["dim"] == dim), None)

    # —— ① au-485-graduate：须持过学签，不许再被读成「未持过」——
    def test_485_graduate_is_positive_prior_visa_not_negative(self):
        """原文是 `have held a Student visa in the last 6 months`——**须持过**。

        P1b-1 之前这条挂在 `no_prior_visa`（未持过任何签证）下，语义完全相反：
        照名字接线会把「持过学签」的正常申请人判成不满足，把「没持过」的人
        判成满足。两类的结论都反。

        现在必须是 `prior_specific_visa_required`，判 silent（画像不采集签证史），
        且**绝不能**产出「未持过」那种口径的 code。
        """
        doc = self.docs["au-485-graduate"]
        self.assertIn("prior_specific_visa_required", mr.requirement_types(doc))
        self.assertNotIn("no_prior_visa", mr.requirement_types(doc))
        for sample in ("A", "B", "C"):
            codes = {d["code"] for d in self.pre("au-485-graduate", sample)}
            self.assertIn("pre_prior_visa_required", codes, sample)
            # 反向读法的 code 一个都不许出现
            self.assertNotIn("pre_prior_visa_none", codes, sample)
            self.assertNotIn("pre_prior_visa_used", codes, sample)
            d = next(x for x in self.pre("au-485-graduate", sample)
                     if x["code"] == "pre_prior_visa_required")
            self.assertEqual(d["kind"], "silent", d)

    # —— ② 三个项目的家属「允许」不得判成禁止 ——
    def test_dependents_allowed_is_not_read_as_forbidden(self):
        """au-485-vocational / uk-graduate-visa 原文明确**允许**家属随行
        （`bring your family members`），us-f1-opt 是「家属可随行但不得就业」。

        这三个值过去都挂在 `no_dependents`（不可带家属）下。照名字接线会让
        「本项目允许带家属」变成「本项目不许带家属」——正好相反的一条建议。
        """
        for pid in ("au-485-vocational", "uk-graduate-visa"):
            doc = self.docs[pid]
            self.assertIn("dependents_allowed", mr.requirement_types(doc, required_only=False))
            self.assertNotIn("no_dependents", mr.requirement_types(doc))
            for sample in ("A", "B", "C"):
                deps = [d for d in self.pre(pid, sample) if d["code"].startswith("pre_dependents")]
                codes = {d["code"] for d in deps}
                # 判 na（只作展示，不构成闸门），且不出现任何禁令 code
                self.assertIn("pre_dependents_allowed", codes, f"{pid}/{sample}")
                self.assertNotIn("pre_dependents_child_present", codes, f"{pid}/{sample}")
                self.assertNotIn("pre_dependents_other_present", codes, f"{pid}/{sample}")
                # 只在**家属维**上断言不判 fail：同一项目的学历维可能合法地判 fail
                self.assertNotIn(
                    "fail", {d["kind"] for d in deps}, f"{pid}/{sample} 家属允许被读成了禁止"
                )
        # us-f1-opt：禁的是「就业」不是「同行」，无家属时应 pass 而非 fail
        d = next(x for x in self.pre("us-f1-opt", "B") if x["code"].startswith("pre_dependents"))
        self.assertEqual(d["code"], "pre_dependents_none", d)
        self.assertEqual(d["kind"], "pass", d)

    # —— ③ SWT 在读判 pass、毕业生不因此 pass ——
    def test_swt_enrollment_direction(self):
        """`enrollment_proof` 是三个学籍值里**唯一真该在读**的一个
        （global-iaeste / us-j1-summer-work-travel 两条）。

        在读 → pass；已毕业 → fail（在读要求做不到）。判反会让毕业生以为能申。
        """
        for pid in ("us-j1-summer-work-travel", "global-iaeste"):
            self.assertIn("enrollment_proof", mr.requirement_types(self.docs[pid]))
            d_in = next(x for x in self.pre(pid, "A") if x["code"].startswith("pre_enroll")
                        or x["code"] == "pre_not_enrolled")
            self.assertEqual(d_in["code"], "pre_enrolled_ok", pid)
            self.assertEqual(d_in["kind"], "pass", pid)
            d_grad = next(x for x in self.pre(pid, "B") if x["code"].startswith("pre_enroll")
                          or x["code"] == "pre_not_enrolled")
            self.assertEqual(d_grad["code"], "pre_not_enrolled", pid)
            self.assertEqual(d_grad["kind"], "fail", pid)
            self.assertEqual(mr.judge(self.docs[pid], mr.SAMPLES["B"])[0], "cannot", pid)

    # —— ④ ie-third-level-graduate 的毕业证明被识别 ——
    def test_ie_degree_proof_is_recognised(self):
        """`degree_completed_proof` = 须已毕业，与 `enrollment_proof` 方向相反。

        爱尔兰这条原文是 `evidence of the final award being attained`，
        明确「不是在读期间续签」。B/C（已毕业）应 pass，A（在读）应 fail。
        """
        self.assertIn("degree_completed_proof", mr.requirement_types(self.docs["ie-third-level-graduate"]))
        for sample in ("B", "C"):
            d = next(x for x in self.pre("ie-third-level-graduate", sample)
                     if x["code"] in ("pre_degree_ok", "pre_degree_missing"))
            self.assertEqual(d["code"], "pre_degree_ok", sample)
            self.assertEqual(d["kind"], "pass", sample)
        d_a = next(x for x in self.pre("ie-third-level-graduate", "A")
                   if x["code"] in ("pre_degree_ok", "pre_degree_missing"))
        self.assertEqual(d_a["code"], "pre_degree_missing", d_a)
        self.assertEqual(d_a["kind"], "fail", d_a)

    # —— ⑤ 4 条「诚实条目」行为与改前一致 ——
    def test_four_honest_entries_unchanged(self):
        """设计稿 §5.4 点名的 4 条 name-honest 条目：接线不得改变它们的结论。

        `kr-h1` / `uk-short-term-study-visa`（家属统称）、`global-iaeste` /
        `us-j1-summer-work-travel`（真在读）。前两条的判定由别的维驱动，
        后两条本单确实改判了（在读要求判出来了）——所以这里钉的是
        **它们的前置维口径与其原文一致**，不是「结论不许变」。
        """
        # kr-h1：禁「家属统称」，画像无家属 → pass；有子女 → 也是 fail（统称包含子女）
        d = next(x for x in self.pre("kr-h1-working-holiday", "B") if x["code"].startswith("pre_dependents"))
        self.assertEqual((d["code"], d["kind"]), ("pre_dependents_none", "pass"), d)
        d = next(x for x in self.pre("kr-h1-working-holiday", "B", dependents="children")
                 if x["code"].startswith("pre_dependents"))
        self.assertEqual((d["code"], d["kind"]), ("pre_dependents_other_present", "fail"), d)
        # uk-short-term-study-visa：同上
        d = next(x for x in self.pre("uk-short-term-study-visa", "B") if x["code"].startswith("pre_dependents"))
        self.assertEqual((d["code"], d["kind"]), ("pre_dependents_none", "pass"), d)
        # 两条真在读项目：A（在读）pass
        for pid in ("global-iaeste", "us-j1-summer-work-travel"):
            d = next(x for x in self.pre(pid, "A") if x["code"].startswith("pre_enroll"))
            self.assertEqual(d["kind"], "pass", pid)

    # —— 缺省即未知：这是全组的地基，单独钉一遍 ——
    def test_missing_profile_fields_stay_silent(self):
        """画像缺字段时必须判 silent（不可判），**绝不默认 pass**。

        这条与「三张样例画像填了值」是两件事，必须分开钉：
        样例画像填值让多数项目能判出来，但引擎本身的缺省行为必须仍是 silent。
        否则「补夹具」与「洗白」在代码上看不出区别——将来有人删掉这个分支，
        样例画像照样全绿，而真实用户会开始看到虚假的「能申」。
        """
        cases = [
            ("au-462-work-holiday", "dependents", "pre_dependents_unknown"),
            ("kr-h1-working-holiday", "dependents", "pre_dependents_unknown"),
            ("us-f1-opt", "dependents", "pre_dependents_unknown"),
            ("ca-pgwp", "prior_participation", "pre_participation_unknown"),
            ("nz-post-study-work", "prior_participation", "pre_participation_unknown"),
            ("au-462-work-holiday", "prior_same_category_visa", "pre_prior_visa_unknown"),
            ("uk-hpi-visa", "prior_same_category_visa", "pre_prior_visa_unknown"),
            ("global-iaeste", "enrollment_status", "pre_enrollment_unknown"),
            ("us-j1-summer-work-travel", "enrollment_status", "pre_enrollment_unknown"),
        ]
        for pid, field, want in cases:
            pr = {k: v for k, v in mr.SAMPLES["B"].items() if k != field}
            self.assertNotIn(field, pr, f"{pid} 的用例没能真正去掉 {field}")
            _, dims = mr.judge(self.docs[pid], pr)
            got = {d["code"]: d["kind"] for d in dims if d["dim"] == "precondition"}
            self.assertIn(want, got, f"{pid} 缺 {field} 时未判 silent：{got}")
            self.assertEqual(got[want], "silent", f"{pid} 缺 {field} 时判成了 {got[want]}")

    # —— 非闸门值：不许把材料当成门槛 ——
    def test_non_gate_values_are_na_not_silent(self):
        """`credential_scoring_input` / `declaration_document` 明确不是资格闸。

        判 silent 会让本来能申的项目变「不可判」——把「我们把材料当成了门槛」
        这件事伪装成数据债。
        """
        for pid in ("sg-employment-pass", "sg-s-pass"):
            self.assertIn("credential_scoring_input",
                          mr.requirement_types(self.docs[pid], required_only=False))
            d = next(x for x in self.pre(pid, "B") if x["code"] == "pre_scoring_input_only")
            self.assertEqual(d["kind"], "na", pid)
            # 别被连带降级：EP / S Pass 对 B 仍应能申（与既有口径一致）
            self.assertEqual(mr.judge(self.docs[pid], mr.SAMPLES["B"])[0], "can", pid)
        self.assertIn("declaration_document",
                      mr.requirement_types(self.docs["fr-recherche-emploi"], required_only=False))
        d = next(x for x in self.pre("fr-recherche-emploi", "B")
                 if x["code"] == "pre_declaration_only")
        self.assertEqual(d["kind"], "na", d)

    # —— 冷却期本单不接线：确认没被顺手接进来 ——
    def test_cooldown_periods_not_wired(self):
        """冷却期 4 段（au-485-graduate 6 个月、research-scholar 24/12 个月与 212(e)）
        本单不接线（P2），必须保持现状。

        判据：这两条项目的 note 里仍带月数/年数，而引擎不对它产出任何
        「按日期比较」的 code——它们落 silent，且 silent 的理由是「未采集签证史」，
        不是「已按冷却期算过」。
        """
        for pid in ("au-485-graduate", "us-j1-research-scholar"):
            codes = {d["code"] for d in self.pre(pid, "B")}
            # 没有任何 code 表示「冷却期已计算」
            self.assertFalse(
                [c for c in codes if "cool" in c or "month" in c],
                f"{pid} 出现了冷却期相关 code：{codes}",
            )
        # research-scholar 仍未接任何签证史分支（它挂的是 no_prior_visa 原值，本单不认）
        doc = self.docs["us-j1-research-scholar"]
        self.assertIn("no_prior_visa", mr.requirement_types(doc))


class P1cPreconditionSplit(unittest.TestCase):
    """P1c：身份与在地拆成两个独立类别后的方向回归（派单 2026-11-15 续腿）。

    守的是**类别归属**与**方向**，不是「当前结论长什么样」。本组每条都写明
    「若照旧接线会错成什么」，因为两种读法在字面上都说得通。
    """

    @classmethod
    def setUpClass(cls):
        cls.docs = {d["program"]["id"]: d for d in mr.load_programs()}

    def pre(self, pid, sample="B"):
        _, dims = mr.judge(self.docs[pid], mr.SAMPLES[sample])
        return [d for d in dims if d["dim"] == "precondition"]

    # —— ① 在地归 inside，不再借身份的 code 发声 ——
    def test_inside_requirements_are_not_read_as_identity(self):
        """三条 `You must be in ... when you apply` 必须判 inside，不是 local_status。

        改前它们靠 `PRE_LOCAL_STATUS` 末支判成 `gap / pre_local_status`，
        need 写的是「先在该国持学生/居留身份并完成学业」——对已经在该国读完书
        的申请人（正是这三个项目的目标人群）等于一句反向建议。

        P1d 起这条要求接地了：三画像现居 CN/CN/TW，都不在这三国，所以三个
        画像下都判 `fail / pre_inside_country_no`。这里钉的是**类别归属**——
        code 必须以 `pre_inside_country` 开头（三态里的哪一种随画像，但不许
        再借 `pre_local_status` 或掉成 `pre_unclassified`）。
        """
        for pid in ("au-485-graduate", "au-485-vocational", "uk-graduate-visa"):
            self.assertEqual(mr.precondition_kinds(self.docs[pid]), ["inside"], pid)
            for sample in ("A", "B", "C"):
                codes = {d["code"] for d in self.pre(pid, sample)}
                self.assertTrue(
                    any(c.startswith("pre_inside_country") for c in codes),
                    f"{pid}/{sample} 没判出在地要求：{codes}",
                )
                self.assertNotIn("pre_local_status", codes, f"{pid}/{sample}")
                # 也不能掉成读不懂（那是把已识别的要求说成没识别）
                self.assertNotIn("pre_unclassified", codes, f"{pid}/{sample}")
                d = next(x for x in self.pre(pid, sample)
                         if x["code"].startswith("pre_inside_country"))
                # 三人都不在项目所在国 → fail（不是 silent：现居地已经采集到了）
                self.assertEqual((d["code"], d["kind"]), ("pre_inside_country_no", "fail"), d)

    # —— ② 身份与在地同时存在时，两条都要出结论（不吞并）——
    def test_identity_and_location_both_reported(self):
        """us-f1-opt / de-20-job-search 各有两份 source，两族必须各自留痕。

        裁决 2「借接的 code 不算兜住」：改前 us-f1-opt 的在地条靠身份条拉起的
        `pre_local_status` 发声，看上去「已判」，实际那条要求零读点。

        P1d 起在地条自己会判（现居 ≠ US/DE → fail），身份条仍是 gap。
        两条并存时整体 take 最差：fail > gap，所以这两个项目在 B 上都判 cannot。
        """
        for pid in ("us-f1-opt", "de-20-job-search"):
            self.assertEqual(mr.precondition_kinds(self.docs[pid]), ["local_status", "inside"], pid)
            codes = {d["code"] for d in self.pre(pid, "B")}
            self.assertIn("pre_local_status", codes, pid)
            self.assertIn("pre_inside_country_no", codes, pid)
            # 单值形状仍取第一项（身份族在前），给老调用方留的兼容口
            self.assertEqual(mr.precondition_kind(self.docs[pid]), "local_status", pid)

    # —— ③ 删末支不能把真身份句一起删掉 ——
    def test_identity_anchor_widened_keeps_real_identity_sentences(self):
        """删掉末支后，靠扩展锚点保住的是「且持」这类并列句。

        us-f1-opt 的真身份句是「须持有效 F-1 学生身份，**且该身份**在递交当日
        仍未失效」——「且」起头。锚点若不放宽到「（须|且）持」，这条会跟着
        末支一起掉成 unclassified（batch9a §1.2 实测：只删末支则 11 项里 5 项
        掉 unclassified，补「且持」救回 us-f1-opt）。
        """
        self.assertIn("local_status", mr.precondition_kinds(self.docs["us-f1-opt"]))
        # 身份族真身份句必须仍判 local_status（不是 home_residence / citizenship）
        ident = mr._classify_identity(
            mr._precondition_notes(self.docs["us-f1-opt"], mr.REQ_TYPE_RESIDENCY)
        )
        self.assertEqual(ident, "local_status")

    # —— ④ 全库顺查：两族 type 的每个值都读得出来，且不落 unclassified ——
    def test_every_precondition_program_classifies(self):
        """17 个带必填前置的项目，两族都要读出一个具体类别。

        允许 unclassified（那是「有要求但没读懂」的诚实留痕），只要不是**两族
        全空**——全空意味着「有要求却被当成没有要求」，那是 §4-3 的原始错误。
        """
        PRE = (mr.REQ_TYPE_RESIDENCY, mr.REQ_TYPE_LOCATION)
        n = 0
        for pid, doc in self.docs.items():
            reqs = [
                r
                for r in ((doc.get("eligibility") or {}).get("other_requirements") or [])
                if r.get("required") is True and r.get("type") in PRE
            ]
            if not reqs:
                self.assertEqual(mr.precondition_kinds(doc), [], pid)
                continue
            n += 1
            self.assertTrue(mr.precondition_kinds(doc), f"{pid} 两族全空")
        self.assertEqual(n, 17)

    # —— ⑤ outside 方向不许被 inside 抢走（镜像关系）——
    def test_outside_is_not_swallowed_by_inside(self):
        """`se-look-for-work` 要「境外」、`uk-graduate-visa` 要「境内」，互为镜像。

        两条要求共用一个 code 会让「必须人在境外」与「必须人在境内」在报告里
        长得一模一样（batch8 立项理由）。合在一起判等于把方向抹平。
        """
        self.assertEqual(mr.precondition_kinds(self.docs["se-look-for-work"]), ["outside"])
        self.assertEqual(mr.precondition_kinds(self.docs["au-407-training"]), ["outside"])
        for pid in ("se-look-for-work", "au-407-training"):
            codes = {d["code"] for d in self.pre(pid, "B")}
            self.assertIn("pre_outside_country", codes, pid)
            self.assertNotIn("pre_inside_country", codes, pid)

    # —— ⑥ 新码必须登记乙类，且与 outside 同在 CLASS_B ——
    def test_inside_code_is_registered_as_class_b(self):
        """新 silent code 不登记就会撞上 `test_every_silent_code_is_classified`。

        同时钉住它**不是**甲类：现居地是「画像没采集的个人事实」，补一个
        `current_location` 字段就能判——按 P2-1 §1.1 判据属乙类。
        """
        self.assertIn("pre_inside_country", mr.CLASS_B_CODES)
        self.assertIn("pre_outside_country", mr.CLASS_B_CODES)
        self.assertNotIn("pre_inside_country", mr.BY_DESIGN_CODES)

    # —— ⑦ flags_of 的两族形状（前端契约）——
    def test_flags_carry_both_kind_and_kinds(self):
        """`kinds` 是数组、`kind` 是单值：前端按 kinds 判，老断言按 kind 读。

        只给 kind 会让 us-f1-opt 的在地条在地图上消失；只给 kinds 会打断
        `p21_worksheets.rule_holds()` 之外的历史调用方。
        """
        for pid in ("us-f1-opt", "de-20-job-search"):
            flags = mr.flags_of(self.docs[pid])["precondition"]
            self.assertIsInstance(flags["kinds"], list, pid)
            self.assertEqual(flags["kinds"], mr.precondition_kinds(self.docs[pid]), pid)
            self.assertEqual(flags["kind"], flags["kinds"][0], pid)
        # 无前置要求的项目：kinds 空数组，kind 为 None（不是空数组）
        empty = next(
            d for d in self.docs.values()
            if not mr.precondition_kinds(d)
        )
        f = mr.flags_of(empty)["precondition"]
        self.assertEqual(f["kinds"], [])
        self.assertIsNone(f["kind"])

    # —— ⑧ §0.2 au-462 受抚养子女按「受抚养关系」定义，不限年龄 ——
    def test_au462_child_ban_is_dependency_not_age(self):
        """官方原文 `not be accompanied by dependent children`——**按受抚养关系定义**。

        「未成年子女」是旧记法加的限定，不是原文的边界：18 岁以上仍在校且受
        抚养者照样在禁内（数据侧 note 已在 1b5552d 按官方原文改回）。

        引擎侧不设年龄分支：画像 `children` 这一档本身就是「有受抚养子女」这个
        与年龄无关的事实。所以本用例守两件事——① 有子女一定判禁（含「成年」
        这个在数据里根本没有年龄粒度的情况）；② 引擎里**不许**出现按年龄切的
        第二档（那会把原文的桶按 18 岁切两半，两半都不再是原文的桶）。
        """
        doc = self.docs["au-462-work-holiday"]
        self.assertIn(mr.DEP_FORBID_CHILD, mr.requirement_types(doc))
        # note 必须仍按受抚养关系表述，不许退回「未成年」
        note = next(
            r["note"] for r in doc["eligibility"]["other_requirements"]
            if r.get("type") == mr.DEP_FORBID_CHILD
        )
        self.assertIn("dependent children", note)
        self.assertIn("不设年龄上限", note)
        # 「未成年子女」只许以「不沿用旧记法」的形式出现（引旧写法并否定它），
        # 不许作为本条的限定语独立出现。
        if "未成年" in note:
            self.assertIn("不沿用旧记法", note)

        # ① 有受抚养子女 → fail（成年与否不影响：画像这一档不按年龄切）
        for sample in ("A", "B", "C"):
            d = next(
                x for x in self.pre("au-462-work-holiday", sample)
                if x["code"].startswith("pre_dependents")
            )
            self.assertEqual((d["code"], d["kind"]), ("pre_dependents_none", "pass"), d)
        d = next(
            x for x in self._pre_with("au-462-work-holiday", "B", dependents="children")
            if x["code"].startswith("pre_dependents")
        )
        self.assertEqual((d["code"], d["kind"]), ("pre_dependents_child_present", "fail"), d)

        # ② 引擎里不许有第二档年龄切分
        self.assertFalse(
            hasattr(mr, "DEP_FORBID_ADULT_CHILD"),
            "不许为「成年子女」另立一个禁令值：原文的桶是按受抚养关系定义的，"
            "按 18 岁切两半后，两半都不再是原文那个桶",
        )

    def _pre_with(self, pid, sample, **override):
        pr = dict(mr.SAMPLES[sample])
        pr.update(override)
        _, dims = mr.judge(self.docs[pid], pr)
        return [d for d in dims if d["dim"] == "precondition"]


class P1dLocationGrounding(unittest.TestCase):
    """P1d：把 `current_location` 接进 judge() 的 `pre_inside_country` 分支。

    守的是**方向**，不是「当前结论长什么样」。在地要求有两种读法在字面上都说得
    通，而读反的代价是不对称的：判反了会把一个已经在该国的人挡在门外（他明明
    符合），或把一个不在该国的人放进去（他递不上去）。所以本组四个方向各钉一条，
    外加「缺字段必须 silent」这条地基。
    """

    @classmethod
    def setUpClass(cls):
        cls.docs = {d["program"]["id"]: d for d in mr.load_programs()}

    def pre(self, pid, **override):
        """以 B 画像为底，按需覆盖字段后取前置维。"""
        pr = dict(mr.SAMPLES["B"])
        pr.update(override)
        _, dims = mr.judge(self.docs[pid], pr)
        return [d for d in dims if d["dim"] == "precondition"]

    def pre_code(self, pid, **override):
        return next(
            (d["code"], d["kind"]) for d in self.pre(pid, **override)
            if d["code"].startswith("pre_inside_country")
        )

    # —— ① 画像在要求国 → pass ——
    def test_inside_requirement_passes_when_profile_is_in_that_country(self):
        """au-485-graduate 要求「递交时在澳洲境内」，画像现居 AU → 这一条判 pass。

        这是接地之前**永远不可能出现**的结论：旧引擎无论画像填什么都只看原文，
        一律判 silent。判 pass 的分支若写错（比如把相等写成不等），已经在澳洲
        读完书的人会看到「你不在澳洲」，而他恰恰是这个项目唯一的目标人群。
        """
        self.assertEqual(mr.precondition_kinds(self.docs["au-485-graduate"]), ["inside"])
        self.assertEqual(
            self.pre_code("au-485-graduate", current_location="AU"),
            ("pre_inside_country_ok", "pass"),
        )
        d = next(x for x in self.pre("au-485-graduate", current_location="AU")
                 if x["code"] == "pre_inside_country_ok")
        # 文案里的国别必须来自数据，不是写死的：need 说要求国、have 说现居地
        self.assertIn("AU", d["need"])
        self.assertIn("AU", d["have"])

    # —— ② 画像不在要求国 → cannot，且理由是「在地」不是别的 ——
    def test_inside_requirement_fails_when_profile_is_elsewhere(self):
        """画像现居 CN、项目在 AU → fail → 整体 cannot。

        关键断言是 **cannot 的理由必须是这一条**：若判 fail 的 code 落到别处
        （比如学历/资金），用户会去补一件无关的事，而真正挡他的是「人不在澳洲，
        这条要求补材料满足不了」。
        """
        state, dims = mr.judge(self.docs["au-485-graduate"], dict(mr.SAMPLES["B"],
                                                                 current_location="CN"))
        self.assertEqual(state, "cannot")
        failures = [d for d in dims if d["kind"] == "fail"]
        self.assertEqual([d["code"] for d in failures], ["pre_inside_country_no"], failures)
        d = failures[0]
        self.assertIn("AU", d["need"], "need 必须写明要求国")
        self.assertIn("CN", d["have"], "have 必须写明画像的现居地")
        self.assertIn("境内", d["why"])

    # —— ③ 无 location → silent（维持 P1c 的诚实结论，缺省绝不判 pass）——
    def test_missing_location_stays_silent(self):
        """画像没有 `current_location` 时必须判 silent，**绝不默认 pass**。

        这条与「三画像填了值」是两件事，必须分开钉：夹具填值让九个项目能判出来，
        但引擎本身的缺省行为必须仍是 silent。否则「补夹具」与「洗白」在代码上
        看不出区别——将来有人删掉这个分支，样例画像照样全绿，而真实用户会开始
        看到虚假的「能申」。

        四种「取不到合法值」的形态各验一遍：键缺失 / 显式 None / 空串 / 小写。
        最后一种是刻意不宽容：`cn` 只差一个大小写，但宽容匹配一旦写错，错误会
        静默传播到每一条项目，而这种错在界面上看起来完全正常。
        """
        for bad in ("absent", None, "", "cn", "CHINA", "中国"):
            pr = dict(mr.SAMPLES["B"])
            if bad == "absent":
                pr.pop("current_location", None)
                self.assertNotIn("current_location", pr)
            else:
                pr["current_location"] = bad
            _, dims = mr.judge(self.docs["au-485-graduate"], pr)
            pre = [d for d in dims if d["dim"] == "precondition"
                   and d["code"].startswith("pre_inside_country")]
            self.assertEqual(len(pre), 1, f"current_location={bad!r} 时在地维缺失")
            self.assertEqual(
                (pre[0]["code"], pre[0]["kind"]),
                ("pre_inside_country", "silent"),
                f"current_location={bad!r} 时未落 silent：{pre[0]}",
            )

    # —— ④ 项目侧拿不到国别 → 也不许硬判 ——
    def test_program_without_country_code_stays_silent(self):
        """项目侧 country_code 缺失时，「境内」无所指 → silent。

        这一支不常见，但少了它，`loc == cc` 会把画像值与 None 比较，结果恒不等
        → 恒判 fail，等于替官方拒绝。

        **不把 `GL` 也特判成缺省**：库里两条全球项目（global-aiesec /
        global-iaeste）根本没有在地要求（`precondition_kinds` 为空），`GL` 在
        它们身上永远不会被这一支读到。为它写一条没有真实用例的分支，等于给
        将来的误读留一个「看起来处理过了」的假象；真出现「全球项目 + 在地要求」
        这种组合时，应该停下来看数据，而不是让引擎猜。
        """
        doc = json.loads(json.dumps(self.docs["au-485-graduate"]))
        self.assertEqual(doc["program"]["country_code"], "AU")
        del doc["program"]["country_code"]
        for loc in ("CN", "AU"):
            pr = dict(mr.SAMPLES["B"], current_location=loc)
            _, dims = mr.judge(doc, pr)
            pre = next(d for d in dims if d["code"].startswith("pre_inside_country"))
            self.assertEqual((pre["code"], pre["kind"]),
                             ("pre_inside_country", "silent"), loc)

    # —— ⑤ 同构一条：uk-graduate-visa 的方向必须与 au-485 一致 ——
    def test_uk_graduate_visa_mirrors_the_same_direction(self):
        """英国毕业生签证的在地要求与澳洲 485 是同一类，方向必须同构。

        单点验证 au-485 不够：两条要求来自不同数据文件、不同措辞（`be in
        Australia` / `You must be in the UK`），只测一条时，另一条可以是
        「恰好也判对了」。这里用同一组画像取值把两条绑在一起验：
        在要求国 → 都 pass；不在 → 都 fail。
        """
        for pid, cc in (("au-485-graduate", "AU"), ("uk-graduate-visa", "GB")):
            self.assertEqual(self.pre_code(pid, current_location=cc),
                             ("pre_inside_country_ok", "pass"), pid)
            self.assertEqual(self.pre_code(pid, current_location="CN"),
                             ("pre_inside_country_no", "fail"), pid)

    # —— ⑥ 新码不许进甲类，旧码的乙类登记不许动 ——
    def test_grounded_codes_are_not_classified_as_silent(self):
        """接地后产生的是 pass/fail，不是 silent，所以不该进甲乙任何一张表。

        `pre_inside_country`（silent）仍留在 `CLASS_B_CODES` 里，一个字节没动：
        它是「画像不采集现居地」的诚实码，本单没有把它从债里摘掉——摘掉的
        前提是画像真的采集了，而那是前端的事，引擎不能替它宣布已还清。
        """
        self.assertIn("pre_inside_country", mr.CLASS_B_CODES)
        self.assertNotIn("pre_inside_country_ok", mr.CLASS_B_CODES)
        self.assertNotIn("pre_inside_country_no", mr.CLASS_B_CODES)
        self.assertNotIn("pre_inside_country_ok", mr.BY_DESIGN_CODES)
        self.assertNotIn("pre_inside_country_no", mr.BY_DESIGN_CODES)

    # —— ⑦ 三画像的 location 取值本身被钉住（它决定翻转方向）——
    def test_sample_profiles_pin_current_location(self):
        """三画像的现居地取值必须显式写在夹具里，且与 persona 一致。

        这不是「随便填一个就行」的字段：它直接决定九个项目行的翻转方向。
        A/B 是大陆、C 是台湾（都是 prospective applicant，人还在护照所属地），
        写成 AU/GB 会让「须在该国境内」那一批全部翻成 pass——数值上更好看，
        但那是把夹具调成结论，不是把引擎修对。
        """
        self.assertEqual(mr.SAMPLES["A"]["current_location"], "CN")
        self.assertEqual(mr.SAMPLES["B"]["current_location"], "CN")
        self.assertEqual(mr.SAMPLES["C"]["current_location"], "TW")
        # 现居地与护照所属地在这批画像上一致（persona 是准申请人）
        for name, cc in (("A", "CN"), ("B", "CN"), ("C", "TW")):
            self.assertEqual(mr.current_location_of(mr.SAMPLES[name]), cc, name)


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
