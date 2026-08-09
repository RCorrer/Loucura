import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  // Define a raiz do projeto Vite como a pasta atual (frontend/)
  root: './',
  plugins: [react()],
  build: {
    // Diretório de saída (relativo à raiz do app, que é segmenthub/)
    outDir: '../static',
    // Limpa o diretório antes de buildar
    emptyOutDir: true,
    rollupOptions: {
      // Força o ponto de entrada para o index.html
      input: './index.html',
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
  resolve: {
    alias: {
      '@shared': path.resolve(__dirname, 'src/shared-ui'),
    },
  },
});