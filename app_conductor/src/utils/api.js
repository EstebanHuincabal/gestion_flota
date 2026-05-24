/**
 * api.js — Cliente HTTP para la app de conductores.
 *
 * Equivalente exacto a gestion-frontend/src/utils/api.js pero adaptado a móvil:
 *  - Tokens en @capacitor/preferences (via storage.js) en lugar de localStorage
 *  - VITE_API_BASE_URL como prefijo de todas las URLs
 *  - Redirige al router de Vue en lugar de window.location.href
 *
 * Flujo:
 *  1. Agrega Authorization: Bearer <access_token> a cada request
 *  2. Si el server responde 401 → intenta refrescar el token
 *  3. Si el refresh falla → limpia sesión y redirige a /login
 */
import { getItem, setItem, clearSession } from './storage.js'
import router from '../router/index.js'

// En desarrollo: '' (usa proxy de Vite) o 'http://10.0.2.2:8000' para emulador Android
// En producción: URL completa del servidor Django
const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

function getAccessToken() {
  return getItem('access_token') || ''
}

async function refreshAccessToken() {
  const refresh = getItem('refresh_token')
  if (!refresh) return false
  try {
    const res = await fetch(`${BASE_URL}/api/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
    if (res.ok) {
      const data = await res.json()
      await setItem('access_token', data.access)
      if (data.refresh) await setItem('refresh_token', data.refresh)
      return true
    }
  } catch {}
  return false
}

async function limpiarSesion() {
  await clearSession()
  router.replace({ name: 'login' })
}

/**
 * apiFetch(url, options)
 *
 * @param {string} url    - Path relativo, ej: '/api/conductor/rutas/'
 * @param {object} options - Opciones fetch: method, body (objeto JS), headers, etc.
 */
export async function apiFetch(url, options = {}) {
  const fullUrl = `${BASE_URL}${url}`
  const headers = { ...(options.headers || {}) }

  const token = getAccessToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  // Serializar body automáticamente si no es FormData
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(options.body)
  }

  let response = await fetch(fullUrl, { ...options, headers })

  // Token expirado → refresh y reintentar una vez
  if (
    response.status === 401 &&
    !url.includes('/api/login/') &&
    !url.includes('/api/token/')
  ) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      headers['Authorization'] = `Bearer ${getAccessToken()}`
      response = await fetch(fullUrl, { ...options, headers })
    } else {
      await limpiarSesion()
      return response
    }
  }

  return response
}
