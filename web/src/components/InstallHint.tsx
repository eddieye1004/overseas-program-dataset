// src/components/InstallHint.tsx
// 「添加到桌面」引导（M4）。
//
// 为什么是一个顶栏小控件 + 弹出层，而不是内容区里的一条横幅：
//   试过横幅。它在首屏占 70–112px，而 900px 视口里筛选区已经吃掉 354px、
//   上方还压着首访引导条与页头，于是第一行卡片被顶到折线以下——
//   e2e 的「桌面首屏露出 ≥2 张完整卡片」当场红（实测 banner 在时 0 张，
//   关掉后 3 张）。一条引导不该把被引导的内容挤走，所以它只能是零高度的
//   悬浮控件：默认收成一个图标，点了才展开步骤。
//
// 三种情况分开处理：
//   1. 已经以独立应用运行（display-mode: standalone）→ 不出现
//   2. Chrome 触发了 beforeinstallprompt → 弹出层里给真按钮，点了弹系统安装框
//   3. 其余（Safari / Firefox / 已拒绝过）→ 给手动步骤，按 UA 选一条
// 用户关掉后记在 localStorage，不再出现。
import { useEffect, useRef, useState } from 'react';
import { useI18n } from '../i18n';

const KEY_DISMISSED = 'opd.installDismissed';

/** beforeinstallprompt 不在 TS 标准 lib 里，单独声明用到的那两个成员 */
interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

/** 是否已经装成独立应用（安卓 Chrome / 桌面 PWA 用这个判据） */
function isStandalone(): boolean {
  if (typeof window === 'undefined') return false;
  if (window.matchMedia?.('(display-mode: standalone)').matches) return true;
  // iOS Safari 没有 display-mode 的 standalone 分支时用 navigator 标记
  return (window.navigator as unknown as { standalone?: boolean }).standalone === true;
}

function readDismissed(): boolean {
  try {
    return localStorage.getItem(KEY_DISMISSED) === '1';
  } catch {
    // 隐私模式下读不到，就当没关过——提示一次不算打扰
    return false;
  }
}

export function InstallHint() {
  const { t } = useI18n();
  const [deferred, setDeferred] = useState<InstallPromptEvent | null>(null);
  const [dismissed, setDismissed] = useState(readDismissed);
  const [standalone, setStandalone] = useState(isStandalone);
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const onPrompt = (e: Event) => {
      // 拦住浏览器自带的小横幅：它会盖在页脚上，且文案不可控
      e.preventDefault();
      setDeferred(e as InstallPromptEvent);
    };
    const onInstalled = () => {
      setStandalone(true);
      setDeferred(null);
      setOpen(false);
    };
    window.addEventListener('beforeinstallprompt', onPrompt);
    window.addEventListener('appinstalled', onInstalled);

    // 从浏览器里装好后切到独立窗口，display-mode 会变，但事件不会再发一次
    const mq = window.matchMedia?.('(display-mode: standalone)');
    const onMode = () => setStandalone(isStandalone());
    mq?.addEventListener?.('change', onMode);

    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt);
      window.removeEventListener('appinstalled', onInstalled);
      mq?.removeEventListener?.('change', onMode);
    };
  }, []);

  // 点外面 / 按 Esc 收起：弹出层不捕获焦点，就不该只能靠再点一次那个图标关掉
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  if (standalone || dismissed) return null;

  const close = () => {
    setDismissed(true);
    setOpen(false);
    try {
      localStorage.setItem(KEY_DISMISSED, '1');
    } catch {
      /* 写不进去就下次再提示，不影响使用 */
    }
  };

  const ua = typeof navigator !== 'undefined' ? navigator.userAgent : '';
  const steps = /iphone|ipad|ipod/i.test(ua)
    ? t('installIOS')
    : /android/i.test(ua)
      ? t('installAndroid')
      : t('installDesktop');

  return (
    <div className="installwrap" ref={wrapRef}>
      <button
        type="button"
        className={open ? 'installchip installchip--on' : 'installchip'}
        aria-expanded={open}
        aria-haspopup="dialog"
        title={t('installTitle')}
        onClick={() => setOpen((v) => !v)}
      >
        <span aria-hidden="true">⤓</span>
        <span className="installchip__text">{t('installTitle')}</span>
      </button>

      {open && (
        <div className="installpop" role="dialog" aria-label={t('installTitle')} data-install="">
          <strong className="installpop__title">{t('installTitle')}</strong>
          <p className="installpop__body">{t('installBody')}</p>
          <p className="installpop__steps">{steps}</p>
          <div className="installpop__side">
            {deferred ? (
              <button
                type="button"
                className="btn btn--primary btn--sm"
                onClick={async () => {
                  await deferred.prompt();
                  const choice = await deferred.userChoice;
                  // 用户选了「不装」也当作已处理：反复弹同一个框是骚扰
                  if (choice.outcome !== 'accepted') close();
                  setDeferred(null);
                }}
              >
                {t('installCta')}
              </button>
            ) : (
              <span className="installpop__hint">{t('installMenuHint')}</span>
            )}
            <button type="button" className="btn btn--ghost btn--sm" onClick={close}>
              {t('installDismiss')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
