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

export const useAuthStore = defineStore('auth', () => {
  const usuario  = ref(null)
  const cargando = ref(false)
  const error    = ref(null)

  const estaAutenticado = computed(() => !!usuario.value)
  const esConductor     = computed(() => usuario.value?.rol === 'CONDUCTOR')

  /** Restaurar sesión guardada al abrir la app */
  async function cargarSesion() {
    try {
      const { value } = await Preferences.get({ key: 'usuario' })
      usuario.value = value ? JSON.parse(value) : null
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

      // El backend retorna la clave "user"
      const userObj = data.user

      // Solo conductores pueden usar esta app
      if (userObj.rol !== 'CONDUCTOR') {
        error.value = 'Esta app es solo para conductores'
        return { success: false }
      }

      // Persistir en almacenamiento nativo
      await Preferences.set({ key: 'access_token',  value: data.access })
      await Preferences.set({ key: 'refresh_token', value: data.refresh })
      await Preferences.set({ key: 'usuario',       value: JSON.stringify(userObj) })

      usuario.value = userObj
      return { success: true, primerLogin: userObj.primer_login }
    } catch (e) {
      error.value = e.message === 'Sin conexión. Verifica tu red.'
        ? e.message
        : (e.message || 'Error al iniciar sesión. Intenta nuevamente.')
      return { success: false }
    } finally {
      cargando.value = false
    }
  }

  /** Cerrar sesión y redirigir al login */
  async function logout() {
    // Desconectar WebSocket antes de limpiar la sesión
    try {
      const { wsService } = await import('../services/websocket.js')
      wsService.disconnect()
    } catch {}

    await limpiarSesion()
    usuario.value = null
    // Importación dinámica para evitar dependencia circular con router
    const { default: router } = await import('../router/index.js')
    router.replace({ name: 'login' })
  }

  return {
    usuario,
    cargando,
    error,
    estaAutenticado,
    esConductor,
    cargarSesion,
    login,
    logout,
  }
})
