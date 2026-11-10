// src/lib/nextstep.ts
// 「下一步做什么」——由数据算，不靠人记。
//
// 为什么要有这个模块：
//   申请看板原本只记录「我现在到哪一步」（状态 + 备注），但申请这件事的
//   难点从来不是记状态，而是「什么时候该动手」。一个项目的窗口 6 月 4 日
//   开放、6 月 25 日关闭，材料要提前 20 天准备——这三件事数据里都有，
//   却要使用者自己记住。把这些数字算成一句「现在该干嘛」，看板才不只是
//   一个备忘录。
//
// 纯函数、不碰 DOM、不读 localStorage：smoke-test 用 esbuild 单独打包这个
// 文件来验证边界，所以这里不能 import React 或任何浏览器 API。

/** 一条跟进记录算出来的下一步。 */
export interface NextAction {
  /**
   * prep 材料准备期已压上来 / open 窗口未来开放 / close 窗口现在开着
   * / closed 上一轮已关、下一轮未公布 / idle 从来没有过日期
   */
  kind: 'prep' | 'open' | 'close' | 'closed' | 'idle';
  /** 距今多少天；closed / idle 时为 null */
  days: number | null;
  /** 对应的日期（YYYY-MM-DD），closed / idle 时为 null */
  date: string | null;
  /** 上一轮窗口的关闭日（仅 closed 时有值），用来告诉人错过的是哪一天 */
  lastClosed: string | null;
  /** 材料准备一共要几天（无数据时为 0） */
  prepDays: number;
}

interface WindowLike {
  year?: number;
  status?: string;
  note?: string;
  open_date?: string | null;
  close_date?: string | null;
  draw_period_end?: string | null;
}

interface ProgramLike {
  // prepare_days 在真实数据里可能是 null（schema 允许），这里一并接受，
  // 由准备的求和逻辑当作 0 —— 缺数字时不猜一个平均值。
  documents?: { prepare_days?: number | null }[];
  timeline?: { windows?: WindowLike[] };
}

const DAY_MS = 86400000;

function toDay(s: string | undefined | null): number | null {
  if (!s) return null;
  const t = Date.parse(s);
  if (Number.isNaN(t)) return null;
  return Math.floor(t / DAY_MS);
}

function todayDay(): number {
  return Math.floor(Date.now() / DAY_MS);
}

/** 材料准备一共要几天。缺 prepare_days 的按 0 算，不猜一个平均值。 */
export function prepDaysOf(p: ProgramLike): number {
  return (p.documents ?? []).reduce((n, d) => n + (d.prepare_days ?? 0), 0);
}

/**
 * 算出「下一步」。
 *
 * 判定顺序（先做能做的、再做要等的）：
 *   1. 今天是窗口内的某一天 → 说还剩几天截止（最紧急）
 *   2. 窗口在未来 → 说还有几天开放；材料准备期已压上来时改口说「现在动手」
 *   3. 上一轮已经关了、下一轮没公布 → 说清错过的是哪一天，别假装无事
 *   4. 从来没有过日期 → idle，不硬编一句话
 *
 * 第 3 条是踩过的坑：au-462 的 2026 窗口 6 月 25 日就关了，2027 窗口
 * 只写了「日期尚未公布」。若只认未来窗口，它会落到 idle，界面上和
 * 「官方从不公布日期」的项目长得一样——但这两件事对使用者完全不同：
 * 前者是「你已错过，等明年 5 月前备好」，后者是「只能一直盯官网」。
 */
export function nextAction(p: ProgramLike, now: number = todayDay()): NextAction {
  const prep = prepDaysOf(p);
  const windows = (p.timeline?.windows ?? []) as WindowLike[];

  let openNow: { close: number | null } | null = null;
  let nextOpen: number | null = null;
  let lastClosed: number | null = null;

  for (const w of windows) {
    const open = toDay(w.open_date);
    const close = toDay(w.close_date);
    if (open != null && close != null && open <= now && now <= close) {
      // 同时开了多个窗口时取最早关闭的那个——那是最紧的
      if (!openNow || (close < (openNow.close ?? Infinity))) openNow = { close };
    } else if (open != null && open > now) {
      if (nextOpen == null || open < nextOpen) nextOpen = open;
    } else if (close != null && close < now) {
      if (lastClosed == null || close > lastClosed) lastClosed = close;
    } else if (open != null && open < now) {
      // 只有开放日、没有关闭日的（先到先得那类，如新西兰 WHV）：
      // 开放日一过名额就没了，所以用开放日当「上次的窗口」。
      if (lastClosed == null || open > lastClosed) lastClosed = open;
    }
  }

  if (openNow) {
    return {
      kind: 'close',
      days: openNow.close != null ? openNow.close - now : null,
      date: openNow.close != null ? isoOf(openNow.close) : null,
      lastClosed: null,
      prepDays: prep,
    };
  }

  if (nextOpen != null) {
    const startPrepare = nextOpen - prep;
    const base = {
      days: nextOpen - now,
      date: isoOf(nextOpen),
      lastClosed: null,
      prepDays: prep,
    };
    // 材料准备期已经压到窗口开放上：现在就该动手
    return startPrepare <= now ? { kind: 'prep', ...base } : { kind: 'open', ...base };
  }

  if (lastClosed != null) {
    return {
      kind: 'closed',
      days: null,
      date: null,
      lastClosed: isoOf(lastClosed),
      prepDays: prep,
    };
  }

  return { kind: 'idle', days: null, date: null, lastClosed: null, prepDays: prep };
}

function isoOf(day: number): string {
  return new Date(day * DAY_MS).toISOString().slice(0, 10);
}

export interface RankedRow {
  id: string;
  action: NextAction;
}

/**
 * 把跟进中的项目按紧急程度排好，供「今天先做这几件」用。
 *
 * 排序：窗口现在开着 < 材料现在就该动手 < 窗口未来开放
 *       < 上一轮已关、下一轮未公布 < 从来没有日期。
 * 同一档内按剩余天数升序 —— 剩 3 天的排在剩 30 天的前面。
 *
 * 「上一轮已关」排在「从来没有日期」之前，是因为前者还有确定的
 * 下一步（备好材料等明年），后者连什么时候该准备都不知道。
 */
export function rankByUrgency(
  rows: { id: string; program: ProgramLike }[],
  now: number = todayDay(),
): RankedRow[] {
  const kindRank: Record<NextAction['kind'], number> = {
    close: 0,
    prep: 1,
    open: 2,
    closed: 3,
    idle: 4,
  };
  return rows
    .map((r) => ({ id: r.id, action: nextAction(r.program, now) }))
    .sort((a, b) => {
      const k = kindRank[a.action.kind] - kindRank[b.action.kind];
      if (k !== 0) return k;
      return (a.action.days ?? 1e9) - (b.action.days ?? 1e9);
    });
}
