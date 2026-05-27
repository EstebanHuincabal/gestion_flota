<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../../utils/api.js'

const suscripciones = ref([])
const kpis          = ref({})
const cargando      = ref(true)
const error         = ref('')
const filtroEstado  = ref('')
const busqueda      = ref('')

async function cargar() {
  cargando.value = true
  error.value    = ''
  try {
    let url = '/api/admin/suscripciones/'
    const params = new URLSearchParams()
    if (filtroEstado.value) params.set('estado', filtroEstado.value)
    if (busqueda.value)     params.set('q', busqueda.value)
    if (params.toString())  url += '?' + params.toString()

    const res  = await apiFetch(url)
    if (!res.ok) { error.value = 'Error al cargar suscripciones.'; return }
    const data = await res.json()
    suscripciones.value = data.suscripciones || []
    kpis.value          = data.kpis || {}
  } catch {
    error.value = 'Error de conexión.'
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)

async function accion(sus, accionNombre, dias = null) {
  const body = { accion: accionNombre }
  if (dias !== null) body.dias = dias
  const res  = await apiFetch(`/api/admin/suscripciones/${sus.id}/`, { method: 'PUT', body })
  if (res.ok) await cargar()
  else alert('Error al ejecutar la acción.')
}

function formatCLP(n) {
  return '$' + parseInt(n).toLocaleString('es-CL')
}

const BADGE = {
  activa:     { label: 'Activa',     cls: 'badge-activa' },
  trial:      { label: 'Trial',      cls: 'badge-trial' },
  gracia:     { label: 'En gracia',  cls: 'badge-gracia' },
  suspendida: { label: 'Suspendida', cls: 'badge-suspendida' },
  cancelada:  { label: 'Cancelada',  cls: 'badge-cancelada' },
}
</script>

<template>
  <div class="pagos-page">
    <h1 class="pagos-title">Pagos y Suscripciones</h1>

    <!-- KPIs -->
    <div class="kpis-grid">
      <div class="kpi-card">
        <p class="kpi-label">MRR del mes</p>
        <p class="kpi-val">{{ kpis.mrr ? formatCLP(kpis.mrr) : '$0' }}</p>
      </div>
      <div class="kpi-card">
        <p class="kpi-label">Activas</p>
        <p class="kpi-val kpi-verde">{{ kpis.activas ?? '—' }}</p>
      </div>
      <div class="kpi-card">
        <p class="kpi-label">En gracia</p>
        <p class="kpi-val kpi-naranja">{{ kpis.en_gracia ?? '—' }}</p>
      </div>
      <div class="kpi-card">
        <p class="kpi-label">Suspendidas</p>
        <p class="kpi-val kpi-rojo">{{ kpis.suspendidas ?? '—' }}</p>
      </div>
    </div>

    <!-- Filtros -->
    <div class="filtros">
      <input
        v-model="busqueda"
        placeholder="Buscar empresa…"
        class="filtro-input"
        @keydown.enter="cargar"
      />
      <select v-model="filtroEstado" class="filtro-select" @change="cargar">
        <option value="">Todos los estados</option>
        <option value="activa">Activa</option>
        <option value="trial">Trial</option>
        <option value="gracia">En gracia</option>
        <option value="suspendida">Suspendida</option>
        <option value="cancelada">Cancelada</option>
      </select>
      <button class="btn-buscar" @click="cargar">Buscar</button>
    </div>

    <div v-if="cargando" class="estado-msg">Cargando…</div>
    <div v-else-if="error" class="error-box">{{ error }}</div>

    <div v-else class="tabla-wrap">
      <table class="tabla">
        <thead>
          <tr>
            <th>Empresa</th>
            <th>Plan</th>
            <th>Ciclo</th>
            <th>Estado</th>
            <th>Próximo cobro</th>
            <th>Último pago</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in suscripciones" :key="s.id">
            <td class="empresa-col">{{ s.empresa }}</td>
            <td>{{ s.plan || '—' }}</td>
            <td class="cap">{{ s.ciclo }}</td>
            <td>
              <span :class="['badge', BADGE[s.estado]?.cls]">
                {{ BADGE[s.estado]?.label || s.estado }}
                <template v-if="s.estado === 'gracia' && s.dias_para_vencer !== null">
                  ({{ s.dias_para_vencer }}d)
                </template>
              </span>
            </td>
            <td>{{ s.fecha_fin || '—' }}</td>
            <td>{{ s.ultimo_pago || '—' }}</td>
            <td class="acciones-col">
              <button
                v-if="s.estado === 'suspendida'"
                class="btn-accion btn-reactivar"
                @click="accion(s, 'reactivar')"
              >Reactivar</button>
              <button
                v-if="s.estado === 'gracia'"
                class="btn-accion btn-extender"
                @click="accion(s, 'extender_gracia', 7)"
              >+7 días gracia</button>
              <router-link
                v-if="s.estado === 'activa'"
                :to="`/admin/pagos?empresa_id=${s.empresa_id}`"
                class="btn-accion btn-pagos"
              >Ver pagos</router-link>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!suscripciones.length" class="estado-msg">Sin resultados.</p>
    </div>
  </div>
</template>

<style scoped>
.pagos-page  { padding: 2rem 2.5rem; max-width: 1100px; margin: 0 auto; }
.pagos-title { font-size: 1.5rem; font-weight: 700; color: #111827; margin: 0 0 1.5rem; }

.kpis-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
.kpi-card  { background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.25rem; }
.kpi-label { font-size: 0.8125rem; color: #6B7280; margin: 0 0 0.35rem; }
.kpi-val   { font-size: 1.5rem; font-weight: 700; color: #111827; margin: 0; }
.kpi-verde   { color: #059669; }
.kpi-naranja { color: #D97706; }
.kpi-rojo    { color: #DC2626; }

.filtros { display: flex; gap: 0.75rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
.filtro-input  {
  flex: 1; min-width: 180px; padding: 0.5rem 0.75rem;
  border: 1px solid #E5E7EB; border-radius: 8px; font-size: 0.875rem; font-family: inherit;
}
.filtro-select {
  padding: 0.5rem 0.75rem; border: 1px solid #E5E7EB; border-radius: 8px;
  font-size: 0.875rem; background: #fff; font-family: inherit;
}
.btn-buscar {
  padding: 0.5rem 1.25rem; background: #4F46E5; color: #fff; border: none;
  border-radius: 8px; font-size: 0.875rem; font-weight: 500; cursor: pointer;
  transition: background 0.15s; font-family: inherit;
}
.btn-buscar:hover { background: #4338CA; }

.estado-msg { color: #6B7280; font-size: 0.9rem; padding: 1.5rem 0; }
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
.empresa-col { font-weight: 600; }
.cap { text-transform: capitalize; }

.badge          { font-size: 0.75rem; font-weight: 600; padding: 2px 10px; border-radius: 99px; white-space: nowrap; }
.badge-activa    { background: #D1FAE5; color: #065F46; }
.badge-trial     { background: #DBEAFE; color: #1D4ED8; }
.badge-gracia    { background: #FEF3C7; color: #92400E; }
.badge-suspendida{ background: #FEE2E2; color: #991B1B; }
.badge-cancelada { background: #F3F4F6; color: #6B7280; }

.acciones-col { white-space: nowrap; }
.btn-accion {
  padding: 0.3rem 0.75rem; border-radius: 6px; font-size: 0.8rem; font-weight: 500;
  cursor: pointer; border: 1px solid transparent; font-family: inherit; text-decoration: none;
  display: inline-block; transition: opacity 0.15s;
}
.btn-accion:hover { opacity: 0.85; }
.btn-reactivar { background: #059669; color: #fff; }
.btn-extender  { background: #D97706; color: #fff; }
.btn-pagos     { background: #4F46E5; color: #fff; }
</style>
