// web/scripts/pwa-icons.mjs
// 生成 PWA 图标：192 / 512 / maskable 512 / apple-touch 180，全部 PNG。
// 做法与 og-image.mjs 相同——无头 Edge 打开内联 HTML，Page.captureScreenshot 截图，
// 不引入 sharp / canvas 这类原生依赖。源图是 public/favicon.svg 那套色与几何，
// 改配色时两处一起改（颜色值在此文件内内联，因为 Edge 截 SVG 需要可独立渲染的文档）。
//
// 用法：node scripts/pwa-icons.mjs
import { spawn } from 'node:child_process';
import { mkdtemp, writeFile, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = resolve(__dirname, '..', 'public', 'icons');

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const port = 9900 + Math.floor(Math.random() * 90);
const profile = await mkdtemp(join(tmpdir(), 'cdp-icon-'));

// 与 tokens.css / favicon.svg 同一套值
const INK = '#8f4630';
const PAPER = '#faf9f5';
const GOLD = '#d9a066';

// bleed = 图形占画布的比例。maskable 图标会被系统裁成圆形/水滴，
// 安全区只有中间 80%，所以图形要缩到 0.56 才不会被切掉笔画。
const iconHtml = (size, bleed, bg) => `<!doctype html><html><head><meta charset="utf-8"><style>
  *{margin:0;padding:0;box-sizing:border-box}
  html,body{width:${size}px;height:${size}px;overflow:hidden}
  body{background:${bg};display:grid;place-items:center}
  svg{width:${Math.round(size * bleed)}px;height:${Math.round(size * bleed)}px;display:block}
</style></head><body>
  <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
    <path d="M20 44V20h9.5a8.5 8.5 0 0 1 0 17H26" fill="none" stroke="${PAPER}"
          stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="44" cy="41" r="3.6" fill="${GOLD}"/>
  </svg>
</body></html>`;

const TARGETS = [
  // [文件名, 画布边长, 图形占比, 底色]
  ['icon-192.png', 192, 0.66, INK],
  ['icon-512.png', 512, 0.66, INK],
  // maskable：满底色 + 图形缩进安全区，Android 裁圆也不切字
  ['icon-maskable-512.png', 512, 0.52, INK],
  // iOS 自己加圆角，不能给透明边，必须满底色
  ['apple-touch-icon.png', 180, 0.66, INK],
];

const proc = spawn(
  EDGE,
  [
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    '--no-first-run',
    '--no-default-browser-check',
    '--force-device-scale-factor=1',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    'about:blank',
  ],
  { stdio: 'ignore' },
);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let target;
for (let i = 0; i < 60; i++) {
  try {
    const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    target = list.find((t) => t.type === 'page');
    if (target) break;
  } catch {
    /* 浏览器还没起来 */
  }
  await sleep(200);
}
if (!target) {
  proc.kill();
  throw new Error('could not attach to Edge');
}

const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((res, rej) => {
  ws.addEventListener('open', res, { once: true });
  ws.addEventListener('error', rej, { once: true });
});
let id = 0;
const pending = new Map();
ws.addEventListener('message', (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg.result);
    pending.delete(msg.id);
  }
});
const send = (method, params = {}) =>
  new Promise((res) => {
    const mid = ++id;
    pending.set(mid, res);
    ws.send(JSON.stringify({ id: mid, method, params }));
  });

await send('Page.enable');
await mkdir(OUT_DIR, { recursive: true });

for (const [name, size, bleed, bg] of TARGETS) {
  await send('Emulation.setDeviceMetricsOverride', {
    width: size,
    height: size,
    deviceScaleFactor: 1,
    mobile: false,
  });
  // data: URL 有长度与转义坑，落临时文件再 file:// 打开更稳
  const tmpHtml = join(profile, `${name}.html`);
  await writeFile(tmpHtml, iconHtml(size, bleed, bg), 'utf8');
  await send('Page.navigate', { url: `file:///${tmpHtml.replace(/\\/g, '/')}` });
  await sleep(420);
  const shot = await send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: false,
  });
  await writeFile(join(OUT_DIR, name), Buffer.from(shot.data, 'base64'));
  console.log(`${name}  ${size}×${size}`);
}

ws.close();
proc.kill();
console.log(`wrote icons to ${OUT_DIR}`);
