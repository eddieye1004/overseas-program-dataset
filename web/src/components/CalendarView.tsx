// src/components/CalendarView.tsx
// 窗口日历：把 33 个项目的开放窗口放到一条时间轴上。
//
// 这一页最重要的一条纪律：**三档确定性永远分开显示，不混排**。
//   confirmed 官方已公布 → 可以据此安排
//   inferred  按往年规律推的 → 只能当参考
//   unknown   无从判断 → 只说「盯什么」，不给日期
// 把推断日期和官方日期并排放在一张表里，读者分不出来，雷达就会把人叫错时间。
// 所以这里不是「一张按日期排序的大表」，而是三块独立的分区。
import { useEffect, useMemo, useState } from 'react';
import { useI18n } from '../i18n';
import { loadIndex } from '../lib/data';
import { detailHref, navigate } from '../lib/router';
import type { ProgramIndexEntry } from '../types';

type IndexEntry = ProgramIndexEntry;

const DAY = 86400000;

/** 距今天的天数（负=已过去）。与 track.py 的 days_left 同口径：按天粒度。 */
function daysFrom(iso: string | null | undefined, now: number): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  return Math.round((t - now) / DAY);
}

function Section({
  title,
  hint,
  children,
  tone,
}: {
  title: string;
  hint: string;
  children: React.ReactNode;
  tone: 'ok' | 'warn' | 'mute';
}) {
  return (
    <section className={`cal__sec cal__sec--${tone}`}>
      <h2 className="cal__secTitle">
        {title}
        <span className="cal__secHint">{hint}</span>
      </h2>
      {children}
    </section>
  );
}

function Row({ p, now }: { p: IndexEntry; now: number }) {
  const { t, td } = useI18n();
  const open = daysFrom(p.window_open, now);
  const close = daysFrom(p.window_close, now);

  // 提醒日 = 开放日 − 建议提前天数。这是全站唯一的算法，
  // 与 scripts/build_calendar.py 的 remind_on 一一对应。
  const remind =
    open != null && p.lead_time_days != null ? open - p.lead_time_days : null;

  const statusText =
    p.schedule_status === 'open'
      ? t('calStatusOpen')
      : p.schedule_status === 'upcoming'
        ? t('calStatusUpcoming')
        : p.schedule_status === 'closed'
          ? t('calStatusClosed')
          : p.schedule_status === 'always_open'
            ? t('calStatusAlways')
            : t('calStatusUnknown');

  return (
    <li className="cal__row">
      <button type="button" className="cal__name" onClick={() => navigate(`/p/${p.id}`)}>
        {td(p.name)}
        <span className="cal__country">{td(p.country)}</span>
      </button>
      <span className={`cal__status cal__status--${p.schedule_status ?? 'unknown'}`}>{statusText}</span>
      <span className="cal__dates">
        {p.window_open ? (
          <>
            <time dateTime={p.window_open}>{p.window_open}</time>
            {p.window_close ? (
              <>
                {' → '}
                <time dateTime={p.window_close}>{p.window_close}</time>
              </>
            ) : null}
          </>
        ) : (
          <span className="cal__nodate">{t('calNoDate')}</span>
        )}
      </span>
      <span className="cal__lead">
        {p.lead_time_days != null ? `${p.lead_time_days} ${t('calDays')}` : '—'}
      </span>
      <span className="cal__remind">
        {remind != null ? (
          p.schedule_status === 'closed' ? (
            // 已关闭的窗口不要再喊「现在就该准备」——那句话与状态自相矛盾，
            // 读者会以为还有活要干。这里只陈述事实：这一轮已经过了。
            <span className="cal__passed">{t('calPassed')}</span>
          ) : remind <= 0 ? (
            <strong className="cal__due">{t('calShouldPrepare')}</strong>
          ) : (
            `${t('calInDays')} ${remind} ${t('calDays')}`
          )
        ) : (
          '—'
        )}
      </span>
      {close != null && close >= 0 && close <= 14 ? (
        <span className="cal__soon">{t('calClosingSoon')}</span>
      ) : null}
    </li>
  );
}

export function CalendarView({ index }: { index?: IndexEntry[] }) {
  const { t } = useI18n();
  const now = useMemo(() => Date.now(), []);
  const [rows, setRows] = useState<IndexEntry[] | null>(index ?? null);

  // 自己取索引：这一页不依赖列表页是否已经加载过，
  // 直接分享 #/calendar 链接进来也要能看（与详情页同样的理由）。
  useEffect(() => {
    if (index || rows) return;
    let alive = true;
    loadIndex()
      .then((d) => alive && setRows(d))
      .catch(() => alive && setRows([]));
    return () => {
      alive = false;
    };
  }, [index, rows]);

  const data = index ?? rows ?? [];

  const groups = useMemo(() => {
    const confirmed = data.filter((p) => p.date_confidence === 'confirmed');
    const inferred = data.filter((p) => p.date_confidence === 'inferred');
    const unknown = data.filter(
      (p) => p.date_confidence === 'unknown' || p.date_confidence == null,
    );
    // confirmed 内部：窗口还开着或即将开放的先排，要求先看「现在能做什么」
    const rank = (s: string | null) =>
      s === 'open' ? 0 : s === 'upcoming' ? 1 : s === 'closed' ? 2 : 3;
    confirmed.sort((a, b) => rank(a.schedule_status) - rank(b.schedule_status));
    return { confirmed, inferred, unknown };
  }, [data]);

  if (rows === null && !index) {
    return (
      <div className="cal">
        <p className="cal__empty">{t('calNoDate')}</p>
      </div>
    );
  }

  return (
    <div className="cal">
      <header className="cal__head">
        <h1 className="page__title">{t('calTitle')}</h1>
        <p className="cal__lede">{t('calLede')}</p>
      </header>

      <div className="cal__legend" role="note">
        <span className="cal__lg cal__lg--ok">{t('calLegendConfirmed')}</span>
        <span className="cal__lg cal__lg--warn">{t('calLegendInferred')}</span>
        <span className="cal__lg cal__lg--mute">{t('calLegendUnknown')}</span>
      </div>

      <Section
        title={t('calSecConfirmed')}
        hint={t('calSecConfirmedHint')}
        tone="ok"
      >
        {groups.confirmed.length ? (
          <ul className="cal__list">
            {groups.confirmed.map((p) => (
              <Row key={p.id} p={p} now={now} />
            ))}
          </ul>
        ) : (
          <p className="cal__empty">{t('calEmpty')}</p>
        )}
      </Section>

      <Section title={t('calSecInferred')} hint={t('calSecInferredHint')} tone="warn">
        {groups.inferred.length ? (
          <ul className="cal__list">
            {groups.inferred.map((p) => (
              <Row key={p.id} p={p} now={now} />
            ))}
          </ul>
        ) : (
          <p className="cal__empty">{t('calEmpty')}</p>
        )}
      </Section>

      <Section title={t('calSecUnknown')} hint={t('calSecUnknownHint')} tone="mute">
        {groups.unknown.length ? (
          <ul className="cal__list cal__list--mute">
            {groups.unknown.map((p) => (
              <Row key={p.id} p={p} now={now} />
            ))}
          </ul>
        ) : (
          <p className="cal__empty">{t('calEmpty')}</p>
        )}
      </Section>

      <p className="cal__foot">
        {t('calFoot')}{' '}
        <a href={detailHref('nz-china-whv')}>{t('calFootLink')}</a>
      </p>
    </div>
  );
}
