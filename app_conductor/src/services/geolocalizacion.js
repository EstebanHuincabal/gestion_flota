import { Geolocation } from '@capacitor/geolocation'
import { Network }     from '@capacitor/network'
import { apiFetch }    from './api.js'
import { wsService }   from './websocket.js'

let watchId       = null   // ID de watchPosition activo
let ultimoEnvio   = 0      // timestamp del último envío (throttle)
const THROTTLE_MS = 3000   // mínimo 3s entre envíos aunque haya movimiento

async function enviarUbicacion(lat, lng, vel) {
  const ahora = Date.now()
  if (ahora - ultimoEnvio < THROTTLE_MS) return
  ultimoEnvio = ahora

  const payload = {
    latitud:   lat,
    longitud:  lng,
    velocidad: vel,
  }

  // Canal principal: WebSocket (tiempo real, sin round-trip HTTP)
  const enviado = wsService.send({ tipo: 'ubicacion_update', ...payload })

  // Fallback REST: si el WebSocket no está conectado, guardar igual en BD
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

export async function iniciarEnvioUbicacion() {
  if (watchId !== null) return true   // ya corriendo

  const permiso = await Geolocation.requestPermissions()
  if (permiso.location !== 'granted') return false

  // Primera posición inmediata
  try {
    const pos = await Geolocation.getCurrentPosition({ enableHighAccuracy: true, timeout: 10000 })
    await enviarUbicacion(
      pos.coords.latitude,
      pos.coords.longitude,
      (pos.coords.speed || 0) * 3.6,
      0,
    )
  } catch { /* sin señal inicial — seguirá con watchPosition */ }

  // watchPosition: dispara en cada cambio de posición del SO (tiempo real)
  watchId = await Geolocation.watchPosition(
    { enableHighAccuracy: true, timeout: 10000 },
    (pos, err) => {
      if (err || !pos) return
      enviarUbicacion(
        pos.coords.latitude,
        pos.coords.longitude,
        (pos.coords.speed || 0) * 3.6,
        0,
      )
    },
  )

  return true
}

export async function detenerEnvioUbicacion() {
  if (watchId !== null) {
    await Geolocation.clearWatch({ id: watchId })
    watchId = null
  }
}
