// web/scripts/screenshot.mjs
// 用 Edge/Chrome 的 CDP 接口按真实设备尺寸截图，并顺带检测横向溢出。
// 无头浏览器的 --window-size 有最小宽度（约 481px），直接传 390 会得到被裁切的图，
// 所以这里用 Emulation.setDeviceMetricsOverride 才是真实手机视口。
//
// 用法：node scripts/screenshot.mjs <url> <out.png> <width> <height> [mobile]
import { spawn } from 'node:child_process';
import { writeFile, mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const [, , url, out, w = '390', h = '1400', mobile = '1'] = process.argv;
const width = Number(w);
const height = Number(h);
const isMobile = mobile === '1';

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const port = 9200 + Math.floor(Math.random() * 400);
const profile = await mkdtemp(join(tmpdir(), 'cdp-'));

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

// 等 CDP 端口就绪
let target = null;
for (let i = 0; i < 60; i++) {
  try {
    const r = await fetch(`http://127.0.0.1:${port}/json/list`);
    const list = await r.json();
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
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg.result ?? {});
    pending.delete(msg.id);
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
await send('Emulation.setDeviceMetricsOverride', {
  width,
  height,
  deviceScaleFactor: 1,
  mobile: isMobile,
});
// 手机 UA，让浏览器按移动端排版（不影响我们的 CSS 断点，但更接近真机）
await send('Emulation.setUserAgentOverride', {
  userAgent: isMobile
    ? 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
    : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
});

await send('Page.navigate', { url });
await sleep(2500);

// 溢出检测：scrollWidth 大于 clientWidth 就说明有元素把页面撑宽了
const probe = await send('Runtime.evaluate', {
  expression: `(() => {
    const de = document.documentElement;
    const W = de.clientWidth;
    const bad = [];
    document.querySelectorAll('body *').forEach((el) => {
      const r = el.getBoundingClientRect();
      if (r.width > W + 1 || r.right > W + 1) {
        bad.push(el.tagName.toLowerCase() + '.' + String(el.className).slice(0, 30) + ' w=' + Math.round(r.width));
      }
    });
    return JSON.stringify({ scrollWidth: de.scrollWidth, clientWidth: W, cards: document.querySelectorAll('.card').length, overflow: bad.slice(0, 6) });
  })()`,
  returnByValue: true,
});
const info = JSON.parse(probe.result.value);

const shot = await send('Page.captureScreenshot', {
  format: 'png',
  captureBeyondViewport: true,
});
await writeFile(out, Buffer.from(shot.data, 'base64'));

console.log(`${out}  ${width}x${height} dpr2 mobile=${isMobile}`);
console.log(
  `scrollWidth=${info.scrollWidth} clientWidth=${info.clientWidth} horizontalOverflow=${info.scrollWidth > info.clientWidth ? 'YES' : 'no'} cards=${info.cards}`,
);
if (info.overflow.length) console.log('wide elements:', info.overflow.join(' | '));

ws.close();
proc.kill();
process.exit(0);
