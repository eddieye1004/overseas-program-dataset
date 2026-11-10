"""scripts/track.py 的回归测试。

重心与 test_validate.py 一致：验证「该红的会红」，而不是「该绿的不会红」。
复核台账存在的意义是让人知道哪条该重新核；如果它在该报警时保持沉默，
那它比不做还糟——一份永远说「全部在周期内」的台账会给人虚假的安全感。

三个边界必须钉住：
  1. 刚好走到周期最后一天算「到期」，超一天算「已过期」（差一天不该翻转）
  2. 写死窗口的项目按 90 天算，其余按 180 天（策略不许漂）
  3. `--check` 有过期记录时退出码为 1，正常时为 0（CI 靠这个变红）

运行：
    python -m unittest discover -s tests -v
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "track.py")
PROGRAMS = os.path.join(ROOT, "data", "programs")

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import track  # noqa: E402


def run_track(*args):
    """跑一次 CLI，返回 (退出码, 标准输出)。"""
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
    )


def load_fixture():
    """取一份真实记录，注入日期断言周期——比手写最小 JSON 更接近真实结构。"""
    with io.open(os.path.join(PROGRAMS, "nz-china-whv.json"), encoding="utf-8") as fh:
        return json.load(fh)


class ClassifyTest(unittest.TestCase):
    """分档边界。"""

    def test_exactly_at_interval_is_due_soon_not_overdue(self):
        # 第 180 天：年限刚好用满，还剩 0 天 → 应当提示，但不能说已过期。
        # 差一天就翻转成「过期」会让使用者在周末看到红色。
        self.assertEqual(track.classify(180, 180), "due_soon")

    def test_one_day_past_interval_is_overdue(self):
        self.assertEqual(track.classify(181, 180), "overdue")

    def test_fresh_when_plenty_left(self):
        self.assertEqual(track.classify(10, 180), "fresh")

    def test_due_soon_window_is_quarter_of_interval(self):
        # 剩余不足 25% 时提前提醒：180 → 第 135 天起算即将到期
        self.assertEqual(track.classify(134, 180), "fresh")
        self.assertEqual(track.classify(135, 180), "due_soon")
        # 90 天周期同理：25% = 22.5，向下取整到 22，所以第 68 天起提醒
        # （剩 23 天时仍大于 22.5 的四分之一线，不能提前喊）
        self.assertEqual(track.classify(67, 90), "fresh")
        self.assertEqual(track.classify(68, 90), "due_soon")


class IntervalTest(unittest.TestCase):
    """周期策略：写死窗口的按 90 天，其余 180 天。"""

    def test_dated_window_gets_short_interval(self):
        doc = load_fixture()  # nz-china-whv 的 windows 里有 open_date
        self.assertTrue(track.has_dated_window(doc))
        self.assertEqual(track.interval_for(doc), track.INTERVAL_DATED_WINDOW)
        self.assertEqual(track.INTERVAL_DATED_WINDOW, 90)

    def test_undated_window_gets_default_interval(self):
        doc = load_fixture()
        for w in doc["timeline"]["windows"]:
            for k in ("open_date", "close_date", "draw_period_end"):
                w.pop(k, None)
        self.assertFalse(track.has_dated_window(doc))
        self.assertEqual(track.interval_for(doc), track.INTERVAL_DEFAULT)
        self.assertEqual(track.INTERVAL_DEFAULT, 180)

    def test_policy_file_is_the_single_source(self):
        # 周期写在 data/review-policy.json 里，web/scripts/sync-data.mjs 也读同一个文件。
        # 这里断言脚本确实从文件读，而不是代码里还留着第二份 90/180。
        policy = track.load_policy()
        self.assertEqual(policy["interval_dated_window_days"], track.INTERVAL_DATED_WINDOW)
        self.assertEqual(policy["interval_default_days"], track.INTERVAL_DEFAULT)
        with io.open(SCRIPT, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("review-policy.json", src)
        self.assertNotRegex(
            src,
            r"^INTERVAL_DATED_WINDOW\s*=\s*\d+$",
            "周期不该在代码里写死数字，必须来自 review-policy.json",
        )


class BuildTest(unittest.TestCase):
    """台账条目的完整性。"""

    def test_every_program_appears_once(self):
        programs = track.load_programs()
        t = track.build(programs, date(2026, 11, 10))
        ids = [r["id"] for r in t["programs"]]
        self.assertEqual(len(ids), len(set(ids)), "台账里同一个 id 出现了两次")
        self.assertEqual(len(ids), len(programs))
        self.assertEqual(t["summary"]["total"], len(programs))

    def test_summary_counts_add_up(self):
        programs = track.load_programs()
        t = track.build(programs, date(2026, 11, 10))
        s = t["summary"]
        self.assertEqual(
            s["overdue"] + s["due_soon"] + s["fresh"] + s["unknown"], s["total"]
        )

    def test_overdue_sorted_first(self):
        programs = track.load_programs()
        t = track.build(programs, date(2030, 1, 1))  # 远期基准日，全部过期
        states = [r["state"] for r in t["programs"]]
        self.assertEqual(states, sorted(states, key=lambda s: ["overdue", "unknown", "due_soon", "fresh"].index(s)))

    def test_future_baseline_marks_everything_overdue(self):
        programs = track.load_programs()
        t = track.build(programs, date(2030, 1, 1))
        self.assertEqual(t["summary"]["overdue"], len(programs))
        self.assertEqual(t["summary"]["fresh"], 0)

    def test_due_date_matches_last_verified_plus_interval(self):
        programs = track.load_programs()
        today = date(2026, 11, 10)
        t = track.build(programs, today)
        for r in t["programs"]:
            if r["last_verified"] is None:
                continue
            lv = track.parse_date(r["last_verified"])
            expected = lv.toordinal() + r["interval_days"]
            self.assertEqual(
                track.parse_date(r["due"]).toordinal(), expected, f"{r['id']} 的下次复核日算错了"
            )


class RenderTest(unittest.TestCase):
    """人读版台账。"""

    def test_md_lists_pending_and_all(self):
        programs = track.load_programs()
        t = track.build(programs, date(2030, 1, 1))
        md = track.render_md(t)
        self.assertIn("# 复核台账", md)
        self.assertIn("## 需要处理", md)
        self.assertIn("## 全部记录", md)
        self.assertIn("## 复核该做什么", md)
        # 每条记录都要在「全部记录」表里出现一次
        for r in t["programs"]:
            self.assertIn(f"`{r['id']}`", md)

    def test_md_marks_generator_so_nobody_edits_by_hand(self):
        programs = track.load_programs()
        md = track.render_md(track.build(programs, date(2026, 11, 10)))
        self.assertIn("本文件由脚本生成", md)
        self.assertIn("scripts/track.py", md)


class CliTest(unittest.TestCase):
    """CI 靠退出码变红，所以退出码本身要被钉住。"""

    def test_check_passes_when_everything_is_fresh(self):
        # 用真实数据 + 当天基准日：刚核过的记录不该被判过期
        r = run_track("--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("在复核周期内", r.stdout)

    def test_check_fails_with_far_future_baseline(self):
        r = run_track("--check", "--today", "2030-01-01")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("超出复核周期", r.stdout)

    def test_check_reports_which_programs_are_late(self):
        # 只说「有过期」不够：台账的价值在于点名。这里断言真的列出了 id。
        r = run_track("--check", "--today", "2030-01-01")
        self.assertIn("au-462-work-holiday", r.stdout)

    def test_check_does_not_write_files(self):
        # --check 只判定不落盘：CI 上跑检查不应该顺手改动工作区，
        # 否则 artifact 里的台账与仓库里的会悄悄不一致。
        before = os.path.getmtime(os.path.join(ROOT, "data", "tracking.json"))
        run_track("--check", "--today", "2030-01-01")
        after = os.path.getmtime(os.path.join(ROOT, "data", "tracking.json"))
        self.assertEqual(before, after, "--check 不该写文件")

    def test_bad_today_is_rejected(self):
        r = run_track("--check", "--today", "2026/11/10")
        self.assertEqual(r.returncode, 2)
        self.assertIn("基准日格式不对", r.stderr)

    def test_json_output_is_parseable(self):
        r = run_track("--json", "--today", "2026-11-10")
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertEqual(data["generated_for"], "2026-11-10")
        self.assertIn("programs", data)
        self.assertIn("summary", data)


class TrackingArtifactTest(unittest.TestCase):
    """仓库里那份 tracking.json 必须与当前数据同步。"""

    def test_committed_tracking_matches_rebuild(self):
        path = os.path.join(ROOT, "data", "tracking.json")
        with io.open(path, encoding="utf-8") as fh:
            committed = json.load(fh)
        # 用已提交的基准日重算，结果必须一模一样——否则说明有人改了数据没重跑脚本
        today = track.parse_date(committed["generated_for"])
        rebuilt = track.build(track.load_programs(), today)
        self.assertEqual(
            committed["summary"],
            rebuilt["summary"],
            "data/tracking.json 与当前数据不一致，请重跑 python scripts/track.py",
        )
        self.assertEqual(
            [r["id"] for r in committed["programs"]], [r["id"] for r in rebuilt["programs"]]
        )

    def test_freshness_md_matches_tracking_json(self):
        path_json = os.path.join(ROOT, "data", "tracking.json")
        path_md = os.path.join(ROOT, "data", "FRESHNESS.md")
        with io.open(path_json, encoding="utf-8") as fh:
            t = json.load(fh)
        with io.open(path_md, encoding="utf-8") as fh:
            md = fh.read()
        self.assertEqual(md, track.render_md(t), "FRESHNESS.md 与 tracking.json 不同步")


if __name__ == "__main__":
    unittest.main()
