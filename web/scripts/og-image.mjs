// web/scripts/og-image.mjs
// 生成 1200×630 的社交分享图（OG image）。
// 做法：用无头 Edge 打开一段内联 HTML，再 Page.captureScreenshot 截图。
// 不用 canvas / sharp / 任何原生依赖，避免多装一个包。
// 用法：node scripts/og-image.mjs
import { spawn } from 'node:child_process';
import { mkdtemp, writeFile, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(__dirname, '..', 'public', 'og.png');

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const port = 9700 + Math.floor(Math.random() * 200);
const profile = await mkdtemp(join(tmpdir(), 'cdp-og-'));

// 与 src/tokens.css 保持同一套值；改配色时两处一起改
const HTML = `<!doctype html><html><head><meta charset="utf-8"><style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{width:1200px;height:630px;background:#faf9f5;color:#141413;
       font-family:"Segoe UI","Microsoft YaHei",system-ui,sans-serif;
       display:flex;flex-direction:column;justify-content:space-between;
       padding:72px 80px;position:relative;overflow:hidden}
  .edge{position:absolute;inset:0;border:14px solid #8f4630;pointer-events:none}
  .kicker{font-size:23px;letter-spacing:.18em;color:#8f4630;font-weight:700}
  h1{font-size:82px;line-height:1.08;letter-spacing:-.02em;font-weight:800;margin-top:26px;
     font-family:Georgia,"Songti SC",serif}
  h1 em{font-style:normal;color:#8f4630}
  .sub{margin-top:30px;font-size:30px;line-height:1.5;color:#3d3d3a;max-width:900px}
  .foot{display:flex;align-items:flex-end;justify-content:space-between;margin-top:44px}
  .stats{display:flex;gap:56px}
  .n{font-size:52px;font-weight:800;line-height:1;font-variant-numeric:tabular-nums}
  .l{font-size:20px;color:#5c5a54;margin-top:9px;letter-spacing:.04em}
  .url{font-size:22px;color:#5c5a54;font-family:ui-monospace,Consolas,monospace}
  .dot{color:#8f4630}
</style></head><body>
  <div class="edge"></div>
  <div>
    <div class="kicker">OVERSEAS PROGRAM DATASET</div>
    <h1>先告诉你<em>哪些不能申</em></h1>
    <div class="sub">面向中国大陆申请人的打工度假 / 海外实习数据库，每条结论都挂着官方来源与核实日期。</div>
  </div>
  <div class="foot">
    <div class="stats">
      <div><div class="n">11</div><div class="l">收录项目</div></div>
      <div><div class="n">2</div><div class="l">语言</div></div>
      <div><div class="n">100<span style="font-size:32px">%</span></div><div class="l">标注官方来源</div></div>
    </div>
    <div class="url">eddieye1004.github.io<span class="dot">/</span>overseas-program-dataset</div>
  </div>
</body></html>`;

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
await send('Emulation.setDeviceMetricsOverride', {
  width: 1200,
  height: 630,
  deviceScaleFactor: 1,
  mobile: false,
});

// 用 data: URL 打开内联 HTML 会踩到长度与转义问题，写临时文件再 file:// 打开更稳
const tmpHtml = join(profile, 'og.html');
await writeFile(tmpHtml, HTML, 'utf8');
await send('Page.navigate', { url: `file:///${tmpHtml.replace(/\\/g, '/')}` });
await sleep(900);

const shot = await send('Page.captureScreenshot', {
  format: 'png',
  captureBeyondViewport: false,
});
await mkdir(dirname(OUT), { recursive: true });
await writeFile(OUT, Buffer.from(shot.data, 'base64'));

ws.close();
proc.kill();

console.log(`wrote ${OUT}`);
