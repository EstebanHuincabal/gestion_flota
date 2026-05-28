export class ApiError extends Error {
  constructor(message, status, codigo) {
    super(message)
    this.status = status
    this.codigo = codigo
  }
}

export function safeJsonParse(str, fallback) {
  try { return JSON.parse(str) } catch { return fallback }
}

function getAccessToken() {
  return localStorage.getItem('access_token') || ''
}

async function refreshAccessToken() {
  const refresh = localStorage.getItem('refresh_token')
  if (!refresh) return false
  try {
    const res = await fetch('/api/token/refresh/', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ refresh }),
    })
    if (res.ok) {
      const data = await res.json()
      localStorage.setItem('access_token', data.access)
      if (data.refresh) localStorage.setItem('refresh_token', data.refresh)
      return true
    }
  } catch {}
  return false
}

function limpiarSesion() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('usuario')
  sessionStorage.removeItem('plan_modulos')
  sessionStorage.removeItem('plan_nombre')
  sessionStorage.removeItem('empresaActiva')
  sessionStorage.removeItem('plan_permisos')
  window.location.href = '/login'
}

// Retorna la Response original (retrocompatible) con timeout y safeJsonParse internos.
// Lanza ApiError solo en caso de abort/red caída.
export async function apiFetch(url, options = {}) {
  const controller = new AbortController()
  const timeout    = setTimeout(() => controller.abort(), 15000)

  try {
    const headers = { ...(options.headers || {}) }

    // Inyectar empresa_id para SUPERADMIN en endpoints de empresa
    const usuario = safeJsonParse(localStorage.getItem('usuario'), {})
    if (usuario.rol === 'SUPERADMIN' && url.includes('/api/empresa/')) {
      const empresaActiva = safeJsonParse(sessionStorage.getItem('empresaActiva'), null)
      if (empresaActiva?.id) {
        const sep = url.includes('?') ? '&' : '?'
        url = `${url}${sep}empresa_id=${empresaActiva.id}`
      }
    }

    const token = getAccessToken()
    if (token) headers['Authorization'] = `Bearer ${token}`

    if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json'
      options.body = JSON.stringify(options.body)
    }

    let response = await fetch(url, { ...options, headers, signal: controller.signal })
    clearTimeout(timeout)

    // Token expirado → intentar refresh y reintentar una vez
    if (response.status === 401 && !url.includes('/api/login/') && !url.includes('/api/token/')) {
      const refreshed = await refreshAccessToken()
      if (refreshed) {
        headers['Authorization'] = `Bearer ${getAccessToken()}`
        response = await fetch(url, { ...options, headers })
      } else {
        limpiarSesion()
        return response
      }
    }

    if (response.status === 402) {
      response.clone().json().then(data => {
        if (data?.codigo === 'SUSCRIPCION_BLOQUEADA') {
          window.dispatchEvent(new CustomEvent('suscripcion-bloqueada', { detail: data }))
        }
      }).catch(() => {})
    }

    if (response.status === 403) {
      response.clone().json().then(data => {
        if (data?.codigo === 'LIMITE_PLAN') {
          window.dispatchEvent(new CustomEvent('limite-plan', { detail: data }))
        } else if (data?.codigo === 'MODULO_NO_INCLUIDO') {
          window.dispatchEvent(new CustomEvent('modulo-bloqueado', { detail: data }))
        } else if (data?.error === 'Sin permisos.') {
          window.dispatchEvent(new CustomEvent('permiso-denegado', {
            detail: 'No tienes permiso para realizar esta acción.'
          }))
        }
      }).catch(() => {})
    }

    return response

  } catch (e) {
    clearTimeout(timeout)
    if (e.name === 'AbortError') {
      return new Response(
        JSON.stringify({ error: 'La petición tardó demasiado. Verifica tu conexión.', codigo: 'TIMEOUT' }),
        { status: 408, headers: { 'Content-Type': 'application/json' } }
      )
    }
    if (e instanceof TypeError && e.message.toLowerCase().includes('fetch')) {
      return new Response(
        JSON.stringify({ error: 'Sin conexión al servidor.', codigo: 'SIN_CONEXION' }),
        { status: 0, headers: { 'Content-Type': 'application/json' } }
      )
    }
    throw e
  }
}
