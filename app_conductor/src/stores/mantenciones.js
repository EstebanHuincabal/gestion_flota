/**
 * stores/mantenciones.js — Mantenciones del vehículo asignado al conductor.
 *
 * Endpoints:
 *   GET  /api/conductor/mantenciones/               → lista (pendiente + en_proceso)
 *   GET  /api/conductor/mantenciones/:id/           → detalle completo
 *   POST /api/conductor/mantenciones/:id/iniciar/   → pendiente → en_proceso
 *   POST /api/conductor/mantenciones/:id/completar/ → en_proceso → realizada + GastoOperativo
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiFetch } from '@/services/api.js'

export const useMantencionesStore = defineStore('mantenciones', () => {
  // ── Estado ─────────────────────────────────────────────────────────────────
  const mantenciones         = ref([])
  const vehiculoEnMantencion = ref(false)
  const vehiculo             = ref(null)
  const cargando             = ref(false)
  const error                = ref(null)

  // ── Getters ────────────────────────────────────────────────────────────────

  /** True si hay urgente (≤ 3 días) o el vehículo está bloqueado */
  const hayUrgente = computed(() =>
    vehiculoEnMantencion.value ||
    mantenciones.value.some(m => m.urgente),
  )

  /** Cantidad de mantenciones activas (pendiente + en_proceso) */
  const totalActivas = computed(() => mantenciones.value.length)

  // ── Acciones ───────────────────────────────────────────────────────────────

  async function cargarMantenciones() {
    cargando.value = true
    error.value    = null
    try {
      const data = await apiFetch('/api/conductor/mantenciones/')
      mantenciones.value         = data.mantenciones          || []
      vehiculoEnMantencion.value = data.vehiculo_en_mantencion ?? false
      vehiculo.value             = data.vehiculo               || null
    } catch (e) {
      error.value = e?.message || 'Sin conexión'
    } finally {
      cargando.value = false
    }
  }

  /** Detalle completo de una mantención (con foto URL). No modifica el store. */
  async function obtenerDetalle(id) {
    return await apiFetch(`/api/conductor/mantenciones/${id}/`)
  }

  /** Conductor inicia la mantención: pendiente → en_proceso */
  async function iniciarMantencion(id) {
    const data = await apiFetch(`/api/conductor/mantenciones/${id}/iniciar/`, {
      method: 'POST',
    })
    _actualizarLocal(data.mantencion)
    vehiculoEnMantencion.value = true
    return data.mantencion
  }

  /**
   * Conductor completa la mantención: en_proceso → realizada.
   * @param {number} id
   * @param {FormData} formData  — campos: costo_final, foto_comprobante?, fecha_realizada?, notas?
   */
  async function completarMantencion(id, formData) {
    const data = await apiFetch(`/api/conductor/mantenciones/${id}/completar/`, {
      method: 'POST',
      body:   formData,         // apiFetch detecta FormData y no serializa a JSON
    })
    // La mantención ya está realizada → sacarla de la lista activa
    mantenciones.value = mantenciones.value.filter(m => m.id !== id)
    vehiculoEnMantencion.value = false
    return data
  }

  /** Actualiza un ítem en el array local sin recargar todo */
  function _actualizarLocal(mantencionActualizada) {
    const idx = mantenciones.value.findIndex(m => m.id === mantencionActualizada.id)
    if (idx !== -1) {
      mantenciones.value[idx] = mantencionActualizada
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
    obtenerDetalle,
    iniciarMantencion,
    completarMantencion,
  }
})
