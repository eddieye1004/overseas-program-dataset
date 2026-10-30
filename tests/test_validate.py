"""validate.py 的回归测试。

设计取舍：本套测试的重心是「**假阴性**」方向——坏数据必须被拦下，
而不是「好数据不被误报」。原因是本仓库的全部可信度都建立在
「CI 是唯一合并闸门」这一点上，闸门漏放的代价比误挡高一个量级。

因此大部分用例采用**变异注入**：取一份真实且当前合格的数据文件，
注入一种已知违规，再断言校验器必然报错。这比手写一个理想化的
最小 JSON 更接近真实风险——它同时也在验证真实数据结构仍被规则覆盖。

运行：
    python -m unittest discover -s tests -v
"""

import copy
import datetime
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "validate.py")
PROGRAMS = os.path.join(ROOT, "data", "programs")
FIXTURE_NAME = "nz-china-whv.json"
FIXTURE = os.path.join(PROGRAMS, FIXTURE_NAME)

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import validate  # noqa: E402


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

class FrozenDate(date):
    """替身类型：让 validate.date.today() 返回可控日期。"""

    _today = date(2026, 10, 30)

    @classmethod
    def today(cls):
        return cls._today


def load_fixture():
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)


def iter_verified_dates(doc):
    """遍历一份文档里所有 last_verified（顶层与 sources 内）。"""
    if isinstance(doc.get("last_verified"), str):
        yield "last_verified", doc["last_verified"]
    for i, src in enumerate(doc.get("sources") or []):
        if isinstance(src, dict) and isinstance(src.get("last_verified"), str):
            yield f"sources[{i}].last_verified", src["last_verified"]


class MutationBase(unittest.TestCase):
    """基于真实文档的变异测试基类。"""

    def setUp(self):
        self.doc = load_fixture()
        self._real_date = validate.date
        validate.date = FrozenDate
        FrozenDate._today = date(2026, 10, 30)

    def tearDown(self):
        validate.date = self._real_date

    def validate_doc(self, doc=None):
        rep = validate.Report()
        validate.validate_program(rep, FIXTURE_NAME, self.doc if doc is None else doc)
        return rep

    @staticmethod
    def errors(rep):
        return " | ".join(m for _, _, m in rep.errors)

    @staticmethod
    def warnings(rep):
        return " | ".join(m for _, _, m in rep.warnings)


# ---------------------------------------------------------------------------
# 1. 来源可信度分级 —— 整个项目的护城河所在
# ---------------------------------------------------------------------------

class TestSourceGrading(unittest.TestCase):
    A_URLS = [
        "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-462",
        "https://www.gov.uk/youth-mobility",
        "https://www.mofa.go.jp/j_info/visit/w_holiday/index.html",
        "https://j1visa.state.gov/programs/summer-work-travel/",
        "https://www.immigration.govt.nz/visas/china-working-holiday-visa/",
        "https://www.canada.ca/en/immigration-refugees-citizenship.html",
        "https://www.irishimmigration.ie/coming-to-work-in-ireland/",
        "https://www.ireland.ie/en/dfa/visas-for-ireland/working-holiday-authorisation/",
        "https://www.gesetze-im-internet.de/aufenthg_2004/__16e.html",
    ]
    B_URLS = ["https://www.iaeste.org/", "https://aiesec.org/global-talent"]
    D_URLS = [
        "https://baike.baidu.com/item/working-holiday",
        "https://zh.wikipedia.org/wiki/Working_holiday_visa",
        "https://www.zhihu.com/question/123456",
        "https://www.xiaohongshu.com/explore/abc",
        "https://medium.com/@someone/wow",
        "https://www.expatmoney.com/blog/x",
    ]

    def test_government_domains_are_grade_a(self):
        for url in self.A_URLS:
            self.assertEqual(validate.classify_source(url), "A", url)

    def test_project_org_domains_are_grade_b(self):
        for url in self.B_URLS:
            self.assertEqual(validate.classify_source(url), "B", url)

    def test_encyclopedia_and_selfmedia_are_grade_d(self):
        for url in self.D_URLS:
            self.assertEqual(validate.classify_source(url), "D", url)

    def test_unknown_host_is_grade_c_not_d(self):
        """未知域名默认为 C（可用但不足以单独支撑断言），不应直接判死。"""
        self.assertEqual(validate.classify_source("https://www.some-uni.edu.cn/x"), "C")

    def test_non_string_url_is_grade_d(self):
        for bad in (None, 123, [], {}):
            self.assertEqual(validate.classify_source(bad), "D")

    def test_forbidden_check_precedes_official_check(self):
        """违规判定必须优先于官方判定，否则白名单片段会被用来洗白 D 级来源。"""
        # 含 "gov" 片段但实际是百科
        self.assertEqual(validate.classify_source("https://baike.baidu.com/gov/x"), "D")


# ---------------------------------------------------------------------------
# 2. 来源质量违规注入
# ---------------------------------------------------------------------------

class TestSourceQualityViolations(MutationBase):

    def test_d_level_source_is_error(self):
        self.doc["sources"][0]["url"] = "https://baike.baidu.com/item/working-holiday"
        rep = self.validate_doc()
        self.assertFalse(rep.ok)
        self.assertIn("D 级", self.errors(rep))

    def test_vague_publisher_is_error(self):
        self.doc["sources"][0]["publisher"] = "公开资料"
        rep = self.validate_doc()
        self.assertFalse(rep.ok)
        self.assertIn("含糊", self.errors(rep))

    def test_vague_publisher_with_suffix_is_error(self):
        """「公开资料汇编」曾绕过精确匹配 —— 加两个字就不是含糊来源了？不可能。"""
        self.doc["sources"][0]["publisher"] = "公开资料汇编"
        rep = self.validate_doc()
        self.assertFalse(rep.ok)
        self.assertIn("含糊", self.errors(rep))

    def test_vague_publisher_variants_are_all_caught(self):
        for name in ("公开资料整理", "网络资料汇总", "综合合集", "Public Sources",
                     "public sources compilation", "未知 汇编"):
            self.doc["sources"][0]["publisher"] = name
            rep = self.validate_doc()
            self.assertFalse(rep.ok, f"{name!r} 未被判为含糊来源")

    def test_real_org_name_containing_vague_word_is_not_caught(self):
        """机构名里含「综合」「资料」不代表来源不明，不能误伤。"""
        for name in ("中国综合开发研究院", "国家统计局资料中心",
                     "Ministry of Foreign Affairs of Japan"):
            self.doc["sources"][0]["publisher"] = name
            rep = self.validate_doc()
            self.assertNotIn("含糊", self.errors(rep), f"{name!r} 被误判为含糊来源")

    def test_is_vague_publisher_helper(self):
        self.assertTrue(validate.is_vague_publisher("公开资料汇编"))
        self.assertTrue(validate.is_vague_publisher("  公开资料  "))
        self.assertFalse(validate.is_vague_publisher(""))
        self.assertFalse(validate.is_vague_publisher(None))
        self.assertFalse(validate.is_vague_publisher("IAESTE A.s.b.l."))

    def test_sources_without_any_official_source_is_error(self):
        """全部来源都只有 C 级 → 资格断言没有官方支撑，必须拦截。"""
        for src in self.doc["sources"]:
            src["url"] = "https://www.some-uni.edu.cn/international/"
            src["type"] = "secondary"
        rep = self.validate_doc()
        self.assertFalse(rep.ok)
        self.assertIn("缺少 A/B 级官方来源", self.errors(rep))

    def test_primary_on_c_level_domain_warns_but_passes(self):
        """C 级域名可作辅助来源，但不能自称 primary —— 告警，不阻断。"""
        self.doc["sources"][0]["url"] = "https://www.some-uni.edu.cn/international/"
        rep = self.validate_doc()
        self.assertTrue(rep.ok, self.errors(rep))
        self.assertIn("primary", self.warnings(rep))

    def test_empty_sources_is_error(self):
        """0 条来源必须拦截 —— 没有来源的资格断言等于没有溯源。"""
        self.doc["sources"] = []
        rep = self.validate_doc()
        self.assertFalse(rep.ok)
        self.assertIn("至少需要 1 条来源", self.errors(rep))


# ---------------------------------------------------------------------------
# 3. 结构完整性
# ---------------------------------------------------------------------------

class TestStructuralChecks(MutationBase):

    REQUIRED_TOP_LEVEL = [
        "schema_version", "program", "eligibility", "timeline",
        "documents", "steps", "sources", "last_verified",
    ]

    def test_each_required_top_level_key_is_enforced(self):
        for key in self.REQUIRED_TOP_LEVEL:
            with self.subTest(missing=key):
                doc = copy.deepcopy(self.doc)
                doc.pop(key)
                rep = self.validate_doc(doc)
                self.assertFalse(rep.ok, f"缺少 {key} 竟然通过了校验")
                self.assertIn("缺少必填字段", self.errors(rep))

    def test_null_required_field_is_error(self):
        self.doc["steps"] = None
        rep = self.validate_doc()
        self.assertFalse(rep.ok)
        self.assertIn("不得为 null", self.errors(rep))

    def test_schema_version_mismatch_is_error(self):
        self.doc["schema_version"] = "9.9.9"
        rep = self.validate_doc()
        self.assertIn("schema 版本不匹配", self.errors(rep))

    def test_bad_date_format_is_error(self):
        self.doc["last_verified"] = "2026/10/16"
        rep = self.validate_doc()
        self.assertIn("YYYY-MM-DD", self.errors(rep))

    def test_impossible_date_is_error(self):
        self.doc["last_verified"] = "2026-02-30"
        rep = self.validate_doc()
        self.assertIn("日期值无效", self.errors(rep))

    def test_non_http_url_is_error(self):
        self.doc["sources"][0]["url"] = "ftp://example.com/x"
        rep = self.validate_doc()
        self.assertIn("http:// 或 https://", self.errors(rep))

    def test_check_url_rejects_non_string(self):
        rep = validate.Report()
        validate.check_url(rep, "f.json", "f", None)
        self.assertFalse(rep.ok)

    def test_check_enum_rejects_unknown_value(self):
        rep = validate.Report()
        validate.check_enum(rep, "f.json", "f", "bogus", {"a", "b"})
        self.assertFalse(rep.ok)
        self.assertIn("非法枚举值", rep.errors[0][2])

    def test_check_required_reports_every_missing_key(self):
        rep = validate.Report()
        missing = validate.check_required(rep, "f.json", {}, ["a", "b", "c"])
        self.assertEqual(missing, ["a", "b", "c"])
        self.assertEqual(len(rep.errors), 3)


# ---------------------------------------------------------------------------
# 4. 时效判定 —— 含 2026-10 时区事故的回归
# ---------------------------------------------------------------------------

class TestStaleness(MutationBase):

    def check(self, recorded, today):
        FrozenDate._today = today
        rep = validate.Report()
        validate._check_staleness(rep, FIXTURE_NAME, "last_verified", recorded)
        return rep

    def test_fresh_date_passes_silently(self):
        rep = self.check("2026-10-16", date(2026, 10, 16))
        self.assertEqual(rep.errors, [])
        self.assertEqual(rep.warnings, [])

    def test_one_day_ahead_is_tolerated(self):
        """回归：GMT+8 深夜按本地日期记录 → CI（UTC）视角超前 1 天，不得判错。"""
        rep = self.check("2026-10-17", date(2026, 10, 16))
        self.assertEqual(rep.errors, [])

    def test_two_days_ahead_is_error(self):
        """容错不能被滥用：真正的「未来日期」仍必须拦下。"""
        rep = self.check("2026-10-18", date(2026, 10, 16))
        self.assertTrue(rep.errors)
        self.assertIn("在未来", rep.errors[0][2])

    def test_beyond_stale_window_warns_not_errors(self):
        rep = self.check("2026-01-01", date(2026, 10, 16))
        self.assertEqual(rep.errors, [])
        self.assertTrue(rep.warnings)
        self.assertIn(str(validate.STALE_DAYS), rep.warnings[0][2])

    def test_boundary_exactly_at_threshold_is_clean(self):
        today = date(2026, 10, 16)
        recorded = today - datetime.timedelta(days=validate.STALE_DAYS)
        rep = self.check(recorded.isoformat(), today)
        self.assertEqual((rep.errors, rep.warnings), ([], []))

    def test_unparseable_date_is_ignored_here(self):
        """格式错误由 check_date 负责报错，本函数不应重复报错或崩溃。"""
        rep = self.check("not-a-date", date(2026, 10, 16))
        self.assertEqual((rep.errors, rep.warnings), ([], []))


# ---------------------------------------------------------------------------
# 5. 跨字段一致性
# ---------------------------------------------------------------------------

class TestConsistency(MutationBase):

    def test_not_eligible_without_critical_risk_warns(self):
        self.doc["eligibility"]["passport_types"]["mainland_china"] = "not_eligible"
        self.doc["risks"] = [
            r for r in self.doc["risks"] if r.get("level") != "critical"
        ]
        rep = self.validate_doc()
        self.assertIn("critical 级别的风险说明", self.warnings(rep))

    def test_not_eligible_with_critical_risk_has_no_such_warning(self):
        self.doc["eligibility"]["passport_types"]["mainland_china"] = "not_eligible"
        rep = self.validate_doc()
        self.assertNotIn("critical 级别的风险说明", self.warnings(rep))


# ---------------------------------------------------------------------------
# 6. CLI / 退出码契约
# ---------------------------------------------------------------------------

class TestCliContract(unittest.TestCase):
    """退出码是 CI 唯一的判据，必须单独锁死。"""

    def run_cli(self, *args, cwd=ROOT):
        # 子进程 stdout 的编码跟随控制台代码页（中文 Windows 上是 GBK），
        # 这里却按 utf-8 解码：子进程一输出中文就 UnicodeDecodeError，
        # stdout 变成 None，下一行 proc.stdout + proc.stderr 直接 TypeError。
        # 显式给子进程 PYTHONIOENCODING=utf-8，让「按 utf-8 解码」这个前提成立。
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        return subprocess.run(
            [sys.executable, SCRIPT, *args],
            cwd=cwd, capture_output=True, text=True, encoding="utf-8", env=env,
        )

    def test_real_dataset_exits_zero(self):
        proc = self.run_cli()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class TestCliOnTempData(unittest.TestCase):
    """在临时数据目录上跑真正的 main()，覆盖加载与退出码路径。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.docs = os.path.join(self._tmp.name, "programs")
        os.makedirs(self.docs)
        self.base = load_fixture()

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, doc=None, raw=None):
        path = os.path.join(self.docs, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(raw if raw is not None else json.dumps(doc, ensure_ascii=False))

    def run_main(self, *args):
        """返回 (退出码, stdout)。PROGRAMS_DIR / SCHEMA_PATH / argv 全部临时替换。"""
        buf = io.StringIO()
        saved = (validate.PROGRAMS_DIR, validate.SCHEMA_PATH, list(sys.argv))
        validate.PROGRAMS_DIR = self.docs
        validate.SCHEMA_PATH = os.path.join(self._tmp.name, "schema.json")
        sys.argv = ["validate.py", *args]
        try:
            with redirect_stdout(buf):
                validate.main()
            code = 0
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
        finally:
            validate.PROGRAMS_DIR, validate.SCHEMA_PATH = saved[0], saved[1]
            sys.argv = saved[2]
        return code, buf.getvalue()

    def test_clean_dataset_exits_zero(self):
        self.write(FIXTURE_NAME, self.base)
        code, out = self.run_main()
        self.assertEqual(code, 0, out)

    def test_duplicate_program_id_is_error(self):
        self.write("a-program.json", copy.deepcopy(self.base))
        self.write("b-program.json", copy.deepcopy(self.base))
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("重复", out)

    def test_filename_id_mismatch_warns_but_passes(self):
        self.write("wrong-name.json", copy.deepcopy(self.base))
        code, out = self.run_main()
        self.assertEqual(code, 0, out)
        self.assertIn("文件名与 program.id 不一致", out)

    def test_empty_directory_is_error(self):
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("没有找到任何 .json", out)

    def test_broken_json_is_error(self):
        self.write("broken.json", raw="{ not valid json")
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("JSON 解析失败", out)

    def test_top_level_array_is_error(self):
        self.write("array.json", raw="[1, 2, 3]")
        code, out = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("顶层必须是 JSON 对象", out)

    def test_warning_alone_does_not_fail_without_strict(self):
        doc = copy.deepcopy(self.base)
        doc["sources"][0]["url"] = "https://www.some-uni.edu.cn/international/"
        self.write(FIXTURE_NAME, doc)
        code, out = self.run_main()
        self.assertEqual(code, 0, out)

    def test_strict_promotes_warnings_to_failure(self):
        """--strict 是「每周审计必须零告警」这一策略的开关，行为必须锁死。"""
        doc = copy.deepcopy(self.base)
        doc["sources"][0]["url"] = "https://www.some-uni.edu.cn/international/"
        self.write(FIXTURE_NAME, doc)
        code, out = self.run_main("--strict")
        self.assertEqual(code, 1, out)

    def _warning_only_doc(self):
        """只有告警、没有错误的数据：用于区分 --strict 的两条路径。"""
        doc = copy.deepcopy(self.base)
        doc["sources"][0]["url"] = "https://www.some-uni.edu.cn/international/"
        return doc

    def test_report_body_agrees_with_exit_code_under_strict(self):
        """报告正文的结论必须与退出码一致 —— 否则 CI 红了、日志却写「通过」。"""
        self.write(FIXTURE_NAME, self._warning_only_doc())
        code, out = self.run_main("--strict")
        self.assertEqual(code, 1)
        self.assertIn("结果: 失败", out)
        self.assertIn("--strict 已启用", out)

    def test_report_body_says_pass_without_strict(self):
        self.write(FIXTURE_NAME, self._warning_only_doc())
        code, out = self.run_main()
        self.assertEqual(code, 0, out)
        self.assertIn("结果: 通过", out)

    def test_json_report_exposes_strict_and_failed(self):
        self.write(FIXTURE_NAME, self._warning_only_doc())
        code, out = self.run_main("--json", "--strict")
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertTrue(payload["ok"], "本例不应产生 error")
        self.assertTrue(payload["strict"])
        self.assertTrue(payload["failed"], "有告警且启用 strict 时 failed 必须为真")


# ---------------------------------------------------------------------------
# 7. 链接收集范围（--check-links 到底查了哪些 URL）
# ---------------------------------------------------------------------------

class TestCollectUrls(unittest.TestCase):
    """collect_urls 必须覆盖 program.official_url、sources[].url 和 steps[].official_link。

    steps[].official_link 曾被整类漏掉：11 个项目共 12 条步骤链接（各使领馆预约页、
    体检页、材料上传入口）从未进入过存活检查。这个用例把覆盖范围钉住，防止回退。
    """

    def setUp(self):
        self.doc = load_fixture()
        self.rep = validate.Report()

    def fields(self):
        return [f for _, _, f in validate.collect_urls(self.rep, self.doc, FIXTURE_NAME)]

    def test_official_url_is_collected(self):
        self.assertIn("program.official_url", self.fields())

    def test_every_source_url_is_collected(self):
        got = self.fields()
        for i in range(len(self.doc["sources"])):
            self.assertIn(f"sources[{i}].url", got)

    def test_every_step_link_is_collected(self):
        got = self.fields()
        for i, step in enumerate(self.doc["steps"]):
            if step.get("official_link"):
                self.assertIn(f"steps[{i}].official_link", got)

    def test_step_without_link_is_skipped(self):
        for step in self.doc["steps"]:
            step.pop("official_link", None)
        got = self.fields()
        self.assertFalse([f for f in got if f.startswith("steps[")], got)

    def test_null_step_link_is_skipped(self):
        self.doc["steps"][0]["official_link"] = None
        self.assertNotIn("steps[0].official_link", self.fields())

    def test_missing_steps_key_is_not_a_crash(self):
        self.doc.pop("steps", None)
        self.doc.pop("sources", None)
        self.assertEqual(self.fields(), ["program.official_url"])

    def test_program_id_falls_back_to_filename(self):
        self.doc["program"].pop("id")
        urls = validate.collect_urls(self.rep, self.doc, "some-file.json")
        self.assertTrue(urls)
        self.assertEqual({p for p, _, _ in urls}, {"some-file"})

    def test_urls_are_three_tuples(self):
        for item in validate.collect_urls(self.rep, self.doc, FIXTURE_NAME):
            self.assertEqual(len(item), 3, item)

    def test_real_dataset_has_step_links_in_scope(self):
        """真实数据里必须确实存在 steps 链接，否则本组用例会静默失效。"""
        found = 0
        for name in sorted(os.listdir(PROGRAMS)):
            if not name.endswith(".json"):
                continue
            with open(os.path.join(PROGRAMS, name), encoding="utf-8") as fh:
                doc = json.load(fh)
            found += sum(1 for _, _, f in validate.collect_urls(validate.Report(), doc, name)
                         if f.startswith("steps["))
        self.assertGreaterEqual(found, 10, f"只在真实数据里找到 {found} 条 steps 链接")


# ---------------------------------------------------------------------------
# 7. 链接检查的行为约定（不发真实请求，用替身拦截 opener）
# ---------------------------------------------------------------------------

class _FakeResp:
    def __init__(self, code):
        self._code = code

    def getcode(self):
        return self._code

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeHTTPError(urllib.error.HTTPError):
    """构造一个「服务器返回错误码」的替身。

    HTTPError 继承自 addinfourl，gc 时会因为 fp 未显式关闭而打 ResourceWarning。
    这些对象是为测试捏造的，没有真实连接要关，所以把 __del__ 换成空操作；
    真实网络路径上 HTTPError 由 urllib 自己收尾，不受这里影响。
    """

    def __init__(self, url, code, msg):
        super().__init__(url, code, msg, {}, io.BytesIO(b""))

    def close(self):
        pass

    def __del__(self):
        pass


class TestCheckLinkBehaviour(unittest.TestCase):
    """check_link 的两条修正必须钉住，否则假告警会悄悄长回来。

    1. UA 停在 Chrome/120 时，iaeste.de 与 irishimmigration.ie 的 WAF 直接 403；
       这两个域名本身没有任何问题，纯粹是客户端版本被判过期。
    2. overseas.mofa.go.kr 先下发 cookie 再 307 回自身，不带 cookie 会无限重定向。
       检查器必须像浏览器一样保存 cookie。
    """

    def setUp(self):
        self._real = urllib.request.build_opener
        self.seen = []
        self.handlers = []
        self.behaviour = lambda req: 200

    def tearDown(self):
        urllib.request.build_opener = self._real

    def install(self):
        seen, handlers = self.seen, self.handlers
        behaviour = self.behaviour

        class FakeOpener:
            def open(self, req, timeout=None):
                seen.append(req)
                out = behaviour(req)
                if isinstance(out, BaseException):
                    raise out
                return _FakeResp(out)

        def fake_build(*hs, **kw):
            handlers.extend(type(h).__name__ for h in hs)
            return FakeOpener()

        urllib.request.build_opener = fake_build

    def run_check(self, behaviour, url="https://example.org/"):
        self.behaviour = behaviour
        self.install()
        return validate.check_link("p", url, timeout=1)

    def test_user_agent_is_not_pinned_to_an_old_chrome(self):
        self.run_check(lambda req: 200)
        ua = self.seen[0].get_header("User-agent") or ""
        major = re.search(r"Chrome/(\d+)", ua)
        self.assertIsNotNone(major, ua)
        self.assertGreaterEqual(
            int(major.group(1)), 130,
            "UA 又退回旧版本了，会让 iaeste.de / irishimmigration.ie 假 403",
        )

    def test_cookie_jar_is_attached_to_the_opener(self):
        self.run_check(lambda req: 200)
        self.assertIn(
            "HTTPCookieProcessor", " ".join(self.handlers),
            "opener 没挂 cookie jar，overseas.mofa.go.kr 会 307 无限重定向",
        )

    def test_404_and_410_are_failures(self):
        for code in (404, 410):
            status = self.run_check(
                lambda req, c=code: _FakeHTTPError(req.full_url, c, "gone")
            )[2]
            self.assertEqual(status, "fail", f"HTTP {code} 必须判为失效")

    def test_403_is_warn_not_fail(self):
        status = self.run_check(lambda req: _FakeHTTPError(req.full_url, 403, "no"))[2]
        self.assertEqual(status, "warn", "反爬 403 不等于链接失效")

    def test_timeout_is_warn(self):
        status = self.run_check(lambda req: urllib.error.URLError("timed out"))[2]
        self.assertEqual(status, "warn")

    def test_connection_reset_is_warn(self):
        status = self.run_check(lambda req: ConnectionResetError(10054, "reset"))[2]
        self.assertEqual(status, "warn")

    def test_2xx_is_ok(self):
        self.assertEqual(self.run_check(lambda req: 200)[2], "ok")

    def test_detail_carries_the_status_code(self):
        detail = self.run_check(lambda req: 200)[3]
        self.assertIn("200", detail)


# ---------------------------------------------------------------------------
# 8. 真实数据集的新鲜度（每次 push 都会跑，比每周定时任务更早发现问题）
# ---------------------------------------------------------------------------

class TestRealDataFreshness(unittest.TestCase):

    def test_every_last_verified_is_within_window_and_not_in_future(self):
        today = date.today()
        problems = []
        checked = 0
        for name in sorted(os.listdir(PROGRAMS)):
            if not name.endswith(".json"):
                continue
            with open(os.path.join(PROGRAMS, name), encoding="utf-8") as fh:
                doc = json.load(fh)
            for field, value in iter_verified_dates(doc):
                checked += 1
                age = (today - datetime.date.fromisoformat(value)).days
                if age > validate.STALE_DAYS:
                    problems.append(f"{name} {field} 已 {age} 天未核实")
                elif age < -validate.FUTURE_TOLERANCE_DAYS:
                    problems.append(f"{name} {field} 是未来日期（超前 {-age} 天）")
        self.assertGreater(checked, 0, "没有扫描到任何 last_verified，测试本身可能失效了")
        self.assertEqual(
            problems, [],
            "数据需要重新核实：\n" + "\n".join(problems),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
