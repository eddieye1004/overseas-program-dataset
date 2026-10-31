# 验收清单（web workbench）

对应仓库 `3726d56` + 本轮未提交改动（UK IHS 主源、ACCEPTANCE 增补）。所有数字为 **2026-10-31 实测值**，数据文件改动后请重跑 `pnpm run sync:data` 再回来看本页——清单里写死的条数会跟着变。

怎么用：按 A → B → C → D 顺序做一遍。每行给出**动作**、**通过标准**、以及**不通过意味着什么**。最后一列指向自动化断言，标 `—` 的只能手测。

---

## A. 可运行性

| # | 动作 | 通过标准 | 不通过意味着什么 | 自动化 |
|---|---|---|---|---|
| A1 | `cd web && pnpm install --frozen-lockfile` | 依赖装好，出现 `node_modules` | lockfile 与 package.json 不同步 | — |
| A2 | `pnpm run sync:data` | 打印 `i18n coverage 100%` / `synced 11 programs`；`public/data/` 下有 `programs.json`(69.6 KB) / `index.json`(9.6 KB) / `i18n.json`(127.2 KB, 727 entries) | 数据 JSON 有语法错，或 `program.id` 与文件名不一致 | smoke [1] |
| A3 | `pnpm exec tsc -b --force` | 退出码 0，无输出 | 改数据字段后类型没同步（`types.ts` 与 `sync-data.mjs` 脱节） | CI |
| A4 | `pnpm exec vite build` | `dist/index.html` + `dist/assets/index-*.{css,js}` + `dist/data/` 三个 JSON | 构建失败，或 `dist/data/` 为空（说明 build 没先跑 sync） | CI |
| A5 | `python -m http.server 8099 --bind 127.0.0.1 -d dist`，打开 `http://127.0.0.1:8099/` | 11 张卡片，无白屏 | 数据路径错（`base: './'` 与子目录部署） | e2e [1] |
| A6 | 刷新 `#/p/jp-working-holiday` | 不 404，停留在详情页 | hash 路由解析坏了 | e2e [16] |
| A7 | `node scripts/smoke-test.mjs` | `PASS 76 / 76 ALL GREEN` | 筛选/排序/匹配的纯函数逻辑被改坏 | 本身即断言集 |
| A8 | `node scripts/e2e-check.mjs http://127.0.0.1:8099/` | `PASS 129 / 129 ALL GREEN` | 交互、路由、i18n、SEO 任一处回归 | 本身即断言集 |
| A9 | 把 A8 的 URL 换成线上 `https://eddieye1004.github.io/overseas-program-dataset/` | 同样 `129 / 129` | 本地绿、线上红 = 部署产物缺文件或 Pages 构建没跑 sync | — |
| A10 | `impeccable.cmd detect --json src dist/index.html` | 输出 `[]` | 出现 `side-tab` / `gimmick` 等 AI 界面痕迹 | — |
| A11 | `node audit.cjs http://127.0.0.1:8099/` | `consoleErrors: []`、`contrast.count: 0`、`hscroll390: 0` | 对比度跌破 4.5:1，或手机横向溢出 | — |

**本机已知偏差（不算失败）**：pnpm **11** 下 `pnpm install` 会以 `[ERR_PNPM_IGNORED_BUILDS] Ignored build scripts: esbuild@0.21.5` 退出 1，但 `node_modules` 已装全、esbuild.exe 可执行、`pnpm run build` 仍退出 0。CI 用 pnpm **9** 无此问题。判定 A1 通过看「`node_modules` 是否存在 + A4 能否构建」，不看 install 的退出码。

---

## B. 双语完整性

| # | 动作 | 通过标准 | 不通过意味着什么 | 自动化 |
|---|---|---|---|---|
| B1 | 点右上「中文 / EN」 | 标题、导航、筛选标签、卡片标题与摘要、详情页全部切英文 | `ENUM_LABELS` 漏了某个枚举值 | e2e [14] |
| B2 | 切 EN 后刷新 | 仍英文；`localStorage['opd.lang'] === 'en'`；`<html lang="en">` | 持久化或 `documentElement.lang` 同步坏了 | e2e [15] |
| B3 | 英文模式翻完 11 张卡的详情页 | 无空字符串、无 `undefined`、无成段中文（官方机构名等专名除外） | 词典缺词，回落了中文 | e2e [16][17] |
| B4 | 看控制台 | 无 `[i18n] missing translation:` 警告 | `i18n-src/chunk-*.json` 少条目 | — |
| B5 | `sync:data` 输出 | 始终 `i18n coverage 100%` | 新加的中文字段没翻译，覆盖率会掉下来 | smoke [8] |
| B6 | 词典自检 | 727 条目，且每条 value 不含 CJK 字符 | 有词条被误填成中文，等于没翻译 | smoke [8] |

---

## C. 筛选与搜索正确性

条数为 2026-10-31 实测。共 11 个项目：大陆可申 6 / 不可申 5；来源 38 条（primary 33）。

| # | 动作 | 通过标准 | 自动化 |
|---|---|---|---|
| C1 | 搜 `canada` | **1 张**（ca-iec），因为是英文名精确匹配 | smoke [3] |
| C2 | 搜 `加拿大` | **2 张**：ca-iec 与 ie。后者命中是因为爱尔兰的 summary 里有「加拿大公民可停留 24 个月」——这是正确命中，不是 bug | smoke [3] |
| C3 | 搜 `work camp` | **0 张**。没有项目的文本同时含这两个词；用它验证「无匹配」空态与 `.relax__chip` 引导 | e2e [22] |
| C4 | 搜 `工作 加拿大` | 多词 AND：两个词都要出现，**2 张** | smoke [3] |
| C5 | 点「我的资格 → 大陆护照不可申」 | **5 张**，`data-status` 全为 `not_eligible` | e2e [4] |
| C6 | 再点同一按钮 | 取消，「我的资格」回到 11 张 | e2e [5] |
| C7 | 点「地区 → 欧洲」 | **3 张**（de-16e、ie、uk-yms） | smoke [4] |
| C8 | 欧洲 + 大洋洲 | **5 张**（同维度多选 = OR，不是 3+2 之外的数） | smoke [5] |
| C9 | 展开「更多筛选」，点「无需中介」 | **7 张**，数字与 chip 上的计数一致 | e2e [6] |
| C10 | 再点「高时薪」 | 结果收窄到 **4 张**（标签之间是 AND） | e2e [6] |
| C11 | 展开「更多筛选」 | 主区只显示计数 ≥3 的 7 个标签（`no_agency_needed` 7 / `high_wage` 5 / `requires_degree` 3 / `stem_friendly` 3 / `requires_agency` 3 / `no_quota_cap` 3 / `once_in_lifetime` 3）；其余 8 个收进「其他标签（8）」 | e2e [25] |
| C12 | 勾「只看已收藏」（先收藏任意 1 个） | 只剩 1 张，URL 出现 `sv=1` | e2e [7] |
| C13 | 勾「只看有致命风险」 | **10 张**，每张 `data-risk` 含 `critical` | e2e [7] |
| C14 | 排序切「停留期长」 | URL 出现 `o=stay`，按停留月数降序 | e2e [8] |
| C15 | 默认排序 | 「可申优先」：第 1 张是 `eligible`，最后几张是 `not_eligible`；收藏项仍置顶 | e2e [25] |
| C16 | 复制带筛选的 URL 到新标签页 | 条件完整还原 | e2e [22] |
| C17 | 智能匹配填年龄 20 | 全部结果按分数降序；硬性不合格的卡分数 ≤30 且带 `×` 理由条 | smoke [13] |
| C18 | 对比加入第 5 个项目 | 按钮禁用，清单仍为 4 列 | e2e [10] |

---

## D. 数据可信度展示

这一块是本项目存在的理由，改版后属于首屏可见内容，必须逐条核。

| # | 动作 | 通过标准 | 自动化 |
|---|---|---|---|
| D1 | 列表页结论条 | 显示 `6 大陆护照可申` / `5 大陆护照不可申` / `来源 38 · 0 超期未复核`，与 `sync:data` 输出一致 | e2e [25] |
| D2 | 任意卡片底部 | 一行内含「年龄 · 停留 · 来源 n / 官方 n · 核实日期（`YYYY-MM-DD`）」，来源数不大于该项目的 `sources` 长度 | e2e [22] |
| D3 | 打开 `global-aiesec-global-talent` | 年龄显示「**未核实**」，不是「0 岁」，也不是某个二手数字 | smoke [12b] · e2e [24] |
| D4 | 打开 `global-iaeste` | 年龄显示「18 岁及以上」（官方只给下限）；费用段与语言分数段不显示具体金额/分数线 | smoke [12b] |
| D5 | 打开 `de-16e-internship` | 年龄显示「无年龄限制」 | smoke [12b] |
| D6 | 项目详情页顶部 | 有判定条写明中文「大陆护照可申 / 不可申」+ 一句官方原话 + 「来源 ↓」按钮 | e2e [26] |
| D7 | 点「来源 ↓」 | 平滑滚到 `#sources`，页面不重新加载（hash 路由不能被改） | e2e [26] |
| D8 | 来源列表 | 每条显示 `primary/secondary` 徽标、可点官方链接、**域名**、核实日期 | e2e [22] |
| D9 | 数据说明页 | 收录 11 / 已核实 11 / 来源 38 / 超期 0；表格逐行给出每个项目的主源数量与核实日期 | e2e [13] |

---

## E. 已知限制（不是缺陷）

- 收藏、对比、申请进度、匹配画像只存 `localStorage`，换设备不同步，也没有导出/导入。
- hash 路由导致 11 个详情页对爬虫是同一个 URL，SEO 收录价值有限；改 path 路由要动 404 回退与全部 e2e，因此未做。
- 桌面端侧栏 6 个导航项与语言切换是 39px / 37px 高，小于 44px 触控标准——有意保留的鼠标密度；窄屏与 `pointer: coarse` 下会补到 44px。
- 「可申/不可申」左侧竖条色条未做。状态由右上徽标与结论条数字表达，再加色条属重复，且 impeccable 会把 `side-tab` 判为 AI 界面痕迹。
- 数据更新仍靠人工改 JSON + `sync:data` + push，没有定时抓取官方页的机制。
