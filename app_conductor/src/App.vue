<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import { Capacitor } from '@capacitor/core'
import { Geolocation } from '@capacitor/geolocation'
import { Camera } from '@capacitor/camera'
import { useThemeStore } from '@/stores/theme.js'
import { useAuthStore } from '@/stores/auth.js'
import { iniciarEnvioUbicacion, detenerEnvioUbicacion, onGpsStateChange } from '@/services/geolocalizacion.js'

// El servicio notifica cuando el GPS se apaga o vuelve → actualizamos el banner
onGpsStateChange((activo) => { gpsDesactivado.value = !activo })

const router     = useRouter()
const themeStore = useThemeStore()
const auth       = useAuthStore()

// ── GPS: enviar ubicación siempre que el conductor esté autenticado ───────────
// Verificar GPS solo una vez al autenticar — no en un intervalo para evitar
// que el SO pregunte repetidamente por la ubicación precisa.
watch(
  () => auth.estaAutenticado && auth.esConductor,
  async (activo) => {
    if (activo) {
      await verificarGpsActivo()
      await iniciarEnvioUbicacion()
    } else {
      detenerEnvioUbicacion()
      gpsDesactivado.value = false
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

// ── Permisos y validación de GPS ─────────────────────────────────────────────
const gpsDesactivado = ref(false)

async function inicializarPermisos() {
  if (!Capacitor.isNativePlatform()) return
  try {
    // Cámara: pedir permiso con imports estáticos (más fiable que dinámicos)
    const camStatus = await Camera.checkPermissions()
    if (camStatus.camera !== 'granted') {
      await Camera.requestPermissions({ permissions: ['camera', 'photos'] })
    }
  } catch (e) {
    console.warn('[Permisos cámara]', e)
  }
  try {
    // GPS: pedir permiso del sistema
    const geoStatus = await Geolocation.checkPermissions()
    if (geoStatus.location !== 'granted') {
      await Geolocation.requestPermissions()
    }
  } catch (e) {
    console.warn('[Permisos GPS]', e)
  }
}

async function verificarGpsActivo() {
  if (!Capacitor.isNativePlatform()) return
  try {
    // Intenta obtener posición con timeout corto
    // Si el hardware GPS está apagado lanza error code 2 (POSITION_UNAVAILABLE)
    await Geolocation.getCurrentPosition({ enableHighAccuracy: false, timeout: 5000 })
    gpsDesactivado.value = false
  } catch (e) {
    // code 1 = permiso denegado, code 2 = GPS apagado, code 3 = timeout
    if (e?.code === 2 || e?.message?.toLowerCase().includes('unavailable')) {
      gpsDesactivado.value = true
    }
  }
}

function abrirAjustesUbicacion() {
  // Abre los ajustes del sistema en Android e iOS
  if (Capacitor.getPlatform() === 'android') {
    window.open('android.settings.LOCATION_SOURCE_SETTINGS', '_system')
  } else {
    window.open('app-settings:', '_system')
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

  <!-- Banner GPS desactivado -->
  <Teleport to="body">
    <div v-if="gpsDesactivado && auth.esConductor" class="gps-banner">
      <span class="gps-banner-icon">📍</span>
      <span class="gps-banner-texto">El GPS está desactivado. Actívalo para el seguimiento de rutas.</span>
      <button class="gps-banner-btn" @click="abrirAjustesUbicacion">Activar</button>
    </div>
  </Teleport>

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

/* Banner GPS desactivado */
.gps-banner {
  position: fixed;
  bottom: env(safe-area-inset-bottom, 0);
  left: 0; right: 0;
  z-index: 9000;
  background: #F59E0B;
  color: #78350F;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  font-size: 0.8125rem;
  font-family: inherit;
  box-shadow: 0 -2px 12px rgba(0,0,0,0.15);
}
.gps-banner-icon { font-size: 1.1rem; flex-shrink: 0; }
.gps-banner-texto { flex: 1; font-weight: 500; line-height: 1.3; }
.gps-banner-btn {
  flex-shrink: 0;
  background: #78350F;
  color: #fff;
  border: none;
  border-radius: 0.5rem;
  padding: 0.4rem 0.875rem;
  font-size: 0.8125rem;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
}
</style>
