/**
 * stores/auth.js — Store de autenticación (Pinia)
 *
 * Gestiona el ciclo completo de sesión del conductor:
 *  - cargarSesion(): restaura estado desde Preferences al iniciar la app
 *  - login(): POST /api/login/ + guarda tokens
 *  - logout(): limpia todo y redirige al login
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { Preferences } from '@capacitor/preferences'
import { apiFetch, limpiarSesion } from '../services/api.js'
import { resetearPermisos } from '../composables/usePermisos.js'

export const useAuthStore = defineStore('auth', () => {
  const usuario  = ref(null)
  const cargando = ref(false)

  /**
   * Objeto de error estructurado:
   *  { tipo, mensaje }
   *
   *  tipos:
   *   'credenciales'  → RUT o contraseña incorrectos
   *   'bloqueado'     → Cuenta bloqueada por intentos fallidos
   *   'sin_conexion'  → Sin red o timeout
   *   'servidor'      → Error 5xx del backend
   *   'no_conductor'  → Usuario no es CONDUCTOR
   *   'desconocido'   → Cualquier otro error
   */
  const error = ref(null)

  const estaAutenticado = computed(() => !!usuario.value)
  const esConductor     = computed(() => usuario.value?.rol === 'CONDUCTOR')

  function limpiarError() {
    error.value = null
  }

  /** Restaurar sesión guardada al abrir la app */
  async function cargarSesion() {
    try {
      const { value } = await Preferences.get({ key: 'usuario' })
      if (!value) { usuario.value = null; return }
      const parsed = JSON.parse(value)
      usuario.value = (parsed && typeof parsed === 'object' && parsed.rol) ? parsed : null
    } catch {
      usuario.value = null
    }
  }

  /**
   * Iniciar sesión con RUT y contraseña.
   * @returns {{ success: boolean, primerLogin?: boolean }}
   */
  async function login(rut, password) {
    cargando.value = true
    error.value    = null
    try {
      const data = await apiFetch('/api/login/', {
        method: 'POST',
        body: JSON.stringify({ rut, password }),
      })

      const userObj = data?.user
      if (!userObj || typeof userObj !== 'object') {
        error.value = { tipo: 'servidor', mensaje: 'Respuesta inesperada del servidor. Intenta nuevamente.' }
        return { success: false }
      }

      if (userObj.rol !== 'CONDUCTOR') {
        error.value = { tipo: 'no_conductor', mensaje: 'Esta app es exclusiva para conductores. Usa el panel web.' }
        return { success: false }
      }

      await Preferences.set({ key: 'access_token',  value: data.access  })
      await Preferences.set({ key: 'refresh_token', value: data.refresh })
      await Preferences.set({ key: 'usuario',       value: JSON.stringify(userObj) })
      await Preferences.set({ key: 'plan_modulos',  value: JSON.stringify(userObj.plan_modulos || []) })
      await Preferences.set({ key: 'plan_nombre',   value: userObj.plan_nombre || '' })

      usuario.value = userObj
      return { success: true, primerLogin: userObj.primer_login }

    } catch (e) {
      error.value = _clasificarError(e)
      return { success: false }
    } finally {
      cargando.value = false
    }
  }

  /** Clasifica un error de apiFetch en un objeto { tipo, mensaje } */
  function _clasificarError(e) {
    // Sin conexión o timeout
    if (e.isNetworkError) {
      const esTimeout = e.message?.includes('tardó demasiado')
      return {
        tipo:    'sin_conexion',
        mensaje: esTimeout
          ? 'El servidor tardó demasiado en responder. Verifica tu conexión e intenta nuevamente.'
          : 'Sin conexión a Internet. Verifica tu red e intenta nuevamente.',
      }
    }

    // Error HTTP con status adjunto
    if (e.status === 401) {
      return { tipo: 'credenciales', mensaje: 'RUT o contraseña incorrectos. Verifica tus datos.' }
    }
    if (e.status === 403) {
      return {
        tipo:    'bloqueado',
        mensaje: e.message || 'Tu cuenta está bloqueada por exceso de intentos fallidos. Contacta al administrador.',
      }
    }
    if (e.status >= 500) {
      return { tipo: 'servidor', mensaje: 'El servidor no está disponible. Intenta en unos minutos.' }
    }
    if (e.status === 400) {
      return { tipo: 'credenciales', mensaje: e.message || 'Datos inválidos. Verifica tu RUT y contraseña.' }
    }

    // Error de sesión expirada (inesperado en login)
    if (e.message === 'SESION_EXPIRADA') {
      return { tipo: 'servidor', mensaje: 'Error de autenticación. Intenta nuevamente.' }
    }

    return { tipo: 'desconocido', mensaje: e.message || 'Error al iniciar sesión. Intenta nuevamente.' }
  }

  /** Cerrar sesión y redirigir al login */
  async function logout() {
    try {
      const { wsService } = await import('../services/websocket.js')
      wsService.disconnect()
    } catch {}

    await resetearPermisos()
    await limpiarSesion()
    usuario.value = null
    error.value   = null
    const { default: router } = await import('../router/index.js')
    router.replace({ name: 'login' })
  }

  /**
   * Expira la sesión por una señal del servidor (cuenta desactivada/bloqueada).
   * No llama limpiarSesion porque api.js ya borró las credenciales; solo
   * resetea el estado local y redirige al login para evitar un bucle.
   */
  async function expirarSesion() {
    if (!usuario.value) return   // ya cerrada → evitar redirects repetidos
    try {
      const { wsService } = await import('../services/websocket.js')
      wsService.disconnect()
    } catch {}
    await resetearPermisos()
    usuario.value = null
    const { default: router } = await import('../router/index.js')
    if (router.currentRoute.value.name !== 'login') {
      router.replace({ name: 'login' })
    }
  }

  return {
    usuario,
    cargando,
    error,
    estaAutenticado,
    esConductor,
    limpiarError,
    cargarSesion,
    login,
    logout,
    expirarSesion,
  }
})
