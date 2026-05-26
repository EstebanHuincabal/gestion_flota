<script setup>
import { ref } from 'vue'
import { useAuthStore }  from '@/stores/auth.js'
import { useThemeStore } from '@/stores/theme.js'
import BottomNav from '@/components/BottomNav.vue'
import { iniciales } from '@/utils/formato.js'

const auth       = useAuthStore()
const themeStore = useThemeStore()

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

    <!-- ── Header con gradiente ───────────────────────────────────────────── -->
    <header class="aj-profile-card">
      <!-- Patrón de fondo -->
      <div class="aj-pattern" aria-hidden="true"/>

      <!-- Contenido del perfil -->
      <div class="aj-profile-inner">
        <!-- Avatar grande -->
        <div class="aj-avatar">
          {{ iniciales(auth.usuario?.nombre) }}
          <span class="aj-avatar-ring" aria-hidden="true"/>
        </div>

        <!-- Info -->
        <div class="aj-profile-info">
          <p class="aj-role-label">Conductor</p>
          <h1 class="aj-name">{{ auth.usuario?.nombre || auth.usuario?.email }}</h1>

          <!-- Chips de datos -->
          <div class="aj-data-chips">
            <span v-if="auth.usuario?.rut" class="aj-chip">
              <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0"/>
              </svg>
              {{ auth.usuario.rut }}
            </span>
            <span v-if="auth.usuario?.empresa" class="aj-chip">
              <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5"/>
              </svg>
              {{ auth.usuario.empresa }}
            </span>
            <span v-if="auth.usuario?.email" class="aj-chip aj-chip--email">
              {{ auth.usuario.email }}
            </span>
          </div>
        </div>
      </div>
    </header>

    <div class="px-4 py-5 flex flex-col gap-4">

      <!-- ── Vehículo asignado ──────────────────────────────────────────────── -->
      <section v-if="auth.usuario?.vehiculo_asignado" class="aj-vehicle-card">
        <div class="aj-vehicle-icon">
          <svg class="w-6 h-6" style="color: var(--color-acento)" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/>
            <path stroke-linecap="round" stroke-linejoin="round" d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0"/>
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-0.5">Vehículo asignado</p>
          <p class="text-xl font-black text-gray-800 font-mono tracking-wider leading-tight">
            {{ auth.usuario.vehiculo_asignado.patente }}
          </p>
          <p class="text-sm text-gray-500 truncate">
            {{ auth.usuario.vehiculo_asignado.marca }}
            {{ auth.usuario.vehiculo_asignado.modelo }}
          </p>
        </div>
        <div class="aj-vehicle-badge">
          <span class="w-2 h-2 rounded-full bg-green-400 inline-block"/>
          Activo
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

      <!-- ── Sección app (estilo iOS) ─────────────────────────────────────── -->
      <section class="aj-settings-group">
        <p class="aj-group-title">Aplicación</p>

        <!-- Versión -->
        <div class="aj-settings-row aj-settings-row--first">
          <div class="aj-row-icon aj-row-icon--blue">
            <svg class="w-4 h-4" fill="white" stroke="none" viewBox="0 0 24 24">
              <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <span class="aj-row-label">Versión</span>
          <span class="aj-row-value">1.0.0</span>
        </div>

        <!-- Sistema -->
        <div class="aj-settings-row">
          <div class="aj-row-icon aj-row-icon--purple">
            <svg class="w-4 h-4" fill="white" stroke="none" viewBox="0 0 24 24">
              <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
            </svg>
          </div>
          <span class="aj-row-label">Sistema de Gestión de Flota</span>
        </div>
      </section>

      <!-- ── Apariencia ───────────────────────────────────────────────────────── -->
      <section class="aj-settings-group">
        <p class="aj-group-title">Apariencia</p>

        <!-- Label descriptivo -->
        <div class="aj-settings-row aj-settings-row--first">
          <div class="aj-row-icon" :style="`background: var(--gradient-primary)`">
            <svg class="w-4 h-4" fill="none" stroke="white" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round"
                d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/>
            </svg>
          </div>
          <div class="flex-1">
            <span class="aj-row-label">Color de la app</span>
            <p class="aj-row-sublabel">{{ themeStore.temaActual.nombre }} — {{ themeStore.temaActual.descripcion }}</p>
          </div>
        </div>

        <!-- Grid de temas -->
        <div class="theme-grid">
          <button
            v-for="tema in themeStore.TEMAS"
            :key="tema.id"
            class="theme-card"
            :class="{ 'theme-card--active': themeStore.temaActualId === tema.id }"
            @click="themeStore.cambiarTema(tema.id)"
            :aria-label="`Tema ${tema.nombre}`"
          >
            <!-- Muestra de gradiente -->
            <div
              class="theme-preview"
              :style="`background: linear-gradient(135deg, ${tema.colorGrad[0]} 0%, ${tema.colorGrad[1]} 100%)`"
            >
              <!-- Check si está activo -->
              <span v-if="themeStore.temaActualId === tema.id" class="theme-check">
                <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
                </svg>
              </span>

              <!-- Mini UI de preview (BottomNav + header simulados) -->
              <div class="theme-mini-ui" aria-hidden="true">
                <!-- mini header -->
                <div class="mini-header"/>
                <!-- mini nav -->
                <div class="mini-nav">
                  <span
                    v-for="i in 4" :key="i"
                    class="mini-dot"
                    :class="i === 1 ? 'mini-dot--active' : ''"
                  />
                </div>
              </div>
            </div>

            <!-- Nombre del tema -->
            <p
              class="theme-label"
              :class="themeStore.temaActualId === tema.id ? 'theme-label--active' : ''"
            >{{ tema.nombre }}</p>
          </button>
        </div>

        <!-- Preview en vivo -->
        <div class="theme-live-preview">
          <div
            class="live-bar"
            :style="`background: var(--gradient-hero)`"
          >
            <span class="live-bar-dot"/>
            <span class="live-bar-text">Vista previa · {{ themeStore.temaActual.nombre }}</span>
          </div>
          <div class="live-nav">
            <div
              v-for="i in 4" :key="i"
              class="live-nav-item"
              :class="i === 1 ? 'live-nav-item--active' : ''"
            >
              <div
                class="live-nav-dot"
                :style="i === 1 ? 'background: var(--color-acento)' : 'background: #D1D5DB'"
              />
            </div>
          </div>
        </div>
      </section>

      <!-- ── Cerrar sesión ──────────────────────────────────────────────────── -->
      <section class="aj-settings-group">
        <button
          @click="confirmandoLogout = true"
          class="aj-settings-row aj-settings-row--first aj-logout-btn w-full text-left"
        >
          <div class="aj-row-icon aj-row-icon--red">
            <svg class="w-4 h-4" fill="none" stroke="white" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
            </svg>
          </div>
          <span class="aj-row-label" style="color: #EF4444; font-weight: 600;">Cerrar sesión</span>
          <svg class="aj-row-chevron" fill="none" stroke="#EF4444" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
          </svg>
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
/* ── Profile card (header) ─────────────────────────────────────────────── */
.aj-profile-card {
  position: relative; overflow: hidden;
  background: var(--gradient-hero);
  padding: max(1.5rem, env(safe-area-inset-top)) 1.25rem 1.5rem;
}
.aj-pattern {
  position: absolute; inset: 0;
  background-image:
    radial-gradient(circle at 90% 10%, rgba(255,255,255,0.12) 0%, transparent 45%),
    radial-gradient(circle at 10% 90%, rgba(124,58,237,0.25) 0%, transparent 50%);
}
.aj-profile-inner {
  position: relative;
  display: flex; align-items: center; gap: 1rem;
}

/* Avatar */
.aj-avatar {
  position: relative; flex-shrink: 0;
  width: 72px; height: 72px; border-radius: 50%;
  background: rgba(255,255,255,0.22);
  border: 2.5px solid rgba(255,255,255,0.45);
  display: flex; align-items: center; justify-content: center;
  color: white; font-size: 1.375rem; font-weight: 800;
}
.aj-avatar-ring {
  position: absolute; inset: -6px;
  border-radius: 50%;
  border: 1.5px solid rgba(255,255,255,0.18);
}

/* Info */
.aj-profile-info { flex: 1; min-width: 0; }
.aj-role-label {
  font-size: 0.625rem; font-weight: 700; letter-spacing: 0.1em;
  color: rgba(255,255,255,0.6); text-transform: uppercase; margin-bottom: 0.15rem;
}
.aj-name {
  font-size: 1.25rem; font-weight: 800; color: white; line-height: 1.2;
  margin-bottom: 0.5rem;
}
.aj-data-chips { display: flex; flex-wrap: wrap; gap: 0.375rem; }
.aj-chip {
  display: inline-flex; align-items: center; gap: 0.25rem;
  background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.22);
  color: rgba(255,255,255,0.85); font-size: 0.6875rem; font-weight: 600;
  border-radius: 999px; padding: 0.2rem 0.5rem;
}
.aj-chip--email { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ── Vehicle card ──────────────────────────────────────────────────────── */
.aj-vehicle-card {
  display: flex; align-items: center; gap: 1rem;
  background: white; border-radius: 1.25rem;
  border: 1px solid #F3F4F6;
  box-shadow: var(--shadow-sm);
  padding: 1rem 1.125rem;
}
.aj-vehicle-icon {
  width: 48px; height: 48px; flex-shrink: 0; border-radius: 0.875rem;
  background: var(--color-acento-suave);
  display: flex; align-items: center; justify-content: center;
}
.aj-vehicle-badge {
  flex-shrink: 0;
  display: inline-flex; align-items: center; gap: 0.3rem;
  background: #ECFDF5; color: #059669;
  font-size: 0.6875rem; font-weight: 700; border-radius: 999px;
  padding: 0.2rem 0.625rem;
}

/* ── Grupo de ajustes estilo iOS ────────────────────────────────────────── */
.aj-settings-group {
  background: white; border-radius: 1.25rem;
  box-shadow: var(--shadow-xs);
  overflow: hidden;
}
.aj-group-title {
  font-size: 0.6875rem; font-weight: 700; letter-spacing: 0.07em;
  text-transform: uppercase; color: #9CA3AF;
  padding: 0.875rem 1.125rem 0.375rem;
}
.aj-settings-row {
  display: flex; align-items: center; gap: 0.875rem;
  padding: 0.875rem 1.125rem;
  border-top: 1px solid #F9FAFB;
  min-height: 52px;
  background: none; border-left: none; border-right: none; border-bottom: none;
  cursor: pointer;
}
.aj-settings-row--first { border-top: none; }
.aj-settings-row:active { background: #F9FAFB; }
.aj-logout-btn:active { background: #FFF5F5; }
.aj-row-icon {
  width: 32px; height: 32px; flex-shrink: 0; border-radius: 0.5rem;
  display: flex; align-items: center; justify-content: center;
}
.aj-row-icon--blue   { background: #3B82F6; }
.aj-row-icon--purple { background: var(--color-acento); }
.aj-row-icon--red    { background: #EF4444; }
.aj-row-label { flex: 1; font-size: 0.9375rem; color: #1F2937; }
.aj-row-value { font-size: 0.875rem; color: #9CA3AF; }
.aj-row-chevron { width: 16px; height: 16px; flex-shrink: 0; opacity: 0.4; }

/* ── Row sublabel ──────────────────────────────────────────────────────── */
.aj-row-sublabel {
  font-size: 0.6875rem; color: #9CA3AF; margin-top: 0.1rem; line-height: 1.3;
}

/* ── Grid de temas ─────────────────────────────────────────────────────── */
.theme-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.625rem;
  padding: 0 1rem 1rem;
}

/* Tarjeta de tema */
.theme-card {
  display: flex; flex-direction: column; align-items: center; gap: 0.375rem;
  background: none; border: none; cursor: pointer; padding: 0;
  -webkit-tap-highlight-color: transparent;
}
.theme-card:active { opacity: 0.7; transform: scale(0.96); transition: all 0.1s; }

/* Preview de color */
.theme-preview {
  position: relative;
  width: 100%; aspect-ratio: 3/2;
  border-radius: 0.75rem;
  overflow: hidden;
  border: 2.5px solid transparent;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.theme-card--active .theme-preview {
  border-color: var(--color-acento);
  box-shadow: 0 0 0 3px var(--color-acento-suave), 0 4px 12px rgba(0,0,0,0.15);
}

/* Check de selección */
.theme-check {
  position: absolute; top: 6px; right: 6px;
  width: 20px; height: 20px; border-radius: 50%;
  background: rgba(255,255,255,0.25);
  border: 1.5px solid rgba(255,255,255,0.6);
  display: flex; align-items: center; justify-content: center;
}
.theme-check svg { width: 11px; height: 11px; }

/* Mini UI dentro del preview */
.theme-mini-ui {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; justify-content: space-between;
  padding: 5px 6px 4px;
}
.mini-header {
  height: 8px; border-radius: 3px;
  background: rgba(255,255,255,0.25); width: 55%;
}
.mini-nav {
  display: flex; justify-content: space-around; align-items: center;
  background: rgba(255,255,255,0.15); border-radius: 4px;
  padding: 3px 4px;
}
.mini-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: rgba(255,255,255,0.35);
}
.mini-dot--active {
  background: white;
  box-shadow: 0 0 4px rgba(255,255,255,0.6);
}

/* Nombre del tema */
.theme-label {
  font-size: 0.6875rem; font-weight: 600; color: #6B7280;
  text-align: center; line-height: 1;
}
.theme-label--active {
  color: var(--color-acento); font-weight: 700;
}

/* ── Preview en vivo ────────────────────────────────────────────────────── */
.theme-live-preview {
  margin: 0 1rem 1rem;
  border-radius: 0.875rem;
  overflow: hidden;
  border: 1px solid #F3F4F6;
  box-shadow: 0 1px 6px rgba(0,0,0,0.06);
}
.live-bar {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.625rem 0.875rem;
}
.live-bar-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: rgba(255,255,255,0.7);
  animation: pulse 1.5s infinite;
}
.live-bar-text {
  font-size: 0.6875rem; font-weight: 600; color: rgba(255,255,255,0.9);
}
.live-nav {
  display: flex; justify-content: space-around; align-items: center;
  background: rgba(255,255,255,0.95);
  padding: 0.5rem 0;
}
.live-nav-item {
  display: flex; flex-direction: column; align-items: center;
  gap: 4px; flex: 1;
}
.live-nav-dot {
  width: 16px; height: 16px; border-radius: 50%;
  transition: background 0.3s;
}
.live-nav-item--active .live-nav-dot {
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.5; transform: scale(1.3); }
}

/* Overlay */
.overlay-enter-active, .overlay-leave-active { transition: opacity 0.25s ease; }
.overlay-enter-from, .overlay-leave-to       { opacity: 0; }

/* Bottom sheet */
.sheet-enter-active, .sheet-leave-active { transition: transform 0.3s ease; }
.sheet-enter-from, .sheet-leave-to       { transform: translateY(100%); }
</style>
