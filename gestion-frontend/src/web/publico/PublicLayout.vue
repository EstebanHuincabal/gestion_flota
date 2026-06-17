<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import { safeJsonParse } from '../../utils/api.js'

const router    = useRouter()
const scrolled  = ref(false)
const menuOpen  = ref(false)

function irALogin() { router.push('/login') }
function irARegistro() { router.push('/registro') }
function _scrollA(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
}

function irAPrecios() {
  if (router.currentRoute.value.name !== 'landing') {
    router.push('/').then(() => setTimeout(() => _scrollA('precios'), 400))
  } else {
    _scrollA('precios')
  }
}

function irACaracteristicas() {
  if (router.currentRoute.value.name !== 'landing') {
    router.push('/').then(() => setTimeout(() => _scrollA('caracteristicas'), 400))
  } else {
    _scrollA('caracteristicas')
  }
}

function onScroll() { scrolled.value = window.scrollY > 20 }
onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))
</script>

<template>
  <div class="min-h-screen bg-white font-inter">

    <!-- ── Navbar ──────────────────────────────────────────────────────── -->
    <header
      class="fixed top-0 inset-x-0 z-50 transition-all duration-300"
      :class="scrolled
        ? 'bg-white/95 backdrop-blur border-b border-gray-100 shadow-sm'
        : 'bg-transparent'"
    >
      <div class="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">

        <!-- Logo -->
        <a href="/" class="flex items-center gap-2.5 no-underline">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center">
            <svg class="w-4.5 h-4.5 text-white" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round"
                d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12"/>
            </svg>
          </div>
          <span
            class="text-base font-bold tracking-tight"
            :class="scrolled ? 'text-gray-900' : 'text-white'"
          >FlotaSystem</span>
        </a>

        <!-- Links desktop -->
        <nav class="hidden md:flex items-center gap-7">
          <button
            @click="irAPrecios"
            class="text-sm font-medium transition-colors"
            :class="scrolled ? 'text-gray-600 hover:text-gray-900' : 'text-white/80 hover:text-white'"
          >Precios</button>
          <button
            @click="irACaracteristicas"
            class="text-sm font-medium transition-colors"
            :class="scrolled ? 'text-gray-600 hover:text-gray-900' : 'text-white/80 hover:text-white'"
          >Características</button>
        </nav>

        <!-- CTAs desktop -->
        <div class="hidden md:flex items-center gap-3">
          <button
            @click="irALogin"
            class="text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
            :class="scrolled
              ? 'text-gray-700 hover:bg-gray-100'
              : 'text-white/90 hover:text-white hover:bg-white/10'"
          >Iniciar sesión</button>
          <button
            @click="irARegistro"
            class="text-sm font-semibold px-4 py-2 rounded-lg bg-white text-indigo-700 hover:bg-gray-50 transition-colors shadow-sm"
          >Comenzar ahora</button>
        </div>

        <!-- Hamburger mobile -->
        <button
          class="md:hidden p-2"
          :class="scrolled ? 'text-gray-700' : 'text-white'"
          @click="menuOpen = !menuOpen"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path v-if="!menuOpen" stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16"/>
            <path v-else stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <!-- Menú mobile -->
      <Transition name="slide-down">
        <div v-if="menuOpen" class="md:hidden bg-white border-t border-gray-100 px-6 py-4 flex flex-col gap-3">
          <button @click="irAPrecios; menuOpen=false" class="text-sm font-medium text-gray-700 text-left py-2">Precios</button>
          <button @click="irALogin; menuOpen=false" class="text-sm font-medium text-gray-700 text-left py-2">Iniciar sesión</button>
          <button @click="irARegistro; menuOpen=false" class="w-full py-2.5 rounded-lg bg-indigo-600 text-white text-sm font-semibold">Comenzar ahora</button>
        </div>
      </Transition>
    </header>

    <!-- ── Contenido de la ruta ──────────────────────────────────────── -->
    <RouterView />

    <!-- ── Footer ────────────────────────────────────────────────────── -->
    <footer class="bg-slate-900 text-white/60 py-12 px-6">
      <div class="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        <div class="flex items-center gap-2.5">
          <div class="w-7 h-7 rounded-md bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12"/>
            </svg>
          </div>
          <span class="text-white font-semibold text-sm">FlotaSystem</span>
        </div>
        <p class="text-xs">© {{ new Date().getFullYear() }} FlotaSystem · Sistema de Gestión de Flota · Chile</p>
        <div class="flex gap-5 text-xs">
          <a href="/terminos" class="hover:text-white transition-colors">Términos</a>
          <span>Contacto</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.slide-down-enter-active, .slide-down-leave-active { transition: all 0.2s ease; }
.slide-down-enter-from, .slide-down-leave-to { opacity: 0; transform: translateY(-8px); }
</style>
