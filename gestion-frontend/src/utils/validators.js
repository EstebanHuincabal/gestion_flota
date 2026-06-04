/**
 * Validadores centralizados para el sistema de gestión de flota.
 * Cada función retorna { valido: boolean, error: string }
 */

// ── RUT chileno ──────────────────────────────────────────────────────────────
// Acepta: 12.345.678-9 o 12345678-9. Valida dígito verificador módulo 11.
export function validarRut(rut) {
  if (!rut || !rut.trim()) return { valido: false, error: 'Ingresa el RUT.' }

  // Normalizar: quitar puntos, trim, lowercase
  const norm = rut.replace(/\./g, '').trim().toLowerCase()

  if (!/^\d{1,8}-[\dk]$/.test(norm)) {
    return { valido: false, error: 'Formato de RUT inválido. Use el formato 12.345.678-9.' }
  }

  const [cuerpo, dv] = norm.split('-')

  // RUTs chilenos válidos tienen entre 7 y 8 dígitos en el cuerpo
  if (cuerpo.length < 7) {
    return { valido: false, error: 'El RUT ingresado es demasiado corto. Verifica el número.' }
  }
  let suma = 0
  let multiplo = 2
  for (let i = cuerpo.length - 1; i >= 0; i--) {
    suma += parseInt(cuerpo[i]) * multiplo
    multiplo = multiplo === 7 ? 2 : multiplo + 1
  }
  const resto = suma % 11
  const dvEsperado = resto === 0 ? '0' : resto === 1 ? 'k' : String(11 - resto)

  if (dv !== dvEsperado) {
    return { valido: false, error: 'RUT inválido. Verifica el número y dígito verificador.' }
  }
  return { valido: true, error: '' }
}

// ── Email ────────────────────────────────────────────────────────────────────
export function validarEmail(email) {
  if (!email || !email.trim()) return { valido: false, error: 'Ingresa el correo electrónico.' }
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!re.test(email.trim())) {
    return { valido: false, error: 'El correo electrónico no es válido.' }
  }
  return { valido: true, error: '' }
}

// ── Teléfono chileno ─────────────────────────────────────────────────────────
// Acepta: +569 XXXXXXXX, +56 9 XXXXXXXX, 9XXXXXXXX y variantes con espacios.
export function validarTelefono(telefono) {
  if (!telefono || !telefono.trim()) return { valido: false, error: 'Ingresa el teléfono.' }
  const limpio = telefono.replace(/[\s\-\(\)]/g, '')
  if (!limpio) return { valido: false, error: 'Ingresa el teléfono.' }
  if (!/^(\+56)?9\d{8}$/.test(limpio)) {
    return {
      valido: false,
      error: 'Teléfono inválido. Use el formato +569 XXXXXXXX o 9XXXXXXXX.',
    }
  }
  return { valido: true, error: '' }
}

// ── Contraseña ───────────────────────────────────────────────────────────────
// Mín 8 chars, al menos 1 mayúscula, 1 número.
// Retorna también { nivel: 'debil'|'media'|'fuerte' }
export function validarPassword(password) {
  if (!password) return { valido: false, error: 'Ingresa una contraseña.', nivel: 'debil' }
  if (password.length < 8) {
    return { valido: false, error: 'La contraseña debe tener al menos 8 caracteres.', nivel: 'debil' }
  }
  if (!/[A-Z]/.test(password)) {
    return { valido: false, error: 'La contraseña debe tener al menos una letra mayúscula.', nivel: 'debil' }
  }
  if (!/[0-9]/.test(password)) {
    return { valido: false, error: 'La contraseña debe tener al menos un número.', nivel: 'debil' }
  }

  // Calcular nivel de fortaleza
  let nivel = 'media'
  const tieneEspecial = /[^A-Za-z0-9]/.test(password)
  const tieneMinuscula = /[a-z]/.test(password)
  if (password.length >= 12 && tieneEspecial && tieneMinuscula) {
    nivel = 'fuerte'
  } else if (password.length >= 10 && (tieneEspecial || tieneMinuscula)) {
    nivel = 'media'
  } else {
    nivel = 'media'
  }

  return { valido: true, error: '', nivel }
}

// ── Patente chilena ──────────────────────────────────────────────────────────
// Formato nuevo: LLLLNN (4 letras + 2 números) ej: ABCD12
// Formato antiguo: LLNNNN (2 letras + 4 números) ej: AB1234
export function validarPatente(patente) {
  if (!patente || !patente.trim()) return { valido: false, error: 'Ingresa la patente.' }
  const valor = patente.toUpperCase().replace(/[\s\-]/g, '')
  if (!/^[A-Z]{4}\d{2}$|^[A-Z]{2}\d{4}$/.test(valor)) {
    return {
      valido: false,
      error: 'Formato de patente inválido. Use LLLLNN (ej: ABCD12) o LLNNNN (ej: AB1234).',
    }
  }
  return { valido: true, error: '' }
}

// ── Licencia de conducir (Chile) ─────────────────────────────────────────────
// Formato: 3 letras + 10 dígitos (ej: ABC1234567890). Debe coincidir con el
// backend (serializers.LICENCIA_PATRON). Campo opcional: vacío se considera válido.
export function validarLicencia(licencia) {
  const v = (licencia || '').trim().toUpperCase()
  if (!v) return { valido: true, error: '' }
  if (!/^[A-Z]{3}\d{10}$/.test(v)) {
    return { valido: false, error: 'Formato inválido. Debe ser 3 letras y 10 dígitos. Ej: ABC1234567890.' }
  }
  return { valido: true, error: '' }
}

// ── Año de vehículo ──────────────────────────────────────────────────────────
// Entre 1950 y año actual + 1
export function validarAnioVehiculo(anio) {
  if (anio === '' || anio === null || anio === undefined) return { valido: true, error: '' }
  const num = Number(anio)
  if (!Number.isInteger(num)) return { valido: false, error: 'El año debe ser un número entero.' }
  const anioActual = new Date().getFullYear()
  if (num < 1950 || num > anioActual + 1) {
    return {
      valido: false,
      error: `El año debe estar entre 1950 y ${anioActual + 1}.`,
    }
  }
  return { valido: true, error: '' }
}

// ── Fecha futura ─────────────────────────────────────────────────────────────
// La fecha no puede ser en el pasado (para fechas programadas)
export function validarFechaFutura(fechaIso) {
  if (!fechaIso) return { valido: false, error: 'Ingresa la fecha.' }
  const hoy = new Date().toISOString().split('T')[0]
  if (fechaIso < hoy) {
    return { valido: false, error: 'La fecha no puede ser en el pasado.' }
  }
  return { valido: true, error: '' }
}

// ── Fecha vigente ────────────────────────────────────────────────────────────
// Debe ser >= hoy (para documentos)
export function validarFechaVigente(fechaIso) {
  if (!fechaIso) return { valido: false, error: 'Ingresa la fecha de vencimiento.' }
  const hoy = new Date().toISOString().split('T')[0]
  if (fechaIso < hoy) {
    return { valido: false, error: 'La fecha de vencimiento no puede ser anterior a hoy.' }
  }
  return { valido: true, error: '' }
}

// ── Nombre (persona o empresa) ────────────────────────────────────────────────
// Valida longitud, que tenga al menos una letra y no tenga caracteres repetidos en exceso.
export function validarNombre(texto, min = 2, max = 255) {
  if (!texto || !texto.trim()) return { valido: false, error: 'Este campo es obligatorio.' }
  const t = texto.trim()
  if (t.length < min) return { valido: false, error: `Debe tener al menos ${min} caracteres.` }
  if (t.length > max) return { valido: false, error: `No puede superar los ${max} caracteres.` }
  if (!/[a-záéíóúñüA-ZÁÉÍÓÚÑÜ]/.test(t)) {
    return { valido: false, error: 'Debe contener al menos una letra.' }
  }
  // Más de 3 caracteres idénticos consecutivos → spam
  if (/(.)\1{3,}/.test(t)) {
    return { valido: false, error: 'El texto contiene caracteres repetidos en exceso.' }
  }
  return { valido: true, error: '' }
}

// ── Longitud de texto ─────────────────────────────────────────────────────────
export function validarLongitud(texto, min, max) {
  if (texto === null || texto === undefined) texto = ''
  const len = texto.length
  if (min !== undefined && len < min) {
    return { valido: false, error: `Debe tener al menos ${min} caracteres.` }
  }
  if (max !== undefined && len > max) {
    return { valido: false, error: `No puede superar los ${max} caracteres.` }
  }
  return { valido: true, error: '' }
}
