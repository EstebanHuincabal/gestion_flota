<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const router = useRouter()
const auth   = useAuthStore()

const rut      = ref('')
const password = ref('')
const verPass  = ref(false)

// Acepta el RUT sin formateo — el backend usa RutBackend que normaliza
const onRutInput = (e) => {
  rut.value = e.target.value.replace(/\s/g, '')
}

const onSubmit = async () => {
  const ok = await auth.login(rut.value, password.value)
  if (ok) router.replace({ name: 'dashboard' })
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-indigo-600 to-violet-700 flex flex-col items-center justify-center p-6 safe-area-inset">

    <!-- Logo / encabezado -->
    <div class="mb-8 text-center">
      <div class="w-20 h-20 bg-white/20 backdrop-blur rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
        <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>
        </svg>
      </div>
      <h1 class="text-white text-2xl font-bold tracking-tight">Gestión de Flota</h1>
      <p class="text-white/70 text-sm mt-1">App del Conductor</p>
    </div>

    <!-- Card de login -->
    <div class="w-full max-w-sm bg-white rounded-2xl p-6 shadow-2xl">
      <h2 class="text-gray-800 text-xl font-bold mb-1">Bienvenido</h2>
      <p class="text-gray-500 text-sm mb-6">Ingresa tus credenciales para continuar</p>

      <!-- Mensaje de error -->
      <div v-if="auth.error" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm flex items-start gap-2">
        <svg class="w-4 h-4 mt-0.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
        </svg>
        {{ auth.error }}
      </div>

      <form @submit.prevent="onSubmit" class="flex flex-col gap-4">

        <!-- RUT -->
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">RUT</label>
          <input
            :value="rut"
            @input="onRutInput"
            type="text"
            placeholder="12345678-9"
            inputmode="text"
            autocomplete="username"
            autocorrect="off"
            autocapitalize="none"
            :disabled="auth.cargando"
            required
            class="w-full px-4 py-3 border-2 border-gray-100 rounded-xl text-sm text-gray-800 bg-gray-50 focus:outline-none focus:border-indigo-500 focus:bg-white transition disabled:opacity-50"
          />
        </div>

        <!-- Contraseña -->
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">Contraseña</label>
          <div class="relative">
            <input
              v-model="password"
              :type="verPass ? 'text' : 'password'"
              placeholder="••••••••"
              autocomplete="current-password"
              :disabled="auth.cargando"
              required
              class="w-full px-4 py-3 pr-11 border-2 border-gray-100 rounded-xl text-sm text-gray-800 bg-gray-50 focus:outline-none focus:border-indigo-500 focus:bg-white transition disabled:opacity-50"
            />
            <button
              type="button"
              @click="verPass = !verPass"
              class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              tabindex="-1"
            >
              <svg v-if="!verPass" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
              </svg>
              <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Botón -->
        <button
          type="submit"
          :disabled="auth.cargando"
          class="w-full py-3 bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-semibold rounded-xl text-sm shadow-md shadow-indigo-200 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2 mt-2"
        >
          <span
            v-if="auth.cargando"
            class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
          />
          {{ auth.cargando ? 'Ingresando...' : 'Ingresar' }}
        </button>

      </form>
    </div>

    <p class="text-white/40 text-xs mt-8">v1.0 · Solo para conductores autorizados</p>
  </div>
</template>
