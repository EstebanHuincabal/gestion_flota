import { Capacitor, registerPlugin } from '@capacitor/core'
import { Network }                   from '@capacitor/network'
import { apiFetch }                  from './api.js'
import { wsService }                 from './websocket.js'

// registerPlugin evita importar el módulo directamente: el build web no puede
// resolver el paquete nativo, pero las llamadas solo ocurren en isNativePlatform().
const BackgroundGeolocation = registerPlugin('BackgroundGeolocation')

let bgWatcherId          = null   // id del watcher nativo
let webWatchId           = null   // id del watcher navigator.geolocation (solo web)
let ultimoEnvio          = 0
let ultimoFix            = 0
let gpsActivo            = false
let ultimaPos            = null
let heartbeatTimer       = null
let _ultimoRecreacionBg  = 0
let _onGpsChange         = null
// true tras enviar gps_inactivo; se resetea al recibir una posición real.
// Evita spam en el loop de recreación Y garantiza un envío al iniciar con GPS apagado.
let _gpsInactivoEnviado  = false

const THROTTLE_MS  = 3000
const BG_RETRY_MS  = 15_000
const HEARTBEAT_MS = 4000
// Sin posición real en este tiempo → "sin señal" (solo fallback web; en nativo
// un vehículo detenido no genera updates por distanceFilter).
const SILENCIO_MS  = 10_000

let _onPermisoInsuficiente = null

export function onGpsStateChange(cb) { _onGpsChange = cb }
function notificarGps(activo) { if (_onGpsChange) _onGpsChange(activo) }

// Se invoca cuando el permiso es solo "mientras se usa" en vez de "todo el tiempo".
export function onPermisoInsuficiente(cb) { _onPermisoInsuficiente = cb }

async function enviarUbicacion(lat, lng, vel, forzar = false) {
  const ahora = Date.now()
  if (!forzar && ahora - ultimoEnvio < THROTTLE_MS) return
  ultimoEnvio = ahora

  const payload = { latitud: lat, longitud: lng, velocidad: vel }
  const enviado = wsService.send({ tipo: 'ubicacion_update', ...payload })

  if (!enviado) {
    try {
      const { connected } = await Network.getStatus()
      if (connected) {
        await apiFetch('/api/conductor/ubicacion/', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
      }
    } catch { /* fail silent */ }
  }
}

async function enviarGpsInactivo() {
  const enviado = wsService.send({ tipo: 'gps_inactivo' })
  if (enviado) return
  try {
    const { connected } = await Network.getStatus()
    if (connected) {
      await apiFetch('/api/conductor/ubicacion/', {
        method: 'POST',
        body: JSON.stringify({ gps_inactivo: true }),
      })
    }
  } catch { /* fail silent */ }
}

function procesarPosicion(lat, lng, velMs) {
  const vel = Math.max(0, (velMs || 0) * 3.6)   // m/s → km/h, clamp del -1 de Android
  ultimaPos = { lat, lng, vel }
  ultimoFix = Date.now()
  _gpsInactivoEnviado = false   // GPS volvió → permitir próximo aviso de inactividad
  const recuperado = !gpsActivo
  if (recuperado) gpsActivo = true
  notificarGps(true)
  enviarUbicacion(lat, lng, vel, recuperado)
}

// ── Modo nativo (BackgroundGeolocation) ─────────────────────────────────────

async function iniciarNativo() {
  try {
    bgWatcherId = await BackgroundGeolocation.addWatcher(
      {
        backgroundMessage: 'Enviando tu ubicación mientras tienes una ruta activa.',
        backgroundTitle:   'Gestión de Flota — rastreo activo',
        requestPermissions: true,
        stale: false,
        distanceFilter: 10,
      },
      (location, error) => {
        if (error) {
          if (error.code === 'NOT_AUTHORIZED') {
            // Permiso insuficiente: el usuario otorgó solo "mientras se usa" en
            // vez de "todo el tiempo". Con pantalla apagada el plugin no recibe GPS.
            if (_onPermisoInsuficiente) _onPermisoInsuficiente()
          }
          if (error.code === 'NOT_AUTHORIZED' || error.code === 'NOT_ENABLED') {
            if (gpsActivo) {
              gpsActivo = false
              notificarGps(false)
            }
            // Enviar gps_inactivo una sola vez por cada período sin GPS
            // (cubre tanto el inicio de sesión con GPS apagado como la pérdida
            // en mitad de una sesión; el flag se resetea al recibir posición).
            if (!_gpsInactivoEnviado) {
              _gpsInactivoEnviado = true
              enviarGpsInactivo()
            }
            // Recrear el watcher con Promise chain (NO setTimeout: se congela en
            // background). Throttle por timestamp para no entrar en bucle mientras
            // el GPS sigue apagado.
            const ahora = Date.now()
            if (ahora - _ultimoRecreacionBg > BG_RETRY_MS) {
              _ultimoRecreacionBg = ahora
              detenerNativo().then(() => iniciarNativo())
            }
          }
          return
        }
        if (!location) return
        procesarPosicion(location.latitude, location.longitude, location.speed)
      },
    )
    return true
  } catch {
    bgWatcherId = null
    return false
  }
}

async function detenerNativo() {
  if (bgWatcherId === null) return
  try { await BackgroundGeolocation.removeWatcher({ id: bgWatcherId }) } catch {}
  bgWatcherId = null
}

export async function abrirAjustesUbicacion() {
  try { await BackgroundGeolocation.openSettings() } catch {}
}

// ── Fallback web (navigator.geolocation) ────────────────────────────────────

function iniciarWeb() {
  if (!navigator.geolocation) return false
  webWatchId = navigator.geolocation.watchPosition(
    (pos) => {
      procesarPosicion(pos.coords.latitude, pos.coords.longitude, pos.coords.speed)
    },
    () => { /* error transitorio, no cambiar estado */ },
    { enableHighAccuracy: true, timeout: 10000 },
  )
  return true
}

function detenerWeb() {
  if (webWatchId === null) return
  navigator.geolocation.clearWatch(webWatchId)
  webWatchId = null
}

// ── Heartbeat ────────────────────────────────────────────────────────────────
// Keepalive de posición. Siempre envía vel=0: el heartbeat no sabe si el
// vehículo sigue a la misma velocidad del último fix. Los fixes reales del
// plugin llevan velocidad correcta; el throttle (THROTTLE_MS) evita que este
// cero pise los fixes mientras el vehículo está en movimiento rápido.

function _iniciarHeartbeat() {
  heartbeatTimer = setInterval(() => {
    const fresco = (Date.now() - ultimoFix) < SILENCIO_MS
    if (fresco) {
      if (!gpsActivo) { gpsActivo = true; notificarGps(true) }
      if (ultimaPos) enviarUbicacion(ultimaPos.lat, ultimaPos.lng, 0)
    } else if (!Capacitor.isNativePlatform() && gpsActivo) {
      gpsActivo = false
      notificarGps(false)
      enviarGpsInactivo()
    }
  }, HEARTBEAT_MS)
}

// ── API pública ──────────────────────────────────────────────────────────────

// Inicia el plugin brevemente para forzar el diálogo de permisos y luego
// lo detiene. Llamar antes de iniciarEnvioUbicacion para que Android muestre
// el prompt de permiso en el momento correcto (pantalla visible).
// En Android 11+ el permiso "todo el tiempo" requiere ir a Ajustes manualmente;
// esta función al menos garantiza que se pida el permiso básico y que el plugin
// quede en estado conocido antes de iniciar el rastreo real.
export async function solicitarPermisoUbicacion() {
  if (!Capacitor.isNativePlatform()) return
  let id = null
  try {
    id = await BackgroundGeolocation.addWatcher(
      { requestPermissions: true, stale: true, distanceFilter: 0 },
      () => {},
    )
  } catch { /* permisos denegados o plataforma sin soporte */ }
  if (id !== null) {
    try { await BackgroundGeolocation.removeWatcher({ id }) } catch {}
  }
}

export async function iniciarEnvioUbicacion() {
  if (bgWatcherId !== null || webWatchId !== null) return true

  if (Capacitor.isNativePlatform()) {
    const ok = await iniciarNativo()
    if (!ok) return false
  } else {
    if (!iniciarWeb()) return false
  }

  _iniciarHeartbeat()
  return true
}

export async function detenerEnvioUbicacion() {
  _ultimoRecreacionBg = 0
  _gpsInactivoEnviado = false
  gpsActivo      = false
  ultimaPos      = null
  ultimoFix      = 0
  if (heartbeatTimer) { clearInterval(heartbeatTimer); heartbeatTimer = null }
  await detenerNativo()
  detenerWeb()
}

// Reanuda al volver del segundo plano. En modo background el servicio nativo
// siguió corriendo con la pantalla bloqueada → no hace falta reiniciar.
export async function reanudarEnvioUbicacion() {
  if (bgWatcherId !== null) {
    ultimoFix = Date.now()   // margen de gracia para el primer fix al reabrir
    return
  }
  await detenerEnvioUbicacion()
  ultimoFix = Date.now()
  await iniciarEnvioUbicacion()
}
