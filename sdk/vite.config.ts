import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  build: {
    lib: {
      entry: resolve(__dirname, 'src/index.ts'),
      name: 'HavisIQ',
      formats: ['iife'],
      fileName: () => 'havisiq-sdk.js',
    },
  },
  test: {
    environment: 'jsdom',
  },
});
