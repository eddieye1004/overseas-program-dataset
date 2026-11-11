"""窗口日历（timeline.schedule + data/calendar.json）的回归测试。

这块东西是「名额雷达」的数据地基，它唯一的价值就是**可信**：
如果推断出来的日期和官方公布的日期长得一样，雷达就会把人叫错时间，
而且错得毫无痕迹。所以测试的重心全部压在「确定性能不能被区分」上：

  1. inferred / unknown 不许携带具体日期（这条是护栏，不是风格）
  2. confirmed 必须真有日期，否则「已确认」三个字没有内容
  3. rolling / no_window 不该有日期
  4. lead_time_days 必须在合理区间，且提醒日 = 开放日 − lead_time
  5. 仓库里 33 个项目全部有 schedule，不允许漏（漏 = 雷达看不见）

运行：python -m unittest discover -s tests -v
"""

import copy
import glob
import io
import json
import os
import sys
import unittest
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRAMS = os.path.join(ROOT, "data", "programs")
CALENDAR = os.path.join(ROOT, "data", "calendar.json")
FIXTURE = os.path.join(PROGRAMS, "nz-china-whv.json")

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import validate  # noqa: E402
import build_calendar  # noqa: E402


def load_fixture():
    with io.open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)


def load_all():
    out = []
    for path in sorted(glob.glob(os.path.join(PROGRAMS, "*.json"))):
        with io.open(path, encoding="utf-8") as fh:
            out.append((os.path.basename(path), json.load(fh)))
    return out


class ScheduleValidationTest(unittest.TestCase):
    """校验器对 schedule 的硬约束。"""

    def setUp(self):
        self.doc = load_fixture()
        self._real_date = validate.date
        validate.date = date
        self.rep = None

    def check(self, doc):
        rep = validate.Report()
        validate._check_schedule(rep, "f.json", doc["timeline"])
        return rep

    def errors(self, rep):
        return " | ".join(m for _, _, m in rep.errors)

    def base(self, **over):
        s = {
            "type": "annual_cycle",
            "status": "upcoming",
            "date_confidence": "unknown",
            "lead_time_days": 30,
            "note": "测试用的一条说明文字。",
        }
        s.update(over)
        return s

    def test_inferred_must_not_carry_dates(self):
        """回归：推断不许冒充官方日期。这是整块日历最重要的一条。"""
        for field in ("open_date", "close_date"):
            with self.subTest(field=field):
                doc = copy.deepcopy(self.doc)
                doc["timeline"]["schedule"] = self.base(
                    date_confidence="inferred", cycle_note="2025-07-02、2026-07-02 均在 7 月初",
                    **{field: "2027-07-02"},
                )
                rep = self.check(doc)
                self.assertFalse(rep.ok)
                self.assertIn("不得填写具体日期", self.errors(rep))

    def test_unknown_must_not_carry_dates(self):
        doc = copy.deepcopy(self.doc)
        doc["timeline"]["schedule"] = self.base(date_confidence="unknown", open_date="2027-01-01")
        rep = self.check(doc)
        self.assertFalse(rep.ok)
        self.assertIn("不得填写具体日期", self.errors(rep))

    def test_confirmed_with_dates_passes(self):
        doc = copy.deepcopy(self.doc)
        doc["timeline"]["schedule"] = self.base(
            type="fixed_dates", date_confidence="confirmed",
            open_date="2026-06-04", close_date="2026-06-25",
        )
        rep = self.check(doc)
        self.assertTrue(rep.ok, self.errors(rep))

    def test_annual_cycle_inferred_needs_cycle_note(self):
        """说「有规律」就必须把往年的日期列出来，否则规律二字无依据。"""
        doc = copy.deepcopy(self.doc)
        doc["timeline"]["schedule"] = self.base(date_confidence="inferred")
        rep = self.check(doc)
        self.assertFalse(rep.ok)
        self.assertIn("往年实际日期序列", self.errors(rep))

    def test_rolling_must_not_have_dates(self):
        doc = copy.deepcopy(self.doc)
        doc["timeline"]["schedule"] = self.base(
            type="rolling", status="always_open", open_date="2026-01-01",
        )
        rep = self.check(doc)
        self.assertFalse(rep.ok)
        self.assertIn("不应填写", self.errors(rep))

    def test_rolling_cannot_be_confirmed(self):
        doc = copy.deepcopy(self.doc)
        doc["timeline"]["schedule"] = self.base(
            type="rolling", status="always_open", date_confidence="confirmed",
        )
        rep = self.check(doc)
        self.assertFalse(rep.ok)
        self.assertIn("不应标 confirmed", self.errors(rep))

    def test_close_before_open_is_error(self):
        doc = copy.deepcopy(self.doc)
        doc["timeline"]["schedule"] = self.base(
            type="fixed_dates", date_confidence="confirmed",
            open_date="2026-06-25", close_date="2026-06-04",
        )
        rep = self.check(doc)
        self.assertFalse(rep.ok)
        self.assertIn("早于开放日", self.errors(rep))

    def test_lead_time_bounds(self):
        for bad in (-1, 400, "30", None):
            with self.subTest(lead=bad):
                doc = copy.deepcopy(self.doc)
                doc["timeline"]["schedule"] = self.base(lead_time_days=bad)
                rep = self.check(doc)
                self.assertFalse(rep.ok, f"lead_time_days={bad!r} 竟然通过了")

    def test_note_must_have_substance(self):
        doc = copy.deepcopy(self.doc)
        doc["timeline"]["schedule"] = self.base(note="无")
        rep = self.check(doc)
        self.assertFalse(rep.ok)
        self.assertIn("缺少判断依据", self.errors(rep))

    def test_unknown_type_is_rejected(self):
        doc = copy.deepcopy(self.doc)
        doc["timeline"]["schedule"] = self.base(type="someday")
        rep = self.check(doc)
        self.assertFalse(rep.ok)
        self.assertIn("非法枚举值", self.errors(rep))


class RealDataScheduleTest(unittest.TestCase):
    """仓库里的真实数据：33 个项目一个都不能漏。"""

    def test_every_program_has_schedule(self):
        missing = []
        for name, doc in load_all():
            sch = (doc.get("timeline") or {}).get("schedule")
            if not isinstance(sch, dict):
                missing.append(name)
        self.assertEqual(missing, [], "以下项目缺 timeline.schedule：" + ", ".join(missing))

    def test_every_schedule_is_valid(self):
        for name, doc in load_all():
            with self.subTest(program=name):
                rep = validate.Report()
                validate._check_schedule(rep, name, doc["timeline"])
                self.assertTrue(rep.ok, f"{name}: " +
                                " | ".join(m for _, _, m in rep.errors))

    def test_no_inferred_program_carries_a_date(self):
        """对真实数据再查一遍这条护栏——防止有人手工改数据绕过。"""
        bad = []
        for name, doc in load_all():
            sch = (doc.get("timeline") or {}).get("schedule") or {}
            if sch.get("date_confidence") in ("inferred", "unknown"):
                if sch.get("open_date") or sch.get("close_date"):
                    bad.append(f"{name} ({sch.get('date_confidence')})")
        self.assertEqual(bad, [], "推断/未知档竟然带了具体日期：" + ", ".join(bad))


class CalendarArtifactTest(unittest.TestCase):
    """data/calendar.json 是派生物，必须与生成器一致。"""

    def test_committed_calendar_matches_rebuild(self):
        with io.open(CALENDAR, encoding="utf-8") as fh:
            committed = json.load(fh)
        rebuilt = build_calendar.build(date.fromisoformat(committed["generated_for"]))
        self.assertEqual(
            committed, rebuilt,
            "data/calendar.json 与当前数据不一致，请重跑 python scripts/build_calendar.py",
        )

    def test_summary_counts_add_up(self):
        with io.open(CALENDAR, encoding="utf-8") as fh:
            cal = json.load(fh)
        s = cal["summary"]
        self.assertEqual(s["total"], len(cal["programs"]))
        self.assertEqual(s["confirmed"] + s["inferred"] + s["unknown"], s["total"])

    def test_remind_on_is_open_minus_lead(self):
        """提醒日的唯一定义：开放日 − 建议提前天数。别处不许另算一套。"""
        with io.open(CALENDAR, encoding="utf-8") as fh:
            cal = json.load(fh)
        checked = 0
        for r in cal["programs"]:
            if r["open_date"] and r["lead_time_days"] is not None:
                expect = date.fromisoformat(r["open_date"]).toordinal() - r["lead_time_days"]
                got = date.fromisoformat(r["remind_on"]).toordinal()
                self.assertEqual(got, expect, r["id"])
                checked += 1
        self.assertGreater(checked, 0, "没有任何记录带确认日期，测试本身失效了")

    def test_confirmed_rows_carry_dates_and_others_do_not(self):
        with io.open(CALENDAR, encoding="utf-8") as fh:
            cal = json.load(fh)
        for r in cal["programs"]:
            if r["date_confidence"] == "confirmed" and r["type"] == "fixed_dates":
                self.assertIsNotNone(r["open_date"], f"{r['id']} 标了已确认却没有开放日")
            if r["date_confidence"] in ("inferred", "unknown"):
                self.assertIsNone(r["open_date"], f"{r['id']} 不是已确认却带了开放日")


if __name__ == "__main__":
    unittest.main()
