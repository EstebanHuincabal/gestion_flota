export function tienePermiso(codigo) {
  const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
  if (usuario.rol === 'SUPERADMIN') return true
  if (usuario.rol === 'CONDUCTOR')  return false
  return Array.isArray(usuario.permisos) && usuario.permisos.includes(codigo)
}

export function getPermisos() {
  const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
  return usuario.permisos || []
}
