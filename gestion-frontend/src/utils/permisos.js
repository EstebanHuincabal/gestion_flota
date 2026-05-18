export function tienePermiso(codigo) {
  const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
  if (usuario.rol === 'SUPERADMIN') return true
  if (usuario.rol === 'CONDUCTOR')  return false

  const planPermisos = JSON.parse(sessionStorage.getItem('plan_permisos') || '[]')
  return Array.isArray(planPermisos) && planPermisos.includes(codigo)
}

export function getPermisos() {
  return JSON.parse(sessionStorage.getItem('plan_permisos') || '[]')
}

export function tieneModulo(modulo) {
  const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
  if (usuario.rol === 'SUPERADMIN') return true
  const planModulos = JSON.parse(sessionStorage.getItem('plan_modulos') || '[]')
  return Array.isArray(planModulos) && planModulos.includes(modulo)
}
