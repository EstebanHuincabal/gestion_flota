<script setup>
import { computed } from 'vue'

const props = defineProps({
  pagina:       { type: Number, required: true },
  totalPaginas: { type: Number, required: true },
  total:        { type: Number, required: true },
  porPagina:    { type: Number, default: 20 },
})
const emit = defineEmits(['update:pagina'])

const inicio = computed(() => Math.min((props.pagina - 1) * props.porPagina + 1, props.total))
const fin    = computed(() => Math.min(props.pagina * props.porPagina, props.total))

// Números de página con puntos suspensivos
const items = computed(() => {
  const tp = props.totalPaginas
  const p  = props.pagina
  if (tp <= 7) return Array.from({ length: tp }, (_, i) => i + 1)

  const set = new Set([1, tp])
  for (let i = Math.max(2, p - 2); i <= Math.min(tp - 1, p + 2); i++) set.add(i)
  const sorted = [...set].sort((a, b) => a - b)

  const result = []
  for (let i = 0; i < sorted.length; i++) {
    result.push(sorted[i])
    if (i < sorted.length - 1 && sorted[i + 1] - sorted[i] > 1) result.push('…')
  }
  return result
})

function ir(n) {
  if (typeof n === 'number') emit('update:pagina', n)
}
</script>

<template>
  <div v-if="total > porPagina" class="flex items-center justify-between px-1 py-3 text-sm text-gray-500">
    <span>Mostrando {{ inicio }}–{{ fin }} de {{ total }} registros</span>

    <div class="flex items-center gap-1">
      <!-- Anterior -->
      <button
        @click="ir(pagina - 1)"
        :disabled="pagina === 1"
        class="px-2 py-1 rounded-lg hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition">
        ‹
      </button>

      <!-- Números -->
      <template v-for="item in items" :key="item">
        <span v-if="item === '…'" class="px-1 select-none">…</span>
        <button v-else
          @click="ir(item)"
          :class="['min-w-[2rem] py-1 rounded-lg text-sm font-medium transition',
            item === pagina
              ? 'bg-indigo-600 text-white'
              : 'hover:bg-gray-100 text-gray-600']">
          {{ item }}
        </button>
      </template>

      <!-- Siguiente -->
      <button
        @click="ir(pagina + 1)"
        :disabled="pagina === totalPaginas"
        class="px-2 py-1 rounded-lg hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition">
        ›
      </button>
    </div>
  </div>
</template>
