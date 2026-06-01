<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Preferences } from '@capacitor/preferences'
import { useAuthStore } from '@/stores/auth.js'
import { validarRut as _validarRutCentral } from '@/utils/validators.js'

const router = useRouter()
const auth   = useAuthStore()

// Oculta el formulario mientras se verifica si ya hay sesión activa
const verificandoSesion = ref(true)

const rutFormateado = ref('')
const password      = ref('')
const verPassword   = ref(false)
const errorRut      = ref('')
const errorPassword = ref('')

const inputPassword = ref(null)

// ── Formateo de RUT ──────────────────────────────────────────────────────────
function formatearRut(valor) {
  // Permitir solo dígitos y K/k; máximo 9 caracteres (8 dígitos + DV)
  let rut = valor.replace(/[^0-9kK]/g, '').toUpperCase()
  if (rut.length > 9) rut = rut.slice(0, 9)
  if (rut.length < 2) return rut
  const dv   = rut.slice(-1)
  let cuerpo = rut.slice(0, -1)
  cuerpo     = cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${cuerpo}-${dv}`
}

/**
 * Normaliza igual que el backend: quita puntos, strip, lowercase.
 * Resultado: "12345678-9"  o  "12345678-k"
 */
function normalizarRut(rut) {
  return rut.replace(/\./g, '').trim().toLowerCase()
}

/**
 * Valida formato Y dígito verificador del RUT chileno.
 * Delega en el validador centralizado de @/utils/validators.js
 */
function validarRut(rutFormateadoVal) {
  return _validarRutCentral(rutFormateadoVal).valido
}

function onRutInput(e) {
  const v = formatearRut(e.target.value)
  rutFormateado.value = v
  e.target.value      = v
  errorRut.value = ''
  // Limpiar error general al volver a escribir
  if (auth.error) auth.limpiarError()
}

function onPasswordInput() {
  errorPassword.value = ''
  if (auth.error) auth.limpiarError()
}

// ── Validación ───────────────────────────────────────────────────────────────
function validar() {
  let ok = true

  const rutResult = _validarRutCentral(rutFormateado.value)
  if (!rutFormateado.value.trim()) {
    errorRut.value = 'Ingresa tu RUT'
    ok = false
  } else if (!rutResult.valido) {
    errorRut.value = rutResult.error
    ok = false
  }

  if (password.value.length < 4) {
    errorPassword.value = 'La contraseña debe tener al menos 4 caracteres'
    ok = false
  }

  return ok
}

/** Lee los módulos del plan y retorna la ruta del primer módulo disponible */
async function _rutaDestino() {
  try {
    const { value } = await Preferences.get({ key: 'plan_modulos' })
    const parsed    = JSON.parse(value || '[]')
    const modulos   = Array.isArray(parsed) ? parsed : []
    if (modulos.includes('rutas'))        return { name: 'rutas' }
    if (modulos.includes('solicitudes'))  return { name: 'solicitudes' }
    if (modulos.includes('mantenciones')) return { name: 'mantencion' }
  } catch {}
  return { name: 'ajustes' }
}

// ── Submit ───────────────────────────────────────────────────────────────────
async function onSubmit() {
  auth.limpiarError()
  if (!validar()) return

  const rut = normalizarRut(rutFormateado.value)
  const { success, primerLogin } = await auth.login(rut, password.value)

  if (success) {
    if (primerLogin) {
      router.replace({ name: 'onboarding' })
    } else {
      // Navegar al módulo correcto según el plan, sin double redirect
      router.replace(await _rutaDestino())
    }
  }
}

// Al presionar "Siguiente" en RUT → enfocar contraseña
function onRutNext() {
  inputPassword.value?.focus()
}

// ── Recuperar contraseña ─────────────────────────────────────────────────────
const recuperandoPassword   = ref(false)
const recuperarRut          = ref('')
const recuperarEstado       = ref('')   // '' | 'enviando' | 'ok' | 'error'
const recuperarError        = ref('')

function abrirRecuperar() {
  recuperarRut.value    = ''
  recuperarEstado.value = ''
  recuperarError.value  = ''
  recuperandoPassword.value = true
}

async function enviarRecuperar() {
  recuperarError.value = ''
  const rut = normalizarRut(recuperarRut.value)
  if (!_validarRutCentral(recuperarRut.value).valido) {
    recuperarError.value = 'Ingresa un RUT válido.'
    return
  }
  recuperarEstado.value = 'enviando'
  try {
    const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    await fetch(`${BASE_URL}/api/conductor/recuperar-password/`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ rut }),
    })
    recuperarEstado.value = 'ok'
  } catch {
    recuperarEstado.value = 'error'
    recuperarError.value  = 'Sin conexión. Verifica tu red e intenta de nuevo.'
  }
}

// ── Verificar sesión al montar ────────────────────────────────────────────────
// El guard del router ya maneja el redirect si hay sesión activa.
// Este bloque es un fallback de seguridad por si el guard falló silenciosamente.
onMounted(async () => {
  await auth.cargarSesion()
  if (auth.estaAutenticado) {
    router.replace(await _rutaDestino())
  } else {
    // Sin sesión: mostrar el formulario
    verificandoSesion.value = false
  }
})
</script>

<template>
  <!-- Spinner mientras se verifica la sesión — evita el flash del formulario antes del redirect -->
  <div
    v-if="verificandoSesion"
    class="min-h-dvh flex items-center justify-center"
    style="background: var(--color-acento)"
  >
    <span class="w-10 h-10 border-2 border-white/30 border-t-white rounded-full animate-spin"/>
  </div>

  <div
    v-else
    class="min-h-dvh flex flex-col overflow-hidden"
    style="background: var(--color-acento); padding-top: env(safe-area-inset-top, 0px)"
  >
    <!-- Logo -->
    <div class="flex flex-col items-center justify-center flex-1 gap-4 py-8 px-4 min-h-0">
      <div class="w-20 h-20 rounded-2xl bg-white/20 flex items-center justify-center shrink-0">
        <svg class="w-11 h-11 text-white" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12"/>
        </svg>
      </div>
      <div class="text-center">
        <h1 class="text-white text-3xl font-bold tracking-tight">Conductor</h1>
        <p class="text-white/60 text-sm mt-1">Gestión de Flota</p>
      </div>
    </div>

    <!-- Card inferior -->
    <div
      class="bg-white rounded-t-3xl px-6 pt-8 shadow-2xl shrink-0 overflow-y-auto"
      style="max-height: min(75vh, 75dvh); padding-bottom: calc(2.5rem + env(safe-area-inset-bottom, 0px));"
    >
      <h2 class="text-gray-800 text-xl font-bold mb-1">Iniciar sesión</h2>
      <p class="text-gray-400 text-sm mb-6">Ingresa tus credenciales para continuar</p>

      <!-- ── Banners de error diferenciados ──────────────────────────── -->
      <Transition name="error-slide">
        <div v-if="auth.error" class="mb-5">

          <!-- SIN CONEXIÓN / TIMEOUT → ícono wifi + botón reintentar -->
          <div
            v-if="auth.error.tipo === 'sin_conexion'"
            class="p-3.5 bg-amber-50 border border-amber-200 rounded-xl flex flex-col gap-2"
          >
            <div class="flex items-start gap-2.5">
              <svg class="w-5 h-5 text-amber-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.288 15.038a5.25 5.25 0 017.424 0M5.106 11.856c3.807-3.808 9.98-3.808 13.788 0M1.924 8.674c5.565-5.565 14.587-5.565 20.152 0M12.53 18.22l-.53.53-.53-.53a.75.75 0 011.06 0z"/>
              </svg>
              <p class="text-sm font-medium text-amber-800">{{ auth.error.mensaje }}</p>
            </div>
            <button
              type="button"
              @click="onSubmit"
              :disabled="auth.cargando"
              class="self-start px-3.5 py-1.5 bg-amber-500 text-white text-xs font-semibold rounded-lg disabled:opacity-50 active:bg-amber-600 transition-colors"
            >
              Reintentar
            </button>
          </div>

          <!-- CUENTA BLOQUEADA → ícono candado + fondo naranja oscuro -->
          <div
            v-else-if="auth.error.tipo === 'bloqueado'"
            class="p-3.5 bg-orange-50 border border-orange-300 rounded-xl flex items-start gap-2.5"
          >
            <svg class="w-5 h-5 text-orange-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"/>
            </svg>
            <div>
              <p class="text-sm font-semibold text-orange-800">Cuenta bloqueada</p>
              <p class="text-xs text-orange-700 mt-0.5">{{ auth.error.mensaje }}</p>
            </div>
          </div>

          <!-- ERROR DE SERVIDOR → ícono server -->
          <div
            v-else-if="auth.error.tipo === 'servidor'"
            class="p-3.5 bg-gray-50 border border-gray-200 rounded-xl flex items-start gap-2.5"
          >
            <svg class="w-5 h-5 text-gray-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z"/>
            </svg>
            <div>
              <p class="text-sm font-semibold text-gray-700">Servidor no disponible</p>
              <p class="text-xs text-gray-500 mt-0.5">{{ auth.error.mensaje }}</p>
            </div>
          </div>

          <!-- APP SOLO CONDUCTORES -->
          <div
            v-else-if="auth.error.tipo === 'no_conductor'"
            class="p-3.5 bg-blue-50 border border-blue-200 rounded-xl flex items-start gap-2.5"
          >
            <svg class="w-5 h-5 text-blue-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"/>
            </svg>
            <p class="text-sm text-blue-800">{{ auth.error.mensaje }}</p>
          </div>

          <!-- CREDENCIALES INCORRECTAS → ícono x-circle, sin bloque prominente -->
          <div
            v-else
            class="p-3 bg-red-50 border border-red-200 rounded-xl flex items-start gap-2"
          >
            <svg class="w-4 h-4 text-red-500 shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
            </svg>
            <p class="text-sm text-red-700">{{ auth.error.mensaje }}</p>
          </div>

        </div>
      </Transition>

      <form @submit.prevent="onSubmit" novalidate class="flex flex-col gap-5">

        <!-- RUT -->
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1.5">RUT</label>
          <input
            :value="rutFormateado"
            @input="onRutInput"
            @keydown.enter.prevent="onRutNext"
            type="text"
            inputmode="numeric"
            placeholder="12.345.678-9"
            autocomplete="username"
            autocorrect="off"
            autocapitalize="none"
            :disabled="auth.cargando"
            enterkeyhint="next"
            :class="[
              'w-full px-4 py-3.5 rounded-xl text-sm text-gray-800 border-2 transition',
              errorRut || auth.error?.tipo === 'credenciales'
                ? 'border-red-400 bg-red-50 focus:border-red-400'
                : 'border-gray-100 bg-gray-50 focus:border-[--color-acento] focus:bg-white'
            ]"
          />
          <p v-if="errorRut" class="mt-1 text-xs text-red-500">{{ errorRut }}</p>
        </div>

        <!-- Contraseña -->
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1.5">Contraseña</label>
          <div class="relative">
            <input
              ref="inputPassword"
              v-model="password"
              @input="onPasswordInput"
              :type="verPassword ? 'text' : 'password'"
              placeholder="••••••••"
              autocomplete="current-password"
              :disabled="auth.cargando"
              enterkeyhint="done"
              :class="[
                'w-full px-4 py-3.5 pr-12 rounded-xl text-sm text-gray-800 border-2 transition',
                errorPassword || auth.error?.tipo === 'credenciales'
                  ? 'border-red-400 bg-red-50 focus:border-red-400'
                  : 'border-gray-100 bg-gray-50 focus:border-[--color-acento] focus:bg-white'
              ]"
            />
            <button
              type="button"
              @click="verPassword = !verPassword"
              tabindex="-1"
              class="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 p-1"
            >
              <svg v-if="!verPassword" class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"/>
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
              <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88"/>
              </svg>
            </button>
          </div>
          <p v-if="errorPassword" class="mt-1 text-xs text-red-500">{{ errorPassword }}</p>
        </div>

        <!-- Botón ingresar -->
        <button
          type="submit"
          :disabled="auth.cargando || auth.error?.tipo === 'bloqueado'"
          class="w-full py-4 rounded-xl text-white font-semibold text-sm flex items-center justify-center gap-2 mt-2 transition-opacity disabled:opacity-50 active:opacity-80"
          style="background: var(--color-acento); box-shadow: 0 4px 14px color-mix(in srgb, var(--color-acento) 40%, transparent)"
        >
          <span
            v-if="auth.cargando"
            class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
          />
          {{ auth.cargando ? 'Ingresando...' : 'Ingresar' }}
        </button>

        <!-- Recuperar contraseña -->
        <button type="button" @click="abrirRecuperar"
          class="w-full text-center text-xs text-gray-400 py-1 active:text-gray-600 transition-colors">
          ¿Olvidaste tu contraseña?
        </button>

      </form>
    </div>

    <!-- ── Sheet: recuperar contraseña ────────────────────────────────────── -->
    <Transition name="sheet">
      <div v-if="recuperandoPassword" class="fixed inset-0 z-50 flex flex-col justify-end"
           style="padding-top: env(safe-area-inset-top)">
        <div class="absolute inset-0 bg-black/50" @click="recuperandoPassword = false"/>
        <div class="relative bg-white rounded-t-3xl px-6 pt-6 pb-10"
             style="padding-bottom: calc(2.5rem + env(safe-area-inset-bottom))">

          <!-- Asa -->
          <div class="flex justify-center mb-5">
            <div class="w-10 h-1 rounded-full bg-gray-300"/>
          </div>

          <!-- Estado: enviado OK -->
          <div v-if="recuperarEstado === 'ok'" class="flex flex-col items-center gap-4 py-4 text-center">
            <div class="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center">
              <i class="ti ti-mail-check text-2xl text-green-600"/>
            </div>
            <div>
              <p class="font-bold text-gray-800 mb-1">Correo enviado</p>
              <p class="text-sm text-gray-500">
                Si el RUT está registrado, recibirás una contraseña temporal en tu correo electrónico.
              </p>
            </div>
            <button @click="recuperandoPassword = false"
              class="w-full py-3.5 rounded-xl text-white font-semibold text-sm"
              style="background: var(--color-acento)">
              Volver al inicio
            </button>
          </div>

          <!-- Estado: formulario -->
          <div v-else>
            <h2 class="text-lg font-bold text-gray-800 mb-1">Recuperar contraseña</h2>
            <p class="text-sm text-gray-500 mb-5">
              Ingresa tu RUT y te enviaremos una contraseña temporal al correo registrado.
            </p>

            <label class="block text-sm font-semibold text-gray-700 mb-1.5">RUT</label>
            <input
              :value="recuperarRut"
              @input="e => { recuperarRut = formatearRut(e.target.value); e.target.value = recuperarRut; recuperarError = '' }"
              type="text" inputmode="numeric" placeholder="12.345.678-9"
              autocomplete="off"
              :class="[
                'w-full px-4 py-3.5 rounded-xl text-sm border-2 transition mb-1',
                recuperarError ? 'border-red-400 bg-red-50' : 'border-gray-100 bg-gray-50 focus:border-[--color-acento] focus:bg-white'
              ]"
              @keyup.enter="enviarRecuperar"
            />
            <p v-if="recuperarError" class="text-xs text-red-500 mb-3">{{ recuperarError }}</p>

            <button @click="enviarRecuperar" :disabled="recuperarEstado === 'enviando'"
              class="w-full py-3.5 rounded-xl text-white font-semibold text-sm flex items-center justify-center gap-2 mt-3 disabled:opacity-60"
              style="background: var(--color-acento)">
              <span v-if="recuperarEstado === 'enviando'"
                class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"/>
              <span v-else><i class="ti ti-send mr-1"/>Enviar contraseña temporal</span>
            </button>
          </div>

        </div>
      </div>
    </Transition>

  </div>
</template>

<style scoped>
.error-slide-enter-active,
.error-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.error-slide-enter-from,
.error-slide-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
.sheet-enter-active,
.sheet-leave-active {
  transition: opacity 0.25s ease;
}
.sheet-enter-active > div:last-child,
.sheet-leave-active > div:last-child {
  transition: transform 0.3s cubic-bezier(0.32, 0.72, 0, 1);
}
.sheet-enter-from,
.sheet-leave-to {
  opacity: 0;
}
.sheet-enter-from > div:last-child,
.sheet-leave-to > div:last-child {
  transform: translateY(100%);
}
</style>
