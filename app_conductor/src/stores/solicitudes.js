/**
 * solicitudes.js — Store Pinia para las solicitudes del conductor.
 *
 * Sincroniza con GET/POST /api/conductor/solicitudes/
 * Con soporte offline: encola la acción y agrega optimistamente al estado local.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiFetch } from '@/services/api.js'
import { encolarAccion, getSolicitudes, saveSolicitudes, saveSolicitudLocal } from '@/services/db.js'

export const useSolicitudesStore = defineStore('solicitudes', () => {
  // ── Estado ─────────────────────────────────────────────────────────────────
  const solicitudes = ref([])
  const cargando    = ref(false)
  const error       = ref(null)
  const enviando    = ref(false)

  // ── Getters ────────────────────────────────────────────────────────────────
  const pendientes = computed(() =>
    solicitudes.value.filter(s => s.estado === 'pendiente' || s.estado === 'en_revision'),
  )

  const resueltas = computed(() =>
    solicitudes.value.filter(s => s.estado === 'aprobado' || s.estado === 'rechazado'),
  )

  // ── Acciones ───────────────────────────────────────────────────────────────

  async function cargarSolicitudes() {
    cargando.value = true
    error.value    = null
    try {
      const data = await apiFetch('/api/conductor/solicitudes/')
      solicitudes.value = data.solicitudes || []
      await saveSolicitudes(solicitudes.value)
    } catch (e) {
      // Offline o error de red → cargar desde SQLite
      const guardadas = await getSolicitudes()
      if (guardadas.length) solicitudes.value = guardadas
      error.value = e?.message || 'Sin conexión'
    } finally {
      cargando.value = false
    }
  }

  /**
   * Crea una solicitud nueva.
   * @param {Object} datos  - { tipo, titulo, descripcion, prioridad }
   * @param {Blob|null} foto - Blob de la imagen (puede ser null)
   * @returns {{ success: boolean, solicitud?: Object, offline?: boolean }}
   */
  async function crearSolicitud(datos, foto = null) {
    enviando.value = true
    error.value    = null
    try {
      let body
      let headers = {}

      if (foto) {
        // Con foto: multipart/form-data
        const fd = new FormData()
        Object.entries(datos).forEach(([k, v]) => fd.append(k, v))
        fd.append('foto', foto, 'foto.jpg')
        body = fd
        // No establecer Content-Type — el browser lo pone con el boundary
      } else {
        // Sin foto: JSON
        body    = JSON.stringify(datos)
        headers = { 'Content-Type': 'application/json' }
      }

      const resp = await apiFetch('/api/conductor/solicitudes/', {
        method: 'POST',
        body,
        headers: Object.keys(headers).length ? headers : undefined,
      })

      const nueva = resp.solicitud
      solicitudes.value.unshift(nueva)
      await saveSolicitudes([nueva])
      return { success: true, solicitud: nueva }

    } catch (e) {
      // Distinguir error de RED (offline real) de error de SERVIDOR (400, 500…)
      // apiFetch marca los errores de red con `isNetworkError = true`
      const esOffline = !navigator.onLine || e?.isNetworkError === true
      if (esOffline) {
        // Sin conexión → encolar y agregar optimistamente al estado local
        const solicitudLocal = {
          ...datos,
          id:         `local_${Date.now()}`,
          estado:     'pendiente',
          foto_url:   null,
          respuesta:  null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }
        solicitudes.value.unshift(solicitudLocal)
        await encolarAccion('crear_solicitud', datos)
        await saveSolicitudLocal(solicitudLocal)
        return { success: true, solicitud: solicitudLocal, offline: true }
      }
      // Error del servidor (validación, autenticación, etc.) → mostrar mensaje real
      error.value = e?.message || 'Error al enviar la solicitud'
      return { success: false, error: error.value }
    } finally {
      enviando.value = false
    }
  }

  return {
    solicitudes,
    cargando,
    error,
    enviando,
    pendientes,
    resueltas,
    cargarSolicitudes,
    crearSolicitud,
  }
})
