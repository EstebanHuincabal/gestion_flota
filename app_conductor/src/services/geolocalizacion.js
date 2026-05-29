import { Capacitor }   from '@capacitor/core'
import { Geolocation } from '@capacitor/geolocation'
import { Network }     from '@capacitor/network'
import { apiFetch }    from './api.js'
import { wsService }   from './websocket.js'

let watchId       = null
let ultimoEnvio   = 0
let reintentando  = false
let _onGpsChange  = null   // callback(activo: boolean) para notificar cambios de estado GPS
const THROTTLE_MS = 3000
const RETRY_MS    = 5000

export function onGpsStateChange(cb) { _onGpsChange = cb }
function notificarGps(activo) { if (_onGpsChange) _onGpsChange(activo) }

async function enviarUbicacion(lat, lng, vel) {
  const ahora = Date.now()
  if (ahora - ultimoEnvio < THROTTLE_MS) return
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

async function crearWatcher() {
  watchId = await Geolocation.watchPosition(
    { enableHighAccuracy: true, timeout: 10000 },
    async (pos, err) => {
      if (err) {
        if (err.code === 2 || err.code === 3) {
          notificarGps(false)   // GPS apagado → avisar al banner
          await _reiniciarWatcher()
        }
        return
      }
      if (!pos) return
      notificarGps(true)   // GPS activo → quitar banner
      await enviarUbicacion(
        pos.coords.latitude,
        pos.coords.longitude,
        (pos.coords.speed || 0) * 3.6,
      )
    },
  )
}

async function _reiniciarWatcher() {
  if (reintentando) return
  reintentando = true

  // Limpiar watcher muerto
  if (watchId !== null) {
    try { await Geolocation.clearWatch({ id: watchId }) } catch {}
    watchId = null
  }

  // Esperar y volver a intentar hasta que el GPS responda
  setTimeout(async () => {
    reintentando = false
    if (watchId !== null) return   // ya fue reiniciado por otra ruta
    try {
      await crearWatcher()
    } catch {
      // Si aún falla, volvemos a intentar
      await _reiniciarWatcher()
    }
  }, RETRY_MS)
}

export async function iniciarEnvioUbicacion() {
  if (watchId !== null) return true

  if (Capacitor.isNativePlatform()) {
    try {
      const permisos = await Geolocation.requestPermissions()
      const ok = permisos.location === 'granted' || permisos.coarseLocation === 'granted'
      if (!ok) return false
    } catch { return false }
  } else {
    if (!navigator.geolocation) return false
  }

  // Primera posición inmediata
  try {
    const pos = await Geolocation.getCurrentPosition({ enableHighAccuracy: true, timeout: 8000 })
    await enviarUbicacion(pos.coords.latitude, pos.coords.longitude, (pos.coords.speed || 0) * 3.6)
  } catch { /* sin señal inicial */ }

  await crearWatcher()
  return true
}

export async function detenerEnvioUbicacion() {
  reintentando = false
  if (watchId === null) return
  try { await Geolocation.clearWatch({ id: watchId }) } catch {}
  watchId = null
}
