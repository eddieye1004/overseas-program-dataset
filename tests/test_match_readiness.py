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
import re
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
        | P1d 后 | 13/41 = 0.3171 | 接入 current_location，在地条判出 fail（cannot），3 项离开 unknown |
        | P3 后 | 12/41 = 0.2927 | 教育路径化，`at-rwr-card-vhq` 判出 cannot |
        | **P1e 后** | **10/41 = 0.2439** | `outside` + `home_residence` 接地，2 项判成 can |
        | **P4 后** | **9/41 = 0.2195** | Sponsor 前置接线，`us-j1-research-scholar` 的 silent 被 gap 压过 |

        上限从 16 回调到 13 是**记录事实**，不是放宽标准：那 3 项从 silent 变
        cannot 是因为引擎终于能判（现居地有了），不是把它们藏起来——它们仍在
        报告里逐条可见，只是状态从「不可判」变成「不能申」。全口径从来不是停工
        闸门，闸门在 `test_stop_line_binds_class_b_only`，它的 1/3 一个数字没改。

        P1e 的 −2 同理：C 画像 12 → 10，离开 unknown 的是 `jp-working-holiday`
        与 `nz-china-whv`（现居 TW == 台湾护照所属地 TW → 常驻要求判 pass，
        其余维本就全 pass → can）。不是把它们藏起来，是把它们**判对了**：
        这两个项目的目标人群正是「人在护照所属地的协议国国民」。逐条归因见
        `test_class_b_members_are_pinned` 与回执 §4。
        """
        rep = mr.audit()
        # 注意：unknown_ratio 是 4 位小数的舍入值，直接与分式比会因舍入假红。
        # 所以钉「项目条数」+「比率等于该条数 / 总数」，两者合起来才是断言本意。
        #
        # 版本轨迹（均为实测）：
        #   P1b-2 前 14 → P1b-2 后 13 → P1c 后 16 → P1d 后 13 → P3 后 12
        #   **P1e 后 10**（10/41 = 0.2439）→ **P4 后 9**（9/41 = 0.2195）
        #
        # P4 的 −1 是 `us-j1-research-scholar`：它唯一的 silent 是甲类
        # `edu_by_sponsor`，P4 接上岗位前置后多出一条 gap，按 fail>gap>silent
        # 整体从 unknown 变 gap。**下限只会更紧**（≤9 而不是「等于 9」仍然成立），
        # 所以这条断言不需要改成等式——全口径是「只许不增」的尺子。
        self.assertLessEqual(max(v["unknown"] for v in rep["samples"].values()), 9)
        self.assertEqual(
            rep["max_unknown_ratio"],
            round(9 / rep["total"], 4),
            "全口径上限被突破了：这是「甲类变多也不许藏」的那把尺子",
        )
        self.assertLessEqual(rep["max_unknown_ratio"], 9 / 41 + 1e-4)
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
        （须常驻护照所属地区），P1d 单按派单 §1.2 只接 `pre_inside_country`，
        因此当时仍留在乙类——见 P1d 回执 §8「遗留待裁」。

        **P3 清偿：C 11 → 10，移除的正是 `at-rwr-card-vhq`，一项不多一项不少**：

        | 项目 | 改前 | 改后 | 原因 |
        |---|---|---|---|
        | `at-rwr-card-vhq` | unknown / 乙 | cannot / `edu_low` | 画像 A 学历层级不足，判 fail；原先是 silent 兜住 |

        这一项从乙类离开不是「洗白」而是**判出来了**：它的「四年制」时长门槛
        与「学士/硕士/博士」层级门槛现在都能读，A 画像（本科在读）层级不够，
        于是得到确定的 cannot。B/C 那边判 pass（48 个月 ≥ 四年制），也不再
        挂在乙类里。

        **P1e 清偿：C 10 → 8，移除的正是 `jp-working-holiday` 与 `nz-china-whv`，
        一项不多一项不少**（本单同时接 `pre_outside_country`，但 `au-407-training`
        仍因语言维 `lang_no_score` 留在乙类，所以 outside 接地**没有**让任何项目
        离开 C 的乙类清单——这一点必须写明，否则看不出两码各自的效果）：

        | 项目 | 改前 | 改后 | 驱动 | 说明 |
        |---|---|---|---|---|
        | `jp-working-holiday` | unknown / 乙 | can | `pre_home_residence` → `_ok` | C 现居 TW == 台湾护照所属地 TW，常驻要求判 pass；其余维全 pass |
        | `nz-china-whv` | unknown / 乙 | can | `pre_home_residence` → `_ok` | 同上（该项目 note 明写「须常驻其护照所属地区」） |

        另有一条**状态不变但前置维变了**，不计入乙类增减但必须留痕：
        `au-407-training`（A/C）与 `se-look-for-work`（A/B/C）的 `pre_outside_country`
        从 silent 变 `pre_outside_country_ok`/pass。它们整体没动，是因为别的维
        本来就 fail/gap/silent 挡着（`au-407` 是 `lang_no_score`，`se` 是 `edu_low`
        + `funds_short`）——这说明单接 outside 不会凭空洗白任何项目，方向是对的。

        没有一条「无因消失」：改前 10 条，改后 8 条，差集恰好是上表两项。
        """
        rep = mr.audit()
        self.assertEqual(
            rep["samples"]["C"]["class_b_ids"],
            [
                "au-407-training",
                "ca-pgwp",
                "de-chancenkarte",
                "dk-working-holiday",
                "mt-nomad-residence",
                "nl-orientation-year",
                "nz-post-study-work",
                "uk-hpi-visa",
            ],
        )
        self.assertEqual(
            rep["samples"]["C"]["by_design_ids"],
            [
                "global-aiesec-global-talent",
            ],
        )

        # 甲类与画像无关：三个 code 都不读画像值，换个人不该让它们消失。
        # P1b-2 记录：接线后 A/B/C 的甲类从 3 降到 2（B、C）——因为
        # `us-j1-summer-work-travel` 在 B/C 上被新接的在读要求判成「不能申」
        # （已毕业 ≠ 在读），不再是 unknown，自然也就没有甲类。这不是甲类口径
        # 改动，是这个项目**本来就该给出的结论**终于判出来了；甲类白名单本身
        # 一个 code 都没动（test_every_silent_code_is_classified 仍钉死两个）。
        #
        # P4 记录：甲类 2/2/2 → 1/1/1（三个画像一致），离开的是
        # `us-j1-research-scholar`——它原先唯一的 silent 是 `edu_by_sponsor`
        # （甲类，由 Sponsor 判断学历层级），三画像因此都判 unknown。P4 接上
        # 岗位/Sponsor 前置后，它额外产出一条 `pre_job_placement`/**gap**，
        # 按「fail > gap > silent」的优先级整体从 unknown 变成 gap。
        # 教育维那条 `edu_by_sponsor`/silent **仍在**（下一行单独钉住），
        # 甲类白名单一个 code 没动，变的只是「同一项目里 gap 压过 silent」。
        a = mr.audit()["samples"]
        self.assertEqual(a["A"]["unknown_by_design"], 1, "A")
        self.assertEqual(a["B"]["unknown_by_design"], 1, "B")
        self.assertEqual(a["C"]["unknown_by_design"], 1, "C")
        # 上面那句「教育维仍在」必须由实测支撑，否则这条注释会变成空话
        edu = {
            d["code"]
            for d in mr.judge(self.docs["us-j1-research-scholar"], mr.SAMPLES["C"])[1]
            if d["dim"] == "education"
        }
        self.assertEqual(edu, {"edu_by_sponsor"}, "研究学者的甲类教育维被 P4 顺手删了")

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
    def test_4_2_four_year_requirement_drives_result(self):
        """note 写「不少于四年高等教育，三年制本科不满足」，结构化只有
        `minimum_level: bachelor_completed`。

        **P3 变更（原断言 edu_years_unknown/silent）**：这条要求已经有了字段与
        画像读点 —— 它是一条时长门槛，不是「学制年数未知」。原断言钉的是旧引擎
        的表达力上限（读到数字也只能判不可判），不是官方要求本身。

        现在两侧都钉住：
          · 时长够（B：48 个月 = 四年制）→ pass；
          · 时长不够（同一个人改成 36 个月 = 三年制）→ fail / `edu_duration_short`；
          · 层级不够（A：在读）→ 仍 fail，且理由落在层级而不是时长。
        """
        self.assertEqual(mr.edu_years_required(self.docs["at-rwr-card-vhq"]), 4)
        d = self.dim("at-rwr-card-vhq", "B", "education")
        self.assertEqual(d["code"], "edu_ok", d)

        # 三年制：同一个人、只改 study_months，结论必须翻成 fail
        pr = dict(mr.SAMPLES["B"])
        pr["study_months"] = 36
        state, dims = mr.judge(self.docs["at-rwr-card-vhq"], pr)
        edu = [x for x in dims if x["dim"] == "education"][0]
        self.assertEqual(state, "cannot")
        self.assertEqual(edu["code"], "edu_duration_short", edu)
        self.assertEqual(edu["kind"], "fail", edu)

        # A（本科在读）因层级不足判 fail，不被时长分支吞掉
        a = self.dim("at-rwr-card-vhq", "A", "education")
        self.assertEqual(a["code"], "edu_low", a)
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
        """全库顺查：只要项目有 required 的**任一**前置族，三画像下都不许「静默」判能申。

        这一条比单点断言更狠：它不依赖某个项目当前的具体结论，只守
        「有前置要求就不能说谁都能申」。落空（读不懂）也算违规 ——
        读不懂必须落 unclassified/silent，不能当作「没有要求」。

        P1c 改口径：影响面从「17 个项目有 residency_requirement」变成
        「17 个项目有前置族中的至少一族」。**条数仍是 17**，但构成变了：
        9 个项目只剩在地族、6 个只剩身份族、2 个（de-20 / us-f1-opt）两族都有。
        所以这里按「任一前置族」取，而不是给两个 type 各写一遍（那会把
        de-20 / us-f1-opt 数两遍，17 变 19）。

        **P1e 变更（重要，不是放宽）**：原断言是 `state != "can"`，在接地之前
        它等价于「前置要求永远是 silent/gap」，因为前置维根本判不出 pass。
        P1e 把 `outside` 与 `home_residence` 接上 `current_location` 之后，
        「合格的人真的合格」第一次可以表达出来——`nz-china-whv` / `jp-working-holiday`
        对「现居 == 护照所属地」的画像正是官方要的那批人，判 can 是**结论**，
        不是漏判。若继续钉 `state != "can"`，这条断言就变成「不许判对」，
        而它原本要防的是**前置要求被静默丢掉**。

        所以判据收窄到本意：**能申的项目，其前置族读出的每一类都必须有对应维结论，
        且都是 pass/na**。三态优先级本来就保证 fail/gap/silent 不可能整体判 can，
        所以真正需要单独守的只剩「要求整条被吞掉」——即 `precondition_kinds()`
        读出了某一类，dims 里却没有它对应的结论。
        """
        PRE_TYPES = (mr.REQ_TYPE_RESIDENCY, mr.REQ_TYPE_LOCATION)
        # kind → 它该在 dims 里留下的 code 前缀。写死这张表是刻意的：将来新增
        # 一个 kind 而忘了接线时，这里会先红，而不是让「有要求却无结论」静默通过。
        KIND_CODES = {
            "local_status": ("pre_local_status",),
            "inside": ("pre_inside_country", "pre_inside_country_ok", "pre_inside_country_no"),
            "outside": ("pre_outside_country", "pre_outside_country_ok", "pre_outside_country_no"),
            "home_residence": (
                "pre_home_residence", "pre_home_residence_ok", "pre_home_residence_no",
            ),
            "citizenship": ("pre_citizenship_basis",),
            "document": ("pre_document_basis",),
            "unclassified": ("pre_unclassified",),
        }
        checked = 0
        cans = []
        for pid, doc in self.docs.items():
            reqs = [
                r
                for r in ((doc.get("eligibility") or {}).get("other_requirements") or [])
                if r.get("required") is True and r.get("type") in PRE_TYPES
            ]
            if not reqs:
                continue
            checked += 1
            kinds = mr.precondition_kinds(doc)
            self.assertTrue(kinds, f"{pid} 有前置要求但没读出任何类别")
            self.assertTrue(
                set(kinds) <= set(KIND_CODES), f"{pid} 出现未登记的类别：{kinds}"
            )
            for sample in ("A", "B", "C"):
                state, dims = mr.judge(doc, mr.SAMPLES[sample])
                codes = {d["code"] for d in dims if d["dim"] == "precondition"}
                # 每一类都必须留下对应结论（不许被吞）
                for kind in kinds:
                    self.assertTrue(
                        codes & set(KIND_CODES[kind]),
                        f"{pid}/{sample} 读出了 {kind} 这一类，但前置维没有对应结论：{codes}",
                    )
                if state != "can":
                    continue
                cans.append(f"{pid}/{sample}")
                # 判 can 时，身份/在地这一族的结论必须是 pass 或 na（fail/gap/silent
                # 由三态优先级保证不会到这里，这里显式再钉一次，防将来改优先级）
                gate = {c for k in kinds for c in KIND_CODES[k]}
                for d in dims:
                    if d["dim"] == "precondition" and d["code"] in gate:
                        self.assertIn(
                            d["kind"], ("pass", "na"),
                            f"{pid}/{sample} 判了能申，但前置维是 {d['kind']}（{d['code']}）",
                        )
        self.assertEqual(checked, 17, f"带 required 前置要求的项目数变了：{checked}")
        # 能申的那几条必须**恰是**接地后由 pass 驱动的，登记成清单防止无声扩张
        self.assertEqual(
            sorted(cans),
            ["jp-working-holiday/C", "nz-china-whv/A", "nz-china-whv/C"],
            "带前置要求却判能申的集合变了：每一条都要人工确认为「要求确实满足」",
        )

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
        冲突时必须按 note 降级，不许拿结构化字段判 fail。

        **P4 变更**：整体状态从 `unknown` 变成 `gap`，因为同一项目里多出一条
        `pre_job_placement`（Sponsor 前置）——按 fail>gap>silent 它压过教育维
        那条 silent。**本条守的东西一个字节没改**：教育维仍是
        `edu_by_sponsor`/silent、仍不是 fail/cannot。所以断言从「整体等于
        unknown」改成「整体不是 cannot，且教育维仍是那条 silent」——继续钉
        `unknown` 就成了「钉住旧结论」而不是「钉住方向（不许替官方拒绝）」。
        """
        self.assertEqual(
            (self.docs["us-j1-research-scholar"]["eligibility"]["education"]["minimum_level"]),
            "master",
        )
        d = self.dim("us-j1-research-scholar", "C", "education")
        self.assertEqual(d["code"], "edu_by_sponsor", d)
        self.assertEqual(d["kind"], "silent", d)
        state = mr.judge(self.docs["us-j1-research-scholar"], mr.SAMPLES["C"])[0]
        self.assertNotEqual(state, "cannot")
        self.assertEqual(state, "gap")

    def test_4_5_structural_note_conflict_scan_is_registered(self):
        """全库顺查「结构化字段与 note 冲突」：登记当前命中集合。

        新增命中时这条会红 —— 每一例都要人工确认是 note 说话还是结构说话，
        不许让新的冲突随默认分支判过去。

        **P3 变更**：判据从 `EDU_RANK.get(...)` 改成 `edu_paths()`——「结构化字段
        是否真的写了一个层级」现在问的是路径里有没有非 any 的 level，而不是总序
        里取到的值是不是 0。总序已退出判定面（见回执 §2 的 grep 读点清单），测试
        若继续引用它，就成了「引擎不用、测试还在用」的第二份口径。
        """
        hits = {
            pid
            for pid, d in self.docs.items()
            if any(
                (p.get("level") or "any") != "any" for p in mr.edu_paths(d)
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
        """两条探测器各自的作用域，必须精确钉住——放宽一侧就会把别的项目误降级。

        `au-407-training` 的「培训项目须属于三类之一」是**培训类型**不是申请人
        身份，这正是收窄锚点到「身份」二字的原因——放宽后它会假阳。

        **P4 变更（命中集合 1 → 5）**：`JOB_PLACEMENT` 从「只认营地辅导员那一句
        英文直译」扩到 J-1 四种官方写法。命中集合变成 J-1 五兄弟里除
        `us-f1-opt`（不是 J-1）之外的四个 + 营地本体，且**每一条都能指出原句**：

        | 项目 | 触发词 | 原句出处 |
        |---|---|---|
        | `us-j1-camp-counselor` | 预先落实 / pre-arranged | documents「预先落实的营地岗位」 |
        | `us-j1-intern` | 三方签字 / 签署的 DS-7002 | internship_contract + documents[2] |
        | `us-j1-trainee` | 三方签字 / 签署的 DS-7002 | internship_contract + documents[2] |
        | `us-j1-summer-work-travel` | 通过雇主面试 | documents[6] Job Offer |
        | `us-j1-research-scholar` | 出具 DS-2019 / Sponsorship | government_support_letter |

        同时**反向钉住不许扩散**：`EMPLOYER_OFFER` 仍只命中 `no-skilled-worker`
        （互斥断言不变），新加坡 EP / S Pass 的「雇主 offer」不许被连带拉进来
        （它们没有「三方签字 / DS-7002 / Sponsorship」这些词，属另一条口径）。
        """
        self.assertEqual(
            [p for p, d in self.docs.items() if mr.job_placement_required(d)],
            [
                "us-j1-camp-counselor",
                "us-j1-intern",
                "us-j1-research-scholar",
                "us-j1-summer-work-travel",
                "us-j1-trainee",
            ],
        )
        self.assertEqual(
            [p for p, d in self.docs.items() if mr.participant_category_required(d)],
            ["us-j1-camp-counselor"],
        )
        # 互斥关系不变：两条探测器命中集合不许重叠
        self.assertEqual(
            {p for p, d in self.docs.items() if mr.job_placement_required(d)}
            & {p for p, d in self.docs.items() if mr.employer_offer_required(d)},
            set(),
        )
        # 反过来也不许把「另一条口径」的项目拉进来
        for pid in ("sg-employment-pass", "sg-s-pass", "no-skilled-worker"):
            self.assertFalse(mr.job_placement_required(self.docs[pid]), pid)
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
        )
        # 点数探测器只是被认定分支引用；单有积分制的项目不受它影响
        #
        # P3 变更（原断言 edu_years_unknown）：`at-rwr-card-vhq` 的原文是
        # 「须完成**不少于四年**的高等教育课程，三年制本科不满足」——这是一条
        # **时长门槛**，不是「学制年数未知」。旧代码用 EDU_YEARS_STRICT 读它，
        # 读到数字后只能判 silent（因为画像不采集学制），于是这条真门槛永远
        # 停在「不可判」。P3 给了画像 `study_months`（B=48 个月=4 年），这条
        # 终于可以判出来了：B 判 pass，A（在读且层级不够）仍判 fail。
        # **不是放宽**：把 B 的 study_months 调成 36（三年制）会翻成
        # `edu_duration_short`（见 test_at_rwr_duration_predicate_drives_result）。
        self.assertEqual(self.dim("at-rwr-card-vhq", "B", "education")["code"], "edu_ok")

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


class P4SponsorPrecondition(unittest.TestCase):
    """P4 Sponsor 前置包：词表扩围 + type 归位 + need 文案四表述 + 注释门禁。

    守的是三件**方向性**的事，每件都配一正一反：

    ① **词表只扩围、不改语义**（§1）：四种 J-1 官方写法必须命中并判 gap；
       同时四条**不许命中**的反例各钉一次（新加坡 offer / 挪威 offer /
       德国实习合同 / 全库其余项目），否则「扩围」会退化成「凡有岗位二字就报」。
    ② **type 归位必须按语义分型、不按 type 名一刀切**（§2）：
       `government_support_letter` 六个成员里只有 sponsorship 型进岗位族；
       其余五型若被接进来，会造出「德国（required=false）」这种假缺口。
    ③ **need 文案项目化**（§3）：四种表述各一条，且**不许串台**——
       研究学者的 need 里不许出现「营地」，营地的 need 里不许出现「DS-2019」。
       这一条是 Muse 裁决 2 的核心：修一处漏网、不许引入一处错文案。
    """

    @classmethod
    def setUpClass(cls):
        cls.docs = {d["program"]["id"]: d for d in mr.load_programs()}

    def pre(self, pid, sample="B", **override):
        pr = dict(mr.SAMPLES[sample])
        pr.update(override)
        _, dims = mr.judge(self.docs[pid], pr)
        return [d for d in dims if d["dim"] == "precondition"]

    def jp_dim(self, pid, sample):
        return next((d for d in self.pre(pid, sample)
                     if d["code"] == "pre_job_placement"), None)

    # ---- ① 词表扩围：四种官方写法各命中，并判 gap ----
    def test_four_sponsor_flavors_all_judged_gap(self):
        """J-1 四种「岗位/Sponsor 前置」写法都必须判 `pre_job_placement`/gap。

        四种写法来自四份不同的官方条文（营地 22 CFR 62.30(h)(3)、研究机构
        DS-2019、SWT 暑期岗位+雇主面试、intern/trainee 的 DS-7002 三方签字）。
        改前只有第一种命中，后三种全 MISS——而引擎注释逐字写着
        「us-j1-intern / us-j1-trainee 两类都判 gap」（本类最后一条门禁用例
        就是这个注释的机械证明）。
        """
        want = {
            "us-j1-camp-counselor": "camp",
            "us-j1-research-scholar": "sponsor_ds2019",
            "us-j1-summer-work-travel": "summer_job",
            "us-j1-intern": "ds7002",
            "us-j1-trainee": "ds7002",
        }
        for pid, flavor in want.items():
            self.assertTrue(mr.job_placement_required(self.docs[pid]), pid)
            self.assertEqual(mr.job_placement_flavor(self.docs[pid]), flavor, pid)
        # 三态：每个项目至少有一个画像从 can/unknown 变 gap（不许只出维不改结论）
        for pid in want:
            states = {mr.judge(self.docs[pid], mr.SAMPLES[s])[0] for s in ("A", "B", "C")}
            self.assertNotIn("can", states, f"{pid} 仍被判能申：{states}")

    def test_placement_regex_does_not_swallow_neighbour_programs(self):
        """反例：四条「看起来像 job placement、其实不是这一族」必须保持不命中。

        - `no-skilled-worker`：雇主担保的具体聘用 → 归 `EMPLOYER_OFFER`（互斥）
        - `sg-employment-pass` / `sg-s-pass`：只要「有雇主 offer」，无文件链
        - `de-16e-internship`：只有一份 Praktikumsvertrag，无 DS-7002 / DS-2019
        - `global-aiesec-global-talent` / `global-iaeste`：岗位「由组织对接确认」，
          没有「预先落实 / 三方签字 / Sponsorship」任一措辞

        这几条是扩词表最容易踩坏的边界：一旦把「岗位」当裸词收进来，六项会同时
        假阳，且方向都是把能申的人判成 gap。
        """
        for pid in ("no-skilled-worker", "sg-employment-pass", "sg-s-pass",
                    "de-16e-internship", "global-aiesec-global-talent",
                    "global-iaeste"):
            self.assertFalse(mr.job_placement_required(self.docs[pid]), pid)
            self.assertIsNone(mr.job_placement_flavor(self.docs[pid]), pid)
            self.assertNotIn(
                "pre_job_placement",
                {d["code"] for d in self.pre(pid, "B")},
                f"{pid} 被扩词表误伤",
            )

    # ---- ② type 归位：语义分型，不按 type 名一刀切 ----
    def test_government_support_letter_is_typed_by_semantics(self):
        """`government_support_letter` 的六个成员必须各归各型，只有 sponsorship
        型进岗位族。

        这条 type 名本身不表意：同样是 `government_support_letter`，包里装的是
        政府支持信（au-462）、官方求职登记（it-ricerca）、学历认证（uk-hpi）、
        院校推荐（us-f1-opt）、Sponsor 的 DS-2019（research-scholar），以及一条
        `required=false` 的德国「预批」（de-16e）。**按 type 名一刀切接线，会把
        四种无关语义读成同一条缺口**——这正是 P1a 的结论（31 条里 27 条按名字接
        会判错）。
        """
        want = {
            "au-462-work-holiday": ("government_letter", True),
            "it-ricerca-lavoro": ("official_registration", True),
            "uk-hpi-visa": ("credential_check", True),
            "us-f1-opt": ("institutional_recommendation", True),
            "us-j1-research-scholar": ("sponsorship", True),
            "de-16e-internship": ("unclassified", False),
        }
        got = {pid: mr.government_support_letter_kind(doc)
               for pid, doc in self.docs.items()
               if mr.government_support_letter_kind(doc)}
        self.assertEqual(got, want)
        # 只有 sponsorship 型进判定面：其余四型一个 pre_job_placement 都不许出
        for pid, (kind, _req) in want.items():
            codes = {d["code"] for d in self.pre(pid, "B")}
            if kind == "sponsorship":
                self.assertIn("pre_job_placement", codes, pid)
            else:
                self.assertNotIn("pre_job_placement", codes, pid)
        # required=false 的德国预批不许被当成硬前提（这正是「按 type 名接线」的假阳）
        self.assertFalse(mr.job_placement_required(self.docs["de-16e-internship"]))

    def test_gsl_kind_is_carried_into_flags(self):
        """分型结果必须进前端契约（flags），否则前端只能重新读中文猜——
        那正是 M1 要消灭的东西。"""
        f = mr.flags_of(self.docs["us-j1-research-scholar"])["precondition"]
        self.assertEqual(f["government_support_letter"],
                         {"kind": "sponsorship", "required": True})
        # 没有该 type 的项目：null，不是空 dict
        f2 = mr.flags_of(self.docs["us-f1-opt"])["precondition"]
        self.assertEqual(f2["government_support_letter"]["kind"],
                         "institutional_recommendation")
        f3 = mr.flags_of(self.docs["jp-working-holiday"])["precondition"]
        self.assertIsNone(f3["government_support_letter"])

    def test_gsl_kind_anchors_are_not_bare_words(self):
        """分型锚点不许用裸词——这是「一条 note 装两个事实」的防误分闸。

        `official_registration` 早先收裸词「登记」、`credential_check` 收「认证」、
        `government_letter` 收「政府」：三条都会把**别族**的句子误分进来
        （「材料须登记」「认证翻译」「政府网站」）。误分的后果不是判错（这一型
        不进判定面），是审计表把一条别族要求记到本族名下——那正是 batch9b
        裁决 1 反复强调的「按字段名一刀切」的错误形态。

        反例就是构造出来的三条句子：它们都不该归入任何具体型。
        """
        from copy import deepcopy

        base = self.docs["us-j1-research-scholar"]
        for sentence in ("材料须在系统内登记后递交",
                         "非英文材料须附认证翻译",
                         "政府网站在线填报"):
            doc = deepcopy(base)
            for r in doc["eligibility"]["other_requirements"]:
                if r.get("type") == mr.REQ_TYPE_GSL:
                    r["note"] = sentence
            self.assertEqual(
                mr.government_support_letter_kind(doc),
                ("unclassified", True),
                f"「{sentence}」被误分到具体型",
            )

    # ---- ③ need 文案项目化：四种表述，且不许串台 ----
    def test_job_placement_need_is_project_specific(self):
        """四种表述各一条 need，且**不许串台**（Muse 2026-11-14 裁决 2）。

        改前 need 硬编码成营地那条法规原文，研究学者/学徒页会看到一句讲营地的
        话——「修了一处漏网、引入一处错文案」。batch2 §4.2④、batch4 §219/§316、
        batch9b §1.2② 已就同一处文案先后记过三次，本包是第四次、也是必须一次
        修完的一次（同时支持四种）。
        """
        needs = {}
        for pid in ("us-j1-camp-counselor", "us-j1-research-scholar",
                    "us-j1-summer-work-travel", "us-j1-intern"):
            d = self.jp_dim(pid, "B")
            self.assertIsNotNone(d, pid)
            needs[pid] = d["need"]
            self.assertTrue(d["need"].strip(), pid)
        # 四条互不相同：任何一个共用就说明文案没项目化
        self.assertEqual(len(set(needs.values())), 4, needs)
        # 研究学者的 need 讲 DS-2019 与接收机构，不许出现「营地」
        self.assertIn("DS-2019", needs["us-j1-research-scholar"])
        self.assertIn("接收机构", needs["us-j1-research-scholar"])
        self.assertNotIn("营地", needs["us-j1-research-scholar"])
        # 营地的 need 反过来不许出现 DS-2019（那是研究机构那条链条）
        self.assertIn("营地", needs["us-j1-camp-counselor"])
        self.assertNotIn("DS-2019", needs["us-j1-camp-counselor"])
        # SWT 的 need 必须含「雇主面试」（原文的唯一取得路径）
        self.assertIn("雇主面试", needs["us-j1-summer-work-travel"])
        # intern 的 need 必须含 DS-7002 与三方签字
        self.assertIn("DS-7002", needs["us-j1-intern"])
        self.assertIn("三方签字", needs["us-j1-intern"])
        # trainee 与 intern 同一条文件链，文案必须一致（同族不许漂）
        self.assertEqual(self.jp_dim("us-j1-trainee", "B")["need"], needs["us-j1-intern"])

    def test_flags_carry_the_flavor(self):
        """flavor 必须进 flags，否则前端只能自己再判一遍中文（两份口径）。"""
        for pid, want in (("us-j1-camp-counselor", "camp"),
                          ("us-j1-research-scholar", "sponsor_ds2019"),
                          ("us-j1-summer-work-travel", "summer_job"),
                          ("us-j1-trainee", "ds7002")):
            f = mr.flags_of(self.docs[pid])["precondition"]
            self.assertEqual(f["job_placement_flavor"], want, pid)
        # 没有岗位前置的项目：null
        self.assertIsNone(
            mr.flags_of(self.docs["no-skilled-worker"])["precondition"]["job_placement_flavor"]
        )

    def test_frontend_need_table_matches_engine(self):
        """前后端 need 文案表必须**逐字节**相同（P4 §3「不许只改一侧」）。

        为什么单独钉一张表而不是让 smoke-test 比：need 是散文，按 M1 的口径不进
        `match-flags.json`（进了就等于把中文 note 塞回索引，前端会重新长出「读中文
        猜结论」的逻辑）。两侧各持一份同键表，靠这条测试保证不漂。

        串台的后果是具体的：只改 Python 一边，网页上的研究学者仍显示营地文案；
        只改前端一边，两边说法不同而没有任何测试会红。
        """
        src = io.open(
            os.path.join(ROOT, "web", "src", "lib", "verdict.ts"), encoding="utf-8"
        ).read()
        m = re.search(r"export const JOB_PLACEMENT_NEED[^{]*\{(.*?)\n\};", src, re.S)
        self.assertIsNotNone(m, "verdict.ts 里找不到 JOB_PLACEMENT_NEED")
        body = m.group(1)
        ts: dict[str, str] = {}
        for km in re.finditer(r"(\w+):\s*\n?\s*'((?:[^'\\]|\\.)*)'", body):
            ts[km.group(1)] = km.group(2).replace("\\'", "'")
        self.assertEqual(ts, mr.JOB_PLACEMENT_NEED, "前后端 need 文案表已漂移")
        # 版本号也必须两侧一致（改判定口径忘改版本号是最常见的一处）
        self.assertIn(
            "export const RULES_VERSION = %d;" % mr.RULES_VERSION, src,
            "verdict.ts 的 RULES_VERSION 未跟上 Python",
        )

    def test_every_hit_has_a_registered_flavor(self):
        """全库顺查：凡命中岗位前置的项目，必须落在四种表述之一。

        `None` 会退回兜底文案（营地那条），那是「修一处漏网、引入一处错文案」
        的同一个坑。这条闸保证「新增一个命中项目时，要么写进四种表述，
        要么这里当场红」。
        """
        hits = {pid: mr.job_placement_flavor(d)
                for pid, d in self.docs.items() if mr.job_placement_required(d)}
        self.assertNotIn(None, hits.values(), hits)
        self.assertEqual(
            set(hits.values()),
            {"camp", "sponsor_ds2019", "summer_job", "ds7002"},
            "四种表述必须都有真实用例，否则表里某一行是死代码",
        )

    # ---- ④ 注释-实测一致性门禁 ----
    def test_comment_claims_match_reality(self):
        """**注释-实测一致性门禁**（batch9a 裁决 4 / batch10 §4）。

        规则：引擎注释块里若用**规范性措辞**（应判 / 都判 / 必判）点名某个项目
        的结论，`tests/` 必须能证明实测一致；否则这条注释就是空头承诺。

        首个用例正是它要防的那一处：`match_readiness.py` 的岗位前置注释块逐字
        写着「us-j1-intern / us-j1-trainee ... **两类都判 gap**」，而 P4 之前
        词表窄到两者都判 `can`——注释即承诺、实测零输出，且没有任何测试会发现。

        实现分两步，两步都必须能红：
          A. 机械扫描：注释块 → (项目, 状态词) 断言清单，逐条跑 judge 验真；
          B. 清单变化即红：新写一句「X 应判 gap」而不改这里，测试提醒登记。
        """
        import re

        engine = io.open(SCRIPT, encoding="utf-8").read().split("\n")
        pids = sorted(self.docs)
        # 规范性措辞：只认「应判 / 都判 / 必判」。不认「判 A 而不是 B」——
        # 那是设计理由（在解释为什么不做某件事），不是对实测的断言。
        #
        # 注意两点，都是被变异测试逼出来的：
        #   ① 长词在前（cannot 先于 can），否则「应判 cannot」会被读成「应判 can」；
        #   ② 匹配前把注释块的换行**去掉**再扫——注释是散文、按屏宽折行，
        #      「两类都应判 / can」这种跨行写法是最自然的一笔，若按行匹配，
        #      一道换行就能让门禁失效（首版正是这样被 M4 变异绕过）。
        claim_rx = re.compile(
            r"(?:应判|都判|必判)[^。；]{0,12}?(cannot|unknown|silent|fail|pass|gap|can|na)"
        )

        blocks, cur = [], []
        for i, line in enumerate(engine, 1):
            if line.strip().startswith("#"):
                cur.append((i, re.sub(r"^\s*#\s?", "", line)))
            else:
                if cur:
                    blocks.append(cur)
                cur = []
        if cur:
            blocks.append(cur)

        claims = {}
        for blk in blocks:
            text = "".join(t for _, t in blk)
            got_pids = [p for p in pids if p in text]
            if not got_pids:
                continue
            for m in claim_rx.finditer(text):
                for pid in got_pids:
                    claims.setdefault((pid, m.group(1)), blk[0][0])

        # B. 清单钉死：当前只有这一个注释块（P4 立下的首用例）。
        #    新增一行注释断言 → 这里红 → 必须补一条实测断言后再登记到本清单。
        #
        #    口径说明（为什么是三条而不是两条）：门禁按**注释块**取项目，
        #    同一块里点了名的项目都算被断言——这是**故意过近似**。过近似的代价
        #    是「多要求一条真断言」，漏抓的代价是「注释继续空转」，两者不对称，
        #    所以宁可宽。营地那条本来就判 gap，多这一条不产生假阳。
        self.assertEqual(
            sorted(claims),
            [("us-j1-camp-counselor", "gap"),
             ("us-j1-intern", "gap"),
             ("us-j1-trainee", "gap")],
            "注释里出现了新的「项目 + 应判 X」断言：请为它补一条实测断言，"
            "再把 (项目, X) 登记到本清单（注释-实测一致性门禁）",
        )

        # A. 逐条验真：注释说 gap，实测就必须真有 gap 维（不是只判 can）
        for (pid, word), line_no in claims.items():
            _, dims = mr.judge(self.docs[pid], mr.SAMPLES["B"])
            kinds = {d["kind"] for d in dims}
            self.assertIn(
                word, kinds,
                f"match_readiness.py:{line_no} 的注释说 {pid} 应判 {word}，"
                f"实测 kinds={sorted(kinds)}（注释-实测不一致）",
            )
        # 首用例的两条必须真的被 pre_job_placement 驱动（不是被别的维凑出来的 gap）
        for pid in ("us-j1-intern", "us-j1-trainee"):
            codes = {d["code"] for d in self.pre(pid, "B")}
            self.assertIn("pre_job_placement", codes, pid)

    def test_camp_counselor_placement_still_gap_after_widening(self):
        """扩围不许把最早那条弄坏：营地仍判 gap，且 need 仍是营地文案。

        历史用例 `test_camp_counselor_job_placement_is_not_silently_passed` 钉的是
        同一条；这里额外钉「扩围后 flavor 仍归 camp」——因为 `camp` 在优先级表里
        排第一，若有人把它挪到 `ds7002` 之后，营地项目的文案会被 DS-7002 抢走，
        而它的原文里根本没有 DS-7002。
        """
        self.assertEqual(mr.job_placement_flavor(self.docs["us-j1-camp-counselor"]), "camp")
        for sample in ("A", "B", "C"):
            d = self.jp_dim("us-j1-camp-counselor", sample)
            self.assertEqual(d["kind"], "gap", sample)
            self.assertIn("营地", d["need"], sample)

    # ---- ⑤ 成对：满足 → 出 gap；不满足 → 不出（运行时注入，不落盘） ----
    def test_pair_type_is_load_bearing(self):
        """**成对用例**：`government_support_letter` 这个 type 是不是真读点。

        正：研究学者原样 → 命中，出 `pre_job_placement`/gap（need 讲 DS-2019）。
        反：把那条 type 改成别的（`no_prior_visa`）→ **必须不再命中**。

        反例这一半是关键：只看正例，「type 归位」与「恰好别的字段也命中」
        分不开。反例证明**判据确实落在这个 type 上**——这也是 §2 与「只把 type
        留在枚举里」的区别：留在枚举里的 type 改不改，输出都一样。
        """
        import copy

        doc = self.docs["us-j1-research-scholar"]
        self.assertTrue(mr.job_placement_required(doc))
        self.assertEqual(mr.government_support_letter_kind(doc), ("sponsorship", True))

        flipped = copy.deepcopy(doc)
        for r in flipped["eligibility"]["other_requirements"]:
            if r.get("type") == mr.REQ_TYPE_GSL:
                r["type"] = "no_prior_visa"
        self.assertIsNone(mr.government_support_letter_kind(flipped))
        self.assertFalse(mr.job_placement_required(flipped))
        self.assertNotIn(
            "pre_job_placement",
            {d["code"] for d in mr.judge(flipped, mr.SAMPLES["B"])[1]},
        )

        # 第二个反例：required 改成 false → 也不算硬前提（可选材料不是门槛）
        optional = copy.deepcopy(doc)
        for r in optional["eligibility"]["other_requirements"]:
            if r.get("type") == mr.REQ_TYPE_GSL:
                r["required"] = False
        self.assertFalse(mr.job_placement_required(optional))

    def test_pair_wordlist_is_load_bearing(self):
        """**成对用例**：词表扩围后，四种写法各能单独拉起闸门。

        做法：拿一个**本来不命中**的项目（`de-16e-internship`，只有一份
        Praktikumsvertrag），把四种写法之一注入到它的一条必填材料 note 上，
        必须立刻出 `pre_job_placement`；把 note 清空则不出。

        为什么用注入而不是只跑真实数据：真实数据的四种写法是「恰好命中」，
        分不清「词表宽」还是「这几个项目别处也命中」。注入把变量压到只剩词表。
        """
        import copy

        base = copy.deepcopy(self.docs["de-16e-internship"])
        self.assertFalse(mr.job_placement_required(base))
        samples = {
            "camp": "须先有预先落实的营地岗位",
            "ds7002": "须有三方签字的 DS-7002",
            "summer_job": "须先由 Sponsor 落实暑期岗位，并通过雇主面试",
            "sponsor_ds2019": "须先拿到接收机构的邀请与 Sponsorship",
        }
        for flavor, sentence in samples.items():
            doc = copy.deepcopy(base)
            doc["documents"][0]["note"] = sentence
            self.assertTrue(mr.job_placement_required(doc), flavor)
            self.assertEqual(mr.job_placement_flavor(doc), flavor)
            codes = {d["code"] for d in mr.judge(doc, mr.SAMPLES["B"])[1]}
            self.assertIn("pre_job_placement", codes, flavor)
            need = next(d for d in mr.judge(doc, mr.SAMPLES["B"])[1]
                        if d["code"] == "pre_job_placement")["need"]
            self.assertEqual(need, mr.JOB_PLACEMENT_NEED[flavor], flavor)
        # 反例：清空所有必填 note → 不出（证明上面那半不是「凡 de-16e 都出」）
        blank = copy.deepcopy(base)
        for d in blank["documents"]:
            d["note"] = ""
        self.assertFalse(mr.job_placement_required(blank))


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

        **P1e 变更**：outside 接地后三个画像（现居 CN/CN/TW）都在 AU / SE 之外，
        于是这一条判 `pass / pre_outside_country_ok`，不再恒为 silent。断言从
        「必须出现原码 `pre_outside_country`」改成「必须出现**以它开头**的码，
        且方向必须是 outside 而不是 inside」——否则本条会变成「钉住旧结论」，
        而不是「钉住方向」。
        """
        self.assertEqual(mr.precondition_kinds(self.docs["se-look-for-work"]), ["outside"])
        self.assertEqual(mr.precondition_kinds(self.docs["au-407-training"]), ["outside"])
        for pid in ("se-look-for-work", "au-407-training"):
            codes = {d["code"] for d in self.pre(pid, "B")}
            self.assertTrue(
                any(c.startswith("pre_outside_country") for c in codes), f"{pid}: {codes}"
            )
            self.assertNotIn("pre_inside_country", codes, pid)
            self.assertFalse(
                any(c.startswith("pre_inside_country") for c in codes), f"{pid}: {codes}"
            )

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


class P1eResidenceGrounding(unittest.TestCase):
    """P1e 成对回归：`pre_outside_country` 与 `pre_home_residence` 两项接地。

    方法论与 P3 一致——**成对**。每一项都同时出示正反两面，否则「把整维判死」
    也能让用例全绿：

    | 码 | 正面（满足 → pass） | 反面（不满足 → fail） |
    |---|---|---|
    | `pre_outside_country` | 现居 ≠ 项目国 → 可递 | 现居 == 项目国 → 申请无效 |
    | `pre_home_residence` | 现居 == 护照所属地 → pass | 现居 ≠ 护照所属地 → fail |

    外加两项各自的地基：「任一边缺失必须 silent，绝不默认 pass」。
    **home_residence 的方向陷阱**单独钉一条：它的判据是「现居 == 护照所属地」，
    不是「现居 == 项目国」。JP 项目在 JP，但要求的是台/港籍住在台/港——
    两种读法在字面上都说得通，读反了会把目标人群整个判错。
    """

    @classmethod
    def setUpClass(cls):
        cls.docs = {d["program"]["id"]: d for d in mr.load_programs()}

    def pre(self, pid, **override):
        pr = dict(mr.SAMPLES["B"])
        pr.update(override)
        _, dims = mr.judge(self.docs[pid], pr)
        return [d for d in dims if d["dim"] == "precondition"]

    def code(self, pid, prefix, **override):
        return next(
            (d["code"], d["kind"]) for d in self.pre(pid, **override)
            if d["code"].startswith(prefix)
        )

    # ===================== pre_outside_country =====================

    def test_outside_passes_when_profile_is_elsewhere(self):
        """`se-look-for-work` 要求「递交时人须在瑞典境外」，画像现居 CN → pass。

        这是接地之前**永远不可能出现**的结论。判 pass 的分支若写反（把不等写成
        等），世上没有一个能申的人——所有人都会看到「你已在瑞典」，而事实相反。
        """
        self.assertEqual(mr.precondition_kinds(self.docs["se-look-for-work"]), ["outside"])
        self.assertEqual(
            self.code("se-look-for-work", "pre_outside_country", current_location="CN"),
            ("pre_outside_country_ok", "pass"),
        )
        d = next(x for x in self.pre("se-look-for-work", current_location="CN")
                 if x["code"] == "pre_outside_country_ok")
        # 文案里的两个国别都必须来自数据，不是写死的
        self.assertIn("SE", d["need"])
        self.assertIn("CN", d["have"])

    def test_outside_fails_when_profile_is_in_that_country(self):
        """画像现居 SE、项目在 SE → fail → 整体 cannot。

        官方原文附带一句「即使 ImmiAccount 允许你在境内递交，申请仍然无效」，
        所以这条不能软化成 gap（「先离境」不是补材料，是要先改变所在地）。
        """
        state, dims = mr.judge(self.docs["se-look-for-work"],
                               dict(mr.SAMPLES["C"], current_location="SE"))
        self.assertEqual(state, "cannot")
        d = next(x for x in dims if x["code"].startswith("pre_outside_country"))
        self.assertEqual((d["code"], d["kind"]), ("pre_outside_country_no", "fail"))
        self.assertIn("SE", d["need"])
        self.assertIn("SE", d["have"])

    def test_outside_mirrors_inside_on_the_same_input(self):
        """同一组画像取值下，同一国家的 inside 与 outside 必须给出**相反**的结论。

        只单独测 outside 不够：把 outside 分支写成 inside 的复制粘贴（别处最容易
        犯的错）时，两条会同时判 pass，而单看 outside 那条仍然「对」。

        库里恰好有这样一对同国反向的要求——都在 AU：
        `au-485-graduate` 要「递交时在澳洲**境内**」，
        `au-407-training` 要「递交时在澳洲**境外**」（2026-11-12 起的原文）。
        于是 `current_location=AU` 时前者 pass、后者 fail，`current_location=CN`
        时整体调转。两次都验，才说明比较的是方向而不是「两个字符串等不等」。
        """
        self.assertEqual(self.docs["au-485-graduate"]["program"]["country_code"], "AU")
        self.assertEqual(self.docs["au-407-training"]["program"]["country_code"], "AU")
        for loc, inside, outside in (
            ("AU", ("pre_inside_country_ok", "pass"), ("pre_outside_country_no", "fail")),
            ("CN", ("pre_inside_country_no", "fail"), ("pre_outside_country_ok", "pass")),
        ):
            self.assertEqual(
                self.code("au-485-graduate", "pre_inside_country", current_location=loc),
                inside, loc,
            )
            self.assertEqual(
                self.code("au-407-training", "pre_outside_country", current_location=loc),
                outside, loc,
            )
            self.assertNotEqual(
                inside[1], outside[1],
                "同一所在地对同国的 inside / outside 必须相反，否则两个分支被写成了同一个",
            )

    def test_outside_missing_location_stays_silent(self):
        """没有合法现居地时必须落回原码 `pre_outside_country`（silent）。

        六种「取不到合法值」的形态各验一遍，与 P1d 对 inside 的要求同严格度。
        这一条守的是「接地」不等于「默认放行」：现居地缺失时判 pass 会让每一个
        没填这个字段的人都看到「可以递」，而其中一部分人其实正在该国境内。
        """
        for bad in ("absent", None, "", "cn", "CHINA", "中国"):
            pr = dict(mr.SAMPLES["B"])
            if bad == "absent":
                pr.pop("current_location", None)
            else:
                pr["current_location"] = bad
            _, dims = mr.judge(self.docs["au-407-training"], pr)
            pre = [d for d in dims if d["code"].startswith("pre_outside_country")]
            self.assertEqual(len(pre), 1, f"current_location={bad!r} 时 outside 维缺失")
            self.assertEqual(
                (pre[0]["code"], pre[0]["kind"]),
                ("pre_outside_country", "silent"),
                f"current_location={bad!r} 时未落 silent：{pre[0]}",
            )

    def test_outside_program_without_country_code_stays_silent(self):
        """项目侧没有国家代码时，「境外」无所指 → silent。

        少了这一支，`loc != cc` 会把画像值与 None 比较、恒不等 → 恒判 pass，
        等于替官方宣布「谁都能递」——比恒判 fail 更危险（放进来的人会被拒签）。
        """
        doc = json.loads(json.dumps(self.docs["se-look-for-work"]))
        self.assertEqual(doc["program"]["country_code"], "SE")
        del doc["program"]["country_code"]
        for loc in ("CN", "SE"):
            _, dims = mr.judge(doc, dict(mr.SAMPLES["B"], current_location=loc))
            pre = next(d for d in dims if d["code"].startswith("pre_outside_country"))
            self.assertEqual((pre["code"], pre["kind"]), ("pre_outside_country", "silent"), loc)

    # ===================== pre_home_residence =====================

    def test_home_residence_passes_when_living_in_passport_country(self):
        """台湾护照 + 现居 TW → `jp-working-holiday` 的常驻要求判 pass。

        项目原文是「须为协议国家/地区国民，**且**目前居住于其国籍国/地区」。
        C 画像（台湾护照、人在台湾）正是这条要求的对象，判 pass 是**结论**，
        不是放水——它的护照维本来就 pass（日本对台湾护照开放）。
        """
        self.assertEqual(
            self.code("jp-working-holiday", "pre_home_residence",
                      passport="taiwan_china", current_location="TW"),
            ("pre_home_residence_ok", "pass"),
        )
        d = next(x for x in self.pre("jp-working-holiday", passport="taiwan_china",
                                     current_location="TW")
                 if x["code"] == "pre_home_residence_ok")
        self.assertIn("TW", d["need"])
        self.assertIn("TW", d["have"])

    def test_home_residence_fails_when_living_elsewhere(self):
        """台湾护照 + 现居 AU → `nz-china-whv` 的常驻要求判 fail。

        官方 note 明写「申请人须常驻其护照所属地区」：一个台湾护照、人在澳洲的
        申请人，既不是大陆名额的对象、也不符合「常驻其护照所属地区」，必须判
        fail 而不是 silent——这条补材料满足不了，得先回台湾。
        """
        state, dims = mr.judge(self.docs["nz-china-whv"],
                               dict(mr.SAMPLES["C"], current_location="AU"))
        self.assertEqual(state, "cannot")
        d = next(x for x in dims if x["code"].startswith("pre_home_residence"))
        self.assertEqual((d["code"], d["kind"]), ("pre_home_residence_no", "fail"))
        self.assertIn("TW", d["need"], "need 必须写明「护照所属地」是哪")
        self.assertIn("AU", d["have"], "have 必须写明画像的现居地")

    def test_home_residence_compares_to_passport_not_program_country(self):
        """**方向陷阱**：判据是「现居 == 护照所属地」，不是「现居 == 项目国」。

        反证：台湾护照、现居 JP（人就在日本）时，`jp-working-holiday` 的常驻要求
        必须判 **fail**——因为日本要求的是「住在你的国籍国」，人在日本恰好不符合。
        若把判据写成 `loc == country_code`，这一例会判 pass，等于把这条要求的
        意思整个反过来（原文从未要求申请人住在日本，那反而与「打工度假」矛盾）。

        同一组数据的镜像：现居 TW 时判 pass（见上一条）。两者合起来才说明比较的
        右操作数是 `PASSPORT_COUNTRY[passport]` 而非 `doc.program.country_code`。
        """
        self.assertEqual(self.docs["jp-working-holiday"]["program"]["country_code"], "JP")
        self.assertEqual(
            self.code("jp-working-holiday", "pre_home_residence",
                      passport="taiwan_china", current_location="JP"),
            ("pre_home_residence_no", "fail"),
        )
        # 同一张护照，换成在护照所属地 → pass（成对的另一半）
        self.assertEqual(
            self.code("jp-working-holiday", "pre_home_residence",
                      passport="taiwan_china", current_location="TW"),
            ("pre_home_residence_ok", "pass"),
        )

    def test_home_residence_missing_either_side_stays_silent(self):
        """护照侧或现居侧任一拿不到 → silent，且**不猜**另一边。

        四种形态：现居缺失/非法、护照不在映射表里。最后一例尤其重要——将来若新增
        一种护照而忘了补映射，这里会落 silent 而不是拿项目国或别的值顶上去。
        """
        cases = [
            {"passport": "taiwan_china", "current_location": None},
            {"passport": "taiwan_china", "current_location": "tw"},
            {"passport": "taiwan_china", "current_location": "中国"},
            # 映射表里没有的护照值：不许猜成大陆/台湾
            {"passport": "macau_china", "current_location": "MO"},
        ]
        for case in cases:
            _, dims = mr.judge(self.docs["jp-working-holiday"],
                               dict(mr.SAMPLES["C"], **case))
            pre = [d for d in dims if d["code"].startswith("pre_home_residence")]
            self.assertEqual(len(pre), 1, case)
            self.assertEqual(
                (pre[0]["code"], pre[0]["kind"]),
                ("pre_home_residence", "silent"),
                f"{case} 时未落 silent：{pre[0]}",
            )

    def test_passport_country_table_covers_exactly_the_three_known_passports(self):
        """映射表只许登记库里真有的三类护照，且值必须与现居地同一套代码体系。

        多登记一类（比如凭印象写上 `macau_china: MO`）会让引擎对一种**从未被
        审计过**的护照下结论；值写成小写或国名会让比较恒不等。两者都是静默错误。
        """
        self.assertEqual(set(mr.PASSPORT_COUNTRY), set(mr.PASSPORTS))
        self.assertEqual(
            mr.PASSPORT_COUNTRY,
            {"mainland_china": "CN", "hong_kong_china": "HK", "taiwan_china": "TW"},
        )
        for k, v in mr.PASSPORT_COUNTRY.items():
            self.assertRegex(v, mr.CURRENT_LOCATION_RE, k)
        # 查不到的护照返回 None，不抛异常、不返回空串
        self.assertIsNone(mr.passport_country_of({"passport": "macau_china"}))
        self.assertIsNone(mr.passport_country_of({}))
        self.assertEqual(mr.passport_country_of({"passport": "taiwan_china"}), "TW")

    # ===================== 两码共用的边界 =====================

    def test_new_grounded_codes_are_not_registered_as_silent(self):
        """四个新码是 pass/fail，不许进甲乙任何一表；两个原码的登记一个字节不动。

        `pre_outside_country` / `pre_home_residence`（silent）**仍留在**
        `CLASS_B_CODES` 里：画像在前端是选填的，真实用户多数不填，引擎不能替
        前端宣布「债已还清」——摘除的前提是字段必填，那是产品决定，不是本单。
        """
        for code in ("pre_outside_country_ok", "pre_outside_country_no",
                     "pre_home_residence_ok", "pre_home_residence_no"):
            self.assertNotIn(code, mr.CLASS_B_CODES, code)
            self.assertNotIn(code, mr.BY_DESIGN_CODES, code)
        for code in ("pre_outside_country", "pre_home_residence"):
            self.assertIn(code, mr.CLASS_B_CODES, code)
            self.assertNotIn(code, mr.BY_DESIGN_CODES, code)

    def test_grounded_two_codes_drive_the_registered_flip_set(self):
        """翻转集合本身被钉住：只有这 3 条 (项目 × 画像) 的三态变了。

        逐条归因（改前 → 改后 → 驱动维）：

        | 项目 | 画像 | 改前 | 改后 | 驱动 |
        |---|---|---|---|---|
        | `jp-working-holiday` | C | unknown | **can** | `pre_home_residence` silent→pass（C 现居 TW == 台湾护照所属地） |
        | `nz-china-whv` | A | unknown | **can** | 同上（A 现居 CN == 大陆护照所属地） |
        | `nz-china-whv` | C | unknown | **can** | 同上 |

        其余 6 条只改前置维、不改三态（`au-407-training` A/B/C、
        `se-look-for-work` A/B/C 的 outside 由 silent 变 pass，但别的维仍挡着）。
        把翻转集合写成断言，是为了让「静默翻转」立刻显形——将来有人动了
        `PASSPORT_COUNTRY` 或 `current_location` 的默认值，这条会红。
        """
        expect = {
            ("jp-working-holiday", "C"): "can",
            ("nz-china-whv", "A"): "can",
            ("nz-china-whv", "C"): "can",
        }
        got = {}
        for pid in ("jp-working-holiday", "nz-china-whv"):
            for name in ("A", "B", "C"):
                got[(pid, name)] = mr.judge(self.docs[pid], mr.SAMPLES[name])[0]
        for key, want in expect.items():
            self.assertEqual(got[key], want, key)
        # 未被接地的两个 outside 项目三态不许翻（它们由别的维决定）
        self.assertEqual(mr.judge(self.docs["au-407-training"], mr.SAMPLES["A"])[0], "unknown")
        self.assertEqual(mr.judge(self.docs["au-407-training"], mr.SAMPLES["B"])[0], "gap")
        self.assertEqual(mr.judge(self.docs["au-407-training"], mr.SAMPLES["C"])[0], "unknown")
        for name in ("A", "B", "C"):
            self.assertEqual(
                mr.judge(self.docs["se-look-for-work"], mr.SAMPLES[name])[0], "cannot", name
            )


class P3EducationPaths(unittest.TestCase):
    """P3 成对回归：教育维从「单一总序」改成「路径谓词」后，三个病灶各钉一对。

    这一组的方法论是**成对**：只钉「假 pass 修好了」不够——把整维判死也能让它绿。
    每一对都必须同时出示正反两面，且 fail 的理由码要落在教育维本身，
    不许靠别的维把整体拉黑来遮。

    | 病灶 | 反面（修前错判） | 正面（修后须成立） |
    |---|---|---|
    | J-1 Intern 假 pass | 已毕业 → 不得 pass | 在读 → 仍 pass |
    | J-1 Trainee 假 cannot | 无学位+5 年 → 不得 cannot | 无学位+不足 → 仍 cannot |
    | F-1 OPT 学年 | 时长不足 → fail | 时长达标 → pass；缺数据 → silent |
    """

    @classmethod
    def setUpClass(cls):
        cls.docs = {d["program"]["id"]: d for d in mr.load_programs()}

    def edu(self, pid, **override):
        """以 B 画像为底，覆盖指定字段后取教育维那一格。"""
        pr = dict(mr.SAMPLES["B"])
        pr.update(override)
        state, dims = mr.judge(self.docs[pid], pr)
        d = next(x for x in dims if x["dim"] == "education")
        return state, d

    # —— 病灶①：intern 假 pass ——
    def test_intern_graduated_is_not_pass_and_enrolled_still_passes(self):
        """us-j1-intern 原文要求「现在必须在读」。旧总序里
        `bachelor_completed`(4) > `bachelor_in_progress`(3)，于是**已毕业的人
        比在读的人更够格** —— 这是全线首个假 pass（batch9b §2 第 3 行）。

        反面：B/C 已毕业（enrollment_status=completed）不得再判 pass，
        且 fail 的理由码必须是教育维的 `edu_not_enrolled`，不是靠别的维遮。
        正面：同一个人改回 enrolled，教育维必须恢复 pass —— 否则「判死」也能
        让反面绿，那是矫枉过正。
        """
        for sample in ("B", "C"):
            # 夹具原值即「已毕业」（enrollment_status=completed），不加覆盖
            state, dims = mr.judge(self.docs["us-j1-intern"], mr.SAMPLES[sample])
            e = next(x for x in dims if x["dim"] == "education")
            self.assertEqual(e["kind"], "fail", f"{sample} 已毕业仍被判 {e}")
            self.assertEqual(e["code"], "edu_not_enrolled", e)
            self.assertEqual(state, "cannot", f"{sample} 应 cannot")

        # 正面：改回在读，教育维必须 pass
        _, d = self.edu("us-j1-intern", education="bachelor_in_progress",
                        enrollment_status="enrolled")
        self.assertEqual(d["kind"], "pass", d)
        self.assertEqual(d["code"], "edu_ok", d)

    # —— 病灶②：trainee 假 cannot ——
    def test_trainee_experience_path_rescues_no_degree(self):
        """us-j1-trainee 官方路径②明文允许「无学历 + 境外 5 年经验」。
        旧总序里没有这个位子，于是把合格者判死 —— 全线首个假 cannot
        （batch10 §2 第 4 行）。

        反面：无学位（high_school）+ 5 年境外经验 → 不得 cannot。
        正面：无学位 + 经验不足（1 年）→ 仍须 cannot，理由 `edu_low`。
        两条一起才说明「路径②通了」而不是「这维被关掉了」。
        """
        state, d = self.edu("us-j1-trainee", education="high_school",
                            work_experience_years=5)
        self.assertNotEqual(state, "cannot", f"路径②仍被判死：{d}")
        self.assertEqual(d["kind"], "pass", d)
        self.assertEqual(d["code"], "edu_ok", d)

        # 防矫枉过正：经验不够仍 cannot
        state2, d2 = self.edu("us-j1-trainee", education="high_school",
                              work_experience_years=1)
        self.assertEqual(state2, "cannot", f"经验不足却放行：{d2}")
        self.assertEqual(d2["kind"], "fail", d2)
        self.assertEqual(d2["code"], "edu_low", d2)

    # —— 病灶③：f1-opt 学年 ——
    def test_f1_opt_duration_predicate_drives_result(self):
        """us-f1-opt 的「一整个学年」过去没有字段可读，学制时长无人管
        （batch9a §2 第 6 行）。现在由时长谓词驱动。

        三态各一条：
          · 时长不足（6 个月 < 10 个月）→ fail / `edu_duration_short`
          · 时长达标（48 个月 = 四年制）→ pass / `edu_ok`
          · 时长缺失（None）→ silent / `edu_duration_unknown`，**不许默认 pass**
        """
        state, d = self.edu("us-f1-opt", study_months=6)
        self.assertEqual(d["kind"], "fail", d)
        self.assertEqual(d["code"], "edu_duration_short", d)
        self.assertEqual(state, "cannot", "时长不足却仍可申")

        _, ok = self.edu("us-f1-opt", study_months=48)
        self.assertEqual(ok["kind"], "pass", ok)
        self.assertEqual(ok["code"], "edu_ok", ok)

        _, unk = self.edu("us-f1-opt", study_months=None)
        self.assertEqual(unk["kind"], "silent", unk)
        self.assertEqual(unk["code"], "edu_duration_unknown", unk)

    # —— 登记表口径：新码必须留在停工线口径内 ——
    def test_new_edu_silent_codes_are_classified(self):
        """派单 §3 明文：新码分类要有测试钉住，**不许顺手把它排除在停工线
        口径外**。`edu_duration_unknown` / `edu_enrollment_unknown` 都是
        「画像没采集那个人自己的事实」，按 P2-1 判据属乙类（画像债），
        补一条画像字段就能判 —— 所以必须在 CLASS_B_CODES 里，与
        `test_every_silent_code_is_classified` 互补。"""
        for code in ("edu_duration_unknown", "edu_enrollment_unknown"):
            self.assertIn(code, mr.CLASS_B_CODES, f"{code} 被排除在乙类之外")

    # —— doctorate 入枚举 ——
    def test_doctorate_is_a_real_level(self):
        """doctorate 补进学历枚举后，必须真的能表达「博士达标」：
        博士学历满足 bachelor_completed 门槛，且不是靠 any 兜过去的。"""
        self.assertIn("doctorate", mr.EDU_LEVEL_ORDER)
        self.assertIn(
            "doctorate",
            mr.EDU_LEVEL_QUALIFIES["bachelor_completed"],
            "博士应满足本科门槛",
        )
        _, d = self.edu("us-f1-opt", education="doctorate", study_months=48)
        self.assertEqual(d["kind"], "pass", d)


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


class FormKeyFields(unittest.TestCase):
    """采集面契约（2026-11-20 01:56 工单：表单关键字段补齐）。

    这一组守的是「闸量的是谁」这件事。此前停工线只量 13 字段的审计夹具，
    而网页表单只有 6 个输入口——闸量出的「线内」是对夹具说的，不是对用户说的。
    真实口径下 HEAD 是 15/41 = 0.3659，早已越线。

    三条断言各挡一类错误：
      · test_profile_fields_are_all_collectable —— 引擎加字段不加表单口（本单前
        的成因）。这条红了就是在说「你又让一个字段只有夹具能用」。
      · test_gate_rules_match_engine_readers —— 门规则与引擎读点不等。
        开小了用户白填，开大了表单又变长。
      · test_gate_never_locks_out_relevant_field —— 「条件显示」变成死锁
        （不填不显示、不显示没法填）。
    """

    @classmethod
    def setUpClass(cls):
        cls.docs = mr.load_programs()

    # —— ① 采集面 = 判定面 ——
    def test_profile_fields_are_all_collectable(self):
        """引擎读的每个画像字段，表单都必须有输入口。

        `collection_gap()` 非空即红。这条比写报告有用：报告不会拦下一个人。
        失败时打印缺口，另外提示去改哪个文件——错误信息要直接指路。
        """
        gap = mr.collection_gap()
        self.assertEqual(
            gap, [],
            "引擎读了这些字段但网页表单没有输入口：%s\n"
            "改 web/src/components/VerdictView.tsx 与 FORM_FIELDS，"
            "两处一起改。" % gap,
        )

    def test_form_fields_exist_in_samples(self):
        """FORM_FIELDS / PROFILE_FIELDS 里的每个键都必须是夹具真有的键。

        防的是手滑写错一个键名——那种错不会红在任何别处，只会让那个字段
        永远取不到值而不自知。
        """
        keys = set(mr.SAMPLES["A"])
        for name, table in (("FORM_FIELDS", mr.FORM_FIELDS),
                            ("PROFILE_FIELDS", mr.PROFILE_FIELDS)):
            unknown = sorted(set(table) - keys)
            self.assertEqual(unknown, [], "%s 里有夹具不存在的键：%s" % (name, unknown))
        # 反向：夹具有的键必须被某一边覆盖，否则那个字段谁也问不到
        uncov = sorted(keys - set(mr.PROFILE_FIELDS))
        self.assertEqual(uncov, [], "夹具字段未被 PROFILE_FIELDS 覆盖：%s" % uncov)

    def test_engine_reads_only_registered_fields(self):
        """引擎实际 pr.get / pr[] 的键必须都在 PROFILE_FIELDS 里。

        这条不靠人维护清单：直接从源码里扫读点。将来谁在 judge() 里加一个
        `pr.get("new_field")` 而没登记，这条当场红——比等下一个人去发现要好。
        """
        src = io.open(mr.__file__, encoding="utf-8").read()
        read = set(re.findall(r'pr\.get\("([a-z_]+)"\)', src))
        read |= set(re.findall(r'pr\["([a-z_]+)"\]', src))
        # SAMPLES 建立时用的键也算（它们是夹具契约的一部分）
        self.assertTrue(read, "没能从源码里扫出任何画像读点，正则过期了？")
        missing = sorted(read - set(mr.PROFILE_FIELDS))
        self.assertEqual(missing, [], "引擎读了未登记的画像字段：%s" % missing)

    # —— ② 条件显示的门 = 引擎读点（同源，不是同结论） ——
    def _readers_of_field(self, field, probe):
        """实测：把某字段从 None 换成真值，(dim,kind,code) 整串变了的项目。"""
        out = set()
        for d in self.docs:
            pr = dict(mr.SAMPLES["C"])
            pr[field] = None
            _, before = mr.judge(d, pr)
            pr2 = dict(pr)
            pr2[field] = probe
            _, after = mr.judge(d, pr2)
            if self._sig(before) != self._sig(after):
                out.add(d["program"]["id"])
        return out

    @staticmethod
    def _sig(dims):
        return "|".join("%s:%s:%s" % (x["dim"], x["kind"], x["code"]) for x in dims)

    def test_gate_rules_match_engine_readers(self):
        """`profile_readers()` 的结论必须与 judge() 的实测读点**逐项目相等**。

        这一条直接调函数、**不经过产物**——产物是快照，改了函数不重生成
        它就还是旧的，测试会拿旧快照比旧结论，两边一样绿，什么也证明不了。
        （本单的变异测试正是这样抓到初版：改坏 profile_readers，8 条断言
        全部照绿，因为它验的是它自己生成的那份 JSON。）

        产物与函数的一致性由 `--check` 那条闸管（产物过期即红），
        所以这里不必再比一次文件。

        两个方向各自打印差异，因为修法完全不同：
          只有实测读（门开小）→ 用户填了也翻不动，白问一次；
          只有函数说读（门开大）→ 表单又变长，违背「不许拉长」。
        """
        probe = dict(mr.PROFILE_FIELD_PROBES)
        for field, val in probe.items():
            measured = self._readers_of_field(field, val)
            by_func = {d["program"]["id"] for d in self.docs
                       if mr.profile_readers(d)[field]}
            self.assertEqual(
                measured, by_func,
                "字段 %s：profile_readers() 与 judge() 实测读点不等。\n"
                "  只有实测读（门开小、用户白填）：%s\n"
                "  只有函数说读（门开大、表单变长）：%s"
                % (field, sorted(measured - by_func), sorted(by_func - measured)),
            )

    def test_gate_reads_in_artifacts_is_fresh(self):
        """产物里的 reads 必须与函数现值一致（防手改产物 / 忘重生成）。

        与上一条分工：上一条验函数对不对，这一条验发出去的那份数据是不是
        函数当前的结果。--check 比的是整个文件的字节，这里只挑 reads 比，
        好处是红了能直接指出是哪个项目的哪个字段不对。
        """
        with io.open(mr.FLAGS, encoding="utf-8") as fh:
            flags = json.load(fh)["programs"]
        stale = []
        for d in self.docs:
            pid = d["program"]["id"]
            want = mr.profile_readers(d)
            got = (flags[pid].get("precondition") or {}).get("p1b2", {}).get("reads")
            if got != want:
                stale.append((pid, want, got))
        self.assertEqual(
            stale[:3], [],
            "产物里的 reads 与函数现值不一致（%d 条）。运行 "
            "python scripts/match_readiness.py --emit" % len(stale),
        )

    def test_gate_reads_covers_every_extra_field(self):
        """profile_readers() 必须把七个补充字段**全部**列出，值为布尔。

        漏一个键的后果：前端 readersOf() 读到 undefined → 当成 false →
        门静默关掉，而且没有任何报错。字段名写错也一样。
        """
        want = set(mr.PROFILE_FIELD_PROBES)
        for d in self.docs:
            reads = mr.profile_readers(d)
            pid = d["program"]["id"]
            self.assertEqual(
                set(reads), want,
                "%s 的 reads 键集合不对：缺 %s / 多 %s"
                % (pid, sorted(want - set(reads)), sorted(set(reads) - want)),
            )
            for k, v in reads.items():
                self.assertIsInstance(v, bool, "%s.reads.%s 不是布尔：%r" % (pid, k, v))

    def test_every_extra_field_is_read_by_someone(self):
        """七个补充字段里，每个都必须至少有一条项目读它。

        全库无人读的字段就不该放进表单——问一条没有任何项目用到的信息，
        是在浪费用户注意力，也会让人以为它很重要。
        """
        for field in mr.PROFILE_FIELD_PROBES:
            n = sum(1 for d in self.docs if mr.profile_readers(d)[field])
            self.assertGreater(
                n, 0,
                "字段 %s 没有任何项目读它 —— 不该进表单" % field,
            )

    # —— ③ 条件显示不许变成死锁 ——
    def test_gate_never_locks_out_relevant_field(self):
        """门只依赖六项必填字段，不依赖补充字段本身（防死锁）。

        「不填不显示、不显示没法填」是条件显示最典型的坏法：用户永远看不到
        那个字段，也就永远拿不到那条结论。判据：门的输入（GateInput）只用
        profile 的六项 + 项目事实——一个**未填**任何补充字段的画像，
        与填满补充字段的画像，开出的字段集合必须相同。
        """
        with io.open(
            os.path.join(ROOT, "web", "src", "lib", "profileFields.ts"), encoding="utf-8"
        ) as fh:
            src = fh.read()
        # 门函数体内不许引用 profile 上的补充字段名
        extra = ("dependents", "enrollment_status", "months_since_graduation",
                 "prior_participation", "prior_same_category_visa", "study_months",
                 "work_experience_years")
        gate_body = src.split("export function shouldAsk", 1)[1].split("\n}", 1)[0]
        used = [f for f in extra if re.search(r"\b%s\b" % f, gate_body)]
        self.assertEqual(
            used, [],
            "门判据读了补充字段 %s —— 那会死锁（不填不显示、不显示没法填）。"
            "门只能看六项必填 + 项目事实。" % used,
        )

    # —— ④ 真实口径读数（本单要报的那个数） ——
    def test_real_profile_reading_is_recorded(self):
        """真实口径（表单能采集的部分）在补完关键字段后必须回到线内。

        本单的目的不是让数字好看，是让闸量对对象。补完 6 个关键字段后，
        真实口径的乙类读数应当与夹具口径**完全一致**——不一致就说明还有字段
        只在夹具里存在，闸仍有两个读数。
        """
        # 表单口径：只保留 FORM_FIELDS，其余置 None
        real = {}
        for name, pr in mr.SAMPLES.items():
            r = dict(pr)
            for k in r:
                if k not in mr.FORM_FIELDS:
                    r[k] = None
            real[name] = r

        saved = mr.SAMPLES
        try:
            mr.SAMPLES = type(saved)((n, real[n]) for n in saved)
            real_rep = mr.audit()
        finally:
            mr.SAMPLES = saved
        fixture_rep = mr.audit()

        for s in "ABC":
            self.assertEqual(
                real_rep["samples"][s]["unknown_class_b"],
                fixture_rep["samples"][s]["unknown_class_b"],
                "画像 %s：真实口径乙类 %d ≠ 夹具口径 %d —— 说明还有字段只在夹具里"
                % (s, real_rep["samples"][s]["unknown_class_b"],
                   fixture_rep["samples"][s]["unknown_class_b"]),
            )
        self.assertLessEqual(
            real_rep["max_ratio_class_b"], mr.STOP_LINE_RATIO,
            "真实口径乙类 %.4f 仍越停工线 %s" % (
                real_rep["max_ratio_class_b"], mr.ratio_text(mr.STOP_LINE_RATIO)),
        )


if __name__ == "__main__":
    unittest.main()
