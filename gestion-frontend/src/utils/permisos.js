import { safeJsonParse } from './api.js'

export function tienePermiso(codigo) {
  const usuario = safeJsonParse(localStorage.getItem('usuario'), {})
  if (usuario.rol === 'SUPERADMIN') return true
  if (usuario.rol === 'CONDUCTOR')  return false

  const planPermisos = safeJsonParse(sessionStorage.getItem('plan_permisos'), [])
  return Array.isArray(planPermisos) && planPermisos.includes(codigo)
}

export function getPermisos() {
  const planPermisos = safeJsonParse(sessionStorage.getItem('plan_permisos'), [])
  return Array.isArray(planPermisos) ? planPermisos : []
}

export function tieneModulo(modulo) {
  const usuario = safeJsonParse(localStorage.getItem('usuario'), {})
  if (usuario.rol === 'SUPERADMIN') return true
  const planModulos = safeJsonParse(sessionStorage.getItem('plan_modulos'), [])
  return Array.isArray(planModulos) && planModulos.includes(modulo)
}
