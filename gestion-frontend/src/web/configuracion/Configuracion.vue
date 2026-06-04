<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../../utils/api.js'
import { useToast } from '../../utils/useToast.js'
import ConfiguracionEmailTab from './tabs/ConfiguracionEmailTab.vue'

const toast = useToast()
const tabActivo = ref('planes')

const TABS = [
  { key: 'planes', label: 'Planes de suscripción' },
  { key: 'email',  label: 'Configuración de email' },
]

// ── Tab Planes ────────────────────────────────────────────────────────────────
const planes = ref([])
const cargandoPlanes = ref(false)

const cargarPlanes = async () => {
  cargandoPlanes.value = true
  try {
    const data = await apiFetch('/api/configuracion/planes/')
    planes.value = Array.isArray(data) ? data : (data.results ?? [])
  } catch {}
  cargandoPlanes.value = false
}

onMounted(() => {
  cargarPlanes()
})
</script>

<template>
  <div class="page">
    <!-- Encabezado -->
    <div class="page-header">
      <h1 class="page-titulo">Configuración del sistema</h1>
      <p class="page-subtitulo">Gestiona planes, notificaciones y otras opciones globales.</p>
    </div>

    <!-- Tabs -->
    <div class="tabs-bar">
      <button
        v-for="t in TABS"
        :key="t.key"
        class="tab-btn"
        :class="{ 'tab-btn--activo': tabActivo === t.key }"
        @click="tabActivo = t.key"
        type="button"
      >
        {{ t.label }}
      </button>
    </div>

    <!-- ── Tab: Planes ── -->
    <template v-if="tabActivo === 'planes'">
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">Planes disponibles</h2>
            <p class="card-desc">Límites de capacidad por plan comercial</p>
          </div>
          <button class="btn-secondary">+ Añadir plan</button>
        </div>
        <div class="card-body">
          <div v-if="cargandoPlanes" class="loading">
            <div class="spinner" />
          </div>
          <div v-else class="planes-grid">
            <div v-if="!planes.length" class="empty">
              No hay planes registrados.
            </div>
            <div
              v-for="plan in planes"
              :key="plan.id"
              class="plan-card"
            >
              <div class="plan-head">
                <h3 class="plan-nombre">{{ plan.nombre }}</h3>
                <button class="btn-link">Editar</button>
              </div>
              <div class="plan-body">
                <div class="plan-row">
                  <span class="plan-label">Vehículos</span>
                  <span class="plan-valor">{{ plan.max_vehiculos }}</span>
                </div>
                <div class="plan-row">
                  <span class="plan-label">Conductores</span>
                  <span class="plan-valor">{{ plan.max_conductores }}</span>
                </div>
                <div class="plan-row">
                  <span class="plan-label">Usuarios</span>
                  <span class="plan-valor">{{ plan.max_usuarios }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ── Tab: Email ── -->
    <ConfiguracionEmailTab v-else-if="tabActivo === 'email'" />
  </div>
</template>

<style scoped>
.page         { padding: 2rem; max-width: 1100px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.5rem; }
.page-header  { display: flex; flex-direction: column; gap: 0.25rem; }
.page-titulo  { font-size: 1.75rem; font-weight: 700; color: #111827; margin: 0; }
.page-subtitulo { font-size: 0.875rem; color: #6B7280; margin: 0; }

/* Tabs */
.tabs-bar {
  display: flex; gap: 0.25rem;
  background: #F3F4F6; border-radius: 10px; padding: 0.25rem; width: fit-content;
}
.tab-btn {
  padding: 0.5rem 1.25rem;
  background: none; border: none; border-radius: 8px;
  font-size: 0.875rem; font-weight: 500; color: #6B7280;
  cursor: pointer; transition: all 0.15s; font-family: inherit;
}
.tab-btn:hover      { color: #374151; }
.tab-btn--activo    { background: #fff; color: #111827; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }

/* Card */
.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; overflow: hidden; }
.card-header {
  padding: 1.25rem 1.5rem 1rem; border-bottom: 1px solid #F3F4F6;
  display: flex; align-items: center; justify-content: space-between;
}
.card-title { font-size: 1rem; font-weight: 600; color: #111827; margin: 0 0 0.2rem; }
.card-desc  { font-size: 0.8125rem; color: #6B7280; margin: 0; }
.card-body  { padding: 1.5rem; }

/* Planes */
.planes-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem;
}
.loading { display: flex; justify-content: center; padding: 2.5rem; }
.spinner {
  width: 28px; height: 28px;
  border: 3px solid #E5E7EB; border-top-color: var(--color-accent, #4F46E5);
  border-radius: 50%; animation: spin 0.75s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.empty { color: #9CA3AF; font-size: 0.875rem; text-align: center; padding: 2rem; }

.plan-card { border: 1px solid #E5E7EB; border-radius: 10px; overflow: hidden; }
.plan-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.75rem 1rem; background: #F9FAFB; border-bottom: 1px solid #E5E7EB;
}
.plan-nombre { font-size: 0.9375rem; font-weight: 700; color: #111827; margin: 0; text-transform: capitalize; }
.btn-link    { background: none; border: none; font-size: 0.8125rem; color: var(--color-accent, #4F46E5); cursor: pointer; font-weight: 500; }
.btn-link:hover { text-decoration: underline; }
.plan-body   { padding: 0.875rem 1rem; display: flex; flex-direction: column; gap: 0.5rem; }
.plan-row    { display: flex; justify-content: space-between; align-items: center; }
.plan-label  { font-size: 0.8125rem; color: #6B7280; }
.plan-valor  { font-size: 0.875rem; font-weight: 600; color: #111827; }

/* Botones */
.btn-secondary {
  padding: 0.5rem 1rem;
  background: #fff; color: #374151;
  border: 1px solid #D1D5DB; border-radius: 8px;
  font-size: 0.875rem; font-weight: 500; cursor: pointer;
  font-family: inherit; transition: background 0.15s;
}
.btn-secondary:hover { background: #F9FAFB; }
</style>
