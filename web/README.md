# 海外项目数据库 · Web 工作台

把仓库里的 `data/programs/*.json` 变成一个能直接用的双语工作台：筛选、搜索、智能匹配、申请看板、收藏、对比、数据说明。纯静态，零运行时费用，个人数据只存浏览器。

---

## 一、技术选型与目录结构

### 选型

| 层 | 选择 | 为什么不是别的 |
|---|---|---|
| 构建 | Vite 5 | 产物是纯静态文件，`dist/` 丢任何静态托管都能跑；不引入 SSR，因为没有需要服务端的东西 |
| UI | React 18 + TypeScript | 筛选用例多、状态跨页面复用（收藏/对比/看板），手写 DOM 会失控；TS 用来钉住 schema 的枚举，改数据时类型会报错 |
| 数据 | 构建期预生成 JSON | `scripts/sync-data.mjs` 把仓库 11 个 program JSON 合并成 3 个静态 JSON。浏览器只发静态请求，没有 API、没有数据库、没有 Key |
| 双语 | 离线词典（key = 中文原串） | 运行时调翻译 API 会产生费用且要联网；词典在构建期生成，访客翻页零延迟。缺词回落中文并 console.warn |
| 路由 | hash（`#/p/<id>`） | GitHub Pages 不支持 SPA fallback rewrite，hash 路由不需要服务端配置，刷新不会 404 |
| 个人状态 | localStorage | 没有账号体系，收藏/对比/进度/画像只存本机。换设备不同步——这是为「零成本 + 不收集数据」付的代价 |

### 目录

```
web/
├─ index.html                 单页入口
├─ package.json               scripts: sync:data / dev / build / preview
├─ vite.config.ts             base: './' —— 同一产物可跑根路径也可跑项目子路径
├─ tsconfig.json
├─ .npmrc                     registry.npmmirror.com（国内装包）
├─ i18n-src/                  翻译源（chunk-1..7.json），构建期不参与打包
│                             merged.json 是本地合并中间产物，已 gitignore
├─ public/data/               sync:data 生成的产物，随构建拷进 dist
│   ├─ programs.json          11 条完整记录 62.5 KB（gzip 约 18 KB）
│   ├─ index.json             卡片用轻量索引 9.0 KB（含来源计数）
│   └─ i18n.json              623 条词条 88.1 KB
├─ scripts/
│   ├─ sync-data.mjs          合并 data/programs/*.json → public/data/
│   ├─ smoke-test.mjs         65 条纯逻辑断言（筛选/排序/匹配/词典对齐）
│   ├─ e2e-check.mjs          84 条真实浏览器断言（CDP，无需 playwright）
│   ├─ shots.mjs              一次跑完 13 张页面截图 + 横向溢出检测
│   └─ screenshot.mjs         单页截图工具（真实手机视口）
├─ deploy/pages.yml           GitHub Pages 工作流，需要时手动拷到 .github/workflows/
└─ src/
   ├─ main.tsx                StrictMode > I18nProvider > App
   ├─ App.tsx                 侧边栏外壳 + 路由分发 + 四个本地状态 hook
   ├─ types.ts                与 data/schema.json 对齐的类型（枚举写成联合类型）
   ├─ tokens.css              设计令牌唯一定义处（81 个变量：色板/圆角/间距/字阶/阴影/焦点环）
   ├─ styles.css              基础样式，颜色与尺寸全部走 var()
   ├─ workbench.css           工作台层：侧栏、卡片动作、匹配、看板、对比、数据表、响应式
   ├─ refine.css              精修层：焦点环、触控目标、来源可视化、可信度条、跳转链接
   ├─ lib/
   │   ├─ data.ts             数据加载（模块级 Promise 缓存）
   │   ├─ filters.ts          筛选/排序纯函数，不读 localStorage，方便单测
   │   ├─ match.ts            匹配打分（资格 40 / 年龄 20 / 预算 10 / 学历 10 / 停留 10 / 偏好 10）
   │   ├─ router.ts           hash 路由
   │   ├─ useTitle.ts         逐页写入 document.title
   │   └─ store.ts            收藏 / 对比 / 最近浏览 / 申请进度，localStorage + 跨标签同步
   ├─ i18n/
   │   ├─ index.tsx           I18nProvider，t() 界面词条、td() 数据词条、te() 枚举标签
   │   └─ ui.ts               界面词条 + 枚举标签 + 匹配理由模板 + 看板状态
   └─ components/             Sidebar / ListView / Card / FilterBar / DetailView /
                              MatchView / TrackView / SavedView / CompareView / AboutView
```

### 成本与限制

| 项 | 数值 |
|---|---|
| 托管 | GitHub Pages 免费（public 仓库 1 GB、月 100 GB 流量）；Cloudflare Pages 免费额度更大 |
| 运行时费用 | 0 元。没有 Function、没有 KV、没有第三方 API |
| 首屏体积 | HTML 0.58 KB + CSS 24.77 KB（gzip 5.63 KB）+ JS 197.71 KB（gzip 64.53 KB）+ index.json 9.0 KB |
| 换设备 | 收藏/进度**不同步**，需要手工导出（本期没做导出，见「已知限制」） |
| 数据更新 | 需要跑 `pnpm run sync:data` 再构建；Pages 工作流已包含这一步 |
| SEO | hash 路由对搜索引擎不友好。要按详情页做 SEO 需换成真实路径 + 站点地图，属于下一阶段 |

---

## 二、信息架构与交互

六个入口，全部在左侧固定栏：

| 入口 | 解决的问题 | 关键交互 |
|---|---|---|
| **项目库** | 「有哪些项目、我能申哪个」 | 关键词同时匹配中英文名/国家/机构；地区·类型·资格·标签四组 chip（同维度 OR、跨维度 AND、标签之间 AND）；只看已收藏 / 只看有致命风险两个开关；年龄过滤；四种排序（默认 / 最近核实 / 停留期长 / 年龄上限高）；筛选状态写进 URL 可分享、刷新不丢 |
| **智能匹配** | 「按我的条件，哪个最值得先看」 | 填一次画像（护照资格 / 年龄 / 学历 / 预算 / 最短停留 / 必须带薪 / 不希望中介 / 偏好地区），按分数降序，每张卡给出 3 条理由（✓ 通过 / × 硬性不符 / ? 数据缺失）。硬门槛不过的分数封顶 30，避免「分数还行但根本不能申」 |
| **我的申请** | 「我申到哪一步了」 | 六个状态（未开始 / 准备材料 / 已提交 / 面试中 / 已获录取 / 未通过）+ 一句备注，顶部状态计数条 |
| **收藏** | 「先存着」 | 卡片右下 ★ 或详情页按钮，任意页面可切换 |
| **对比** | 「几个项目并排看」 | 上限 4 个，10 行字段（地区/类型/护照资格/年龄/停留/学历/语言/资金/风险/核实日期）；满 4 个后第 5 个按钮禁用 |
| **数据说明** | 「这些数可信吗」 | 收录数 / 已标注核实日期 / 来源总数 / 超过 90 天未复核；11 行明细表；四条收录规则 |

跨页面一致性的三处设计：

1. **语言**：右上「中文 / EN」一键切换，写 `localStorage['opd.lang']`，刷新后保持；同步更新 `<html lang>`。
2. **状态贯通**：收藏在卡片、详情页、收藏页三处都能切；`storage` 事件让两个标签页同步。
3. **本地优先**：所有个人数据都在 `opd.*` 前缀下，界面上明说「只存在本机、不上传」。

响应式：≥980 px 三列、620–980 px 两列、<620 px 单列；<720 px 侧栏变顶部横滑导航条，对比表逐列堆叠，数据表转块状。

---

## 三、核心代码

全部代码在 `src/`，这里给三处最能说明设计的。

### 1. 筛选与排序是纯函数（`src/lib/filters.ts`）

```ts
export interface Filters {
  q: string;
  regions: string[];
  types: string[];
  statuses: string[];
  tags: string[];        // 标签之间是 AND：选中多个必须同时具备
  ageOnly: boolean;
  age: number;
  savedOnly: boolean;
  criticalOnly: boolean;
}

export function matches(p: ProgramIndexEntry, f: Filters, savedIds: readonly string[] = []) {
  // 关键词：按空格拆词，每个词都要命中（中英文名/国家/机构），大小写不敏感
  const words = f.q.trim().toLowerCase().split(/\s+/).filter(Boolean);
  for (const w of words) {
    const hay = [p.name, p.name_en, p.country, p.authority].join(' ').toLowerCase();
    if (!hay.includes(w)) return false;
  }
  // 同维度多选是 OR
  if (f.regions.length && !f.regions.includes(p.region)) return false;
  if (f.types.length && !f.types.includes(p.program_type)) return false;
  if (f.statuses.length && !f.statuses.includes(p.status)) return false;
  // 标签是 AND
  for (const tag of f.tags) if (!(p.tags ?? []).includes(tag)) return false;
  // 年龄：数据里没有年龄区间的条目在开启年龄筛选时保留，宁可多显示也不误杀
  if (f.ageOnly && p.age_min != null && p.age_max != null) {
    if (f.age < p.age_min || f.age > p.age_max) return false;
  }
  if (f.savedOnly && !savedIds.includes(p.id)) return false;
  if (f.criticalOnly && !(p.risk_levels ?? []).includes('critical')) return false;
  return true;
}
```

`savedIds` 是参数而不是在函数里读 localStorage——这样这段逻辑能在 Node 里直接跑单测（`smoke-test.mjs` 就是这么验的）。

### 2. 匹配打分（`src/lib/match.ts`）

```ts
const W = { status: 40, age: 20, budget: 10, edu: 10, stay: 10, prefer: 10 };
const EDU_RANK = { high_school: 1, vocational: 2, bachelor_in_progress: 3,
                   bachelor_completed: 4, master: 5, any: 0 };
const HARD_FAIL = ['m.statusNo', 'm.ageLow', 'm.ageHigh', 'm.eduLow'];

export function scoreOne(p: ProgramIndexEntry, pr: Profile): MatchResult {
  let score = 0;
  const reasons: Reason[] = [];

  // 资格是硬门槛：40 分全给，不给就一分不给并直接封顶
  if (pr.status) {
    if (p.status === pr.status) { score += W.status; reasons.push({ kind: 'pass', code: 'm.statusOk' }); }
    else { reasons.push({ kind: 'fail', code: 'm.statusNo' }); }
  }
  // 年龄：落在区间内给满分，不在区间给 fail
  if (pr.age != null && p.age_min != null && p.age_max != null) {
    if (pr.age < p.age_min) { reasons.push({ kind: 'fail', code: 'm.ageLow', value: String(p.age_min) }); }
    else if (pr.age > p.age_max) { reasons.push({ kind: 'fail', code: 'm.ageHigh', value: String(p.age_max) }); }
    else { score += W.age; reasons.push({ kind: 'pass', code: 'm.ageOk' }); }
  }
  // ……预算/学历/停留/偏好的分项略，规则一致：能算就给分，数据缺失只标 warn 不扣分

  // 硬性不合格时把分数压到 30 以下，保证排序里永远排在有资格的后面
  if (reasons.some((r) => HARD_FAIL.includes(r.code))) score = Math.min(score, 30);
  return { id: p.id, score, reasons };
}
```

关键取舍：**缺数据只标 `warn` 不扣分**。因为「官网没写资金数额」是数据的诚实，不是项目更差；把它当扣分项会系统性惩罚信息透明的那一条。

### 3. 本地状态的读写与跨标签同步（`src/lib/store.ts`）

```ts
function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) ?? fallback;
  } catch {
    return fallback;   // 隐私模式/内容损坏时静默回落，不能因为读不到偏好就白屏
  }
}

function useStoredList(key: string, max?: number) {
  const [list, setList] = useState<string[]>(() => read<string[]>(key, []));
  useEffect(() => { write(key, list); }, [key, list]);
  useEffect(() => {
    const onStorage = (e: StorageEvent) => { if (e.key === key) setList(read<string[]>(key, [])); };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, [key]);
  const toggle = useCallback((id: string) => {
    setList((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (max != null && prev.length >= max) return prev;   // 满了就不加，不改动已有选择
      return [...prev, id];
    });
  }, [max]);
  return { list, toggle };
}
```

i18n 的运行时部分（`src/i18n/index.tsx`）：界面词条查 `UI[lang]`，数据词条查构建期生成的 `i18n.json`（key 就是中文原文），枚举值查 `ENUM_LABELS[lang]`。`td()` 找不到时回落中文并在 DEV 下 `console.warn`，这样漏译会立刻暴露而不是静默变成空白。

---

## 四、本地启动与部署

### 本机跑起来

```bash
cd web
pnpm install            # 首次
pnpm run sync:data      # 从 ../data/programs/*.json 生成 public/data/*
pnpm run dev            # http://127.0.0.1:5173
```

`pnpm build` 在这台机器上会因为 `tsc`/`vite` 不在 PATH 而失败，直接用等价命令：

```bash
node node_modules/typescript/bin/tsc -b --force
node node_modules/vite/bin/vite.js build
python -m http.server 8099 --bind 127.0.0.1 -d dist   # 预览产物
```

### 三条自检命令

```bash
node scripts/smoke-test.mjs                         # 65 条纯逻辑断言
node scripts/e2e-check.mjs http://127.0.0.1:8099/   # 84 条真实浏览器断言
node scripts/shots.mjs http://127.0.0.1:8099/ ./shots  # 13 张截图 + 三档视口溢出检测
```

再加两道视觉门（需要本机装了 impeccable skill）：

```bash
node node_modules/typescript/bin/tsc -b --force                  # 类型
impeccable.cmd detect --json src dist/index.html                 # AI 痕迹检测，期望输出 []
```

### 部署到 GitHub Pages

1. 把 `web/deploy/pages.yml` 拷到仓库根 `.github/workflows/pages.yml`（现在放在 web 里是为了不越界改 `.github/`）。
2. 仓库 Settings → Pages → Source 选 **GitHub Actions**。
3. push 到 `main`，工作流依次跑：install → sync:data → tsc → smoke-test → build → 上传 → 发布。
4. 站点地址 `https://<用户名>.github.io/overseas-program-dataset/`。`base: './'` 让子路径和根路径都能用，不用改代码。

### 部署到 Cloudflare Pages（可选，免备案、国内更快）

- 构建命令：`cd web && pnpm install && pnpm run sync:data && pnpm exec vite build`
- 输出目录：`web/dist`
- 环境变量：不需要任何变量（没有 Key、没有 API）

---

## 五、验收清单

逐条可执行。左边是动作，右边是通过标准。

### A. 可运行性

| # | 动作 | 通过标准 |
|---|---|---|
| A1 | `cd web && pnpm install` | 无 error；`node_modules` 生成 |
| A2 | `pnpm run sync:data` | 打印 `i18n coverage 100%` / `synced 11 programs`，`public/data/` 下三个 JSON 都在 |
| A3 | `node node_modules/typescript/bin/tsc -b --force` | 退出码 0，无输出 |
| A4 | `node node_modules/vite/bin/vite.js build` | `dist/index.html` + `dist/assets/*` 生成，`dist/data/` 三个 JSON 被拷入 |
| A5 | `python -m http.server 8099 -d dist` 后打开首页 | 11 张卡片渲染，无白屏、无控制台报错 |
| A6 | 刷新任意页面（包括详情页 `#/p/jp-working-holiday`） | 不 404，内容一致 |
| A7 | `node scripts/smoke-test.mjs` | `PASS 65 / 65 ALL GREEN` |
| A8 | `node scripts/e2e-check.mjs http://127.0.0.1:8099/` | `PASS 84 / 84 ALL GREEN` |
| A9 | `impeccable.cmd detect --json src dist/index.html` | 输出 `[]`（零告警） |
| A10 | 浏览器跑 `audit.cjs http://127.0.0.1:8099/` | 控制台报错 0、对比度不合格 0、390px 横向溢出 0 |

### B. 双语完整性

| # | 动作 | 通过标准 |
|---|---|---|
| B1 | 点右上「中文 / EN」 | 标题、导航、筛选标签、卡片标题、详情页全部切英文；无中文残留（官方机构名等专有名词除外） |
| B2 | 切到 EN 后刷新 | 仍是英文（`localStorage['opd.lang'] === 'en'`），`<html lang="en">` |
| B3 | 详情页逐个展开小节 | 中文模式的每个 note 在英文模式都有对应英文；不出现空字符串或 `undefined` |
| B4 | 看控制台 | 无 `[i18n] missing` 警告（有则说明词典漏词） |
| B5 | `sync:data` 的输出 | 始终 `i18n coverage 100%`；新增中文字段未翻译时这里会掉到 100% 以下 |

### C. 筛选与搜索正确性

| # | 动作 | 通过标准 |
|---|---|---|
| C1 | 搜 `canada` | 只剩 1 张（ca-iec）；搜 `加拿大` 命中同一条 |
| C2 | 搜 `work camp`（多词） | 结果同时含两个词，不是任一命中 |
| C3 | 筛「大陆护照不可申」 | 5 张，`data-status` 全为 `not_eligible` |
| C4 | 再点同一 chip | 取消筛选，回到 11 张 |
| C5 | 点「无需中介」再点「高时薪」 | 结果收窄（标签 AND），每张卡都同时含两个标签 |
| C6 | 勾「只看已收藏」（先收藏 1 个） | 只剩 1 张，URL 出现 `sv=1` |
| C7 | 勾「只看有致命风险」 | 只剩 10 张，每张卡 `data-risk` 含 `critical` |
| C8 | 排序切「停留期长」 | URL 出现 `o=stay`，卡片按停留月数降序 |
| C9 | 复制带筛选的 URL 到新标签页打开 | 筛选条件完整还原 |
| C10 | 智能匹配填年龄 20 | 出现全部结果并按分数降序；硬性不合格的卡分数 ≤30 且带 `×` 理由 |
| C11 | 对比加入第 5 个项目 | 按钮禁用，清单仍为 4，不出现第 5 列 |

### D. 已知限制（不在本期范围）

- 收藏/进度不能跨设备同步，也没有导出/导入按钮。
- hash 路由对 SEO 不友好，详情页无法被搜索引擎单独收录。
- 只有 11 个项目，样本量小；「智能匹配」的权重是按常识设的，没有真实用户行为校准。
- 数据更新仍需人工跑 `sync:data` + push；没有定时抓取官方页面的机制。
