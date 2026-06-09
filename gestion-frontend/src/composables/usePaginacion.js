import { ref, computed, watch } from 'vue'

export function usePaginacion(lista, porPagina = 20) {
  const pagina = ref(1)

  const total       = computed(() => lista.value.length)
  const totalPaginas = computed(() => Math.max(1, Math.ceil(total.value / porPagina)))

  const paginado = computed(() => {
    const inicio = (pagina.value - 1) * porPagina
    return lista.value.slice(inicio, inicio + porPagina)
  })

  // Volver a página 1 cuando cambia la cantidad de elementos (filtro aplicado, recarga, etc.)
  watch(total, () => { pagina.value = 1 })

  function irA(n) {
    pagina.value = Math.max(1, Math.min(n, totalPaginas.value))
  }

  return { pagina, totalPaginas, total, paginado, irA }
}
