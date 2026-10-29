// src/components/AboutView.tsx
// 数据说明页：收录多少、核过多少、有多少条来源、哪些过期没复核。
// 这一页的存在本身就是产品的一部分——它把「数据可信到什么程度」摆到台面上，
// 而不是藏在 JSON 里等人发现。
import { useEffect, useMemo, useState } from 'react';
import { useI18n } from '../i18n';
import { loadPrograms } from '../lib/data';
import { useDocumentTitle } from '../lib/useTitle';
import type { ProgramRecord } from '../types';

/** 距今超过这么多天就算过期未复核（与 CI 里的链接检查节奏对齐） */
const STALE_DAYS = 90;

function daysSince(date: string | null | undefined): number | null {
  if (!date) return null;
  const t = Date.parse(date);
  if (Number.isNaN(t)) return null;
  return Math.floor((Date.now() - t) / 86400000);
}

export function AboutView() {
  const { t, td, te, lang } = useI18n();
  const [recs, setRecs] = useState<ProgramRecord[] | null>(null);

  useDocumentTitle([t('dataTitle'), t('pageTitleSuffix')]);

  useEffect(() => {
    let alive = true;
    loadPrograms()
      .then((d) => alive && setRecs(d))
      .catch(() => alive && setRecs([]));
    return () => {
      alive = false;
    };
  }, []);

  const stats = useMemo(() => {
    const list = recs ?? [];
    const total = list.length;
    const verified = list.filter((r) => !!r.last_verified).length;
    const sources = list.reduce((n, r) => n + (r.sources?.length ?? 0), 0);
    const primary = list.reduce(
      (n, r) => n + (r.sources ?? []).filter((s) => s.type === 'primary').length,
      0,
    );
    const stale = list.filter((r) => {
      const d = daysSince(r.last_verified);
      return d != null && d > STALE_DAYS;
    }).length;
    return { total, verified, sources, primary, stale };
  }, [recs]);

  if (!recs) return <p className="state">{t('searchHint')}…</p>;

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
        <li className={stats.stale > 0 ? 'stat stat--warn' : 'stat'}>
          <span className="stat__num">{stats.stale}</span>
          <span className="stat__label">{t('dataStale')}</span>
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
          </tr>
        </thead>
        <tbody>
          {recs.map((r) => {
            const d = daysSince(r.last_verified);
            const stale = d != null && d > STALE_DAYS;
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
                <td className={stale ? 'dtable__stale' : undefined}>
                  {r.last_verified ?? '—'}
                  {stale ? ` (${d}d)` : ''}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

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
              ? 'If a page does not state it, the field is left out or marked unverified — never filled with a guess.'
              : '官方页面没写的字段，宁可不填或标注「未能核实」，也不填一个看起来合理的值。'}
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
    </div>
  );
}
