/**
 * sync.js — Motor de sincronización online/offline.
 *
 * Comportamiento:
 *  - Con conexión:  fetch backend → guardar en SQLite → retornar datos frescos
 *  - Sin conexión:  leer SQLite   → retornar datos cacheados
 *  - Al reconectar: procesar cola de acciones pendientes en orden
 */
import { Network } from '@capacitor/network'
import { apiFetch } from './api.js'
import { getRutas, saveRutas, getPendientes, encolarAccion as _encolarDB, eliminarPendiente } from './db.js'

export { encolarAccion }

// ── Listener de red ───────────────────────────────────────────────────────────

/**
 * Inicia el listener de cambios de red.
 * @param {(online: boolean) => void} onStatusChange  callback al cambiar red
 */
export async function iniciarSync(onStatusChange) {
  Network.addListener('networkStatusChange', async (status) => {
    onStatusChange?.(status.connected)
    if (status.connected) {
      await _procesarPendientes()
    }
  })
}

// ── Carga con fallback ────────────────────────────────────────────────────────

/**
 * Intenta cargar rutas del backend; si falla (sin red) usa la cache SQLite.
 * @returns {{ rutas: Array, online: boolean }}
 */
export async function cargarConFallback() {
  const status = await Network.getStatus()

  if (status.connected) {
    try {
      const data  = await apiFetch('/api/conductor/rutas/')
      const rutas = data.rutas || []
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
 * @param {object} payload  { url, method, body }
 */
async function encolarAccion(tipo, payload) {
  await _encolarDB(tipo, payload)

  const status = await Network.getStatus()
  if (status.connected) {
    await _procesarPendientes()
  }
}

// ── Procesamiento de la cola ──────────────────────────────────────────────────

async function _procesarPendientes() {
  const pendientes = await getPendientes()
  for (const accion of pendientes) {
    try {
      await apiFetch(accion.payload.url, {
        method: accion.payload.method || 'POST',
        body:   JSON.stringify(accion.payload.body || {}),
      })
      await eliminarPendiente(accion.id)
    } catch {
      // Se reintentará en la próxima reconexión
    }
  }
}
