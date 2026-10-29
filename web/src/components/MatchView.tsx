// src/components/MatchView.tsx
// 智能匹配页：左边填条件，右边出排序结果。
// 分数的计算在 lib/match.ts（纯函数，可单测）；这里只负责表单和渲染。
import { useEffect, useMemo, useState } from 'react';
import { useI18n } from '../i18n';
import { loadIndex } from '../lib/data';
import { matchAll, EMPTY_PROFILE, type Profile } from '../lib/match';
import { MATCH_TEXT } from '../i18n/ui';
import { loadJson, saveJson } from '../lib/store';
import { useDocumentTitle } from '../lib/useTitle';
import type { ProgramIndexEntry } from '../types';
import { Card } from './Card';

const KEY_PROFILE = 'opd.profile';

/** 画像落盘：用户刷新不用重填。读的时候和 EMPTY_PROFILE 合并，避免旧版本字段缺失 */
function readProfile(): Profile {
  return { ...EMPTY_PROFILE, ...loadJson<Partial<Profile>>(KEY_PROFILE, {}) };
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="pfield">
      <span className="pfield__label">{label}</span>
      {children}
    </label>
  );
}

export function MatchView({
  savedIds,
  onToggleSave,
}: {
  savedIds: string[];
  onToggleSave: (id: string) => void;
}) {
  const { t, te, lang } = useI18n();
  const [all, setAll] = useState<ProgramIndexEntry[] | null>(null);
  const [pr, setPr] = useState<Profile>(readProfile);

  useDocumentTitle([t('matchTitle'), t('pageTitleSuffix')]);

  useEffect(() => {
    let alive = true;
    loadIndex()
      .then((d) => alive && setAll(d))
      .catch(() => alive && setAll([]));
    return () => {
      alive = false;
    };
  }, []);

  // 每改一项就落盘，不做「保存」按钮——表单短，实时存更省事
  useEffect(() => {
    saveJson(KEY_PROFILE, pr);
  }, [pr]);

  const results = useMemo(() => (all ? matchAll(all, pr) : []), [all, pr]);

  // 分数只对上了条件的有意义；一条条件都没填时全部 0 分，此时不显示排序提示
  const hasAny = useMemo(
    () =>
      pr.status != null ||
      pr.age != null ||
      pr.education != null ||
      pr.budgetCny != null ||
      pr.minStayMonths != null ||
      pr.mustBePaid ||
      pr.preferNoAgency ||
      pr.regions.length > 0,
    [pr],
  );

  const byId = useMemo(() => {
    const m = new Map<string, ProgramIndexEntry>();
    for (const p of all ?? []) m.set(p.id, p);
    return m;
  }, [all]);

  const regions = useMemo(() => {
    const set = new Set((all ?? []).map((p) => p.region));
    return [...set];
  }, [all]);

  /** 把 Reason 数组翻成当前语言的短句，最多给 3 条 */
  const reasonsOf = (id: string) => {
    const r = results.find((x) => x.id === id);
    return (r?.reasons ?? []).map((x) => ({
      kind: x.kind,
      text: (MATCH_TEXT[lang][x.code] ?? x.code).replace('{v}', x.value ?? ''),
    }));
  };

  const bestScore = results.length > 0 ? results[0].score : -1;

  return (
    <div className="match">
      <header className="page__head">
        <h1 className="page__title">{t('matchTitle')}</h1>
        <p className="page__intro">{t('matchIntro')}</p>
      </header>

      <div className="match__grid">
        {/* 左：条件表单 */}
        <form className="profile" onSubmit={(e) => e.preventDefault()}>
          <h2 className="profile__title">{t('profileTitle')}</h2>
          <p className="profile__desc">{t('profileDesc')}</p>

          <Field label={t('profileStatus')}>
            <select
              className="input"
              value={pr.status ?? ''}
              onChange={(e) => setPr({ ...pr, status: e.target.value || null })}
            >
              <option value="">{t('profileAny')}</option>
              <option value="eligible">{te('eligible')}</option>
              <option value="not_eligible">{te('not_eligible')}</option>
              <option value="conditional">{te('conditional')}</option>
            </select>
          </Field>

          <Field label={t('profileAge')}>
            <input
              className="input"
              type="number"
              min={14}
              max={99}
              inputMode="numeric"
              placeholder="20"
              value={pr.age ?? ''}
              onChange={(e) =>
                setPr({ ...pr, age: e.target.value === '' ? null : Number(e.target.value) })
              }
            />
          </Field>

          <Field label={t('profileEdu')}>
            <select
              className="input"
              value={pr.education ?? ''}
              onChange={(e) => setPr({ ...pr, education: e.target.value || null })}
            >
              <option value="">{t('profileAny')}</option>
              <option value="high_school">{te('high_school')}</option>
              <option value="vocational">{te('vocational')}</option>
              <option value="bachelor_in_progress">{te('bachelor_in_progress')}</option>
              <option value="bachelor_completed">{te('bachelor_completed')}</option>
              <option value="master">{te('master')}</option>
            </select>
          </Field>

          <Field label={t('profileBudget')}>
            <input
              className="input"
              type="number"
              min={0}
              step={1000}
              inputMode="numeric"
              placeholder="30000"
              value={pr.budgetCny ?? ''}
              onChange={(e) =>
                setPr({ ...pr, budgetCny: e.target.value === '' ? null : Number(e.target.value) })
              }
            />
          </Field>

          <Field label={t('profileStay')}>
            <select
              className="input"
              value={pr.minStayMonths ?? ''}
              onChange={(e) =>
                setPr({ ...pr, minStayMonths: e.target.value === '' ? null : Number(e.target.value) })
              }
            >
              <option value="">{t('profileAny')}</option>
              {[3, 6, 12, 18, 24].map((n) => (
                <option key={n} value={n}>
                  {n} {t('monthsUnit')}+
                </option>
              ))}
            </select>
          </Field>

          <label className="pcheck">
            <input
              type="checkbox"
              checked={pr.mustBePaid}
              onChange={(e) => setPr({ ...pr, mustBePaid: e.target.checked })}
            />
            {t('profilePaid')}
          </label>

          <label className="pcheck">
            <input
              type="checkbox"
              checked={pr.preferNoAgency}
              onChange={(e) => setPr({ ...pr, preferNoAgency: e.target.checked })}
            />
            {t('profileNoAgency')}
          </label>

          {regions.length > 0 && (
            <fieldset className="chips pfield">
              <legend className="chips__legend">{t('profileRegions')}</legend>
              <div className="chips__row">
                {regions.map((r) => {
                  const on = pr.regions.includes(r);
                  return (
                    <button
                      type="button"
                      key={r}
                      className={on ? 'chip chip--on' : 'chip'}
                      aria-pressed={on}
                      onClick={() =>
                        setPr({
                          ...pr,
                          regions: on ? pr.regions.filter((x) => x !== r) : [...pr.regions, r],
                        })
                      }
                    >
                      {te(r)}
                    </button>
                  );
                })}
              </div>
            </fieldset>
          )}

          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => setPr(EMPTY_PROFILE)}
          >
            {t('profileReset')}
          </button>
          <p className="profile__saved">{t('profileSaved')}</p>
        </form>

        {/* 右：排序结果 */}
        <div className="match__results">
          {!all ? (
            <p className="state">{t('searchHint')}…</p>
          ) : !hasAny ? (
            <p className="state">{t('matchEmpty')}</p>
          ) : (
            <>
              <p className="muted match__hint">{t('matchTopHint')}</p>
              <ul className="grid grid--match">
                {results.map((r) => {
                  const p = byId.get(r.id);
                  if (!p) return null;
                  return (
                    <li key={r.id}>
                      <Card
                        p={p}
                        saved={savedIds.includes(p.id)}
                        onToggleSave={onToggleSave}
                        score={r.score}
                        best={r.score === bestScore && bestScore > 0}
                        reasons={reasonsOf(r.id)}
                      />
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
