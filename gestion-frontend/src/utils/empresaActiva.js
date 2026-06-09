import { apiFetch, safeJsonParse } from './api.js'

// Centinela de la opción "Todas las empresas" del SelectorEmpresa. Debe coincidir
// con EMPRESA_TODAS del backend (g_de_flota/views.py). Viaja como empresa_id.
export const EMPRESA_TODAS = '__todas__'

export const getEmpresaActiva = () =>
  safeJsonParse(sessionStorage.getItem('empresaActiva'), null)

// True si el SUPERADMIN tiene seleccionada la opción "Todas las empresas".
export const esEmpresaTodas = () => getEmpresaActiva()?.id === EMPRESA_TODAS

// Pseudo-empresa "Todas las empresas" para anteponer a los selectores inline de
// cada módulo. Al seleccionarla, setEmpresaActiva guarda el centinela y el backend
// devuelve los datos de todas las empresas (solo lectura).
export const OPCION_TODAS = { id: EMPRESA_TODAS, nombre: 'Todas las empresas' }

// Antepone "Todas las empresas" a una lista de empresas (para los dropdowns).
export const conOpcionTodas = (empresas) => [OPCION_TODAS, ...(empresas || [])]

// Para SUPERADMIN, deja "Todas las empresas" preseleccionada cuando todavía no
// hay ninguna empresa elegida en la sesión. Se invoca al iniciar sesión y al
// arrancar la app (cubre también sesiones ya abiertas tras recargar).
export const initEmpresaActivaDefault = () => {
  const usuario = safeJsonParse(localStorage.getItem('usuario'), {})
  if (usuario.rol === 'SUPERADMIN' && !sessionStorage.getItem('empresaActiva')) {
    setEmpresaActiva(OPCION_TODAS)
  }
}

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
