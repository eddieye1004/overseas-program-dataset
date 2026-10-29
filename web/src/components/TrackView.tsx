// src/components/TrackView.tsx
// 我的申请：按状态分列看板。每个项目一个状态 + 一句备注，全部存本机。
// 这不是申请系统，只是自用的进度板——把它做轻，才不会被误当成「代办」。
import { useEffect, useMemo, useState } from 'react';
import { useI18n } from '../i18n';
import { TRACK_STATUS, TRACK_TEXT, type TrackStatus } from '../i18n/ui';
import { loadIndex } from '../lib/data';
import { detailHref } from '../lib/router';
import { useDocumentTitle } from '../lib/useTitle';
import type { useTrack } from '../lib/store';
import type { ProgramIndexEntry } from '../types';

interface Props {
  track: ReturnType<typeof useTrack>;
}

export function TrackView({ track }: Props) {
  const { t, td, te, lang } = useI18n();
  const [all, setAll] = useState<ProgramIndexEntry[] | null>(null);

  useDocumentTitle([t('trackTitle'), t('pageTitleSuffix')]);

  useEffect(() => {
    let alive = true;
    loadIndex()
      .then((d) => alive && setAll(d))
      .catch(() => alive && setAll([]));
    return () => {
      alive = false;
    };
  }, []);

  const byId = useMemo(() => {
    const m = new Map<string, ProgramIndexEntry>();
    for (const p of all ?? []) m.set(p.id, p);
    return m;
  }, [all]);

  // 只渲染真正在跟进的项目；map 里可能残留已不存在的 id
  const rows = useMemo(
    () =>
      Object.entries(track.map)
        .map(([id, e]) => ({ p: byId.get(id), e }))
        .filter((x): x is { p: ProgramIndexEntry; e: (typeof track.map)[string] } => !!x.p),
    [track.map, byId],
  );

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const r of rows) c[r.e.status] = (c[r.e.status] ?? 0) + 1;
    return c;
  }, [rows]);

  if (!all) return <p className="state">{t('searchHint')}…</p>;

  return (
    <div className="track">
      <header className="page__head">
        <h1 className="page__title">{t('trackTitle')}</h1>
        <p className="page__intro">{t('trackIntro')}</p>
      </header>

      {rows.length === 0 ? (
        <div className="state">
          <p className="state__title">{t('trackEmpty')}</p>
          <a className="btn btn--primary" href="#/">
            {t('navBrowse')}
          </a>
        </div>
      ) : (
        <>
          {/* 状态计数条：一眼看出卡在哪一步 */}
          <ul className="statbar">
            {TRACK_STATUS.map((s) => (
              <li key={s} className={`stat stat--${s}`}>
                <span className="stat__num">{counts[s] ?? 0}</span>
                <span className="stat__label">{TRACK_TEXT[lang][s]}</span>
              </li>
            ))}
          </ul>

          <ul className="tracklist">
            {rows.map(({ p, e }) => (
              <li key={p.id} className="trackrow">
                <div className="trackrow__main">
                  <a className="trackrow__title" href={detailHref(p.id)}>
                    {lang === 'en' ? p.name_en || p.name : p.name}
                  </a>
                  <span className="trackrow__meta">
                    {te(p.region)} · {td(p.country)} · {t('lastVerified')} {p.last_verified ?? '—'}
                  </span>
                </div>

                <div className="trackrow__side">
                  <select
                    className="input input--sm"
                    aria-label={t('trackTitle')}
                    value={e.status}
                    onChange={(ev) => track.setStatus(p.id, ev.target.value as TrackStatus)}
                  >
                    {TRACK_STATUS.map((s) => (
                      <option key={s} value={s}>
                        {TRACK_TEXT[lang][s]}
                      </option>
                    ))}
                  </select>

                  <input
                    className="input input--sm trackrow__note"
                    aria-label={t('trackNote')}
                    placeholder={t('trackNote')}
                    value={e.note}
                    onChange={(ev) => track.setNote(p.id, ev.target.value)}
                  />

                  <a className="btn btn--ghost btn--sm" href={detailHref(p.id)}>
                    {t('trackOpen')}
                  </a>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={() => track.remove(p.id)}
                  >
                    {t('trackRemove')}
                  </button>
                </div>
              </li>
            ))}
          </ul>

          <button type="button" className="btn btn--ghost" onClick={track.clear}>
            {t('trackClear')}
          </button>
        </>
      )}
    </div>
  );
}
