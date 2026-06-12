import { ref } from 'vue'
import { apiFetch } from '@/services/api.js'

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
      const res = await apiFetch('/api/moderar/', {
        method: 'POST',
        body: JSON.stringify({ texto }),
      })
      if (!res.aprobado) {
        aviso.value      = res.razon || 'Tu mensaje contiene lenguaje inapropiado.'
        sugerencia.value = res.sugerencia || ''
        return false
      }
      limpiar()
      return true
    } catch {
      limpiar()
      return true
    }
  }

  return { moderar, aviso, sugerencia, limpiar }
}
