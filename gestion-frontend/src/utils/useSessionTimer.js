import { ref, onUnmounted } from 'vue'

const WARN_ANTES_MS = 2 * 60 * 1000  // Aviso 2 minutos antes de expirar

function leerExp() {
  const token = localStorage.getItem('access_token')
  if (!token) return null
  try {
    const partes = token.split('.')
    if (partes.length < 2) return null
    const payload = JSON.parse(atob(partes[1].replace(/-/g, '+').replace(/_/g, '/')))
    return typeof payload.exp === 'number' ? payload.exp * 1000 : null
  } catch {
    return null
  }
}

async function renovarToken() {
  const refresh = localStorage.getItem('refresh_token')
  if (!refresh) return false
  try {
    const res = await fetch('/api/token/refresh/', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ refresh }),
    })
    if (res.ok) {
      const data = await res.json()
      localStorage.setItem('access_token', data.access)
      if (data.refresh) localStorage.setItem('refresh_token', data.refresh)
      return true
    }
  } catch {}
  return false
}

function limpiarSesion() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('usuario')
  sessionStorage.removeItem('plan_modulos')
  sessionStorage.removeItem('plan_nombre')
  sessionStorage.removeItem('plan_permisos')
  sessionStorage.removeItem('empresaActiva')
  window.location.href = '/login'
}

export function useSessionTimer() {
  const mostrarModal     = ref(false)
  const segundosRestantes = ref(120)

  let timerAviso           = null
  let timerCuentaRegresiva = null

  function limpiarTimers() {
    clearTimeout(timerAviso)
    clearInterval(timerCuentaRegresiva)
    timerAviso           = null
    timerCuentaRegresiva = null
  }

  function iniciarCuentaRegresiva(expMs) {
    timerCuentaRegresiva = setInterval(() => {
      const restantes = Math.round((expMs - Date.now()) / 1000)
      if (restantes <= 0) {
        limpiarTimers()
        mostrarModal.value = false
        limpiarSesion()
        return
      }
      segundosRestantes.value = restantes
    }, 1000)
  }

  function programar() {
    limpiarTimers()
    const exp = leerExp()
    if (!exp) return

    const ahora            = Date.now()
    const msHastaExpiracion = exp - ahora

    if (msHastaExpiracion <= 0) {
      limpiarSesion()
      return
    }

    const msHastaAviso = msHastaExpiracion - WARN_ANTES_MS

    if (msHastaAviso <= 0) {
      // Menos de 2 minutos — mostrar aviso inmediatamente
      segundosRestantes.value = Math.round(msHastaExpiracion / 1000)
      mostrarModal.value      = true
      iniciarCuentaRegresiva(exp)
    } else {
      timerAviso = setTimeout(() => {
        const expActual = leerExp()
        if (!expActual) return
        const restantes = Math.round((expActual - Date.now()) / 1000)
        if (restantes <= 0) { limpiarSesion(); return }
        segundosRestantes.value = restantes
        mostrarModal.value      = true
        iniciarCuentaRegresiva(expActual)
      }, msHastaAviso)
    }
  }

  async function extenderSesion() {
    limpiarTimers()
    mostrarModal.value = false
    const ok = await renovarToken()
    if (ok) {
      programar()
    } else {
      limpiarSesion()
    }
  }

  function logoutDesdeModal() {
    limpiarTimers()
    mostrarModal.value = false
    limpiarSesion()
  }

  onUnmounted(limpiarTimers)

  programar()

  return { mostrarModal, segundosRestantes, extenderSesion, logoutDesdeModal }
}
