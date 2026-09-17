# 变更记录 · Changelog

本项目的数据变更遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式。

日期格式：`YYYY-MM-DD`

---

## [未发布]

### 修复 — 来源质量（2026-09-17）

**背景**：在一次链接复验中，发现 4 个项目的 `sources` 中混入了 D 级来源（百科、商业博客），
以及 1 处 `publisher` 含糊标注、1 处张冠李戴（韩国 H-1 的来源指向"数字游民签证"文章）。
这直接违背了本项目"每条数据可追溯至官方来源"的核心承诺。

**修复内容**：
- `ca-iec-working-holiday.json` — 删除百度百科来源，替换为 IRCC 官方 `Who can apply` 页
- `uk-youth-mobility-scheme.json` — 删除百度百科来源，替换为 GOV.UK `Youth Mobility Scheme` 资格页
- `kr-h1-working-holiday.json` — 删除指向"数字游民签证"的商业博客来源，替换为韩国官方 WHIC 逐国/地区说明页
- `global-aiesec-global-talent.json` — 删除百度百科来源，替换为 AIESEC 官方 Global Talent 项目页
- `global-iaeste.json` — 修正中国大陆合作机构标注（Archibucks 与 HLG 为 Co-operating Institution，**非** National Committee）
- `au-462-work-holiday.json` — 澳大利亚旅游局页面从 primary 降为 secondary（非移民局官方页）
- `us-j1-summer-work-travel.json` — 合并重复来源，高校来源从 primary 降为 secondary
- `jp-working-holiday.json` — 修正 publisher 与 URL 不符的来源；补充日本官方 2026-02-01 起中国台湾可参与两次的放宽说明

**新增自动化防线（关键）**：
- `scripts/validate.py` — 新增 `classify_source()` 域名分级器与 `_check_sources_quality()` 检查
  - D 级域名（百科/自媒体/商业博客）→ **校验失败，阻断合并**
  - `publisher` 含糊（"公开资料"等）→ **校验失败**
  - 项目全部来源均不足 A/B 级 → **校验失败**
  - 标注 primary 但域名可信度为 C 级 → **告警**
- 反向测试：注入 3 类违规，**3/3 全部捕获，退出码 1**

**分级标准（`data/sources.md` 同步更新）**：
| 级别 | 定义 | 示例 |
|---|---|---|
| A | 目的地国家政府官网、法律文本 | `immi.homeaffairs.gov.au`、`gov.uk`、`mofa.go.jp` |
| B | 项目本体国际组织官网 | `iaeste.org`、`aiesec.org` |
| C | 高校官方部门等可核验机构 | 高校 `.edu.cn` / `.edu.mo` 国际处 |
| D | 百科、自媒体、商业博客 — **禁止使用** | 百度百科、知乎、商业移民博客 |

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
