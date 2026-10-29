// src/App.tsx
// 应用外壳：左侧固定导航 + 右侧内容区，形态参考 CampPilot 那类工作台。
// 所有用户状态（收藏 / 对比 / 申请进度 / 最近浏览）在这一层持有再下发，
// 好处是切路由时状态不丢，也不必让每个页面各自读一遍 localStorage。
import { useCallback } from 'react';
import { useI18n } from './i18n';
import { useRoute } from './lib/router';
import { COMPARE_MAX, useCompare, useRecent, useSaved, useTrack } from './lib/store';
import { ListView } from './components/ListView';
import { DetailView } from './components/DetailView';
import { MatchView } from './components/MatchView';
import { TrackView } from './components/TrackView';
import { SavedView } from './components/SavedView';
import { CompareView } from './components/CompareView';
import { AboutView } from './components/AboutView';
import { Sidebar } from './components/Sidebar';

function LangSwitch() {
  const { lang, setLang, t } = useI18n();
  return (
    <button
      type="button"
      className="langswitch"
      // 点一下就在两种语言间切换；当前语言高亮，另一语言淡显
      onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')}
      aria-label={lang === 'zh' ? 'Switch to English' : '切换到中文'}
      title={lang === 'zh' ? 'Switch to English' : '切换到中文'}
    >
      <span className={lang === 'zh' ? 'langswitch__on' : ''}>中文</span>
      <span className="langswitch__sep">/</span>
      <span className={lang === 'en' ? 'langswitch__on' : ''}>EN</span>
      <span className="sr-only">{t('lang')}</span>
    </button>
  );
}

export default function App() {
  const { t } = useI18n();
  const route = useRoute();

  const saved = useSaved();
  const compare = useCompare();
  const recent = useRecent();
  const track = useTrack();

  const toggleSave = saved.toggle;
  const toggleCompare = compare.toggle;

  /** 「加入我的申请」：已在进度板里就不重复加，默认状态为 todo */
  const addTrack = useCallback(
    (id: string) => {
      if (!track.map[id]) track.setStatus(id, 'todo');
    },
    [track],
  );

  // 详情页里已经在这个项目的对比清单中时，不应算「满」
  const currentId = route.name === 'detail' ? route.id : '';
  const compareFull =
    compare.list.length >= COMPARE_MAX && !compare.list.includes(currentId);

  return (
    <div className="app app--shell">
      {/* 键盘用户的第一个 Tab 位：跳过侧栏直接进内容区 */}
      <a className="skiplink" href="#main">
        {t('skipToContent')}
      </a>

      <Sidebar
        route={route}
        savedCount={saved.list.length}
        trackCount={Object.keys(track.map).length}
        compareCount={compare.list.length}
      />

      <div className="shell">
        <header className="shell__bar">
          <span className="shell__crumb">{t('siteTitle')}</span>
          <LangSwitch />
        </header>

        <main className="main" id="main" tabIndex={-1}>
          {route.name === 'list' && (
            <ListView savedIds={saved.list} onToggleSave={toggleSave} />
          )}
          {route.name === 'detail' && (
            <DetailView
              id={route.id}
              saved={saved.list.includes(route.id)}
              onToggleSave={toggleSave}
              onAddTrack={addTrack}
              tracked={!!track.map[route.id]}
              onAddCompare={toggleCompare}
              compareFull={compareFull}
              onSeeRecent={recent.push}
            />
          )}
          {route.name === 'match' && (
            <MatchView savedIds={saved.list} onToggleSave={toggleSave} />
          )}
          {route.name === 'track' && <TrackView track={track} />}
          {route.name === 'saved' && (
            <SavedView savedIds={saved.list} onToggleSave={toggleSave} />
          )}
          {route.name === 'compare' && (
            <CompareView
              compareIds={compare.list}
              onRemove={compare.remove}
              onClear={compare.clear}
            />
          )}
          {route.name === 'about' && <AboutView />}
        </main>

        <footer className="ftr">
          <p>{t('footerNote')}</p>
        </footer>
      </div>
    </div>
  );
}
