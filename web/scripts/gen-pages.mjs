// scripts/gen-pages.mjs
// 为每个项目生成一个真实路径的静态 HTML：public/p/<id>.html
//
// 为什么要这一步：主站是 hash 路由（#/p/xxx），Google 官方明确不支持用片段作为
// 独立页面——sitemap 里 26 条详情 URL 等于 0 条可索引页。这个脚本把每条记录渲染成
// 一个自足静态页（标题、description、JSON-LD、要点表、风险、来源清单、回站 CTA），
// 让搜索引擎有 26 个真页面可收，同时把权重导回交互版。
//
// 页面不依赖打包产物：单独引 guides/guide.css，与长文共用一套令牌，首屏零 JS。
//
// 运行：node scripts/gen-pages.mjs（已串进 npm run sync:data，CI 会自动跑）
import { readdir, readFile, writeFile, mkdir, rm } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = resolve(__dirname, '..');
const DATA_DIR = resolve(WEB_ROOT, '..', 'data', 'programs');
const PUBLIC_DIR = join(WEB_ROOT, 'public');
const OUT_DIR = join(PUBLIC_DIR, 'p');
const SITE = 'https://eddieye1004.github.io/overseas-program-dataset';

const esc = (s) =>
  String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

/** 纯文本摘要：去掉 markdown 痕迹，供 meta description 用 */
const plain = (s) => String(s ?? '').replace(/\s+/g, ' ').trim();

const STATUS_TEXT = {
  eligible: '大陆护照可申',
  not_eligible: '大陆护照不可申',
  conditional: '有条件可申',
  unknown: '资格未明确',
};

const ENROLL_TEXT = {
  required: '须全程保持在读学籍',
  enrolled_or_recent: '在读，或毕业不久（窗口见正文）',
  unknown: '官方未公布',
  none: '不要求学籍',
};

const REGION_TEXT = {
  oceania: '大洋洲',
  asia: '亚洲',
  europe: '欧洲',
  north_america: '北美洲',
  south_america: '南美洲',
  africa: '非洲',
  global: '全球',
};

/**
 * 年龄展示。0–99 在数据里兼作"无上限"与"未核实"两种含义，必须靠 note 区分
 * （与 sync-data.mjs 的 age_verified 同一判据：只有真正查不到的两条以 ⚠️ 开头），
 * 否则静态页会把"官方没公布年龄"渲染成"0 岁及以上"。
 */
function ageText(age) {
  const min = Number.isFinite(age?.min) ? age.min : null;
  const rawMax = Number.isFinite(age?.max) ? age.max : null;
  const note = (age?.note ?? '').trim();
  if (min === 0 && rawMax === 99) {
    return note.startsWith('⚠️') ? '官方未公布' : '无年龄限制';
  }
  const max = rawMax != null && rawMax < 99 ? rawMax : null;
  if (min == null && max == null) return '官方未公布';
  if (min != null && max == null) return `${min} 岁及以上`;
  if (min == null && max != null) return `${max} 岁及以下`;
  return `${min}–${max} 岁`;
}

function moneyText(m) {
  if (!m?.amount?.local_amount) return '官方未公布';
  const cur = m.amount.currency ?? '';
  return `${cur} ${m.amount.local_amount}`.trim();
}

/**
 * 单条记录 → 要点行（label, value）。
 * enrollScope 来自 index.json，不在本文件里重算——两处各判一遍必然漂移。
 */
function factRows(p, enrollScope) {
  const el = p.eligibility ?? {};
  const wc = p.work_conditions ?? {};
  const rows = [
    ['主管机构', p.program.authority ?? ''],
    ['地区', REGION_TEXT[p.program.region] ?? p.program.region],
    ['年龄', ageText(el.age)],
    ['学籍门槛', ENROLL_TEXT[enrollScope] ?? ''],
    ['英语要求', el.language?.required ? '有硬性要求' : '无硬性要求'],
    ['资金证明', moneyText(el.funds)],
    ['最长停留', wc.max_stay_months ? `${wc.max_stay_months} 个月` : ''],
  ];
  return rows.filter(([, v]) => v && v !== '—');
}

function sourceList(p) {
  const list = p.sources ?? [];
  if (list.length === 0) return '';
  const items = list
    .map(
      (s) =>
        `<li><a href="${esc(s.url)}" rel="nofollow noopener">${esc(s.name)}</a>` +
        `<span class="srcmeta">${s.type === 'primary' ? '官方一手' : '二手'}` +
        (s.last_verified ? ` · 核实 ${esc(s.last_verified)}` : '') +
        `</span></li>`,
    )
    .join('\n      ');
  return `
    <h2>来源</h2>
    <ul class="srclist">
      ${items}
    </ul>`;
}

/**
 * 生成单页。
 * @param {object} p 完整记录（data/programs/<id>.json）
 * @param {{enrollScope: string, indexPath: Map<string, object>}} ctx
 */
function render(p, ctx) {
  const id = p.program.id;
  const el = p.eligibility ?? {};
  const status = el.passport_types?.mainland_china ?? 'unknown';
  const statusText = STATUS_TEXT[status] ?? STATUS_TEXT.unknown;
  const enroll = ctx.enrollScope ?? 'none';
  const title = `${p.program.name} · 海外项目数据库`;
  const desc = plain(
    `${statusText}。${p.program.summary ?? ''} 核实至 ${p.last_verified ?? '—'}，共 ${(p.sources ?? []).length} 条官方来源。`,
  ).slice(0, 155);
  const rows = factRows(p, ctx.enrollScope)
    .map(([k, v]) => `<tr><th scope="row">${esc(k)}</th><td>${esc(v)}</td></tr>`)
    .join('\n        ');
  const risks = (p.risks ?? [])
    .map(
      (r) =>
        `<li><span class="tag ${r.level === 'critical' ? 'tag--no' : r.level === 'warning' ? 'tag--warn' : 'tag--ok'}">${esc(
          r.level === 'critical' ? '致命' : r.level === 'warning' ? '注意' : '提示',
        )}</span> ${esc(r.description)}</li>`,
    )
    .join('\n      ');
  const docs = (p.documents ?? [])
    .map((d) => `<li>${esc(d.name)}${d.note ? `<span class="srcmeta">${esc(d.note)}</span>` : ''}</li>`)
    .join('\n      ');
  const jsonld = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: title,
    description: desc,
    inLanguage: 'zh-CN',
    url: `${SITE}/p/${id}.html`,
    isPartOf: { '@type': 'Dataset', name: '海外项目数据库', url: `${SITE}/` },
    dateModified: p.last_verified ?? undefined,
    about: {
      '@type': 'Thing',
      name: p.program.name,
      alternateName: p.program.name_en ?? undefined,
    },
  };

  return `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<title>${esc(title)}</title>
<meta name="description" content="${esc(desc)}" />
<link rel="canonical" href="${SITE}/p/${id}.html" />
<meta property="og:type" content="article" />
<meta property="og:title" content="${esc(p.program.name)}" />
<meta property="og:description" content="${esc(desc)}" />
<meta property="og:url" content="${SITE}/p/${id}.html" />
<meta property="og:locale" content="zh_CN" />
<meta property="og:image" content="${SITE}/og.png" />
<link rel="icon" href="../favicon.svg" />
<link rel="stylesheet" href="../guides/guide.css" />
<script type="application/ld+json">
${JSON.stringify(jsonld, null, 2)}
</script>
</head>
<body>

<div class="top">
  <div class="top__inner">
    <a class="top__brand" href="../">海外项目数据库</a>
    <a class="top__nav" href="../#/p/${id}">打开交互版 →</a>
  </div>
</div>

<main class="wrap">

<h1>${esc(p.program.name)}</h1>
<p class="meta">${esc(p.program.name_en ?? '')} · ${esc(p.program.country)} · 核实至 ${esc(p.last_verified ?? '—')}</p>

<div class="verdict">
  <p><strong>${esc(statusText)}</strong>——这是护照资格判定，年龄、学历、在读状态另见下表。</p>
  <p>${esc(p.program.summary ?? '')}</p>
</div>

<h2>要点</h2>
<div class="scroll">
  <table class="tbl">
    <tbody>
        ${rows}
    </tbody>
  </table>
</div>

${docs ? `<h2>材料</h2>
    <ul class="srclist">
      ${docs}
    </ul>` : ''}

${risks ? `<h2>风险</h2>
    <ul class="srclist">
      ${risks}
    </ul>` : ''}

${sourceList(p)}

<h2>下一步</h2>
<p>这条记录的完整字段（申请步骤、时间窗口、费用、工作限制、逐条来源断言）在交互版里：</p>
<div class="cta">
  <strong>打开 ${esc(p.program.name)} 的完整页面</strong>
  <a href="../#/p/${id}">进入交互版 →</a>
</div>
<p class="meta">官方入口：<a href="${esc(p.program.official_url)}" rel="nofollow noopener">${esc(p.program.authority ?? p.program.official_url)}</a></p>

</main>

<p class="foot">
  海外项目数据库 · 共 ${ctx.total} 个项目 · 数据以各官方页面为准，本站只做索引。
  <a href="../">回到项目库</a>
</p>

</body>
</html>
`;
}

/**
 * enrollment_scope 的判定与 sync-data.mjs 必须一致，否则静态页与列表页会给出
 * 两种答案。这里不重复实现规则，而是直接读 sync-data 产出的 index.json。
 */
async function loadScopes() {
  const raw = await readFile(join(PUBLIC_DIR, 'data', 'index.json'), 'utf8');
  const index = JSON.parse(raw);
  const map = new Map();
  for (const e of index) map.set(e.id, e.enrollment_scope);
  return map;
}

async function main() {
  const files = (await readdir(DATA_DIR)).filter((f) => f.endsWith('.json')).sort();
  if (files.length === 0) throw new Error(`no json found in ${DATA_DIR}`);

  // index.json 由 sync-data.mjs 先生成（package.json 里顺序保证）
  let scopes;
  try {
    scopes = await loadScopes();
  } catch {
    throw new Error('public/data/index.json 不存在：先跑 node scripts/sync-data.mjs');
  }

  // 整目录重建：删掉项目后遗留的旧页面必须一起消失，否则搜索引擎会收到 404 链
  await rm(OUT_DIR, { recursive: true, force: true });
  await mkdir(OUT_DIR, { recursive: true });

  let n = 0;
  for (const f of files) {
    const p = JSON.parse(await readFile(join(DATA_DIR, f), 'utf8'));
    const id = p.program.id;
    const html = render(p, {
      enrollScope: scopes.get(id),
      total: files.length,
    });
    await writeFile(join(OUT_DIR, `${id}.html`), html, 'utf8');
    n++;
  }

  // 一个极简索引页，避免 /p/ 目录直接 404；顺带把 26 条链接集中一处
  const links = [];
  for (const f of files) {
    const p = JSON.parse(await readFile(join(DATA_DIR, f), 'utf8'));
    links.push(
      `<li><a href="./${p.program.id}.html">${esc(p.program.name)}</a> <span class="srcmeta">${esc(
        STATUS_TEXT[p.eligibility?.passport_types?.mainland_china] ?? '',
      )}</span></li>`,
    );
  }
  await writeFile(
    join(OUT_DIR, 'index.html'),
    `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>全部项目 · 海外项目数据库</title>
<link rel="canonical" href="${SITE}/p/" />
<link rel="icon" href="../favicon.svg" />
<link rel="stylesheet" href="../guides/guide.css" />
</head>
<body>
<div class="top"><div class="top__inner">
  <a class="top__brand" href="../">海外项目数据库</a>
  <a class="top__nav" href="../">打开项目库 →</a>
</div></div>
<main class="wrap">
<h1>全部 ${files.length} 个项目</h1>
<p class="lede">每条都是一个独立页面，可直接被搜索引擎收录；完整字段在交互版里。</p>
<ul class="srclist">
  ${links.join('\n  ')}
</ul>
</main>
<p class="foot">数据以各官方页面为准，本站只做索引。<a href="../">回到项目库</a></p>
</body>
</html>
`,
    'utf8',
  );

  console.log(`generated ${n} static pages in public/p/`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
