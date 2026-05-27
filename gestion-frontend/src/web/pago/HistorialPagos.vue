<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../../utils/api.js'

const pagos    = ref([])
const cargando = ref(true)
const error    = ref('')

onMounted(async () => {
  try {
    const res  = await apiFetch('/api/pago/historial/')
    if (!res.ok) { error.value = 'No se pudo cargar el historial.'; return }
    const data = await res.json()
    pagos.value = data.pagos || []
  } catch {
    error.value = 'Error de conexión.'
  } finally {
    cargando.value = false
  }
})

function formatCLP(n) {
  return '$' + parseInt(n).toLocaleString('es-CL')
}

function exportarCSV() {
  if (!pagos.value.length) return
  const headers = ['Orden', 'Plan', 'Ciclo', 'Monto', 'Fecha', 'Estado']
  const rows    = pagos.value.map(p => [
    p.orden_compra,
    p.plan,
    p.ciclo,
    p.monto,
    p.fecha || '',
    p.estado,
  ])
  const csv = [headers, ...rows].map(r => r.join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a'); a.href = url; a.download = 'historial_pagos.csv'; a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="historial-page">
    <div class="historial-header">
      <div>
        <h1 class="historial-title">Historial de pagos</h1>
        <p class="historial-sub">Pagos aprobados de tu suscripción</p>
      </div>
      <button v-if="pagos.length" class="btn-export" @click="exportarCSV">
        ↓ Exportar CSV
      </button>
    </div>

    <div v-if="cargando" class="estado-msg">Cargando…</div>
    <div v-else-if="error"  class="error-box">{{ error }}</div>
    <div v-else-if="!pagos.length" class="estado-msg">No hay pagos registrados aún.</div>

    <div v-else class="tabla-wrap">
      <table class="tabla">
        <thead>
          <tr>
            <th>Orden</th>
            <th>Plan</th>
            <th>Ciclo</th>
            <th>Monto</th>
            <th>Fecha</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in pagos" :key="p.id">
            <td class="orden-col">{{ p.orden_compra }}</td>
            <td>{{ p.plan }}</td>
            <td class="cap">{{ p.ciclo }}</td>
            <td>{{ formatCLP(p.monto) }}</td>
            <td>{{ p.fecha }}</td>
            <td><span class="badge-ok">Aprobado</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.historial-page   { padding: 2rem 2.5rem; max-width: 900px; margin: 0 auto; }
.historial-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; }
.historial-title  { font-size: 1.5rem; font-weight: 700; color: #111827; margin: 0 0 0.25rem; }
.historial-sub    { font-size: 0.875rem; color: #6B7280; margin: 0; }

.btn-export {
  padding: 0.5rem 1rem; background: #fff; border: 1px solid #E5E7EB;
  border-radius: 8px; font-size: 0.8125rem; font-weight: 500; color: #374151;
  cursor: pointer; transition: background 0.15s; font-family: inherit;
}
.btn-export:hover { background: #F9FAFB; }

.estado-msg { color: #6B7280; font-size: 0.9rem; padding: 2rem 0; }
.error-box  { background: #FEF2F2; border: 1px solid #FECACA; color: #B91C1C; padding: 0.75rem 1rem; border-radius: 8px; font-size: 0.875rem; }

.tabla-wrap { overflow-x: auto; }
.tabla { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.tabla thead th {
  text-align: left; padding: 0.625rem 0.875rem;
  background: #F9FAFB; color: #374151; font-weight: 600;
  border-bottom: 1px solid #E5E7EB; white-space: nowrap;
}
.tabla tbody tr:hover { background: #F9FAFB; }
.tabla tbody td { padding: 0.75rem 0.875rem; border-bottom: 1px solid #F3F4F6; color: #374151; }
.orden-col   { font-family: monospace; font-size: 0.8rem; color: #6B7280; }
.cap         { text-transform: capitalize; }
.badge-ok    { background: #D1FAE5; color: #065F46; font-size: 0.75rem; font-weight: 600; padding: 2px 10px; border-radius: 99px; }
</style>
