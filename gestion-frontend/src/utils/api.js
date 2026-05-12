function getCsrfToken() {
  const match = document.cookie.match(/csrftoken=([^;]+)/)
  return match ? match[1] : ''
}

export async function apiFetch(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const headers = { ...(options.headers || {}) }

  // Para SUPERADMIN en endpoints de empresa, inyectar empresa_id como query param
  const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
  if (usuario.rol === 'SUPERADMIN' && url.includes('/api/empresa/')) {
    const empresaActiva = JSON.parse(sessionStorage.getItem('empresaActiva') || 'null')
    if (empresaActiva?.id) {
      const sep = url.includes('?') ? '&' : '?'
      url = `${url}${sep}empresa_id=${empresaActiva.id}`
    }
  }

  if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) {
    headers['X-CSRFToken'] = getCsrfToken()
  }

  if (options.body && typeof options.body === 'object') {
    headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(options.body)
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include',
  })

  if (response.status === 401 && !url.includes('/api/login/')) {
    localStorage.removeItem('usuario')
    sessionStorage.removeItem('empresaActiva')
    window.location.href = '/login'
    return response
  }

  if (response.status === 403) {
    response.clone().json().then(data => {
      if (data?.error === 'Sin permisos.') {
        window.dispatchEvent(new CustomEvent('permiso-denegado', {
          detail: 'No tienes permiso para realizar esta acción.'
        }))
      }
    }).catch(() => {})
  }

  return response
}
