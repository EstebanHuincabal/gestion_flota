import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
  ],
  server: {
    port: 7183,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // Archivos subidos (fotos de vehículos, comprobantes, documentos) los
      // sirve Django en dev; sin este proxy darían 404 desde el puerto de Vite.
      '/media': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
        // El backend (daphne) corta las conexiones WS de golpe cada vez que
        // reinicia por autoreload o al recargar el front (HMR). Eso genera un
        // ECONNRESET benigno: el cliente del mapa reconecta solo. Silenciamos
        // ese ruido y dejamos pasar cualquier otro error real.
        configure: (proxy) => {
          proxy.on('error', (err) => {
            if (err && err.code === 'ECONNRESET') return
            console.warn('[ws proxy]', err?.message || err)
          })
        },
      },
    },
  },
})
