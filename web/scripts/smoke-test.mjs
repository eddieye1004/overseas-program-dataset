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
const { UI, ENUM_LABELS, MATCH_TEXT, TRACK_STATUS, TRACK_TEXT, VERDICT_TEXT } = await import(
  `file://${outUi.replace(/\\/g, '/')}`
);

// 首访引导的判定规则也是纯函数（只吃一份快照、不碰 localStorage），
// 所以能在无浏览器环境里直接断言「谁该看到引导、谁不该」。
const outOnboard = join(WEB, '.tmp-onboard.mjs');
await build({
  entryPoints: [join(WEB, 'src/lib/onboarding.ts')],
  bundle: true,
  format: 'esm',
  outfile: outOnboard,
  platform: 'neutral',
});
const { ONBOARD_VERSION, shouldShowOnboarding } = await import(
  `file://${outOnboard.replace(/\\/g, '/')}`
);

// 「下一步」也是纯函数：吃一条完整记录、吐一句话的依据。
// 它的输入是窗口日期与材料准备期，输出决定看板顶部先推哪几条，
// 算错了会让人错过一年一次的名额，所以边界必须逐条钉死。
const outNext = join(WEB, '.tmp-next.mjs');
await build({
  entryPoints: [join(WEB, 'src/lib/nextstep.ts')],
  bundle: true,
  format: 'esm',
  outfile: outNext,
  platform: 'neutral',
});
const { nextAction, prepDaysOf, rankByUrgency } = await import(
  `file://${outNext.replace(/\\/g, '/')}`
);

// 判定状态量（data/match-flags.json）与判定函数（lib/verdict.ts）是 M2 的另一半：
// 判定口径的唯一权威在 Python（scripts/match_readiness.py），TypeScript 只做
// 纯比较。这个文件把两侧钉死——任何一边改了口径而另一边没跟上，这里立刻红。
const outVerdict = join(WEB, '.tmp-verdict.mjs');
await build({
  entryPoints: [join(WEB, 'src/lib/verdict.ts')],
  bundle: true,
  format: 'esm',
  outfile: outVerdict,
  platform: 'neutral',
});
const { judgeOne, judgeAll, countByState, STATE_ORDER, RULES_VERSION, EMPTY_VERDICT_PROFILE } =
  await import(`file://${outVerdict.replace(/\\/g, '/')}`);

const index = JSON.parse(await readFile(join(WEB, 'public/data/index.json'), 'utf8'));
const dict = JSON.parse(await readFile(join(WEB, 'public/data/i18n.json'), 'utf8'));
const programs = JSON.parse(await readFile(join(WEB, 'public/data/programs.json'), 'utf8'));
const flags = JSON.parse(await readFile(join(WEB, 'public/data/match-flags.json'), 'utf8'));
// 样例快照直接从仓库 data/ 读，不进 public/：它是测试对账用的事实基线，
// 不是站点要发给浏览器的资源，复制一份到 public 只会多一份会漂移的副本。
const samples = JSON.parse(
  await readFile(join(WEB, '..', 'data', 'match-samples.json'), 'utf8'),
);

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
// 条数不写死：项目会一直加。这里守的是数据自洽，具体数字由
// README 记录（那处标注了取数日期）。
const TOTAL = index.length;
const N_ELIGIBLE = index.filter((p) => p.status === 'eligible').length;
const N_NOT = index.filter((p) => p.status === 'not_eligible').length;
ok('index 非空', TOTAL > 0, `got ${TOTAL}`);
ok('programs 条数与 index 一致', programs.length === TOTAL, `index=${TOTAL}, programs=${programs.length}`);
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
  'status 只有 eligible / not_eligible，且两者之和 = 总数',
  index.every((p) => p.status === 'eligible' || p.status === 'not_eligible') &&
    N_ELIGIBLE + N_NOT === TOTAL,
  `eligible=${N_ELIGIBLE}, not=${N_NOT}, total=${TOTAL}`,
);
console.log(`   实测：共 ${TOTAL} 项，可申 ${N_ELIGIBLE}，不可申 ${N_NOT}`);

console.log('\n[2] 默认无筛选');
ok('空筛选返回全部', applyFilters(index, EMPTY_FILTERS).length === TOTAL);

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
// 数字从数据派生，不写死：加项目不该让断言变红。
const countWhere = (fn) => index.filter(fn).length;
ok(
  '按地区 oceania 与数据一致',
  applyFilters(index, { ...EMPTY_FILTERS, regions: ['oceania'] }).length ===
    countWhere((p) => p.region === 'oceania'),
);
ok(
  '按类型 working_holiday 与数据一致',
  applyFilters(index, { ...EMPTY_FILTERS, types: ['working_holiday'] }).length ===
    countWhere((p) => p.program_type === 'working_holiday'),
);
ok(
  '按资格 eligible 条数与数据一致',
  applyFilters(index, { ...EMPTY_FILTERS, statuses: ['eligible'] }).length === N_ELIGIBLE,
);
ok(
  '按资格 not_eligible 条数与数据一致',
  applyFilters(index, { ...EMPTY_FILTERS, statuses: ['not_eligible'] }).length === N_NOT,
);

// 学籍门槛这一维是列表页新加的筛选项：它决定「能不能不脱产申请」，
// 是多数在职申请人第一道过滤。这里断言它按枚举精确匹配、且与数据条数一致。
const ENROLL_VALUES = ['none', 'enrolled_or_recent', 'required', 'unknown'];
for (const v of ENROLL_VALUES) {
  ok(
    `按学籍门槛 ${v} 与数据一致`,
    applyFilters(index, { ...EMPTY_FILTERS, enrollment: [v] }).length ===
      countWhere((p) => (p.enrollment_scope ?? 'unknown') === v),
  );
}
ok(
  '学籍门槛组内 OR：四值相加 = 总数',
  ENROLL_VALUES.reduce(
    (n, v) => n + applyFilters(index, { ...EMPTY_FILTERS, enrollment: [v] }).length,
    0,
  ) === TOTAL,
  '每个项目必须恰好落在一个学籍门槛档里，否则筛选会漏或重复',
);
ok(
  '学籍门槛与资格状态组间 AND 生效',
  applyFilters(index, { ...EMPTY_FILTERS, enrollment: ['none'], statuses: ['eligible'] }).every(
    (p) => (p.enrollment_scope ?? 'unknown') === 'none' && p.status === 'eligible',
  ),
);

console.log('\n[5] 组合筛选（组间 AND / 组内 OR）');
const combo = applyFilters(index, { ...EMPTY_FILTERS, regions: ['asia'], statuses: ['not_eligible'] });
ok(
  '亚洲 + 不可申 组间 AND 生效',
  combo.length >= 2 &&
    combo.every((p) => p.region === 'asia' && p.status === 'not_eligible') &&
    ['jp-working-holiday', 'kr-h1-working-holiday'].every((id) => combo.some((p) => p.id === id)),
  JSON.stringify(combo.map((p) => p.id)),
);
const or = applyFilters(index, { ...EMPTY_FILTERS, regions: ['oceania', 'europe'] });
// 组内 OR 应等于两个地区条数之和，不写死具体值
ok(
  '组内 OR：大洋洲+欧洲 = 两地之和',
  or.length ===
    applyFilters(index, { ...EMPTY_FILTERS, regions: ['oceania'] }).length +
      applyFilters(index, { ...EMPTY_FILTERS, regions: ['europe'] }).length,
  `got ${or.length}`,
);
const tagsAnd = applyFilters(index, { ...EMPTY_FILTERS, tags: ['no_agency_needed', 'high_wage'] });
ok('标签 AND 语义生效', tagsAnd.every((p) => p.tags.includes('no_agency_needed') && p.tags.includes('high_wage')));

console.log('\n[6] 年龄筛选');
const age20 = applyFilters(index, { ...EMPTY_FILTERS, ageOnly: true, age: 20 });
ok('20 岁覆盖全部项目', age20.length === TOTAL, `got ${age20.length}`);
const age40 = applyFilters(index, { ...EMPTY_FILTERS, ageOnly: true, age: 40 });
ok('40 岁被年龄上限过滤', age40.length < TOTAL, `got ${age40.length}`);
const age17 = applyFilters(index, { ...EMPTY_FILTERS, ageOnly: true, age: 17 });
ok('17 岁低于下限被过滤', age17.length < TOTAL, `got ${age17.length}`);
const ageOff = applyFilters(index, { ...EMPTY_FILTERS, ageOnly: false, age: 40 });
ok('未勾选年龄时忽略年龄', ageOff.length === TOTAL);

console.log('\n[7] 筛选项派生（全部来自数据，不硬编码）');
const f = buildFacets(index);
ok('regions 5 种', f.regions.length === 5, JSON.stringify(f.regions.map((x) => x.value)));
ok(
  'types 与数据里出现的类型数一致',
  f.types.length === new Set(index.map((p) => p.program_type)).size,
  JSON.stringify(f.types.map((x) => x.value)),
);
ok('statuses 2 种', f.statuses.length === 2, JSON.stringify(f.statuses.map((x) => x.value)));
ok('tags 有值', f.tags.length > 0, `got ${f.tags.length}`);
ok('region 计数合计 = 总数', f.regions.reduce((a, b) => a + b.count, 0) === TOTAL);

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

// 默认排序改成「可申优先」后，第一屏应该全是能申的项目。
// 这条断言锁的是产品决定：访客滚到一半才发现「我申不了」是最糟的体验。
const byEligible = sortPrograms(index, 'eligible');
const RANK = { eligible: 0, conditional: 1, unknown: 2, not_eligible: 3 };
ok(
  'eligible：状态优先级不递增（可申在前，不可申沉底）',
  byEligible.every((p, i) => i === 0 || RANK[byEligible[i - 1].status] <= RANK[p.status]),
  byEligible.map((p) => p.status).join(','),
);
ok(
  'eligible：首条可申，末条不可申',
  byEligible[0].status === 'eligible' &&
    byEligible[byEligible.length - 1].status === 'not_eligible',
  `${byEligible[0].status} / ${byEligible[byEligible.length - 1].status}`,
);
ok('eligible：不改变条数', byEligible.length === index.length);
ok(
  'eligible：收藏仍置顶（用户标注优先于系统判断）',
  sortPrograms(index, 'eligible', ['jp-working-holiday'])[0].id === 'jp-working-holiday',
);

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

console.log('\n[12b] 年龄占位语义：未核实 ≠ 0 岁');
{
  // 索引层把 99 统一成 null，「官方未公布年龄」与「无上限」都表现为 null，
  // 只能靠 age_verified 区分。这条断言锁住这个区分，避免卡片再次显示「0 岁」。
  const aiesec = index.find((p) => p.id === 'global-aiesec-global-talent');
  ok('未核实年龄的项目 age_verified=false', aiesec?.age_verified === false, JSON.stringify(aiesec));
  ok('未核实年龄的项目 min 不被当作真实下限', aiesec?.age_min === 0 && aiesec?.age_max === null);

  const de = index.find((p) => p.id === 'de-16e-internship');
  ok('「无年龄上限」的项目 age_verified=true', de?.age_verified === true, JSON.stringify(de));

  // 年龄筛选不该因数据缺失而排除项目：20 岁筛「未核实」那条要保留
  const withAge = applyFilters(index, { ...EMPTY_FILTERS, ageOnly: true, age: 20 });
  ok(
    '年龄筛选保留未核实项目',
    withAge.some((p) => p.id === 'global-aiesec-global-talent'),
    `got ${withAge.length}`,
  );
  // 40 岁应被 au-462（上限 30）排除，但仍保留未核实那条
  const at40 = applyFilters(index, { ...EMPTY_FILTERS, ageOnly: true, age: 40 });
  ok(
    '超龄项目被排除',
    !at40.some((p) => p.id === 'au-462-work-holiday'),
    `got ${at40.length}`,
  );
  ok(
    '未核实项目仍保留',
    at40.some((p) => p.id === 'global-aiesec-global-talent'),
    `got ${at40.length}`,
  );
  ok('20 岁比 40 岁筛出的更多', withAge.length >= at40.length, `${withAge.length} vs ${at40.length}`);
}

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
ok('matchAll 返回全部项目', ranked.length === TOTAL, `got ${ranked.length}`);
ok('matchAll 按分数降序', ranked.every((r, i) => i === 0 || ranked[i - 1].score >= r.score));
ok('matchAll 每条都有 id 与 0–100 分', ranked.every((r) => r.id && r.score >= 0 && r.score <= 100));
const paidTop = matchAll(index, { ...EMPTY_PROFILE, mustBePaid: true, preferNoAgency: true })[0];
ok(
  '带薪+免中介偏好产生对应理由',
  paidTop.reasons.some((r) => r.code === 'm.paidOk' || r.code === 'm.paidUnknown'),
);

// —— 身份（在读 / 毕业 2 年内 / 在职）——
// 这一组守的是「学历字段分不出身份」这件事：IAESTE 与 J-1 的 minimum_level
// 都是 bachelor_in_progress，德国 16e 也是，但只有前两条要求在读证明。
console.log('\n[13b] 身份：在读 vs 在职');
const ENROLLED_ONLY = ['global-iaeste', 'us-j1-summer-work-travel'];
ok(
  'enrollment_scope=required 的正好是 IAESTE 与 J-1',
  JSON.stringify(
    index.filter((p) => p.enrollment_scope === 'required').map((p) => p.id).sort(),
  ) === JSON.stringify(ENROLLED_ONLY),
  JSON.stringify(index.filter((p) => p.enrollment_scope === 'required').map((p) => p.id)),
);
ok(
  '德国 16e 学历写 bachelor_in_progress，但门槛是「在读或毕业 2 年内」',
  get('de-16e-internship').education === 'bachelor_in_progress' &&
    get('de-16e-internship').enrollment_scope === 'enrolled_or_recent',
  get('de-16e-internship').enrollment_scope,
);
ok(
  'IAESTE 学历同样写 bachelor_in_progress，却必须在读',
  get('global-iaeste').education === 'bachelor_in_progress' &&
    get('global-iaeste').enrollment_scope === 'required',
);
ok(
  'AIESEC 官方未公布身份门槛，记为 unknown 而不是 none',
  get('global-aiesec-global-talent').enrollment_scope === 'unknown',
  get('global-aiesec-global-talent').enrollment_scope,
);
ok(
  'AU 462 的注里同时出现「在读」与「2 年」，但门槛仍是 none（它接受已毕业者）',
  get('au-462-work-holiday').enrollment_scope === 'none',
  get('au-462-work-holiday').enrollment_scope,
);

const asEnrolled = scoreOne(get('global-iaeste'), {
  ...EMPTY_PROFILE,
  studentStatus: 'enrolled',
});
const asWorking = scoreOne(get('global-iaeste'), {
  ...EMPTY_PROFILE,
  studentStatus: 'working',
});
ok(
  '在读申 IAESTE 得分 > 在职申 IAESTE',
  asEnrolled.score > asWorking.score,
  `${asEnrolled.score} vs ${asWorking.score}`,
);
ok(
  '在职申 IAESTE 给出 m.studentNeeded 且是 fail',
  asWorking.reasons.some((r) => r.code === 'm.studentNeeded' && r.kind === 'fail'),
);
ok('在职申 IAESTE 被压到 ≤30', asWorking.score <= 30, `got ${asWorking.score}`);

const recentOn16e = scoreOne(get('de-16e-internship'), {
  ...EMPTY_PROFILE,
  studentStatus: 'recent_grad',
});
ok(
  '毕业 2 年内申 16e 不触发在读 fail',
  !recentOn16e.reasons.some((r) => r.code === 'm.studentNeeded'),
  JSON.stringify(recentOn16e.reasons.map((r) => r.code)),
);
ok(
  '不要求在读的项目对在职者给 pass 而非 fail',
  scoreOne(get('nz-china-whv'), { ...EMPTY_PROFILE, studentStatus: 'working' }).reasons.some(
    (r) => r.code === 'm.studentFree' && r.kind === 'pass',
  ),
);
ok(
  '不填身份时不计分（不计入分母）',
  scoreOne(get('global-iaeste'), { ...EMPTY_PROFILE }).reasons.length === 0,
);
const workingEligible = index.filter(
  (p) => p.status === 'eligible' && p.enrollment_scope === 'none',
).length;
ok(
  '在职可申 = 可申里 enrollment_scope 为 none 的条数',
  workingEligible ===
    index.filter((p) => p.status === 'eligible' && p.enrollment_scope === 'none').length,
  `${workingEligible}`,
);
ok('在职可申严格少于可申总数', workingEligible < index.filter((p) => p.status === 'eligible').length);

console.log('\n[14] 首访引导判定');
/** 造一份「全新访客」快照，再按用例改单项 */
const blank = () => ({ onboarded: null, replay: null, saved: [], track: {}, profile: null });
ok('全新访客显示引导', shouldShowOnboarding(blank()));
ok(
  '已看过当前版本的不再显示',
  !shouldShowOnboarding({ ...blank(), onboarded: ONBOARD_VERSION }),
);
ok(
  '看过旧版本的要再显示一次（文案改版后老用户能看到新版）',
  shouldShowOnboarding({ ...blank(), onboarded: ONBOARD_VERSION - 1 }),
);
ok('点了重看立刻显示', shouldShowOnboarding({ ...blank(), replay: 1, onboarded: ONBOARD_VERSION }));
ok(
  '有收藏但没标记过的不打扰（已证明会用这个站）',
  !shouldShowOnboarding({ ...blank(), saved: ['jp-working-holiday'] }),
);
ok(
  '有申请进度但没标记过的不打扰',
  !shouldShowOnboarding({ ...blank(), track: { 'au-462-work-holiday': { status: 'preparing' } } }),
);
ok(
  '填过匹配条件但没标记过的不打扰',
  !shouldShowOnboarding({ ...blank(), profile: { age: 24 } }),
);
// store 初始化时会写空值进 localStorage：这些不能被当成「有历史」
ok('空收藏数组不算有历史', shouldShowOnboarding({ ...blank(), saved: [] }));
ok('空进度对象不算有历史', shouldShowOnboarding({ ...blank(), track: {} }));
ok(
  '全 false / 空串的 profile 不算有历史',
  shouldShowOnboarding({ ...blank(), profile: { age: null, regions: [], degree: '' } }),
);
ok(
  'false 字段不算有历史（布尔条件默认关闭）',
  shouldShowOnboarding({ ...blank(), profile: { paidOnly: false, agencyFree: false } }),
);

console.log('\n[15] 下一步该做什么');
// 基准日固定成一个具体的天数，避免用 Date.now() 让断言随运行时刻漂
const D = (s) => Math.floor(Date.parse(s) / 86400000);
const NOW = D('2026-11-10');

/** 造一条只有窗口与材料的最小记录 */
const rec = (open, close, prep) => ({
  documents: prep == null ? [] : [{ prepare_days: prep }],
  timeline: { windows: [{ year: 2026, status: 'open', note: '', open_date: open, close_date: close }] },
});

ok('材料准备期求和', prepDaysOf(rec('2026-11-01', '2026-11-30', 7)) === 7);
ok('缺 prepare_days 时按 0 算，不猜平均值', prepDaysOf({ documents: [{}, { prepare_days: null }] }) === 0);

// 1) 窗口现在开着 → 说截止日
const inWindow = nextAction(rec('2026-10-19', '2026-10-30', 5), D('2026-10-25'));
ok('窗口内的动作是 close', inWindow.kind === 'close', inWindow.kind);
ok('窗口内算出剩余天数', inWindow.days === 5, String(inWindow.days));
ok('窗口内给出截止日', inWindow.date === '2026-10-30', String(inWindow.date));

// 2) 窗口还没开、但材料准备期已经压上来 → prep
const prepNow = nextAction(rec('2026-11-20', '2026-11-30', 20), NOW);
ok('准备期已压到窗口前时动作是 prep', prepNow.kind === 'prep', prepNow.kind);
ok('prep 报告窗口还剩几天', prepNow.days === 10, String(prepNow.days));

// 3) 窗口远、准备期还没压上来 → open
const farOpen = nextAction(rec('2027-03-01', '2027-03-20', 5), NOW);
ok('窗口还远时动作是 open', farOpen.kind === 'open', farOpen.kind);

// 4) 没有窗口日期 → idle，且不硬编日期
const noDates = nextAction({ documents: [{ prepare_days: 5 }], timeline: { windows: [{ year: 2026, status: 'unknown', note: '官方未公布' }] } }, NOW);
ok('无窗口日期时动作是 idle', noDates.kind === 'idle', noDates.kind);
ok('idle 不编造日期', noDates.date === null && noDates.days === null);

// 4b) 上一轮已关、下一轮未公布 → closed，并交代错过的日期
const closedPast = nextAction(
  {
    documents: [{ prepare_days: 5 }],
    timeline: {
      windows: [
        { year: 2026, status: 'closed', note: '', open_date: '2026-06-04', close_date: '2026-06-25' },
        { year: 2027, status: 'unknown', note: '日期未公布' },
      ],
    },
  },
  NOW,
);
ok('上一轮已关时动作是 closed', closedPast.kind === 'closed', closedPast.kind);
ok('closed 交代错过的关闭日', closedPast.lastClosed === '2026-06-25', String(closedPast.lastClosed));
ok('closed 不编造下一轮日期', closedPast.date === null && closedPast.days === null);

// 5) 边界：开放当天算「开着」，关闭当天也算「开着」（最后一天还能交）
ok('开放当天算窗口内', nextAction(rec('2026-11-10', '2026-11-30', 0), NOW).kind === 'close');
ok('关闭当天仍算窗口内', nextAction(rec('2026-10-01', '2026-11-10', 0), NOW).kind === 'close');
ok('关闭次日起不再算窗口内', nextAction(rec('2026-10-01', '2026-11-09', 0), NOW).kind !== 'close');

// 6) 多个窗口：同时开着取最早关闭的那个
const twoOpen = nextAction(
  {
    documents: [],
    timeline: {
      windows: [
        { year: 2026, status: 'open', note: '', open_date: '2026-11-01', close_date: '2026-12-31' },
        { year: 2026, status: 'open', note: '', open_date: '2026-11-05', close_date: '2026-11-20' },
      ],
    },
  },
  NOW,
);
ok('多窗口同时开着时取最早截止', twoOpen.date === '2026-11-20', String(twoOpen.date));

// 7) 排序：close 先于 prep 先于 open 先于 closed 先于 idle
const rankedNext = rankByUrgency(
  [
    { id: 'idle', program: { documents: [], timeline: { windows: [] } } },
    { id: 'closed', program: rec('2026-03-01', '2026-03-20', 1) },
    { id: 'open', program: rec('2027-03-01', '2027-03-20', 1) },
    { id: 'prep', program: rec('2026-11-20', '2026-11-30', 20) },
    { id: 'close', program: rec('2026-11-01', '2026-11-15', 1) },
  ],
  NOW,
);
ok(
  '紧急度排序 close > prep > open > closed > idle',
  rankedNext.map((r) => r.id).join(',') === 'close,prep,open,closed,idle',
  rankedNext.map((r) => r.id).join(','),
);
ok(
  '同档内按剩余天数升序',
  rankByUrgency(
    [
      { id: 'b', program: rec('2026-11-01', '2026-11-30', 0) },
      { id: 'a', program: rec('2026-11-01', '2026-11-12', 0) },
    ],
    NOW,
  )
    .map((r) => r.id)
    .join(',') === 'a,b',
);

// 8) 真实数据：带写死窗口的三条必须给出可执行结论
const datedIds = ['au-462-work-holiday', 'jp-working-holiday', 'nz-china-whv'];
for (const id of datedIds) {
  const p = programs.find((x) => x.program?.id === id) ?? programs.find((x) => x.id === id);
  const a = nextAction(p ?? {}, NOW);
  ok(`真实数据 ${id} 能算出具体动作（不是 idle）`, a.kind !== 'idle', a.kind);
}

console.log('\n[15] 资格判定：Python 与 TypeScript 同一口径');
{
  // 1) 版本号必须两边一致。改了判定逻辑只改一边，这里是最先红的地方，
  //    而且是红在「版本不匹配」这种一眼能懂的原因上，不用去翻 diff。
  ok(
    'rules_version 两侧一致',
    RULES_VERSION === flags.rules_version,
    `ts ${RULES_VERSION} / data ${flags.rules_version}`,
  );
  ok(
    'match-flags 覆盖全部项目',
    Object.keys(flags.programs).length === TOTAL,
    `flags ${Object.keys(flags.programs).length} / index ${TOTAL}`,
  );
  ok(
    'match-flags 的 id 与 index 完全一致',
    JSON.stringify(Object.keys(flags.programs).sort()) ===
      JSON.stringify(index.map((p) => p.id).sort()),
  );

  // 2) 逐样例、逐项目比对三态结论与逐维 code。
  //    只比 state 不够：两条都判 gap，一条是差雅思、一条是差资金，
  //    对用户是两件完全不同的事。所以连 (dim, kind, code) 一起比。
  for (const [name, pr] of Object.entries(samples.samples)) {
    const diffs = [];
    for (const [id, perSample] of Object.entries(samples.verdicts)) {
      const expected = perSample[name];
      const got = judgeOne(flags.programs[id], pr);
      const gotDims = got.dims.map((d) => `${d.dim}:${d.kind}:${d.code}`).join(',');
      const wantDims = expected.dims.map((d) => `${d.dim}:${d.kind}:${d.code}`).join(',');
      if (got.state !== expected.state) {
        diffs.push(`${id} 状态 ${got.state} ≠ ${expected.state}`);
      } else if (gotDims !== wantDims) {
        diffs.push(`${id} 逐维 ${gotDims} ≠ ${wantDims}`);
      }
    }
    ok(
      `样例 ${name}：${Object.keys(samples.verdicts).length} 条判定与 Python 完全一致`,
      diffs.length === 0,
      diffs.slice(0, 3).join(' | '),
    );
  }

  // 3) 三态的分布也要对得上——只比单条会漏掉「整组都算错但彼此自洽」的情况
  for (const [name, pr] of Object.entries(samples.samples)) {
    const rows = judgeAll(flags, index.map((p) => p.id), pr);
    const c = countByState(rows);
    const want = { can: 0, cannot: 0, gap: 0, unknown: 0 };
    for (const v of Object.values(samples.verdicts)) want[v[name].state] += 1;
    ok(
      `样例 ${name}：三态计数一致（能申 ${want.can} / 差什么 ${want.gap} / 不可判 ${want.unknown} / 不能申 ${want.cannot}）`,
      c.can === want.can && c.gap === want.gap && c.unknown === want.unknown && c.cannot === want.cannot,
      `ts ${JSON.stringify(c)} vs py ${JSON.stringify(want)}`,
    );
  }

  // 4) 硬性规则的定点断言。这些不依赖快照，写死的是「语义」而不是「当前结果」：
  //    快照只能证明两侧一致，不能证明两侧都还对。
  const ai = samples.samples.A; // 大陆 / 21 / 本科在读 / 雅思 6.0 / 3 万
  const au462 = judgeOne(flags.programs['au-462-work-holiday'], ai);
  ok('A 画像对澳洲 462：雅思 6.0 ≥ 4.5 判通过', au462.dims.find((d) => d.dim === 'language')?.code === 'lang_ok');
  ok(
    'A 画像对澳洲 462：本科在读但要求已完成 2 年，判不可判而非通过',
    au462.dims.find((d) => d.dim === 'education')?.code === 'edu_years_unknown',
  );

  const eur = { ...ai, age: 35 };
  ok(
    '超龄是 fail 不是 gap：年龄不合格优先于语言差距',
    judgeOne(flags.programs['au-462-work-holiday'], eur).state === 'cannot',
  );

  const b = samples.samples.B; // 大陆 / 28 / 本科毕业 / 无语言成绩 / 8 万
  const bLang = judgeOne(flags.programs['nz-china-whv'], b).dims.find((d) => d.dim === 'language');
  ok('B 画像无语言成绩 → 差什么（lang_missing），不是不可判', bLang?.code === 'lang_missing');

  const c = samples.samples.C; // 台湾 / 25 / 本科毕业 / 雅思 6.5 / 5 万
  ok(
    'C 画像对澳洲 462：台湾护照明确不可申',
    judgeOne(flags.programs['au-462-work-holiday'], c).dims[0].code === 'passport_no',
  );

  // 5) 「官方没公布」不许被当成「不设限」
  const aiesec = judgeOne(flags.programs['global-aiesec-global-talent'], ai);
  ok(
    'AIESEC 年龄未公布 → 不可判，不按 0–99 当无限制',
    aiesec.dims.find((d) => d.dim === 'age')?.code === 'age_unknown',
  );
  ok('AIESEC 结论为不可判', aiesec.state === 'unknown', aiesec.state);

  // 6) 资金：官方不设固定金额 ≠ 你没钱
  const de20 = judgeOne(flags.programs['de-20-job-search'], ai);
  ok(
    '官方不设固定金额的资金证明判「不适用」，不判差钱',
    de20.dims.find((d) => d.dim === 'funds')?.code === 'funds_by_design',
  );

  // 7) 状态优先级：fail > gap > silent
  ok('STATE_ORDER 首项为能申（先看还能做什么）', STATE_ORDER[0] === 'can', STATE_ORDER.join(','));
  ok('STATE_ORDER 覆盖四态', STATE_ORDER.length === 4 && new Set(STATE_ORDER).size === 4);

  // 8) 空画像也能跑：不该抛异常，也不该给出「能申」
  const emptyRows = judgeAll(flags, index.map((p) => p.id), EMPTY_VERDICT_PROFILE);
  ok('默认画像对全部项目都能算出结论', emptyRows.length === TOTAL, `got ${emptyRows.length}`);
  ok(
    '默认画像至少产出一条能申与一条不能申（说明判定真的在分叉）',
    new Set(emptyRows.map((r) => r.verdict.state)).size >= 3,
    JSON.stringify(countByState(emptyRows)),
  );

  // 9) 每个 code 都必须有中英文案，否则界面露出裸 key
  const codes = new Set();
  for (const id of Object.keys(flags.programs)) {
    for (const pr of Object.values(samples.samples)) {
      for (const d of judgeOne(flags.programs[id], pr).dims) codes.add(d.code);
    }
  }
  ok(
    `${codes.size} 个判定 code 全部有 zh/en 文案`,
    [...codes].every((code) => VERDICT_TEXT.zh[code] && VERDICT_TEXT.en[code]),
    [...codes].filter((code) => !VERDICT_TEXT.zh[code] || !VERDICT_TEXT.en[code]).join(','),
  );
  ok(
    'VERDICT_TEXT.zh 与 en 键一致',
    JSON.stringify(Object.keys(VERDICT_TEXT.zh).sort()) ===
      JSON.stringify(Object.keys(VERDICT_TEXT.en).sort()),
  );
  ok('VERDICT_TEXT.en 无中文', Object.values(VERDICT_TEXT.en).every((v) => !HAS_CJK.test(v)));
}

console.log('\n[16] 界面词条双语对齐');
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
  'm.studentOk', 'm.studentFree', 'm.studentNeeded', 'm.studentRecentOk', 'm.studentTooLate', 'm.studentUnknown',
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
    fs.rm(outOnboard, { force: true }),
    fs.rm(outNext, { force: true }),
    fs.rm(outVerdict, { force: true }),
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
