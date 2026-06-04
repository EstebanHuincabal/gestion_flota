<script setup>
/**
 * GastosCorrectivosEmpresa.vue — Página de gastos correctivos para el USUARIO.
 *
 * Punto de entrada del módulo desde el menú del panel de empresa. Aporta el
 * selector de período y delega el contenido en el componente GastosCorrectivos.
 */
import { ref } from 'vue'
import GastosCorrectivos from './GastosCorrectivos.vue'

const hoy     = new Date()
const mesSel  = ref(hoy.getMonth() + 1)
const anioSel = ref(hoy.getFullYear())
const meses   = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
const anios   = Array.from({ length: 5 }, (_, i) => hoy.getFullYear() - i)
</script>

<template>
  <div class="page">
    <div class="header">
      <div>
        <h1 class="titulo">Gastos correctivos</h1>
        <p class="subtitulo">Mantenciones no presupuestadas (fallas inesperadas)</p>
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

    <GastosCorrectivos :mes="mesSel" :anio="anioSel" />
  </div>
</template>

<style scoped>
.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; max-width: 1200px; }
.header { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
.titulo { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.subtitulo { font-size: 0.875rem; color: #6B7280; margin: 0; }
.periodo { display: flex; gap: 0.5rem; }
.sel { padding: 0.5rem 0.75rem; border: 1.5px solid #E5E7EB; border-radius: 8px; font-size: 0.875rem; background: #fff; color: #374151; cursor: pointer; }
@media (max-width: 1024px) { .page { padding: 1rem; } }
</style>
