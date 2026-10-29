// src/lib/useTitle.ts
// 把当前页面标题写进 document.title。
//
// 为什么需要：这是纯前端 hash 路由，浏览器标签页标题永远停在 index.html 里的那一个，
// 用户开三个标签页就分不清哪个是哪个；截图分享时也看不出在哪个页面。
// 只在 title 真的变了时才赋值，避免每次渲染都碰 document.title。
import { useEffect } from 'react';

/**
 * @param parts 标题片段，从具体到笼统。空值会被跳过。
 *              例：['加拿大 · IEC 打工度假', '海外项目数据库']
 */
export function useDocumentTitle(parts: (string | null | undefined)[]) {
  const title = parts.filter(Boolean).join(' · ');
  useEffect(() => {
    if (title && document.title !== title) document.title = title;
  }, [title]);
}
