/**
 * stores/mantenciones.js — Mantenciones del vehículo asignado al conductor.
 *
 * Sincroniza con GET /api/conductor/mantenciones/
 * Expone:
 *   - mantenciones: lista de mantenciones pendientes/en proceso
 *   - vehiculoEnMantencion: bool — el vehículo está bloqueado por mantención
 *   - vehiculo: datos básicos del vehículo asignado
 *   - hayUrgente: computed — hay alguna mantención con ≤ 3 días
 *   - totalActivas: computed — cantidad de mantenciones pendientes/en proceso
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiFetch } from '@/services/api.js'

export const useMantencionesStore = defineStore('mantenciones', () => {
  // ── Estado ─────────────────────────────────────────────────────────────────
  const mantenciones          = ref([])
  const vehiculoEnMantencion  = ref(false)
  const vehiculo              = ref(null)
  const cargando              = ref(false)
  const error                 = ref(null)

  // ── Getters ────────────────────────────────────────────────────────────────
  /** True si hay al menos una mantención con ≤ 3 días o el vehículo está bloqueado */
  const hayUrgente = computed(() =>
    vehiculoEnMantencion.value ||
    mantenciones.value.some(m => m.urgente),
  )

  /** Cantidad de mantenciones activas (pendiente + en proceso) */
  const totalActivas = computed(() => mantenciones.value.length)

  // ── Acciones ───────────────────────────────────────────────────────────────
  async function cargarMantenciones() {
    cargando.value = true
    error.value    = null
    try {
      const data = await apiFetch('/api/conductor/mantenciones/')
      mantenciones.value         = data.mantenciones         || []
      vehiculoEnMantencion.value = data.vehiculo_en_mantencion ?? false
      vehiculo.value             = data.vehiculo              || null
    } catch (e) {
      error.value = e?.message || 'Sin conexión'
    } finally {
      cargando.value = false
    }
  }

  return {
    mantenciones,
    vehiculoEnMantencion,
    vehiculo,
    cargando,
    error,
    hayUrgente,
    totalActivas,
    cargarMantenciones,
  }
})
