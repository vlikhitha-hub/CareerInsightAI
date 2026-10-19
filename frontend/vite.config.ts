import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: { rollupOptions: { output: { manualChunks(id) {
    if (!id.includes('/node_modules/')) return undefined;
    if (id.includes('/node_modules/lucide-react/')) return 'icons';
    if (/\/node_modules\/(react|react-dom|scheduler)\//.test(id)) return 'react-vendor';
    return 'vendor';
  } } } },
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
});
