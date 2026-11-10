// src/components/AboutView.tsx
// 数据说明页：收录多少、核过多少、有多少条来源、哪些到期该复核。
// 这一页的存在本身就是产品的一部分——它把「数据可信到什么程度」摆到台面上，
// 而不是藏在 JSON 里等人发现。
import { useEffect, useMemo, useState } from 'react';
import { useI18n } from '../i18n';
import { loadIndex, loadPrograms } from '../lib/data';
import { requestReplay } from '../lib/onboarding';
import { navigate } from '../lib/router';
import { useDocumentTitle } from '../lib/useTitle';
import type { ProgramIndexEntry, ProgramRecord } from '../types';

/** 距今多少天。缺日期返回 null，不当作 0 处理。 */
function daysSince(date: string | null | undefined): number | null {
  if (!date) return null;
  const t = Date.parse(date);
  if (Number.isNaN(t)) return null;
  return Math.floor((Date.now() - t) / 86400000);
}

export function AboutView() {
  const { t, td, te, lang } = useI18n();
  const [recs, setRecs] = useState<ProgramRecord[] | null>(null);
  const [idx, setIdx] = useState<ProgramIndexEntry[] | null>(null);

  useDocumentTitle([t('dataTitle'), t('pageTitleSuffix')]);

  useEffect(() => {
    let alive = true;
    // 来源条数在完整记录里，复核状态在索引里（由 sync-data.mjs 按
    // data/review-policy.json 算好）——两处各取所需，不在这里重算周期。
    Promise.all([loadPrograms(), loadIndex()])
      .then(([p, i]) => {
        if (!alive) return;
        setRecs(p);
        setIdx(i);
      })
      .catch(() => {
        if (!alive) return;
        setRecs([]);
        setIdx([]);
      });
    return () => {
      alive = false;
    };
  }, []);

  const reviewById = useMemo(() => {
    const m = new Map<string, ProgramIndexEntry>();
    for (const e of idx ?? []) m.set(e.id, e);
    return m;
  }, [idx]);

  const stats = useMemo(() => {
    const list = recs ?? [];
    const total = list.length;
    const verified = list.filter((r) => !!r.last_verified).length;
    const sources = list.reduce((n, r) => n + (r.sources?.length ?? 0), 0);
    const primary = list.reduce(
      (n, r) => n + (r.sources ?? []).filter((s) => s.type === 'primary').length,
      0,
    );
    const entries = idx ?? [];
    const overdue = entries.filter(
      (e) => e.review_state === 'overdue' || e.review_state === 'unknown',
    ).length;
    const dueSoon = entries.filter((e) => e.review_state === 'due_soon').length;
    return { total, verified, sources, primary, overdue, dueSoon };
  }, [recs, idx]);

  // 到期该核的那几条单独列出来。这一页的目标不是夸数据全，
  // 而是让人能在一分钟内判断「我要用的那条是不是刚核过」。
  const pending = useMemo(() => {
    const entries = idx ?? [];
    return entries
      .filter(
        (e) =>
          e.review_state === 'overdue' ||
          e.review_state === 'due_soon' ||
          e.review_state === 'unknown',
      )
      .sort((a, b) => (a.review_days_left ?? 1e9) - (b.review_days_left ?? 1e9));
  }, [idx]);

  if (!recs || !idx) return <p className="state">{t('searchHint')}…</p>;

  return (
    <div className="page">
      <header className="page__head">
        <h1 className="page__title">{t('dataTitle')}</h1>
        <p className="page__intro">{t('dataIntro')}</p>
      </header>

      <ul className="statbar">
        <li className="stat">
          <span className="stat__num">{stats.total}</span>
          <span className="stat__label">{t('dataTotal')}</span>
        </li>
        <li className="stat">
          <span className="stat__num">{stats.verified}</span>
          <span className="stat__label">{t('dataVerified')}</span>
        </li>
        <li className="stat">
          <span className="stat__num">{stats.sources}</span>
          <span className="stat__label">{t('dataSources')}</span>
        </li>
        <li className={stats.overdue > 0 ? 'stat stat--warn' : 'stat'}>
          <span className="stat__num">{stats.overdue}</span>
          <span className="stat__label">{t('dataStale')}</span>
        </li>
        <li className={stats.dueSoon > 0 ? 'stat stat--warn' : 'stat'}>
          <span className="stat__num">{stats.dueSoon}</span>
          <span className="stat__label">{t('dataDueSoon')}</span>
        </li>
      </ul>

      <table className="dtable">
        <thead>
          <tr>
            <th>{t('navBrowse')}</th>
            <th>{t('authority')}</th>
            <th>{t('passportCheck')}</th>
            <th>{t('sources')}</th>
            <th>{t('lastVerified')}</th>
            <th>{t('dataNextReview')}</th>
          </tr>
        </thead>
        <tbody>
          {recs.map((r) => {
            const d = daysSince(r.last_verified);
            const rv = reviewById.get(r.program.id);
            const overdue = rv?.review_state === 'overdue' || rv?.review_state === 'unknown';
            const soon = rv?.review_state === 'due_soon';
            return (
              <tr key={r.program.id}>
                <td>
                  <a href={`#/p/${encodeURIComponent(r.program.id)}`}>
                    {lang === 'en' ? r.program.name_en || r.program.name : r.program.name}
                  </a>
                </td>
                <td>{td(r.program.authority ?? '')}</td>
                <td>{te(r.eligibility.passport_types?.mainland_china)}</td>
                <td>
                  {(r.sources ?? []).filter((s) => s.type === 'primary').length} /{' '}
                  {(r.sources ?? []).length}
                </td>
                <td className={overdue ? 'dtable__stale' : undefined}>
                  {r.last_verified ?? '—'}
                  {d != null ? ` (${d}d)` : ''}
                </td>
                <td className={overdue || soon ? 'dtable__stale' : undefined}>
                  {rv?.review_due ?? '—'}
                  {rv?.review_days_left != null
                    ? rv.review_days_left < 0
                      ? ` (${t('dataOverdueBy').replace('{n}', String(-rv.review_days_left))})`
                      : ` (${rv.review_days_left}d)`
                    : ''}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* 到期名单：把「该去核哪几条」直接摆在页面上，
          这样「数据会过时」不是一句抽象的免责声明，而是一张有名字的清单。 */}
      {pending.length > 0 && (
        <section className="sec">
          <h2 className="sec__title">{t('dataPendingTitle')}</h2>
          <p className="sec__note">{t('dataPendingNote')}</p>
          <ul className="ul">
            {pending.map((e) => (
              <li key={e.id}>
                <a href={`#/p/${encodeURIComponent(e.id)}`}>
                  {lang === 'en' ? e.name_en || e.name : e.name}
                </a>
                {' · '}
                {e.review_state === 'overdue'
                  ? t('dataOverdueBy').replace('{n}', String(Math.abs(e.review_days_left ?? 0)))
                  : e.review_state === 'unknown'
                    ? t('dataNoDate')
                    : t('dataDueIn').replace('{n}', String(e.review_days_left ?? 0))}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="sec">
        <h2 className="sec__title">{t('dataRules')}</h2>
        <ul className="ul">
          <li>
            {lang === 'en'
              ? 'Every eligibility call traces to one official URL. Secondary sources never drive a verdict.'
              : '每条资格判定只对应一个官方 URL；二手来源不作为判定依据。'}
          </li>
          <li>
            {lang === 'en'
              ? 'If an official page does not state a field, it says who to ask instead — never filled with a plausible guess.'
              : '官方页面没写的字段，写明「官方未规定、该向谁确认」，不填一个看起来合理的值。'}
          </li>
          <li>
            {lang === 'en'
              ? 'Personal data (profile, saved, applications) stays in this browser. No account, no server, no upload.'
              : '个人数据（画像、收藏、申请进度）只存在本浏览器，没有账号、没有服务器、不上传。'}
          </li>
          <li>
            {lang === 'en'
              ? 'This site is an index. It does not file applications and does not give visa advice.'
              : '本站是索引，不代办申请、不提供签证建议。提交前请自行复核官方页面。'}
          </li>
        </ul>
      </section>

      {/* 手动重看引导：唯一的入口在这里。挂在数据说明页而不是首屏，
          因为首屏已经有引导条本身，再放一个按钮会让「跳过」这个决定显得可疑。 */}
      <section className="sec">
        <h2 className="sec__title">{t('onboardStep2Title')}</h2>
        <button
          type="button"
          className="btn"
          data-onboard-replay=""
          onClick={() => {
            requestReplay();
            navigate('/');
          }}
        >
          {t('onboardReplay')}
        </button>
      </section>
    </div>
  );
}
