#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
overseas-program-dataset 数据校验脚本

用途：
    校验 data/programs/*.json 是否符合 data/schema.json 的结构要求，
    并可选检查所有官方链接是否存活。

设计原则：
    1. 零第三方依赖（只用标准库），确保任何环境可运行
    2. 错误信息清晰可操作（指出文件、字段、原因）
    3. 退出码可用于 CI：0 = 全部通过，1 = 存在错误

用法：
    python scripts/validate.py                  # 仅结构校验（离线）
    python scripts/validate.py --check-links    # 附加链接存活检查
    python scripts/validate.py --json           # 以 JSON 输出报告
    python scripts/validate.py --strict         # 警告也视为失败
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
PROGRAMS_DIR = os.path.join(DATA_DIR, "programs")
SCHEMA_PATH = os.path.join(DATA_DIR, "schema.json")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[a-z0-9-]+$")
COUNTRY_CODE_RE = re.compile(r"^[A-Z]{2}$")
URL_RE = re.compile(r"^https?://")

# 来源新鲜度阈值（天）——超过则告警
STALE_DAYS = 180

VALID_REGIONS = {
    "oceania", "asia", "europe", "north_america",
    "south_america", "africa", "global",
}

VALID_PROGRAM_TYPES = {
    "working_holiday", "paid_internship",
    "internship_visa", "cultural_exchange", "short_term_work",
}

VALID_MECHANISMS = {
    "ballot", "first_come_first_served",
    "rolling", "appointment", "annual_negotiation",
}

VALID_ELIGIBILITY_STATUS = {
    "eligible", "not_eligible", "conditional", "unknown",
}

VALID_EDUCATION_LEVELS = {
    "high_school", "vocational", "bachelor_in_progress",
    "bachelor_completed", "master", "any",
}

VALID_CURRENCIES = {
    "AUD", "NZD", "JPY", "KRW", "USD", "EUR", "GBP",
    "CNY", "HKD", "TWD", "SGD", "PLN", "DKK", "SEK", "NOK",
    "CAD", "CHF", "THB", "MYR", "VND", "IDR", "ILS", "TRY",
}

VALID_LANGUAGE_TESTS = {
    "IELTS", "TOEFL_iBT", "PTE", "Cambridge", "CEFR", "OET", "none",
}

VALID_WINDOW_STATUS = {"upcoming", "open", "closed", "unknown"}

VALID_REQUIREMENT_TYPES = {
    "health_check", "criminal_record", "insurance", "no_dependents",
    "return_ticket", "government_support_letter", "enrollment_proof",
    "internship_contract", "blocked_account", "no_prior_visa",
    "residency_requirement",
}

VALID_RISK_LEVELS = {"info", "warning", "critical"}

VALID_TAGS = {
    "no_quota_cap", "ballot_required", "first_come_first_served", "rolling",
    "once_in_lifetime", "renewable", "requires_agency", "no_agency_needed",
    "farm_work_available", "high_wage", "low_cost", "requires_degree",
    "stem_friendly", "high_demand",
    "cultural_exchange", "engineering_friendly", "paid", "unpaid",
    "english_required", "no_english_required", "residency_required",
}


# ---------------------------------------------------------------------------
# 报告容器
# ---------------------------------------------------------------------------

class Report:
    def __init__(self):
        self.errors = []      # (file, field, message)
        self.warnings = []    # (file, field, message)
        self.info = []        # (file, field, message)
        self.link_results = []  # (program_id, url, ok, detail)
        self.files_checked = 0
        self.programs_checked = 0

    def error(self, f, field, msg):
        self.errors.append((f, field, msg))

    def warn(self, f, field, msg):
        self.warnings.append((f, field, msg))

    def note(self, f, field, msg):
        self.info.append((f, field, msg))

    @property
    def ok(self):
        return len(self.errors) == 0


# ---------------------------------------------------------------------------
# 基础校验器
# ---------------------------------------------------------------------------

def check_date(rep, fname, field, value):
    if not isinstance(value, str):
        rep.error(fname, field, f"日期必须是字符串，实际为 {type(value).__name__}")
        return False
    if not DATE_RE.match(value):
        rep.error(fname, field, f"日期格式必须为 YYYY-MM-DD，实际为 '{value}'")
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        rep.error(fname, field, f"日期值无效：'{value}'")
        return False
    return True


def check_url(rep, fname, field, value):
    if not isinstance(value, str):
        rep.error(fname, field, f"URL 必须是字符串，实际为 {type(value).__name__}")
        return False
    if not URL_RE.match(value):
        rep.error(fname, field, f"URL 必须以 http:// 或 https:// 开头，实际为 '{value}'")
        return False
    return True


def check_enum(rep, fname, field, value, allowed):
    if value not in allowed:
        rep.error(
            fname, field,
            f"非法枚举值 '{value}'，允许值：{sorted(allowed)}"
        )
        return False
    return True


def check_required(rep, fname, obj, keys, prefix=""):
    """检查 obj 是否包含全部 keys，返回缺失列表"""
    missing = []
    for k in keys:
        if k not in obj:
            missing.append(f"{prefix}{k}")
            rep.error(fname, f"{prefix}{k}", "缺少必填字段")
        elif obj[k] is None and k not in ("quota", "open_date", "close_date"):
            rep.error(fname, f"{prefix}{k}", "字段值不得为 null")
    return missing


# ---------------------------------------------------------------------------
# 主校验逻辑
# ---------------------------------------------------------------------------

def validate_program(rep, fname, doc):
    """校验单个项目文件"""
    p = fname

    # --- 顶层必填 ---
    top_required = [
        "schema_version", "program", "eligibility", "timeline",
        "documents", "steps", "sources", "last_verified",
    ]
    check_required(rep, p, doc, top_required)

    if "schema_version" in doc and doc["schema_version"] != "0.1.0":
        rep.error(p, "schema_version",
                  f"schema 版本不匹配：期望 '0.1.0'，实际 '{doc['schema_version']}'")

    if "last_verified" in doc:
        check_date(rep, p, "last_verified", doc["last_verified"])
        _check_staleness(rep, p, "last_verified", doc["last_verified"])

    # --- program ---
    prog = doc.get("program", {})
    if not isinstance(prog, dict):
        rep.error(p, "program", "必须是对象")
    else:
        req = ["id", "name", "name_en", "country", "country_code",
               "region", "program_type", "official_url"]
        check_required(rep, p, prog, req, prefix="program.")

        pid = prog.get("id", "?")
        if "id" in prog and not ID_RE.match(str(prog["id"])):
            rep.error(p, "program.id",
                      f"必须为小写连字符格式（如 au-462-work-holiday），实际 '{prog['id']}'")

        if "country_code" in prog and not COUNTRY_CODE_RE.match(str(prog["country_code"])):
            rep.error(p, "program.country_code",
                      f"必须为 2 位大写国家代码，实际 '{prog['country_code']}'")

        if "region" in prog:
            check_enum(rep, p, "program.region", prog["region"], VALID_REGIONS)

        if "program_type" in prog:
            check_enum(rep, p, "program.program_type", prog["program_type"],
                       VALID_PROGRAM_TYPES)

        if "official_url" in prog:
            check_url(rep, p, "program.official_url", prog["official_url"])

        if "tags" in prog:
            if not isinstance(prog["tags"], list):
                rep.error(p, "program.tags", "必须是数组")
            else:
                for t in prog["tags"]:
                    if t not in VALID_TAGS:
                        rep.error(p, "program.tags", f"非法标签 '{t}'")

        if "summary" in prog and len(str(prog["summary"])) > 500:
            rep.warn(p, "program.summary",
                     f"简介过长（{len(str(prog['summary']))} 字符），建议 200 字以内")

    # --- eligibility ---
    elig = doc.get("eligibility", {})
    if not isinstance(elig, dict):
        rep.error(p, "eligibility", "必须是对象")
    else:
        req = ["passport_types", "age", "education", "language",
               "funds", "other_requirements"]
        check_required(rep, p, elig, req, prefix="eligibility.")

        # 护照类型 —— 最关键字段
        pt = elig.get("passport_types", {})
        if isinstance(pt, dict):
            if "mainland_china" not in pt:
                rep.error(p, "eligibility.passport_types",
                          "必须包含 mainland_china 字段（这是本数据集的核心字段）")
            for k in ("mainland_china", "hong_kong_china", "taiwan_china"):
                if k in pt:
                    check_enum(rep, p, f"eligibility.passport_types.{k}",
                               pt[k], VALID_ELIGIBILITY_STATUS)
        elif "passport_types" in elig:
            rep.error(p, "eligibility.passport_types", "必须是对象")

        # 年龄
        age = elig.get("age", {})
        if isinstance(age, dict):
            check_required(rep, p, age, ["min", "max", "note"], prefix="eligibility.age.")
            if "min" in age and "max" in age:
                try:
                    if int(age["min"]) > int(age["max"]):
                        rep.error(p, "eligibility.age",
                                  f"min({age['min']}) 不得大于 max({age['max']})")
                except (TypeError, ValueError):
                    rep.error(p, "eligibility.age", "min/max 必须是整数")

        # 学历
        edu = elig.get("education", {})
        if isinstance(edu, dict):
            check_required(rep, p, edu, ["minimum_level", "note"],
                           prefix="eligibility.education.")
            if "minimum_level" in edu:
                check_enum(rep, p, "eligibility.education.minimum_level",
                           edu["minimum_level"], VALID_EDUCATION_LEVELS)

        # 语言
        lang = elig.get("language", {})
        if isinstance(lang, dict):
            check_required(rep, p, lang, ["required", "note"],
                           prefix="eligibility.language.")
            if not isinstance(lang.get("required"), bool):
                rep.error(p, "eligibility.language.required", "必须是布尔值")
            for i, t in enumerate(lang.get("tests", [])):
                if not isinstance(t, dict):
                    rep.error(p, f"eligibility.language.tests[{i}]", "必须是对象")
                    continue
                check_required(rep, p, t, ["test", "min_score", "validity_months"],
                               prefix=f"eligibility.language.tests[{i}].")
                if "test" in t and t["test"] not in VALID_LANGUAGE_TESTS:
                    rep.error(p, f"eligibility.language.tests[{i}].test",
                              f"非法考试类型 '{t['test']}'")

        # 资金
        funds = elig.get("funds", {})
        if isinstance(funds, dict):
            check_required(rep, p, funds, ["required", "note"],
                           prefix="eligibility.funds.")
            if not isinstance(funds.get("required"), bool):
                rep.error(p, "eligibility.funds.required", "必须是布尔值")
            amt = funds.get("amount")
            if isinstance(amt, dict):
                _check_money(rep, p, "eligibility.funds.amount", amt)

        # 其他要求
        others = elig.get("other_requirements", [])
        if not isinstance(others, list):
            rep.error(p, "eligibility.other_requirements", "必须是数组")
        else:
            for i, o in enumerate(others):
                if not isinstance(o, dict):
                    rep.error(p, f"eligibility.other_requirements[{i}]", "必须是对象")
                    continue
                check_required(rep, p, o, ["type", "required", "note"],
                               prefix=f"eligibility.other_requirements[{i}].")
                if "type" in o and o["type"] not in VALID_REQUIREMENT_TYPES:
                    rep.error(p, f"eligibility.other_requirements[{i}].type",
                              f"非法类型 '{o['type']}'，允许值：{sorted(VALID_REQUIREMENT_TYPES)}")

    # --- timeline ---
    tl = doc.get("timeline", {})
    if not isinstance(tl, dict):
        rep.error(p, "timeline", "必须是对象")
    else:
        check_required(rep, p, tl, ["mechanism", "quota", "windows"],
                       prefix="timeline.")
        if "mechanism" in tl:
            check_enum(rep, p, "timeline.mechanism", tl["mechanism"], VALID_MECHANISMS)

        if "quota" in tl:
            q = tl["quota"]
            if q is not None and not isinstance(q, int):
                rep.error(p, "timeline.quota", "必须为整数或 null")

        windows = tl.get("windows", [])
        if not isinstance(windows, list):
            rep.error(p, "timeline.windows", "必须是数组")
        elif len(windows) == 0:
            rep.error(p, "timeline.windows", "至少需要 1 个时间窗口记录")
        else:
            years_seen = set()
            for i, w in enumerate(windows):
                if not isinstance(w, dict):
                    rep.error(p, f"timeline.windows[{i}]", "必须是对象")
                    continue
                check_required(rep, p, w, ["year", "status", "note"],
                               prefix=f"timeline.windows[{i}].")
                if "status" in w:
                    check_enum(rep, p, f"timeline.windows[{i}].status",
                               w["status"], VALID_WINDOW_STATUS)
                for dk in ("open_date", "close_date", "draw_period_end"):
                    if dk in w and w[dk] is not None:
                        check_date(rep, p, f"timeline.windows[{i}].{dk}", w[dk])
                y = w.get("year")
                if isinstance(y, int):
                    if y in years_seen:
                        rep.warn(p, f"timeline.windows[{i}]",
                                 f"年份 {y} 重复出现，请确认是否有意为之")
                    years_seen.add(y)

        for i, fee in enumerate(tl.get("fees", [])):
            if not isinstance(fee, dict):
                rep.error(p, f"timeline.fees[{i}]", "必须是对象")
                continue
            check_required(rep, p, fee, ["item", "amount"],
                           prefix=f"timeline.fees[{i}].")
            if isinstance(fee.get("amount"), dict):
                _check_money(rep, p, f"timeline.fees[{i}].amount", fee["amount"])

    # --- documents ---
    docs = doc.get("documents", [])
    if not isinstance(docs, list):
        rep.error(p, "documents", "必须是数组")
    elif len(docs) == 0:
        rep.error(p, "documents", "至少需要 1 项材料")
    else:
        for i, d in enumerate(docs):
            if not isinstance(d, dict):
                rep.error(p, f"documents[{i}]", "必须是对象")
                continue
            check_required(rep, p, d, ["name", "required"], prefix=f"documents[{i}].")
            if not isinstance(d.get("required"), bool):
                rep.error(p, f"documents[{i}].required", "必须是布尔值")

    # --- steps ---
    steps = doc.get("steps", [])
    if not isinstance(steps, list):
        rep.error(p, "steps", "必须是数组")
    elif len(steps) == 0:
        rep.error(p, "steps", "至少需要 1 个步骤")
    else:
        numbers = []
        for i, s in enumerate(steps):
            if not isinstance(s, dict):
                rep.error(p, f"steps[{i}]", "必须是对象")
                continue
            check_required(rep, p, s, ["step_no", "title", "description"],
                           prefix=f"steps[{i}].")
            if "step_no" in s:
                if not isinstance(s["step_no"], int):
                    rep.error(p, f"steps[{i}].step_no", "必须是整数")
                else:
                    numbers.append(s["step_no"])
                if "official_link" in s and s["official_link"] is not None:
                    check_url(rep, p, f"steps[{i}].official_link", s["official_link"])
        if numbers and numbers != list(range(1, len(numbers) + 1)):
            rep.error(p, "steps",
                      f"step_no 必须从 1 连续递增，实际：{numbers}")

    # --- work_conditions ---
    wc = doc.get("work_conditions")
    if wc is not None:
        if not isinstance(wc, dict):
            rep.error(p, "work_conditions", "必须是对象")
        elif "restricted_occupations" in wc and not isinstance(wc["restricted_occupations"], list):
            rep.error(p, "work_conditions.restricted_occupations", "必须是数组")

    # --- risks ---
    risks = doc.get("risks")
    if risks is not None:
        if not isinstance(risks, list):
            rep.error(p, "risks", "必须是数组")
        else:
            for i, r in enumerate(risks):
                if not isinstance(r, dict):
                    rep.error(p, f"risks[{i}]", "必须是对象")
                    continue
                check_required(rep, p, r, ["level", "description"], prefix=f"risks[{i}].")
                if "level" in r:
                    check_enum(rep, p, f"risks[{i}].level", r["level"], VALID_RISK_LEVELS)

    # --- sources ---
    srcs = doc.get("sources", [])
    if not isinstance(srcs, list):
        rep.error(p, "sources", "必须是数组")
    elif len(srcs) == 0:
        rep.error(p, "sources", "至少需要 1 条来源（这是本数据集的核心要求）")
    else:
        has_primary = False
        for i, s in enumerate(srcs):
            if not isinstance(s, dict):
                rep.error(p, f"sources[{i}]", "必须是对象")
                continue
            check_required(rep, p, s, ["type", "name", "url", "last_verified"],
                           prefix=f"sources[{i}].")
            if s.get("type") == "primary":
                has_primary = True
            elif s.get("type") == "secondary":
                pass
            elif "type" in s:
                rep.error(p, f"sources[{i}].type",
                          f"必须是 'primary' 或 'secondary'，实际 '{s['type']}'")

            if "url" in s:
                check_url(rep, p, f"sources[{i}].url", s["url"])
            if "last_verified" in s:
                check_date(rep, p, f"sources[{i}].last_verified", s["last_verified"])

        if not has_primary:
            rep.error(p, "sources",
                      "至少需要 1 条 primary（官方一手）来源。二手来源不能作为唯一依据。")

    # --- 跨字段一致性 ---
    _check_consistency(rep, p, doc)


def _check_money(rep, fname, field, amt):
    if "local_amount" not in amt:
        rep.error(fname, field, "缺少 local_amount")
    elif not isinstance(amt["local_amount"], (int, float)):
        rep.error(fname, f"{field}.local_amount", "必须是数字")
    elif amt["local_amount"] < 0:
        rep.error(fname, f"{field}.local_amount", "不得为负数")

    if "currency" not in amt:
        rep.error(fname, field, "缺少 currency")
    elif amt["currency"] not in VALID_CURRENCIES:
        rep.error(fname, f"{field}.currency",
                  f"非法币种 '{amt['currency']}'，允许值：{sorted(VALID_CURRENCIES)}")

    if "cny_estimate" in amt and not isinstance(amt["cny_estimate"], (int, float)):
        rep.error(fname, f"{field}.cny_estimate", "必须是数字")


def _check_staleness(rep, fname, field, date_str):
    """检查数据是否过旧"""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return
    age = (date.today() - d).days
    if age > STALE_DAYS:
        rep.warn(fname, field,
                 f"数据距今已 {age} 天（>{STALE_DAYS} 天），建议重新核实官方来源")
    elif age < 0:
        rep.error(fname, field, f"核实日期在未来（{date_str}），可能填写错误")


def _check_consistency(rep, fname, doc):
    """跨字段一致性检查"""
    elig = doc.get("eligibility", {})
    pt = elig.get("passport_types", {})
    prog = doc.get("program", {})
    pid = prog.get("id", "?")

    if not isinstance(pt, dict):
        return

    mainland = pt.get("mainland_china")

    # 一致性 1：标记为 not_eligible 的项目，应有 critical 风险说明
    if mainland == "not_eligible":
        risks = doc.get("risks", [])
        has_critical = any(
            isinstance(r, dict) and r.get("level") == "critical" for r in risks
        )
        if not has_critical:
            rep.warn(fname, "risks",
                     f"项目 {pid} 对大陆护照标记为 not_eligible，"
                     f"但缺少 critical 级别的风险说明（建议说明为何不可申请）")

    # 一致性 2：标记为 eligible 的项目应有配额机制说明
    if mainland == "eligible":
        tl = doc.get("timeline", {})
        if isinstance(tl, dict) and "quota" not in tl:
            rep.warn(fname, "timeline.quota",
                     f"项目 {pid} 对大陆护照开放，但未说明配额（quota）")

    # 一致性 3：quota 为 null 时应有 quota_note 解释
    tl = doc.get("timeline", {})
    if isinstance(tl, dict):
        if tl.get("quota") is None and not tl.get("quota_note"):
            rep.warn(fname, "timeline.quota_note",
                     "quota 为 null 但缺少 quota_note 说明（无名额限制？不在协议内？）")


# ---------------------------------------------------------------------------
# 链接检查
# ---------------------------------------------------------------------------

def check_link(program_id, url, timeout=15, insecure_fallback=True):
    """检查单个 URL 是否可访问。

    返回 (program_id, url, status, detail)
    status 取值：
        "ok"        —— 可访问
        "warn"      —— 结果不确定（反爬、证书、超时），需人工确认
        "fail"      —— 明确失效（如 404、410）

    设计说明：
        官方签证/移民网站常有反爬机制（403/429）、或使用中间证书链导致
        部分网络环境下证书校验失败、或对特定地区限速。这些都不等于链接失效。
        因此本函数将"不确定"与"明确失效"分开处理，避免 CI 误报。
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
    }

    def _attempt(context):
        req = urllib.request.Request(url, method="GET", headers=headers)
        return urllib.request.urlopen(req, timeout=timeout, context=context)

    # 第一次：正常校验证书
    try:
        with _attempt(None) as resp:
            code = resp.getcode()
            if 200 <= code < 400:
                return (program_id, url, "ok", f"HTTP {code}")
            return (program_id, url, "warn", f"HTTP {code}")
    except urllib.error.HTTPError as e:
        if e.code in (403, 405, 429, 503):
            return (program_id, url, "warn",
                    f"HTTP {e.code}（反爬/限速，非失效）")
        if e.code in (404, 410):
            return (program_id, url, "fail", f"HTTP {e.code} 链接已失效")
        return (program_id, url, "warn", f"HTTP {e.code}")
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if "CERTIFICATE_VERIFY_FAILED" in reason:
            # 证书链问题：尝试跳过校验重试
            if insecure_fallback:
                try:
                    import ssl as _ssl
                    ctx = _ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = _ssl.CERT_NONE
                    with _attempt(ctx) as resp:
                        code = resp.getcode()
                        if 200 <= code < 400:
                            return (program_id, url, "warn",
                                    f"HTTP {code}（证书链不完整，链接本身可用）")
                        return (program_id, url, "warn", f"HTTP {code}")
                except Exception:  # noqa: BLE001
                    pass
            return (program_id, url, "warn",
                    "SSL 证书校验失败（可能为本地证书库缺失或网络限制）")
        if "timed out" in reason.lower() or "timeout" in reason.lower():
            return (program_id, url, "warn", "连接超时（可能为网络限制/目标站限速）")
        return (program_id, url, "warn", f"连接失败：{reason}")
    except Exception as e:  # noqa: BLE001
        return (program_id, url, "warn", f"异常：{type(e).__name__}: {e}")


def collect_urls(rep, doc, fname):
    urls = []
    prog = doc.get("program", {})
    pid = prog.get("id", os.path.splitext(fname)[0])
    if isinstance(prog, dict) and prog.get("official_url"):
        urls.append((pid, prog["official_url"]))
    for s in doc.get("sources", []):
        if isinstance(s, dict) and s.get("url"):
            urls.append((pid, s["url"]))
    return urls


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------

def print_report(rep, as_json=False):
    if as_json:
        out = {
            "ok": rep.ok,
            "files_checked": rep.files_checked,
            "programs_checked": rep.programs_checked,
            "summary": {
                "errors": len(rep.errors),
                "warnings": len(rep.warnings),
                "info": len(rep.info),
            },
            "errors": [
                {"file": f, "field": fld, "message": m}
                for f, fld, m in rep.errors
            ],
            "warnings": [
                {"file": f, "field": fld, "message": m}
                for f, fld, m in rep.warnings
            ],
            "info": [
                {"file": f, "field": fld, "message": m}
                for f, fld, m in rep.info
            ],
            "links": [
                {"program": p, "url": u, "status": st, "detail": d}
                for p, u, st, d in rep.link_results
            ],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    line = "=" * 72
    print(line)
    print("  overseas-program-dataset  数据校验报告")
    print(line)
    print()

    if rep.errors:
        print(f"[错误] {len(rep.errors)} 项 —— 必须修复")
        print("-" * 72)
        for f, fld, m in rep.errors:
            print(f"  {f}")
            print(f"    字段: {fld}")
            print(f"    问题: {m}")
        print()

    if rep.warnings:
        print(f"[警告] {len(rep.warnings)} 项 —— 建议修复")
        print("-" * 72)
        for f, fld, m in rep.warnings:
            print(f"  {f}  [{fld}]")
            print(f"    {m}")
        print()

    if rep.info:
        print(f"[提示] {len(rep.info)} 项")
        print("-" * 72)
        for f, fld, m in rep.info:
            print(f"  {f}  [{fld}]  {m}")
        print()

    if rep.link_results:
        oks = [r for r in rep.link_results if r[2] == "ok"]
        warns = [r for r in rep.link_results if r[2] == "warn"]
        fails = [r for r in rep.link_results if r[2] == "fail"]
        print(f"[链接检查] 共 {len(rep.link_results)} 条 —— "
              f"正常 {len(oks)} / 待确认 {len(warns)} / 失效 {len(fails)}")
        print("-" * 72)
        for p, u, st, d in rep.link_results:
            mark = {"ok": "OK  ", "warn": "WARN", "fail": "FAIL"}[st]
            print(f"  [{mark}] {p}")
            print(f"         {u}")
            print(f"         {d}")
        print()
        if warns:
            print("  说明：标记为 WARN 的链接多为反爬、证书链或网络限制所致，")
            print("        不等于链接失效。建议在能正常访问该站点的网络环境下人工确认。")
            print()
        if fails:
            rep.error("links", "-", f"{len(fails)} 条官方链接已明确失效，请更新")
        print()

    print(line)
    status = "通过" if rep.ok else "失败"
    print(f"  结果: {status}")
    print(f"  检查文件: {rep.files_checked} 个")
    print(f"  检查项目: {rep.programs_checked} 个")
    print(f"  错误 {len(rep.errors)} / 警告 {len(rep.warnings)}")
    print(line)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="校验 overseas-program-dataset 的数据文件"
    )
    parser.add_argument("--check-links", action="store_true",
                        help="检查所有官方链接是否存活（需要网络）")
    parser.add_argument("--json", action="store_true",
                        help="以 JSON 格式输出报告")
    parser.add_argument("--strict", action="store_true",
                        help="警告也视为失败（退出码 1）")
    parser.add_argument("--timeout", type=int, default=15,
                        help="链接检查超时秒数（默认 15）")
    args = parser.parse_args()

    rep = Report()

    # 检查目录存在
    if not os.path.isdir(PROGRAMS_DIR):
        rep.error("data/programs/", "-", f"目录不存在：{PROGRAMS_DIR}")
        print_report(rep, args.json)
        sys.exit(1)

    # 检查 schema 本身可解析
    if os.path.isfile(SCHEMA_PATH):
        try:
            with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
                json.load(fh)
            rep.files_checked += 1
        except json.JSONDecodeError as e:
            rep.error("data/schema.json", "-", f"JSON 解析失败：{e}")
    else:
        rep.warn("data/schema.json", "-", "schema 文件不存在")

    # 遍历项目文件
    files = sorted(
        f for f in os.listdir(PROGRAMS_DIR) if f.endswith(".json")
    )
    if not files:
        rep.error("data/programs/", "-", "目录下没有找到任何 .json 文件")

    id_seen = {}
    all_urls = []

    for fname in files:
        path = os.path.join(PROGRAMS_DIR, fname)
        rep.files_checked += 1

        try:
            with open(path, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except json.JSONDecodeError as e:
            rep.error(fname, "-", f"JSON 解析失败：{e.msg}（行 {e.lineno} 列 {e.colno}）")
            continue
        except UnicodeDecodeError:
            rep.error(fname, "-", "文件编码错误，必须为 UTF-8")
            continue

        if not isinstance(doc, dict):
            rep.error(fname, "-", "顶层必须是 JSON 对象")
            continue

        rep.programs_checked += 1
        validate_program(rep, fname, doc)

        # 检查 id 唯一性
        pid = doc.get("program", {}).get("id") if isinstance(doc.get("program"), dict) else None
        if pid:
            if pid in id_seen:
                rep.error(fname, "program.id",
                          f"项目 id '{pid}' 与 {id_seen[pid]} 重复")
            else:
                id_seen[pid] = fname

            # 检查文件名与 id 是否一致（建议而非强制）
            expected = f"{pid}.json"
            if fname != expected:
                rep.warn(fname, "-",
                         f"文件名与 program.id 不一致，建议改为 '{expected}'")

        if args.check_links:
            all_urls.extend(collect_urls(rep, doc, fname))

    # 并行检查链接
    if args.check_links and all_urls:
        # 去重（同一 URL 可能出现在多个项目中）
        seen = set()
        unique = []
        for pid, url in all_urls:
            if url not in seen:
                seen.add(url)
                unique.append((pid, url))

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {
                pool.submit(check_link, pid, url, args.timeout): (pid, url)
                for pid, url in unique
            }
            for fut in as_completed(futures):
                try:
                    rep.link_results.append(fut.result())
                except Exception as e:  # noqa: BLE001
                    pid, url = futures[fut]
                    rep.link_results.append((pid, url, False, f"检查器异常：{e}"))

        rep.link_results.sort(key=lambda r: (r[0], r[1]))

    print_report(rep, args.json)

    if not rep.ok:
        sys.exit(1)
    if args.strict and rep.warnings:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
