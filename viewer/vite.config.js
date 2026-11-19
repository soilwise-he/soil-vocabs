import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { conceptPages } from './scripts/concept-pages.mjs'

export default defineConfig({
  plugins: [vue(), conceptPages()],
  base: './',
  server: { host: '127.0.0.1', port: 5174, strictPort: true },
  preview: { host: '127.0.0.1', port: 4174, strictPort: true },
})
