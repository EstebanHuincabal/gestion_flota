import { apiFetch } from './api.js'

export const getEmpresaActiva = () =>
  JSON.parse(sessionStorage.getItem('empresaActiva') || 'null')

export const setEmpresaActiva = (emp) =>
  sessionStorage.setItem('empresaActiva', JSON.stringify({ id: emp.id, nombre: emp.nombre }))

export const clearEmpresaActiva = () =>
  sessionStorage.removeItem('empresaActiva')

// Agrega ?empresa_id=X automáticamente para SUPERADMIN.
// Si SUPERADMIN no tiene empresa activa devuelve una respuesta controlada
// con status 400 para que los componentes muestren el estado "sin empresa".
export const apiFetchEmpresa = (path, options = {}) => {
  const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
  if (usuario.rol === 'SUPERADMIN') {
    const empresa = getEmpresaActiva()
    if (!empresa) {
      return Promise.resolve(
        new Response(JSON.stringify({ error: 'sin_empresa' }), { status: 400 })
      )
    }
    const sep = path.includes('?') ? '&' : '?'
    return apiFetch(`${path}${sep}empresa_id=${empresa.id}`, options)
  }
  return apiFetch(path, options)
}

// Devuelve ruta(path): sin prefijo para SUPERADMIN, /empresa para USUARIO
export const useEmpresaNav = () => {
  const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
  const prefijo = usuario.rol === 'SUPERADMIN' ? '' : '/empresa'
  const ruta = (path) => `${prefijo}${path}`
  return { ruta }
}
