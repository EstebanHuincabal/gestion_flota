<script setup>
import { onMounted } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import { Capacitor } from '@capacitor/core'
import { useThemeStore } from '@/stores/theme.js'

const router     = useRouter()
const themeStore = useThemeStore()


// ── Push Notifications (solo dispositivos nativos) ────────────────────────────
async function inicializarPush() {
  // Solo funciona en iOS / Android; en el navegador no hacemos nada
  if (!Capacitor.isNativePlatform()) return

  try {
    const { PushNotifications } = await import('@capacitor/push-notifications')

    // Solicitar permiso
    const { receive } = await PushNotifications.requestPermissions()
    if (receive !== 'granted') return

    // Registrar para recibir el token FCM
    await PushNotifications.register()

    // ── Token FCM obtenido → enviarlo al backend ──────────────────────────────
    PushNotifications.addListener('registration', async ({ value: token }) => {
      try {
        const { apiFetch } = await import('@/services/api.js')
        await apiFetch('/api/conductor/push-token/', {
          method: 'POST',
          body:   JSON.stringify({ token }),
        })
      } catch {
        // Sin sesión todavía o sin conexión — se intentará al reconectar
      }
    })

    // ── Error de registro ─────────────────────────────────────────────────────
    PushNotifications.addListener('registrationError', (err) => {
      console.warn('[Push] Error de registro:', err)
    })

    // ── Notificación recibida con la app en PRIMER PLANO ──────────────────────
    PushNotifications.addListener('pushNotificationReceived', (notif) => {
      // Mostrar un toast en lugar de la notificación del sistema (que no aparece en foreground)
      mostrarToastPush(notif.title, notif.body, notif.data)
    })

    // ── Toque sobre una notificación (app en SEGUNDO PLANO o cerrada) ─────────
    PushNotifications.addListener('pushNotificationActionPerformed', ({ notification }) => {
      const data = notification.data || {}
      const tipo = data.tipo || ''

      if (tipo === 'mantencion_aprobada' || tipo === 'solicitud_aprobada' || tipo === 'solicitud_rechazada') {
        router.push('/solicitudes')
      } else if (tipo === 'mantencion_programada') {
        router.push('/mantencion')
      }
    })

  } catch (e) {
    console.warn('[Push] No disponible:', e)
  }
}

// Toast nativo mínimo para notificaciones en primer plano
// (reutilizado por toda la app mediante un elemento fijo al root)
const _toasts = []
let _toastEl  = null

function mostrarToastPush(titulo, cuerpo, data = {}) {
  if (!_toastEl) {
    _toastEl = document.createElement('div')
    _toastEl.style.cssText = `
      position: fixed; top: max(1rem, env(safe-area-inset-top) + 0.5rem);
      left: 1rem; right: 1rem; z-index: 9999;
      display: flex; flex-direction: column; gap: 0.5rem;
      pointer-events: none;
    `
    document.body.appendChild(_toastEl)
  }

  const card = document.createElement('div')
  card.style.cssText = `
    background: #1f2937; color: white; border-radius: 0.875rem;
    padding: 0.75rem 1rem; pointer-events: auto; cursor: pointer;
    box-shadow: 0 4px 16px rgba(0,0,0,0.25);
    animation: slideDown 0.3s ease;
  `
  card.innerHTML = `
    <p style="font-size:0.8125rem; font-weight:700; margin:0 0 0.125rem">${titulo || ''}</p>
    <p style="font-size:0.75rem; opacity:0.85; margin:0">${cuerpo || ''}</p>
  `

  // Al tocar el toast → navegar
  const tipo = data?.tipo || ''
  card.addEventListener('click', () => {
    if (tipo === 'mantencion_aprobada') router.push('/solicitudes')
    else if (tipo === 'solicitud_rechazada') router.push('/solicitudes')
    else if (tipo === 'mantencion_programada') router.push('/mantencion')
    card.remove()
  })

  _toastEl.appendChild(card)
  setTimeout(() => card.remove(), 5000)
}

onMounted(async () => {
  await themeStore.cargarTema()   // ← carga y aplica el tema guardado del conductor
  await inicializarPush()
})
</script>

<template>
  <RouterView />
</template>

<style>
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px); }
  to   { opacity: 1; transform: translateY(0); }
}
</style>
