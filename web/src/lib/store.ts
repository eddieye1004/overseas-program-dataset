// src/lib/store.ts
// 本地用户状态：收藏、对比清单、最近浏览。
// 全部存 localStorage，没有账号、没有后端、零成本，换设备不同步（这是刻意的取舍）。
import { useCallback, useEffect, useState } from 'react';

const KEY_SAVED = 'opd.saved';
const KEY_COMPARE = 'opd.compare';
const KEY_RECENT = 'opd.recent';

/** 对比清单最多放几个：手机屏幕上 4 个已经挤满，超过就没意义 */
export const COMPARE_MAX = 4;

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    const v = JSON.parse(raw);
    return v ?? fallback;
  } catch {
    // 存储被禁用或内容损坏时静默回落，不能因为读不到偏好就白屏
    return fallback;
  }
}

function write(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* 隐私模式下不可写，忽略 */
  }
}

/** 暴露给需要自己管状态的地方（比如匹配画像），语义与内部 read/write 一致 */
export function loadJson<T>(key: string, fallback: T): T {
  return read<T>(key, fallback);
}
export function saveJson(key: string, value: unknown): void {
  write(key, value);
}

/**
 * 通用受控列表状态：读初始值 → 变更时落盘 → 跨标签页同步。
 * 用一个 hook 覆盖收藏与对比两种场景，避免两份几乎一样的代码。
 */
function useStoredList(key: string, max?: number) {
  const [list, setList] = useState<string[]>(() => read<string[]>(key, []));

  useEffect(() => {
    write(key, list);
  }, [key, list]);

  // 另一个标签页改了收藏，这边跟着更新，避免两个页面状态打架
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === key) setList(read<string[]>(key, []));
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, [key]);

  const toggle = useCallback(
    (id: string) => {
      setList((prev) => {
        if (prev.includes(id)) return prev.filter((x) => x !== id);
        if (max != null && prev.length >= max) return prev; // 满了就不加，不改动已有选择
        return [...prev, id];
      });
    },
    [max],
  );

  const remove = useCallback((id: string) => {
    setList((prev) => prev.filter((x) => x !== id));
  }, []);

  const clear = useCallback(() => setList([]), []);

  return { list, toggle, remove, clear, set: setList };
}

/** 收藏的项目 id 列表 */
export function useSaved() {
  return useStoredList(KEY_SAVED);
}

/** 对比清单（有上限） */
export function useCompare() {
  return useStoredList(KEY_COMPARE, COMPARE_MAX);
}

/** 最近浏览：详情页挂载时把 id 推到队首，最多留 6 条 */
export function useRecent() {
  const { list, set } = useStoredList(KEY_RECENT);
  const push = useCallback(
    (id: string) => {
      set((prev) => [id, ...prev.filter((x) => x !== id)].slice(0, 6));
    },
    [set],
  );
  return { list, push };
}

/** 申请进度：id → { status, note, updated } */
export interface TrackEntry {
  status: string;
  note: string;
  updated: string;
}
export type TrackMap = Record<string, TrackEntry>;

const KEY_TRACK = 'opd.track';

/**
 * 追踪清单（M3）。与「我的申请」（KEY_TRACK）刻意分成两份：
 *   追踪清单回答「我在关注哪些项目、它们的窗口什么时候开」——只存 id，不存状态；
 *   我的申请回答「我交到哪一步了」——有状态、备注、更新时间。
 * 合成一份会逼着人「先关注才能看进度」，而看窗口根本不需要先做决定。
 */
const KEY_WATCH = 'opd.watch';

/** 只存 id 列表：窗口信息在 index.json 里，随数据更新自动跟着变，不存快照 */
export function useWatch() {
  const { list, toggle, remove, clear } = useStoredList(KEY_WATCH);
  return { list, toggle, remove, clear };
}
/** 申请进度看板。状态值域由 ui.ts 的 TRACK_STATUS 约束，这里只管存。 */
export function useTrack() {
  const [map, setMap] = useState<TrackMap>(() => read<TrackMap>(KEY_TRACK, {}));

  useEffect(() => {
    write(KEY_TRACK, map);
  }, [map]);

  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === KEY_TRACK) setMap(read<TrackMap>(KEY_TRACK, {}));
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const setStatus = useCallback((id: string, status: string) => {
    setMap((prev) => ({
      ...prev,
      [id]: { status, note: prev[id]?.note ?? '', updated: new Date().toISOString().slice(0, 10) },
    }));
  }, []);

  const setNote = useCallback((id: string, note: string) => {
    setMap((prev) => {
      if (!prev[id]) return prev; // 没在跟进的项目不加备注，避免凭空建条目
      return { ...prev, [id]: { ...prev[id], note } };
    });
  }, []);

  const remove = useCallback((id: string) => {
    setMap((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }, []);

  const clear = useCallback(() => setMap({}), []);

  return { map, setStatus, setNote, remove, clear };
}
