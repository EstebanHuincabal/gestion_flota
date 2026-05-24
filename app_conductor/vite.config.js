import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],

  // Leer variables de entorno desde la raíz del monorepo (gestion_flota/.env)
  envDir: '..',

  resolve: {
    alias: {
      // Permite usar '@/...' igual que en el sistema web
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  server: {
    port: 5174,   // Puerto distinto al web (5173) para correr ambos en paralelo
    proxy: {
      // En desarrollo con Vite en browser, redirige /api/* al backend Django
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
