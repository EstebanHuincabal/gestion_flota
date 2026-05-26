/**
 * services/api.js — Cliente HTTP centralizado de la app de conductores.
 *
 * Todas las llamadas al backend pasan por apiFetch().
 * - Agrega Authorization: Bearer automáticamente
 * - Reintenta con refresh token si recibe 401
 * - Limpia la sesión y lanza 'SESION_EXPIRADA' si el refresh falla
 * - Lanza Error con mensaje legible en cualquier otro error HTTP
 */
import { Preferences } from '@capacitor/preferences'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function apiFetch(url, options = {}) {
  const { value: token } = await Preferences.get({ key: 'access_token' })

  const headers = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  // Solo añadir Content-Type JSON si el body NO es FormData.
  // Para FormData el browser lo fija automáticamente con el boundary correcto;
  // si lo ponemos a mano el servidor no puede parsear el multipart.
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  let res
  try {
    res = await fetch(`${BASE_URL}${url}`, { ...options, headers })
  } catch {
    // Error de red puro (sin conexión, DNS, timeout…)
    const err = new Error('Sin conexión. Verifica tu red.')
    err.isNetworkError = true
    throw err
  }

  // Token expirado → intentar refresh y reintentar una vez
  if (res.status === 401) {
    const refreshed = await intentarRefresh()
    if (refreshed) {
      const { value: newToken } = await Preferences.get({ key: 'access_token' })
      try {
        const retryRes = await fetch(`${BASE_URL}${url}`, {
          ...options,
          headers: { ...headers, Authorization: `Bearer ${newToken}` },
        })
        if (!retryRes.ok) throw new Error('Sesión expirada')
        return retryRes.json()
      } catch {
        throw new Error('Sesión expirada')
      }
    }
    await limpiarSesion()
    throw new Error('SESION_EXPIRADA')
  }

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}))
    throw new Error(errData.error || errData.detail || 'Error del servidor')
  }

  return res.json()
}

async function intentarRefresh() {
  try {
    const { value: refresh } = await Preferences.get({ key: 'refresh_token' })
    if (!refresh) return false
    const res = await fetch(`${BASE_URL}/api/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
    if (!res.ok) return false
    const data = await res.json()
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
}
