// src/components/CompareView.tsx
// 对比页：把最多 4 个项目并排放在同一张表里，逐字段对齐。
// 表格用 CSS grid 而不是 <table>，因为手机上 <table> 会横跑，grid 可以逐项换行。
import { useEffect, useMemo, useState } from 'react';
import { useI18n } from '../i18n';
import { loadIndex } from '../lib/data';
import { COMPARE_MAX } from '../lib/store';
import { detailHref } from '../lib/router';
import { useDocumentTitle } from '../lib/useTitle';
import type { ProgramIndexEntry } from '../types';

interface Props {
  compareIds: string[];
  onRemove: (id: string) => void;
  onClear: () => void;
}

export function CompareView({ compareIds, onRemove, onClear }: Props) {
  const { t, td, te, lang } = useI18n();
  const [all, setAll] = useState<ProgramIndexEntry[] | null>(null);

  useDocumentTitle([t('compareTitle'), t('pageTitleSuffix')]);

  useEffect(() => {
    let alive = true;
    loadIndex()
      .then((d) => alive && setAll(d))
      .catch(() => alive && setAll([]));
    return () => {
      alive = false;
    };
  }, []);

  const items = useMemo(() => {
    if (!all) return [];
    const m = new Map(all.map((p) => [p.id, p]));
    return compareIds.map((id) => m.get(id)).filter(Boolean) as ProgramIndexEntry[];
  }, [all, compareIds]);

  if (!all) return <p className="state">{t('searchHint')}…</p>;

  /** 每行一个字段，行内按列展开——手机上每列独立一行，不会横向溢出 */
  const rows: { label: string; render: (p: ProgramIndexEntry) => React.ReactNode }[] = [
    {
      label: t('filterRegion'),
      render: (p) => `${te(p.region)} · ${td(p.country)}`,
    },
    {
      label: t('filterType'),
      render: (p) => te(p.program_type),
    },
    {
      label: t('passportCheck'),
      render: (p) => <span className={`badge badge--${p.status === 'eligible' ? 'ok' : 'no'}`}>{te(p.status)}</span>,
    },
    {
      label: t('age'),
      // 0–99 是「官方没写年龄限制」的占位区间，对比表里同样按未核实显示
      render: (p) =>
        p.age_min === 0 && p.age_max === 99
          ? t('notVerified')
          : p.age_min != null
            ? `${p.age_min}–${p.age_max ?? '—'}`
            : '—',
    },
    {
      label: t('stay'),
      render: (p) => (p.max_stay_months != null ? `${p.max_stay_months} ${t('monthsUnit')}` : '—'),
    },
    {
      label: t('education'),
      render: (p) => te(p.education ?? 'any'),
    },
    {
      label: t('languageReq'),
      render: (p) => (p.language_required ? t('required') : t('notRequired')),
    },
    {
      label: t('funds'),
      render: (p) =>
        p.funds_amount != null
          ? `${p.funds_amount.toLocaleString()} ${p.funds_currency ?? ''}`
          : t('profileAny'),
    },
    {
      label: t('risks'),
      render: (p) =>
        p.risk_levels.length > 0 ? p.risk_levels.map((r) => te(r)).join(' · ') : '—',
    },
    {
      label: t('lastVerified'),
      render: (p) => p.last_verified ?? '—',
    },
  ];

  return (
    <div className="page">
      <header className="page__head">
        <h1 className="page__title">{t('compareTitle')}</h1>
        <p className="page__intro">
          {items.length} / {COMPARE_MAX}
        </p>
      </header>

      {items.length === 0 ? (
        <div className="state">
          <p className="state__title">{t('compareEmpty')}</p>
          <a className="btn btn--primary" href="#/">
            {t('navBrowse')}
          </a>
        </div>
      ) : (
        <>
          <div className="cmp" style={{ ['--cols' as string]: String(items.length) }}>
            {/* 表头：项目名 + 移出按钮 */}
            <div className="cmp__head">
              <div className="cmp__cell cmp__cell--label" />
              {items.map((p) => (
                <div className="cmp__cell" key={p.id}>
                  <a className="cmp__title" href={detailHref(p.id)}>
                    {lang === 'en' ? p.name_en || p.name : p.name}
                  </a>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={() => onRemove(p.id)}
                  >
                    {t('trackRemove')}
                  </button>
                </div>
              ))}
            </div>

            {rows.map((r) => (
              <div className="cmp__row" key={r.label}>
                <div className="cmp__cell cmp__cell--label">{r.label}</div>
                {items.map((p) => (
                  <div className="cmp__cell" key={p.id}>
                    {r.render(p)}
                  </div>
                ))}
              </div>
            ))}
          </div>

          <button type="button" className="btn btn--ghost" onClick={onClear}>
            {t('compareClear')}
          </button>
        </>
      )}
    </div>
  );
}
