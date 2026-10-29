// src/i18n/index.tsx
// 语言状态 + 查词逻辑。
// 关键设计：数据文件本身只有中文，英文译文放在 public/data/i18n.json 里，
// key 就是中文原串。所以 t() 遇到中文字符串时去词典查，查不到就回落原文。
// 这样数据仓库保持单语言（便于用 schema 校验），站点却能做到真正双语。
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import type { Lang } from '../types';
import { ENUM_LABELS, UI } from './ui';

const STORAGE_KEY = 'opd.lang';
/** 词典：中文原串 → 英文译文。启动时从 public/data/i18n.json 载入。 */
type Dict = Record<string, string>;

interface I18nValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  /** 页面骨架词条（按钮、标题、筛选项标签） */
  t: (key: keyof (typeof UI)['zh']) => string;
  /** 数据里的中文串 → 当前语言。中文模式下原样返回，英文模式下查词典。 */
  td: (text: string | null | undefined) => string;
  /** 枚举值（region / program_type / tags / 资格状态 …）→ 界面标签 */
  te: (value: string | null | undefined) => string;
  /** 词典载入完成与否；未完成时英文模式会先显示中文，避免闪成空白 */
  ready: boolean;
}

const I18nContext = createContext<I18nValue | null>(null);

/** 读 localStorage 里存的语言；用户没选过就按浏览器语言猜。 */
function readInitialLang(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'zh' || saved === 'en') return saved;
  } catch {
    // 隐私模式下 localStorage 可能抛异常，忽略即可
  }
  const nav = typeof navigator !== 'undefined' ? navigator.language : 'zh-CN';
  return nav.toLowerCase().startsWith('zh') ? 'zh' : 'en';
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(readInitialLang);
  const [dict, setDict] = useState<Dict>({});
  const [ready, setReady] = useState(false);

  // 词典只载一次。失败时不阻塞渲染：英文模式回落成中文，页面仍然可用。
  useEffect(() => {
    let alive = true;
    fetch(`${import.meta.env.BASE_URL}data/i18n.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d: Dict) => {
        if (alive) setDict(d);
      })
      .catch((err) => {
        console.warn('[i18n] dictionary failed to load, falling back to Chinese:', err);
      })
      .finally(() => {
        if (alive) setReady(true);
      });
    return () => {
      alive = false;
    };
  }, []);

  // 语言写入 localStorage，同时同步 <html lang>，让屏幕阅读器和浏览器翻译行为正确
  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem(STORAGE_KEY, l);
    } catch {
      /* 忽略写入失败 */
    }
    if (typeof document !== 'undefined') {
      document.documentElement.lang = l === 'zh' ? 'zh-CN' : 'en';
    }
  }, []);

  const value = useMemo<I18nValue>(() => {
    const t = (key: keyof (typeof UI)['zh']) => UI[lang][key] ?? UI.zh[key] ?? String(key);

    const td = (text: string | null | undefined) => {
      if (!text) return '';
      if (lang === 'zh') return text;
      const hit = dict[text];
      if (hit) return hit;
      // 词典缺条目时回落中文，开发环境下提示，方便补词条
      if (import.meta.env.DEV && /[\u4e00-\u9fff]/.test(text)) {
        console.warn('[i18n] missing translation:', text.slice(0, 60));
      }
      return text;
    };

    const te = (v: string | null | undefined) => {
      if (!v) return '';
      return ENUM_LABELS[lang][v] ?? v;
    };

    return { lang, setLang, t, td, te, ready };
  }, [lang, setLang, dict, ready]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n must be used inside <I18nProvider>');
  return ctx;
}
