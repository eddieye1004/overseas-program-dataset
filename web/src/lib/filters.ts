// src/lib/filters.ts
// 纯函数筛选逻辑，不依赖 React，方便单独测试与复用。
import type { ProgramIndexEntry } from '../types';

export interface Filters {
  /** 关键词：同时匹配 name / name_en / country / authority / tags */
  q: string;
  regions: string[];
  types: string[];
  /** 资格状态筛选：'eligible' | 'not_eligible' | 'conditional' | 'unknown' */
  statuses: string[];
  tags: string[];
  /** 只看年龄符合的（需要用户提供年龄才生效） */
  ageOnly: boolean;
  age: number | null;
  /** 只看已收藏的项目（需要外部传入收藏集合） */
  savedOnly: boolean;
  /** 只看带致命风险的项目——用于排雷，不用于挑选 */
  criticalOnly: boolean;
}

export const EMPTY_FILTERS: Filters = {
  q: '',
  regions: [],
  types: [],
  statuses: [],
  tags: [],
  ageOnly: false,
  age: null,
  savedOnly: false,
  criticalOnly: false,
};

/** 列表排序方式。match 由智能匹配页使用，不在项目库里出现。 */
export type SortMode = 'default' | 'verified' | 'stay' | 'age';

/** 把数据里的 'YYYY-MM-DD' 转成可比较的数字；缺失排到最后 */
function dateValue(s: string | null): number {
  if (!s) return -1;
  const t = Date.parse(s);
  return Number.isNaN(t) ? -1 : t;
}

/** 排序：稳定、不改原数组。default 保持数据文件里的顺序（等于 id 字母序）。 */
export function sortPrograms(
  list: ProgramIndexEntry[],
  mode: SortMode,
  savedIds: string[] = [],
): ProgramIndexEntry[] {
  const out = [...list];
  switch (mode) {
    case 'verified':
      // 最近核过的排前面，未标注核实日期的沉底
      out.sort((a, b) => dateValue(b.last_verified) - dateValue(a.last_verified));
      break;
    case 'stay':
      // 停留期长的排前面，没有停留期数据的沉底
      out.sort((a, b) => (b.max_stay_months ?? -1) - (a.max_stay_months ?? -1));
      break;
    case 'age':
      // 年龄下限高的排前面，相当于"越晚越来不及的先看"
      out.sort((a, b) => (b.age_max ?? -1) - (a.age_max ?? -1));
      break;
    default:
      // 收藏的置顶，其余保持原顺序
      if (savedIds.length > 0) {
        const set = new Set(savedIds);
        out.sort((a, b) => Number(set.has(b.id)) - Number(set.has(a.id)));
      }
  }
  return out;
}

/** 关键词切词：中英文都按空白切，再小写比对；空查询返回 null 表示不过滤 */
function normalizeQuery(q: string): string[] {
  return q
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean);
}

/**
 * 单条命中判定。多个关键词之间是 AND（都要出现），
 * 同一维度多选之间是 OR（选了大洋洲+亚洲，两条都留下）。
 */
export function matches(
  p: ProgramIndexEntry,
  f: Filters,
  /** 收藏集合由调用方注入，filters.ts 不自己去读 localStorage，保持纯函数 */
  savedIds: readonly string[] = [],
): boolean {
  // 关键词：把所有可搜索文本拼起来做子串匹配，避免漏掉中英文混排
  const terms = normalizeQuery(f.q);
  if (terms.length > 0) {
    const haystack = [
      p.name,
      p.name_en,
      p.country,
      p.country_code,
      p.authority ?? '',
      p.visa_code ?? '',
      p.summary,
      p.id,
      ...(p.tags ?? []),
    ]
      .join(' ')
      .toLowerCase();
    if (!terms.every((t) => haystack.includes(t))) return false;
  }

  if (f.regions.length > 0 && !f.regions.includes(p.region)) return false;
  if (f.types.length > 0 && !f.types.includes(p.program_type)) return false;
  if (f.statuses.length > 0 && !f.statuses.includes(p.status)) return false;

  // 标签是 AND 语义：选了「带薪」+「适合 STEM」，要同时满足（申请人的实际约束）
  if (f.tags.length > 0) {
    const own = new Set(p.tags ?? []);
    if (!f.tags.every((t) => own.has(t))) return false;
  }

  // 年龄：只有用户填了年龄才生效；缺失年龄信息的项目默认保留（不因数据缺失隐藏）
  if (f.ageOnly && f.age != null) {
    if (p.age_min != null && f.age < p.age_min) return false;
    if (p.age_max != null && f.age > p.age_max) return false;
  }

  // 收藏视图：只留收藏过的
  if (f.savedOnly && !savedIds.includes(p.id)) return false;

  // 致命风险视图：只留 risks 里出现 critical 的
  if (f.criticalOnly && !(p.risk_levels ?? []).includes('critical')) return false;

  return true;
}

export function applyFilters(
  list: ProgramIndexEntry[],
  f: Filters,
  savedIds: readonly string[] = [],
): ProgramIndexEntry[] {
  return list.filter((p) => matches(p, f, savedIds));
}

/** 统计每个筛选维度当前有多少个可用选项，全部从数据推导，不在代码里硬编码列表 */
export interface Facets {
  regions: { value: string; count: number }[];
  types: { value: string; count: number }[];
  statuses: { value: string; count: number }[];
  tags: { value: string; count: number }[];
}

export function buildFacets(list: ProgramIndexEntry[]): Facets {
  const count = (
    pick: (p: ProgramIndexEntry) => string[] | string,
  ): { value: string; count: number }[] => {
    const map = new Map<string, number>();
    for (const p of list) {
      const raw = pick(p);
      const values = Array.isArray(raw) ? raw : [raw];
      for (const v of values) {
        if (!v) continue;
        map.set(v, (map.get(v) ?? 0) + 1);
      }
    }
    return [...map.entries()]
      .map(([value, c]) => ({ value, count: c }))
      .sort((a, b) => b.count - a.count || a.value.localeCompare(b.value));
  };

  return {
    regions: count((p) => p.region),
    types: count((p) => p.program_type),
    statuses: count((p) => p.status),
    tags: count((p) => p.tags ?? []),
  };
}

/** 在数组里切换某个值（多选筛选按钮共用） */
export function toggleValue(arr: string[], v: string): string[] {
  return arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v];
}
