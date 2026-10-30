# 2026-10-30 独立复核：ca-iec 与 jp-working-holiday 主源

> 执行者：WorkBuddy（Buddy）
> 工具：ego-browser（ego lite）CLI 0.6.1.13 / Chromium 156.0.8078.48 / Node v24.22.1
> 目的：对 dsh 于 2026-10-29 提交的两个数据修正做第三方独立验证，不复用其抓取路径
> 结论：**两条判定均成立。但 2026-10-28 审计中"无法核实"的结论是工具限制，不是站点失效。**

---

## 1. 为什么换工具复核

2026-10-28 的 T1 审计用 Python `urllib` 探测，结论是：

| 站点 | 当时的失败表现 |
|---|---|
| `canada.ca` | TCP/TLS 均通，HTTP 层 `ConnectionResetError [WinError 10054]` 与读超时，首页同样失败 |
| `www.mofa.go.jp` | 全站 403，响应体为 Akamai `Access Denied`，换 UA 与各种请求头组合均无效 |

本次改用 ego lite（真实 Chromium，完整 TLS 指纹 + HTTP/2），**两个站点均一次打开成功**：

| 站点 | ego-browser 实测 |
|---|---|
| `canada.ca/.../iec.html` | 页面正常，`Work and Travel in Canada with International Experience Canada - Canada.ca` |
| `www.mofa.go.jp/j_info/visit/w_holiday/index.html` | 页面正常，`The Working Holiday Programmes in Japan \| Ministry of Foreign Affairs of Japan` |

**结论：10-28 的失败来自抓取客户端的协议特征被识别（Akamai/边缘 WAF 对 urllib 的 TLS 指纹与 HTTP/1.1 特征），不是站点封 IP，也不是链接失效。** 这条更正对数据集的方法论有直接影响：今后遇到"不可达"，先怀疑工具，再怀疑链接。

---

## 2. ca-iec-working-holiday

页面：`https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec/eligibility.html`
标题：`International Experience Canada: Who can apply - Canada.ca`
取样时间：2026-10-30 17:3x（Asia/Shanghai）

页面提供一个必选下拉：

> Select your country or territory of citizenship to see which categories are available: (required)

选项按字母序排列，实测片段：

```
Andorra / Australia / Austria / Belgium / Canada / Chile / Costa Rica /
Croatia / Czech Republic / Denmark / Estonia / Finland / France / Germany /
Greece / Hong Kong / Iceland / Ireland / Italy / Japan / Republic of Korea /
Latvia / Lithuania ...
```

**机器判定：**

| 检查 | 结果 |
|---|---|
| 列表中精确匹配 `China` | **false（不存在）** |
| 列表中出现的亚洲选项 | `Hong Kong`、`Japan`、`Taiwan` |
| 页面总文本行数 | 118 |

即：中国大陆护照在 IEC 的"国籍/地区"下拉中**不作为一个可选选项存在**，而中国香港、中国台湾存在。

**这比"某段文字说不接受中国大陆"是更强的证据**——不是被拒绝，是根本不在可选集合内。

对 `eligibility.passport_types` 的支撑：`mainland_china: not_eligible` / `hong_kong_china: eligible` / `taiwan_china: eligible` —— **全部成立**。

旁证：首页显示 `2026 IEC season is closed`，与 dsh 提交中 `timeline.windows[2026].status: closed` 一致。

---

## 3. jp-working-holiday

页面：`https://www.mofa.go.jp/j_info/visit/w_holiday/index.html`
标题：`The Working Holiday Programmes in Japan | Ministry of Foreign Affairs of Japan`
取样时间：2026-10-30 17:3x（Asia/Shanghai）

页面原文（节选）：

> The working holiday programmes are, based on bilateral arrangements, intended to make it possible for the youth of Japan and its partner countries/regions to ...
> As of 1 April, 2026, Japan has introduced the programmes with the following **32 countries** ...

国家/地区表（编号 · 名称 · 起始年 · 年度签证上限）节选：

```
4   South Korea      1999   10,000
10  Taiwan           2009   10,000
11  Hong Kong        2010   1,500
...
32  Italy            2026   500
```

**机器判定：**

| 检查 | 结果 |
|---|---|
| 伙伴国家/地区总数 | 32（官方自述） |
| 列表中的中国相关条目 | `Taiwan`（第 10）、`Hong Kong`（第 11） |
| 列表中是否有 `China` | **无** |

对 `eligibility.passport_types` 的支撑：`mainland_china: not_eligible` / `hong_kong_china: eligible` / `taiwan_china: eligible` —— **全部成立**。

补充：页面把 `Taiwan` 与 `Hong Kong` 单列在 32 个伙伴之列，中国大陆不在其中，与"双边互惠安排"的项目性质一致。

---

## 4. 与 dsh 结论的比对

| 项 | dsh 2026-10-29 提交 | 本次独立复核 | 一致性 |
|---|---|---|---|
| `ca-iec` mainland 不可申请 | 保留 not_eligible | 成立（选项级排除） | 一致 |
| `ca-iec` 2026 季度关闭 | closed | 成立（首页明示） | 一致 |
| `ca-iec` 语言要求 | 改为不需要 | 未独立验证 | 待验 |
| `ca-iec` 费用 184.75 CAD | 已改 | 未独立验证 | 待验 |
| `jp` mainland 不可申请 | 保留 not_eligible | 成立（32 国列表无 China） | 一致 |
| `jp` 年度名额 | 未逐项比对 | Taiwan 10,000 / HK 1,500 | 部分 |

**核心判定一致，且本次给出了比 dsh 更直接的证据形式（选项级排除、官方 32 国计数）。**

---

## 5. 方法学问题（需写入交接）

1. **dsh 未交代如何突破 403/reset。** 它 10-28 判定两站不可达，10-29 却提交了"against canada.ca / against mofa.go.jp"的修正，commit message 里给了精确的"0 hits across all three pages"这类可验证表述，但没有说明用什么客户端读到页面。**结论可信，路径不可复现**——这是交接后必须补齐的项，否则下一轮换人无法复现核实过程。
2. **"不可达"必须在报告里区分工具原因与站点原因。** 本次证明 10-28 的两条"未能核实"是工具原因，若当时直接写进数据的 `last_verified`，会产生虚假的核实记录。
3. **ego-browser 应作为数据核实的标准工具**，而不是 `urllib`/`requests`。理由：政府站点普遍部署 Akamai/Cloudflare，对非浏览器客户端的拦截是常态。

---

## 6. 本次未做的

- 未独立验证 `ca-iec` 的费用、语言要求、停留时长等字段
- 未复核 dsh 在 `88feb43`、`3c37660` 中改动的其余 6 个项目（AU / NZ / KR / US / DE / IE）
- 未验证 `web/` 前端的构建与部署产物
- 未运行 e2e 测试

以上属阶段 1 后续验收范围。
