/**
 * solicitudes.js — Store Pinia para las solicitudes del conductor.
 *
 * Sincroniza con GET/POST /api/conductor/solicitudes/
 * Con soporte offline: encola la acción y agrega optimistamente al estado local.
 *
 * tipos_permitidos: lista de tipos habilitados por el plan de la empresa.
 * Si el plan no incluye un tipo, el conductor no puede crear solicitudes de ese tipo.
 *
 * Tiempo real: conecta al WebSocket `ws/conductor/` para recibir cambios de
 * estado (aprobado / rechazado) sin necesidad de hacer polling.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiFetch } from '@/services/api.js'
import { wsService } from '@/services/websocket.js'
import { encolarAccion, getSolicitudes, saveSolicitudes, saveSolicitudLocal } from '@/services/db.js'

// Todos los tipos posibles — se usan como fallback cuando no hay respuesta del servidor
const TODOS_LOS_TIPOS = ['mantencion', 'combustible', 'incidencia']

export const useSolicitudesStore = defineStore('solicitudes', () => {
  // ── Estado ─────────────────────────────────────────────────────────────────
  const solicitudes     = ref([])
  const cargando        = ref(false)
  const error           = ref(null)
  const enviando        = ref(false)
  let   _cargandoId     = 0   // para cancelar requests concurrentes
  /**
   * Tipos de solicitud habilitados por el plan de la empresa.
   * null = aún no cargados (mostrar todos mientras tanto).
   * []   = sin permiso para ningún tipo.
   */
  const tiposPermitidos = ref(null)

  /**
   * Indica si llegó un cambio de estado via WebSocket que aún no ha visto
   * el usuario (para animar la tarjeta actualizada).
   * Contiene el id de la solicitud recién actualizada, o null.
   */
  const actualizadaId = ref(null)

  // ── Getters ────────────────────────────────────────────────────────────────
  const pendientes = computed(() =>
    solicitudes.value.filter(s => s.estado === 'pendiente' || s.estado === 'en_revision'),
  )

  const resueltas = computed(() =>
    solicitudes.value.filter(s => s.estado === 'aprobado' || s.estado === 'rechazado'),
  )

  /** Devuelve true si el tipo dado está habilitado por el plan */
  function esTipoPermitido(tipo) {
    if (tiposPermitidos.value === null) return true   // cargando → no bloquear
    return tiposPermitidos.value.includes(tipo)
  }

  // ── WebSocket — tiempo real ────────────────────────────────────────────────

  let _wsUnsub = null   // función para cancelar el handler registrado

  function _iniciarWs() {
    // Evitar registrar múltiples handlers si se llama varias veces
    if (_wsUnsub) _wsUnsub()

    _wsUnsub = wsService.on('solicitud_actualizada', (data) => {
      const idx = solicitudes.value.findIndex(s => s.id === data.solicitud_id)
      if (idx !== -1) {
        // Actualización inmutable en el array reactivo
        solicitudes.value[idx] = {
          ...solicitudes.value[idx],
          estado:    data.estado,
          respuesta: data.respuesta ?? solicitudes.value[idx].respuesta,
        }
        // Marcar para animar la tarjeta
        actualizadaId.value = data.solicitud_id
        setTimeout(() => { actualizadaId.value = null }, 3000)
      }
    })

    // Conectar WebSocket (no hace nada si ya está activo)
    wsService.connect()
  }

  function detenerWs() {
    if (_wsUnsub) {
      _wsUnsub()
      _wsUnsub = null
    }
    wsService.disconnect()
  }

  // ── Acciones ───────────────────────────────────────────────────────────────

  async function cargarSolicitudes() {
    // Cancelar carga previa si aún está pendiente (race condition pull-to-refresh)
    const miId = ++_cargandoId
    cargando.value = true
    error.value    = null
    try {
      const data = await apiFetch('/api/conductor/solicitudes/')
      // Si ya hay una carga más reciente iniciada, descartar este resultado
      if (miId !== _cargandoId) return
      solicitudes.value = Array.isArray(data.solicitudes) ? data.solicitudes : []
      tiposPermitidos.value = Array.isArray(data.tipos_permitidos)
        ? data.tipos_permitidos
        : TODOS_LOS_TIPOS
      await saveSolicitudes(solicitudes.value)
    } catch (e) {
      if (miId !== _cargandoId) return
      // Offline o error de red → cargar desde SQLite
      const guardadas = await getSolicitudes()
      if (guardadas.length) solicitudes.value = guardadas
      if (tiposPermitidos.value === null) tiposPermitidos.value = TODOS_LOS_TIPOS
      error.value = e?.message || 'Sin conexión'
    } finally {
      if (miId === _cargandoId) cargando.value = false
      _iniciarWs()
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
      // Validar tamaño de foto: máximo 10 MB
      if (foto && foto.size > 10 * 1024 * 1024) {
        error.value = 'La foto no puede superar los 10 MB. Elige una imagen más pequeña.'
        return { success: false, error: error.value }
      }

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

        // Serializar la foto como base64 para sobrevivir en la cola SQLite
        let fotoBase64 = null
        if (foto) {
          try {
            fotoBase64 = await new Promise((resolve, reject) => {
              const reader = new FileReader()
              reader.onload  = () => resolve(reader.result.split(',')[1])
              reader.onerror = reject
              reader.readAsDataURL(foto)
            })
          } catch {
            fotoBase64 = null
          }
        }

        await encolarAccion('crear_solicitud', {
          url:       '/api/conductor/solicitudes/',
          method:    'POST',
          body:      datos,
          fotoBase64,
        })
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
    tiposPermitidos,
    actualizadaId,
    pendientes,
    resueltas,
    esTipoPermitido,
    cargarSolicitudes,
    crearSolicitud,
    detenerWs,
  }
})
