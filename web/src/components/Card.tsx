// src/components/Card.tsx
// 列表卡片。只读 index.json 里的轻量字段，不做详情请求。
//
// 结构要点：外层用 <article> 而不是 <a>。卡片里要放「收藏」按钮，
// 而 <a> 里嵌 <button> 在 HTML 里是非法嵌套，点击行为也会互相抢。
// 整卡可点靠 .card__link::after 撑满实现，按钮用 z-index 浮在上层。
import { useI18n } from '../i18n';
import { detailHref } from '../lib/router';
import type { ProgramIndexEntry } from '../types';

const STATUS_CLASS: Record<string, string> = {
  eligible: 'badge badge--ok',
  not_eligible: 'badge badge--no',
  conditional: 'badge badge--maybe',
  unknown: 'badge badge--unk',
};

interface Props {
  p: ProgramIndexEntry;
  saved: boolean;
  onToggleSave: (id: string) => void;
  /** 智能匹配页传入的匹配分，普通列表不传 */
  score?: number;
  best?: boolean;
  /** 卡片底部附几条匹配理由（匹配页用） */
  reasons?: { kind: 'pass' | 'fail' | 'warn'; text: string }[];
}

export function Card({ p, saved, onToggleSave, score, best, reasons }: Props) {
  const { t, td, te, lang } = useI18n();

  // 中文模式显示中文名，英文模式优先 name_en（数据里 11 条全都有）
  const title = lang === 'en' ? p.name_en || p.name : p.name;
  const sub = lang === 'en' ? p.name : p.name_en;

  const ageText =
    p.age_min != null && p.age_max != null
      ? `${p.age_min}–${p.age_max}`
      : p.age_min != null
        ? `${p.age_min}+`
        : '—';

  const stayText = p.max_stay_months != null ? `${p.max_stay_months} ${t('monthsUnit')}` : '—';

  return (
    <article
      className="card"
      data-status={p.status}
      data-risk={(p.risk_levels ?? []).join(' ')}
    >
      <div className="card__top">
        <span className="card__country">
          {te(p.region)} · {td(p.country)}
        </span>
        <span className="card__topright">
          {typeof score === 'number' && (
            <span className={best ? 'score score--best' : 'score'}>{score}</span>
          )}
          <span className={STATUS_CLASS[p.status] ?? 'badge'}>{te(p.status)}</span>
        </span>
      </div>

      <h3 className="card__title">
        <a className="card__link" href={detailHref(p.id)}>
          {title}
        </a>
      </h3>
      <p className="card__sub">{sub}</p>
      <p className="card__summary">{td(p.summary)}</p>

      <dl className="card__facts">
        <div>
          <dt>{t('age')}</dt>
          <dd>{ageText}</dd>
        </div>
        <div>
          <dt>{t('stay')}</dt>
          <dd>{stayText}</dd>
        </div>
        <div>
          <dt>{t('lang')}</dt>
          <dd>{p.language_required ? t('required') : t('notRequired')}</dd>
        </div>
      </dl>

      {reasons && reasons.length > 0 && (
        <ul className="card__reasons">
          {reasons.slice(0, 3).map((r, i) => (
            <li key={i} className={`rsn rsn--${r.kind}`}>
              {r.text}
            </li>
          ))}
        </ul>
      )}

      <div className="card__tags">
        {p.tags.slice(0, 4).map((tg) => (
          <span className="tag" key={tg}>
            {te(tg)}
          </span>
        ))}
      </div>

      {/* 可信度条：几条来源、其中几条官方、最后核于哪天。卡片上就该看得到，
          而不是点进详情才知道这条数据靠不靠得住。 */}
      <p className="card__trust">
        <span className="card__trust__src" title={t('sourcePrimaryCount')}>
          {t('sourceCount')} {p.source_count ?? 0}
          <span className="card__trust__p"> · {t('primary')} {p.source_primary ?? 0}</span>
        </span>
        {p.last_verified && (
          <span className="card__trust__date">
            {t('verifiedOn')} {p.last_verified}
          </span>
        )}
      </p>

      <button
        type="button"
        className={saved ? 'card__save card__save--on' : 'card__save'}
        aria-pressed={saved}
        aria-label={saved ? t('unsave') : t('save')}
        title={saved ? t('unsave') : t('save')}
        onClick={() => onToggleSave(p.id)}
      >
        {saved ? '★' : '☆'}
      </button>
    </article>
  );
}
