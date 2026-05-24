/**
 * stores/rutas.js — Store de rutas del conductor (Pinia).
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { init as initDB } from '../services/db.js'
import { cargarConFallback, iniciarSync, encolarAccion } from '../services/sync.js'
import { apiFetch } from '../services/api.js'

export const useRutasStore = defineStore('rutas', () => {
  const rutas      = ref([])
  const cargando   = ref(false)
  const error      = ref(null)
  const online     = ref(true)
  const ultimaSync = ref(null)

  // ── Computed ────────────────────────────────────────────────────────────────

  const rutaActiva = computed(() =>
    rutas.value.find(r => r.estado === 'activo') ?? null
  )

  const rutasPendientes = computed(() =>
    rutas.value
      .filter(r => r.estado === 'pendiente')
      .sort((a, b) => {
        if (!a.fecha_programada) return 1
        if (!b.fecha_programada) return -1
        return new Date(a.fecha_programada) - new Date(b.fecha_programada)
      })
  )

  const rutasFinalizadas = computed(() =>
    rutas.value
      .filter(r => r.estado === 'finalizado')
      .sort((a, b) => new Date(b.fecha_fin || 0) - new Date(a.fecha_fin || 0))
      .slice(0, 10)
  )

  // ── Acciones ────────────────────────────────────────────────────────────────

  /** Inicializar SQLite y listeners de red */
  async function init() {
    await initDB()
    await iniciarSync((conectado) => {
      online.value = conectado
    })
  }

  /** Cargar rutas (con fallback a cache si no hay conexión) */
  async function cargarRutas() {
    cargando.value = true
    error.value    = null
    try {
      const resultado = await cargarConFallback()
      rutas.value    = resultado.rutas
      online.value   = resultado.online
      ultimaSync.value = new Date().toISOString()
    } catch (e) {
      error.value = e.message || 'Error al cargar rutas'
    } finally {
      cargando.value = false
    }
  }

  /** Iniciar una ruta — encola si no hay conexión */
  async function iniciarRuta(id, kmInicio) {
    const payload = {
      url:    `/api/conductor/rutas/${id}/iniciar/`,
      method: 'POST',
      body:   { km_inicio: kmInicio },
    }
    try {
      const data = await apiFetch(payload.url, {
        method: payload.method,
        body:   JSON.stringify(payload.body),
      })
      // Actualizar estado local inmediatamente
      const idx = rutas.value.findIndex(r => r.id === id)
      if (idx > -1) rutas.value[idx] = data.ruta
    } catch (e) {
      if (e.message.includes('Sin conexión')) {
        // Optimistic update local
        const idx = rutas.value.findIndex(r => r.id === id)
        if (idx > -1) {
          rutas.value[idx] = { ...rutas.value[idx], estado: 'activo', km_inicio: kmInicio }
        }
        await encolarAccion('iniciar_ruta', payload)
      } else {
        throw e
      }
    }
  }

  /** Finalizar una ruta — encola si no hay conexión */
  async function finalizarRuta(id, datos) {
    const payload = {
      url:    `/api/conductor/rutas/${id}/finalizar/`,
      method: 'POST',
      body:   datos,
    }
    try {
      const data = await apiFetch(payload.url, {
        method: payload.method,
        body:   JSON.stringify(payload.body),
      })
      const idx = rutas.value.findIndex(r => r.id === id)
      if (idx > -1) rutas.value[idx] = data.ruta
    } catch (e) {
      if (e.message.includes('Sin conexión')) {
        const idx = rutas.value.findIndex(r => r.id === id)
        if (idx > -1) {
          rutas.value[idx] = { ...rutas.value[idx], estado: 'finalizado', ...datos }
        }
        await encolarAccion('finalizar_ruta', payload)
      } else {
        throw e
      }
    }
  }

  return {
    rutas,
    cargando,
    error,
    online,
    ultimaSync,
    rutaActiva,
    rutasPendientes,
    rutasFinalizadas,
    init,
    cargarRutas,
    iniciarRuta,
    finalizarRuta,
  }
})
