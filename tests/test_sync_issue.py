"""scripts/sync_issue.py 的回归测试。

这个东西的价值全在「幂等」两个字上：如果它每周刷一张新 issue，比不喊还糟——
维护者会在三个月后关掉通知，而那之后所有真正的到期提醒一起失效。

所以这里不测「正文好不好看」，只钉死四件事：
  1. 固定标题是唯一锚点：标题里出现日期/运行号就必须被拦；
  2. 有 open issue 时只 PATCH，绝不 POST（不新建）；
  3. 没有待办时把 issue 关掉，而不是留一张空表；
  4. 「仅有配额缺口」也算活着的待办（这是最容易写错的一条）。

运行：python -m unittest discover -s tests -v
"""

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import sync_issue  # noqa: E402


def make_tracking(states, quota_unverified=()):
    """states: [(id, state)] → 一份最小 tracking。"""
    programs = []
    for pid, state in states:
        programs.append({
            "id": pid,
            "name": pid,
            "country": "X",
            "file": f"{pid}.json",
            "last_verified": "2026-11-01",
            "age_days": 10,
            "interval_days": 180,
            "due": "2027-05-01",
            "days_left": 170,
            "state": state,
            "dated_window": False,
            "sources": [],
            "quota_pending": False,
            "quota_status": "no_quota",
        })
    return {
        "generated_for": "2026-11-11",
        "policy": {
            "interval_dated_window_days": 90,
            "interval_default_days": 180,
            "due_soon_ratio": 0.25,
        },
        "summary": {
            "total": len(programs),
            "overdue": sum(1 for _, s in states if s == "overdue"),
            "due_soon": sum(1 for _, s in states if s == "due_soon"),
            "fresh": sum(1 for _, s in states if s == "fresh"),
            "unknown": sum(1 for _, s in states if s == "unknown"),
        },
        "quota_unverified": [
            {"id": q, "name": q, "country": "X", "quota_note": "待核实说明文字"} for q in quota_unverified
        ],
        "programs": programs,
    }


class IdempotencyAnchorTest(unittest.TestCase):
    """标题是幂等的锚点，不许含任何随时间变化的成分。"""

    def test_title_has_no_date_or_run_id(self):
        t = sync_issue.ISSUE_TITLE
        self.assertNotRegex(t, r"\d{4}[-/]\d{1,2}", "标题里不该出现日期：" + t)
        self.assertNotRegex(t, r"#\d+", "标题里不该出现 issue/运行号：" + t)
        self.assertNotIn("{{", t)

    def test_title_and_label_are_constants(self):
        # 它们被 find_open_issue 与 ensure_label 共用；一旦变成函数返回值，
        # 「先搜已有 issue」这一步就失去了锚点。
        self.assertIsInstance(sync_issue.ISSUE_TITLE, str)
        self.assertIsInstance(sync_issue.ISSUE_LABEL, str)
        self.assertTrue(sync_issue.ISSUE_TITLE.strip())


class BodyTest(unittest.TestCase):
    def test_body_carries_marker_for_human_identification(self):
        body = sync_issue.render_body(make_tracking([("a", "overdue")]), [{"id": "a", "state": "overdue"}])
        self.assertIn(sync_issue.MARKER, body)

    def test_body_lists_every_pending_row(self):
        tr = make_tracking([("a", "overdue"), ("b", "due_soon"), ("c", "fresh")])
        pending = sync_issue.needs_attention(tr)
        self.assertEqual([r["id"] for r in pending], ["a", "b"])
        body = sync_issue.render_body(tr, pending)
        self.assertIn("`a`", body)
        self.assertIn("`b`", body)
        self.assertNotIn("`c`", body, "fresh 记录不该混进待复核表")

    def test_body_includes_quota_section_when_present(self):
        tr = make_tracking([("a", "fresh")], quota_unverified=["at-rwr-card-vhq"])
        body = sync_issue.render_body(tr, [])
        self.assertIn("配额待核实", body)
        self.assertIn("at-rwr-card-vhq", body)

    def test_pipe_in_note_does_not_break_table(self):
        """备注里带竖线会把 markdown 表格拆散，必须转义。"""
        tr = make_tracking([("a", "fresh")], quota_unverified=["q"])
        tr["quota_unverified"][0]["quota_note"] = "有 | 竖线"
        body = sync_issue.render_body(tr, [])
        row = [ln for ln in body.splitlines() if "`q`" in ln][0]
        self.assertIn("\\|", row)


class OpenWorkTest(unittest.TestCase):
    """「该不该存在这张 issue」的判定。"""

    def test_fresh_only_means_no_work(self):
        tr = make_tracking([("a", "fresh")])
        self.assertFalse(sync_issue.has_open_work(tr, sync_issue.needs_attention(tr)))

    def test_overdue_means_work(self):
        tr = make_tracking([("a", "overdue")])
        self.assertTrue(sync_issue.has_open_work(tr, sync_issue.needs_attention(tr)))

    def test_quota_gap_alone_keeps_issue_alive(self):
        """回归：只有配额缺口时会误判「没活了」而把刚建的 issue 关掉。"""
        tr = make_tracking([("a", "fresh")], quota_unverified=["at-rwr-card-vhq"])
        pending = sync_issue.needs_attention(tr)
        self.assertEqual(pending, [], "本例不该有任何待复核行")
        self.assertTrue(
            sync_issue.has_open_work(tr, pending),
            "仅剩配额待核实时，issue 必须继续存在",
        )


# ---------------------------------------------------------------------------
# 用假的 GitHub API 复现「每周跑一次」
# ---------------------------------------------------------------------------

class FakeGitHub:
    """记录所有调用，按调用序列给出确定的响应。"""

    def __init__(self, existing_issue=None, label_state="created"):
        self.calls = []
        self.existing = existing_issue
        self.label_state = label_state

    def __call__(self, method, path, token, payload=None):
        self.calls.append((method, path, payload))
        if path.startswith("/search/issues"):
            items = [self.existing] if self.existing else []
            return 200, {"items": items}
        if path.endswith("/labels"):
            # ensure_label 走 gh()，这里模拟 GitHub 的两种真实返回：
            # created → 201；exists → 422（标签已存在，属正常分支）。
            if self.label_state == "exists":
                return 422, {}
            return 201, {}
        if method == "POST" and path.endswith("/issues"):
            self.existing = {"number": 7, "title": sync_issue.ISSUE_TITLE}
            return 201, {"number": 7}
        if method == "PATCH":
            return 200, {}
        return 200, {}


class WeeklyRunTest(unittest.TestCase):
    """连跑两周：第一周建，第二周必须只更新，不许出现第二条。"""

    def setUp(self):
        self._orig_gh = sync_issue.gh
        self._orig_find = sync_issue.find_open_issue
        self._orig_env = dict(os.environ)

    def tearDown(self):
        sync_issue.gh = self._orig_gh
        sync_issue.find_open_issue = self._orig_find
        os.environ.clear()
        os.environ.update(self._orig_env)

    def _run(self, tracking, fake):
        """把 main() 跑一遍，返回它产生的 API 调用序列。

        gh 被换成 fake；find_open_issue 走真实实现（它内部也调 gh），
        这样「搜已有 → 决定新建还是更新」这条链路是完整被测的。
        """
        sync_issue.gh = fake
        orig_load = sync_issue.load_tracking
        sync_issue.load_tracking = lambda: tracking
        os.environ["GH_TOKEN"] = "x"
        os.environ["GITHUB_REPOSITORY"] = "o/r"
        argv = sys.argv
        sys.argv = ["sync_issue.py"]
        try:
            sync_issue.main()
        finally:
            sys.argv = argv
            sync_issue.load_tracking = orig_load

    def test_first_run_creates_second_run_only_updates(self):
        fake = FakeGitHub()
        tr = make_tracking([("a", "overdue")])

        self._run(tr, fake)
        creates = [c for c in fake.calls if c[0] == "POST" and c[1].endswith("/issues")]
        self.assertEqual(len(creates), 1, "第一次应当新建一张")
        self.assertEqual(creates[0][2]["title"], sync_issue.ISSUE_TITLE)

        fake.calls.clear()
        self._run(tr, fake)
        creates2 = [c for c in fake.calls if c[0] == "POST" and c[1].endswith("/issues")]
        patches = [c for c in fake.calls if c[0] == "PATCH"]
        self.assertEqual(creates2, [], "第二次不许再新建——这正是要防的「每周刷一张」")
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0][1], "/repos/o/r/issues/7")

    def test_existing_issue_is_patched_not_duplicated(self):
        fake = FakeGitHub(existing_issue={"number": 3, "title": sync_issue.ISSUE_TITLE})
        self._run(make_tracking([("a", "overdue")]), fake)
        self.assertEqual([c for c in fake.calls if c[0] == "POST" and c[1].endswith("/issues")], [])
        self.assertEqual([c[1] for c in fake.calls if c[0] == "PATCH"], ["/repos/o/r/issues/3"])

    def test_no_work_closes_the_issue(self):
        fake = FakeGitHub(existing_issue={"number": 5, "title": sync_issue.ISSUE_TITLE})
        self._run(make_tracking([("a", "fresh")]), fake)
        patch = [c for c in fake.calls if c[0] == "PATCH"]
        self.assertEqual(len(patch), 1)
        self.assertEqual(patch[0][2]["state"], "closed")

    def test_no_work_and_no_issue_makes_no_write_calls(self):
        fake = FakeGitHub()
        self._run(make_tracking([("a", "fresh")]), fake)
        writes = [c for c in fake.calls if c[0] in ("POST", "PATCH")]
        self.assertEqual(writes, [], "没事可做时不该产生任何写操作")

    def test_label_exists_422_does_not_block_creation(self):
        """标签已存在（422）是正常分支，不能因此让 issue 建不出来。"""
        fake = FakeGitHub(label_state="exists")
        self._run(make_tracking([("a", "overdue")]), fake)
        creates = [c for c in fake.calls if c[0] == "POST" and c[1].endswith("/issues")]
        self.assertEqual(len(creates), 1)
        self.assertEqual(creates[0][2]["labels"], [sync_issue.ISSUE_LABEL])

    def test_quota_gap_only_still_creates_issue(self):
        fake = FakeGitHub()
        self._run(make_tracking([("a", "fresh")], quota_unverified=["q"]), fake)
        creates = [c for c in fake.calls if c[0] == "POST" and c[1].endswith("/issues")]
        self.assertEqual(len(creates), 1, "只剩配额缺口时也要建 issue")


if __name__ == "__main__":
    unittest.main()
