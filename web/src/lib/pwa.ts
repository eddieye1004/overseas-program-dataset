// src/lib/pwa.ts
// 注册 service worker（M4）。
//
// 只在生产构建里注册：dev server 下 vite 的模块 URL 带查询串、热更新频繁，
// SW 的缓存优先策略会把旧模块留在缓存里，改代码不生效——那是最难查的一类
// 「我明明改了」。dev 下直接返回，什么都不做。
//
// 注册失败不能影响页面：这个站的主体是数据与判定，装不上桌面只是少一个入口。
export function registerServiceWorker(): void {
  if (typeof window === 'undefined') return;
  if (!('serviceWorker' in navigator)) return;
  // import.meta.env.PROD 在 vite build 产物里是 true，dev 里是 false
  if (!import.meta.env.PROD) return;

  window.addEventListener('load', () => {
    // 相对路径 + BASE_URL：站点跑在 /overseas-program-dataset/ 子路径下，
    // 写死 '/sw.js' 会 404 到域名根，而 404 的 SW 注册会静默失败。
    const url = `${import.meta.env.BASE_URL}sw.js`;
    navigator.serviceWorker.register(url).catch((err) => {
      console.warn('[pwa] service worker registration failed:', err);
    });
  });
}
