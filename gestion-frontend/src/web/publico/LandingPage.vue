<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../../utils/api.js'

const router  = useRouter()
const planes  = ref([])
const cargandoPlanes = ref(true)

onMounted(async () => {
  try {
    const res = await fetch('/api/planes/')
    if (res.ok) planes.value = await res.json()
  } catch {}
  cargandoPlanes.value = false
})

function precio(plan) {
  const p = plan.precio_mensual
  if (!p) return 'A consultar'
  return new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(Number(p))
}

function contratar(plan) {
  router.push({ name: 'registro', query: { plan_id: plan.id } })
}

const FEATURES = [
  {
    icon: `<path stroke-linecap="round" stroke-linejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12"/>`,
    titulo: 'Gestión de flota completa',
    descripcion: 'Administra flotas, vehículos y conductores desde un panel centralizado. Historial, asignaciones y estados en tiempo real.',
    color: 'bg-indigo-50 text-indigo-600',
  },
  {
    icon: `<path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>`,
    titulo: 'Mantención predictiva',
    descripcion: 'Reglas automáticas por tipo de servicio. Alertas antes de que fallen los vehículos. Reduce costos de reparación hasta un 30%.',
    color: 'bg-purple-50 text-purple-600',
  },
  {
    icon: `<path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>`,
    titulo: 'Control de documentos',
    descripcion: 'Permisos de circulación, revisiones técnicas, SOAP y licencias con alertas de vencimiento automáticas para toda la flota.',
    color: 'bg-emerald-50 text-emerald-600',
  },
  {
    icon: `<path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>`,
    titulo: 'Gestión de conductores',
    descripcion: 'Asignaciones vehículo-conductor, historial completo, documentos y solicitudes desde la app móvil dedicada.',
    color: 'bg-amber-50 text-amber-600',
  },
  {
    icon: `<path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>`,
    titulo: 'Reportes y análisis',
    descripcion: 'Dashboards con KPIs de flota, costos de mantención, TCO por vehículo y exportación a Excel. Decisiones con datos reales.',
    color: 'bg-sky-50 text-sky-600',
  },
  {
    icon: `<path stroke-linecap="round" stroke-linejoin="round" d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"/>`,
    titulo: 'App móvil para conductores',
    descripcion: 'App iOS/Android para conductores: rutas, checklist pre-viaje, solicitudes de mantención con foto y modo offline.',
    color: 'bg-rose-50 text-rose-600',
  },
]

const PLAN_HIGHLIGHT = { pro: true }

function scrollAPrecios() {
  document.getElementById('precios')?.scrollIntoView({ behavior: 'smooth' })
}
</script>

<template>
  <!-- ── HERO ────────────────────────────────────────────────────────────── -->
  <section class="relative min-h-screen flex items-center overflow-hidden bg-gradient-to-br from-slate-900 via-purple-950 to-slate-900">
    <!-- Orbes decorativos -->
    <div class="absolute top-0 right-0 w-[600px] h-[600px] bg-purple-700/20 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3 pointer-events-none"/>
    <div class="absolute bottom-0 left-0 w-[400px] h-[400px] bg-indigo-700/20 rounded-full blur-3xl translate-y-1/2 -translate-x-1/4 pointer-events-none"/>

    <div class="relative max-w-3xl mx-auto px-6 pt-32 pb-24 text-center">
      <!-- Texto -->
      <div>
        <div class="inline-flex items-center px-3 py-1.5 rounded-full bg-white/10 border border-white/20 text-white/80 text-xs font-medium mb-6">
          Sistema SaaS para gestión de flota en Chile
        </div>
        <h1 class="text-4xl md:text-5xl lg:text-6xl font-extrabold text-white leading-tight tracking-tight mb-6">
          Controla tu flota,<br>
          <span class="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            reduce costos.
          </span>
        </h1>
        <p class="text-lg text-white/65 leading-relaxed max-w-xl mx-auto mb-10">
          Mantención predictiva, documentos, conductores y rutas en una sola plataforma.
          Diseñado para empresas de transporte en Chile.
        </p>
        <div class="flex flex-wrap justify-center gap-4">
          <button
            @click="router.push('/registro')"
            class="px-7 py-3.5 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold text-sm shadow-lg shadow-purple-900/40 hover:opacity-90 active:scale-95 transition-all"
          >
            Comenzar ahora →
          </button>
          <button
            @click="scrollAPrecios"
            class="px-7 py-3.5 rounded-xl border border-white/25 text-white/85 font-semibold text-sm hover:bg-white/10 transition-colors"
          >
            Ver planes
          </button>
        </div>

      </div>

    </div>
  </section>

  <!-- ── CARACTERÍSTICAS ──────────────────────────────────────────────── -->
  <section id="caracteristicas" class="py-24 bg-white">
    <div class="max-w-6xl mx-auto px-6">
      <div class="text-center mb-16">
        <h2 class="text-3xl md:text-4xl font-extrabold text-gray-900 tracking-tight mb-4">
          Todo lo que necesita tu flota
        </h2>
        <p class="text-lg text-gray-500 max-w-xl mx-auto">
          Una plataforma completa para gestionar vehículos, conductores, mantenciones y documentos.
        </p>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-8">
        <div
          v-for="f in FEATURES" :key="f.titulo"
          class="group p-6 rounded-2xl border border-gray-100 hover:border-indigo-100 hover:shadow-lg hover:shadow-indigo-50 transition-all duration-300"
        >
          <div class="w-10 h-10 rounded-xl flex items-center justify-center mb-4" :class="f.color">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24" v-html="f.icon"/>
          </div>
          <h3 class="text-base font-semibold text-gray-900 mb-2">{{ f.titulo }}</h3>
          <p class="text-sm text-gray-500 leading-relaxed">{{ f.descripcion }}</p>
        </div>
      </div>
    </div>
  </section>

  <!-- ── PRECIOS ──────────────────────────────────────────────────────── -->
  <section id="precios" class="py-24 bg-gray-50">
    <div class="max-w-6xl mx-auto px-6">
      <div class="text-center mb-12">
        <h2 class="text-3xl md:text-4xl font-extrabold text-gray-900 tracking-tight mb-4">
          Planes simples y transparentes
        </h2>
        <p class="text-gray-500 mb-8">Sin costos ocultos. Cambia de plan cuando lo necesites.</p>
      </div>

      <!-- Skeleton cargando -->
      <div v-if="cargandoPlanes" class="grid md:grid-cols-3 gap-6">
        <div v-for="i in 3" :key="i" class="rounded-2xl bg-white border border-gray-100 p-8 animate-pulse">
          <div class="h-4 bg-gray-200 rounded w-20 mb-3"/>
          <div class="h-8 bg-gray-200 rounded w-32 mb-6"/>
          <div v-for="j in 4" :key="j" class="h-3 bg-gray-100 rounded mb-3"/>
        </div>
      </div>

      <!-- Cards de planes -->
      <div v-else class="grid md:grid-cols-3 gap-6">
        <div
          v-for="plan in planes" :key="plan.id"
          class="relative rounded-2xl bg-white border-2 p-8 flex flex-col transition-all duration-300"
          :class="PLAN_HIGHLIGHT[plan.nombre]
            ? 'border-indigo-500 shadow-xl shadow-indigo-100 scale-[1.02]'
            : 'border-gray-100 hover:border-indigo-200 hover:shadow-lg'"
        >
          <!-- Badge popular -->
          <div
            v-if="PLAN_HIGHLIGHT[plan.nombre]"
            class="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white text-xs font-bold shadow-md"
          >
            Más popular
          </div>

          <div class="mb-6">
            <p class="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-1">{{ plan.nombre_display }}</p>
            <div class="flex items-end gap-1 mb-2">
              <span class="text-4xl font-extrabold text-gray-900">{{ precio(plan) }}</span>
              <span v-if="plan.precio_mensual" class="text-gray-400 text-sm pb-1">/mes</span>
            </div>
            <p v-if="plan.descripcion" class="text-sm text-gray-500">{{ plan.descripcion }}</p>
          </div>

          <!-- Límites -->
          <ul class="space-y-2.5 mb-8 flex-1">
            <li class="flex items-center gap-2 text-sm text-gray-700">
              <svg class="w-4 h-4 text-emerald-500 shrink-0" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
              </svg>
              <strong>{{ plan.max_vehiculos }}</strong>&nbsp;vehículos
            </li>
            <li class="flex items-center gap-2 text-sm text-gray-700">
              <svg class="w-4 h-4 text-emerald-500 shrink-0" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
              </svg>
              <strong>{{ plan.max_conductores }}</strong>&nbsp;conductores
            </li>
            <li class="flex items-center gap-2 text-sm text-gray-700">
              <svg class="w-4 h-4 text-emerald-500 shrink-0" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
              </svg>
              <strong>{{ plan.max_usuarios }}</strong>&nbsp;usuarios admin
            </li>
            <li v-for="mod in plan.modulos" :key="mod" class="flex items-center gap-2 text-sm text-gray-700">
              <svg class="w-4 h-4 text-emerald-500 shrink-0" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
              </svg>
              {{ mod.charAt(0).toUpperCase() + mod.slice(1) }}
            </li>
          </ul>

          <button
            @click="contratar(plan)"
            class="w-full py-3 rounded-xl font-semibold text-sm transition-all"
            :class="PLAN_HIGHLIGHT[plan.nombre]
              ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:opacity-90 shadow-md shadow-indigo-200'
              : 'bg-gray-900 text-white hover:bg-gray-700'"
          >
            Contratar {{ plan.nombre_display }}
          </button>
        </div>
      </div>

      <p class="text-center text-sm text-gray-400 mt-8">
        Pago seguro con Transbank Webpay Plus · Soporte en español · Datos alojados en Chile
      </p>
    </div>
  </section>

  <!-- ── CTA FINAL ────────────────────────────────────────────────────── -->
  <section class="py-24 bg-gradient-to-br from-slate-900 via-purple-950 to-slate-900">
    <div class="max-w-3xl mx-auto px-6 text-center">
      <h2 class="text-3xl md:text-4xl font-extrabold text-white tracking-tight mb-4">
        ¿Listo para optimizar tu flota?
      </h2>
      <p class="text-white/60 text-lg mb-10 max-w-xl mx-auto">
        Empieza hoy. Configura tu cuenta en menos de 5 minutos y comienza a ahorrar.
      </p>
      <button
        @click="router.push('/registro')"
        class="px-8 py-4 rounded-xl bg-white text-indigo-700 font-bold text-base hover:bg-gray-50 shadow-xl transition-all active:scale-95"
      >
        Comenzar ahora →
      </button>
    </div>
  </section>
</template>
