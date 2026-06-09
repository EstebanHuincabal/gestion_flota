/**
 * formato.js — Helpers de presentación para la app de conductores.
 */

/** Formatea un monto en pesos chilenos: $85.400 */
export function formatCLP(monto) {
  if (!monto && monto !== 0) return '$0'
  return '$' + Number(monto).toLocaleString('es-CL')
}

/** Convierte minutos a "Xh Ymin" */
export function formatDuracion(minutos) {
  if (!minutos) return '—'
  const h = Math.floor(minutos / 60)
  const m = minutos % 60
  if (h === 0) return `${m}min`
  if (m === 0) return `${h}h`
  return `${h}h ${m}min`
}

/**
 * Fecha relativa amigable: "Hoy 08:30" / "Mañana 14:00" / "Lun 20/05"
 * Acepta DateField (solo fecha) y DateTimeField (con hora).
 */
export function formatFechaRuta(iso) {
  if (!iso) return '—'
  // Si es solo fecha (sin T), agregar hora 00:00 para evitar desfase de zona
  const normalized = iso.includes('T') ? iso : `${iso}T00:00:00`
  const fecha  = new Date(normalized)
  const hoy    = new Date()
  const manana = new Date(hoy)
  manana.setDate(hoy.getDate() + 1)

  const mismodia = (a, b) => a.getFullYear() === b.getFullYear()
    && a.getMonth() === b.getMonth()
    && a.getDate()  === b.getDate()

  const tieneHora = iso.includes('T')
  const hora = tieneHora
    ? fecha.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' })
    : null

  if (mismodia(fecha, hoy))    return hora ? `Hoy ${hora}` : 'Hoy'
  if (mismodia(fecha, manana)) return hora ? `Mañana ${hora}` : 'Mañana'

  const fechaStr = fecha.toLocaleDateString('es-CL', { weekday: 'short', day: '2-digit', month: '2-digit' })
  return hora ? `${fechaStr} ${hora}` : fechaStr
}

/** Tiempo transcurrido desde una fecha ISO: "hace 3 min" / "hace 2h" */
export function tiempoDesde(iso) {
  if (!iso) return 'nunca'
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (diff < 60)   return 'hace un momento'
  if (diff < 3600) return `hace ${Math.floor(diff / 60)} min`
  return `hace ${Math.floor(diff / 3600)}h`
}

/**
 * Agrupa una lista de items por antigüedad de fecha en secciones:
 * "Hoy", "Ayer", "Esta semana", "Este mes", "Anteriores".
 * `obtenerFecha(item)` debe devolver un string ISO.
 * Devuelve [{ label, items }] solo con los grupos que tienen elementos.
 */
export function agruparPorFecha(items, obtenerFecha) {
  const ORDEN = ['Hoy', 'Ayer', 'Esta semana', 'Este mes', 'Anteriores']
  const hoy  = new Date()
  const ayer = new Date(hoy)
  ayer.setDate(hoy.getDate() - 1)

  const mismoDia = (a, b) => a.getFullYear() === b.getFullYear()
    && a.getMonth() === b.getMonth()
    && a.getDate()  === b.getDate()

  const grupos = {}
  for (const item of items) {
    const fecha = new Date(obtenerFecha(item))
    let label
    if (mismoDia(fecha, hoy))       label = 'Hoy'
    else if (mismoDia(fecha, ayer)) label = 'Ayer'
    else {
      const diasDiff = Math.floor((hoy - fecha) / 86400000)
      if (diasDiff < 7)       label = 'Esta semana'
      else if (diasDiff < 30) label = 'Este mes'
      else                    label = 'Anteriores'
    }
    ;(grupos[label] ??= []).push(item)
  }
  return ORDEN.filter(g => grupos[g]?.length).map(label => ({ label, items: grupos[label] }))
}

/** Iniciales del nombre para el avatar: "Juan Muñoz" → "JM" */
export function iniciales(nombre) {
  if (!nombre) return '?'
  return nombre
    .split(' ')
    .slice(0, 2)
    .map(n => n[0])
    .join('')
    .toUpperCase()
}
