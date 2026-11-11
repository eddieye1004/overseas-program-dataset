// web/scripts/e2e-check.mjs
// 用 CDP 在真实浏览器里跑交互断言：侧边栏导航、搜索、筛选、排序、收藏、
// 对比（上限 4）、申请进度看板、智能匹配、数据说明、语言切换与持久化、
// 详情页、移动端布局。无头浏览器 + 真实 DOM，不用装 playwright。
// 用法：node scripts/e2e-check.mjs http://127.0.0.1:8099/
import { spawn } from 'node:child_process';
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const base = process.argv[2] ?? 'http://127.0.0.1:4173/';
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const port = 9600 + Math.floor(Math.random() * 300);
const profile = await mkdtemp(join(tmpdir(), 'cdp-e2e-'));

const proc = spawn(
  EDGE,
  [
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    '--no-first-run',
    '--no-default-browser-check',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    'about:blank',
  ],
  { stdio: 'ignore' },
);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let target = null;
for (let i = 0; i < 80; i++) {
  try {
    const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    target = list.find((t) => t.type === 'page');
    if (target) break;
  } catch {
    /* retry */
  }
  await sleep(250);
}
if (!target) {
  proc.kill();
  throw new Error('CDP target not ready');
}

const ws = new WebSocket(target.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) {
    pending.get(m.id)(m);
    pending.delete(m.id);
  }
});
await new Promise((res, rej) => {
  ws.addEventListener('open', res, { once: true });
  ws.addEventListener('error', rej, { once: true });
});
const send = (method, params = {}) =>
  new Promise((res) => {
    const mid = ++id;
    pending.set(mid, res);
    ws.send(JSON.stringify({ id: mid, method, params }));
  });

await send('Page.enable');
await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', {
  width: 1280,
  height: 900,
  deviceScaleFactor: 1,
  mobile: false,
});

/** 在页面里执行表达式并取回值；页面异常要抛出来，避免假绿 */
async function evalJs(expression) {
  const r = await send('Runtime.evaluate', {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (r.result?.exceptionDetails) {
    throw new Error(
      r.result.exceptionDetails.exception?.description ??
        JSON.stringify(r.result.exceptionDetails),
    );
  }
  return r.result?.result?.value;
}

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

async function goto(hash) {
  await send('Page.navigate', { url: base + hash });
  await sleep(1400);
  // 公网站点时首次导航可能还在 about:blank / 未完成加载，此时 localStorage 会抛
  // SecurityError: Access is denied for this document。轮询到文档真正就绪再继续。
  for (let i = 0; i < 40; i++) {
    const st = await evalJs(
      `({ ready: document.readyState, href: location.href, hasRoot: !!document.querySelector('#root') })`,
    ).catch(() => null);
    if (st?.ready === 'complete' && st.href.startsWith(base) && st.hasRoot) return;
    await sleep(250);
  }
  throw new Error(`goto(${hash}) timed out; last location: ${await evalJs('location.href').catch(() => '?')}`);
}

/** 按可见文本点元素，比 nth-child 稳：布局改动不会让断言挂 */
async function clickByText(text, sel = 'button') {
  return evalJs(`(() => {
    const el = [...document.querySelectorAll(${JSON.stringify(sel)})]
      .find(e => (e.textContent || '').includes(${JSON.stringify(text)}));
    if (!el) return false;
    el.click();
    return true;
  })()`);
}

/** 给 input/select 赋值并触发 React 认识的事件 */
async function setValue(sel, value, tag = 'input', evt = 'input') {
  return evalJs(`(() => {
    const el = document.querySelector(${JSON.stringify(sel)});
    if (!el) return false;
    const proto = ${tag === 'select' ? 'HTMLSelectElement' : 'HTMLInputElement'}.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, ${JSON.stringify(String(value))});
    el.dispatchEvent(new Event(${JSON.stringify(evt)}, { bubbles: true }));
    return true;
  })()`);
}

// 期望条数从数据派生，不写死：新增项目不该让 e2e 变红。
// 注意：这里以前写的是常量 12 / 11 / 7 / 5，注释却声称「从数据派生」。
// 2026-11-01 加第 12 个项目时，sitemap 少了一条 URL 而总数没变，只数条数的
// 断言没抓到——同一类问题。直接读 public/data/index.json，改数据即同步。
const INDEX = JSON.parse(
  await (await import('node:fs/promises')).readFile(
    new URL('../public/data/index.json', import.meta.url),
    'utf8',
  ),
);
const EXPECT_TOTAL = INDEX.length;
const EXPECT_CRITICAL = INDEX.filter((p) => (p.risk_levels ?? []).includes('critical')).length;
const EXPECT_ELIGIBLE = INDEX.filter((p) => p.status === 'eligible').length;
const EXPECT_NOT_ELIGIBLE = INDEX.filter((p) => p.status === 'not_eligible').length;
// 搜索命中数也从数据派生：2026-11-08 加 ca-pgwp 时，写死的「canada 只剩 1 张」
// 直接变红，而实际行为是对的——加拿大本来就有两个项目。
const searchHaystack = (p) =>
  [
    p.name,
    p.name_en,
    p.country,
    p.country_code,
    p.authority ?? '',
    p.visa_code ?? '',
    p.summary,
    p.id,
    ...(p.tags ?? []),
  ]
    .join(' ')
    .toLowerCase();
const EXPECT_CANADA_IDS = INDEX.filter((p) => searchHaystack(p).includes('canada'))
  .map((p) => p.id)
  .sort();
// 长文数量同样派生自 sync-data 生成的 sitemap，避免再加一篇时又漏。
const SITEMAP = await (
  await import('node:fs/promises')
).readFile(new URL('../public/sitemap.xml', import.meta.url), 'utf8');
const GUIDE_COUNT = (SITEMAP.match(/\/guides\//g) ?? []).length;

console.log('\n[1] 首屏渲染（工作台外壳）');
await goto('#/');
await evalJs(`localStorage.clear()`);
await goto('#/');
ok('侧边栏存在', await evalJs(`!!document.querySelector('.sidebar')`));
const navCount = await evalJs(`document.querySelectorAll('.sidebar__item').length`);
ok('侧边栏 7 个导航入口', navCount === 7, `got ${navCount}`);
const brandText = await evalJs(`document.querySelector('.sidebar__name strong')?.textContent ?? ''`);
ok('站点标题非空', brandText.length > 0, brandText);
ok(
  '卡片数 = 数据条数',
  (await evalJs(`document.querySelectorAll('.card').length`)) === EXPECT_TOTAL,
  `got ${await evalJs(`document.querySelectorAll('.card').length`)}`,
);
ok(
  '每张卡片都有详情链接',
  await evalJs(
    `[...document.querySelectorAll('.card')].every(a => (a.querySelector('.card__link')?.getAttribute('href')||'').startsWith('#/p/'))`,
  ),
);
ok(
  '当前导航项高亮且 aria-current',
  await evalJs(`!!document.querySelector('.sidebar__item--on[aria-current="page"]')`),
);

console.log('\n[1b] 首访引导（内联条，不是模态）');
// [1] 刚清过 localStorage，所以这里必然是「全新访客」
ok('全新访客看到引导条', await evalJs(`!!document.querySelector('[data-onboard]')`));
// 收起态高度 <60px：高过这条线，首屏那排卡片就会被顶出去
const obH = await evalJs(
  `Math.round(document.querySelector('[data-onboard]')?.getBoundingClientRect().height ?? -1)`,
);
ok('收起态引导条 <60px，不顶掉首屏卡片', obH > 0 && obH < 60, `got ${obH}px`);
ok(
  '引导条未使用 dialog 语义（不是模态）',
  await evalJs(
    `(() => { const ob = document.querySelector('[data-onboard]'); return !!ob && ob.getAttribute('role') !== 'dialog' && !ob.hasAttribute('aria-modal'); })()`,
  ),
);
ok('引导条不遮挡卡片链接', await evalJs(`!!document.querySelector('.card__link')`));
ok(
  '引导条一句话讲清这个站回答什么问题',
  /能申|适用|eligib/i.test(await evalJs(`document.querySelector('[data-onboard]')?.textContent ?? ''`)),
  (await evalJs(`document.querySelector('[data-onboard]')?.textContent ?? ''`)).slice(0, 40),
);

// 展开：六模块用途 + 三步路径都要出现，且每行的「做什么」不是空的
await evalJs(`document.querySelector('[data-onboard-expand]')?.click()`);
await sleep(350);
ok(
  '展开后显示六个模块的用途',
  (await evalJs(`document.querySelectorAll('[data-onboard] [data-module]').length`)) === 6,
  `got ${await evalJs(`document.querySelectorAll('[data-onboard] [data-module]').length`)}`,
);
ok(
  '展开后显示三步路径',
  (await evalJs(`document.querySelectorAll('[data-onboard] [data-path-step]').length`)) === 3,
);
ok(
  '模块用途不是只重复模块名',
  await evalJs(
    `[...document.querySelectorAll('[data-onboard] [data-module]')].every(tr => (tr.querySelector('td')?.textContent||'').trim().length > 3)`,
  ),
);
ok(
  '展开态写明收录条数',
  /\d+\s*(条|programs)/.test(await evalJs(`document.querySelector('[data-onboard]')?.textContent ?? ''`)),
);

// 跳过必须写盘，刷新后不再出现
await evalJs(`document.querySelector('[data-onboard-expand]')?.click()`);
await sleep(250);
await evalJs(`document.querySelector('[data-onboard-skip]')?.click()`);
await sleep(350);
ok('点跳过后引导条消失', await evalJs(`!document.querySelector('[data-onboard]')`));
ok(
  '点跳过写入了已读标记',
  await evalJs(`localStorage.getItem('opd.onboarded') !== null`),
  await evalJs(`String(localStorage.getItem('opd.onboarded'))`),
);
await goto('#/');
await sleep(700);
ok('刷新后不再打扰（已读标记生效）', await evalJs(`!document.querySelector('[data-onboard]')`));
ok(
  '引导关掉后页面说明回来（老用户看到完整页头）',
  await evalJs(
    `(() => { const p = document.querySelector('.page__intro--list'); return !!p && getComputedStyle(p).display !== 'none'; })()`,
  ),
);

// 数据说明页的「重看」入口：App 常驻，路由切换不会重挂载，靠事件叫回来
await goto('#/about');
await sleep(900);
const replayBtn = await evalJs(`!!document.querySelector('[data-onboard-replay]')`);
ok('数据说明页有「重看引导」入口', replayBtn === true);
if (replayBtn) {
  await evalJs(`document.querySelector('[data-onboard-replay]').click()`);
  await sleep(800);
  ok('点重看后引导条回到列表页并显示', await evalJs(`!!document.querySelector('[data-onboard]')`));
  ok(
    '重看标记读后即清（刷新不会每次弹）',
    await evalJs(`String(localStorage.getItem('opd.replay')) === 'null'`),
    await evalJs(`String(localStorage.getItem('opd.replay'))`),
  );
}

// 收尾：清掉本轮写的标记，后续小节按「看过并关掉」的状态继续
await evalJs(`localStorage.removeItem('opd.onboarded'); localStorage.removeItem('opd.replay');`);
await goto('#/');
await sleep(600);
await evalJs(`document.querySelector('[data-onboard-skip]')?.click()`);
await sleep(300);

console.log('\n[2] 搜索交互（真实输入事件）');
await evalJs(`(() => {
  const input = document.querySelector('input[type=search]');
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  setter.call(input, 'canada');
  input.dispatchEvent(new Event('input', { bubbles: true }));
  return true;
})()`);
await sleep(400);
ok(
  `搜索 canada 后只剩 ${EXPECT_CANADA_IDS.length} 张`,
  (await evalJs(`document.querySelectorAll('.card').length`)) === EXPECT_CANADA_IDS.length,
  await evalJs(`[...document.querySelectorAll('.card__link')].map((a) => a.getAttribute('href')).join(',')`),
);
ok(
  '命中的正好是加拿大的项目',
  JSON.stringify(
    await evalJs(
      `[...document.querySelectorAll('.card__link')].map((a) => a.getAttribute('href').replace('#/p/', '')).sort()`,
    ),
  ) === JSON.stringify(EXPECT_CANADA_IDS),
);
ok('筛选条件写入 URL', await evalJs(`location.hash.includes('q=canada')`));

console.log('\n[3] 清空筛选');
await clickByText('清空筛选');
await sleep(400);
ok(
  '清空后恢复全部',
  (await evalJs(`document.querySelectorAll('.card').length`)) === EXPECT_TOTAL,
);

console.log('\n[4] 资格筛选按钮');
await evalJs(`[...document.querySelectorAll('.chip')].find(c => /大陆护照不可申/.test(c.textContent)).click()`);
await sleep(400);
ok(
  '筛「不可申」张数与数据一致',
  (await evalJs(`document.querySelectorAll('.card').length`)) === EXPECT_NOT_ELIGIBLE,
  `got ${await evalJs(`document.querySelectorAll('.card').length`)}`,
);
ok(
  '所有结果都是 not_eligible',
  await evalJs(`[...document.querySelectorAll('.card')].every(c => c.dataset.status === 'not_eligible')`),
);

console.log('\n[5] 再次点击取消筛选（toggle）');
await evalJs(`[...document.querySelectorAll('.chip')].find(c => /大陆护照不可申/.test(c.textContent)).click()`);
await sleep(400);
ok(
  '取消后回到全部',
  (await evalJs(`document.querySelectorAll('.card').length`)) === EXPECT_TOTAL,
);

console.log('\n[6] 标签 AND 语义');
const tagCounts = await evalJs(`(() => {
  const out = {};
  document.querySelectorAll('.chip').forEach(c => {
    const m = c.textContent.match(/^(.*?)(\\d+)$/);
    if (m) out[m[1].trim()] = Number(m[2]);
  });
  return JSON.stringify(out);
})()`);
const TC = JSON.parse(tagCounts);
const noAgency = TC['无需中介'];
await evalJs(`[...document.querySelectorAll('.chip')].find(c => /^无需中介/.test(c.textContent.trim())).click()`);
await sleep(350);
const t1 = await evalJs(`document.querySelectorAll('.card').length`);
await evalJs(`[...document.querySelectorAll('.chip')].find(c => /^高时薪/.test(c.textContent.trim())).click()`);
await sleep(350);
const t2 = await evalJs(`document.querySelectorAll('.card').length`);
ok('单标签「无需中介」条数与 facet 计数一致', t1 === noAgency, `facet=${noAgency}, rendered=${t1}`);
ok('再加「高时薪」后收窄（AND 生效）', t2 < t1, `before=${t1}, after=${t2}`);
await clickByText('清空筛选');
await sleep(300);

console.log('\n[7] 只看已收藏 / 只看有致命风险（新增开关）');
/** 按 label 文本点开关：.switch 里既有年龄开关也有收藏/风险开关，不能按序号取 */
const toggleSwitch = (label) =>
  evalJs(`(() => {
    const lab = [...document.querySelectorAll('.switch')]
      .find(l => (l.textContent || '').includes(${JSON.stringify(label)}));
    if (!lab) return false;
    lab.querySelector('input').click();
    return true;
  })()`);
await evalJs(`document.querySelectorAll('.card__save')[0].click()`);
await sleep(300);
ok('找到「只看已收藏」开关', (await toggleSwitch('只看已收藏')) === true);
await sleep(400);
const savedOnlyCount = await evalJs(`document.querySelectorAll('.card').length`);
ok('只看已收藏后只剩 1 张', savedOnlyCount === 1, `got ${savedOnlyCount}`);
ok('开关状态写入 URL', await evalJs(`location.hash.includes('sv=1')`));
await toggleSwitch('只看已收藏');
await sleep(400);
ok(
  '关掉后回到全部',
  (await evalJs(`document.querySelectorAll('.card').length`)) === EXPECT_TOTAL,
);
await toggleSwitch('只看有致命风险');
await sleep(400);
const criticalCount = await evalJs(`document.querySelectorAll('.card').length`);
// 11 条数据里 10 条至少含一个 critical 级风险，写死数字但由数据实测得来
ok('只看致命风险后只剩带 critical 的条数', criticalCount === EXPECT_CRITICAL, `got ${criticalCount}`);
ok(
  '结果卡片都带 critical 风险',
  await evalJs(
    `[...document.querySelectorAll('.card')].every(c => c.dataset.risk?.includes('critical'))`,
  ),
);
await toggleSwitch('只看有致命风险');
await sleep(400);

console.log('\n[8] 排序下拉');
await setValue('.listbar select', 'stay', 'select', 'change');
await sleep(400);
ok('排序写入 URL', await evalJs(`location.hash.includes('o=stay')`));
ok(
  '停留期排序后仍渲染全部',
  (await evalJs(`document.querySelectorAll('.card').length`)) === EXPECT_TOTAL,
);
ok('localStorage 里已有 1 条收藏', await evalJs(`(JSON.parse(localStorage.getItem('opd.saved')||'[]')).length === 1`));
ok(
  '侧边栏收藏计数出现 1',
  await evalJs(`[...document.querySelectorAll('.sidebar__count')].some(n => n.textContent.trim() === '1')`),
);

console.log('\n[9] 收藏页');
await goto('#/saved');
ok('收藏页显示 1 张卡', (await evalJs(`document.querySelectorAll('.card').length`)) === 1);
ok(
  '收藏页标题是收藏',
  await evalJs(`/收藏|Saved/.test(document.querySelector('.page__title')?.textContent ?? '')`),
);

console.log('\n[10] 对比清单（上限 4）');
const cmpIds = ['au-462-work-holiday', 'ca-iec-working-holiday', 'jp-working-holiday', 'nz-china-whv'];
for (const pid of cmpIds) {
  await goto('#/p/' + pid);
  // 详情页在数据 fetch 完成前只渲染 .state，此时按钮不存在。
  // 公网上 fetch 慢，硬 sleep 会导致点击落空（本地 8099 却刚好够），必须轮询。
  for (let i = 0; i < 40; i++) {
    const ready = await evalJs(`!!document.querySelector('.detail__actions button')`);
    if (ready) break;
    await sleep(200);
  }
  await evalJs(
    `[...document.querySelectorAll('.detail__actions button')].find(b => /对比/.test(b.textContent))?.click()`,
  );
  await sleep(400);
}
ok(
  '四个项目已加入对比',
  (await evalJs(`(JSON.parse(localStorage.getItem('opd.compare')||'[]')).length`)) === 4,
);
await goto('#/p/uk-youth-mobility-scheme');
for (let i = 0; i < 40; i++) {
  const ready = await evalJs(`!!document.querySelector('.detail__actions button')`);
  if (ready) break;
  await sleep(200);
}
ok(
  '第 5 个时对比按钮禁用（上限生效）',
  await evalJs(
    `[...document.querySelectorAll('.detail__actions button')].find(b => /对比/.test(b.textContent))?.disabled === true`,
  ),
);
await goto('#/compare');
ok('对比页标题是对比', await evalJs(`/对比|Compare/.test(document.querySelector('.page__title')?.textContent ?? '')`));
ok('对比页渲染 4 列', await evalJs(`!!document.querySelector('.cmp')`));
ok(
  '对比表有字段行',
  (await evalJs(`document.querySelectorAll('.cmp__row').length`)) >= 8,
  String(await evalJs(`document.querySelectorAll('.cmp__row').length`)),
);
await clickByText('清空');
await sleep(350);
ok(
  '清空后对比为空',
  (await evalJs(`(JSON.parse(localStorage.getItem('opd.compare')||'[]')).length`)) === 0,
);

console.log('\n[11] 申请进度看板');
await goto('#/p/jp-working-holiday');
await evalJs(
  `[...document.querySelectorAll('.detail__actions button')].find(b => /加入我的申请/.test(b.textContent))?.click()`,
);
await sleep(350);
ok(
  '加入后 localStorage 有 opd.track',
  (await evalJs(`Object.keys(JSON.parse(localStorage.getItem('opd.track')||'{}')).length`)) === 1,
);
await goto('#/track');
ok('看板出现 1 行', (await evalJs(`document.querySelectorAll('.trackrow').length`)) === 1);
ok('状态计数条 6 项', (await evalJs(`document.querySelectorAll('.stat').length`)) === 6);
await setValue('.trackrow select', 'interview', 'select', 'change');
await sleep(350);
ok(
  '切换状态写入 localStorage',
  await evalJs(`Object.values(JSON.parse(localStorage.getItem('opd.track')||'{}'))[0].status === 'interview'`),
);
// 备注框没有显式 type 属性，[type=text] 选择器匹配不到，按 class 取
await setValue('.trackrow__note', '已约 11 月 5 日面试', 'input', 'input');
await sleep(350);
ok(
  '备注写入 localStorage',
  await evalJs(
    `Object.values(JSON.parse(localStorage.getItem('opd.track')||'{}'))[0].note.includes('11 月 5 日')`,
  ),
);

console.log('\n[11b] 看板给出「下一步」');
// 这一段守的是「看板不只是备忘录」：项目进了跟进列表后，
// 页面必须自己算出什么时候该动手，而不是等人去翻窗口日期。
ok(
  '看板有今日待办区',
  (await evalJs(`document.querySelectorAll('[data-nextup]').length`)) === 1,
);
ok(
  '今日待办区有标题',
  (await evalJs(
    `(document.querySelector('[data-nextup] .nextup__title')?.textContent ?? '').trim().length > 3`,
  )),
);
// jp-working-holiday 的 2026 窗口 10 月 30 日已关、2027 未公布 →
// 必须落到「上一轮已结束」而不是什么都不说
const jpNext = await evalJs(
  `document.querySelector('.trackrow__next')?.textContent ?? ''`,
);
ok('未能给出具体动作的条目也会说明原因（不静默）', jpNext.trim().length > 0, jpNext);
ok(
  '已关闭的窗口会点出关闭日期',
  /2026-10-30|10 月 30|已结束|closed/i.test(jpNext),
  jpNext,
);
// 把一条有未来窗口的项目加进来，验证「今天先做这几件」真的会挑出来
await goto('#/p/au-462-work-holiday');
await evalJs(
  `[...document.querySelectorAll('.detail__actions button')].find(b => /加入我的申请/.test(b.textContent))?.click()`,
);
await sleep(350);
await goto('#/track');
ok(
  '两条跟进时时间轴仍只取最紧的（≤3 条）',
  (await evalJs(`document.querySelectorAll('.nextup__item').length`)) <= 3,
);

console.log('\n[12] 智能匹配');
await goto('#/match');
ok('匹配页有条件表单', await evalJs(`!!document.querySelector('.profile')`));
ok('未填条件时显示提示', await evalJs(`!!document.querySelector('.state')`));
await setValue('.profile input[type=number]', '20');
await sleep(500);
const matchCards = await evalJs(`document.querySelectorAll('.card').length`);
ok('填条件后出现全部结果', matchCards === EXPECT_TOTAL, `got ${matchCards}`);
ok('卡片显示匹配分', await evalJs(`!!document.querySelector('.score')`));
ok('卡片显示匹配理由', (await evalJs(`document.querySelectorAll('.rsn').length`)) > 0);
const scores = JSON.parse(
  await evalJs(`JSON.stringify([...document.querySelectorAll('.score')].map(s => Number(s.textContent)))`),
);
ok('分数按降序排列', scores.every((v, i) => i === 0 || scores[i - 1] >= v), JSON.stringify(scores));
ok('画像写入 localStorage', await evalJs(`JSON.parse(localStorage.getItem('opd.profile')||'{}').age === 20`));
ok('最佳项有 best 高亮', await evalJs(`!!document.querySelector('.score--best')`));
ok(
  '硬性不合格项分数被压到 30 以下',
  await evalJs(`[...document.querySelectorAll('.card')].every(c => {
    const hasFail = !!c.querySelector('.rsn--fail');
    if (!hasFail) return true;
    const s = Number(c.querySelector('.score')?.textContent ?? '999');
    return s <= 30;
  })`),
);
await clickByText('清空');
await sleep(350);
ok('清空条件后回到提示态', await evalJs(`!!document.querySelector('.state')`));

console.log('\n[12b] 身份：在读 vs 在职');
ok(
  '匹配页有「当前身份」下拉',
  await evalJs(
    `[...document.querySelectorAll('.profile .pfield__label')].some(l => l.textContent.includes('身份'))`,
  ),
);

// 在职：选 working，要求在读证明的项目应出现 fail 理由
await setValue('.profile .student-sel', 'working', 'select', 'change');
await sleep(700);
const workingFails = await evalJs(
  `JSON.stringify([...document.querySelectorAll('.card')].map(c => ({
     id: c.querySelector('.card__link')?.getAttribute('href') || '',
     fail: [...c.querySelectorAll('.rsn--fail')].map(x => x.textContent).join('|'),
   })).filter(x => x.fail.includes('在读')))`,
);
ok('在职时出现「要求在读证明」的 fail 理由', JSON.parse(workingFails || '[]').length > 0, workingFails);
ok(
  '在职时被压的是 IAESTE 与 J-1',
  (() => {
    const ids = JSON.parse(workingFails || '[]').map((r) => r.id).join(',');
    return ids.includes('global-iaeste') && ids.includes('us-j1-summer-work-travel');
  })(),
  workingFails,
);

// 在读：切回 enrolled，同两条的 fail 应消失
await setValue('.profile .student-sel', 'enrolled', 'select', 'change');
await sleep(700);
const enrolledFails = await evalJs(
  `[...document.querySelectorAll('.card')].filter(c =>
     [...c.querySelectorAll('.rsn--fail')].some(x => x.textContent.includes('在读'))).length`,
);
ok('切回在读后「要求在读」的 fail 消失', enrolledFails === 0, `got ${enrolledFails}`);
await clickByText('清空');
await sleep(350);

console.log('\n[13] 数据说明页');
await goto('#/about');
// 五格：收录 / 可申 / 不可申 / 来源数 / 即将到期。
// 第五格是 2026-11-10 加复核台账时补的——数据说明页要能提前说
// 「哪几条快到期了」，所以它不能是四格。
ok('五个统计数字', (await evalJs(`document.querySelectorAll('.stat').length`)) === 5);
ok(
  '数据表行数 = 数据条数',
  (await evalJs(`document.querySelectorAll('.dtable tbody tr').length`)) === EXPECT_TOTAL,
);
ok(
  '收录数 = 数据条数',
  (await evalJs(`document.querySelector('.stat__num')?.textContent.trim()`)) === String(EXPECT_TOTAL),
);

console.log('\n[14] 语言切换 + 持久化');
await goto('#/');
ok(
  '默认中文模式标题',
  (await evalJs(`document.querySelector('.sidebar__name strong').textContent`)).includes('海外项目'),
);
await evalJs(`document.querySelector('.langswitch').click()`);
await sleep(600);
const enTitle = await evalJs(`document.querySelector('.sidebar__name strong').textContent`);
ok('切到 EN 后标题变英文', enTitle.includes('Overseas'), enTitle);
ok('html lang 同步为 en', (await evalJs(`document.documentElement.lang`)) === 'en');
ok('localStorage 记下语言', (await evalJs(`localStorage.getItem('opd.lang')`)) === 'en');
const cardTitleEn = await evalJs(`document.querySelector('.card__title').textContent.trim()`);
ok('卡片标题切换为英文名（无中日韩字符）', !/[\u4e00-\u9fff\u3040-\u30ff]/.test(cardTitleEn), cardTitleEn);
ok(
  '侧边栏导航也切英文',
  await evalJs(
    `[...document.querySelectorAll('.sidebar__item')].some(e => /Programs|Smart match|Saved|Compare/i.test(e.textContent))`,
  ),
);

console.log('\n[15] 刷新后语言保持');
await send('Page.navigate', { url: base + '#/' });
await sleep(1600);
ok(
  '刷新后仍是英文',
  (await evalJs(`document.querySelector('.sidebar__name strong').textContent`)).includes('Overseas'),
);

console.log('\n[16] 详情页（英文模式）+ 三个动作按钮');
await goto('#/p/jp-working-holiday');
await sleep(600);
ok(
  '详情页标题为英文名',
  (await evalJs(`document.querySelector('.detail__title')?.textContent ?? ''`)).includes('Japan'),
);
ok('有护照资格警示块', await evalJs(`!!document.querySelector('.callout--warn')`));
ok('有官方链接按钮', await evalJs(`!!document.querySelector('a.btn--primary[href^="https://"]')`));
ok('来源区列出 primary 徽标', await evalJs(`!!document.querySelector('.srcdot--p')`));
const actBtns = await evalJs(`document.querySelectorAll('.detail__actions button').length`);
ok('详情页有三个本地动作按钮', actBtns === 3, `got ${actBtns}`);

console.log('\n[17] 切回中文并检查详情页');
await evalJs(`document.querySelector('.langswitch').click()`);
await sleep(650);
ok(
  '切回中文后标题的中文名',
  (await evalJs(`document.querySelector('.detail__title')?.textContent ?? ''`)).includes('日本'),
);

console.log('\n[18] 直接访问不存在的项目 id');
await goto('#/p/does-not-exist');
await sleep(700);
ok('显示空状态而非白屏', await evalJs(`!!document.querySelector('.state')`));
ok('提供返回按钮', await evalJs(`!!document.querySelector('.state button')`));

console.log('\n[19] 未知路由回落列表');
await goto('#/nope');
await sleep(800);
ok(
  '未知 hash 回落到项目库',
  (await evalJs(`document.querySelectorAll('.card').length`)) === EXPECT_TOTAL,
);

console.log('\n[20] 无障碍基础');
await goto('#/');
ok('语言按钮有 aria-label', await evalJs(`!!document.querySelector('.langswitch').getAttribute('aria-label')`));
ok('搜索框有可访问名称', await evalJs(`!!document.querySelector('input[type=search]').getAttribute('aria-label')`));
ok('筛选组用 fieldset/legend', (await evalJs(`document.querySelectorAll('fieldset.chips').length`)) >= 3);
ok(
  '当前导航有 aria-current=page',
  await evalJs(`document.querySelector('.sidebar__item--on')?.getAttribute('aria-current') === 'page'`),
);
ok('收藏按钮有 aria-pressed', await evalJs(`document.querySelector('.card__save').hasAttribute('aria-pressed')`));

console.log('\n[21] 移动端（390px）');
await send('Emulation.setDeviceMetricsOverride', {
  width: 390,
  height: 844,
  deviceScaleFactor: 1,
  mobile: true,
});
await sleep(800);
const mob = JSON.parse(
  await evalJs(`JSON.stringify({
    sw: document.documentElement.scrollWidth,
    cw: document.documentElement.clientWidth,
    cols: getComputedStyle(document.querySelector('.grid')).gridTemplateColumns.split(' ').length,
    navDir: getComputedStyle(document.querySelector('.sidebar__nav')).flexDirection
  })`),
);
ok('390px 无横向溢出', mob.sw <= mob.cw, JSON.stringify(mob));
ok('390px 单列布局', mob.cols === 1, JSON.stringify(mob));
ok('390px 侧栏变横向导航条', mob.navDir === 'row', JSON.stringify(mob));

console.log('\n[22] 信息架构补强：页面标题 / 来源可视化 / 空结果引导');
await goto('#/');
await sleep(700);
{
  // hash 路由不会自动改 document.title，靠 useDocumentTitle 显式写
  const t1 = await evalJs(`document.title`);
  ok('列表页标签页标题含页面名', /项目库|Programs/.test(t1), t1);

  // 卡片上直接能看到「几条来源 / 几条官方 / 核实于哪天」
  // 2026-10-31 改版把这三项压进一行 .card__factsline，选择器随之调整
  ok(
    '卡片显示来源计数',
    await evalJs(
      `[...document.querySelectorAll('.card__factsline')].every(el => /来源|Sources/.test(el.textContent))`,
    ),
  );
  ok(
    '卡片显示核实日期',
    await evalJs(
      `[...document.querySelectorAll('.card__factsline')].every(el => /\\d{4}-\\d{2}-\\d{2}/.test(el.textContent))`,
    ),
  );

  // 键盘用户的第一个 Tab 位
  ok('存在跳到主内容的链接', await evalJs(`!!document.querySelector('a.skiplink[href="#main"]')`));

  // 空结果时逐个列出生效条件，而不是只给一个笼统的重置
  await evalJs(`(() => {
    const el = document.querySelector('input[type=search]');
    const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    set.call(el, 'zzzz-no-such-program');
    el.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  })()`);
  await sleep(600);
  const relax = await evalJs(`document.querySelectorAll('.relax__chip').length`);
  ok('空结果给出可单独移除的条件', relax >= 1, `got ${relax}`);

  // 点掉那条条件应回到有结果的状态
  await evalJs(`document.querySelector('.relax__chip').click()`);
  await sleep(700);
  const back = await evalJs(`document.querySelectorAll('.card').length`);
  ok('点掉条件后恢复结果', back === EXPECT_TOTAL, `got ${back}`);
}

await goto('#/p/ca-iec-working-holiday');
await sleep(900);
{
  const t2 = await evalJs(`document.title`);
  ok('详情页标签页标题含项目名', /加拿大|IEC|International Experience/.test(t2), t2);
  // 域名单独渲染，读者才能判断来源落在哪个站
  const host = await evalJs(`document.querySelector('.srcurl')?.textContent ?? ''`);
  ok('来源区显示域名', host.includes('canada.ca'), host);
  ok(
    '来源区有 primary 计数',
    await evalJs(`!!document.querySelector('.srcsum__item--p strong')`),
  );
}

console.log('\n[23] SEO 基础件：robots / sitemap / favicon / OG / JSON-LD');

{
  // 这些是爬虫与分享卡片依赖的静态文件，构建漏拷会静默 404，必须实测
  const probe = await evalJs(`(async () => {
    const get = async (p) => {
      try {
        const r = await fetch(p, { cache: 'no-store' });
        return { ok: r.ok, status: r.status, text: r.ok ? await r.text() : '' };
      } catch (e) {
        return { ok: false, status: 0, text: '' };
      }
    };
    const [robots, sitemap, icon, ogimg, manifest, icon192, icon512, maskable, apple] =
      await Promise.all([
        get('./robots.txt'),
        get('./sitemap.xml'),
        get('./favicon.svg'),
        get('./og.png'),
        get('./manifest.webmanifest'),
        get('./icons/icon-192.png'),
        get('./icons/icon-512.png'),
        get('./icons/icon-maskable-512.png'),
        get('./icons/apple-touch-icon.png'),
      ]);
    let mf = null;
    try { mf = JSON.parse(manifest.text); } catch (e) { mf = null; }
    // 只在内存里比对 PNG 魔数，不把二进制写进返回值
    const isPng = (t) => t.startsWith('\\uFFFDPNG');
    return {
      manifestOk: manifest.ok,
      manifestJson: mf,
      pngOk: isPng(icon192.text) && isPng(icon512.text) && isPng(maskable.text) && isPng(apple.text),
      manifestHref: document.querySelector('link[rel="manifest"]')?.getAttribute('href') ?? '',
      appleTouchHref:
        document.querySelector('link[rel="apple-touch-icon"]')?.getAttribute('href') ?? '',
      themeColor: document.querySelector('meta[name="theme-color"]')?.content ?? '',
      pngIconHref:
        document.querySelector('link[rel="icon"][sizes="192x192"]')?.getAttribute('href') ?? '',
      robotsOk: robots.ok,
      robotsSitemap: /Sitemap:\\s*https:\\/\\//i.test(robots.text),
      sitemapOk: sitemap.ok,
      sitemapUrls: (sitemap.text.match(/<loc>/g) || []).length,
      sitemapText: sitemap.text,
      iconOk: icon.ok && /<svg/i.test(icon.text),
      // 分享图必须是真 PNG（前 8 字节魔数），不是占位 SVG
      ogImageOk: ogimg.ok && ogimg.text.startsWith('\\uFFFDPNG'),
      ogImageTag: document.querySelector('meta[property="og:image"]')?.content ?? '',
      ogImageSize: (document.querySelector('meta[property="og:image:width"]')?.content ?? '') + 'x' +
        (document.querySelector('meta[property="og:image:height"]')?.content ?? ''),
      canonical: document.querySelector('link[rel="canonical"]')?.href ?? '',
      ogTitle: document.querySelector('meta[property="og:title"]')?.content ?? '',
      ogDesc: document.querySelector('meta[property="og:description"]')?.content ?? '',
      ogLocale: document.querySelector('meta[property="og:locale"]')?.content ?? '',
      twCard: document.querySelector('meta[name="twitter:card"]')?.content ?? '',
      twImage: document.querySelector('meta[name="twitter:image"]')?.content ?? '',
      ldType: (() => {
        try {
          return JSON.parse(document.querySelector('script[type="application/ld+json"]').textContent)['@type'];
        } catch (e) { return ''; }
      })(),
      iconHref: document.querySelector('link[rel="icon"]')?.getAttribute('href') ?? '',
    };
  })()`);

  ok('robots.txt 可访问', probe.robotsOk === true);
  ok('robots.txt 指向 sitemap', probe.robotsSitemap === true);
  ok('sitemap.xml 可访问', probe.sitemapOk === true);
  // 条数对不等于内容对：2026-11-01 加第 12 个项目时 sitemap 少一条 URL，
  // 但总数仍是 12（首页 + 11 个旧项目），只数条数的断言没抓到。
  // 所以这里逐 id 比对——但 id 列表从 INDEX 派生，不写死：
  // 写死 12 个 id 的版本在 2026-11-08 加到 26 个项目后仍在检查早已删除的旧集合。
  //
  // 2026-11-09：详情页 URL 从 `#/p/<id>` 改成真路径 `/p/<id>.html`。
  // hash 片段不被搜索引擎当作独立页面，旧 sitemap 里那 26 条等于 0 条可索引页。
  const smText = String(probe.sitemapText ?? '');
  const smMissing = INDEX.map((p) => p.id).filter(
    (id) => !smText.includes(`/p/${id}.html`),
  );
  ok(
    'sitemap 覆盖全部项目详情页（真路径，非 hash）',
    smMissing.length === 0,
    `缺 ${smMissing.length} 条: ${smMissing.join(', ')}`,
  );
  // 反向也要查：不能再退回 hash 形式，否则等于没修
  ok(
    'sitemap 不再使用 #/p/ 形式的片段 URL',
    !smText.includes('#/p/'),
    `仍有 ${(smText.match(/#\/p\//g) ?? []).length} 条 hash URL`,
  );
  // 首页 + 每个项目真页面 + /p/ 索引页 + 每篇长文（长文条数由 sitemap 里的
  // /guides/ 计数派生，这里只校验「不重复、不缺项目」，长文覆盖由 [27] 负责）
  ok(
    'sitemap 条数 = 首页 + 项目数 + /p/ 索引页 + 长文数',
    probe.sitemapUrls === 2 + EXPECT_TOTAL + GUIDE_COUNT,
    `got ${probe.sitemapUrls}, 应为 ${2 + EXPECT_TOTAL + GUIDE_COUNT}（首页 + /p/ 索引 + 项目 ${EXPECT_TOTAL} + 长文 ${GUIDE_COUNT}）`,
  );
  ok('favicon.svg 是可解析的 SVG', probe.iconOk === true);
  ok('index.html 用真 favicon 而非空 data URI', probe.iconHref.includes('favicon.svg'), probe.iconHref);
  ok('canonical 指向站点根', probe.canonical.endsWith('/overseas-program-dataset/'), probe.canonical);
  ok('og:title 存在', probe.ogTitle.length > 0, probe.ogTitle);
  ok('og:description 存在', probe.ogDesc.length > 0);
  ok('og:locale 声明 zh_CN', probe.ogLocale === 'zh_CN', probe.ogLocale);
  ok('twitter:card 存在', probe.twCard.length > 0, probe.twCard);
  ok('og:image 指向绝对 URL', /^https:\/\/.*\/og\.png$/.test(probe.ogImageTag), probe.ogImageTag);
  ok('og:image 尺寸声明 1200x630', probe.ogImageSize === '1200x630', probe.ogImageSize);
  ok('og.png 是真实 PNG', probe.ogImageOk === true);
  ok('twitter:image 与 og:image 一致', probe.twImage === probe.ogImageTag);
  ok('JSON-LD @type 为 Dataset', probe.ldType === 'Dataset', probe.ldType);

  console.log('\n[23b] 可安装（PWA manifest 与图标）');
  // 目标不是「有个 manifest 文件」，而是 iOS / Android 都能「添加到主屏幕」并当独立应用打开。
  // 缺 192 或 512 的 any 图标、缺 maskable、图标不是真 PNG，浏览器会静默降级成普通书签。
  const mf = probe.manifestJson ?? {};
  const icons = Array.isArray(mf.icons) ? mf.icons : [];
  const has = (sizes, purpose) =>
    icons.some((i) => i.sizes === sizes && (i.purpose ?? 'any') === purpose);
  ok('manifest.webmanifest 可访问且是合法 JSON', probe.manifestOk === true && probe.manifestJson !== null);
  ok('index.html 声明了 manifest', probe.manifestHref.includes('manifest.webmanifest'), probe.manifestHref);
  ok('manifest 有 name 与 short_name', !!mf.name && !!mf.short_name, `${mf.name} / ${mf.short_name}`);
  ok(
    'manifest start_url 与 scope 都是站点内相对路径',
    mf.start_url === './' && mf.scope === './',
    `${mf.start_url} / ${mf.scope}`,
  );
  ok('manifest display 为 standalone', mf.display === 'standalone', String(mf.display));
  ok('manifest theme_color 与页面一致', mf.theme_color === probe.themeColor && !!probe.themeColor, `${mf.theme_color} vs ${probe.themeColor}`);
  ok('manifest 含 192×192 的 any 图标', has('192x192', 'any'));
  ok('manifest 含 512×512 的 any 图标', has('512x512', 'any'));
  // maskable 必须有独立一张、且尺寸缩到安全区内，否则安卓把 P 字裁掉
  ok('manifest 含 maskable 图标', has('512x512', 'maskable'));
  ok('四张图标都是真 PNG', probe.pngOk === true);
  ok('apple-touch-icon 指向 180px PNG', probe.appleTouchHref.endsWith('apple-touch-icon.png'), probe.appleTouchHref);
  ok('页面有 iOS standalone 声明', await evalJs(`!!document.querySelector('meta[name="apple-mobile-web-app-capable"], meta[name="mobile-web-app-capable"]')`) === true);
  // 静态真路径页也带 manifest：从搜索结果直接落到详情页的人，同样能安装
  const pHtml = await (await fetch(`${base}p/au-462-work-holiday.html`)).text();
  ok('项目静态页也声明 manifest', /rel="manifest"/.test(pHtml));
  ok('项目静态页也带 apple-touch-icon', /apple-touch-icon\.png/.test(pHtml));
}

console.log('\n[24] 未核实值不显示为假数字');
{
  // 官方没公布年龄的项目（AIESEC）在数据里是 0–99 占位，卡片必须显示「未核实」而不是「0–99」
  await goto('#/p/global-aiesec-global-talent');
  await sleep(900);
  const ageRow = await evalJs(`(() => {
    const rows = [...document.querySelectorAll('.kv')];
    const hit = rows.find((r) => (r.querySelector('dt')?.textContent ?? '').includes('年龄'));
    return hit ? hit.querySelector('dd').textContent : '';
  })()`);
  ok('未公布年龄的项目显示「未核实」', ageRow.includes('未核实'), ageRow);
  ok('不再出现裸露的 0–99 区间', !/0\s*[–-]\s*99/.test(ageRow), ageRow);

  const feeRow = await evalJs(`(() => {
    const rows = [...document.querySelectorAll('.kv')];
    const hit = rows.find((r) => (r.querySelector('dt')?.textContent ?? '').includes('费用'));
    return hit ? hit.querySelector('dd').textContent : '';
  })()`);
  ok('费用为空时明说官方未公布', feeRow.includes('官方页面未公布'), feeRow);
}

console.log('\n[24b] 配额四态各自渲染成不同的东西');
{
  // 四态化之前，这四条在页面上长得一模一样：都只有一句 note，
  // 读者分不出「确定没有上限」和「我们还没查」。这组断言把「不合并」钉住。
  const quotaRow = async (pid) => {
    await goto(`#/p/${pid}`);
    await sleep(700);
    return evalJs(`(() => {
      const rows = [...document.querySelectorAll('.kv')];
      const hit = rows.find((r) => (r.querySelector('dt')?.textContent ?? '').includes('名额'));
      return hit ? hit.querySelector('dd').textContent.trim() : '';
    })()`);
  };

  // capped：要同时出现数字和「同时在册」的口径说明
  const sg = await quotaRow('sg-work-holiday-programme');
  ok('capped 显示具体数字', /2,000/.test(sg), sg);
  ok('capped 标出「同时在册」口径而不是年度发放', sg.includes('同时在册'), sg);

  // capped + 年度口径：不能误标成同时在册
  const nz = await quotaRow('nz-china-whv');
  ok('capped 年度口径不写「同时在册」', /1,000/.test(nz) && !nz.includes('同时在册'), nz);

  // not_published：有状态词，且不得出现任何数字当作名额
  const hpi = await quotaRow('uk-hpi-visa');
  ok('not_published 说「未公布数字」', hpi.includes('未公布'), hpi);
  ok('not_published 不把限额伪装成数字', !/^\d|：\s*\d/.test(hpi), hpi);

  // unverified：必须是「待核实」，不能落成空白，也不能落成「无上限」
  const at = await quotaRow('at-rwr-card-vhq');
  ok('unverified 显示「待核实」', at.includes('待核实'), at);
  ok('unverified 不被说成「无名额上限」', !at.includes('无名额上限'), at);

  // no_quota：对大陆护照不可申的项目也要说清是哪种「没有」
  const jp = await quotaRow('jp-working-holiday');
  ok('no_quota 显示「无名额上限」', jp.includes('无名额上限'), jp);
  ok('no_quota 解释里点明大陆护照不在协议内', /不在.{0,8}名单|不分配名额/.test(jp), jp);
}

console.log('\\n[25] 信息架构改版：结论条 / 折叠筛选 / 推叠卡片预算');
{
  await send('Emulation.setDeviceMetricsOverride', {
    width: 1280,
    height: 900,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await goto('#/');
  await sleep(700);

  // 结论条：访客第一个问题是「我能申什么」，这两个数字必须首屏就有
  const stats = await evalJs(
    `JSON.stringify([...document.querySelectorAll('.statsbar__item')].map(e => e.textContent.trim()))`,
  );
  const S = JSON.parse(stats);
  ok('首屏有结论条', S.length >= 3, stats);
  // 「大陆护照可申」本身包含「可申」二字，所以不能只测子串，
  // 用前缀数字 + 是否含「不可申」三字区分两种。
  ok(
    '结论条含不可申计数',
    S.some((s) => s.startsWith(String(EXPECT_NOT_ELIGIBLE)) && s.includes('不可申')),
    stats,
  );
  // 在职可申必须严格小于可申总数：差额就是那几条有学籍门槛的项目。
  // 这条防的是「两个数字算成一样」——那说明 enrollment_scope 没进派生逻辑。
  // 它是可申数的括号附注，不是一个独立并列项，所以数值用正则从「在职可申 3」里取。
  ok(
    '结论条含在职可申，且小于可申总数',
    S.some((s) => {
      if (!s.includes('在职可申')) return false;
      const m = s.match(/在职可申\s*(\d+)/);
      if (!m) return false;
      const n = Number(m[1]);
      return Number.isFinite(n) && n > 0 && n < EXPECT_ELIGIBLE;
    }),
    stats,
  );
  ok(
    '结论条含可申计数',
    S.some(
      (s) => s.startsWith(String(EXPECT_ELIGIBLE)) && s.includes('可申') && !s.includes('不可申'),
    ),
    stats,
  );

  // 默认排序把可申的排前面，第一张卡必须是 eligible
  ok(
    '默认排序首卡可申',
    (await evalJs(`document.querySelector('.card')?.dataset.status`)) === 'eligible',
  );
  ok(
    '排序下拉默认选中「可申优先」',
    (await evalJs(`document.querySelector('.listbar select')?.value`)) === 'eligible',
  );

  // 「我的资格」必须排在第一组（搜索之后），而不是夹在类型和标签之间
  const firstLegend = await evalJs(
    `document.querySelectorAll('.filters fieldset.chips legend')[0]?.textContent ?? ''`,
  );
  ok('第一组筛选是「我的资格」', /资格|eligibility/i.test(firstLegend), firstLegend);
  ok(
    '资格按钮是双栏大按钮',
    await evalJs(`!!document.querySelector('.chips--pair .chip')`),
  );

  // 折叠：默认收起，展开后显示更多条件
  ok('折叠区默认收起', await evalJs(`document.querySelector('.filters__extra')?.hidden === true`));
  ok(
    '更多筛选按钮 aria-expanded=false',
    (await evalJs(`document.querySelector('.filters__more')?.getAttribute('aria-expanded')`)) ===
      'false',
  );
  await evalJs(`document.querySelector('.filters__more').click()`);
  await sleep(400);
  ok('展开后折叠区可见', await evalJs(`document.querySelector('.filters__extra')?.hidden === false`));
  await evalJs(`document.querySelector('.filters__more').click()`);
  await sleep(400);

  // 重复计数必须已删除：结果数只在 .listbar 出现一次
  ok('筛选区不再重复显示结果计数', await evalJs(`!document.querySelector('.filters__count')`));

  // 卡片预算：≤220px 才能让桌面首屏露出 2 张以上完整卡片
  const cardH = await evalJs(`Math.round(document.querySelector('.card').getBoundingClientRect().height)`);
  ok('卡片高度 ≤240px', cardH <= 240, `got ${cardH}px`);
  const fullCards = await evalJs(
    `[...document.querySelectorAll('.card')].filter(c => { const r = c.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }).length`,
  );
  ok('桌面首屏露出 ≥2 张完整卡片', fullCards >= 2, `got ${fullCards}`);

  // 移动端抽屉：<720px 筛选面板收成一条，首屏必须出现卡片
  await send('Emulation.setDeviceMetricsOverride', {
    width: 390,
    height: 844,
    deviceScaleFactor: 1,
    mobile: true,
  });
  await sleep(600);
  await goto('#/');
  await sleep(800);
  const m = JSON.parse(
    await evalJs(`(() => {
      const f = document.querySelector('.filters');
      return JSON.stringify({
        sheetVisible: !!document.querySelector('.filters__sheetbtn') &&
          getComputedStyle(document.querySelector('.filters__sheetbtn')).display !== 'none',
        bodyHidden: getComputedStyle(document.querySelector('.filters__body')).display === 'none',
        filtersH: Math.round(f.getBoundingClientRect().height),
        gridTop: Math.round(document.querySelector('.grid').getBoundingClientRect().top),
        vh: innerHeight,
      });
    })()`),
  );
  ok('移动端有筛选抽屉按钮', m.sheetVisible, JSON.stringify(m));
  ok('移动端筛选体默认收起', m.bodyHidden, JSON.stringify(m));
  ok('移动端筛选条高度 <120px', m.filtersH < 120, `got ${m.filtersH}px`);
  ok('移动端首屏能看到卡片网格', m.gridTop < m.vh, `gridTop=${m.gridTop}, vh=${m.vh}`);

  await evalJs(`document.querySelector('.filters__sheetbtn').click()`);
  await sleep(500);
  ok(
    '点开抽屉后筛选体可见',
    await evalJs(`getComputedStyle(document.querySelector('.filters__body')).display !== 'none'`),
  );

  await send('Emulation.setDeviceMetricsOverride', {
    width: 1280,
    height: 900,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await sleep(400);
}

console.log('\\n[26] 详情页判定条 + 来源锚点');
{
  await goto('#/p/ca-iec-working-holiday');
  await sleep(900);
  const v = await evalJs(`document.querySelector('.verdict')?.textContent ?? ''`);
  ok('详情页标题下有判定条', v.length > 0, v.slice(0, 60));
  ok('判定条写明不可申', /不可申|Not open/.test(v), v.slice(0, 60));
  ok(
    '判定条带来源跳转按钮',
    (await evalJs(`document.querySelector('.verdict__src')?.tagName`)) === 'BUTTON',
  );
  ok('来源区块有 id=sources', await evalJs(`!!document.querySelector('#sources')`));
  // 锚点必须真能滚过去：位置应在文档中段之后，而不是顶部
  // 无头环境里 smooth 滚动动画不一定推进（实测同一个页面在独立脚本里滚到 2332px，
  // 在长流程 e2e 里始终停在 0）。所以不去断言动画结果，改为记录 scrollIntoView
  // 的调用参数——这才是产品代码该保证的东西：按钮点了确实去找 #sources。
  await evalJs(`(() => {
    window.__scrolled = null;
    const orig = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = function (opt) {
      window.__scrolled = { id: this.id || null, behavior: opt && opt.behavior };
      return orig.call(this, opt);
    };
    return true;
  })()`);
  await evalJs(`document.querySelector('.verdict__src').click()`);
  await sleep(600);
  const spy = JSON.parse(await evalJs(`JSON.stringify(window.__scrolled)`));
  ok('按钮对 #sources 调用 scrollIntoView', spy && spy.id === 'sources', JSON.stringify(spy));
  ok('使用平滑滚动', spy && spy.behavior === 'smooth', JSON.stringify(spy));

  // 来源区块确实在页面下方（否则这个按钮没有存在意义）
  const geo = JSON.parse(
    await evalJs(`(() => {
      const r = document.querySelector('#sources').getBoundingClientRect();
      return JSON.stringify({ top: Math.round(r.top), scrollable: document.documentElement.scrollHeight > innerHeight });
    })()`),
  );
  ok('来源区块位于首屏之下且页面可滚', geo.top > 400 && geo.scrollable, JSON.stringify(geo));
  // 不能断言「scrollY 没变」——这个按钮的全部目的就是滚动，滚动了才是对的。
  // 早前它在无头环境里恰好没推进才通过，属于把环境巧合当成产品契约。
  // 真正该守的是：滚动没有把详情页卸载掉（本站 hash 路由，改错锚点写法就会掉回列表）。
  ok(
    '滚动后仍停在详情页（路由未被破坏）',
    await evalJs(`location.hash.startsWith('#/p/ca-iec-working-holiday') && !!document.querySelector('.verdict')`),
  );
}


console.log('\\n[27] 长文页（public/guides，静态 HTML，不经 React）');
{
  // 长文是唯一能被搜索引擎单独收录的页面（详情页用 hash 路由，收录不了）。
  // 它们不进打包、不进 i18n，所以必须单独验：能打开、有 canonical、有 JSON-LD。
  const probe = await evalJs(`(async () => {
    const get = async (p) => {
      try {
        const r = await fetch(p, { cache: 'no-store' });
        return { ok: r.ok, status: r.status, text: r.ok ? await r.text() : '' };
      } catch (e) { return { ok: false, status: 0, text: '' }; }
    };
    const out = {};
    for (const g of ["age-wall.html", "misinformation.html"]) {
      const r = await get('./guides/' + g);
      out[g] = {
        ok: r.ok,
        status: r.status,
        bytes: r.text.length,
        hasCanonical: r.text.includes('rel="canonical"') && r.text.includes('https://eddieye1004.github.io'),
        hasLd: r.text.includes('application/ld+json'),
        hasCta: r.text.includes('class="cta"'),
        h1: (() => {
          const a = r.text.indexOf('<h1');
          if (a < 0) return 0;
          const b = r.text.indexOf('>', a);
          const c = r.text.indexOf('</h1>', b);
          return c > b ? r.text.slice(b + 1, c).replace(new RegExp('<[^>]+>', 'g'), '').trim().length : 0;
        })(),
      };
    }
    const css = await get('./guides/guide.css');
    return { guides: out, cssOk: css.ok, cssBytes: css.text.length };
  })()`);

  for (const g of ["age-wall.html", "misinformation.html"]) {
    const d = probe.guides[g];
    ok(`长文 ${g} 可访问`, d.ok === true, `status=${d.status}`);
    ok(`长文 ${g} 正文非空`, d.bytes > 4000, `bytes=${d.bytes}`);
    ok(`长文 ${g} 只有一个 h1 且有内容`, d.h1 > 4, `h1len=${d.h1}`);
    ok(`长文 ${g} canonical 指向线上地址`, d.hasCanonical === true);
    ok(`长文 ${g} 含 JSON-LD`, d.hasLd === true);
    ok(`长文 ${g} 含回流主站的 CTA`, d.hasCta === true);
  }
  ok('guide.css 可访问', probe.cssOk === true);
}

console.log('\n[28] 纠错入口：每个页面都要能说「这里错了」');
{
  // 页脚是全站唯一常驻的反馈入口。它有三件事必须同时成立：
  // 链接指向正确的 issue 表单（带 template 参数，否则会落到模板选择页 → 多一步错路）、
  // 新窗口打开时不泄露 window.opener、以及中英文各有自己的文案。
  const FOOTER_ISSUE_SEL = '.ftr a[href*="issues/new"]';
  const probeFooter = () =>
    evalJs(`(() => {
      const a = document.querySelector('${FOOTER_ISSUE_SEL}');
      if (!a) return JSON.stringify({ found: false });
      return JSON.stringify({
        found: true,
        href: a.getAttribute('href'),
        target: a.getAttribute('target'),
        rel: a.getAttribute('rel'),
        text: (a.textContent || '').trim(),
      });
    })()`);

  await goto('#/');
  await sleep(700);
  const zh = JSON.parse(await probeFooter());
  ok('列表页页脚有纠错链接', zh.found === true);
  ok(
    '纠错链接带 template 参数（否则落到模板选择页）',
    /issues\/new\?template=data-correction\.yml$/.test(zh.href || ''),
    zh.href,
  );
  ok('纠错链接指向本仓库', (zh.href || '').includes('eddieye1004/overseas-program-dataset'), zh.href);
  ok('纠错链接新窗口打开', zh.target === '_blank');
  ok('纠错链接带 rel=noopener', /noopener/.test(zh.rel || ''), zh.rel);
  ok('中文纠错文案非空且含「纠错」', zh.text.includes('纠错'), zh.text);

  // 详情页也要有：发现错误的那一页往往不是列表页
  await goto('#/p/nz-china-whv');
  await sleep(900);
  const onDetail = JSON.parse(await probeFooter());
  ok('详情页页脚也有纠错链接', onDetail.found === true);

  // 英文模式：文案必须换，链接不能跟着变成中文。
  // 语言开关是**一个**按钮（点一下切到另一种语言），不是两个按钮——
  // 按 /EN/ 找子按钮会落空，e2e 其余处也是直接点 .langswitch。
  await goto('#/');
  await sleep(500);
  const langNow = await evalJs(
    `document.querySelector('.langswitch').getAttribute('aria-label')`,
  );
  // aria-label 是「切换到另一种语言」的说法，用当前页面语言判断状态
  const isZhNow = langNow === 'Switch to English';
  if (isZhNow) {
    await evalJs(`document.querySelector('.langswitch').click()`);
    await sleep(700);
  }
  const en = JSON.parse(await probeFooter());
  ok('英文模式纠错链接仍在', en.found === true);
  ok('英文纠错文案已切换', en.text !== zh.text && /error|Report/i.test(en.text), en.text);
  ok('英文模式链接不变（不随语言走本地化路径）', en.href === zh.href, en.href);
  // 切回中文，避免影响后续断言
  if (isZhNow) {
    await evalJs(`document.querySelector('.langswitch').click()`);
    await sleep(500);
  }
}

console.log('\n[29] 窗口日历：三档确定性不许混排');
{
  await goto('#/calendar');
  await sleep(1200);

  ok('日历页标题存在', await evalJs(`!!document.querySelector('.page__title')`));

  const secs = JSON.parse(
    await evalJs(`JSON.stringify([...document.querySelectorAll('.cal__sec')].map(s => ({
      tone: s.className.match(/cal__sec--(\\w+)/)?.[1] || '',
      rows: s.querySelectorAll('.cal__row').length,
      hasDate: [...s.querySelectorAll('.cal__dates time')].length,
    })))`),
  );
  ok('日历分成三个区块', secs.length === 3, JSON.stringify(secs));
  ok(
    '三块分别是 已公布 / 推断 / 无从判断',
    secs.map((s) => s.tone).join(',') === 'ok,warn,mute',
    secs.map((s) => s.tone).join(','),
  );

  // 核心红线：推断与「无从判断」两块里不许出现任何具体日期。
  // 一旦出现，读者就会把它当官方日期——这正是这页要防的事。
  const inferred = secs[1];
  const unknown = secs[2];
  ok('推断区块不含任何具体日期', inferred.hasDate === 0, `found ${inferred.hasDate}`);
  ok('无从判断区块不含任何具体日期', unknown.hasDate === 0, `found ${unknown.hasDate}`);
  ok('已公布区块确实有日期（否则三档形同虚设）', secs[0].hasDate > 0, `found ${secs[0].hasDate}`);

  // 推断区块必须写明「只作参考」
  const inferredHint = await evalJs(
    `document.querySelectorAll('.cal__sec')[1]?.querySelector('.cal__secHint')?.textContent || ''`,
  );
  ok('推断区块明确标注了非官方', /参考|reference/i.test(inferredHint), inferredHint);

  // 提醒日的算法只有一处：页面不得自己另算。
  // 取一条有 open_date 的记录，核对「还剩天数」与日期差一致。
  const check = JSON.parse(
    await evalJs(`(() => {
      const s = document.querySelectorAll('.cal__sec')[0];
      const row = s && s.querySelector('.cal__row');
      if (!row) return JSON.stringify({ ok: false });
      const t = row.querySelector('.cal__dates time');
      if (!t) return JSON.stringify({ ok: false });
      const days = Math.round((Date.parse(t.getAttribute('datetime')) - Date.now()) / 86400000);
      return JSON.stringify({ ok: true, iso: t.getAttribute('datetime'), days });
    })()`),
  );
  ok('已公布区块首行带可解析的日期', check.ok === true, JSON.stringify(check));

  // 从侧栏点进日历也能到
  await goto('#/');
  await sleep(600);
  await evalJs(
    `[...document.querySelectorAll('.sidebar__item')].find(e => /日历|Calendar/.test(e.textContent))?.click()`,
  );
  await sleep(800);
  ok('侧栏导航可进入日历页', await evalJs(`location.hash.includes('calendar')`));
}

ws.close();
proc.kill();

console.log(`\n${'='.repeat(48)}`);
console.log(`PASS ${pass} / ${pass + fails.length}`);
if (fails.length) {
  console.log('\nFAILED:');
  for (const x of fails) console.log(`  - ${x}`);
  process.exit(1);
}
console.log('ALL GREEN');
process.exit(0);
