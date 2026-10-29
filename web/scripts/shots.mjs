// web/scripts/shots.mjs
// 一次跑完工作台各页截图：项目库、智能匹配、申请看板、对比、数据说明、详情、移动端。
// 收藏/对比/申请是需要状态的页面，这里用 CDP 先写 localStorage 再导航。
//
// 用法：node scripts/shots.mjs http://127.0.0.1:8099/ ../shots
import { spawn } from 'node:child_process';
import { writeFile, mkdtemp, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const base = process.argv[2] ?? 'http://127.0.0.1:8099/';
const outDir = resolve(process.argv[3] ?? '../shots');
await mkdir(outDir, { recursive: true });

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const port = 9250 + Math.floor(Math.random() * 400);
const profile = await mkdtemp(join(tmpdir(), 'cdp-shots-'));

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
    /* 还没起来 */
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
    pending.get(m.id)(m.result ?? {});
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

const evalJs = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  return r.result?.value;
};

/** 先落地一次拿到 origin，再写 localStorage（否则 about:blank 域写不进去） */
await send('Emulation.setDeviceMetricsOverride', {
  width: 1280,
  height: 900,
  deviceScaleFactor: 1,
  mobile: false,
});
await send('Page.navigate', { url: base + '#/' });
await sleep(2000);
await evalJs(`(() => {
  localStorage.setItem('opd.saved', JSON.stringify(['jp-working-holiday','nz-china-whv','au-462-work-holiday']));
  localStorage.setItem('opd.compare', JSON.stringify(['au-462-work-holiday','ca-iec-working-holiday','jp-working-holiday','nz-china-whv']));
  localStorage.setItem('opd.track', JSON.stringify({
    'jp-working-holiday': { status: 'interview', note: '已约 11 月 5 日面试', updated: '2026-10-29' },
    'au-462-work-holiday': { status: 'submitted', note: '等抽签结果', updated: '2026-10-28' },
    'nz-china-whv': { status: 'preparing', note: '准备雅思成绩单', updated: '2026-10-27' },
    'ca-iec-working-holiday': { status: 'rejected', note: '大陆护照不可申', updated: '2026-10-26' }
  }));
  localStorage.setItem('opd.profile', JSON.stringify({ status: 'eligible', age: 20, education: 'bachelor_in_progress', budgetCny: 30000, minStayMonths: 6, mustBePaid: true, preferNoAgency: false, regions: [] }));
  return true;
})()`);

// 关键：React 的 useState 初值在挂载时读取，之后写 localStorage 不会回灌。
// 所以种完数据必须整页重载一次，否则收藏/对比/看板截图全是空态。
await send('Page.reload', { ignoreCache: false });
await sleep(2200);
/** 截一张：可选择先把视口设成手机/桌面，再等渲染；clip 撑到整页高度 */
async function shot(name, hash, { width = 1280, height = 900, mobile = false, wait = 1800 } = {}) {
  await send('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    deviceScaleFactor: 1,
    mobile,
  });
  // 只改 hash 属于同文档导航，React 不会重新挂载；localStorage 里的新状态就进不来。
  // 所以每次截图前先导航再强制 reload，保证是全新挂载。
  await send('Page.navigate', { url: base + hash });
  await sleep(600);
  await send('Page.reload', { ignoreCache: false });
  await sleep(wait);
  const info = JSON.parse(
    await evalJs(`(() => {
      const de = document.documentElement;
      return JSON.stringify({
        sw: de.scrollWidth,
        cw: de.clientWidth,
        sh: de.scrollHeight,
        cards: document.querySelectorAll('.card').length,
      });
    })()`),
  );
  const shotData = await send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: true,
    clip: {
      x: 0,
      y: 0,
      width: Math.max(info.cw, width),
      height: Math.min(Math.max(info.sh, height), 6000),
      scale: 1,
    },
  });
  const file = join(outDir, name + '.png');
  await writeFile(file, Buffer.from(shotData.data, 'base64'));
  const flags = info.sw > info.cw ? 'OVERFLOW' : 'ok';
  console.log(
    `${name}.png  ${width}x${Math.min(Math.max(info.sh, height), 6000)} cards=${info.cards} hscroll=${flags}`,
  );
  return info;
}

await evalJs(`localStorage.setItem('opd.lang','zh')`);
await shot('01-list', '#/');
await shot('03-match', '#/match');
await shot('04-track', '#/track');
await shot('05-compare', '#/compare');
await shot('06-saved', '#/saved');
await shot('07-about', '#/about');
await shot('08-detail', '#/p/jp-working-holiday');
await shot('09-mobile-list', '#/', { width: 390, height: 844, mobile: true });
await shot('10-mobile-detail', '#/p/jp-working-holiday', { width: 390, height: 844, mobile: true });
// 平板档：三档视口验收里中间那档，最容易出现「两列挤成一团」的宽度
await shot('09b-tablet-list', '#/', { width: 768, height: 1024, mobile: true });

// 英文版：切语言后重截两张关键页
await evalJs(`localStorage.setItem('opd.lang','en')`);
await shot('11-list-en', '#/');
await shot('12-match-en', '#/match');
await shot('13-compare-en', '#/compare');
await evalJs(`localStorage.setItem('opd.lang','zh')`);

ws.close();
proc.kill();
process.exit(0);
