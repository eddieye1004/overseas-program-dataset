// scripts/sync-data.mjs
// 把仓库根目录 data/programs/*.json 合并成前端可直接 fetch 的两个静态文件：
//   public/data/programs.json  完整数据（11 条，含 documents/steps/risks/sources），详情页用
//   public/data/index.json     轻量索引（列表页/筛选用，只保留卡片与筛选需要的字段）
// 运行：node scripts/sync-data.mjs（package.json 里是 pnpm sync:data）
import { readdir, readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = resolve(__dirname, '..');
const DATA_DIR = resolve(WEB_ROOT, '..', 'data', 'programs');
const I18N_DIR = join(WEB_ROOT, 'i18n-src');
const OUT_DIR = join(WEB_ROOT, 'public', 'data');

/** 从单条 program 里抽出列表页需要的字段，避免把整份 97KB 数据塞进首屏。 */function toIndexEntry(p) {
  const el = p.eligibility ?? {};
  const age = el.age ?? {};
  const funds = el.funds ?? {};
  const lang = el.language ?? {};
  const wc = p.work_conditions ?? {};

  // 99 在数据里表示“无上限”，前端统一转成 null，由 UI 决定如何展示
  const ageMin = Number.isFinite(age.min) ? age.min : null;
  const ageMax = Number.isFinite(age.max) && age.max < 99 ? age.max : null;

  // 0–99 在 schema 里兼作两种含义，索引层必须把它们分开，否则卡片会把
  // 「官方没公布年龄」渲染成「0 岁以上」：
  //   a) 真实的「无年龄上限」——note 写的是「无年龄上限」（如 de-16e、iaeste）
  //   b) 「未核实」——note 以 ⚠️ 开头并写明官方未公布（如 global-aiesec）
  // 判据只能落在 note 上，因为数据里没有独立字段；这条规则一旦 schema 加了
  // age_verified 之类的字段就该删掉。
  const ageUnknown = age.min === 0 && age.max === 99 && /未核实/.test(age.note ?? '');

  return {
    id: p.program.id,
    name: p.program.name,
    name_en: p.program.name_en ?? p.program.name,
    country: p.program.country,
    country_code: p.program.country_code,
    region: p.program.region,
    program_type: p.program.program_type,
    visa_code: p.program.visa_code ?? null,
    official_url: p.program.official_url,
    authority: p.program.authority ?? null,
    summary: p.program.summary,
    tags: p.program.tags ?? [],
    active: p.program.active !== false,

    // 列表卡片与筛选要用的派生字段
    status: el.passport_types?.mainland_china ?? 'unknown',
    age_min: ageMin,
    age_max: ageMax,
    age_verified: !ageUnknown,
    max_stay_months: wc.max_stay_months ?? null,
    education: el.education?.minimum_level ?? null,
    language_required: lang.required === true,
    funds_amount: funds.amount?.local_amount ?? null,
    funds_currency: funds.amount?.currency ?? null,
    risk_levels: (p.risks ?? []).map((r) => r.level),
    last_verified: p.last_verified ?? null,
    // 列表卡片也要能看出「这条有几条官方主源」——核来源是核心路径的一环，
    // 藏在详情页里等于没有。只放计数，不放 URL，索引体积几乎不变。
    source_count: (p.sources ?? []).length,
    source_primary: (p.sources ?? []).filter((s) => s.type === 'primary').length,
  };
}

/**
 * 遍历数据里所有“可能是中文”的字符串（含中文标点或汉字的），检查是否都能在词典里查到。
 * 只做覆盖度自检，不改数据；命中不到的字符串会被前端回落成中文显示，同时 dev 下 console.warn。
 */
function findUntranslated(programs, dict) {
  const out = new Set();
  const HAS_CJK = /[\u4e00-\u9fff]/;
  const visit = (node) => {
    if (typeof node === 'string') {
      if (HAS_CJK.test(node) && !(node in dict)) out.add(node);
      return;
    }
    if (Array.isArray(node)) {
      node.forEach(visit);
      return;
    }
    if (node && typeof node === 'object') {
      // 这些是机器可读的枚举/URL/日期，不需要翻译
      for (const [k, v] of Object.entries(node)) {
        if (k === 'id' || k === 'url' || k === 'official_url' || k === 'official_link') continue;
        if (k === 'last_verified' || k === 'verified_by' || k === 'schema_version') continue;
        visit(v);
      }
    }
  };
  visit(programs);
  return [...out];
}

async function main() {
  const files = (await readdir(DATA_DIR)).filter((f) => f.endsWith('.json')).sort();
  if (files.length === 0) throw new Error(`no json found in ${DATA_DIR}`);

  const programs = [];
  for (const f of files) {
    const raw = await readFile(join(DATA_DIR, f), 'utf8');
    const obj = JSON.parse(raw);
    if (!obj.program?.id) throw new Error(`${f}: missing program.id`);
    if (obj.program.id !== f.replace(/\.json$/, '')) {
      throw new Error(`${f}: program.id "${obj.program.id}" does not match filename`);
    }
    programs.push(obj);
  }

  // 顺序固定下来，避免每次构建产物 diff 抖动
  programs.sort((a, b) => a.program.id.localeCompare(b.program.id));

  // 合并离线词典：i18n-src/chunk-*.json，key 是中文原串，value 是英文译文。
  // 运行时不做机器翻译，只按中文原串查表（详见 src/i18n/index.tsx）。
  const dict = {};
  for (const f of (await readdir(I18N_DIR)).filter((f) => /^chunk-\d+\.json$/.test(f)).sort()) {
    Object.assign(dict, JSON.parse(await readFile(join(I18N_DIR, f), 'utf8')));
  }

  await mkdir(OUT_DIR, { recursive: true });
  const full = JSON.stringify(programs, null, 0);
  const index = JSON.stringify(programs.map(toIndexEntry), null, 0);
  const i18n = JSON.stringify(dict, null, 0);
  await writeFile(join(OUT_DIR, 'programs.json'), full, 'utf8');
  await writeFile(join(OUT_DIR, 'index.json'), index, 'utf8');
  await writeFile(join(OUT_DIR, 'i18n.json'), i18n, 'utf8');

  // 覆盖率自检：数据里出现的中文串若不在词典里，构建时就报出来，别等到页面上才发现
  const missing = findUntranslated(programs, dict);
  if (missing.length > 0) {
    console.warn(`WARN ${missing.length} untranslated string(s):`);
    for (const s of missing.slice(0, 20)) console.warn(`  - ${s}`);
    if (missing.length > 20) console.warn(`  ... and ${missing.length - 20} more`);
  } else {
    console.log('i18n coverage 100%');
  }

  const bytes = (s) => `${(s.length / 1024).toFixed(1)} KB`;
  console.log(`synced ${programs.length} programs`);
  console.log(`  programs.json  ${bytes(full)}`);
  console.log(`  index.json     ${bytes(index)}`);
  console.log(`  i18n.json      ${bytes(i18n)} (${Object.keys(dict).length} entries)`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
