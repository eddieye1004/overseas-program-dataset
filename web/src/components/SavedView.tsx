// src/components/SavedView.tsx
// 收藏页：直接复用列表卡片，只是数据源换成收藏集合。
// 空态给出回项目库的入口，不留死胡同。
import { useEffect, useMemo, useState } from 'react';
import { useI18n } from '../i18n';
import { loadIndex } from '../lib/data';
import { useDocumentTitle } from '../lib/useTitle';
import type { ProgramIndexEntry } from '../types';
import { Card } from './Card';

export function SavedView({
  savedIds,
  onToggleSave,
}: {
  savedIds: string[];
  onToggleSave: (id: string) => void;
}) {
  const { t } = useI18n();
  const [all, setAll] = useState<ProgramIndexEntry[] | null>(null);

  useDocumentTitle([t('savedTitle'), t('pageTitleSuffix')]);

  useEffect(() => {
    let alive = true;
    loadIndex()
      .then((d) => alive && setAll(d))
      .catch(() => alive && setAll([]));
    return () => {
      alive = false;
    };
  }, []);

  // 按收藏顺序展示（后收藏的排前面），而不是按数据文件顺序
  const list = useMemo(() => {
    if (!all) return [];
    const m = new Map(all.map((p) => [p.id, p]));
    return [...savedIds].reverse().map((id) => m.get(id)).filter(Boolean) as ProgramIndexEntry[];
  }, [all, savedIds]);

  if (!all) return <p className="state">{t('searchHint')}…</p>;

  return (
    <div className="page">
      <header className="page__head">
        <h1 className="page__title">{t('savedTitle')}</h1>
      </header>

      {list.length === 0 ? (
        <div className="state">
          <p className="state__title">{t('savedEmpty')}</p>
          <a className="btn btn--primary" href="#/">
            {t('navBrowse')}
          </a>
        </div>
      ) : (
        <ul className="grid">
          {list.map((p) => (
            <li key={p.id}>
              <Card p={p} saved onToggleSave={onToggleSave} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
