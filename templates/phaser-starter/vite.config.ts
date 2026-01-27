import { defineConfig } from 'vite';

export default defineConfig({
  base: './',
  server: {
    port: 8080
  },
  build: {
    outDir: '../build_output',
    emptyOutDir: true,
    assetsDir: 'assets',
  }
});
