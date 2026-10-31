// src/components/FilterBar.tsx
// 筛选区：搜索 + 资格 + 地区常驻，其余条件折进「更多筛选」。
//
// 顺序是产品判断，不是随手排的：
//   搜索 → 我的资格 → 地区 → [折叠：项目类型 / 标签 / 年龄 / 收藏 / 风险]
// 「我的资格」必须排第一组，因为访客来这里的第一个问题是「我能不能申」，
// 而不是「我想去哪个洲」。原先它排第三组、和「项目类型」视觉等价，
// 实测把筛选面板顶到 584px（桌面视口的 65%），首屏一张卡片都看不到。
//
// 所有选项都从数据里推导（buildFacets），数据加项目不用改这个文件。
import { useState } from 'react';
import { useI18n } from '../i18n';
import { toggleValue, type Facets, type Filters } from '../lib/filters';
import type { ProgramIndexEntry } from '../types';

interface Props {
  filters: Filters;
  facets: Facets;
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
  pair,
}: {
  label: string;
  options: { value: string; count: number }[];
  selected: string[];
  onToggle: (v: string) => void;
  te: (v: string) => string;
  /** 双栏大按钮：只给「我的资格」这种只有 2 项、且决定后续一切的分组用 */
  pair?: boolean;
}) {
  if (options.length === 0) return null;
  return (
    <fieldset className={pair ? 'chips chips--pair' : 'chips'}>
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

/** 统计「除搜索词和地区之外」还有多少条件生效，用于折叠按钮上的徽标 */
function foldedCount(f: Filters): number {
  return (
    f.types.length +
    f.tags.length +
    (f.ageOnly && f.age != null ? 1 : 0) +
    (f.savedOnly ? 1 : 0) +
    (f.criticalOnly ? 1 : 0)
  );
}

export function FilterBar({ filters, facets, onChange, onReset, all }: Props) {
  const { t, te } = useI18n();

  // 折叠区默认收起；但只要有条件生效就展开，否则用户看不到自己选了什么、也取消不掉
  const [open, setOpen] = useState(() => foldedCount(filters) > 0);
  // 窄屏抽屉：默认收起，把首屏整个让给结果卡片
  const [sheet, setSheet] = useState(false);
  const folded = foldedCount(filters);

  // 标签只展示有筛选价值的那几个。
  // 阈值取「总数的 25%」而不是写死 3：项目从 11 条长到 50 条时，
  // 原本只匹配 1–2 个的标签会自动回到展开区，不需要改代码。
  const tagThreshold = Math.max(3, Math.ceil(all.length * 0.25));
  const mainTags = facets.tags.filter((o) => o.count >= tagThreshold);
  const restTags = facets.tags.filter((o) => o.count < tagThreshold);

  return (
    <section className="filters" aria-label={t('filtersToggle')} data-sheet={sheet}>
      {/* 窄屏才显示：一条 sticky 条，把筛选面板整体收进抽屉。
          宽度 ≥720px 时此按钮被 CSS 隐藏，桌面仍是常驻面板。 */}
      <button
        type="button"
        className="filters__sheetbtn"
        aria-expanded={sheet}
        aria-controls="filters-body"
        onClick={() => setSheet(!sheet)}
      >
        <span>{t('filtersToggle')}</span>
        {folded > 0 && <span className="filters__more__badge">{folded}</span>}
        <span className="filters__more__caret" aria-hidden="true">
          {sheet ? '▴' : '▾'}
        </span>
      </button>

      <div className="filters__body" id="filters-body">
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

      {/* 第一组：我的资格。两栏大按钮，选中即实心。 */}
      <ChipGroup
        label={t('filterStatus')}
        options={facets.statuses}
        selected={filters.statuses}
        onToggle={(v) => onChange({ ...filters, statuses: toggleValue(filters.statuses, v) })}
        te={te}
        pair
      />

      <ChipGroup
        label={t('filterRegion')}
        options={facets.regions}
        selected={filters.regions}
        onToggle={(v) => onChange({ ...filters, regions: toggleValue(filters.regions, v) })}
        te={te}
      />

      <button
        type="button"
        className="filters__more"
        aria-expanded={open}
        aria-controls="filters-more"
        onClick={() => setOpen(!open)}
      >
        <span>{open ? t('fewerFilters') : t('moreFilters')}</span>
        {folded > 0 && (
          <span className="filters__more__badge">
            {t('selectedCount')} {folded}
          </span>
        )}
        <span className="filters__more__caret" aria-hidden="true">
          {open ? '▴' : '▾'}
        </span>
      </button>

      {/* 折叠区始终渲染（用 hidden 收起），这样键盘 Tab 顺序、fieldset 语义都不依赖展开状态 */}
      <div className="filters__extra" id="filters-more" hidden={!open}>
        <ChipGroup
          label={t('filterType')}
          options={facets.types}
          selected={filters.types}
          onToggle={(v) => onChange({ ...filters, types: toggleValue(filters.types, v) })}
          te={te}
        />

        <ChipGroup
          label={t('filterTags')}
          options={mainTags}
          selected={filters.tags}
          onToggle={(v) => onChange({ ...filters, tags: toggleValue(filters.tags, v) })}
          te={te}
        />

        {restTags.length > 0 && (
          <details className="filters__rest">
            <summary>
              {t('otherTags')}（{restTags.length}）
            </summary>
            <ChipGroup
              label={t('otherTags')}
              options={restTags}
              selected={filters.tags}
              onToggle={(v) => onChange({ ...filters, tags: toggleValue(filters.tags, v) })}
              te={te}
            />
          </details>
        )}

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
      </div>

      {/* 结果计数只在 .listbar 里出现一次。这里再显示一遍，会让读者
          怀疑两个不同的数字（实测两处相距 380px），所以只留清空按钮。 */}
      <div className="filters__foot">
        <button type="button" className="btn btn--ghost" onClick={onReset}>
          {t('reset')}
        </button>
        {/* 抽屉里的「看结果」：选完条件直接收起，不用再去找上面的按钮 */}
        <button type="button" className="btn filters__apply" onClick={() => setSheet(false)}>
          {t('closeFilters')}
        </button>
      </div>
      </div>
    </section>
  );
}
