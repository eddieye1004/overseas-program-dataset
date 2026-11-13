// web/public/sw.js
// 最小可安装所需的 service worker（M4）。
//
// 为什么必须有它：Chrome 的安装条件里除了 manifest 与图标，还要求页面
// 注册一个带 fetch 处理器的 service worker。没有它，地址栏不会出现安装图标，
// beforeinstallprompt 也不触发——于是「添加到桌面」引导只能退化成一段文字说明。
//
// 缓存策略刻意分成三类，因为这三类内容的更新节奏完全不同：
//   data/*.json  网络优先。这些文件每次 sync:data 都会变（项目、复核状态），
//                用缓存优先会让用户看到几天前的数据，而这一站的价值就在「新」。
//                离线时才退回缓存。
//   页面导航       网络优先。**这一类必须是网络优先**：index.html 的文件名不带
//                构建哈希，URL 永远是同一个，用缓存优先就会把用户永久钉在
//                首次访问时的那个版本上——新版 JS 的哈希变了也拿不到，因为
//                入口 HTML 根本不刷新。离线时才退回缓存。
//   其余静态资源  缓存优先。文件名带构建哈希，内容变了 URL 就变了，不存在陈旧问题。
//
// 版本号一变，旧缓存在 activate 里全部清掉。不这么做的话，改了这个文件
// 用户也拿不到新版——浏览器只在字节变化时更新 SW，但缓存的旧资源会留着。

const VERSION = 'opd-v2';
const DATA_CACHE = `${VERSION}-data`;
const PAGE_CACHE = `${VERSION}-page`;
const STATIC_CACHE = `${VERSION}-static`;

// 安装时不预缓存任何东西：预缓存列表一旦写死就会漂移（每次加项目都要改），
// 而首屏真正需要的文件由第一次访问自然带进缓存。
self.addEventListener('install', (event) => {
  // 新 SW 立刻接管，不必等所有旧页面关闭
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k)),
      );
      await self.clients.claim();
    })(),
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  // 只处理同源 GET。POST 与跨域请求（GitHub issue 链接等）直接放行。
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  const isData = /\/data\/[^/]+\.json$/.test(url.pathname);
  // 页面导航由浏览器以 mode: 'navigate' 发起，destination 也是 document。
  // 判 mode 而不是「pathname 以 / 结尾」：GitHub Pages 子路径、带 hash 的路由
  // 都不能靠 pathname 形状区分。
  const isNavigation = req.mode === 'navigate';

  if (isData || isNavigation) {
    // 网络优先：数据新、页面新比离线快更重要；网络挂了才用缓存兜底
    event.respondWith(
      (async () => {
        try {
          const fresh = await fetch(req);
          // 只落缓存 200：把 404/500 的响应缓存起来，断网时就会稳定复现一个
          // 服务端错误，比「没有缓存」还糟。
          if (fresh.ok) {
            const cache = await caches.open(isData ? DATA_CACHE : PAGE_CACHE);
            cache.put(req, fresh.clone());
          }
          return fresh;
        } catch (err) {
          const hit = await caches.match(req);
          if (hit) return hit;
          throw err;
        }
      })(),
    );
    return;
  }

  // 静态资源：缓存优先，未命中再走网络并回填
  event.respondWith(
    (async () => {
      const hit = await caches.match(req);
      if (hit) return hit;
      const res = await fetch(req);
      // 只缓存成功的同源响应；opaque 响应（跨域 no-cors）缓存了也没法用
      if (res.ok && res.type === 'basic') {
        const cache = await caches.open(STATIC_CACHE);
        cache.put(req, res.clone());
      }
      return res;
    })(),
  );
});
