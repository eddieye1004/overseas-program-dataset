// src/components/DetailView.tsx
// 详情页：进入时才拉 programs.json（62.5KB），并从中挑出当前项目。
// 所有中文串都过 td()，枚举过 te()，因此同一份数据能完整双语渲染。
import { useEffect, useState } from 'react';
import { useI18n } from '../i18n';
import { loadProgram } from '../lib/data';
import { navigate } from '../lib/router';
import { useDocumentTitle } from '../lib/useTitle';
import type { ProgramRecord } from '../types';

/**
 * 从 URL 里取域名用于展示。来源列表里只写机构名（如「加拿大移民、难民及公民部」），
 * 读者无法一眼判断这条来源是不是真的落在 canada.ca 上，把域名摆出来才可核。
 * 解析失败时回退到原始字符串，不隐藏链接。
 */
function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="sec">
      <h2 className="sec__title">{title}</h2>
      {children}
    </section>
  );
}

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  if (v === null || v === undefined || v === '') return null;
  return (
    <div className="kv">
      <dt>{k}</dt>
      <dd>{v}</dd>
    </div>
  );
}

function money(
  m: { local_amount?: number; currency?: string; cny_estimate?: number } | undefined,
  td: (s: string) => string,
): string {
  if (!m?.local_amount && m?.local_amount !== 0) return '';
  const cur = m.currency ?? '';
  const base = `${m.local_amount.toLocaleString()} ${cur}`.trim();
  const cny = m.cny_estimate ? `（≈ ¥${m.cny_estimate.toLocaleString()}）` : '';
  return td(base + cny);
}

export function DetailView({
  id,
  saved,
  onToggleSave,
  onAddTrack,
  tracked,
  onAddCompare,
  compareFull,
  onSeeRecent,
}: {
  id: string;
  saved: boolean;
  onToggleSave: (id: string) => void;
  onAddTrack: (id: string) => void;
  tracked: boolean;
  onAddCompare: (id: string) => void;
  compareFull: boolean;
  onSeeRecent: (id: string) => void;
}) {
  const { t, td, te, lang } = useI18n();
  const [rec, setRec] = useState<ProgramRecord | null>(null);
  const [state, setState] = useState<'loading' | 'ok' | 'missing' | 'error'>('loading');

  // 标题随项目名走；rec 未到位时先用占位，避免出现「详情 · 海外项目数据库」这种空壳标题
  useDocumentTitle([rec ? (lang === 'en' ? rec.program.name_en || rec.program.name : rec.program.name) : null, t('pageTitleSuffix')]);

  useEffect(() => {
    let alive = true;
    setState('loading');
    loadProgram(id)
      .then((r) => {
        if (!alive) return;
        if (r) {
          setRec(r);
          setState('ok');
          // 进详情就算浏览过，写进最近浏览（最多 6 条）
          onSeeRecent(id);
        } else {
          setState('missing');
        }
      })
      .catch(() => alive && setState('error'));
    return () => {
      alive = false;
    };
    // onSeeRecent 每次渲染都是新函数，故意不放进依赖，避免无限循环
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (state === 'loading') return <p className="state">{t('searchHint')}…</p>;
  if (state !== 'ok' || !rec)
    return (
      <div className="state">
        <p>{t('noResults')}</p>
        <button className="btn" type="button" onClick={() => navigate('/')}>
          {t('back')}
        </button>
      </div>
    );

  const { program: p, eligibility: el, timeline: tl, work_conditions: wc } = rec;
  const title = lang === 'en' ? p.name_en || p.name : p.name;
  const sub = lang === 'en' ? p.name : p.name_en ?? '';
  const passport = el.passport_types ?? {};

  return (
    <article className="detail">
      <button className="btn btn--ghost detail__back" type="button" onClick={() => navigate('/')}>
        ← {t('back')}
      </button>

      <header className="detail__head">
        <div className="detail__badges">
          <span className={`badge badge--${passport.mainland_china === 'eligible' ? 'ok' : 'no'}`}>
            {te(passport.mainland_china)}
          </span>
          <span className="badge">{te(p.region)}</span>
          <span className="badge">{te(p.program_type)}</span>
        </div>
        <h1 className="detail__title">{title}</h1>
        {sub && <p className="detail__sub">{sub}</p>}
        <p className="detail__summary">{td(p.summary)}</p>
        <div className="detail__meta">
          <span>
            {t('authority')}：{td(p.authority)}
          </span>
          <a className="btn btn--primary" href={p.official_url} target="_blank" rel="noreferrer">
            {t('officialSite')} ↗
          </a>
        </div>

        {/* 三个本地动作：收藏、加入申请、加入对比。全部只写 localStorage */}
        <div className="detail__actions">
          <button
            type="button"
            className={saved ? 'btn btn--ghost btn--on' : 'btn btn--ghost'}
            aria-pressed={saved}
            onClick={() => onToggleSave(p.id)}
          >
            {saved ? '★' : '☆'} {saved ? t('unsave') : t('save')}
          </button>
          <button
            type="button"
            className={tracked ? 'btn btn--ghost btn--on' : 'btn btn--ghost'}
            aria-pressed={tracked}
            onClick={() => onAddTrack(p.id)}
          >
            ✓ {t('trackAdd')}
          </button>
          <button
            type="button"
            className="btn btn--ghost"
            disabled={compareFull}
            title={compareFull ? t('compareFull') : t('compare')}
            onClick={() => onAddCompare(p.id)}
          >
            ⇄ {t('compare')}
          </button>
        </div>
        {compareFull && <p className="muted detail__cmpnote">{t('compareFull')}</p>}
      </header>

      {/* 护照资格说明单列，这是整个产品最核心的判定 */}
      {passport.note && (
        <div className="callout callout--warn">
          <strong>{t('passportCheck')}</strong>
          <p>{td(passport.note)}</p>
        </div>
      )}

      <Section title={t('eligibility')}>
        <dl className="kvs">
          <KV
            k={t('ageRequirement')}
            v={
              el.age
                ? `${el.age.min ?? '—'}–${el.age.max ?? '—'}${el.age.note ? ` · ${td(el.age.note)}` : ''}`
                : null
            }
          />
          <KV k={t('education')} v={te(el.education?.minimum_level)} />
          <KV
            k={t('languageReq')}
            v={
              el.language
                ? el.language.required
                  ? (el.language.tests ?? [])
                      .map((x) => `${te(x.test)} ${x.min_score ?? ''}`.trim())
                      .join(' / ') || t('required')
                  : t('notRequired')
                : null
            }
          />
          <KV
            k={t('funds')}
            v={
              el.funds
                ? [money(el.funds.amount, td), td(el.funds.note ?? '')].filter(Boolean).join(' · ')
                : null
            }
          />
          <KV
            k={t('otherReqs')}
            v={
              (el.other_requirements ?? []).length > 0 ? (
                <ul className="ul">
                  {el.other_requirements!.map((o, i) => (
                    <li key={i} className={o.required === false ? 'req req--off' : 'req'}>
                      {/* 中文枚举标签自带「需」前缀，标为不要求时去掉，避免「需体检（不要求）」自相矛盾 */}
                      <span className="req__type">
                        {o.required === false ? te(o.type).replace(/^需/, '') : te(o.type)}
                      </span>
                      {o.required === false && <span className="req__flag">{t('notRequired')}</span>}
                      {o.note ? <span className="req__note"> — {td(o.note)}</span> : null}
                    </li>
                  ))}
                </ul>
              ) : null
            }
          />
        </dl>
      </Section>

      <Section title={t('timeline')}>
        <dl className="kvs">
          <KV k={t('mechanism')} v={te(tl.mechanism)} />
          <KV
            k={t('quota')}
            v={
              tl.quota != null
                ? `${tl.quota.toLocaleString()}${tl.quota_note ? ` · ${td(tl.quota_note)}` : ''}`
                : td(tl.quota_note ?? '')
            }
          />
          <KV
            k={t('windows')}
            v={
              (tl.windows ?? []).length > 0 ? (
                <ul className="ul">
                  {tl.windows!.map((w, i) => (
                    <li key={i}>
                      {w.year} · {te(w.status)}
                      {w.note ? ` — ${td(w.note)}` : ''}
                    </li>
                  ))}
                </ul>
              ) : null
            }
          />
          <KV
            k={t('fee')}
            v={
              (tl.fees ?? []).length > 0 ? (
                <ul className="ul">
                  {tl.fees!.map((f, i) => (
                    <li key={i}>
                      {td(f.item)} — {money(f.amount, td)}
                      {f.amount?.note ? ` · ${td(f.amount.note)}` : ''}
                      {f.note ? ` · ${td(f.note)}` : ''}
                    </li>
                  ))}
                </ul>
              ) : null
            }
          />
          <KV k={t('processingTime')} v={td(tl.processing_time)} />
        </dl>
      </Section>

      {rec.documents?.length > 0 && (
        <Section title={t('documents')}>
          <ul className="ul ul--cards">
            {rec.documents.map((d, i) => (
              <li key={i}>
                <strong>{td(d.name)}</strong>
                {d.required === false && <span className="muted">（{t('notRequired')}）</span>}
                {d.note && <div className="muted">{td(d.note)}</div>}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {rec.steps?.length > 0 && (
        <Section title={t('steps')}>
          <ol className="steps">
            {rec.steps.map((s) => (
              <li key={s.step_no}>
                <h3>
                  {s.step_no}. {td(s.title)}
                </h3>
                {s.description && <p>{td(s.description)}</p>}
                {s.duration && <p className="muted">{td(s.duration)}</p>}
                {s.official_link && (
                  <a href={s.official_link} target="_blank" rel="noreferrer">
                    {t('openLink')} ↗
                  </a>
                )}
              </li>
            ))}
          </ol>
        </Section>
      )}

      {wc && (
        <Section title={t('workConditions')}>
          <dl className="kvs">
            <KV
              k={t('maxStay')}
              v={wc.max_stay_months != null ? `${wc.max_stay_months} ${t('monthsUnit')}` : null}
            />
            <KV
              k={t('sameEmployer')}
              v={
                wc.max_same_employer_months === 0
                  ? t('notRequired')
                  : wc.max_same_employer_months != null
                    ? `${wc.max_same_employer_months} ${t('monthsUnit')}`
                    : null
              }
            />
            <KV
              k={t('renewable')}
              v={
                wc.renewable == null
                  ? null
                  : wc.renewable
                    ? `${t('required')} — ${td(wc.renewal_condition ?? '')}`
                    : td(wc.renewal_condition ?? t('notRequired'))
              }
            />
            <KV
              k={t('restricted')}
              v={
                (wc.restricted_occupations ?? []).length > 0 ? (
                  <ul className="ul">
                    {wc.restricted_occupations!.map((x, i) => (
                      <li key={i}>{td(x)}</li>
                    ))}
                  </ul>
                ) : null
              }
            />
            <KV k="" v={wc.note ? td(wc.note) : null} />
          </dl>
        </Section>
      )}

      {(rec.risks ?? []).length > 0 && (
        <Section title={t('risks')}>
          <ul className="risks">
            {rec.risks!.map((r, i) => (
              <li key={i} className={`risk risk--${r.level}`}>
                <span className="risk__lv">{te(r.level)}</span>
                <span>{td(r.description)}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title={t('sources')}>
        {/* 先给一行汇总：读者最想知道「有几条官方主源」，而不是逐条数 */}
        <p className="srcsum">
          <span className="srcsum__item">
            {t('sourceCount')} <strong>{(rec.sources ?? []).length}</strong>
          </span>
          <span className="srcsum__item srcsum__item--p">
            {t('sourcePrimaryCount')}{' '}
            <strong>{(rec.sources ?? []).filter((s) => s.type === 'primary').length}</strong>
          </span>
          {(rec.sources ?? []).some((s) => s.type !== 'primary') && (
            <span className="srcsum__item">
              {t('sourceSecondaryCount')}{' '}
              <strong>{(rec.sources ?? []).filter((s) => s.type !== 'primary').length}</strong>
            </span>
          )}
        </p>

        <ul className="ul ul--cards ul--src">
          {(rec.sources ?? []).map((s, i) => (
            <li key={i}>
              <span className={s.type === 'primary' ? 'srcdot srcdot--p' : 'srcdot'}>
                {te(s.type)}
              </span>
              <a href={s.url} target="_blank" rel="noreferrer">
                {td(s.name)}
              </a>
              {/* 域名单独成段：来源可信不可信，先看它落在哪个站 */}
              <code className="srcurl" title={s.url}>
                {hostOf(s.url)}
              </code>
              {s.last_verified && (
                <span className="muted">
                  {' '}
                  · {t('lastVerified')} {s.last_verified}
                </span>
              )}
            </li>
          ))}
        </ul>
        <p className="muted detail__verify">
          {t('lastVerified')}：{rec.last_verified ?? '—'} · {t('verifiedBy')}：
          {rec.verified_by ?? '—'}
        </p>
      </Section>
    </article>
  );
}
