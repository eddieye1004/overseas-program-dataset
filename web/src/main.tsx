import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { I18nProvider } from './i18n';
import { registerServiceWorker } from './lib/pwa';
// 顺序有意义：tokens 先定义变量，其余文件消费变量；ia.css 最后，覆盖信息架构层
import './tokens.css';
import './styles.css';
import './workbench.css';
import './refine.css';
import './ia.css';
// 首访引导条：单独一份，避免把 90 行仅在首访生效的规则塞进上述任一分层
import './onboard.css';
// 资格判定 / 追踪清单 / 安装引导（2026-11-12 追踪系统一期），同样单独分层
import './verdict.css';

const root = document.getElementById('root');
if (!root) throw new Error('#root not found');

createRoot(root).render(
  <StrictMode>
    <I18nProvider>
      <App />
    </I18nProvider>
  </StrictMode>,
);

// 渲染之后再注册：SW 注册会占用一次网络与存储，不该和首屏抢资源
registerServiceWorker();
