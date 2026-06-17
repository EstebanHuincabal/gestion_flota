/**
 * services/api.js — Cliente HTTP centralizado de la app de conductores.
 *
 * - Agrega Authorization: Bearer automáticamente
 * - Timeout de 15 segundos con AbortController
 * - Reintenta con refresh token si recibe 401
 * - Limpia la sesión y lanza 'SESION_EXPIRADA' si el refresh falla
 * - Lanza Error con mensaje legible en cualquier otro error HTTP
 */
import { Preferences } from '@capacitor/preferences'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TIMEOUT_MS = 15_000

export async function apiFetch(url, options = {}) {
  const { value: token } = await Preferences.get({ key: 'access_token' })

  const headers = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    'X-App-Platform': 'capacitor',
    ...options.headers,
  }

  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)

  let res
  try {
    res = await fetch(`${BASE_URL}${url}`, { ...options, headers, signal: controller.signal })
  } catch (fetchErr) {
    clearTimeout(timer)
    if (fetchErr.name === 'AbortError') {
      const err = new Error('La petición tardó demasiado. Verifica tu conexión.')
      err.isNetworkError = true
      throw err
    }
    // El fetch falla tanto sin internet del dispositivo como con el servidor caído:
    // no se distinguen desde el cliente, así que el mensaje no culpa solo a la red.
    const err = new Error('No se pudo conectar con el servidor. Verifica tu conexión o intenta más tarde.')
    err.isNetworkError = true
    throw err
  }
  clearTimeout(timer)

  // Token expirado → intentar refresh y reintentar una vez
  // NO aplicar a /api/login/ — ese 401 significa credenciales inválidas, no token expirado
  if (res.status === 401 && !url.includes('/api/login/')) {
    const refreshed = await intentarRefresh()
    if (refreshed) {
      const { value: newToken } = await Preferences.get({ key: 'access_token' })
      const ctrl2  = new AbortController()
      const timer2 = setTimeout(() => ctrl2.abort(), TIMEOUT_MS)
      try {
        const retryRes = await fetch(`${BASE_URL}${url}`, {
          ...options,
          headers: { ...headers, Authorization: `Bearer ${newToken}` },
          signal: ctrl2.signal,
        })
        clearTimeout(timer2)
        if (!retryRes.ok) {
          // El token se renovó pero la cuenta ya no tiene acceso (desactivada/bloqueada)
          if (retryRes.status === 401) await limpiarSesion()
          const errData = await retryRes.json().catch(() => ({}))
          throw new Error(errData.error || errData.detail || 'Sesión expirada')
        }
        return retryRes.json().catch(() => ({}))
      } catch (e) {
        clearTimeout(timer2)
        if (e.name === 'AbortError') throw new Error('La petición tardó demasiado. Verifica tu conexión.')
        throw e
      }
    }
    await limpiarSesion()
    throw new Error('SESION_EXPIRADA')
  }

  // Suscripción bloqueada → emitir evento global (no durante el login)
  if (res.status === 402) {
    let errData = {}
    try { errData = await res.json() } catch {}
    if (errData.codigo === 'SUSCRIPCION_BLOQUEADA' && !url.includes('/api/login/')) {
      window.dispatchEvent(new CustomEvent('suscripcion-bloqueada', {
        detail: { mensaje: errData.error, estado: errData.estado },
      }))
    }
    throw new Error(errData.error || 'Suscripción bloqueada')
  }

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}))
    // Empresa desactivada por el SUPERADMIN → mostrar pantalla de bloqueo con el
    // motivo (mismo mecanismo que la suscripción bloqueada). No se expulsa de
    // golpe: el conductor lee el mensaje y cierra sesión desde ahí.
    // En el login NO se dispara el sheet: el error se muestra en el formulario.
    if (res.status === 403 && errData.codigo === 'EMPRESA_DESACTIVADA' && !url.includes('/api/login/')) {
      window.dispatchEvent(new CustomEvent('empresa-desactivada', {
        detail: { mensaje: errData.error },
      }))
    }
    const err = new Error(errData.error || errData.detail || `Error ${res.status}`)
    err.status = res.status
    err.codigo = errData.codigo || null
    throw err
  }

  return res.json().catch(() => ({}))
}

async function intentarRefresh() {
  try {
    const { value: refresh } = await Preferences.get({ key: 'refresh_token' })
    if (!refresh) return false
    const res = await fetch(`${BASE_URL}/api/token/refresh/`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ refresh }),
    })
    if (!res.ok) return false
    const data = await res.json().catch(() => null)
    if (!data?.access) return false
    await Preferences.set({ key: 'access_token', value: data.access })
    if (data.refresh) await Preferences.set({ key: 'refresh_token', value: data.refresh })
    return true
  } catch {
    return false
  }
}

export async function limpiarSesion() {
  await Preferences.remove({ key: 'access_token' })
  await Preferences.remove({ key: 'refresh_token' })
  await Preferences.remove({ key: 'usuario' })
  await Preferences.remove({ key: 'plan_modulos' })
  await Preferences.remove({ key: 'plan_nombre' })
  // Avisar a la app para que expulse al usuario al login en tiempo real
  try {
    window.dispatchEvent(new CustomEvent('sesion-expirada'))
  } catch {}
}
