import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      // Habilita el manifest y el service worker también con `npm run dev`
      // (localhost es un contexto seguro), para poder probar la PWA en local.
      devOptions: {
        enabled: true,
        type: 'module',
      },
      includeAssets: ['favicon.ico', 'apple-touch-icon-180x180.png', 'pwa-icon-source.svg'],
      manifest: {
        name: 'Gestión de Flota',
        short_name: 'Flota',
        description: 'Sistema de gestión de flota: vehículos, rutas, GPS y mantenimiento.',
        lang: 'es',
        theme_color: '#534AB7',
        background_color: '#534AB7',
        display: 'standalone',
        start_url: '/',
        scope: '/',
        icons: [
          { src: 'pwa-64x64.png', sizes: '64x64', type: 'image/png' },
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'maskable-icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // El service worker no debe interceptar la API, el admin de Django,
        // los WebSockets ni los archivos servidos por el backend.
        navigateFallbackDenylist: [/^\/api/, /^\/admin/, /^\/ws/, /^\/media/, /^\/static/],
      },
    }),
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
