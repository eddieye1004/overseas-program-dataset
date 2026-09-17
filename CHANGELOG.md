# 变更记录 · Changelog

本项目的数据变更遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式。

日期格式：`YYYY-MM-DD`

---

## [未发布]

### 计划中
- 增加新加坡 Work Holiday Pass 资格核实（大陆护照适用性待确认）
- 增加中国香港 / 中国台湾护照的项目资格对照表
- 增加"申请难度"与"总成本估算"派生字段
- 提供 CSV 导出以便非开发者使用

---

## [0.1.0] - 2026-09-17

### 新增

**核心数据（8 个可用项目）**
- `au-462-work-holiday.json` — 澳大利亚 Work and Holiday Visa (462)
- `nz-china-whv.json` — 新西兰 China Working Holiday Visa
- `jp-working-holiday.json` — 日本 Working Holiday Programme
- `kr-h1-working-holiday.json` — 韩国 H-1 Working Holiday
- `us-j1-summer-work-travel.json` — 美国 J-1 Summer Work Travel
- `de-16e-internship.json` — 德国 §16e 与学业相关实习居留许可
- `global-iaeste.json` — IAESTE 国际技术实习
- `global-aiesec-global-talent.json` — AIESEC Global Talent

**显式排除记录（3 个项目）**
- `ca-iec-working-holiday.json` — 加拿大 IEC（大陆护照不可申请）
- `uk-youth-mobility-scheme.json` — 英国 YMS（大陆护照不可申请）
- `ie-working-holiday-authorisation.json` — 爱尔兰 WHA（大陆护照不可申请）

> 记录"不可申请"的项目是本数据集的重要设计。它帮助用户避免把时间浪费在错误目标上。

**基础设施**
- `data/schema.json` — 6 表数据字段定义（program / eligibility / timeline / documents / steps / sources）
- `data/sources.md` — 官方来源清单
- `scripts/validate.py` — 数据完整性与官方链接存活校验
- `.github/workflows/validate.yml` — 每周自动校验

### 数据来源

所有数据均来自各国移民局官网、驻华使领馆及项目官方页面。
每条数据的 `sources` 字段记录了具体来源 URL 与核实日期（`2026-09-17`）。

### 已知局限

- 日本、韩国打工度假对华协议为**年度协商制**，部分年份可能暂停，数据中的资格状态需按年复核
- 新加坡 Work Holiday Pass 对大陆护照的适用性尚未核实
- 人名币估算金额（`cny_estimate`）按 2026-09 汇率粗略折算，仅供参考
