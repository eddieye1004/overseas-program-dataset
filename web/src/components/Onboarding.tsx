// src/components/Onboarding.tsx
// 首访引导条：一行结论 + 可展开的三步说明。
//
// 为什么是内联条、而且是「收起态只占一行」：
//   1. 本站唯一的「啊哈」是首屏那几个数字。模态会把它盖住，等于先讲流程再给结论。
//   2. 首屏高度是硬预算。1280×900 下页头 117 + 筛选面板 354 + 结果条 44，
//      留给卡片的只剩 253px —— 恰好一排卡片（223px）。任何高于 ~30px 的新区块
//      都会把这一排挤出首屏（e2e 的「桌面首屏露出 ≥2 张完整卡片」直接红）。
//      所以收起态只渲染一行（标题 + 计数 + 展开/跳过），六模块表与三步路径折进展开区。
//   3. 模态要处理焦点陷阱、Esc、滚动穿透、aria-modal——为一个只读索引站付这笔账不值，
//      而且遮罩会让 e2e 里那一百多条交互断言全部超时。
//
// 判定逻辑在 lib/onboarding.ts（纯函数、不进 React），这里只管渲染与状态机。
import { useEffect, useMemo, useState } from 'react';
import { useI18n } from '../i18n';
import {
  clearReplay,
  markOnboarded,
  readOnboardSnapshot,
  REPLAY_EVENT,
  shouldShowOnboarding,
} from '../lib/onboarding';
import type { UiKey } from '../i18n/ui';

/** 六个模块的用途表：键名复用侧栏，不新造名字——否则同一件事会有两种叫法 */
const MODULES: { key: UiKey; hint: UiKey }[] = [
  { key: 'navBrowse', hint: 'navBrowseHint' },
  { key: 'navMatch', hint: 'navMatchHint' },
  { key: 'navTrack', hint: 'navTrackHint' },
  { key: 'navSaved', hint: 'navSavedHint' },
  { key: 'navCompare', hint: 'navCompareHint' },
  { key: 'navData', hint: 'navDataHint' },
];

const PATH_STEPS: UiKey[] = ['onboardPath1', 'onboardPath2', 'onboardPath3'];

export function Onboarding({ programCount }: { programCount: number | null }) {
  const { t } = useI18n();
  // 首访判定只在挂载时做一次：之后的所有变化都由本组件的 state 驱动，
  // 避免「点了跳过 → 写 localStorage → 判定变化 → 组件被自己卸载」的竞态。
  const [visible, setVisible] = useState(() => shouldShowOnboarding(readOnboardSnapshot()));
  // 收起态：首屏只留一行结论，展开与否由用户决定
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (visible) clearReplay();
  }, [visible]);

  // 数据说明页的「重看」按钮：本组件在 App 里常驻，路由切换不会重新挂载，
  // 所以必须靠事件把它叫回来，否则点了没反应。
  useEffect(() => {
    const onReplay = () => {
      setOpen(false);
      setVisible(true);
    };
    window.addEventListener(REPLAY_EVENT, onReplay);
    return () => window.removeEventListener(REPLAY_EVENT, onReplay);
  }, []);

  // 引导条在时，收起 `.page__intro`：那一行说的「按国家、地区…每条都标注官方来源」
  // 与引导条第一行完全重叠，两条并存既啰嗦又多吃 26px 首屏。
  // 用 data 属性而不是 React 状态传递，是因为这条规则只影响样式，不值得穿三层 props。
  useEffect(() => {
    const root = document.documentElement;
    if (visible) root.dataset.onboarding = '1';
    else delete root.dataset.onboarding;
    return () => {
      delete root.dataset.onboarding;
    };
  }, [visible]);

  const close = () => {
    markOnboarded();
    setVisible(false);
    // 焦点回到主内容区：完成后键盘用户的下一站应该是内容，不是页面顶部
    document.getElementById('main')?.focus();
  };

  const count = programCount ?? 0;
  const body = useMemo(() => t('onboardStep1Body').replace('{n}', String(count)), [t, count]);

  if (!visible) return null;

  return (
    <section
      className="onboard"
      data-onboard=""
      data-open={open ? '' : undefined}
      aria-label={t('onboardStep1Title')}
      // 刻意不用 role="dialog" / aria-modal：这不是模态，页面其余部分必须可交互
      role="region"
    >
      {/* 收起态就一行标题。首屏高度是硬预算（见文件头），多一行解释就会顶掉一排卡片；
          解释与计数放进展开区第一段，那里有空间讲完整。 */}
      <div className="onboard__bar">
        <p className="onboard__lead">
          <strong className="onboard__title">{t('onboardStep1Title')}</strong>
        </p>
        <button
          type="button"
          className="onboard__toggle"
          data-onboard-expand=""
          aria-expanded={open}
          aria-controls="onboard-body"
          onClick={() => setOpen(!open)}
        >
          {open ? t('onboardCollapse') : t('onboardExpand')}
        </button>
        <button type="button" className="onboard__skip" data-onboard-skip="" onClick={close}>
          {t('onboardSkip')}
        </button>
      </div>

      {/* 展开区始终渲染（用 hidden 收起），键盘 Tab 顺序与语义不依赖展开状态 */}
      <div className="onboard__body" id="onboard-body" hidden={!open}>
        <p className="onboard__text">{body}</p>
        <div className="onboard__cols">
          <div className="onboard__col">
            <p className="onboard__sub">{t('onboardStep2Title')}</p>
            <table className="onboard__table">
              <thead>
                <tr>
                  <th scope="col">{t('onboardModuleCol')}</th>
                </tr>
              </thead>
              <tbody>
                {MODULES.map((m) => (
                  <tr key={m.key} data-module="">
                    <th scope="row">{t(m.key)}</th>
                    <td>{t(m.hint)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="onboard__col">
            <p className="onboard__sub">{t('onboardStep3Title')}</p>
            <ol className="onboard__steps">
              {PATH_STEPS.map((k) => (
                <li key={k} data-path-step="">
                  {t(k)}
                </li>
              ))}
            </ol>
            <button type="button" className="btn btn--primary" data-onboard-done="" onClick={close}>
              {t('onboardStart')}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
