<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import { Capacitor } from '@capacitor/core'
import { useThemeStore } from '@/stores/theme.js'
import { useAuthStore } from '@/stores/auth.js'
import { iniciarEnvioUbicacion, detenerEnvioUbicacion } from '@/services/geolocalizacion.js'

const router     = useRouter()
const themeStore = useThemeStore()
const auth       = useAuthStore()

// ── GPS: enviar ubicación siempre que el conductor esté autenticado ───────────
// Arranca al iniciar sesión, se detiene al cerrar sesión.
watch(
  () => auth.estaAutenticado && auth.esConductor,
  async (activo) => {
    if (activo) {
      await iniciarEnvioUbicacion()
    } else {
      detenerEnvioUbicacion()
    }
  },
  { immediate: true }
)

// ── Bloqueo por suscripción ───────────────────────────────────
const bloqueado      = ref(false)
const mensajeBloqueo = ref('')

function onBloqueada(e) {
  mensajeBloqueo.value = e.detail?.mensaje || 'La suscripción de tu empresa no está activa. Contacta al administrador.'
  bloqueado.value = true
}

async function cerrarSesionBloqueo() {
  await auth.logout()
  bloqueado.value = false
}

// Sesión expirada (cuenta desactivada/bloqueada en el servidor) → expulsar al login
function onSesionExpirada() {
  bloqueado.value = false
  auth.expirarSesion()
}


// ── Status Bar ───────────────────────────────────────────────────────────────
async function aplicarColorStatusBar(color) {
  if (!Capacitor.isNativePlatform()) return
  try {
    const { StatusBar } = await import('@capacitor/status-bar')
    await StatusBar.setBackgroundColor({ color })
  } catch {}
}

async function inicializarStatusBar() {
  if (!Capacitor.isNativePlatform()) return
  try {
    const { StatusBar, Style } = await import('@capacitor/status-bar')
    await StatusBar.setOverlaysWebView({ overlay: false })
    await StatusBar.setStyle({ style: Style.Light })
    await StatusBar.setBackgroundColor({ color: themeStore.temaActual.colorGrad[0] })
  } catch (e) {
    console.warn('[StatusBar]', e)
  }
}

// Sincronizar color de status bar cuando el conductor cambia de tema
watch(() => themeStore.temaActualId, () => {
  aplicarColorStatusBar(themeStore.temaActual.colorGrad[0])
})

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

    // ── Token FCM obtenido → enviarlo al backend (con reintento) ─────────────
    PushNotifications.addListener('registration', async ({ value: token }) => {
      const _enviarToken = async (intentos = 0) => {
        try {
          const { apiFetch } = await import('@/services/api.js')
          await apiFetch('/api/conductor/push-token/', {
            method: 'POST',
            body:   JSON.stringify({ token }),
          })
        } catch {
          // Reintentar hasta 3 veces con backoff exponencial
          if (intentos < 3) {
            setTimeout(() => _enviarToken(intentos + 1), 5000 * (intentos + 1))
          }
        }
      }
      await _enviarToken()
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

// ── Permisos de cámara y GPS ──────────────────────────────────────────────────
async function inicializarPermisos() {
  if (!Capacitor.isNativePlatform()) return
  try {
    const { Camera }       = await import('@capacitor/camera')
    const { Geolocation }  = await import('@capacitor/geolocation')
    await Camera.requestPermissions({ permissions: ['camera', 'photos'] })
    await Geolocation.requestPermissions()
  } catch (e) {
    console.warn('[Permisos]', e)
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
  await themeStore.cargarTema()
  await inicializarStatusBar()
  await inicializarPush()
  await inicializarPermisos()
  window.addEventListener('suscripcion-bloqueada', onBloqueada)
  window.addEventListener('sesion-expirada', onSesionExpirada)
})

onUnmounted(() => {
  window.removeEventListener('suscripcion-bloqueada', onBloqueada)
  window.removeEventListener('sesion-expirada', onSesionExpirada)
})
</script>

<template>
  <RouterView />

  <!-- Overlay bloqueante: suscripción suspendida/pendiente -->
  <Teleport to="body">
    <div v-if="bloqueado" class="bloqueo-overlay">
      <div class="bloqueo-box">
        <div class="bloqueo-icono">⚠️</div>
        <h2 class="bloqueo-titulo">Acceso restringido</h2>
        <p class="bloqueo-msg">{{ mensajeBloqueo }}</p>
        <button class="bloqueo-btn" @click="cerrarSesionBloqueo">
          Cerrar sesión
        </button>
      </div>
    </div>
  </Teleport>
</template>

<style>
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Overlay de bloqueo por suscripción */
.bloqueo-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  z-index: 99999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  padding-top: max(1.5rem, env(safe-area-inset-top));
  padding-bottom: max(1.5rem, env(safe-area-inset-bottom));
}

.bloqueo-box {
  background: #ffffff;
  border-radius: 1.25rem;
  padding: 2rem 1.75rem;
  max-width: 360px;
  width: 100%;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.bloqueo-icono {
  font-size: 2.75rem;
  margin-bottom: 1rem;
  line-height: 1;
}

.bloqueo-titulo {
  font-size: 1.125rem;
  font-weight: 700;
  color: #111827;
  margin: 0 0 0.75rem;
}

.bloqueo-msg {
  font-size: 0.9rem;
  color: #4B5563;
  line-height: 1.55;
  margin: 0 0 1.5rem;
}

.bloqueo-btn {
  width: 100%;
  padding: 0.75rem;
  background: #DC2626;
  color: #ffffff;
  border: none;
  border-radius: 0.75rem;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s;
}

.bloqueo-btn:active {
  background: #B91C1C;
}
</style>
