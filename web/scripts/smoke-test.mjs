// web/scripts/smoke-test.mjs
// 无浏览器环境下验证核心逻辑：筛选、搜索、i18n 覆盖率。
// 用 esbuild 把 TS 的筛选与词条模块即时转成 ESM，直接在 node 里跑断言。
// 运行：node scripts/smoke-test.mjs
import { readFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const WEB = resolve(__dirname, '..');

// esbuild 在 pnpm 里不是直接依赖（只是 vite 的传递依赖），从 .pnpm 目录按真实路径加载，
// 这样脚本不用额外安装任何东西。
const esbuildEntry = join(
  WEB,
  'node_modules/.pnpm/esbuild@0.21.5/node_modules/esbuild/lib/main.js',
);
const { build } = await import(pathToFileURL(esbuildEntry).href);

// 把纯逻辑模块打包成可直接 import 的 ESM（不碰 React）
const outfile = join(WEB, '.tmp-smoke.mjs');
await build({
  entryPoints: [join(WEB, 'src/lib/filters.ts')],
  bundle: true,
  format: 'esm',
  outfile,
  platform: 'neutral',
});
const { applyFilters, buildFacets, EMPTY_FILTERS, matches, sortPrograms, toggleValue } =
  await import(`file://${outfile.replace(/\\/g, '/')}`);

// 匹配打分是纯逻辑，也单独打包后直接断言，不进浏览器就能验证排序与理由
const outMatch = join(WEB, '.tmp-match.mjs');
await build({
  entryPoints: [join(WEB, 'src/lib/match.ts')],
  bundle: true,
  format: 'esm',
  outfile: outMatch,
  platform: 'neutral',
});
const { scoreOne, matchAll, EMPTY_PROFILE } = await import(
  `file://${outMatch.replace(/\\/g, '/')}`
);

// 界面词条表（zh/en 两套 + 匹配理由 + 进度状态），用于校验双语键完全对齐
const outUi = join(WEB, '.tmp-ui.mjs');
await build({
  entryPoints: [join(WEB, 'src/i18n/ui.ts')],
  bundle: true,
  format: 'esm',
  outfile: outUi,
  platform: 'neutral',
});
const { UI, ENUM_LABELS, MATCH_TEXT, TRACK_STATUS, TRACK_TEXT } = await import(
  `file://${outUi.replace(/\\/g, '/')}`
);

const index = JSON.parse(await readFile(join(WEB, 'public/data/index.json'), 'utf8'));
const dict = JSON.parse(await readFile(join(WEB, 'public/data/i18n.json'), 'utf8'));
const programs = JSON.parse(await readFile(join(WEB, 'public/data/programs.json'), 'utf8'));

let pass = 0;
const fails = [];
function ok(name, cond, detail = '') {
  if (cond) {
    pass++;
    console.log(`  ok   ${name}`);
  } else {
    fails.push(`${name}${detail ? ` — ${detail}` : ''}`);
    console.log(`  FAIL ${name}${detail ? ` — ${detail}` : ''}`);
  }
}

console.log('\n[1] 数据集完整性');
ok('index 条数 = 11', index.length === 11, `got ${index.length}`);
ok('programs 条数 = 11', programs.length === 11, `got ${programs.length}`);
ok(
  'index 每条都有 id/name/name_en/status',
  index.every((p) => p.id && p.name && p.name_en && p.status),
);
ok(
  'index 与 programs 的 id 集合一致',
  JSON.stringify(index.map((p) => p.id).sort()) ===
    JSON.stringify(programs.map((p) => p.program.id).sort()),
);
ok(
  '大陆可申 6 条 / 不可申 5 条',
  index.filter((p) => p.status === 'eligible').length === 6 &&
    index.filter((p) => p.status === 'not_eligible').length === 5,
  `eligible=${index.filter((p) => p.status === 'eligible').length}, not=${index.filter((p) => p.status === 'not_eligible').length}`,
);

console.log('\n[2] 默认无筛选');
ok('空筛选返回全部', applyFilters(index, EMPTY_FILTERS).length === 11);

console.log('\n[3] 关键词搜索（中英文双向）');
const zh = applyFilters(index, { ...EMPTY_FILTERS, q: '加拿大' });
// 命中数不写死：只要「加拿大」这串出现在某条 summary/note 里，该条就该被搜出来。
// （2026-10-30：ie-working-holiday-authorisation 的 summary 提到「加拿大公民 24 个月」，
//  于是它也被命中。这是搜索行为正确，不是回归。）
ok(
  '搜「加拿大」包含 ca-iec',
  zh.length >= 1 && zh.some((p) => p.id === 'ca-iec-working-holiday'),
  JSON.stringify(zh.map((p) => p.id)),
);
const en = applyFilters(index, { ...EMPTY_FILTERS, q: 'canada' });
ok('搜「canada」命中同一条（英文名匹配）', en.length >= 1 && en.some((p) => p.id === 'ca-iec-working-holiday'));
const partial = applyFilters(index, { ...EMPTY_FILTERS, q: 'work' });
ok('搜「work」命中多条', partial.length >= 5, `got ${partial.length}`);
const mixed = applyFilters(index, { ...EMPTY_FILTERS, q: 'working holiday' });
ok('多词 AND：working + holiday 都命中', mixed.length >= 5, `got ${mixed.length}`);
const none = applyFilters(index, { ...EMPTY_FILTERS, q: 'zzzznotexist' });
ok('无匹配返回空数组', none.length === 0);
const caseIns = applyFilters(index, { ...EMPTY_FILTERS, q: 'JAPAN' });
ok('搜索大小写不敏感', caseIns.length >= 1);

console.log('\n[4] 单维度筛选');
ok('按地区 oceania = 2（au + nz）', applyFilters(index, { ...EMPTY_FILTERS, regions: ['oceania'] }).length === 2);
ok('按类型 working_holiday = 7', applyFilters(index, { ...EMPTY_FILTERS, types: ['working_holiday'] }).length === 7);
ok('按资格 eligible = 6', applyFilters(index, { ...EMPTY_FILTERS, statuses: ['eligible'] }).length === 6);
ok('按资格 not_eligible = 5', applyFilters(index, { ...EMPTY_FILTERS, statuses: ['not_eligible'] }).length === 5);

console.log('\n[5] 组合筛选（组间 AND / 组内 OR）');
const combo = applyFilters(index, { ...EMPTY_FILTERS, regions: ['asia'], statuses: ['not_eligible'] });
ok('亚洲 + 不可申 = jp/kr', combo.length === 2 && combo.every((p) => ['jp-working-holiday', 'kr-h1-working-holiday'].includes(p.id)), JSON.stringify(combo.map((p) => p.id)));
const or = applyFilters(index, { ...EMPTY_FILTERS, regions: ['oceania', 'europe'] });
// 大洋洲 2（au-462、nz-china）+ 欧洲 3（de-16e、ie、uk-yms）
ok('组内 OR：大洋洲+欧洲 = 5', or.length === 5, `got ${or.length}`);
const tagsAnd = applyFilters(index, { ...EMPTY_FILTERS, tags: ['no_agency_needed', 'high_wage'] });
ok('标签 AND 语义生效', tagsAnd.every((p) => p.tags.includes('no_agency_needed') && p.tags.includes('high_wage')));

console.log('\n[6] 年龄筛选');
const age20 = applyFilters(index, { ...EMPTY_FILTERS, ageOnly: true, age: 20 });
ok('20 岁全部可申（11 条都覆盖 20）', age20.length === 11, `got ${age20.length}`);
const age40 = applyFilters(index, { ...EMPTY_FILTERS, ageOnly: true, age: 40 });
ok('40 岁被年龄上限过滤', age40.length < 11, `got ${age40.length}`);
const age17 = applyFilters(index, { ...EMPTY_FILTERS, ageOnly: true, age: 17 });
ok('17 岁低于下限被过滤', age17.length < 11, `got ${age17.length}`);
const ageOff = applyFilters(index, { ...EMPTY_FILTERS, ageOnly: false, age: 40 });
ok('未勾选年龄时忽略年龄', ageOff.length === 11);

console.log('\n[7] 筛选项派生（全部来自数据，不硬编码）');
const f = buildFacets(index);
ok('regions 5 种', f.regions.length === 5, JSON.stringify(f.regions.map((x) => x.value)));
ok('types 3 种', f.types.length === 3, JSON.stringify(f.types.map((x) => x.value)));
ok('statuses 2 种', f.statuses.length === 2, JSON.stringify(f.statuses.map((x) => x.value)));
ok('tags 有值且计数合计 ≥ 11', f.tags.length > 10);
ok('region 计数合计 = 11', f.regions.reduce((a, b) => a + b.count, 0) === 11);

console.log('\n[8] 双语完整性（词典覆盖所有中文串）');
const HAS_CJK = /[\u4e00-\u9fff]/;
const skip = new Set(['id', 'url', 'official_url', 'official_link', 'last_verified', 'verified_by', 'schema_version']);
const missing = [];
(function walk(node, path) {
  if (typeof node === 'string') {
    if (HAS_CJK.test(node) && !(node in dict)) missing.push(`${path}: ${node.slice(0, 40)}`);
    return;
  }
  if (Array.isArray(node)) return node.forEach((v, i) => walk(v, `${path}[${i}]`));
  if (node && typeof node === 'object') {
    for (const [k, v] of Object.entries(node)) {
      if (skip.has(k)) continue;
      walk(v, `${path}.${k}`);
    }
  }
})(programs, '$');
ok('无遗漏中文串', missing.length === 0, missing.slice(0, 5).join(' | '));
ok('词典条目数 > 600', Object.keys(dict).length > 600, `got ${Object.keys(dict).length}`);
ok(
  '词典 value 无中文（确保真的翻译了）',
  Object.values(dict).every((v) => typeof v === 'string' && !HAS_CJK.test(v)),
  Object.entries(dict).filter(([, v]) => HAS_CJK.test(v)).slice(0, 3).map(([k]) => k.slice(0, 30)).join(' | '),
);

console.log('\n[9] toggleValue 多选行为');
ok('加入', JSON.stringify(toggleValue([], 'a')) === '["a"]');
ok('移除', JSON.stringify(toggleValue(['a', 'b'], 'a')) === '["b"]');

console.log('\n[10] 每张卡片必有官方 URL（A/B 级来源要求）');
ok('全部有 https official_url', index.every((p) => p.official_url.startsWith('https://')));
ok(
  '全部有 last_verified 日期',
  index.every((p) => /^\d{4}-\d{2}-\d{2}$/.test(p.last_verified ?? '')),
);

console.log('\n[11] 排序（sortPrograms）');
const byVerified = sortPrograms(index, 'verified');
ok(
  'verified：last_verified 严格不递增',
  byVerified.every(
    (p, i) => i === 0 || (byVerified[i - 1].last_verified ?? '') >= (p.last_verified ?? ''),
  ),
);
const byStay = sortPrograms(index, 'stay');
ok(
  'stay：max_stay_months 严格不递增',
  byStay.every(
    (p, i) => i === 0 || (byStay[i - 1].max_stay_months ?? -1) >= (p.max_stay_months ?? -1),
  ),
);
ok('排序不改变条数', byStay.length === index.length && byVerified.length === index.length);
const savedFirst = sortPrograms(index, 'default', ['jp-working-holiday', 'nz-china-whv']);
ok(
  'default：收藏的两条置顶',
  savedFirst[0].id === 'jp-working-holiday' || savedFirst[0].id === 'nz-china-whv',
  savedFirst.slice(0, 2).map((p) => p.id).join(','),
);
ok('default：不传收藏时顺序不变', sortPrograms(index, 'default')[0].id === index[0].id);

console.log('\n[12] 收藏视图 / 致命风险视图筛选');
const savedOnly = applyFilters(
  index,
  { ...EMPTY_FILTERS, savedOnly: true },
  ['jp-working-holiday', 'ie-working-holiday-authorisation'],
);
ok('savedOnly：只留收藏的 2 条', savedOnly.length === 2, `got ${savedOnly.length}`);
ok(
  'savedOnly：不传收藏集合时为空',
  applyFilters(index, { ...EMPTY_FILTERS, savedOnly: true }).length === 0,
);
const critical = applyFilters(index, { ...EMPTY_FILTERS, criticalOnly: true });
ok(
  'criticalOnly：每条都含 critical 风险',
  critical.length > 0 && critical.every((p) => (p.risk_levels ?? []).includes('critical')),
  `got ${critical.length}`,
);
ok('criticalOnly：条数少于全部', critical.length < index.length, `got ${critical.length}`);
const both = applyFilters(
  index,
  { ...EMPTY_FILTERS, savedOnly: true, criticalOnly: true },
  ['jp-working-holiday'],
);
ok('两个开关可叠加', both.length === 1 && both[0].id === 'jp-working-holiday');

console.log('\n[13] 智能匹配打分（lib/match.ts）');
const get = (id) => index.find((p) => p.id === id);
const emptyScore = scoreOne(get('au-462-work-holiday'), EMPTY_PROFILE);
ok('空画像不打分也不给理由', emptyScore.score === 0 && emptyScore.reasons.length === 0);
const goodProfile = {
  ...EMPTY_PROFILE,
  status: 'eligible',
  age: 20,
  education: 'bachelor_in_progress',
  minStayMonths: 12,
};
const auScore = scoreOne(get('au-462-work-holiday'), goodProfile);
ok('符合条件得高分（≥70）', auScore.score >= 70, `got ${auScore.score}`);
const jpScore = scoreOne(get('jp-working-holiday'), goodProfile);
ok('资格不符被压到 ≤30', jpScore.score <= 30, `got ${jpScore.score}`);
ok('资格不符给出 fail 理由', jpScore.reasons.some((r) => r.code === 'm.statusNo' && r.kind === 'fail'));
const youngScore = scoreOne(get('nz-china-whv'), { ...EMPTY_PROFILE, age: 16 });
ok('低于年龄下限触发 fail', youngScore.reasons.some((r) => r.code === 'm.ageLow'));
ok(
  '高于年龄上限触发 fail',
  scoreOne(get('nz-china-whv'), { ...EMPTY_PROFILE, age: 45 }).reasons.some(
    (r) => r.code === 'm.ageHigh',
  ),
);
ok(
  '学历不足触发 fail',
  scoreOne(get('de-16e-internship'), { ...EMPTY_PROFILE, education: 'high_school' }).reasons.some(
    (r) => r.code === 'm.eduLow',
  ),
);
const ranked = matchAll(index, goodProfile);
ok('matchAll 返回全部 11 条', ranked.length === 11);
ok('matchAll 按分数降序', ranked.every((r, i) => i === 0 || ranked[i - 1].score >= r.score));
ok('matchAll 每条都有 id 与 0–100 分', ranked.every((r) => r.id && r.score >= 0 && r.score <= 100));
const paidTop = matchAll(index, { ...EMPTY_PROFILE, mustBePaid: true, preferNoAgency: true })[0];
ok(
  '带薪+免中介偏好产生对应理由',
  paidTop.reasons.some((r) => r.code === 'm.paidOk' || r.code === 'm.paidUnknown'),
);

console.log('\n[14] 界面词条双语对齐');
const zhKeys = Object.keys(UI.zh).sort();
const enKeys = Object.keys(UI.en).sort();
ok(
  'UI.zh 与 UI.en 键完全一致',
  JSON.stringify(zhKeys) === JSON.stringify(enKeys),
  `zh ${zhKeys.length} / en ${enKeys.length}`,
);
ok('UI 无空值', zhKeys.every((k) => UI.zh[k] && UI.en[k]));
ok(
  'ENUM_LABELS.zh 与 en 键一致',
  JSON.stringify(Object.keys(ENUM_LABELS.zh).sort()) ===
    JSON.stringify(Object.keys(ENUM_LABELS.en).sort()),
);
ok('ENUM_LABELS.en 无中文', Object.values(ENUM_LABELS.en).every((v) => !HAS_CJK.test(v)));
ok(
  'MATCH_TEXT.zh 与 en 键一致',
  JSON.stringify(Object.keys(MATCH_TEXT.zh).sort()) ===
    JSON.stringify(Object.keys(MATCH_TEXT.en).sort()),
);
ok('MATCH_TEXT.en 无中文', Object.values(MATCH_TEXT.en).every((v) => !HAS_CJK.test(v)));
ok('TRACK_TEXT 覆盖全部状态', TRACK_STATUS.every((s) => TRACK_TEXT.zh[s] && TRACK_TEXT.en[s]));
ok('TRACK_STATUS 6 个状态', TRACK_STATUS.length === 6, TRACK_STATUS.join(','));
// 打分用到的理由码必须都有文案，否则界面会露出 m.xxx 这种裸 key
const reasonCodes = [
  'm.statusOk', 'm.statusNo', 'm.ageOk', 'm.ageLow', 'm.ageHigh', 'm.ageUnknown',
  'm.budgetOk', 'm.budgetLow', 'm.budgetUnknown', 'm.eduOk', 'm.eduLow',
  'm.stayOk', 'm.stayLow', 'm.stayUnknown', 'm.paidOk', 'm.paidUnknown',
  'm.agencyOk', 'm.agencyNeeded', 'm.regionOk', 'm.regionNo',
];
ok(
  'MATCH_TEXT 覆盖全部理由码',
  reasonCodes.every((c) => MATCH_TEXT.zh[c] && MATCH_TEXT.en[c]),
);

await import('node:fs/promises').then((fs) =>
  Promise.all([
    fs.rm(outfile, { force: true }),
    fs.rm(outMatch, { force: true }),
    fs.rm(outUi, { force: true }),
  ]),
);

console.log(`\n${'='.repeat(48)}`);
console.log(`PASS ${pass} / ${pass + fails.length}`);
if (fails.length) {
  console.log('\nFAILED:');
  for (const x of fails) console.log(`  - ${x}`);
  process.exit(1);
}
console.log('ALL GREEN');
