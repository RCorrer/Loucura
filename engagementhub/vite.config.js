import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/track': 'http://localhost:8000',
      '/webhook': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
  resolve: {
    alias: {
      '@shared': path.resolve(__dirname, 'src/shared-ui'),
    },
  },
});
