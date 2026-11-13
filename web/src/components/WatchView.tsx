// src/components/WatchView.tsx
// 追踪清单（M3）：把关注的项目放在一起，汇总它们的申请窗口。
//
// 这一页唯一的硬纪律：**确定性四档永不混排**。
//   confirmed  官方已公布 → 可以按这个日期安排
//   inferred   按往年规律推算 → 显示「参考日期（未确认）」，并说明不能据此卡时间
//   rolling    常年可申 → 说「常年可申，无申请窗口」，绝不编一个日期出来
//   unknown    官方没公布 → 只说「日期未公布」，不给任何数字
//
// 「滚动型不编日期」不是文案问题，是数据问题：rolling 类项目（如德国 20 条
// 找工作签证、荷兰 orientation year）本来就没有窗口，前端若按「今天 + 往年
// 规律」补一个 date，用户会按那个日期去准备，而官方从未承诺过这一天。
// 所以滚动型的窗口区只写口径，不出现任何 <time>。
import { useEffect, useMemo, useState } from 'react';
import { useI18n } from '../i18n';
import { loadIndex } from '../lib/data';
import { detailHref, navigate } from '../lib/router';
import { useDocumentTitle } from '../lib/useTitle';
import type { useWatch } from '../lib/store';
import type { ProgramIndexEntry } from '../types';

const DAY = 86400000;

/** 距今天的天数（负=已过去）。与 CalendarView / track.py 同口径，按天粒度。 */
function daysFrom(iso: string | null | undefined, now: number): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  return Math.round((t - now) / DAY);
}

/** 一条项目在清单里的窗口口径。四档互斥，顺序即判定优先级。 */
type WindowMode = 'confirmed' | 'inferred' | 'rolling' | 'unknown';

function modeOf(p: ProgramIndexEntry): WindowMode {
  // 滚动型先判：这类项目即便 schedule_status 是 open，也不该出现日期
  if (p.schedule_type === 'rolling' || p.schedule_status === 'always_open') return 'rolling';
  if (p.date_confidence === 'confirmed' && (p.window_open || p.window_close)) return 'confirmed';
  if (p.date_confidence === 'inferred') return 'inferred';
  return 'unknown';
}

export function WatchView({ watch }: { watch: ReturnType<typeof useWatch> }) {
  const { t, te, td, lang } = useI18n();
  const [all, setAll] = useState<ProgramIndexEntry[] | null>(null);
  const now = useMemo(() => Date.now(), []);

  useDocumentTitle([t('watchTitle'), t('pageTitleSuffix')]);

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

  // 清单里可能残留已下架项目的 id，渲染时跳过但不悄悄删掉用户的清单
  const rows = useMemo(
    () => watch.list.map((id) => byId.get(id)).filter((p): p is ProgramIndexEntry => !!p),
    [watch.list, byId],
  );

  /** 窗口状态的文案：四档各一句，rolling 与 unknown 都不许出现日期 */
  const statusText = (p: ProgramIndexEntry): string => {
    const mode = modeOf(p);
    if (mode === 'rolling') return t('watchStatusAlways');
    if (p.schedule_status === 'open') return t('watchStatusOpen');
    if (p.schedule_status === 'upcoming') return t('watchStatusUpcoming');
    if (p.schedule_status === 'closed') return t('watchStatusClosed');
    return t('watchStatusUnknown');
  };

  /** 距离一句话：只在 confirmed 且有具体日期时出现 */
  const countdown = (iso: string | null | undefined): string | null => {
    const d = daysFrom(iso, now);
    if (d == null) return null;
    if (d === 0) return t('watchToday');
    return d > 0
      ? t('watchDaysFromNow').replace('{n}', String(d))
      : t('watchDaysAgo').replace('{n}', String(-d));
  };

  if (!all) return <p className="state">{t('searchHint')}…</p>;

  return (
    <div className="watch">
      <header className="page__head">
        <h1 className="page__title">{t('watchTitle')}</h1>
        <p className="page__intro">{t('watchIntro')}</p>
      </header>

      {rows.length === 0 ? (
        <div className="state">
          <p className="state__title">{t('watchEmpty')}</p>
          <p className="state__body">{t('watchEmptyBody')}</p>
          <a className="btn btn--primary" href="#/">
            {t('navBrowse')}
          </a>
        </div>
      ) : (
        <>
          <ul className="watchlist">
            {rows.map((p) => {
              const mode = modeOf(p);
              const open = daysFrom(p.window_open, now);
              const close = daysFrom(p.window_close, now);
              // 提醒日 = 开放日 − 建议提前天数。只有 confirmed 才算，
              // 推算日期再减提前期会得到一个「精确但错的」日期，比不给更糟。
              const remind =
                mode === 'confirmed' && open != null && p.lead_time_days != null
                  ? open - p.lead_time_days
                  : null;

              return (
                <li key={p.id} className={`wrow wrow--${mode}`}>
                  <div className="wrow__head">
                    <a className="wrow__title" href={detailHref(p.id)}>
                      {lang === 'en' ? p.name_en || p.name : p.name}
                    </a>
                    <span className="wrow__meta">
                      {te(p.region)} · {td(p.country)} · {p.last_verified ?? '—'}
                    </span>
                  </div>

                  <div className="wrow__window">
                    <span className="wrow__label">{t('watchWindow')}</span>

                    {mode === 'rolling' ? (
                      // 滚动型：只有口径，没有任何日期节点
                      <span className="wrow__rolling">{t('watchRolling')}</span>
                    ) : mode === 'confirmed' ? (
                      <span className="wrow__dates">
                        <span className="wrow__tag wrow__tag--ok">{t('watchConfirmed')}</span>
                        <time dateTime={p.window_open ?? undefined}>{p.window_open}</time>
                        {p.window_close ? (
                          <>
                            {' → '}
                            <time dateTime={p.window_close}>{p.window_close}</time>
                          </>
                        ) : null}
                        {p.window_close && countdown(p.window_close) ? (
                          <span className="wrow__count">{countdown(p.window_close)}</span>
                        ) : null}
                      </span>
                    ) : mode === 'inferred' ? (
                      <span className="wrow__dates">
                        <span className="wrow__tag wrow__tag--warn">{t('watchInferred')}</span>
                        {/* 推算日期照样可能带具体值，但不给倒计时、不当官方日期用 */}
                        {p.window_open ? (
                          <span className="wrow__loose">{p.window_open}</span>
                        ) : (
                          <span className="wrow__nodate">{t('watchNoDate')}</span>
                        )}
                        <span className="wrow__note">{t('watchInferredHint')}</span>
                      </span>
                    ) : (
                      <span className="wrow__dates">
                        <span className="wrow__nodate">{t('watchNoDate')}</span>
                        <span className="wrow__note">{t('watchNoWindowData')}</span>
                      </span>
                    )}
                  </div>

                  <div className="wrow__foot">
                    <span className={`wrow__status wrow__status--${mode}`}>{statusText(p)}</span>
                    {p.lead_time_days != null && (
                      <span className="wrow__lead">
                        {t('watchLead')} {p.lead_time_days} {t('calDays')}
                        {remind != null && mode === 'confirmed' ? (
                          <span className="wrow__remind">
                            {' · '}
                            {remind <= 0 ? t('calShouldPrepare') : countdown(isoOf(remind))}
                          </span>
                        ) : null}
                      </span>
                    )}
                    <button
                      type="button"
                      className="btn btn--ghost btn--sm"
                      onClick={() => watch.remove(p.id)}
                    >
                      {t('watchRemove')}
                    </button>
                  </div>

                  {/* 关闭的窗口要说清「上一轮过了」，而不是留个空格让人以为还没开 */}
                  {mode === 'confirmed' && close != null && close < 0 ? (
                    <p className="wrow__closed">{t('calPassed')}</p>
                  ) : null}
                </li>
              );
            })}
          </ul>

          <div className="watch__foot">
            <button type="button" className="btn btn--ghost" onClick={watch.clear}>
              {t('watchClear')}
            </button>
            <button type="button" className="btn btn--ghost" onClick={() => navigate('/calendar')}>
              {t('navCalendar')}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

/** 天数（自 1970 起的整数天）→ YYYY-MM-DD。与 CalendarView 的算法同源。 */
function isoOf(day: number): string {
  return new Date(day * DAY).toISOString().slice(0, 10);
}
