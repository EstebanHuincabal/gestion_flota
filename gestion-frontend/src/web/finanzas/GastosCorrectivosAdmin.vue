<script setup>
/**
 * GastosCorrectivosAdmin.vue — Vista de gastos correctivos para el SUPERADMIN.
 *
 * Reutiliza el componente GastosCorrectivos, agregando un selector de empresa
 * (el super-admin elige de qué empresa ver los correctivos) y un selector de
 * período. El SelectorEmpresa guarda la empresa activa que apiFetchEmpresa usa.
 */
import { ref } from 'vue'
import SelectorEmpresa from '../../components/SelectorEmpresa.vue'
import GastosCorrectivos from './GastosCorrectivos.vue'
import { getEmpresaActiva } from '../../utils/empresaActiva.js'

const hoy     = new Date()
const mesSel  = ref(hoy.getMonth() + 1)
const anioSel = ref(hoy.getFullYear())
const meses   = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
const anios   = Array.from({ length: 5 }, (_, i) => hoy.getFullYear() - i)

const empresa = ref(getEmpresaActiva())
function onCambioEmpresa(emp) { empresa.value = emp }
</script>

<template>
  <div class="page">
    <div class="header">
      <div>
        <h1 class="titulo">Gastos correctivos</h1>
        <p class="subtitulo">Mantenciones no presupuestadas por empresa</p>
      </div>
      <div class="periodo">
        <select v-model.number="mesSel" class="sel">
          <option v-for="(m, i) in meses" :key="i" :value="i + 1">{{ m }}</option>
        </select>
        <select v-model.number="anioSel" class="sel">
          <option v-for="a in anios" :key="a" :value="a">{{ a }}</option>
        </select>
      </div>
    </div>

    <SelectorEmpresa @cambio="onCambioEmpresa" />

    <!-- Sin empresa seleccionada -->
    <div v-if="!empresa" class="vacio">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
      </svg>
      <p>Selecciona una empresa para ver sus gastos correctivos.</p>
    </div>

    <!-- key fuerza remontar el componente al cambiar de empresa -->
    <GastosCorrectivos
      v-else
      :key="empresa.id"
      :mes="mesSel"
      :anio="anioSel"
    />
  </div>
</template>

<style scoped>
.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; max-width: 1200px; }
.header { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
.titulo { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.subtitulo { font-size: 0.875rem; color: #6B7280; margin: 0; }
.periodo { display: flex; gap: 0.5rem; }
.sel { padding: 0.5rem 0.75rem; border: 1.5px solid #E5E7EB; border-radius: 8px; font-size: 0.875rem; background: #fff; color: #374151; cursor: pointer; }
.vacio { display: flex; flex-direction: column; align-items: center; gap: 0.75rem; padding: 3rem 1rem; color: #9CA3AF; text-align: center; }
.vacio svg { width: 48px; height: 48px; color: #D1D5DB; }
</style>
