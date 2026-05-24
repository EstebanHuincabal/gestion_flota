<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'

const router = useRouter()
const auth   = useAuthStore()

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
 * Reglas:
 *  - Cuerpo: 1 a 8 dígitos  (RUTs válidos: 1 a 99.999.999)
 *  - Separador: guión
 *  - DV: 0-9 o K (algoritmo módulo 11)
 */
function validarRut(rutFormateadoVal) {
  const norm = normalizarRut(rutFormateadoVal)

  // Formato básico: 1–8 dígitos + guión + (dígito o k)
  if (!/^\d{1,8}-[\dk]$/.test(norm)) return false

  const [cuerpo, dv] = norm.split('-')

  // Algoritmo módulo 11 — igual que el SII
  let suma      = 0
  let multiplo  = 2
  for (let i = cuerpo.length - 1; i >= 0; i--) {
    suma     += parseInt(cuerpo[i]) * multiplo
    multiplo  = multiplo === 7 ? 2 : multiplo + 1
  }
  const resto      = suma % 11
  const dvEsperado = resto === 0 ? '0' : resto === 1 ? 'k' : String(11 - resto)

  return dv === dvEsperado
}

function onRutInput(e) {
  rutFormateado.value = formatearRut(e.target.value)
  errorRut.value = ''
}

function onPasswordInput() {
  errorPassword.value = ''
}

// ── Validación ───────────────────────────────────────────────────────────────
function validar() {
  let ok = true

  if (!rutFormateado.value.trim()) {
    errorRut.value = 'Ingresa tu RUT'
    ok = false
  } else if (!validarRut(rutFormateado.value)) {
    errorRut.value = 'RUT inválido. Verifica el número y dígito verificador'
    ok = false
  }

  if (password.value.length < 4) {
    errorPassword.value = 'La contraseña debe tener al menos 4 caracteres'
    ok = false
  }

  return ok
}

// ── Submit ───────────────────────────────────────────────────────────────────
async function onSubmit() {
  auth.error = null
  if (!validar()) return

  const rut = normalizarRut(rutFormateado.value)
  const { success, primerLogin } = await auth.login(rut, password.value)

  if (success) {
    router.replace(primerLogin ? { name: 'onboarding' } : { name: 'rutas' })
  }
}

// Al presionar "Siguiente" en RUT → enfocar contraseña
function onRutNext() {
  inputPassword.value?.focus()
}

// ── Verificar sesión al montar ────────────────────────────────────────────────
onMounted(async () => {
  await auth.cargarSesion()
  if (auth.estaAutenticado) {
    router.replace({ name: 'rutas' })
  }
})
</script>

<template>
  <div class="min-h-screen flex flex-col" style="background: var(--color-acento)">

    <!-- Zona superior: logo + nombre -->
    <div class="flex flex-col items-center justify-center flex-1 gap-4 pb-6">
      <!-- Ícono camión -->
      <div class="w-20 h-20 rounded-2xl bg-white/20 flex items-center justify-center">
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

    <!-- Card inferior (≈60% pantalla) -->
    <div class="bg-white rounded-t-3xl px-6 pt-8 pb-10 shadow-2xl" style="min-height: 60vh">
      <h2 class="text-gray-800 text-xl font-bold mb-1">Iniciar sesión</h2>
      <p class="text-gray-400 text-sm mb-6">Ingresa tus credenciales para continuar</p>

      <!-- Error general del store -->
      <div v-if="auth.error" class="mb-5 p-3 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm flex items-start gap-2">
        <svg class="w-4 h-4 mt-0.5 shrink-0" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
        </svg>
        {{ auth.error }}
      </div>

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
              errorRut
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
                errorPassword
                  ? 'border-red-400 bg-red-50 focus:border-red-400'
                  : 'border-gray-100 bg-gray-50 focus:border-[--color-acento] focus:bg-white'
              ]"
            />
            <!-- Toggle mostrar/ocultar -->
            <button
              type="button"
              @click="verPassword = !verPassword"
              tabindex="-1"
              class="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 p-1"
            >
              <!-- Ojo abierto -->
              <svg v-if="!verPassword" class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"/>
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
              <!-- Ojo tachado -->
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
          :disabled="auth.cargando"
          class="w-full py-4 rounded-xl text-white font-semibold text-sm flex items-center justify-center gap-2 mt-2 transition-opacity disabled:opacity-60"
          style="background: var(--color-acento); box-shadow: 0 4px 14px color-mix(in srgb, var(--color-acento) 40%, transparent)"
        >
          <span
            v-if="auth.cargando"
            class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
          />
          {{ auth.cargando ? 'Ingresando...' : 'Ingresar' }}
        </button>

      </form>
    </div>

  </div>
</template>
