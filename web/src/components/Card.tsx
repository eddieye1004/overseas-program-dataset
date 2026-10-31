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

  // 0–99 是「官方没写年龄限制」在 schema 里的占位区间（min/max 不允许 null），
  // 直接显示会被读成一条真实规定，所以按未核实处理。
  // 索引里 age_max 已被 sync-data 统一成 null（99 视作无上限），
  // 所以「未核实」不能再靠 min===0 && max===99 判断——那个组合在索引层不存在，
  // 会导致「官方未公布年龄」的项目被渲染成「0 岁」。改读 age_verified。
  // min=0 同理表示「官方没设下限」（如 de-16e 允许任何年龄在读学生），
  // 不能渲染成「0 岁」。
  const ageKnown = p.age_verified !== false && (p.age_min != null || p.age_max != null);
  const noLower = p.age_min == null || p.age_min === 0;
  const noUpper = p.age_max == null;

  let ageText: string;
  if (!ageKnown) {
    ageText = t('notVerified');
  } else if (noLower && noUpper) {
    ageText = t('noAgeLimit');
  } else if (noLower) {
    ageText = `${p.age_max} ${t('ageUnit')}${t('andUnder')}`;
  } else if (noUpper) {
    ageText = `${p.age_min} ${t('ageUnit')}${t('andOver')}`;
  } else {
    ageText = `${p.age_min}–${p.age_max} ${t('ageUnit')}`;
  }

  const stayText = p.max_stay_months != null ? `${p.max_stay_months} ${t('monthsUnit')}` : t('notVerified');

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

      {reasons && reasons.length > 0 && (
        <ul className="card__reasons">
          {reasons.slice(0, 3).map((r, i) => (
            <li key={i} className={`rsn rsn--${r.kind}`}>
              {r.text}
            </li>
          ))}
        </ul>
      )}

      {/* 4 个字段压成一行：年龄 · 停留 · 来源 · 核实日期。
          原先 dt/dd 三列 + 单独一条 trust 共占 77px，合并后省 45px，
          而且读起来像一句描述而不是表格式罗列。 */}
      <p className="card__factsline">
        <span>{ageText}</span>
        <span>{stayText}</span>
        <span>
          {t('sourceCount')} {p.source_count ?? 0}
          <span className="card__factsline__p"> / {t('primary')} {p.source_primary ?? 0}</span>
        </span>
        {p.last_verified && <span>{p.last_verified}</span>}
      </p>

      <div className="card__tags">
        {p.tags.slice(0, 4).map((tg) => (
          <span className="tag" key={tg}>
            {te(tg)}
          </span>
        ))}
      </div>

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
