import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  build: {
    outDir: '../src/coherent_lasers/genesis_mx/app/frontend/build',
    emptyOutDir: true,
  }
})
