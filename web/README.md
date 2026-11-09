# 海外项目数据库 · Web 工作台

把仓库里的 `data/programs/*.json` 变成一个能直接用的双语工作台：筛选、搜索、智能匹配、申请看板、收藏、对比、数据说明。纯静态，零运行时费用，个人数据只存浏览器。

---

## 一、技术选型与目录结构

### 选型

| 层 | 选择 | 为什么不是别的 |
|---|---|---|
| 构建 | Vite 5 | 产物是纯静态文件，`dist/` 丢任何静态托管都能跑；不引入 SSR，因为没有需要服务端的东西 |
| UI | React 18 + TypeScript | 筛选用例多、状态跨页面复用（收藏/对比/看板），手写 DOM 会失控；TS 用来钉住 schema 的枚举，改数据时类型会报错 |
| 数据 | 构建期预生成 JSON | `scripts/sync-data.mjs` 把仓库 27 个 program JSON 合并成 3 个静态 JSON。浏览器只发静态请求，没有 API、没有数据库、没有 Key |
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
├─ i18n-src/                  翻译源（chunk-*.json），构建期不参与打包
│                             merged.json 是本地合并中间产物，已 gitignore
├─ public/data/               sync:data 生成的产物，随构建拷进 dist
│   ├─ programs.json          27 条完整记录 354.0 KB（gzip 106.4 KB）
│   ├─ index.json             卡片用轻量索引 33.2 KB（gzip 9.0 KB，含来源计数）
│   └─ i18n.json              1799 条词条 602.8 KB（gzip 202.7 KB）
├─ public/p/                  gen-pages.mjs 生成：每项目一个真路径静态页 + 一个 /p/ 索引
│                             （28 个 HTML，4.4–10.0 KB，均值 8.4 KB）
├─ public/manifest.webmanifest  PWA 清单：standalone + 192/512/maskable 图标 + 三个快捷方式
├─ public/icons/              pwa-icons.mjs 生成的四张 PNG（192 / 512 / maskable 512 / apple 180）
├─ scripts/
│   ├─ sync-data.mjs          合并 data/programs/*.json → public/data/ + 生成 sitemap
│   ├─ gen-pages.mjs          生成 public/p/<id>.html 静态详情页（真路径，不是片段）
│   ├─ smoke-test.mjs         106 条纯逻辑断言（筛选/排序/匹配/词典对齐/引导判定）
│   ├─ e2e-check.mjs          179 条真实浏览器断言（CDP，无需 playwright）
│   ├─ pwa-icons.mjs          无头 Edge 截图生成 PWA 图标（不引 sharp / canvas）
│   ├─ shots.mjs              一次跑完 13 张页面截图 + 横向溢出检测
│   └─ screenshot.mjs         单页截图工具（真实手机视口）
└─ src/
   ├─ main.tsx                StrictMode > I18nProvider > App
   ├─ App.tsx                 侧边栏外壳 + 路由分发 + 四个本地状态 hook + 引导条挂载
   ├─ onboard.css             首访引导条样式（收起态一行 / 展开区两列）
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
   │   ├─ onboarding.ts       首访引导的显示判定（不 import store，避免 React 进纯逻辑测试）
   │   ├─ useTitle.ts         逐页写入 document.title
   │   └─ store.ts            收藏 / 对比 / 最近浏览 / 申请进度，localStorage + 跨标签同步
   ├─ i18n/
   │   ├─ index.tsx           I18nProvider，t() 界面词条、td() 数据词条、te() 枚举标签
   │   └─ ui.ts               界面词条 + 枚举标签 + 匹配理由模板 + 看板状态
   └─ components/             Sidebar / ListView / Card / FilterBar / DetailView /
                              MatchView / TrackView / SavedView / CompareView / AboutView /
                              Onboarding（首访引导条）
```

### 成本与限制

| 项 | 数值 |
|---|---|
| 托管 | GitHub Pages 免费（public 仓库 1 GB、月 100 GB 流量）；Cloudflare Pages 免费额度更大 |
| 运行时费用 | 0 元。没有 Function、没有 KV、没有第三方 API |
| 首屏体积 | HTML 3.8 KB（gzip 1.3 KB）+ CSS 31.7 KB（gzip 6.7 KB）+ JS 212.0 KB（gzip 68.1 KB）+ index.json 31.9 KB（gzip 8.5 KB） |
| 换设备 | 收藏/进度**不同步**，需要手工导出（本期没做导出，见「已知限制」） |
| 数据更新 | 需要跑 `pnpm run sync:data` 再构建；Pages 工作流已包含这一步 |
| SEO | 详情页已由 `gen-pages.mjs` 生成为真路径 `/p/<id>.html` 并进 sitemap；交互版仍是 hash 路由（`#/p/<id>`），两者并存互不影响 |

---

## 二、信息架构与交互

六个入口，全部在左侧固定栏：

| 入口 | 解决的问题 | 关键交互 |
|---|---|---|
| **项目库** | 「有哪些项目、我能申哪个」 | 关键词同时匹配中英文名/国家/机构；地区·类型·资格·学籍门槛·标签五组 chip（同维度 OR、跨维度 AND、标签之间 AND）；只看已收藏 / 只看有致命风险两个开关；年龄过滤；四种排序（默认 / 最近核实 / 停留期长 / 年龄上限高）；筛选状态写进 URL 可分享、刷新不丢 |
| **智能匹配** | 「按我的条件，哪个最值得先看」 | 填一次画像（护照资格 / 年龄 / 学历 / 预算 / 最短停留 / 必须带薪 / 不希望中介 / 偏好地区），按分数降序，每张卡给出 3 条理由（✓ 通过 / × 硬性不符 / ? 数据缺失）。硬门槛不过的分数封顶 30，避免「分数还行但根本不能申」 |
| **我的申请** | 「我申到哪一步了」 | 六个状态（未开始 / 准备材料 / 已提交 / 面试中 / 已获录取 / 未通过）+ 一句备注，顶部状态计数条 |
| **收藏** | 「先存着」 | 卡片右下 ★ 或详情页按钮，任意页面可切换 |
| **对比** | 「几个项目并排看」 | 上限 4 个，10 行字段（地区/类型/护照资格/年龄/停留/学历/语言/资金/风险/核实日期）；满 4 个后第 5 个按钮禁用 |
| **数据说明** | 「这些数可信吗」 | 收录数 / 已标注核实日期 / 来源总数 / 超过 90 天未复核；11 行明细表；四条收录规则 |

首访引导（`components/Onboarding.tsx`）：全新访客进入任何页面时，页头下方出现一条 44px 高的内联条，一句话说清「这个站只回答一个问题：大陆护照，你能申哪些」，右侧「展开看怎么用」展开成两列——左列六个模块各自的用途，右列三步拿到第一条结论。点「跳过」写 `opd.onboarded`，以后不再出现；「数据说明」页底部留「重看引导」入口，靠 `opd:replay-onboarding` 事件把已挂载的引导条叫回来（App 常驻、路由切换不重挂载，只改 localStorage 它读不到）。引导条刻意不用 `role="dialog"`：它是页面内容的一部分，不该拦截焦点，也不该在首屏吃掉卡片位置——实测 1280×900 下展开态仍露出 3 张完整卡片。

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
node scripts/smoke-test.mjs                         # 106 条纯逻辑断言
node scripts/e2e-check.mjs http://127.0.0.1:8099/   # 179 条真实浏览器断言
node scripts/shots.mjs http://127.0.0.1:8099/ ./shots  # 13 张截图 + 三档视口溢出检测
```

再加两道视觉门（需要本机装了 impeccable skill）：

```bash
node node_modules/typescript/bin/tsc -b --force                  # 类型
impeccable.cmd detect --json src dist/index.html                 # AI 痕迹检测，期望输出 []
```

### 部署到 GitHub Pages

1. 站点已上线：`https://eddieye1004.github.io/overseas-program-dataset/`（Pages 的 `build_type` 为 `workflow`）。
2. 工作流在 `.github/workflows/pages.yml`，push 到 `main` 且改动落在 `web/**` 或 `data/programs/**` 时自动跑：install → sync:data → tsc → smoke-test → build → 上传 → 发布。
3. 新建仓库时要注意：`configure-pages` 的 `enablement: true` 在首次运行里**会失败**——实测报 `Create Pages site failed. Resource not accessible by integration`，`GITHUB_TOKEN` 建不了 Pages 站点。解决方式是用有 `pages:write` 权限的个人 token 调一次 `POST /repos/{owner}/{repo}/pages`，body `{"build_type":"workflow"}`，之后工作流就能正常发布。这一步只做一次。
4. `base: './'` 让子路径和根路径都能用，不用改代码。

### 部署到 Cloudflare Pages（可选，免备案、国内更快）

- 构建命令：`cd web && pnpm install && pnpm run sync:data && pnpm exec vite build`
- 输出目录：`web/dist`
- 环境变量：不需要任何变量（没有 Key、没有 API）

### 装到手机主屏幕（PWA）

浏览器判断「可安装」的条件（MDN《Making PWAs installable》，2026-10-06 最后修改）：有 manifest、`name` 或 `short_name`、`icons` 里有 192 与 512、有 `start_url`、有 `display`、`prefer_related_applications` 不为 true，且站点走 https 或 localhost。本仓库全部满足，没有 service worker —— **离线不是目标**，数据每天在变，装一个会缓存旧数据的壳比不给装更糟。

- `public/manifest.webmanifest`：`display: standalone`、`start_url`/`scope` 都是 `./`（同一份产物既能跑子路径也能跑根路径），三个快捷方式指向 `#/`、`#/match`、`#/track`。
- `public/icons/`：192 / 512 / maskable-512 / apple-touch-180，四张 PNG 由 `node scripts/pwa-icons.mjs` 用无头 Edge 截图生成，不引 sharp / canvas。maskable 那张图形缩到 52% 是因为系统裁切的安全区只有中间 80%。
- `index.html` 与 `gen-pages.mjs` 生成的 27 个静态页都声明 `manifest` 与 `apple-touch-icon`：从搜索结果直接落到详情页的人同样能装。
- iOS 只认 `apple-touch-icon` 与 `apple-mobile-web-app-capable`，不读 manifest 的 `display`；安卓 Chrome / Samsung Internet 才把 manifest 当权威。
- 微信内置浏览器不支持「添加到主屏幕」，其菜单里是「在浏览器中打开」。国内用户的实际路径是：微信里读到链接 → 右上角「在浏览器中打开」→ Safari/Chrome 加到桌面。这一步没法在页面里绕过。

改配色时三处一起改：`src/tokens.css`、`public/favicon.svg`、`scripts/pwa-icons.mjs`（颜色值内联在脚本里，因为 Edge 截 SVG 需要一个能独立渲染的文档）。

---

## 五、验收清单

验收按 A 可运行性 / B 双语完整性 / C 筛选与搜索正确性 / D 数据可信度展示 四组做：A 组跑下面三条命令 + 打开 `/p/<id>.html` 不 404（真路径，不是 `#/p/<id>` 片段）；B 组切 EN 后翻完全部详情页无中文残留、刷新仍英文；C 组用国家 × 类型 × 护照判定 × 年龄 × 标签多维组合核对排序；D 组看「数据说明」页的收录数、核实日期、来源总数、超 90 天未复核四项是否与 `data/sources.md` 一致。

三条命令能覆盖 A/C/D 的大部分回归，日常改完先跑这三条：

```bash
pnpm run sync:data
node scripts/smoke-test.mjs                        # PASS 106 / 106
node scripts/e2e-check.mjs http://127.0.0.1:8099/  # PASS 179 / 179
```

两套测试的条数从数据派生，不写死，所以加项目不会让它们变红。文档里出现的「27 个项目、可申 21 / 不可申 6、来源 111」是 2026-11-09 的取数，改 `data/programs/*.json` 后需重新取数。

### 已知限制（不是缺陷）

- 收藏、对比、申请进度、匹配画像只存 `localStorage`，换设备不同步，也没有导出/导入。
- 交互版仍是 hash 路由：`#/p/<id>` 对爬虫是同一个 URL。为此另生成了真路径静态页 `/p/<id>.html`（进 sitemap），但换掉应用内路由要动 404 回退与全部 e2e，因此没做。两份内容由 `sync-data` + `gen-pages` 保证同源。
- 桌面端侧栏导航与语言切换 39px 高，小于 44px 触控标准——有意保留的鼠标密度；窄屏与 `pointer: coarse` 下补到 44px。
- 「可申/不可申」左侧竖条未做：状态已由徽标与结论条数字表达，再加色条属重复，且 impeccable 会把 `side-tab` 判为 AI 界面痕迹。
- 数据更新仍靠人工改 JSON + `sync:data` + push，没有定时抓取官方页的机制。
- 本机 pnpm 11 下 `pnpm install` 会以 `[ERR_PNPM_IGNORED_BUILDS]` 退出 1（`node_modules` 与构建仍正常）；CI 用 pnpm 9 无此问题。
