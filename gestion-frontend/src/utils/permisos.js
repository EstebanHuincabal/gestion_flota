const CATEGORIA_A_MODULO = {
  flotas:       'flotas',
  vehiculos:    'vehiculos',
  conductores:  'conductores',
  mantenciones: 'mantencion_correctiva',
  documentos:   'documentos',
  dashboard:    'dashboard',
  predictivo:   'mantencion_predictiva',
  gps:          'gps',
  reportes:     'reportes',
  usuarios:     null, // siempre disponible para admin de empresa
}

export function tienePermiso(codigo) {
  const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
  if (usuario.rol === 'SUPERADMIN') return true
  if (usuario.rol === 'CONDUCTOR') return false

  // Capa 1: verificar que el módulo esté habilitado en el plan
  const categoria = codigo.split('.')[0]
  const moduloRequerido = CATEGORIA_A_MODULO[categoria]
  if (moduloRequerido !== null && moduloRequerido !== undefined) {
    if (!tieneModulo(moduloRequerido)) return false
  }

  // Capa 2: verificar permiso individual
  return Array.isArray(usuario.permisos) && usuario.permisos.includes(codigo)
}

export function getPermisos() {
  const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
  return usuario.permisos || []
}

export function tieneModulo(modulo) {
  const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
  if (usuario.rol === 'SUPERADMIN') return true
  const planModulos = JSON.parse(sessionStorage.getItem('plan_modulos') || '[]')
  return Array.isArray(planModulos) && planModulos.includes(modulo)
}
