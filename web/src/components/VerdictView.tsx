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
import {
  EXTRA_FIELDS,
  MAX_VISIBLE_EXTRA,
  primaryExtraFields,
  readersOf,
  secondaryExtraFields,
  visibleExtraFields,
  type ExtraField,
  type GateInput,
  type GateProgram,
} from '../lib/profileFields';
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
  const { t, td, te, lang } = useI18n();
  const [index, setIndex] = useState<ProgramIndexEntry[] | null>(null);
  const [flags, setFlags] = useState<MatchFlagsFile | null>(null);
  const [profile, setProfile] = useState<VerdictProfile>(readProfile);
  /** 只有点过「开始判定」才出结果：边打字边刷新四十条结果会晃得没法读 */
  const [submitted, setSubmitted] = useState(false);
  /** 「继续细化」是否展开（默认收起，见 profileFields.ts 的 MAX_VISIBLE_EXTRA） */
  const [extraOpen, setExtraOpen] = useState(false);

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

  /**
   * 现居地下拉的国家清单：从 index 里实际出现的项目国别生成，去重后按中文名排序。
   *
   * 不从别处引一份手写国家表：项目覆盖到哪国，选项就有哪国，永远不会出现
   * 「下拉里有这个国家但库里没有项目」或反之。全球项目（country_code=GL）不进去选，
   * 它不是一个人能「住在」的地方。
   */
  const countryOptions = useMemo(() => {
    const m = new Map<string, string>();
    for (const p of index ?? []) {
      const code = p.country_code;
      if (!code || code === 'GL' || m.has(code)) continue;
      m.set(code, p.country);
    }
    return [...m.entries()]
      .map(([code, name]) => ({ code, name }))
      .sort((a, b) => a.name.localeCompare(b.name, 'zh-Hans-CN'));
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

  /**
   * 门的输入：每条项目「读哪些补充字段」+「**在补充字段全空时**它是否判不出结论」。
   *
   * 为什么用「全空」的基线而不是当前填好的画像：
   * 否则门会自己咬自己——用户答了「无家属」，那条项目立刻能判，门就关掉这个
   * 字段，值被清空，项目又变回不可判，字段再打开……每次渲染翻一次。
   * 拿基线算，门只取决于六项主字段，答完一项不会让问过的项消失。
   *
   * 这也正好符合工单的说法：「无条件显示」问的是「这些信息能不能改变你的
   * 结论」，那是基线性质，不是「现在还差什么」。
   *
   * 判定用与结果区同一个 judgeAll，不另写一套：否则会出现「门说这条项目
   * 需要家属信息，结果区却说它已经能申」这种自相矛盾。
   */
  const gatePrograms = useMemo<GateProgram[]>(() => {
    if (!flags || !index) return [];
    // 基线画像：主字段照用，七个补充字段一律 null
    const baseline: VerdictProfile = { ...profile };
    for (const f of EXTRA_FIELDS) {
      (baseline as unknown as Record<string, unknown>)[f] = null;
    }
    const verdicts = judgeAll(flags, index.map((p) => p.id), baseline);
    const undecided = new Set(
      verdicts.filter((v) => v.verdict.state === 'unknown').map((v) => v.id),
    );
    return Object.entries(flags.programs).map(([id, f]) => ({
      id,
      reads: readersOf(f),
      undecided: undecided.has(id),
    }));
  }, [flags, index, profile]);

  const gateInput = useMemo<GateInput>(
    () => ({ profile, programs: gatePrograms }),
    [profile, gatePrograms],
  );

  /** 门开着的字段。为空时整块「再补几条」都不渲染——这才是「不许拉长」。 */
  const extraVisible = useMemo(
    () => (gatePrograms.length ? visibleExtraFields(gateInput) : []),
    [gateInput, gatePrograms.length],
  );
  const extraPrimary = useMemo(
    () => (extraVisible.length ? primaryExtraFields(gateInput) : []),
    [gateInput, extraVisible.length],
  );
  const extraSecondary = useMemo(
    () => (extraOpen ? secondaryExtraFields(gateInput) : []),
    [gateInput, extraOpen],
  );

  /**
   * 一个补充字段的控件。
   *
   * 每条都用「不填」作为默认项并显式写出「不确定」——这与六项主字段同一口径：
   * 缺省是未知，不是「没有」。把 dependents 默认成「没有家属」会替用户承认
   * 一个他没说过的事实，判定立刻偏乐观。
   */
  const renderExtraField = (field: ExtraField) => {
    const set = (patch: Partial<VerdictProfile>) => setProfile({ ...profile, ...patch });

    if (field === 'enrollment_status') {
      return (
        <label className="pfield" key={field}>
          <span className="pfield__label">{t('verdictEnrollment')}</span>
          <select
            className="input"
            value={profile.enrollment_status ?? ''}
            onChange={(e) =>
              set({
                enrollment_status:
                  (e.target.value || null) as VerdictProfile['enrollment_status'],
              })
            }
          >
            <option value="">{t('verdictEnrollmentUnknown')}</option>
            <option value="enrolled">{t('optEnrolled')}</option>
            <option value="completed">{t('optCompleted')}</option>
          </select>
        </label>
      );
    }

    if (field === 'prior_participation') {
      return (
        <label className="pfield" key={field}>
          <span className="pfield__label">{t('verdictParticipation')}</span>
          <select
            className="input"
            value={profile.prior_participation ?? ''}
            onChange={(e) =>
              set({
                prior_participation:
                  (e.target.value || null) as VerdictProfile['prior_participation'],
              })
            }
          >
            <option value="">{t('verdictParticipationUnknown')}</option>
            <option value="none">{t('optPartNo')}</option>
            <option value="used">{t('optPartYes')}</option>
          </select>
        </label>
      );
    }

    if (field === 'prior_same_category_visa') {
      return (
        <label className="pfield" key={field}>
          <span className="pfield__label">{t('verdictPriorVisa')}</span>
          <select
            className="input"
            value={profile.prior_same_category_visa ?? ''}
            onChange={(e) =>
              set({
                prior_same_category_visa:
                  (e.target.value || null) as VerdictProfile['prior_same_category_visa'],
              })
            }
          >
            <option value="">{t('verdictPriorVisaUnknown')}</option>
            <option value="none">{t('optVisaNo')}</option>
            <option value="used">{t('optVisaYes')}</option>
          </select>
        </label>
      );
    }

    if (field === 'dependents') {
      return (
        <label className="pfield" key={field}>
          <span className="pfield__label">{t('verdictDependents')}</span>
          <select
            className="input"
            value={profile.dependents ?? ''}
            onChange={(e) =>
              set({ dependents: (e.target.value || null) as VerdictProfile['dependents'] })
            }
          >
            <option value="">{t('verdictDependentsUnknown')}</option>
            <option value="none">{t('optDepNone')}</option>
            <option value="children">{t('optDepChildren')}</option>
            <option value="partner">{t('optDepPartner')}</option>
            <option value="other">{t('optDepOther')}</option>
          </select>
        </label>
      );
    }

    // 三个数字字段：空串即「未知」，不写 0。
    // 0 与「没填」在这里是两件不同的事实（J-1 Trainee 的经验年限就是靠这个
    // 区分判 fail 还是判 silent），所以绝不用 0 当占位。
    const numField = (
      label: Parameters<typeof t>[0],
      hint: Parameters<typeof t>[0],
      value: number | null | undefined,
      min: number,
      step: number,
      apply: (v: number | null) => Partial<VerdictProfile>,
    ) => (
      <label className="pfield" key={field}>
        <span className="pfield__label">{t(label)}</span>
        <input
          className="input"
          type="number"
          min={min}
          step={step}
          inputMode="numeric"
          placeholder={t(hint)}
          value={value ?? ''}
          onChange={(e) => set(apply(e.target.value === '' ? null : Number(e.target.value)))}
        />
      </label>
    );

    if (field === 'study_months') {
      return numField('verdictStudyMonths', 'verdictStudyMonthsUnknown', profile.study_months, 0, 1,
        (v) => ({ study_months: v }));
    }
    if (field === 'months_since_graduation') {
      return numField('verdictGradMonths', 'verdictGradMonthsUnknown',
        profile.months_since_graduation, 0, 1, (v) => ({ months_since_graduation: v }));
    }
    return numField('verdictWorkYears', 'verdictWorkYearsUnknown',
      profile.work_experience_years, 0, 1, (v) => ({ work_experience_years: v }));
  };

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

          {/*
            现居地（P1d）。与护照分开问：护照决定「你是谁」，这里决定「你人在哪」。
            有几条项目要求递交时人必须在该国境内（英国的毕业生签证就是），
            这条要求判的是后者——拿中国护照在英国读完书的人，护照条件与在地条件
            是两项，只填护照会让那条要求永远「不可判」。

            选项从 index 里已出现的国家生成，不另写一份国家表：项目覆盖到哪国，
            这里就能选到哪国，多一份手写清单只会和 data/programs 漂移。
            「不确定 / 不填」是默认项 → 引擎判 silent（不可判），绝不默认通过。
          */}
          <label className="pfield">
            <span className="pfield__label">{t('verdictLocation')}</span>
            <select
              className="input"
              value={profile.current_location ?? ''}
              onChange={(e) =>
                setProfile({ ...profile, current_location: e.target.value || null })
              }
            >
              <option value="">{t('verdictLocationUnknown')}</option>
              {countryOptions.map((c) => (
                <option key={c.code} value={c.code}>
                  {td(c.name)}
                </option>
              ))}
            </select>
            <span className="pfield__hint">{t('verdictLocationHint')}</span>
          </label>

          {/*
            补充条件（本单）。只在「有项目会因为它而不可判」时出现，
            默认最多露 MAX_VISIBLE_EXTRA 项，其余收在「继续细化」里。

            整块为空时**什么都不渲染**——没有一条项目读这些字段的人
            （理论上不会有，但数据变化时可能）不该看到一个空标题。
          */}
          {extraPrimary.length > 0 && (
            <fieldset className="pgate">
              <legend className="pgate__title">{t('verdictExtraTitle')}</legend>
              <p className="pgate__desc">{t('verdictExtraDesc')}</p>
              {extraPrimary.map(renderExtraField)}
              {extraSecondary.map(renderExtraField)}
              {extraVisible.length > MAX_VISIBLE_EXTRA && (
                <button
                  type="button"
                  className="btn btn--ghost btn--sm pgate__more"
                  aria-expanded={extraOpen}
                  onClick={() => setExtraOpen(!extraOpen)}
                >
                  {extraOpen ? t('verdictExtraLess') : t('verdictExtraMore')}
                </button>
              )}
              <p className="pgate__hint">{t('verdictExtraHint')}</p>
            </fieldset>
          )}

          <button type="submit" className="btn btn--primary">
            {t('verdictSubmit')}
          </button>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => {
              setProfile(EMPTY_VERDICT_PROFILE);
              setSubmitted(false);
              setExtraOpen(false);
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
