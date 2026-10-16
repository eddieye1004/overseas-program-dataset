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

## [0.2.0] - 2026-10-16

### 修复 — 资格判定错误：日本、韩国应为不可申请（2026-10-16）

**问题**：`jp-working-holiday.json` 与 `kr-h1-working-holiday.json` 的 `eligibility.passport_types.mainland_china`
被标记为 `conditional`，护照说明中写为"年度协商制""未在公开名单中明确列出"，README 覆盖表标注"⚠️ 需查当年协议"。

**核实结论（A 级政府来源）**：

- 日本外务省《The Working Holiday Programmes in Japan》：截至 2026-04-01 共 32 个协议国家/地区，
  含中国台湾（10,000）、中国香港（1,500），**不含中国大陆**；中日之间未签订打工度假协议。
- 韩国外交部（在外同胞厅 WHIC）《List of Partner Countries/Regions and Annual Quota》（2026/27 更新）：
  共 30 个国家/地区，含中国台湾（800）、中国香港（1,000），**不含中国大陆**。

**风险**：`conditional` 会让读者产生"可能可以申请"的行动预期。本数据集的核心定位正是消灭"把不对大陆护照
开放的项目写成可申请"这一类错误，因此这两条属于护城河上的直接漏洞。

**修复**：两条记录的判定改为 `not_eligible`，护照说明与 critical 风险改写为确定性结论；
移除无法核实且与官方声明相悖的"指定代招渠道"表述，代之以日本外务省的官方反欺诈声明；
README 覆盖表同步改为 ❌ 不可申请。

### 修复 — 数据时效刷新（2026-10-16）

全部项目 `last_verified` 于 2026-10-16 复核。本批针对活跃窗口项目完成实质更新：

- `au-462-work-holiday.json`：处理时长由"约 4-8 周"修正为官方口径"约 3 个月"；新增 2027-28 财年
  注册窗口条目（日期待公布）。
- `us-j1-summer-work-travel.json`：移除已失效的"2026 年 9 月底前完成报名"建议，改为官方事实
  （无统一报名截止日期，由各 Sponsor 自行设定）；新增对应风险提示。
- `nz-china-whv.json`：新增 2027 年开放窗口条目（待 INZ 公布，预计 2027 年 1 月前后）。
- `jp-working-holiday.json` / `kr-h1-working-holiday.json`：来源核实日期同步更新。

### 修复 — CI 触发范围（2026-09-17）

**问题**：`validate.yml` 的 `paths` 过滤器只覆盖 `data/**`、`scripts/**` 和工作流文件本身。
仓库首次推送及后续所有 push 均**未触发**任何自动运行（实测 `runs total_count = 0`），
手动触发才首次跑通（run #1，`success`）。

**风险**：若贡献者只修改 `README.md`、`CONTRIBUTING.md`、`CHANGELOG.md` 或 `docs/**`，
CI 将被静默跳过。对于以「来源质量由 CI 强制」为核心定位的数据集，任何未被校验的合并
都是护城河的漏洞。

**修复**：把 `paths` 扩展到文档与变更日志，确保所有可能影响数据集可信度的改动都进入校验。

> 注：数据集的 CI 运行成本极低（离线校验数十秒），为省算力而收窄 `paths` 属于负收益优化。

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

### 变更 — CI 工具链升级与时区容错（2026-10-16）

**背景**：首次修复推送后 CI 失败（run #7），失败步骤为「校验数据完整性（离线）」。
根因不是数据本身错误——`validate.py` 把"核实日期在未来"判为 error，而 GitHub runner 使用 **UTC**；
维护者在 GMT+8 深夜按本地日期（2026-10-17）记录 `last_verified` 时，UTC 仍是 2026-10-16，
于是被误判为未来日期并 `exit 1`。该陷阱会稳定复现，影响所有在 GMT+8 夜间核实数据的维护者。

**修复**：
- `scripts/validate.py` — `_check_staleness()` 增加时区容错常量 `FUTURE_TOLERANCE_DAYS = 1`：
  超前 1 天以内视为正常的"本地时区 / UTC"偏移，静默通过；超前更多仍判为填写错误。
- `.github/workflows/validate.yml` — 三个 action 升级并按 **commit SHA 固定**（tag 可被移动，指向前者不安全）：

  | Action | 升级前 | 升级后 |
  |---|---|---|
  | `actions/checkout` | `@v4` | `@v7.0.1` |
  | `actions/setup-python` | `@v5` | `@v7.0.0` |
  | `actions/upload-artifact` | `@v4` | `@v7.0.2` |

  动因：CI 日志已明确告警 `Node.js 20 is deprecated`，旧版 action 正被强制运行在 Node 24 兼容垫片上。
  `python-version` 保持 `3.11` 不变——CI 只需覆盖实际支持的最低版本，无理由抬高。

**验证**：以 CI 的 UTC 基准（2026-10-16）回归测试，`last_verified` 记为 10-17 静默通过、
记为 10-18 仍报错、198 天前仍告警；本地 `scripts/validate.py` 通过（0 错误 / 0 警告）。

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

- 日本、韩国打工度假：v0.1.0 时记为"对华年度协商制"，已于 v0.2.0 依两国外交部门官方名单更正为
  **大陆护照不可申请**（中日、中韩之间均未签订打工度假协议）
- 新加坡 Work Holiday Pass 对大陆护照的适用性尚未核实
- 人名币估算金额（`cny_estimate`）按 2026-09 汇率粗略折算，仅供参考
