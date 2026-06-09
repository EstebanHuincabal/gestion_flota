<script setup>
/**
 * SelectorEmpresa.vue — Selector de empresa para módulos del panel SUPERADMIN.
 *
 * Solo se muestra para SUPERADMIN. Guarda la empresa elegida en sessionStorage
 * (vía empresaActiva.js) para que apiFetch inyecte ?empresa_id= automáticamente,
 * y emite `cambio` (empresa | null) para que el módulo recargue sus datos.
 *
 * Uso:
 *   <SelectorEmpresa @cambio="onCambioEmpresa" />
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { apiFetch, safeJsonParse } from '../utils/api.js'
import { getEmpresaActiva, setEmpresaActiva, clearEmpresaActiva, EMPRESA_TODAS } from '../utils/empresaActiva.js'

const emit = defineEmits(['cambio'])

// Opción especial "Todas": muestra los datos de todas las empresas a la vez.
// Viaja por la misma tubería que una empresa normal (id centinela), por lo que
// apiFetch inyecta ?empresa_id=__todas__ y el backend filtra (o no) en consecuencia.
const OPCION_TODAS = { id: EMPRESA_TODAS, nombre: 'Todas las empresas' }

const esSuperadmin = computed(() => {
  const usuario = safeJsonParse(localStorage.getItem('usuario'), {})
  return usuario.rol === 'SUPERADMIN'
})

const empresas         = ref([])
const seleccionada     = ref(getEmpresaActiva())
const busqueda         = ref('')
const cargando         = ref(false)
const abierto          = ref(false)

const filtradas = computed(() => {
  const q = busqueda.value.toLowerCase().trim()
  if (!q) return empresas.value
  return empresas.value.filter(e => e.nombre.toLowerCase().includes(q))
})

// La opción "Todas" se muestra salvo que la búsqueda no coincida con su texto.
const mostrarTodas = computed(() => {
  const q = busqueda.value.toLowerCase().trim()
  return !q || 'todas las empresas'.includes(q)
})
const esTodas = computed(() => seleccionada.value?.id === EMPRESA_TODAS)

async function cargarEmpresas() {
  cargando.value = true
  try {
    const res = await apiFetch('/api/empresas/')
    if (res.ok) empresas.value = await res.json()
  } catch {
    empresas.value = []
  } finally {
    cargando.value = false
  }
}

function seleccionar(emp) {
  seleccionada.value = { id: emp.id, nombre: emp.nombre }
  busqueda.value     = ''
  abierto.value      = false
  setEmpresaActiva(emp)
  emit('cambio', seleccionada.value)
}

function limpiar() {
  seleccionada.value = null
  abierto.value      = false
  clearEmpresaActiva()
  emit('cambio', null)
}

function cerrarFuera() { abierto.value = false }

onMounted(() => {
  if (!esSuperadmin.value) return
  cargarEmpresas()
  document.addEventListener('click', cerrarFuera)
})
onUnmounted(() => document.removeEventListener('click', cerrarFuera))
</script>

<template>
  <div v-if="esSuperadmin" class="se-wrap">
    <label class="se-label">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:16px;height:16px;color:#6366F1">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
          d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
      </svg>
      Empresa
    </label>

    <div class="se-selector">
      <button
        class="se-btn"
        :class="{ 'se-btn--active': seleccionada }"
        @click.stop="abierto = !abierto"
      >
        <span v-if="seleccionada" class="se-nombre">{{ seleccionada.nombre }}</span>
        <span v-else class="se-placeholder">Selecciona una empresa…</span>
        <span v-if="seleccionada" class="se-clear" @click.stop="limpiar" title="Limpiar">✕</span>
        <svg v-else fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:16px;height:16px;color:#9CA3AF;flex-shrink:0">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
        </svg>
      </button>

      <div v-if="abierto" class="se-dropdown" @click.stop>
        <div class="se-search">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:15px;height:15px;color:#9CA3AF;flex-shrink:0">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
          </svg>
          <input v-model="busqueda" type="text" placeholder="Buscar empresa…" class="se-input"/>
        </div>

        <div class="se-list">
          <div v-if="cargando" class="se-loading">Cargando…</div>
          <template v-else>
          <button
            v-if="mostrarTodas"
            class="se-item se-item--todas"
            :class="{ 'se-item--selected': esTodas }"
            @click="seleccionar(OPCION_TODAS)"
          >
            <span class="se-avatar se-avatar--todas">★</span>
            <div class="se-item-info">
              <span class="se-item-nombre">Todas las empresas</span>
              <span class="se-item-rut">Ver datos de todas las empresas</span>
            </div>
            <span v-if="esTodas" style="color:#6366F1;font-size:0.875rem">✓</span>
          </button>
          <div v-if="filtradas.length === 0 && !mostrarTodas" class="se-empty">Sin resultados</div>
          <button
            v-for="emp in filtradas"
            :key="emp.id"
            class="se-item"
            :class="{ 'se-item--selected': seleccionada?.id === emp.id }"
            @click="seleccionar(emp)"
          >
            <span class="se-avatar">{{ emp.nombre[0]?.toUpperCase() }}</span>
            <div class="se-item-info">
              <span class="se-item-nombre">{{ emp.nombre }}</span>
              <span class="se-item-rut">{{ emp.rut || '' }}</span>
            </div>
            <span v-if="seleccionada?.id === emp.id" style="color:#6366F1;font-size:0.875rem">✓</span>
          </button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.se-wrap { margin-bottom: 1.25rem; }
.se-label {
  display: flex; align-items: center; gap: 0.4rem;
  font-size: 0.8rem; font-weight: 600; color: #6B7280; margin-bottom: 0.4rem;
}
.se-selector { position: relative; max-width: 380px; }
.se-btn {
  width: 100%; display: flex; align-items: center; gap: 0.5rem;
  padding: 0.6rem 0.85rem; background: #fff;
  border: 1.5px solid #E5E7EB; border-radius: 10px;
  font-size: 0.875rem; cursor: pointer; transition: border-color 0.15s;
}
.se-btn:hover { border-color: #C7D2FE; }
.se-btn--active { border-color: #6366F1; }
.se-nombre { flex: 1; text-align: left; color: #111827; font-weight: 500; }
.se-placeholder { flex: 1; text-align: left; color: #9CA3AF; }
.se-clear {
  color: #9CA3AF; font-size: 0.85rem; padding: 0 0.25rem; border-radius: 4px;
}
.se-clear:hover { color: #DC2626; background: #FEE2E2; }
.se-dropdown {
  position: absolute; top: calc(100% + 4px); left: 0; right: 0; z-index: 50;
  background: #fff; border: 1px solid #E5E7EB; border-radius: 10px;
  box-shadow: 0 12px 32px rgba(0,0,0,0.14); overflow: hidden;
}
.se-search {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.6rem 0.75rem; border-bottom: 1px solid #F3F4F6;
}
.se-input { flex: 1; border: none; outline: none; font-size: 0.85rem; color: #111827; background: transparent; }
.se-list { max-height: 16rem; overflow-y: auto; }
.se-loading, .se-empty { padding: 1rem; text-align: center; font-size: 0.8rem; color: #9CA3AF; }
.se-item {
  width: 100%; display: flex; align-items: center; gap: 0.6rem;
  padding: 0.6rem 0.75rem; background: transparent; border: none;
  border-bottom: 1px solid #F9FAFB; cursor: pointer; text-align: left;
}
.se-item:hover { background: #EEF2FF; }
.se-item--selected { background: #EEF2FF; }
.se-avatar {
  width: 32px; height: 32px; border-radius: 8px; flex-shrink: 0;
  background: linear-gradient(135deg, #6366F1, #8B5CF6); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.85rem; font-weight: 700;
}
.se-avatar--todas { background: linear-gradient(135deg, #0EA5E9, #6366F1); }
.se-item--todas { border-bottom: 1px solid #EEF2FF; }
.se-item-info { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.se-item-nombre { font-size: 0.875rem; font-weight: 600; color: #111827; }
.se-item-rut { font-size: 0.72rem; color: #9CA3AF; }
</style>
