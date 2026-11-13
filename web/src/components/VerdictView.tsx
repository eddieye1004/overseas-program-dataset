// src/components/VerdictView.tsx
// 资格判定页：左边填五项条件，右边按三态分组列出 41 个项目。
//
// 与「智能匹配」页的分工（两页都留着，不是重复）：
//   匹配页回答「哪个更值得先看」，给 0–100 分，允许把不确定当半分。
//   判定页回答「我到底能不能申」，只有三态 + 差多少，不设分值——
//   把「不可判」折成一个分数会让人误以为那是「差不多能申」。
//
// 判定逻辑全在 lib/verdict.ts（纯函数），这里只负责表单、分组与文案。
import { useEffect, useMemo, useState } from 'react';
import { useI18n } from '../i18n';
import { VERDICT_TEXT } from '../i18n/ui';
import { loadFlags, loadIndex } from '../lib/data';
import { loadJson, saveJson } from '../lib/store';
import { detailHref } from '../lib/router';
import { useDocumentTitle } from '../lib/useTitle';
import {
  EMPTY_VERDICT_PROFILE,
  RULES_VERSION,
  STATE_ORDER,
  countByState,
  judgeAll,
  type DimVerdict,
  type MatchFlagsFile,
  type VerdictProfile,
  type VerdictState,
} from '../lib/verdict';
import type { ProgramIndexEntry } from '../types';

const KEY_PROFILE = 'opd.verdict';

/** 画像写入 localStorage：刷新后不用重填，与匹配页同样不做「保存」按钮 */
function readProfile(): VerdictProfile {
  return { ...EMPTY_VERDICT_PROFILE, ...loadJson<Partial<VerdictProfile>>(KEY_PROFILE, {}) };
}

const EDU_OPTIONS: VerdictProfile['education'][] = [
  'high_school',
  'vocational',
  'bachelor_in_progress',
  'bachelor_completed',
  'master',
];

const PASSPORT_OPTIONS: VerdictProfile['passport'][] = [
  'mainland_china',
  'hong_kong_china',
  'taiwan_china',
];

const DIM_LABEL: Record<DimVerdict['dim'], Parameters<ReturnType<typeof useI18n>['t']>[0]> = {
  passport: 'verdictDimPassport',
  age: 'verdictDimAge',
  education: 'verdictDimEdu',
  language: 'verdictDimLang',
  funds: 'verdictDimFunds',
  precondition: 'verdictDimPrecondition',
};

/** 状态的色调 class：与既有 badge 体系一致，不另造一套颜色 */
const STATE_TONE: Record<VerdictState, string> = {
  can: 'ok',
  gap: 'warn',
  unknown: 'mute',
  cannot: 'no',
};

export function VerdictView({
  watchedIds,
  onToggleWatch,
}: {
  watchedIds: string[];
  onToggleWatch: (id: string) => void;
}) {
  const { t, te, lang } = useI18n();
  const [index, setIndex] = useState<ProgramIndexEntry[] | null>(null);
  const [flags, setFlags] = useState<MatchFlagsFile | null>(null);
  const [profile, setProfile] = useState<VerdictProfile>(readProfile);
  /** 只有点过「开始判定」才出结果：边打字边刷新四十条结果会晃得没法读 */
  const [submitted, setSubmitted] = useState(false);

  useDocumentTitle([t('verdictTitle'), t('pageTitleSuffix')]);

  useEffect(() => {
    let alive = true;
    Promise.all([loadIndex(), loadFlags()])
      .then(([idx, f]) => {
        if (!alive) return;
        setIndex(idx);
        setFlags(f);
      })
      .catch(() => {
        if (!alive) return;
        setIndex([]);
        setFlags(null);
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    saveJson(KEY_PROFILE, profile);
  }, [profile]);

  const byId = useMemo(() => {
    const m = new Map<string, ProgramIndexEntry>();
    for (const p of index ?? []) m.set(p.id, p);
    return m;
  }, [index]);

  const rows = useMemo(() => {
    if (!flags || !index || !submitted) return null;
    const ids = index.map((p) => p.id);
    const verdicts = judgeAll(flags, ids, profile);
    const byState: Record<VerdictState, typeof verdicts> = {
      can: [],
      gap: [],
      unknown: [],
      cannot: [],
    };
    for (const v of verdicts) byState[v.verdict.state].push(v);
    return byState;
  }, [flags, index, profile, submitted]);

  const counts = useMemo(() => (rows ? countByState(Object.values(rows).flat()) : null), [rows]);

  /** 把一条维结论翻成当前语言的句子：模板里 {need}/{have} 用实际值填 */
  const dimText = (d: DimVerdict): string => {
    const tpl = VERDICT_TEXT[lang][d.code] ?? VERDICT_TEXT.zh[d.code] ?? d.code;
    return tpl.replace('{need}', d.need ?? '').replace('{have}', d.have ?? '');
  };

  const sectionCopy: Record<VerdictState, { title: string; hint: string }> = {
    can: { title: t('verdictSecCan'), hint: t('verdictSecCanHint') },
    gap: { title: t('verdictSecGap'), hint: t('verdictSecGapHint') },
    unknown: { title: t('verdictSecUnknown'), hint: t('verdictSecUnknownHint') },
    cannot: { title: t('verdictSecCannot'), hint: t('verdictSecCannotHint') },
  };

  const loading = index === null || flags === null;

  return (
    <div className="verdict">
      <header className="page__head">
        <h1 className="page__title">{t('verdictTitle')}</h1>
        <p className="page__intro">{t('verdictIntro')}</p>
      </header>

      <div className="verdict__grid">
        {/* 左：五项条件 */}
        <form
          className="profile"
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted(true);
            // 手机上结果在表单下方，判定完直接滚过去，否则点了像没反应
            if (window.matchMedia('(max-width: 900px)').matches) {
              document
                .getElementById('verdict-results')
                ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
          }}
        >
          <h2 className="profile__title">{t('verdictProfileTitle')}</h2>
          <p className="profile__desc">{t('verdictProfileDesc')}</p>

          <label className="pfield">
            <span className="pfield__label">{t('verdictPassport')}</span>
            <select
              className="input"
              value={profile.passport}
              onChange={(e) =>
                setProfile({ ...profile, passport: e.target.value as VerdictProfile['passport'] })
              }
            >
              {PASSPORT_OPTIONS.map((v) => (
                <option key={v} value={v}>
                  {te(v)}
                </option>
              ))}
            </select>
          </label>

          <label className="pfield">
            <span className="pfield__label">{t('verdictAge')}</span>
            <input
              className="input"
              type="number"
              min={14}
              max={99}
              inputMode="numeric"
              value={profile.age}
              onChange={(e) =>
                setProfile({ ...profile, age: e.target.value === '' ? 0 : Number(e.target.value) })
              }
            />
          </label>

          <label className="pfield">
            <span className="pfield__label">{t('verdictEdu')}</span>
            <select
              className="input"
              value={profile.education}
              onChange={(e) =>
                setProfile({
                  ...profile,
                  education: e.target.value as VerdictProfile['education'],
                })
              }
            >
              {EDU_OPTIONS.map((v) => (
                <option key={v} value={v}>
                  {te(v)}
                </option>
              ))}
            </select>
          </label>

          <label className="pfield">
            <span className="pfield__label">{t('verdictIelts')}</span>
            <select
              className="input"
              value={profile.ielts ?? ''}
              onChange={(e) =>
                setProfile({
                  ...profile,
                  ielts: e.target.value === '' ? null : Number(e.target.value),
                })
              }
            >
              {/* 只有这两类值：没考过，或具体分数。0 分不是一种真实情况 */}
              <option value="">{t('verdictIeltsNone')}</option>
              {[4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9].map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <span className="pfield__hint">{t('verdictIeltsHint')}</span>
          </label>

          <label className="pfield">
            <span className="pfield__label">{t('verdictBudget')}</span>
            <input
              className="input"
              type="number"
              min={0}
              step={1000}
              inputMode="numeric"
              value={profile.budget_cny}
              onChange={(e) =>
                setProfile({
                  ...profile,
                  budget_cny: e.target.value === '' ? 0 : Number(e.target.value),
                })
              }
            />
          </label>

          <button type="submit" className="btn btn--primary">
            {t('verdictSubmit')}
          </button>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => {
              setProfile(EMPTY_VERDICT_PROFILE);
              setSubmitted(false);
            }}
          >
            {t('verdictReset')}
          </button>
          <p className="profile__saved">{t('verdictSaved')}</p>
          <p className="profile__saved">{t('verdictSubmitHint')}</p>
        </form>

        {/* 右：三态分组结果 */}
        <div className="verdict__results" id="verdict-results">
          {loading ? (
            <p className="state">{t('searchHint')}…</p>
          ) : !submitted || !rows || !counts ? (
            <p className="state">{t('verdictEmpty')}</p>
          ) : (
            <>
              <ul className="statbar">
                {STATE_ORDER.map((s) => (
                  <li key={s} className={`stat stat--${STATE_TONE[s]}`}>
                    <span className="stat__num">{counts[s]}</span>
                    <span className="stat__label">
                      {s === 'can'
                        ? t('verdictCountCan')
                        : s === 'gap'
                          ? t('verdictCountGap')
                          : s === 'unknown'
                            ? t('verdictCountUnknown')
                            : t('verdictCountCannot')}
                    </span>
                  </li>
                ))}
              </ul>

              {STATE_ORDER.map((state) => {
                const list = rows[state];
                if (list.length === 0) return null;
                return (
                  <section key={state} className={`vsec vsec--${STATE_TONE[state]}`}>
                    <h2 className="vsec__title">
                      {sectionCopy[state].title}
                      <span className="vsec__hint">{sectionCopy[state].hint}</span>
                    </h2>
                    <ul className="vlist">
                      {list.map(({ id, verdict }) => {
                        const p = byId.get(id);
                        if (!p) return null;
                        // 只列「不是 pass 也不是 na」的维：na 在这条上不构成门槛，
                        // 全列出来会让「能申」的项目也拖着一串「不要求」的赘述
                        const shown = verdict.dims.filter(
                          (d) => d.kind !== 'pass' && d.kind !== 'na',
                        );
                        const passes = verdict.dims.filter((d) => d.kind === 'pass');
                        const watched = watchedIds.includes(id);
                        return (
                          <li key={id} className={`vrow vrow--${STATE_TONE[state]}`}>
                            <div className="vrow__main">
                              <a className="vrow__title" href={detailHref(id)}>
                                {lang === 'en' ? p.name_en || p.name : p.name}
                              </a>
                              <span className="vrow__meta">
                                {te(p.region)} · {te(p.country)}
                              </span>

                              {shown.length > 0 && (
                                <ul className="vdims">
                                  {shown.map((d, i) => (
                                    <li key={i} className={`vdim vdim--${d.kind}`}>
                                      <span className="vdim__label">{t(DIM_LABEL[d.dim])}</span>
                                      <span className="vdim__text">{dimText(d)}</span>
                                      {d.inferred && (
                                        <span className="vdim__tag">{t('verdictInferred')}</span>
                                      )}
                                    </li>
                                  ))}
                                </ul>
                              )}

                              {/* 能申的项目也要给人「凭什么」的落点：列出通过的维，
                                  否则一整条只会显示项目名，看着像没算 */}
                              {verdict.state === 'can' && passes.length > 0 && (
                                <p className="vrow__passes">
                                  {passes.map((d) => t(DIM_LABEL[d.dim])).join(' · ')}
                                </p>
                              )}
                            </div>

                            <div className="vrow__side">
                              <a className="btn btn--ghost btn--sm" href={detailHref(id)}>
                                {t('verdictDetailLink')}
                              </a>
                              <button
                                type="button"
                                className={watched ? 'btn btn--ghost btn--sm btn--on' : 'btn btn--ghost btn--sm'}
                                aria-pressed={watched}
                                onClick={() => onToggleWatch(id)}
                              >
                                {watched ? t('watchAdded') : t('watchAdd')}
                              </button>
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  </section>
                );
              })}

              <p className="verdict__foot">
                {t('verdictDisclaimer')}
                <span className="verdict__version">
                  {t('verdictRulesVersion')} v{RULES_VERSION}
                  {flags && flags.rules_version !== RULES_VERSION
                    ? ` · 数据为 v${flags.rules_version}`
                    : ''}
                </span>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
