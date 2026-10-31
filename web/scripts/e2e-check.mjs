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

console.log('\n[1] 首屏渲染（工作台外壳）');
await goto('#/');
await evalJs(`localStorage.clear()`);
await goto('#/');
ok('侧边栏存在', await evalJs(`!!document.querySelector('.sidebar')`));
const navCount = await evalJs(`document.querySelectorAll('.sidebar__item').length`);
ok('侧边栏 6 个导航入口', navCount === 6, `got ${navCount}`);
const brandText = await evalJs(`document.querySelector('.sidebar__name strong')?.textContent ?? ''`);
ok('站点标题非空', brandText.length > 0, brandText);
ok('11 张卡片渲染', (await evalJs(`document.querySelectorAll('.card').length`)) === 11);
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

console.log('\n[2] 搜索交互（真实输入事件）');
await evalJs(`(() => {
  const input = document.querySelector('input[type=search]');
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  setter.call(input, 'canada');
  input.dispatchEvent(new Event('input', { bubbles: true }));
  return true;
})()`);
await sleep(400);
ok('搜索 canada 后只剩 1 张', (await evalJs(`document.querySelectorAll('.card').length`)) === 1);
ok(
  '剩余卡片是 ca-iec',
  await evalJs(`document.querySelector('.card__link')?.getAttribute('href') === '#/p/ca-iec-working-holiday'`),
);
ok('筛选条件写入 URL', await evalJs(`location.hash.includes('q=canada')`));

console.log('\n[3] 清空筛选');
await clickByText('清空筛选');
await sleep(400);
ok('清空后恢复 11 张', (await evalJs(`document.querySelectorAll('.card').length`)) === 11);

console.log('\n[4] 资格筛选按钮');
await evalJs(`[...document.querySelectorAll('.chip')].find(c => /大陆护照不可申/.test(c.textContent)).click()`);
await sleep(400);
ok('筛「不可申」= 5 张', (await evalJs(`document.querySelectorAll('.card').length`)) === 5);
ok(
  '所有结果都是 not_eligible',
  await evalJs(`[...document.querySelectorAll('.card')].every(c => c.dataset.status === 'not_eligible')`),
);

console.log('\n[5] 再次点击取消筛选（toggle）');
await evalJs(`[...document.querySelectorAll('.chip')].find(c => /大陆护照不可申/.test(c.textContent)).click()`);
await sleep(400);
ok('取消后回到 11 张', (await evalJs(`document.querySelectorAll('.card').length`)) === 11);

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
ok('关掉后回到 11 张', (await evalJs(`document.querySelectorAll('.card').length`)) === 11);
await toggleSwitch('只看有致命风险');
await sleep(400);
const criticalCount = await evalJs(`document.querySelectorAll('.card').length`);
// 11 条数据里 10 条至少含一个 critical 级风险，写死数字但由数据实测得来
ok('只看致命风险后只剩 10 张', criticalCount === 10, `got ${criticalCount}`);
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
ok('停留期排序后仍渲染 11 张', (await evalJs(`document.querySelectorAll('.card').length`)) === 11);
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

console.log('\n[12] 智能匹配');
await goto('#/match');
ok('匹配页有条件表单', await evalJs(`!!document.querySelector('.profile')`));
ok('未填条件时显示提示', await evalJs(`!!document.querySelector('.state')`));
await setValue('.profile input[type=number]', '20');
await sleep(500);
const matchCards = await evalJs(`document.querySelectorAll('.card').length`);
ok('填条件后出现全部结果', matchCards === 11, `got ${matchCards}`);
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

console.log('\n[13] 数据说明页');
await goto('#/about');
ok('四个统计数字', (await evalJs(`document.querySelectorAll('.stat').length`)) === 4);
ok('数据表 11 行', (await evalJs(`document.querySelectorAll('.dtable tbody tr').length`)) === 11);
ok('收录数 = 11', (await evalJs(`document.querySelector('.stat__num')?.textContent.trim()`)) === '11');

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
ok('未知 hash 回落到项目库', (await evalJs(`document.querySelectorAll('.card').length`)) === 11);

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
  ok('点掉条件后恢复结果', back === 11, `got ${back}`);
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
    const [robots, sitemap, icon, ogimg] = await Promise.all([
      get('./robots.txt'),
      get('./sitemap.xml'),
      get('./favicon.svg'),
      get('./og.png'),
    ]);
    return {
      robotsOk: robots.ok,
      robotsSitemap: /Sitemap:\\s*https:\\/\\//i.test(robots.text),
      sitemapOk: sitemap.ok,
      sitemapUrls: (sitemap.text.match(/<loc>/g) || []).length,
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
  // 首页 + 11 个项目详情页
  ok('sitemap 含 12 条 URL', probe.sitemapUrls === 12, `got ${probe.sitemapUrls}`);
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
  // 改用前缀数字区分：6 那条是可申，5 那条是不可申。
  ok(
    '结论条含不可申计数',
    S.some((s) => /^5\s/.test(s) && s.includes('不可申')),
    stats,
  );
  ok(
    '结论条含可申计数',
    S.some((s) => /^6\s/.test(s) && s.includes('可申') && !s.includes('不可申')),
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
