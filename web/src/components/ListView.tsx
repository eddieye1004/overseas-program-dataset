// src/components/ListView.tsx
// 项目库：加载 index.json → 派生筛选项 → 筛选 → 排序 → 渲染卡片。
// 筛选条件放 URL 的 query 段（hash 之后），刷新和分享都不丢。
import { useEffect, useMemo, useRef, useState } from 'react';
import { useI18n } from '../i18n';
import { loadIndex } from '../lib/data';
import {
  applyFilters,
  buildFacets,
  EMPTY_FILTERS,
  sortPrograms,
  type Filters,
  type SortMode,
} from '../lib/filters';
import { useDocumentTitle } from '../lib/useTitle';
import type { UiKey } from '../i18n/ui';
import type { ProgramIndexEntry } from '../types';
import { Card } from './Card';
import { FilterBar } from './FilterBar';

/** 空结果时列出「当前生效的单个条件」，供用户点掉最可能过严的那一项 */
interface ActiveChip {
  key: string;
  label: string;
  /** 返回移除该条件后的新 Filters，不修改传入对象 */
  without: (f: Filters) => Filters;
}

function activeChips(
  f: Filters,
  t: (k: UiKey) => string,
  te: (s: string) => string,
): ActiveChip[] {
  const out: ActiveChip[] = [];
  const dropFrom =
    (field: 'regions' | 'types' | 'statuses' | 'tags', v: string) =>
    (d: Filters): Filters => ({ ...d, [field]: d[field].filter((x) => x !== v) });

  if (f.q) out.push({ key: 'q', label: `“${f.q}”`, without: (d) => ({ ...d, q: '' }) });
  f.regions.forEach((v) =>
    out.push({ key: `r:${v}`, label: te(v), without: dropFrom('regions', v) }),
  );
  f.types.forEach((v) =>
    out.push({ key: `t:${v}`, label: te(v), without: dropFrom('types', v) }),
  );
  f.statuses.forEach((v) =>
    out.push({ key: `s:${v}`, label: te(v), without: dropFrom('statuses', v) }),
  );
  f.tags.forEach((v) =>
    out.push({ key: `g:${v}`, label: te(v), without: dropFrom('tags', v) }),
  );
  if (f.ageOnly && f.age != null)
    out.push({
      key: 'a',
      label: `${t('age')} ≤ ${f.age}`,
      without: (d) => ({ ...d, ageOnly: false }),
    });
  if (f.savedOnly)
    out.push({ key: 'sv', label: t('savedOnly'), without: (d) => ({ ...d, savedOnly: false }) });
  if (f.criticalOnly)
    out.push({
      key: 'cr',
      label: t('criticalOnly'),
      without: (d) => ({ ...d, criticalOnly: false }),
    });
  return out;
}

/** 把筛选条件写进 location.hash 的 query 段，便于分享具体筛选视图 */
function filtersToHash(f: Filters, sort: SortMode): string {
  const sp = new URLSearchParams();
  if (f.q) sp.set('q', f.q);
  if (f.regions.length) sp.set('r', f.regions.join(','));
  if (f.types.length) sp.set('t', f.types.join(','));
  if (f.statuses.length) sp.set('s', f.statuses.join(','));
  if (f.tags.length) sp.set('g', f.tags.join(','));
  if (f.ageOnly && f.age != null) sp.set('a', String(f.age));
  if (f.savedOnly) sp.set('sv', '1');
  if (f.criticalOnly) sp.set('cr', '1');
  if (sort !== 'default') sp.set('o', sort);
  const qs = sp.toString();
  return qs ? `#/?${qs}` : '#/';
}

function hashToState(): { filters: Filters; sort: SortMode } {
  const raw = window.location.hash;
  const i = raw.indexOf('?');
  if (i < 0) return { filters: EMPTY_FILTERS, sort: 'default' };
  const sp = new URLSearchParams(raw.slice(i + 1));
  const arr = (k: string) =>
    (sp.get(k) ?? '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
  const a = sp.get('a');
  const o = sp.get('o');
  return {
    filters: {
      q: sp.get('q') ?? '',
      regions: arr('r'),
      types: arr('t'),
      statuses: arr('s'),
      tags: arr('g'),
      ageOnly: a != null,
      age: a != null && a !== '' ? Number(a) : null,
      savedOnly: sp.get('sv') === '1',
      criticalOnly: sp.get('cr') === '1',
    },
    sort: o === 'verified' || o === 'stay' || o === 'age' ? o : 'default',
  };
}

interface Props {
  savedIds: string[];
  onToggleSave: (id: string) => void;
}

export function ListView({ savedIds, onToggleSave }: Props) {
  const { t, te } = useI18n();
  const [all, setAll] = useState<ProgramIndexEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  // 只在首次挂载时解析 URL，之后以组件状态为准，避免来回覆盖用户输入
  const initial = useRef(hashToState()).current;
  const [filters, setFilters] = useState<Filters>(initial.filters);
  const [sort, setSort] = useState<SortMode>(initial.sort);

  // 标签页标题跟随界面语言，hash 路由不会自动改 document.title
  useDocumentTitle([t('listTitle'), t('pageTitleSuffix')]);

  useEffect(() => {
    let alive = true;
    loadIndex()
      .then((d) => alive && setAll(d))
      .catch((e: Error) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, []);

  // 筛选与排序变化时同步到 URL；用 replaceState 避免每次输入都塞一条历史记录
  useEffect(() => {
    const next = filtersToHash(filters, sort);
    if (window.location.hash !== next) {
      window.history.replaceState(null, '', next);
    }
  }, [filters, sort]);

  const facets = useMemo(() => (all ? buildFacets(all) : null), [all]);
  const visible = useMemo(() => {
    if (!all) return [];
    return sortPrograms(applyFilters(all, filters, savedIds), sort, savedIds);
  }, [all, filters, sort, savedIds]);

  if (error) return <p className="state">数据加载失败：{error}</p>;
  if (!all || !facets) return <p className="state">{t('searchHint')}…</p>;

  // 空结果时把生效条件逐个列出来，让用户知道是「哪一条」把结果筛没了
  const chips = activeChips(filters, t, te);

  return (
    <div className="page">
      <header className="page__head">
        <h1 className="page__title">{t('listTitle')}</h1>
        <p className="page__intro">{t('listIntro')}</p>
      </header>

      <FilterBar
        filters={filters}
        facets={facets}
        resultCount={visible.length}
        all={all}
        onChange={setFilters}
        onReset={() => setFilters(EMPTY_FILTERS)}
      />

      <div className="listbar">
        <p className="listbar__count" aria-live="polite">
          {visible.length} {t('results')}
        </p>
        <label className="listbar__sort">
          <span>{t('sortBy')}</span>
          <select
            className="input input--sm"
            value={sort}
            onChange={(e) => setSort(e.target.value as SortMode)}
          >
            <option value="default">{t('sortDefault')}</option>
            <option value="verified">{t('sortVerified')}</option>
            <option value="stay">{t('sortStay')}</option>
            <option value="age">{t('sortAge')}</option>
          </select>
        </label>
      </div>

      {visible.length === 0 ? (
        <div className="state">
          <p className="state__title">{t('noResults')}</p>
          <p className="muted">{t('noResultsHint')}</p>

          {/* 逐个条件给「移除」按钮：比一个笼统的「重置」更能让人看懂是哪条卡住了 */}
          {chips.length > 0 && (
            <>
              <p className="relax__hint">{t('relaxHint')}</p>
              <ul className="relax">
                {chips.map((c) => (
                  <li key={c.key}>
                    <button
                      type="button"
                      className="relax__chip"
                      onClick={() => setFilters(c.without(filters))}
                    >
                      <span>{c.label}</span>
                      <span className="relax__x" aria-hidden="true">
                        ×
                      </span>
                      <span className="sr-only">
                        {t('relaxRemove')} {c.label}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}

          <button className="btn" type="button" onClick={() => setFilters(EMPTY_FILTERS)}>
            {t('clearAll')}
          </button>
        </div>
      ) : (
        <ul className="grid">
          {visible.map((p) => (
            <li key={p.id}>
              <Card p={p} saved={savedIds.includes(p.id)} onToggleSave={onToggleSave} />
            </li>
          ))}
        </ul>
      )}

      <p className="muted listfoot">
        {t('countPrograms')} {all.length}
      </p>
    </div>
  );
}
