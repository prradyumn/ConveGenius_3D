import { defineConfig } from 'vite';

export default defineConfig({
  base: './',
  // strictPort on both: this machine already runs other Vite projects on the
  // default 5173/4173, and without strictPort Vite silently falls back to
  // another port while something else answers on the one you typed. That
  // wasted real debugging time - fail loudly instead.
  server: { host: true, port: 5290, strictPort: true },
  preview: { host: true, port: 4290, strictPort: true },
  build: {
    target: 'es2019',
    assetsInlineLimit: 0,
    chunkSizeWarningLimit: 1200,
  },
});
