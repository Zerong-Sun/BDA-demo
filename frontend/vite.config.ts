import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      debug: '/src/vendor/debug-browser-default.ts',
      'debug/src/browser.js': '/src/vendor/debug-browser-default.ts',
      'mutative/dist/index.js': 'mutative/dist/mutative.esm.mjs',
      'style-to-js': '/src/vendor/style-to-js-default.ts',
      'style-to-js/cjs/index.js': '/src/vendor/style-to-js-default.ts',
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8100',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    // Mol* has circular ESM deps; pre-bundling breaks BuiltInPluginBehaviors.registerDefault.
    exclude: ['molstar'],
  },
  build: {
    chunkSizeWarningLimit: 2000,
  },
})
