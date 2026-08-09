// segmenthub/frontend/vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  root: './',
  plugins: [react()],
  build: {
    outDir: '../static',
    emptyOutDir: true,
    rollupOptions: {
      input: './index.html', // <-- FORÇA O PONTO DE ENTRADA
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  resolve: {
    alias: {
      '@shared': path.resolve(__dirname, 'src/shared-ui'),
    },
  },
});