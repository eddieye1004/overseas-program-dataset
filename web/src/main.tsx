import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { I18nProvider } from './i18n';
// 顺序有意义：tokens 先定义变量，其余文件消费变量；ia.css 最后，覆盖信息架构层
import './tokens.css';
import './styles.css';
import './workbench.css';
import './refine.css';
import './ia.css';

const root = document.getElementById('root');
if (!root) throw new Error('#root not found');

createRoot(root).render(
  <StrictMode>
    <I18nProvider>
      <App />
    </I18nProvider>
  </StrictMode>,
);
