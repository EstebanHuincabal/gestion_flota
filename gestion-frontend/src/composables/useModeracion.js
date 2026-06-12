import { ref } from 'vue'
import { apiFetch } from '../utils/api.js'

export function useModeracion() {
  const aviso      = ref('')
  const sugerencia = ref('')

  function limpiar() {
    aviso.value      = ''
    sugerencia.value = ''
  }

  async function moderar(texto) {
    if (!texto || texto.trim().length < 3) { limpiar(); return true }
    try {
      const res  = await apiFetch('/api/moderar/', {
        method: 'POST',
        body: { texto },
      })
      const data = await res.json()
      if (!data.aprobado) {
        aviso.value      = data.razon || 'Tu mensaje contiene lenguaje inapropiado.'
        sugerencia.value = data.sugerencia || ''
        return false
      }
      limpiar()
      return true
    } catch {
      limpiar()
      return true  // fail-open: si el servicio falla, no bloquear al usuario
    }
  }

  return { moderar, aviso, sugerencia, limpiar }
}
