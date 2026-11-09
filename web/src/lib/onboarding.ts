// src/lib/onboarding.ts
// 首访引导的判定逻辑。刻意做成纯函数、不碰 React、不自己读 localStorage：
//   - smoke-test.mjs 能像 bundle filters.ts 那样直接 import 来断言（见 scripts/smoke-test.mjs）
//   - 组件只负责把它读到的快照传进来，规则改动集中在这一处
//
// 为什么需要它：站里 26 张卡 + 4 组筛选一屏铺开，新访客看得懂每张卡，却不知道
// 「可申」只代表护照资格、也不知道六个模块各自能干什么。引导条是第一层答案。
//
// 注意：刻意不 import store.ts。store.ts 会拉进 React，而 smoke-test 用 esbuild
// 以 platform:'neutral' 打包本文件来直接断言——一旦引入 React，打包就会失败。

/** 引导词条版本号。改文案就 +1，老用户会再看一次新版——而不是永远看不到。 */
export const ONBOARD_VERSION = 1;

// 与 store.ts 里的键名保持一致（那边只导出 hook，键名常量没对外暴露）
const KEY_ONBOARDED = 'opd.onboarded';
const KEY_REPLAY = 'opd.replay';
const KEY_SAVED = 'opd.saved';
const KEY_TRACK = 'opd.track';
const KEY_PROFILE = 'opd.profile';

/** 读 localStorage 里的 JSON。存储被禁用或内容损坏时回落到 fallback，不白屏。 */
function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (raw == null || raw === '') return fallback;
    const v = JSON.parse(raw);
    return (v ?? fallback) as T;
  } catch {
    return fallback;
  }
}

/** 写 localStorage。隐私模式下不可写时静默失败——引导条不挡内容，写不进去也能用。 */
function writeJson(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* ignore */
  }
}

/** 判定所需的全部输入，全部来自 localStorage 快照 */
export interface OnboardSnapshot {
  /** 已看过的版本号；null 表示从没看过 */
  onboarded: number | null;
  /** 1 表示用户刚点了「重看引导」，读完即清 */
  replay: number | null;
  saved: unknown[];
  track: Record<string, unknown>;
  profile: unknown;
}

/**
 * 是否显示引导条。
 * 顺序不能换：replay（手动触发）→ 版本号（已看过）→ 有历史（老用户）。
 * 把「有历史」放最后，是为了让清过数据但留下收藏的人也被判定成老用户——
 * 他们显然已经会用这个站了，再教一遍是打扰。
 */
export function shouldShowOnboarding(s: OnboardSnapshot): boolean {
  if (s.replay === 1) return true;
  if (s.onboarded != null && s.onboarded >= ONBOARD_VERSION) return false;
  // 空数组 / 空对象不算「有历史」：store 初始化时就会写入空值
  if (s.saved.length > 0) return false;
  if (Object.keys(s.track).length > 0) return false;
  if (s.profile != null && hasAnyField(s.profile)) return false;
  return true;
}

/** profile 是对象且至少有一个非空字段（空对象、null、空串一律不算） */
function hasAnyField(profile: unknown): boolean {
  if (typeof profile !== 'object' || profile === null) return false;
  return Object.values(profile as Record<string, unknown>).some((v) => {
    if (v == null || v === '' || v === false) return false;
    if (Array.isArray(v)) return v.length > 0;
    return true;
  });
}

/** 从 localStorage 读一份判定快照。读失败时当作全新访客，宁可多显示一次。 */
export function readOnboardSnapshot(): OnboardSnapshot {
  return {
    onboarded: readJson<number | null>(KEY_ONBOARDED, null),
    replay: readJson<number | null>(KEY_REPLAY, null),
    saved: readJson<unknown[]>(KEY_SAVED, []),
    track: readJson<Record<string, unknown>>(KEY_TRACK, {}),
    profile: readJson<unknown>(KEY_PROFILE, null),
  };
}

/** 标记「已看过」当前版本。任意一屏点跳过、或走完最后一屏都调它。 */
export function markOnboarded(): void {
  writeJson(KEY_ONBOARDED, ONBOARD_VERSION);
}

/**
 * 手动重看：只置 replay 标记，不清 onboarded——重看不该改变「已看过」这个事实。
 *
 * 同时派发一个 window 事件：引导条组件常驻在 App 里，从数据说明页点「重看」
 * 不会让它重新挂载，只改 localStorage 它读不到。事件是这层通知的唯一通道。
 */
export function requestReplay(): void {
  writeJson(KEY_REPLAY, 1);
  try {
    window.dispatchEvent(new Event(REPLAY_EVENT));
  } catch {
    /* 非浏览器环境（node 里跑冒烟测试）没有 window，忽略 */
  }
}

/** 重看请求的事件名。组件监听它，把 visible 拉回 true。 */
export const REPLAY_EVENT = 'opd:replay-onboarding';

/** 组件读完 replay 后必须清掉，否则每次刷新都弹。 */
export function clearReplay(): void {
  writeJson(KEY_REPLAY, null);
}
