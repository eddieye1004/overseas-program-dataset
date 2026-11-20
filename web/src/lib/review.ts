// src/lib/review.ts
// 复核状态的**渲染时**计算。
//
// 为什么不在构建时算好写进 index.json：
//   index.json 是入库产物，必须有「同数据 → 同字节」的性质，否则改完数据跑一次
//   sync-data 就产生 41 条纯日期漂移（实测 2026-11-20，HEAD 48fb859）。
//   但「还剩几天」本质上是「相对今天」的量——把它冻进产物，站点就会永远显示
//   构建那天算出的天数，越用越错，等于把新鲜度语义冻死。
//
// 所以切分：
//   · 构建时只落**与日期无关**的三件事：周期、下次复核日、提前预警阈值。
//     三者都只由 data/programs/*.json + data/review-policy.json 决定。
//   · 相对今天的那两个量（剩余天数、状态）在渲染时算。
//
// 判据与 scripts/track.py 的 classify() 逐字对应，改一处必须改另一处：
//   overdue   days_left < 0
//   due_soon  days_left <= soon_at（soon_at = max(1, floor(interval * ratio))）
//   fresh     其余
//   unknown   缺 last_verified / review_due
// tests/test_track.py 钉住了 Python 侧的边界，smoke-test 钉住了这一侧不漂。
import type { ProgramIndexEntry, ReviewState } from '../types';

export interface ReviewView {
  state: ReviewState;
  /** 距下次复核还有几天；已过期为负；缺日期为 null */
  daysLeft: number | null;
  due: string | null;
  interval: number;
}

/** 今天零点（本地）。取零点是为了让「差一天」永远是差一天，不受当天时刻影响。 */
function todayStart(): number {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

/**
 * 一条索引记录的复核视图。
 *
 * today 可注入，只为测试与快照复现；生产调用不传，走真实当天。
 */
export function reviewOf(e: ProgramIndexEntry, today: number = todayStart()): ReviewView {
  const interval = e.review_interval ?? 180;
  const due = e.review_due ?? null;
  if (!due) {
    return { state: 'unknown', daysLeft: null, due: null, interval };
  }
  const dueMs = Date.parse(`${due}T00:00:00`);
  if (Number.isNaN(dueMs)) {
    return { state: 'unknown', daysLeft: null, due: null, interval };
  }
  // 用本地零点的日差，不用毫秒直除：夏令时切的那一天会差出一小时，
  // 毫秒直除会得到 172 而不是 173。
  const daysLeft = Math.round((dueMs - today) / 86400000);
  const soonAt = e.review_soon_at ?? Math.max(1, Math.floor(interval * 0.25));
  const state: ReviewState =
    daysLeft < 0 ? 'overdue' : daysLeft <= soonAt ? 'due_soon' : 'fresh';
  return { state, daysLeft, due, interval };
}

/** 批量：给一批索引条目算出复核视图，按「最该处理」排序。 */
export function reviewIndex(
  entries: ProgramIndexEntry[],
): Array<ProgramIndexEntry & ReviewView> {
  const today = todayStart();
  return entries
    .map((e) => {
      const r = reviewOf(e, today);
      return { ...e, ...r, review_state: r.state, review_days_left: r.daysLeft };
    })
    .sort((a, b) => (a.daysLeft ?? 1e9) - (b.daysLeft ?? 1e9));
}
