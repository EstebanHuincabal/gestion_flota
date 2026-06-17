import { ref } from 'vue'
import { useToast } from '../utils/useToast.js'

export function useAsync() {
  const cargando = ref(false)
  const error    = ref(null)
  const toast    = useToast()

  // Ejecuta fn() manejando automáticamente loading y error.
  // fn puede retornar una Response (apiFetch) o cualquier valor.
  async function ejecutar(fn, opciones = {}) {
    const {
      onError,
      mensajeError = 'Ocurrió un error. Intenta nuevamente.',
      mostrarToast = true,
    } = opciones

    cargando.value = true
    error.value    = null

    try {
      const result = await fn()

      // Si el resultado es una Response, verificar ok
      if (result instanceof Response || (result && typeof result.ok === 'boolean')) {
        if (!result.ok) {
          let data = {}
          try { data = await result.json() } catch {}
          const msg = data.error || data.detail || mensajeError
          throw new Error(msg)
        }
        return result
      }

      return result
    } catch (e) {
      error.value = e.message || mensajeError
      if (mostrarToast) toast.error(error.value)
      if (onError) onError(e)
      return null
    } finally {
      cargando.value = false
    }
  }

  return { cargando, error, ejecutar }
}
