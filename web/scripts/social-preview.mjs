// web/scripts/social-preview.mjs
// 生成仓库门面用的社交预览图（GitHub Settings → Social preview，1200×630）。
//
// 和 og-image.mjs 的区别（两者别混）：
//   og-image.mjs       → web/public/og.png   站点分享卡片，跟着站点一起发布
//   social-preview.mjs → docs/social-preview.png  仓库门面，人工上传到 GitHub 设置
// 手法相同：无头 Edge 打开内联 HTML 再截图，不引入 canvas / sharp 等原生依赖。
//
// 图上每个数字都从仓库数据派生，不写死。理由见 og-image.mjs 里那次事故：
// 硬编码的「11」在项目加到 26 个后还在图上，而图是二进制、grep 不到的，
// 属于最难发现的一类过期内容。
//
// 用法：node scripts/social-preview.mjs   （在 web/ 下跑，与其余脚本一致）
import { spawn } from 'node:child_process';
import { mkdtemp, writeFile, mkdir, readFile, readdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(__dirname, '..', '..');
const OUT = resolve(REPO, 'docs', 'social-preview.png');

// ---- 数字全部从数据派生 ----
const PROGRAMS_DIR = join(REPO, 'data', 'programs');
const files = (await readdir(PROGRAMS_DIR)).filter((f) => f.endsWith('.json')).sort();
const docs = await Promise.all(
  files.map(async (f) => JSON.parse(await readFile(join(PROGRAMS_DIR, f), 'utf8'))),
);
const TOTAL = docs.length;
const ELIGIBLE = docs.filter(
  (d) => d.eligibility?.passport_types?.mainland_china === 'eligible',
).length;
const SOURCES = docs.reduce((n, d) => n + (d.sources?.length ?? 0), 0);
const POLICY = JSON.parse(await readFile(join(REPO, 'data', 'review-policy.json'), 'utf8'));
const IV_DATED = POLICY.interval_dated_window_days;
const IV_DEFAULT = POLICY.interval_default_days;

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const port = 9700 + Math.floor(Math.random() * 200);
const profile = await mkdtemp(join(tmpdir(), 'cdp-social-'));

// 与 src/tokens.css 同一套值；改配色时两处一起改
const HTML = `<!doctype html><html><head><meta charset="utf-8"><style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{width:1200px;height:630px;background:#faf9f5;color:#141413;
       font-family:"Segoe UI","Microsoft YaHei",system-ui,sans-serif;
       display:flex;flex-direction:column;justify-content:space-between;
       padding:64px 72px;position:relative;overflow:hidden}
  .edge{position:absolute;inset:0;border:12px solid #8f4630;pointer-events:none}
  .kicker{font-size:21px;letter-spacing:.2em;color:#8f4630;font-weight:700}
  h1{font-size:64px;line-height:1.16;letter-spacing:-.02em;font-weight:800;margin-top:22px;
     font-family:Georgia,"Songti SC",serif;max-width:1040px}
  h1 em{font-style:normal;color:#8f4630}
  .sub{margin-top:22px;font-size:26px;line-height:1.55;color:#3d3d3a;max-width:1000px}
  .foot{display:flex;align-items:flex-end;justify-content:space-between;margin-top:38px;
        border-top:1px solid #ddd9cf;padding-top:26px}
  .stats{display:flex;gap:52px}
  .n{font-size:44px;font-weight:800;line-height:1;font-variant-numeric:tabular-nums}
  .l{font-size:18px;color:#5c5a54;margin-top:8px;letter-spacing:.03em}
  .url{font-size:20px;color:#5c5a54;font-family:ui-monospace,Consolas,monospace;
       text-align:right;line-height:1.5}
  .dot{color:#8f4630}
</style></head><body>
  <div class="edge"></div>
  <div>
    <div class="kicker">OVERSEAS YOUTH MOBILITY PROGRAM DATASET</div>
    <h1>每条资格都挂<em>官方来源</em>，<br>并标注核实日期</h1>
    <div class="sub">面向中国大陆申请人的打工度假 / 海外实习 / 毕业后工签开放数据集：每条结论可追溯到政府官方页面，CI 校验来源等级与链接存活。</div>
  </div>
  <div class="foot">
    <div class="stats">
      <div><div class="n">${TOTAL}</div><div class="l">收录项目</div></div>
      <div><div class="n">${ELIGIBLE}</div><div class="l">护照可申</div></div>
      <div><div class="n">${SOURCES}</div><div class="l">条官方来源</div></div>
      <div><div class="n">${IV_DATED}<span style="font-size:26px">/${IV_DEFAULT}</span></div><div class="l">天复核周期</div></div>
    </div>
    <div class="url">eddieye1004.github.io<span class="dot">/</span><br>overseas-program-dataset</div>
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

const tmpHtml = join(profile, 'social.html');
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

console.log(`wrote ${OUT}  (${TOTAL} programs / ${ELIGIBLE} eligible / ${SOURCES} sources)`);
