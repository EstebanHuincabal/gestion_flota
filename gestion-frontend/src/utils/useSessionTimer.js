import { ref, onUnmounted } from 'vue'
import { refreshAccessToken } from './api.js'

// Cierre de sesión por INACTIVIDAD REAL del usuario (no por expiración del token).
// Mientras haya actividad (mouse/teclado/scroll), el access token se renueva en
// segundo plano y la sesión no se interrumpe — pensado para pantallas que quedan
// abiertas todo el día. Solo tras un rato sin actividad se avisa y se cierra.
const INACTIVIDAD_MAX_MS = 30 * 60 * 1000   // 30 min sin actividad → cerrar sesión
const WARN_ANTES_MS      = 2 * 60 * 1000    // avisar 2 min antes del cierre
const REFRESH_ANTES_MS   = 5 * 60 * 1000    // renovar el token si le quedan < 5 min
const CHECK_MS           = 1000             // evaluar una vez por segundo

const EVENTOS_ACTIVIDAD = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll', 'click']

// Vencimiento (ms epoch) del access token actual, leído de su payload.
function leerExp() {
  const token = localStorage.getItem('access_token')
  if (!token) return null
  try {
    const partes = token.split('.')
    if (partes.length < 2) return null
    const payload = JSON.parse(atob(partes[1].replace(/-/g, '+').replace(/_/g, '/')))
    return typeof payload.exp === 'number' ? payload.exp * 1000 : null
  } catch {
    return null
  }
}

function limpiarSesion() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('usuario')
  sessionStorage.removeItem('plan_modulos')
  sessionStorage.removeItem('plan_nombre')
  sessionStorage.removeItem('plan_permisos')
  sessionStorage.removeItem('empresaActiva')
  window.location.href = '/login'
}

export function useSessionTimer() {
  const mostrarModal      = ref(false)
  const segundosRestantes = ref(Math.round(WARN_ANTES_MS / 1000))

  let ultimaActividad = Date.now()
  let intervalo       = null
  let refrescando     = false

  function marcarActividad() {
    ultimaActividad = Date.now()
    if (mostrarModal.value) mostrarModal.value = false   // el usuario volvió
  }

  async function tick() {
    const ahora               = Date.now()
    const restanteInactividad = INACTIVIDAD_MAX_MS - (ahora - ultimaActividad)

    // 1. Demasiado tiempo sin actividad → cerrar sesión.
    if (restanteInactividad <= 0) {
      detener()
      limpiarSesion()
      return
    }

    // 2. Entrando en la ventana de aviso → mostrar el modal con cuenta regresiva.
    if (restanteInactividad <= WARN_ANTES_MS) {
      segundosRestantes.value = Math.ceil(restanteInactividad / 1000)
      mostrarModal.value = true
      return
    }

    // 3. Hay actividad reciente: mantener la sesión viva renovando el token en
    //    segundo plano cuando está por expirar.
    mostrarModal.value = false
    const exp = leerExp()
    if (exp && exp - ahora < REFRESH_ANTES_MS && !refrescando) {
      refrescando = true
      try {
        const r = await refreshAccessToken()
        // Solo si el refresh token venció de verdad cerramos; un fallo de red
        // no interrumpe (se reintenta en el próximo tick).
        if (!r.ok && r.expired) {
          detener()
          limpiarSesion()
        }
      } finally {
        refrescando = false
      }
    }
  }

  // El usuario confirma desde el modal que sigue ahí.
  function extenderSesion() {
    marcarActividad()
  }

  function logoutDesdeModal() {
    detener()
    limpiarSesion()
  }

  function detener() {
    if (intervalo) { clearInterval(intervalo); intervalo = null }
    EVENTOS_ACTIVIDAD.forEach(e => window.removeEventListener(e, marcarActividad))
  }

  EVENTOS_ACTIVIDAD.forEach(e => window.addEventListener(e, marcarActividad, { passive: true }))
  intervalo = setInterval(tick, CHECK_MS)

  onUnmounted(detener)

  return { mostrarModal, segundosRestantes, extenderSesion, logoutDesdeModal }
}
