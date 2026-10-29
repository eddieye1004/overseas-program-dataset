// src/lib/router.ts
// 极简 hash 路由：不用 react-router，省掉一个依赖和一层嵌套。
// 站点托管在 GitHub Pages 上不能配置服务端 rewrite，hash 路由天然不需要。
import { useEffect, useState } from 'react';

export type Route =
  | { name: 'list' }
  | { name: 'detail'; id: string }
  | { name: 'match' }
  | { name: 'track' }
  | { name: 'saved' }
  | { name: 'compare' }
  | { name: 'about' };

function parse(hash: string): Route {
  // 形如 #/p/ca-iec-working-holiday、#/match、#/about
  // 先砍掉 query 段（列表页把筛选条件塞在 ? 之后），否则 #/match?x=1 会匹配不上
  const clean = hash.replace(/^#\/?/, '').split('?')[0];
  if (clean.startsWith('p/')) {
    const id = decodeURIComponent(clean.slice(2));
    if (id) return { name: 'detail', id };
  }
  if (clean === 'match') return { name: 'match' };
  if (clean === 'track') return { name: 'track' };
  if (clean === 'saved') return { name: 'saved' };
  if (clean === 'compare') return { name: 'compare' };
  if (clean === 'about') return { name: 'about' };
  return { name: 'list' };
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parse(window.location.hash));

  useEffect(() => {
    const onChange = () => {
      setRoute(parse(window.location.hash));
      // 切到详情页时回到顶部，否则会停在上一页的滚动位置
      window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior });
    };
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);

  return route;
}

export function navigate(path: string): void {
  window.location.hash = path;
}

/** 生成详情页链接；id 里可能有特殊字符，统一编码 */
export function detailHref(id: string): string {
  return `#/p/${encodeURIComponent(id)}`;
}
