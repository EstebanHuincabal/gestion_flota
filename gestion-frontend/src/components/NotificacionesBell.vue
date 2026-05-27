<template>
  <div class="relative" ref="bellRef">
    <!-- Campana -->
    <button
      @click="toggleDropdown"
      class="relative p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition"
      title="Notificaciones"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
      </svg>
      <span
        v-if="noLeidas > 0"
        class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center"
      >
        {{ noLeidas > 99 ? '99+' : noLeidas }}
      </span>
    </button>

    <!-- Dropdown -->
    <div
      v-if="abierto"
      class="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-lg border border-gray-100 z-50 overflow-hidden"
    >
      <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <span class="text-sm font-semibold text-gray-900">Notificaciones</span>
        <button
          v-if="noLeidas > 0"
          @click="marcarTodas"
          class="text-xs text-indigo-600 hover:text-indigo-800"
        >
          Marcar todas
        </button>
      </div>

      <ul class="max-h-72 overflow-y-auto divide-y divide-gray-50">
        <li
          v-for="n in recientes" :key="n.id"
          @click="abrir(n)"
          :class="['flex items-start gap-3 px-4 py-3 cursor-pointer hover:bg-gray-50 transition', !n.leida && 'bg-indigo-50/40']"
        >
          <div :class="['flex-shrink-0 mt-0.5 w-2 h-2 rounded-full', !n.leida ? 'bg-indigo-500' : 'bg-transparent']"></div>
          <div class="flex-1 min-w-0">
            <p :class="['text-xs text-gray-900 truncate', !n.leida && 'font-semibold']">{{ n.titulo }}</p>
            <p class="text-xs text-gray-500 truncate mt-0.5">{{ n.mensaje }}</p>
            <p class="text-[10px] text-gray-400 mt-1">{{ formatRelativo(n.fecha) }}</p>
          </div>
        </li>
        <li v-if="recientes.length === 0" class="px-4 py-6 text-center text-xs text-gray-500">
          No hay notificaciones recientes
        </li>
      </ul>

      <div class="border-t border-gray-100 px-4 py-2.5 text-center">
        <router-link
          :to="baseUrl + '/notificaciones'"
          @click="abierto = false"
          class="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
        >
          Ver todas las notificaciones →
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../utils/api.js'

const router = useRouter()
const usuario = JSON.parse(localStorage.getItem('usuario') || '{}')
const baseUrl = computed(() => usuario.rol === 'SUPERADMIN' ? '' : '/empresa')

const noLeidas = ref(0)
const recientes = ref([])
const abierto   = ref(false)
const bellRef   = ref(null)

let ws = null
let wsReconnectDelay = 1000
let wsReconnectTimer = null

const fetchConteo = async () => {
  try {
    const res = await apiFetch('/api/notificaciones/no-leidas/')
    if (res.ok) noLeidas.value = (await res.json()).count
  } catch {}
}

function conectarWS() {
  const token = localStorage.getItem('access_token')
  if (!token) return

  // En dev conecta directo al backend (evita problemas con el proxy WS de Vite)
  // En producción usa el mismo host que sirve la app
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const host  = import.meta.env.DEV ? '127.0.0.1:8000' : location.host
  ws = new WebSocket(`${proto}://${host}/ws/notificaciones/?token=${token}`)

  ws.onopen = () => {
    wsReconnectDelay = 1000
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (import.meta.env.DEV) console.log('[WS notif] recibido:', data)
      if (data.type === 'nueva_notificacion') {
        if (import.meta.env.DEV) console.log('[WS notif] noLeidas antes:', noLeidas.value, '→', data.count)
        noLeidas.value = typeof data.count === 'number' ? data.count : noLeidas.value + 1
        if (import.meta.env.DEV) console.log('[WS notif] noLeidas después:', noLeidas.value)
        if (data.notificacion && !abierto.value) {
          recientes.value = [data.notificacion, ...recientes.value].slice(0, 10)
        }
        // Emitir evento global para que otros componentes reaccionen en tiempo real
        window.dispatchEvent(new CustomEvent('ws:notificacion', { detail: data.notificacion || {} }))
      }
    } catch (e) {
      if (import.meta.env.DEV) console.error('[WS notif] error:', e)
    }
  }

  ws.onclose = () => {
    wsReconnectTimer = setTimeout(() => {
      wsReconnectDelay = Math.min(wsReconnectDelay * 2, 30_000)
      conectarWS()
    }, wsReconnectDelay)
  }

  ws.onerror = () => ws.close()
}

const fetchRecientes = async () => {
  try {
    const res = await apiFetch('/api/notificaciones/?leida=false&page=1')
    if (res.ok) recientes.value = (await res.json()).results.slice(0, 10)
  } catch {}
}

const toggleDropdown = async () => {
  abierto.value = !abierto.value
  if (abierto.value) await fetchRecientes()
}

const abrir = async (n) => {
  if (!n.leida) {
    await apiFetch('/api/notificaciones/leer/', { method: 'POST', body: { ids: [n.id] } })
    n.leida = true
    noLeidas.value = Math.max(0, noLeidas.value - 1)
  }
  abierto.value = false
  if (n.url_accion) router.push(n.url_accion)
}

const marcarTodas = async () => {
  await apiFetch('/api/notificaciones/leer/', { method: 'POST', body: { todas: true } })
  recientes.value.forEach(n => (n.leida = true))
  noLeidas.value = 0
}

const cerrarSiAfuera = (e) => {
  if (bellRef.value && !bellRef.value.contains(e.target)) abierto.value = false
}

const formatRelativo = (fecha) => {
  const diff = Date.now() - new Date(fecha).getTime()
  const min = Math.floor(diff / 60000)
  if (min < 1)  return 'Ahora'
  if (min < 60) return `Hace ${min}m`
  const h = Math.floor(min / 60)
  if (h < 24)   return `Hace ${h}h`
  return `Hace ${Math.floor(h / 24)}d`
}

onMounted(() => {
  fetchConteo()
  conectarWS()
  document.addEventListener('click', cerrarSiAfuera)
})

onUnmounted(() => {
  clearTimeout(wsReconnectTimer)
  if (ws) ws.close()
  document.removeEventListener('click', cerrarSiAfuera)
})
</script>
