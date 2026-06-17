<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../../../../utils/api.js'
import { apiFetchEmpresa, useEmpresaNav, getEmpresaActiva, setEmpresaActiva, conOpcionTodas, EMPRESA_TODAS } from '../../../../utils/empresaActiva.js'
import { useToast } from '../../../../utils/useToast.js'

const router = useRouter()
const { ruta } = useEmpresaNav()
const toast = useToast()

const hoy         = new Date()
const anio        = ref(hoy.getFullYear())
const mes         = ref(hoy.getMonth() + 1)
const calendario  = ref({})
const cargando    = ref(true)
const diaSelected = ref(null)

const esSuperadmin     = JSON.parse(localStorage.getItem('usuario') || '{}').rol === 'SUPERADMIN'
const empresaActiva    = ref(getEmpresaActiva())
const empresas         = ref([])
const cargandoEmpresas = ref(false)
const mostrarDropdown  = ref(false)
const busqueda         = ref('')
const sinEmpresa       = computed(() => esSuperadmin && !empresaActiva.value)
// Modo "Todas las empresas": solo lectura.
const esTodas = computed(() => empresaActiva.value?.id === EMPRESA_TODAS)

const empresasFiltradas = computed(() => {
  if (!busqueda.value.trim()) return empresas.value
  const q = busqueda.value.toLowerCase()
  return empresas.value.filter(e => e.nombre.toLowerCase().includes(q))
})

const cargarEmpresas = async () => {
  if (!esSuperadmin) return
  cargandoEmpresas.value = true
  try {
    const res = await apiFetch('/api/empresas/')
    if (res.ok) empresas.value = conOpcionTodas(await res.json())
  } finally {
    cargandoEmpresas.value = false
  }
}

const seleccionarEmpresa = (emp) => {
  setEmpresaActiva(emp)
  empresaActiva.value   = { id: emp.id, nombre: emp.nombre }
  mostrarDropdown.value = false
  busqueda.value        = ''
  cargarMes()
}

const MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
const DIAS  = ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom']

const tituloMes = computed(() => `${MESES[mes.value - 1]} ${anio.value}`)

const cargarMes = async () => {
  if (sinEmpresa.value) { cargando.value = false; return }
  cargando.value = true
  diaSelected.value = null
  try {
    const res = await apiFetchEmpresa(`/api/empresa/mantenciones/calendario/?year=${anio.value}&month=${mes.value}`)
    if (res.ok) calendario.value = await res.json()
    else calendario.value = {}
  } finally {
    cargando.value = false
  }
}

const mesAnterior = () => {
  if (mes.value === 1) { mes.value = 12; anio.value-- }
  else mes.value--
}
const mesSiguiente = () => {
  if (mes.value === 12) { mes.value = 1; anio.value++ }
  else mes.value++
}

const diasDelMes = computed(() => {
  const primerDia = new Date(anio.value, mes.value - 1, 1)
  const ultimoDia = new Date(anio.value, mes.value, 0)
  const offset    = (primerDia.getDay() + 6) % 7
  const hoyISO    = hoy.toISOString().split('T')[0]
  const celdas    = []

  for (let i = 0; i < offset; i++) celdas.push(null)

  for (let d = 1; d <= ultimoDia.getDate(); d++) {
    const iso = `${anio.value}-${String(mes.value).padStart(2,'0')}-${String(d).padStart(2,'0')}`
    celdas.push({ numero: d, iso, esHoy: iso === hoyISO, eventos: calendario.value[iso] || [] })
  }

  while (celdas.length % 7 !== 0) celdas.push(null)
  return celdas
})

const totalEventos = computed(() =>
  Object.values(calendario.value).reduce((acc, arr) => acc + arr.length, 0)
)

const seleccionarDia = (dia) => {
  if (!dia || !dia.eventos.length) return
  diaSelected.value = diaSelected.value?.iso === dia.iso ? null : dia
}

const irEditar = (id) => router.push(ruta(`/mantenciones/${id}/editar`))

const chipClase = (estado) => ({
  pendiente:  'chip-yellow',
  en_proceso: 'chip-blue',
  realizada:  'chip-green',
}[estado] || 'chip-yellow')

const badgeClasePanel = (estado) => ({
  pendiente:  'badge-warning',
  en_proceso: 'badge-info',
  realizada:  'badge-success',
}[estado] || 'badge-warning')

watch([anio, mes], cargarMes)
onMounted(async () => { await Promise.all([cargarEmpresas(), cargarMes()]) })
</script>

<template>
  <div class="page">

    <!-- Encabezado -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Mantenciones</h1>
        <p class="page-subtitle">Gestiona el mantenimiento y costos de tu flota</p>
      </div>
      <div v-if="esSuperadmin" class="selector-wrap">
        <button class="selector-btn" :class="{ 'sin-sel': !empresaActiva }" @click="mostrarDropdown = !mostrarDropdown">
          <span class="selector-icono"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg></span>
          <span class="selector-texto">{{ empresaActiva ? empresaActiva.nombre : 'Seleccionar empresa…' }}</span>
          <svg class="selector-chevron" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
        </button>
        <div v-if="mostrarDropdown" class="selector-dropdown">
          <div class="dropdown-search">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            <input v-model="busqueda" placeholder="Buscar empresa..." class="dropdown-input" autofocus/>
          </div>
          <div v-if="cargandoEmpresas" class="dropdown-empty">Cargando...</div>
          <div v-else-if="!empresasFiltradas.length" class="dropdown-empty">Sin resultados</div>
          <button v-for="emp in empresasFiltradas" :key="emp.id" class="dropdown-option" :class="{ selected: empresaActiva?.id === emp.id }" @click="seleccionarEmpresa(emp)">
            <span class="option-avatar">{{ emp.nombre[0].toUpperCase() }}</span>
            <span class="option-nombre">{{ emp.nombre }}</span>
            <svg v-if="empresaActiva?.id === emp.id" class="option-check" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
          </button>
        </div>
        <div v-if="mostrarDropdown" class="dropdown-overlay" @click="mostrarDropdown = false"/>
      </div>
    </div>

    <!-- Sub-navegación -->
    <div class="subnav">
      <router-link :to="ruta('/mantenciones')"            class="subnav-tab" active-class="subnav-tab-active" exact>Programados</router-link>
      <router-link :to="ruta('/mantenciones/calendario')" class="subnav-tab" active-class="subnav-tab-active">Calendario</router-link>
      <router-link :to="ruta('/mantenciones/historial')"  class="subnav-tab" active-class="subnav-tab-active">Historial</router-link>
      <router-link :to="ruta('/mantenciones/nueva')"      class="subnav-btn">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
        Programar
      </router-link>
    </div>

    <div v-if="sinEmpresa" class="sin-empresa-box">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
      <p>Selecciona una empresa usando el selector de arriba a la derecha para ver su calendario.</p>
    </div>
    <div v-else-if="cargando" class="loading"><div class="spinner"/>Cargando...</div>

    <template v-else>
      <div class="layout-cal">
        <!-- Columna principal: calendario -->
        <div class="cal-wrap">
          <!-- Cabecera navegación -->
          <div class="cal-header">
            <button class="nav-btn" @click="mesAnterior">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
            </button>
            <span class="cal-titulo">{{ tituloMes }}</span>
            <button class="nav-btn" @click="mesSiguiente">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
            </button>
            <span class="cal-resumen">{{ totalEventos }} mantención{{ totalEventos !== 1 ? 'es' : '' }} este mes</span>
          </div>

          <!-- Grid días de semana -->
          <div class="cal-grid">
            <div v-for="d in DIAS" :key="d" class="cal-dia-nombre">{{ d }}</div>

            <template v-for="(celda, i) in diasDelMes" :key="i">
              <!-- Celda vacía (offset) -->
              <div v-if="!celda" class="cal-celda cal-celda-vacia"/>

              <!-- Celda de día -->
              <div
                v-else
                :class="[
                  'cal-celda',
                  celda.esHoy      && 'cal-celda-hoy',
                  celda.eventos.length && 'cal-celda-con-eventos',
                  diaSelected?.iso === celda.iso && 'cal-celda-selected'
                ]"
                @click="seleccionarDia(celda)"
              >
                <span class="cal-numero">{{ celda.numero }}</span>
                <div class="cal-chips">
                  <span
                    v-for="(ev, j) in celda.eventos.slice(0, 2)"
                    :key="j"
                    :class="['chip', chipClase(ev.estado)]"
                    :title="ev.vehiculo_patente + ' — ' + ev.tipo_mantencion"
                  >{{ ev.vehiculo_patente }}</span>
                  <span v-if="celda.eventos.length > 2" class="chip chip-more">+{{ celda.eventos.length - 2 }}</span>
                </div>
              </div>
            </template>
          </div>
        </div>

        <!-- Panel lateral: detalle del día seleccionado -->
        <div class="panel-detalle" v-if="diaSelected">
          <div class="panel-header">
            <h3 class="panel-titulo">
              {{ new Date(diaSelected.iso + 'T12:00:00').toLocaleDateString('es-CL', { weekday: 'long', day: 'numeric', month: 'long' }) }}
            </h3>
            <button class="panel-cerrar" @click="diaSelected = null">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
          <div class="panel-lista">
            <div v-for="ev in diaSelected.eventos" :key="ev.id" class="panel-item" @click="!esTodas && irEditar(ev.id)">
              <div class="panel-item-top">
                <span :class="['badge', badgeClasePanel(ev.estado)]">{{ ev.estado_display }}</span>
                <span class="panel-patente">{{ ev.vehiculo_patente }}</span>
              </div>
              <p class="panel-tipo">{{ ev.tipo_mantencion }}</p>
              <p v-if="esTodas && ev.empresa_nombre" class="panel-tipo" style="color:#4F46E5;font-weight:600">{{ ev.empresa_nombre }}</p>
            </div>
          </div>
        </div>

        <!-- Panel lateral vacío -->
        <div class="panel-detalle panel-vacio" v-else>
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" class="panel-icon"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
          <p>Haz clic en un día con mantenciones para ver el detalle</p>
        </div>
      </div>

      <!-- Leyenda -->
      <div class="leyenda">
        <span class="leyenda-item"><span class="chip chip-yellow">●</span> Pendiente</span>
        <span class="leyenda-item"><span class="chip chip-blue">●</span> En Proceso</span>
        <span class="leyenda-item"><span class="chip chip-green">●</span> Realizada</span>
      </div>
    </template>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }
.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; background: #F9FAFB; min-height: 100vh; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem; }
.page-title { font-size: 1.5rem; font-weight: 700; color: #111827; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }

.subnav { display: flex; align-items: center; gap: 0.25rem; border-bottom: 2px solid #E5E7EB; margin-bottom: 1.75rem; }
.subnav-tab { padding: 0.625rem 1rem; font-size: 0.875rem; font-weight: 500; color: #6B7280; text-decoration: none; border-bottom: 2px solid transparent; margin-bottom: -2px; transition: color 0.15s; }
.subnav-tab:hover { color: #4F46E5; }
.subnav-tab-active { color: #4F46E5; border-bottom-color: #4F46E5; font-weight: 600; }
.subnav-btn { margin-left: auto; display: inline-flex; align-items: center; gap: 0.375rem; padding: 0.45rem 1rem; background: linear-gradient(135deg,#4F46E5,#7C3AED); color: #fff; font-size: 0.8125rem; font-weight: 600; border-radius: 8px; text-decoration: none; transition: opacity 0.15s; }
.subnav-btn:hover { opacity: 0.9; }
.subnav-btn svg { width: 15px; height: 15px; }

/* Layout */
.layout-cal { display: flex; gap: 1.5rem; align-items: flex-start; }
.cal-wrap { flex: 1; background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }

/* Cabecera calendario */
.cal-header { display: flex; align-items: center; gap: 0.75rem; padding: 1rem 1.25rem; border-bottom: 1px solid #E5E7EB; }
.cal-titulo { font-size: 1rem; font-weight: 700; color: #111827; flex: 1; text-align: center; }
.cal-resumen { font-size: 0.8rem; color: #6B7280; }
.nav-btn { width: 32px; height: 32px; border-radius: 8px; border: 1px solid #E5E7EB; background: #fff; color: #6B7280; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.15s; }
.nav-btn:hover { border-color: #4F46E5; color: #4F46E5; }
.nav-btn svg { width: 16px; height: 16px; }

/* Grid */
.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); }
.cal-dia-nombre { padding: 0.625rem 0.5rem; text-align: center; font-size: 0.75rem; font-weight: 600; color: #6B7280; background: #F9FAFB; border-bottom: 1px solid #E5E7EB; border-right: 1px solid #F3F4F6; }
.cal-dia-nombre:last-child { border-right: none; }

.cal-celda { min-height: 90px; padding: 0.5rem; border-bottom: 1px solid #F3F4F6; border-right: 1px solid #F3F4F6; vertical-align: top; display: flex; flex-direction: column; gap: 0.25rem; }
.cal-celda:nth-child(7n) { border-right: none; }
.cal-celda-vacia { background: #F9FAFB; }
.cal-celda-hoy .cal-numero { background: #4F46E5; color: #fff; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; }
.cal-celda-con-eventos { cursor: pointer; }
.cal-celda-con-eventos:hover { background: #EEF2FF; }
.cal-celda-selected { background: #EEF2FF; }
.cal-numero { font-size: 0.8125rem; font-weight: 600; color: #374151; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; }
.cal-chips { display: flex; flex-direction: column; gap: 0.2rem; }

.chip { font-size: 0.6875rem; font-weight: 600; padding: 0.125rem 0.375rem; border-radius: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.chip-yellow { background: #FEF3C7; color: #92400E; }
.chip-blue   { background: #DBEAFE; color: #1E40AF; }
.chip-green  { background: #D1FAE5; color: #065F46; }
.chip-more   { background: #F3F4F6; color: #6B7280; }

/* Panel detalle */
.panel-detalle { width: 280px; flex-shrink: 0; background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); overflow: hidden; }
.panel-header { display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.25rem; border-bottom: 1px solid #E5E7EB; }
.panel-titulo { font-size: 0.875rem; font-weight: 700; color: #111827; margin: 0; text-transform: capitalize; }
.panel-cerrar { width: 28px; height: 28px; border: none; background: none; color: #9CA3AF; cursor: pointer; display: flex; align-items: center; justify-content: center; border-radius: 6px; }
.panel-cerrar:hover { background: #F3F4F6; color: #374151; }
.panel-cerrar svg { width: 16px; height: 16px; }
.panel-lista { padding: 0.75rem; display: flex; flex-direction: column; gap: 0.5rem; }
.panel-item { padding: 0.75rem; border: 1px solid #E5E7EB; border-radius: 10px; cursor: pointer; transition: background 0.15s; }
.panel-item:hover { background: #F9FAFB; border-color: #4F46E5; }
.panel-item-top { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }
.panel-patente { font-size: 0.8rem; font-weight: 700; color: #374151; }
.panel-tipo { font-size: 0.8125rem; color: #6B7280; margin: 0; }

.panel-vacio { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 2.5rem 1.5rem; text-align: center; }
.panel-icon { width: 40px; height: 40px; color: #D1D5DB; margin-bottom: 0.75rem; }
.panel-vacio p { font-size: 0.8125rem; color: #9CA3AF; margin: 0; }

/* Leyenda */
.leyenda { display: flex; gap: 1.25rem; margin-top: 1rem; }
.leyenda-item { display: flex; align-items: center; gap: 0.375rem; font-size: 0.8125rem; color: #6B7280; }

.badge { display: inline-flex; padding: 0.2rem 0.5rem; border-radius: 999px; font-size: 0.7rem; font-weight: 600; }
.badge-success { background: #D1FAE5; color: #065F46; }
.badge-warning { background: #FEF3C7; color: #92400E; }
.badge-info    { background: #DBEAFE; color: #1E40AF; }

.loading, .empty { display: flex; flex-direction: column; align-items: center; padding: 4rem; color: #6B7280; }
.spinner { width: 28px; height: 28px; border: 3px solid #E5E7EB; border-top-color: #7C3AED; border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 1rem; }
@keyframes spin { to { transform: rotate(360deg); } }
.sin-empresa-box { display: flex; flex-direction: column; align-items: center; gap: 1rem; padding: 4rem 2rem; text-align: center; color: #9CA3AF; }
.sin-empresa-box svg { width: 48px; height: 48px; color: #D1D5DB; }
.sin-empresa-box p { font-size: 0.9375rem; max-width: 360px; line-height: 1.6; margin: 0; }
.selector-wrap { position: relative; }
.selector-btn { display: flex; align-items: center; gap: 0.5rem; padding: 0.55rem 0.875rem; background: #fff; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; font-weight: 500; color: #374151; cursor: pointer; font-family: inherit; white-space: nowrap; transition: border-color 0.15s; max-width: 260px; }
.selector-btn:hover { border-color: #7C3AED; }
.selector-btn.sin-sel { border-style: dashed; color: #9CA3AF; }
.selector-icono svg { width: 16px; height: 16px; color: #6B7280; flex-shrink: 0; }
.selector-texto { flex: 1; overflow: hidden; text-overflow: ellipsis; text-align: left; }
.selector-chevron { width: 14px; height: 14px; color: #9CA3AF; flex-shrink: 0; }
.selector-dropdown { position: absolute; top: calc(100% + 6px); right: 0; width: 280px; background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.12); overflow: hidden; z-index: 200; max-height: 320px; display: flex; flex-direction: column; overflow-y: auto; }
.dropdown-search { display: flex; align-items: center; gap: 0.5rem; padding: 0.625rem 0.875rem; border-bottom: 1px solid #F3F4F6; flex-shrink: 0; }
.dropdown-search svg { width: 15px; height: 15px; color: #9CA3AF; flex-shrink: 0; }
.dropdown-input { flex: 1; border: none; outline: none; font-size: 0.875rem; color: #111827; font-family: inherit; background: transparent; }
.dropdown-empty { padding: 1rem; font-size: 0.8125rem; color: #9CA3AF; text-align: center; }
.dropdown-option { display: flex; align-items: center; gap: 0.625rem; width: 100%; padding: 0.625rem 0.875rem; background: none; border: none; cursor: pointer; text-align: left; font-family: inherit; transition: background 0.12s; }
.dropdown-option:hover { background: #F5F3FF; }
.dropdown-option.selected { background: #EEF2FF; }
.option-avatar { flex-shrink: 0; width: 28px; height: 28px; background: linear-gradient(135deg,#4F46E5,#7C3AED); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; color: #fff; }
.option-nombre { flex: 1; font-size: 0.875rem; font-weight: 500; color: #111827; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.option-check { width: 16px; height: 16px; color: #4F46E5; flex-shrink: 0; }
.dropdown-overlay { position: fixed; inset: 0; z-index: 199; }
</style>
