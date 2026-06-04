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

// Refresh en curso compartido (single-flight): si varias peticiones reciben 401
// a la vez, todas esperan UN solo refresh en vez de disparar varios en paralelo
// (lo que con la rotación de tokens dejaría la sesión inconsistente).
let _refreshPromise = null

// Devuelve { ok, expired }:
//   ok=true             → token renovado.
//   ok=false expired=true  → el refresh token está vencido/es inválido → cerrar sesión.
//   ok=false expired=false → fallo transitorio (red/servidor) → NO cerrar sesión.
export function refreshAccessToken() {
  if (_refreshPromise) return _refreshPromise
  _refreshPromise = _hacerRefresh().finally(() => { _refreshPromise = null })
  return _refreshPromise
}

async function _hacerRefresh() {
  const refresh = localStorage.getItem('refresh_token')
  if (!refresh) return { ok: false, expired: true }
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
      return { ok: true }
    }
    // 400/401 → el refresh token ya no sirve: la sesión realmente expiró.
    if (res.status === 400 || res.status === 401) return { ok: false, expired: true }
    // Otros (500, 502…) → problema del servidor, no de la sesión: no desloguear.
    return { ok: false, expired: false }
  } catch {
    // Error de red (sin conexión, timeout…): no desloguear por un parpadeo.
    return { ok: false, expired: false }
  }
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
      const refresh = await refreshAccessToken()
      if (refresh.ok) {
        headers['Authorization'] = `Bearer ${getAccessToken()}`
        response = await fetch(url, { ...options, headers })
      } else if (refresh.expired) {
        // El refresh token venció: la sesión terminó de verdad.
        limpiarSesion()
        return response
      }
      // Fallo transitorio (red/servidor): se devuelve el 401 sin cerrar sesión;
      // la próxima petición reintentará el refresh.
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
      // 503 (no 0): el constructor de Response solo acepta 200-599. El "sin
      // conexión" se identifica por el campo codigo, no por el status.
      return new Response(
        JSON.stringify({ error: 'Sin conexión al servidor.', codigo: 'SIN_CONEXION' }),
        { status: 503, headers: { 'Content-Type': 'application/json' } }
      )
    }
    throw e
  }
}
