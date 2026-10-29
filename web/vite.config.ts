import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 纯静态站点：产物是 dist/ 里的静态文件，没有服务端、没有环境变量、没有密钥。
// base 用相对路径 './'，这样同一份产物既能跑在用户主页根（/），
// 也能跑在 GitHub Pages 的项目子路径（/overseas-program-dataset/），无需改代码。
export default defineConfig({
  base: './',
  plugins: [react()],
  build: {
    outDir: 'dist',
    // 11 条数据 + 词典体积很小，不做额外拆包，避免多请求
    assetsInlineLimit: 4096,
  },
  server: {
    port: 5173,
    host: '127.0.0.1',
  },
});
