// src/components/Sidebar.tsx
// 左侧固定导航。手机上是顶部横滑条（见 styles.css 的 .sidebar 断点）。
// 计数徽标直接从本地状态算，不需要请求数据，所以侧边栏永远即时。
import type { ReactNode } from 'react';
import { useI18n } from '../i18n';
import { navigate, type Route } from '../lib/router';

export type NavName =
  | 'list'
  | 'match'
  | 'verdict'
  | 'calendar'
  | 'track'
  | 'saved'
  | 'compare'
  | 'about';

interface Item {
  name: NavName;
  path: string;
  labelKey:
    | 'navBrowse'
    | 'navMatch'
    | 'navVerdict'
    | 'navCalendar'
    | 'navTrack'
    | 'navSaved'
    | 'navCompare'
    | 'navData';
  /** 一句话说明这一格是干什么的。新手最常见的困惑是「六个名字看不出区别」。 */
  hintKey:
    | 'navBrowseHint'
    | 'navMatchHint'
    | 'navVerdictHint'
    | 'navCalendarHint'
    | 'navTrackHint'
    | 'navSavedHint'
    | 'navCompareHint'
    | 'navDataHint';
  icon: string;
  count?: number;
}

export function Sidebar({
  route,
  savedCount,
  trackCount,
  compareCount,
}: {
  route: Route;
  savedCount: number;
  trackCount: number;
  compareCount: number;
}) {
  const { t } = useI18n();

  // 当前高亮：详情页归到「项目库」这一项，用户才知道自己在哪一层
  const active: NavName = route.name === 'detail' ? 'list' : (route.name as NavName);

  const items: Item[] = [
    { name: 'list', path: '/', labelKey: 'navBrowse', hintKey: 'navBrowseHint', icon: '▤' },
    // 判定在匹配上面：先回答「能不能申」，再看「哪个更值得先看」。
    // 顺序反了会让人拿分数当资格，而分数只是排序。
    {
      name: 'verdict',
      path: '/verdict',
      labelKey: 'navVerdict',
      hintKey: 'navVerdictHint',
      icon: '⊪',
    },
    { name: 'match', path: '/match', labelKey: 'navMatch', hintKey: 'navMatchHint', icon: '◈' },
    {
      name: 'calendar',
      path: '/calendar',
      labelKey: 'navCalendar',
      hintKey: 'navCalendarHint',
      icon: '◷',
    },
    {
      name: 'track',
      path: '/track',
      labelKey: 'navTrack',
      hintKey: 'navTrackHint',
      icon: '✓',
      count: trackCount,
    },
    {
      name: 'saved',
      path: '/saved',
      labelKey: 'navSaved',
      hintKey: 'navSavedHint',
      icon: '★',
      count: savedCount,
    },
    {
      name: 'compare',
      path: '/compare',
      labelKey: 'navCompare',
      hintKey: 'navCompareHint',
      icon: '⇄',
      count: compareCount,
    },
    { name: 'about', path: '/about', labelKey: 'navData', hintKey: 'navDataHint', icon: 'ⓘ' },
  ];

  return (
    <aside className="sidebar" aria-label={t('workbench')}>
      <a className="sidebar__brand" href="#/">
        <span className="sidebar__mark" aria-hidden="true" />
        <span className="sidebar__name">
          <strong>{t('siteTitle')}</strong>
          <small>{t('workbench')}</small>
        </span>
      </a>

      <nav className="sidebar__nav">
        {items.map((it) => {
          const on = active === it.name;
          const cls: ReactNode = (
            <>
              <span className="sidebar__icon" aria-hidden="true">
                {it.icon}
              </span>
              <span className="sidebar__text">
                <span className="sidebar__label">{t(it.labelKey)}</span>
                {/* 用途说明：桌面常驻小字，窄屏由 CSS 隐藏（顶部横滑条放不下） */}
                <span className="sidebar__hint">{t(it.hintKey)}</span>
              </span>
              {it.count != null && it.count > 0 && (
                <span className="sidebar__count">{it.count}</span>
              )}
            </>
          );
          return (
            <button
              key={it.name}
              type="button"
              className={on ? 'sidebar__item sidebar__item--on' : 'sidebar__item'}
              aria-current={on ? 'page' : undefined}
              onClick={() => navigate(it.path)}
            >
              {cls}
            </button>
          );
        })}
      </nav>

      <p className="sidebar__foot">{t('profileDesc')}</p>
    </aside>
  );
}
