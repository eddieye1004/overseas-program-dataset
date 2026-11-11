# 仓库门面设置清单 · Repository Settings Checklist

这份文件只写**要在 GitHub 设置里填什么**，不写怎么填。全部内容都是可复制的精确字符串。

> **不要把这里当成已完成的状态。** 下列每一项都需要有人在 GitHub 上点一次或用连接器写一次。
> 仓库内无法自动完成的原因：About 描述、topics、social preview 都只能通过
> `PATCH /repos/{owner}/{repo}` 与仓库设置页修改，而本机的 keyring 凭据在 session-0
> 下读不到，`gh` 无法认证。所以这里只出清单。

最后核对时间：2026-11-11。填写后请把「现状」一列改掉，或直接删掉本节的历史值。

---

## 1. About 描述（Description）

一行。GitHub 在搜索结果与仓库页顶部都显示它，超过约 160 字符会被截断。

### 现状（需替换）

当前值是一段 277 字符的英文，把「CI 拦百科与自媒体」这类实现细节写进去了，
在列表页会被截断到看不全：

```
Open dataset of working-holiday, internship & exchange programs for students - with verified official sources only. Every program record cites A-level government or program-owner sources; encyclopedia & self-media links are blocked by CI. A bilingual static site ships with it.
```

### 建议值 · 中文

```
面向中国大陆护照的海外打工度假 / 实习 / 毕业后工签数据集：29 个项目、117 条官方来源，每条资格可追溯并标注核实日期，CI 校验来源等级。
```

字符数 74（按 Unicode 码点算）。取舍：先给「面向谁」，再说「多少个项目、多少条来源」，
最后一句是差异点（可追溯 + CI 校验）。没有写「最全 / 最权威」——那是自评，本仓库没有依据支撑。

### 建议值 · 英文

```
Working-holiday, internship and post-study work programs for mainland Chinese passport holders: 29 programs, 117 cited official sources, each claim traceable and dated. Source tiers and links checked in CI.
```

字符数 206。英文版比中文长是正常的——英文单词信息密度低，硬压到同样的字符数会丢「29 / 117」
这组最能说明规模的事实。若希望更短，可删掉末句 `Source tiers and links checked in CI.`
（降到 168）。

### 选哪个

About 只有一个字段，不能同时放两版。**建议填英文版**：GitHub 的 topics 与搜索面向英文世界，
而中文读者从 README 与站点拿到同样的信息。若目标读者以中文社区为主，改填中文版。

---

## 2. Website

```
https://eddieye1004.github.io/overseas-program-dataset/
```

**必须带结尾斜杠**。GitHub Pages 对不带斜杠的路径会 301 到带斜杠版本，多一跳；
而 site 内的相对链接（`./p/<id>.html`、`./guides/...`）都以目录为基准解析，
省略斜杠在某些客户端会解析到上一级。实测两个变体都能打开，但带斜杠是唯一不会出歧义的写法。

核对于 2026-11-11：该地址与 `p/au-462-work-holiday.html` 均返回 200。

---

## 3. Topics（≤10 个）

GitHub 上限 20 个，本清单按 10 个给——超过 10 个之后边际收益骤降，而且会稀释前几个的权重。

### 现状（11 个，需收敛）

```
awesome-list, data-quality, dataset, github-pages, i18n, internship, open-data, source-verification, study-abroad, visa, working-holiday
```

### 终选（10 个）

```
dataset, open-data, working-holiday, visa, internship, source-verification, data-quality, study-abroad, github-pages, i18n
```

### 取舍理由

| topic | 去留 | 理由 |
|---|---|---|
| `dataset` | 留 | 最基础的身份标签，搜索「dataset」时的主要入口 |
| `open-data` | 留 | 说明可自由复用（CC BY 4.0），是复用的前置条件 |
| `working-holiday` | 留 | 本仓库最集中的主题（8 条打工度假记录），检索意图最明确 |
| `visa` | 留 | 覆盖面最广的上级词，把毕业后工签、实习签证都收进来 |
| `internship` | 留 | 第二大类（J-1 系列、IAESTE、AIESEC、德国 §16e） |
| `source-verification` | 留 | **本仓库的差异点**：不是又一个攻略合集，而是带来源等级的校验 |
| `data-quality` | 留 | 与上一条互补，指向 CI 与 schema 这一层 |
| `study-abroad` | 留 | 覆盖短期学习签证与毕业后工签这两类查询 |
| `github-pages` | 留 | 说明自带可浏览站点，区别于纯 JSON 仓库 |
| `i18n` | 留 | 中英双语是实际实现（词典查表），也是复用者会关心的点 |
| `awesome-list` | **去** | 本仓库不是「资源链接清单」形态，是结构化数据 + 校验，挂这个 topic 会招来预期不符的访问 |

### 一条判断

`source-verification` 与 `data-quality` 保留两个而不是合并成一个词：前者说的是**数据本身**的属性
（每条结论有官方来源），后者说的是**工程**属性（CI、schema、复核周期）。搜这两个词的人意图不同。

---

## 4. Social preview

上传：`docs/social-preview.png`（1200×630，GitHub 要求的最小尺寸正好是 1280×640，
1200×630 会被等比放大并轻微裁边；这是可接受的，因为四周留了 12px 边框与 64px 内边距）。

**不要手工改这张图**。它由 `web/scripts/social-preview.mjs` 生成，图上四个数字
（项目数、可申数、来源条数、复核周期）全部从 `data/programs/*.json` 与
`data/review-policy.json` 派生。数据变了就重跑：

```bash
cd web && node scripts/social-preview.mjs
```

重跑后需要**重新上传**——GitHub 不会跟着文件变化自动更新 social preview。

---

## 5. 其余建议项（不影响门面，但建议一并核对）

| 设置 | 建议值 | 说明 |
|---|---|---|
| Default branch | `main` | 现状应为 main，核对一次即可；本仓库的 push 触发与 Pages 都依赖它 |
| Features → Discussions | 关 | 纠错入口已统一到 issue 模板，再开一个 Discussions 会分裂讨论 |
| Features → Wiki | 关 | 文档在 `docs/` 与 README 里；wiki 与仓库内容会漂移，且不受 PR 校验 |
| Features → Sponsorships | 关 | 与项目定位无关 |
| Merge button | 允许 Squash merge | 数据改动多为单条记录，squash 后历史更可读；其余两种可关 |
| Automatically delete head branches | 开 | 减少分支堆积 |
| Releases | 暂不建 | 数据是持续更新的，没有需要冻结的版本号；等有下游依赖时再谈 |

---

## 填完之后的自检

三项都能在无登录状态下验证，填完直接跑：

```bash
# 1. About 描述与 homepage 是否生效
curl -s https://api.github.com/repos/eddieye1004/overseas-program-dataset \
  | python -c "import json,sys; d=json.load(sys.stdin); print(d['description']); print(d['homepage']); print(d['topics'])"

# 2. Pages 是否仍可访问
curl -sI https://eddieye1004.github.io/overseas-program-dataset/ | head -1

# 3. social preview 是否已换（返回 200 且 content-length 与本地文件接近）
curl -sI https://opengraph.githubassets.com/1/eddieye1004/overseas-program-dataset | head -3
```

第 3 条的图由 GitHub 自己渲染（About 描述 + 仓库名），与上传的 social preview 是两套东西：
`opengraph.githubassets.com` 给的是自动生成的卡片，上传的图用于社交平台与分享卡。
两者都值得看一眼，颜色与文字不要互相打架。
