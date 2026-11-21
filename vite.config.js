import { defineConfig } from 'vite';

export default defineConfig({
  define: {
    __SITES_PREVIEW__: JSON.stringify(process.env.SITES_DEMO === '1'),
  },
  server: {
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', ws: true },
    },
  },
});
