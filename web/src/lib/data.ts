// src/lib/data.ts
// 数据加载与缓存。
// 列表页只需要 index.json（8.7KB），点进详情才拉 programs.json（62.5KB）。
// 两个请求都用模块级 Promise 缓存，来回切换路由不会重复下载。
import type { ProgramIndexEntry, ProgramRecord } from '../types';

const BASE = import.meta.env.BASE_URL;

let indexPromise: Promise<ProgramIndexEntry[]> | null = null;
let fullPromise: Promise<ProgramRecord[]> | null = null;

/** 轻量索引：卡片列表与全部筛选都基于它 */
export function loadIndex(): Promise<ProgramIndexEntry[]> {
  if (!indexPromise) {
    indexPromise = fetch(`${BASE}data/index.json`).then((r) => {
      if (!r.ok) throw new Error(`index.json ${r.status}`);
      return r.json() as Promise<ProgramIndexEntry[]>;
    });
    // 失败时清掉缓存，下次进入页面可以重试
    indexPromise.catch(() => {
      indexPromise = null;
    });
  }
  return indexPromise;
}

/** 完整档案：详情页用 */
export function loadPrograms(): Promise<ProgramRecord[]> {
  if (!fullPromise) {
    fullPromise = fetch(`${BASE}data/programs.json`).then((r) => {
      if (!r.ok) throw new Error(`programs.json ${r.status}`);
      return r.json() as Promise<ProgramRecord[]>;
    });
    fullPromise.catch(() => {
      fullPromise = null;
    });
  }
  return fullPromise;
}

/** 按 id 取单条完整档案，供详情页使用 */
export async function loadProgram(id: string): Promise<ProgramRecord | undefined> {
  const all = await loadPrograms();
  return all.find((p) => p.program.id === id);
}
