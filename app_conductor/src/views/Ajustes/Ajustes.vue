<script setup>
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth.js'
import BottomNav from '@/components/BottomNav.vue'
import { iniciales } from '@/utils/formato.js'

const auth = useAuthStore()

// ── Confirmación de cierre de sesión ─────────────────────────────────────────
const confirmandoLogout = ref(false)
const cerrando          = ref(false)

async function handleLogout() {
  cerrando.value = true
  await auth.logout()
}
</script>

<template>
  <div class="min-h-dvh bg-gray-50 pb-nav">

    <!-- ── Header ──────────────────────────────────────────────────────────── -->
    <header class="bg-white px-4 pt-safe pb-4 border-b border-gray-100">
      <h1 class="text-lg font-bold text-gray-800">Ajustes</h1>
    </header>

    <div class="px-4 py-5 flex flex-col gap-4">

      <!-- ── Tarjeta de perfil ─────────────────────────────────────────────── -->
      <section class="bg-white rounded-2xl shadow-sm overflow-hidden">

        <!-- Banner superior + avatar ---------------------------------------->
        <div class="relative h-20" style="background: var(--color-acento)">
          <!-- Degradado oscuro en la parte inferior del banner -->
          <div class="absolute inset-0 bg-gradient-to-b from-transparent to-black/20"/>
        </div>

        <div class="px-5 pb-5">
          <!-- Avatar flotante -->
          <div class="flex items-end gap-4 -mt-8 mb-3">
            <div
              class="w-16 h-16 rounded-full flex items-center justify-center text-white text-xl font-bold shadow-lg border-3 border-white shrink-0"
              style="background: var(--color-acento); border-width: 3px; border-color: white"
            >
              {{ iniciales(auth.usuario?.nombre) }}
            </div>
            <div class="pb-1">
              <p class="text-xs text-gray-400 font-medium">CONDUCTOR</p>
            </div>
          </div>

          <!-- Datos del usuario -->
          <h2 class="text-lg font-bold text-gray-800 leading-tight">
            {{ auth.usuario?.nombre || auth.usuario?.email }}
          </h2>

          <div class="mt-2 flex flex-col gap-1.5">
            <!-- RUT -->
            <div class="flex items-center gap-2 text-sm text-gray-500">
              <svg class="w-4 h-4 shrink-0 text-gray-400" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2"/>
              </svg>
              <span>{{ auth.usuario?.rut || '—' }}</span>
            </div>

            <!-- Email -->
            <div v-if="auth.usuario?.email" class="flex items-center gap-2 text-sm text-gray-500">
              <svg class="w-4 h-4 shrink-0 text-gray-400" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
              </svg>
              <span>{{ auth.usuario.email }}</span>
            </div>

            <!-- Empresa -->
            <div v-if="auth.usuario?.empresa" class="flex items-center gap-2 text-sm text-gray-500">
              <svg class="w-4 h-4 shrink-0 text-gray-400" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
              </svg>
              <span>{{ auth.usuario.empresa }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- ── Vehículo asignado ──────────────────────────────────────────────── -->
      <section v-if="auth.usuario?.vehiculo_asignado" class="bg-white rounded-2xl shadow-sm p-5">
        <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Vehículo asignado
        </h3>

        <div class="flex items-center gap-4">
          <!-- Ícono camión -->
          <div
            class="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
            style="background: color-mix(in srgb, var(--color-acento) 12%, white)"
          >
            <svg class="w-6 h-6" style="color: var(--color-acento)" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0"/>
            </svg>
          </div>

          <div class="flex-1 min-w-0">
            <!-- Patente -->
            <p class="text-lg font-bold text-gray-800 font-mono tracking-wider">
              {{ auth.usuario.vehiculo_asignado.patente }}
            </p>
            <!-- Marca y modelo -->
            <p class="text-sm text-gray-500 truncate">
              {{ auth.usuario.vehiculo_asignado.marca }}
              {{ auth.usuario.vehiculo_asignado.modelo }}
            </p>
          </div>
        </div>
      </section>

      <!-- ── Sin vehículo ───────────────────────────────────────────────────── -->
      <section v-else class="bg-orange-50 border border-orange-200 rounded-2xl p-4 flex items-center gap-3">
        <svg class="w-5 h-5 text-orange-500 shrink-0" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
        </svg>
        <div>
          <p class="text-sm font-semibold text-orange-700">Sin vehículo asignado</p>
          <p class="text-xs text-orange-600 mt-0.5">Contacta a tu administrador para que te asigne un vehículo.</p>
        </div>
      </section>

      <!-- ── Sección app ────────────────────────────────────────────────────── -->
      <section class="bg-white rounded-2xl shadow-sm overflow-hidden">
        <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider px-5 pt-4 pb-2">
          Aplicación
        </h3>

        <!-- Versión -->
        <div class="flex items-center justify-between px-5 py-3 border-t border-gray-50">
          <div class="flex items-center gap-3">
            <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <span class="text-sm text-gray-700">Versión</span>
          </div>
          <span class="text-sm text-gray-400">1.0.0</span>
        </div>

        <!-- Empresa / sistema -->
        <div class="flex items-center justify-between px-5 py-3 border-t border-gray-50">
          <div class="flex items-center gap-3">
            <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
            </svg>
            <span class="text-sm text-gray-700">Sistema de Gestión de Flota</span>
          </div>
        </div>
      </section>

      <!-- ── Cerrar sesión ──────────────────────────────────────────────────── -->
      <section class="bg-white rounded-2xl shadow-sm overflow-hidden">
        <button
          @click="confirmandoLogout = true"
          class="w-full flex items-center gap-3 px-5 py-4 text-red-500 hover:bg-red-50 transition-colors min-h-[56px]"
        >
          <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
          </svg>
          <span class="text-sm font-semibold">Cerrar sesión</span>
        </button>
      </section>

    </div>

    <!-- ── Modal confirmación logout ─────────────────────────────────────────── -->
    <Transition name="overlay">
      <div
        v-if="confirmandoLogout"
        class="fixed inset-0 bg-black/50 z-40 flex items-end"
        @click.self="confirmandoLogout = false"
      >
        <Transition name="sheet">
          <div
            v-if="confirmandoLogout"
            class="w-full bg-white rounded-t-3xl p-6"
            style="padding-bottom: calc(1.5rem + env(safe-area-inset-bottom, 0px))"
          >
            <!-- Handle -->
            <div class="w-10 h-1 bg-gray-200 rounded-full mx-auto mb-5"/>

            <!-- Contenido -->
            <div class="flex flex-col items-center gap-1 mb-6">
              <div class="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center mb-2">
                <svg class="w-7 h-7 text-red-500" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
                </svg>
              </div>
              <h3 class="text-base font-bold text-gray-800">¿Cerrar sesión?</h3>
              <p class="text-sm text-gray-500 text-center">
                Se cerrará tu sesión en este dispositivo.
              </p>
            </div>

            <div class="flex gap-3">
              <button
                @click="confirmandoLogout = false"
                class="flex-1 py-3.5 rounded-xl border border-gray-200 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors min-h-[48px]"
              >
                Cancelar
              </button>
              <button
                @click="handleLogout"
                :disabled="cerrando"
                class="flex-1 py-3.5 rounded-xl text-sm font-semibold text-white bg-red-500 hover:bg-red-600 transition-colors min-h-[48px] flex items-center justify-center gap-2 disabled:opacity-60"
              >
                <span v-if="cerrando" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"/>
                <span>{{ cerrando ? 'Saliendo…' : 'Cerrar sesión' }}</span>
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>

    <!-- ── Bottom nav ─────────────────────────────────────────────────────── -->
    <BottomNav />

  </div>
</template>

<style scoped>
/* Overlay */
.overlay-enter-active, .overlay-leave-active { transition: opacity 0.25s ease; }
.overlay-enter-from, .overlay-leave-to       { opacity: 0; }

/* Bottom sheet */
.sheet-enter-active, .sheet-leave-active { transition: transform 0.3s ease; }
.sheet-enter-from, .sheet-leave-to       { transform: translateY(100%); }
</style>
