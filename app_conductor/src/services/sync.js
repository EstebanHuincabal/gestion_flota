/**
 * sync.js — Motor de sincronización online/offline.
 *
 * Comportamiento:
 *  - Con conexión:  fetch backend → guardar en SQLite → retornar datos frescos
 *  - Sin conexión:  leer SQLite   → retornar datos cacheados
 *  - Al reconectar: procesar cola de acciones pendientes en orden
 *
 * Fotos offline: se serializan como base64 en el payload y se reconstruyen
 * como Blob al momento de sincronizar, para sobrevivir entre sesiones.
 */
import { Network } from '@capacitor/network'
import { apiFetch } from './api.js'
import { getRutas, saveRutas, getPendientes, encolarAccion as _encolarDB, eliminarPendiente } from './db.js'

export { encolarAccion }

// ── Listener de red ───────────────────────────────────────────────────────────

export async function iniciarSync(onStatusChange) {
  Network.addListener('networkStatusChange', async (status) => {
    onStatusChange?.(status.connected)
    if (status.connected) {
      await _procesarPendientes()
    }
  })
}

// ── Carga con fallback ────────────────────────────────────────────────────────

export async function cargarConFallback() {
  let status
  try {
    status = await Network.getStatus()
  } catch {
    status = { connected: false }
  }

  if (status.connected) {
    try {
      const data  = await apiFetch('/api/conductor/rutas/')
      const rutas = Array.isArray(data.rutas) ? data.rutas : []
      await saveRutas(rutas)
      return { rutas, online: true }
    } catch {
      // Falló aunque había red → usar cache
    }
  }

  const rutas = await getRutas()
  return { rutas, online: false }
}

// ── Cola de acciones offline ──────────────────────────────────────────────────

/**
 * Encola una acción y la intenta enviar de inmediato si hay conexión.
 * @param {string} tipo     ej: 'iniciar_ruta'
 * @param {object} payload  { url, method, body, fotoBase64? }
 */
async function encolarAccion(tipo, payload) {
  await _encolarDB(tipo, payload)

  let status
  try {
    status = await Network.getStatus()
  } catch {
    status = { connected: false }
  }

  if (status.connected) {
    await _procesarPendientes()
  }
}

// ── Procesamiento de la cola ──────────────────────────────────────────────────

async function _procesarPendientes() {
  const pendientes = await getPendientes()
  for (const accion of pendientes) {
    try {
      const p = accion.payload || {}

      // Si el payload tiene foto en base64, reconstruir el FormData
      if (p.fotoBase64) {
        const bytes = Uint8Array.from(atob(p.fotoBase64), c => c.charCodeAt(0))
        const blob  = new Blob([bytes], { type: 'image/jpeg' })
        const fd    = new FormData()
        if (p.body && typeof p.body === 'object') {
          Object.entries(p.body).forEach(([k, v]) => fd.append(k, v))
        }
        fd.append('foto', blob, 'foto.jpg')
        await apiFetch(p.url, { method: p.method || 'POST', body: fd })
      } else {
        await apiFetch(p.url, {
          method: p.method || 'POST',
          body:   JSON.stringify(p.body || {}),
        })
      }

      await eliminarPendiente(accion.id)
    } catch {
      // Se reintentará en la próxima reconexión
    }
  }
}
