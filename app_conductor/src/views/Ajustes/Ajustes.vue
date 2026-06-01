<script setup>
import { ref } from 'vue'
import { Preferences } from '@capacitor/preferences'
import { useAuthStore }  from '@/stores/auth.js'
import { useThemeStore } from '@/stores/theme.js'
import { usePermisos }   from '@/composables/usePermisos.js'
import BottomNav from '@/components/BottomNav.vue'
import { iniciales } from '@/utils/formato.js'
import { apiFetch } from '@/services/api.js'

const auth       = useAuthStore()
const themeStore = useThemeStore()

const { modulos, planNombre } = usePermisos()

const MODULO_LABELS = {
  rutas:                 'Rutas y trabajos',
  mantencion_correctiva: 'Mantención correctiva',
  mantencion_predictiva: 'Mantención predictiva',
  documentos:            'Documentos',
  combustible:           'Combustible',
  finanzas:              'Finanzas',
}

// ── Confirmación de cierre de sesión ─────────────────────────────────────────
const confirmandoLogout = ref(false)
const cerrando          = ref(false)

async function handleLogout() {
  cerrando.value = true
  await auth.logout()
}

// ── Cambiar contraseña ────────────────────────────────────────────────────────
const cambioPassAbierto  = ref(false)
const cambioPassGuardando = ref(false)
const cambioPassForm = ref({ actual: '', nuevo: '', confirmar: '' })
const cambioPassVer  = ref({ actual: false, nuevo: false, confirmar: false })
const cambioPassErr  = ref({})
const cambioPassToast = ref({ visible: false, mensaje: '', error: false })

function abrirCambiarPassword() {
  cambioPassForm.value  = { actual: '', nuevo: '', confirmar: '' }
  cambioPassVer.value   = { actual: false, nuevo: false, confirmar: false }
  cambioPassErr.value   = {}
  cambioPassAbierto.value = true
}

async function guardarCambioPassword() {
  cambioPassErr.value = {}
  const { actual, nuevo, confirmar } = cambioPassForm.value
  const errs = {}
  if (!actual)      errs.actual    = 'Ingresa tu contraseña actual.'
  if (nuevo.length < 8)            errs.nuevo = 'Mínimo 8 caracteres.'
  else if (!/[A-Z]/.test(nuevo))   errs.nuevo = 'Debe tener al menos una mayúscula.'
  else if (!/[0-9]/.test(nuevo))   errs.nuevo = 'Debe tener al menos un número.'
  else if (nuevo === actual)        errs.nuevo = 'Debe ser diferente a la actual.'
  if (!errs.nuevo && nuevo !== confirmar) errs.confirmar = 'Las contraseñas no coinciden.'
  if (Object.keys(errs).length) { cambioPassErr.value = errs; return }

  cambioPassGuardando.value = true
  try {
    const res = await apiFetch('/api/conductor/cambiar-password/', {
      method: 'PATCH',
      body: JSON.stringify({ password_actual: actual, password_nuevo: nuevo, confirmar }),
    })
    if (res.errores) { cambioPassErr.value = res.errores; return }
    cambioPassAbierto.value = false
    mostrarCambioToast('Contraseña actualizada correctamente.')
  } catch (e) {
    mostrarCambioToast(e?.message || 'No se pudo guardar. Intenta de nuevo.', true)
  } finally {
    cambioPassGuardando.value = false
  }
}

function mostrarCambioToast(mensaje, error = false) {
  cambioPassToast.value = { visible: true, mensaje, error }
  setTimeout(() => { cambioPassToast.value.visible = false }, 3500)
}

// ── Editar perfil ─────────────────────────────────────────────────────────────
const editandoPerfil  = ref(false)
const guardandoPerfil = ref(false)
const perfilToast     = ref({ visible: false, mensaje: '', error: false })
const perfilForm      = ref({ telefono: '', licencia: '', nombre: '' })
const perfilErrores   = ref({})

// Devuelve solo los 8 dígitos del móvil (sin el +569 prefix)
function _digitesTelefono(tel) {
  const limpio = (tel || '').replace(/[\s\-\(\)]/g, '')
  if (limpio.startsWith('+569')) return limpio.slice(4)
  if (limpio.startsWith('569'))  return limpio.slice(3)
  if (limpio.startsWith('9') && limpio.length === 9) return limpio.slice(1)
  return limpio
}

function abrirEditarPerfil() {
  perfilForm.value = {
    nombre:   auth.usuario?.nombre   || '',
    telefono: _digitesTelefono(auth.usuario?.telefono),
    licencia: auth.usuario?.licencia || '',
  }
  perfilErrores.value = {}
  editandoPerfil.value = true
}

// Validación local de licencia chilena: 1-3 letras + opcional guion/espacio + 4-9 dígitos
function validarLicenciaChilena(lic) {
  return /^[A-Za-z]{1,3}[-\s]?\d{4,9}$/.test(lic.trim())
}

async function guardarPerfil() {
  perfilErrores.value  = {}
  guardandoPerfil.value = true

  // Validación local antes de llamar al API
  const errLocal = {}
  const telCompleto = '+569' + perfilForm.value.telefono.replace(/\D/g, '')
  if (perfilForm.value.telefono && !/^\d{8}$/.test(perfilForm.value.telefono.replace(/\D/g, ''))) {
    errLocal.telefono = 'Ingresa los 8 dígitos después de +569.'
  }
  if (perfilForm.value.licencia && !validarLicenciaChilena(perfilForm.value.licencia)) {
    errLocal.licencia = 'Formato inválido. Ej: A-123456 o B1234567.'
  }
  if (Object.keys(errLocal).length) {
    perfilErrores.value  = errLocal
    guardandoPerfil.value = false
    return
  }

  try {
    const payload = {}
    const u = auth.usuario || {}
    if (perfilForm.value.nombre   !== u.nombre)   payload.nombre   = perfilForm.value.nombre.trim()
    if (telCompleto !== u.telefono)               payload.telefono = telCompleto
    if (perfilForm.value.licencia !== u.licencia) payload.licencia = perfilForm.value.licencia.trim().toUpperCase()

    if (!Object.keys(payload).length) { editandoPerfil.value = false; return }

    const res = await apiFetch('/api/conductor/perfil/', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })

    if (res.errores) {
      perfilErrores.value = res.errores
      return
    }

    // Actualizar store y Preferences
    const actualizado = {
      ...u,
      ...('nombre'   in payload ? { nombre:   res.nombre   || payload.nombre }   : {}),
      ...('telefono' in payload ? { telefono: payload.telefono } : {}),
      ...('licencia' in payload ? { licencia: payload.licencia, requiere_licencia: res.requiere_licencia ?? false } : {}),
    }
    auth.usuario = actualizado
    await Preferences.set({ key: 'usuario', value: JSON.stringify(actualizado) })

    editandoPerfil.value = false
    mostrarPerfilToast('Perfil actualizado correctamente.')
  } catch (e) {
    mostrarPerfilToast(e?.message || 'No se pudo guardar. Intenta de nuevo.', true)
  } finally {
    guardandoPerfil.value = false
  }
}

function mostrarPerfilToast(mensaje, error = false) {
  perfilToast.value = { visible: true, mensaje, error }
  setTimeout(() => { perfilToast.value.visible = false }, 3500)
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

      <!-- Botón editar perfil -->
      <button @click="abrirEditarPerfil"
        class="mt-3 flex items-center gap-1.5 text-xs text-white/80 bg-white/15 rounded-full px-3 py-1.5 mx-auto">
        <i class="ti ti-edit text-xs"/>
        Editar perfil
      </button>
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

      <!-- ── Plan de la empresa ───────────────────────────────────────────── -->
      <section class="aj-settings-group">
        <p class="aj-group-title">Plan de la empresa</p>
        <div class="aj-plan-body">
          <p class="aj-plan-nombre">{{ planNombre || 'Sin plan asignado' }}</p>
          <div class="aj-plan-chips">
            <span
              v-for="mod in modulos"
              :key="mod"
              class="aj-plan-chip"
            >
              {{ MODULO_LABELS[mod] || mod }}
            </span>
            <span v-if="modulos.length === 0" class="aj-plan-empty">
              Sin módulos activos
            </span>
          </div>
        </div>
      </section>

      <!-- ── Sección app (estilo iOS) ─────────────────────────────────────── -->
      <section class="aj-settings-group">
        <p class="aj-group-title">Aplicación</p>

        <!-- Versión -->
        <div class="aj-settings-row aj-settings-row--first">
          <div class="aj-row-icon aj-row-icon--blue">
            <i class="ti ti-info-circle text-white text-sm"/>
          </div>
          <span class="aj-row-label">Versión</span>
          <span class="aj-row-value">1.0.0</span>
        </div>

        <!-- Sistema -->
        <div class="aj-settings-row">
          <div class="aj-row-icon aj-row-icon--purple">
            <i class="ti ti-shield-check text-white text-sm"/>
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
            <i class="ti ti-palette text-white text-sm"/>
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
                <i class="ti ti-check text-white text-xs font-black"/>
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

      <!-- ── Seguridad ─────────────────────────────────────────────────────── -->
      <section class="aj-group">
        <p class="aj-group-title">Seguridad</p>
        <button @click="abrirCambiarPassword" class="aj-group-item">
          <span class="aj-group-item-icon" style="background:#EDE9FE;">
            <i class="ti ti-lock text-sm" style="color:#7C3AED;"/>
          </span>
          <span class="aj-group-item-label">Cambiar contraseña</span>
          <i class="ti ti-chevron-right aj-group-item-chevron"/>
        </button>
      </section>

      <!-- ── Cerrar sesión ──────────────────────────────────────────────────── -->
      <button @click="confirmandoLogout = true" class="aj-logout-standalone">
        <i class="ti ti-logout text-lg"/>
        Cerrar sesión
      </button>

    </div>

    <!-- ── Modal confirmación logout ─────────────────────────────────────────── -->
    <Transition name="overlay">
      <div
        v-if="confirmandoLogout"
        class="fixed inset-0 bg-black/50 z-[60] flex items-end"
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
                <i class="ti ti-logout text-red-500 text-2xl"/>
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

    <!-- ── Bottom-sheet: editar perfil ──────────────────────────────────────── -->
    <Transition name="sheet">
      <div v-if="editandoPerfil" class="fixed inset-0 z-[60] flex flex-col justify-end">
        <div class="absolute inset-0 bg-black/50" @click="editandoPerfil = false"/>
        <div class="relative bg-white rounded-t-2xl"
             style="max-height: min(85vh,85dvh); padding-bottom: env(safe-area-inset-bottom, 0px); overflow-y: auto;">
          <!-- Asa -->
          <div class="flex justify-center pt-3 pb-1 sticky top-0 bg-white z-10">
            <div class="w-10 h-1 rounded-full bg-gray-300"/>
          </div>
          <div class="px-5 pb-6">
            <h2 class="text-base font-bold text-gray-800 mb-4">Editar perfil</h2>

            <!-- Nombre -->
            <div class="mb-3">
              <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Nombre completo</label>
              <input v-model="perfilForm.nombre" type="text" placeholder="Tu nombre"
                class="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-[var(--color-acento)]"
                :class="perfilErrores.nombre ? 'border-red-300' : ''"/>
              <p v-if="perfilErrores.nombre" class="text-xs text-red-500 mt-1">{{ perfilErrores.nombre }}</p>
            </div>

            <!-- Teléfono -->
            <div class="mb-3">
              <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Teléfono</label>
              <div class="flex border rounded-xl overflow-hidden"
                   :class="perfilErrores.telefono ? 'border-red-300' : 'border-gray-200'">
                <span class="px-3 py-2.5 text-sm font-mono bg-gray-50 text-gray-500 border-r border-gray-200 select-none">+569</span>
                <input v-model="perfilForm.telefono" type="tel" placeholder="12345678" maxlength="8"
                  class="flex-1 px-3 py-2.5 text-sm font-mono focus:outline-none"
                  @input="perfilForm.telefono = perfilForm.telefono.replace(/\D/g,'').slice(0,8)"/>
              </div>
              <p v-if="perfilErrores.telefono" class="text-xs text-red-500 mt-1">{{ perfilErrores.telefono }}</p>
            </div>

            <!-- Licencia -->
            <div class="mb-5">
              <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">N° de licencia</label>
              <input v-model="perfilForm.licencia" type="text" placeholder="Ej: A-123456"
                class="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm font-mono uppercase focus:outline-none focus:border-[var(--color-acento)]"
                :class="perfilErrores.licencia ? 'border-red-300' : ''"/>
              <p v-if="perfilErrores.licencia" class="text-xs text-red-500 mt-1">{{ perfilErrores.licencia }}</p>
            </div>

            <button @click="guardarPerfil" :disabled="guardandoPerfil"
              class="w-full py-3 rounded-xl text-white font-semibold text-sm flex items-center justify-center gap-2"
              style="background: var(--color-acento)">
              <span v-if="guardandoPerfil" class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"/>
              <span v-else>Guardar cambios</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Toast de perfil -->
    <Transition name="toast">
      <div v-if="perfilToast.visible"
        class="fixed left-1/2 -translate-x-1/2 z-[70] px-4 py-2.5 rounded-xl shadow-lg text-sm font-medium text-white flex items-center gap-2"
        :class="perfilToast.error ? 'bg-red-600' : 'bg-gray-800'"
        style="bottom: calc(1.5rem + env(safe-area-inset-bottom))">
        <i :class="perfilToast.error ? 'ti ti-alert-circle' : 'ti ti-circle-check'"/>
        {{ perfilToast.mensaje }}
      </div>
    </Transition>

    <!-- ── Bottom-sheet: cambiar contraseña ──────────────────────────────────── -->
    <Transition name="sheet">
      <div v-if="cambioPassAbierto" class="fixed inset-0 z-[60] flex flex-col justify-end">
        <div class="absolute inset-0 bg-black/50" @click="cambioPassAbierto = false"/>
        <div class="relative bg-white rounded-t-2xl"
             style="max-height: min(90vh,90dvh); padding-bottom: env(safe-area-inset-bottom, 0px); overflow-y: auto;">
          <div class="flex justify-center pt-3 pb-1 sticky top-0 bg-white z-10">
            <div class="w-10 h-1 rounded-full bg-gray-300"/>
          </div>
          <div class="px-5 pb-6">
            <h2 class="text-base font-bold text-gray-800 mb-1">Cambiar contraseña</h2>
            <p class="text-xs text-gray-400 mb-5">Mínimo 8 caracteres, una mayúscula y un número.</p>

            <!-- Campo genérico con toggle visibilidad -->
            <template v-for="campo in [
              { key: 'actual',    label: 'Contraseña actual',    placeholder: '••••••••', autoComplete: 'current-password' },
              { key: 'nuevo',     label: 'Nueva contraseña',     placeholder: '••••••••', autoComplete: 'new-password' },
              { key: 'confirmar', label: 'Confirmar contraseña', placeholder: '••••••••', autoComplete: 'new-password' },
            ]" :key="campo.key">
              <div class="mb-3">
                <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                  {{ campo.label }}
                </label>
                <div class="relative">
                  <input
                    v-model="cambioPassForm[campo.key]"
                    :type="cambioPassVer[campo.key] ? 'text' : 'password'"
                    :placeholder="campo.placeholder"
                    :autocomplete="campo.autoComplete"
                    class="w-full border rounded-xl px-4 py-2.5 text-sm pr-10 focus:outline-none focus:border-[var(--color-acento)]"
                    :class="cambioPassErr[campo.key] ? 'border-red-300' : 'border-gray-200'"
                    @input="delete cambioPassErr[campo.key]"
                  />
                  <button type="button" tabindex="-1"
                    @click="cambioPassVer[campo.key] = !cambioPassVer[campo.key]"
                    class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                    <i :class="cambioPassVer[campo.key] ? 'ti ti-eye-off' : 'ti ti-eye'" class="text-sm"/>
                  </button>
                </div>
                <p v-if="cambioPassErr[campo.key]" class="text-xs text-red-500 mt-1">
                  {{ cambioPassErr[campo.key] }}
                </p>
              </div>
            </template>

            <button @click="guardarCambioPassword" :disabled="cambioPassGuardando"
              class="w-full mt-2 py-3 rounded-xl text-white font-semibold text-sm flex items-center justify-center gap-2"
              style="background: var(--color-acento)">
              <span v-if="cambioPassGuardando" class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"/>
              <span v-else><i class="ti ti-lock-check mr-1"/>Guardar nueva contraseña</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Toast de cambio de contraseña -->
    <Transition name="toast">
      <div v-if="cambioPassToast.visible"
        class="fixed left-1/2 -translate-x-1/2 z-[70] px-4 py-2.5 rounded-xl shadow-lg text-sm font-medium text-white flex items-center gap-2"
        :class="cambioPassToast.error ? 'bg-red-600' : 'bg-gray-800'"
        style="bottom: calc(1.5rem + env(safe-area-inset-bottom))">
        <i :class="cambioPassToast.error ? 'ti ti-alert-circle' : 'ti ti-circle-check'"/>
        {{ cambioPassToast.mensaje }}
      </div>
    </Transition>

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
  pointer-events: none;
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

/* ── Plan de la empresa ─────────────────────────────────────────────────── */
.aj-plan-body {
  padding: 0.75rem 1.125rem 1rem;
}
.aj-plan-nombre {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #1F2937;
  margin: 0 0 0.625rem;
}
.aj-plan-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}
.aj-plan-chip {
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.2rem 0.625rem;
  border-radius: 999px;
  background: #E1F5EE;
  color: #085041;
}
.aj-plan-empty {
  font-size: 0.75rem;
  color: #9CA3AF;
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

/* ── Botón cerrar sesión ────────────────────────────────────────────────── */
.aj-logout-standalone {
  width: 100%;
  display: flex; align-items: center; justify-content: center;
  gap: 0.625rem;
  padding: 1rem;
  background: #FEF2F2;
  border: 1.5px solid #FECACA;
  border-radius: 1.25rem;
  color: #EF4444;
  font-size: 0.9375rem; font-weight: 700;
  cursor: pointer; font-family: inherit;
  min-height: 56px;
  transition: background 0.15s, transform 0.1s;
  -webkit-tap-highlight-color: transparent;
}
.aj-logout-standalone:active {
  background: #FEE2E2;
  transform: scale(0.98);
}

/* Overlay */
.overlay-enter-active, .overlay-leave-active { transition: opacity 0.25s ease; }
.overlay-enter-from, .overlay-leave-to       { opacity: 0; }

/* Bottom sheet */
.sheet-enter-active, .sheet-leave-active { transition: transform 0.3s ease; }
.sheet-enter-from, .sheet-leave-to       { transform: translateY(100%); }
</style>
