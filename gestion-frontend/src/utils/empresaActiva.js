import { apiFetch, safeJsonParse } from './api.js'

export const getEmpresaActiva = () =>
  safeJsonParse(sessionStorage.getItem('empresaActiva'), null)

export const setEmpresaActiva = (emp) =>
  sessionStorage.setItem('empresaActiva', JSON.stringify({ id: emp.id, nombre: emp.nombre }))

export const clearEmpresaActiva = () =>
  sessionStorage.removeItem('empresaActiva')

// Para SUPERADMIN exige que haya una empresa activa seleccionada; si no la hay,
// devuelve una respuesta controlada con status 400 para que los componentes
// muestren el estado "sin empresa".
// El ?empresa_id=X lo inyecta apiFetch() de forma centralizada para los
// endpoints /api/empresa/ — aquí NO se vuelve a agregar (evita duplicarlo).
export const apiFetchEmpresa = (path, options = {}) => {
  const usuario = safeJsonParse(localStorage.getItem('usuario'), {})
  if (usuario.rol === 'SUPERADMIN' && !getEmpresaActiva()) {
    return Promise.resolve(
      new Response(JSON.stringify({ error: 'sin_empresa' }), { status: 400, headers: { 'Content-Type': 'application/json' } })
    )
  }
  return apiFetch(path, options)
}

// Devuelve ruta(path): sin prefijo para SUPERADMIN, /empresa para USUARIO
export const useEmpresaNav = () => {
  const usuario = safeJsonParse(localStorage.getItem('usuario'), {})
  const prefijo = usuario.rol === 'SUPERADMIN' ? '' : '/empresa'
  const ruta = (path) => `${prefijo}${path}`
  return { ruta }
}
