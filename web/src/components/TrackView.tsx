// src/components/TrackView.tsx
// 我的申请：按状态分列看板 + 每条的「下一步」。
//
// 为什么加「下一步」：状态（待办/已递交…）是使用者自己填的，看板只能帮人回忆；
// 真正让人回来的是「什么时候该动手」。窗口开放日、关闭日、材料准备天数是数据
// 里已有的事实，算成一句话之后，看板就从备忘录变成了日程。
import { useEffect, useMemo, useState } from 'react';
import { useI18n } from '../i18n';
import { TRACK_STATUS, TRACK_TEXT, type TrackStatus, type UiKey } from '../i18n/ui';
import { loadIndex, loadPrograms } from '../lib/data';
import { nextAction, rankByUrgency, type NextAction } from '../lib/nextstep';
import { detailHref } from '../lib/router';
import { useDocumentTitle } from '../lib/useTitle';
import type { useTrack } from '../lib/store';
import type { ProgramIndexEntry, ProgramRecord } from '../types';

interface Props {
  track: ReturnType<typeof useTrack>;
}

/** 下一步的一句话。数字都来自 data，不在这里编。 */
function actionText(a: NextAction, t: (k: UiKey) => string): string {
  switch (a.kind) {
    case 'close':
      return a.days == null
        ? t('nextCloseUnknown')
        : t('nextClose').replace('{n}', String(a.days)).replace('{date}', a.date ?? '');
    case 'prep':
      return t('nextPrep')
        .replace('{n}', String(a.days))
        .replace('{date}', a.date ?? '')
        .replace('{prep}', String(a.prepDays));
    case 'open':
      return t('nextOpen').replace('{n}', String(a.days)).replace('{date}', a.date ?? '');
    case 'closed':
      return t('nextClosed').replace('{date}', a.lastClosed ?? '');
    default:
      return t('nextIdle');
  }
}

export function TrackView({ track }: Props) {
  const { t, td, te, lang } = useI18n();
  const [all, setAll] = useState<ProgramIndexEntry[] | null>(null);
  const [full, setFull] = useState<ProgramRecord[] | null>(null);

  useDocumentTitle([t('trackTitle'), t('pageTitleSuffix')]);

  useEffect(() => {
    let alive = true;
    // 索引给卡片字段，完整记录给 documents.prepare_days 与 windows——
    // 「下一步」要算材料准备期，索引里没有这两样。
    Promise.all([loadIndex(), loadPrograms()])
      .then(([i, f]) => {
        if (!alive) return;
        setAll(i);
        setFull(f);
      })
      .catch(() => {
        if (!alive) return;
        setAll([]);
        setFull([]);
      });
    return () => {
      alive = false;
    };
  }, []);

  const byId = useMemo(() => {
    const m = new Map<string, ProgramIndexEntry>();
    for (const p of all ?? []) m.set(p.id, p);
    return m;
  }, [all]);

  const recById = useMemo(() => {
    const m = new Map<string, ProgramRecord>();
    for (const r of full ?? []) m.set(r.program.id, r);
    return m;
  }, [full]);

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

  // 「今天先做这几件」：跨项目排序，只取最紧的三件。
  // 三件而不是全部，是因为一屏给十件事等于没给优先级。
  const urgent = useMemo(() => {
    const ranked = rankByUrgency(
      rows
        .map((r) => ({ id: r.p.id, program: recById.get(r.p.id) }))
        .filter((x): x is { id: string; program: ProgramRecord } => !!x.program),
    );
    // idle（官方压根没公布过日期）没有可执行的动作，不占这三格；
    // closed 要留着——它说的是「上一轮结束了，现在就该备材料」。
    return ranked.filter((r) => r.action.kind !== 'idle').slice(0, 3);
  }, [rows, recById]);

  if (!all || !full) return <p className="state">{t('searchHint')}…</p>;

  return (
    <div className="track">
      <header className="page__head">
        <h1 className="page__title">{t('trackTitle')}</h1>
        <p className="page__intro">{t('trackIntro')}</p>
      </header>

      {rows.length === 0 ? (
        <div className="state">
          <p className="state__title">{t('trackEmpty')}</p>
          {/* 空状态讲清"这里会发生什么"，而不是只说"没有内容"。
              四行状态迁移、"下一步会自动算"、"只存本机"这三点，不写就没人知道。 */}
          <p className="state__body">{t('trackEmptyBody')}</p>
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

          {/* 今天该动手的几件。这一块是「让人回来」的那一半：
              其余部分都只是在等用户主动想起这个网站。 */}
          <section className="nextup" data-nextup="">
            <h2 className="nextup__title">{t('nextUpTitle')}</h2>
            {urgent.length === 0 ? (
              <p className="nextup__empty">{t('nextUpEmpty')}</p>
            ) : (
              <ol className="nextup__list">
                {urgent.map((u) => {
                  const p = byId.get(u.id);
                  return (
                    <li key={u.id} className={`nextup__item nextup__item--${u.action.kind}`}>
                      <a className="nextup__name" href={detailHref(u.id)}>
                        {p ? (lang === 'en' ? p.name_en || p.name : p.name) : u.id}
                      </a>
                      <span className="nextup__what">{actionText(u.action, t as never)}</span>
                    </li>
                  );
                })}
              </ol>
            )}
          </section>

          <ul className="tracklist">
            {rows.map(({ p, e }) => {
              const rec = recById.get(p.id);
              const na = rec ? nextAction(rec) : null;
              return (
                <li key={p.id} className="trackrow">
                  <div className="trackrow__main">
                    <a className="trackrow__title" href={detailHref(p.id)}>
                      {lang === 'en' ? p.name_en || p.name : p.name}
                    </a>
                    <span className="trackrow__meta">
                      {te(p.region)} · {td(p.country)} · {t('lastVerified')} {p.last_verified ?? '—'}
                    </span>
                    {na && na.kind !== 'idle' && (
                      <span className={`trackrow__next trackrow__next--${na.kind}`}>
                        {actionText(na, t as never)}
                      </span>
                    )}
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
              );
            })}
          </ul>

          <button type="button" className="btn btn--ghost" onClick={track.clear}>
            {t('trackClear')}
          </button>
        </>
      )}
    </div>
  );
}
