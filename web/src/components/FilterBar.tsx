// src/components/FilterBar.tsx
// 筛选区：搜索框 + 年龄输入 + 四组多选筛选。
// 所有选项都从数据里推导（buildFacets），数据加项目不用改这个文件。
import { useI18n } from '../i18n';
import { toggleValue, type Facets, type Filters } from '../lib/filters';
import type { ProgramIndexEntry } from '../types';

interface Props {
  filters: Filters;
  facets: Facets;
  /** 当前筛选后的条数，显示在结果行 */
  resultCount: number;
  onChange: (next: Filters) => void;
  onReset: () => void;
  all: ProgramIndexEntry[];
}

function ChipGroup({
  label,
  options,
  selected,
  onToggle,
  te,
}: {
  label: string;
  options: { value: string; count: number }[];
  selected: string[];
  onToggle: (v: string) => void;
  te: (v: string) => string;
}) {
  if (options.length === 0) return null;
  return (
    <fieldset className="chips">
      <legend className="chips__legend">{label}</legend>
      <div className="chips__row">
        {options.map((o) => {
          const on = selected.includes(o.value);
          return (
            <button
              type="button"
              key={o.value}
              className={on ? 'chip chip--on' : 'chip'}
              aria-pressed={on}
              onClick={() => onToggle(o.value)}
            >
              {te(o.value)}
              <span className="chip__count">{o.count}</span>
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

export function FilterBar({ filters, facets, resultCount, onChange, onReset, all }: Props) {
  const { t, te } = useI18n();

  return (
    <section className="filters" aria-label={t('filterTags')}>
      <div className="filters__search">
        <input
          type="search"
          className="input"
          placeholder={t('searchPlaceholder')}
          value={filters.q}
          onChange={(e) => onChange({ ...filters, q: e.target.value })}
          aria-label={t('searchPlaceholder')}
        />
      </div>

      <ChipGroup
        label={t('filterRegion')}
        options={facets.regions}
        selected={filters.regions}
        onToggle={(v) => onChange({ ...filters, regions: toggleValue(filters.regions, v) })}
        te={te}
      />
      <ChipGroup
        label={t('filterType')}
        options={facets.types}
        selected={filters.types}
        onToggle={(v) => onChange({ ...filters, types: toggleValue(filters.types, v) })}
        te={te}
      />
      <ChipGroup
        label={t('filterStatus')}
        options={facets.statuses}
        selected={filters.statuses}
        onToggle={(v) => onChange({ ...filters, statuses: toggleValue(filters.statuses, v) })}
        te={te}
      />
      <ChipGroup
        label={t('filterTags')}
        options={facets.tags}
        selected={filters.tags}
        onToggle={(v) => onChange({ ...filters, tags: toggleValue(filters.tags, v) })}
        te={te}
      />

      <div className="filters__age">
        <label className="switch">
          <input
            type="checkbox"
            checked={filters.ageOnly}
            onChange={(e) => onChange({ ...filters, ageOnly: e.target.checked })}
          />
          <span>{t('filterAgeOnly')}</span>
        </label>
        <input
          type="number"
          className="input input--age"
          min={14}
          max={99}
          placeholder="25"
          value={filters.age ?? ''}
          disabled={!filters.ageOnly}
          onChange={(e) =>
            onChange({ ...filters, age: e.target.value === '' ? null : Number(e.target.value) })
          }
          aria-label={t('age')}
        />
      </div>

      {/* 两个开关型筛选：收藏范围与风险排雷，和上面的多选维度并列 */}
      <div className="filters__toggles">
        <label className="switch">
          <input
            type="checkbox"
            checked={filters.savedOnly}
            onChange={(e) => onChange({ ...filters, savedOnly: e.target.checked })}
          />
          <span>{t('savedOnly')}</span>
        </label>
        <label className="switch">
          <input
            type="checkbox"
            checked={filters.criticalOnly}
            onChange={(e) => onChange({ ...filters, criticalOnly: e.target.checked })}
          />
          <span>{t('criticalOnly')}</span>
        </label>
      </div>

      <div className="filters__foot">
        <span className="filters__count">
          <strong>{resultCount}</strong> / {all.length} {t('results')}
        </span>
        <button type="button" className="btn btn--ghost" onClick={onReset}>
          {t('reset')}
        </button>
      </div>
    </section>
  );
}
