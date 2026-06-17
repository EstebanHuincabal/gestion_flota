<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { validarRut, validarEmail, validarTelefono, validarPassword, validarNombre, soloTexto } from '../../utils/validators.js'
import InputTelefono from '../../components/InputTelefono.vue'
import { COMUNAS_POR_REGION } from '../../utils/comunasChile.js'

const router = useRouter()
const route  = useRoute()

// ── Estado del wizard ────────────────────────────────────────────────────────
const paso      = ref(1)
const enviando  = ref(false)
const errorGral = ref('')

// ── Planes ───────────────────────────────────────────────────────────────────
const planes          = ref([])
const cargandoPlanes  = ref(true)
const planSeleccionado = ref(null)
const ciclo            = 'mensual'   // solo facturación mensual

onMounted(async () => {
  try {
    const res = await fetch('/api/planes/')
    if (res.ok) planes.value = await res.json()
  } catch {}
  cargandoPlanes.value = false

  // Pre-seleccionar desde query params (viene de la landing)
  if (route.query.plan_id) {
    planSeleccionado.value = planes.value.find(p => p.id == route.query.plan_id) || null
    if (planSeleccionado.value && paso.value === 1) paso.value = 2
  }
})

// ── Datos empresa ─────────────────────────────────────────────────────────────
const empresa = ref({ nombre: '', rut: '', email: '', telefono: '', direccion: '', comuna: '', ciudad: '', region: '', pais: 'Chile' })
const errEmp  = ref({})

// Comunas filtradas según la región seleccionada
const comunasDisponibles = computed(() =>
  COMUNAS_POR_REGION[empresa.value.region] || []
)

// Al cambiar región, limpiar comuna y ciudad si ya no corresponden
watch(() => empresa.value.region, () => {
  empresa.value.comuna = ''
  empresa.value.ciudad = ''
})

// Al seleccionar una comuna, auto-rellenar ciudad con el mismo valor
function onComunaChange() {
  if (empresa.value.comuna) empresa.value.ciudad = empresa.value.comuna
}

const REGIONES = [
  { value: 'arica_y_parinacota', label: 'Arica y Parinacota' },
  { value: 'tarapaca',           label: 'Tarapacá' },
  { value: 'antofagasta',        label: 'Antofagasta' },
  { value: 'atacama',            label: 'Atacama' },
  { value: 'coquimbo',           label: 'Coquimbo' },
  { value: 'valparaiso',         label: 'Valparaíso' },
  { value: 'metropolitana',      label: 'Metropolitana' },
  { value: 'ohiggins',           label: "O'Higgins" },
  { value: 'maule',              label: 'Maule' },
  { value: 'nuble',              label: 'Ñuble' },
  { value: 'biobio',             label: 'Biobío' },
  { value: 'la_araucania',       label: 'La Araucanía' },
  { value: 'los_rios',           label: 'Los Ríos' },
  { value: 'los_lagos',          label: 'Los Lagos' },
  { value: 'aysen',              label: 'Aysén' },
  { value: 'magallanes',         label: 'Magallanes' },
]

function formatRut(val) {
  let c = val.replace(/[^0-9kK]/g, '').toUpperCase().slice(0, 9)
  if (c.length < 2) return c
  const dv = c.slice(-1)
  const body = c.slice(0, -1).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${body}-${dv}`
}
// Estado de verificación del RUT empresa contra la BD
const rutEmpVerificando = ref(false)
let _debounceRutEmp = null

async function verificarRutEmpresa() {
  const r = validarRut(empresa.value.rut)
  if (!r.valido) return   // solo verificar si el formato es válido
  rutEmpVerificando.value = true
  try {
    const res = await fetch(`/api/verificar-rut/?rut=${encodeURIComponent(empresa.value.rut)}&tipo=empresa`)
    if (res.ok) {
      const data = await res.json()
      if (!data.disponible) {
        errEmp.value = { ...errEmp.value, rut: data.mensaje || 'Este RUT ya está registrado.' }
      }
    }
  } catch {} finally {
    rutEmpVerificando.value = false
  }
}

function onRutEmpInput(e) {
  const v = formatRut(e.target.value)
  empresa.value.rut = v
  e.target.value    = v
  errEmp.value.rut  = ''
  // Verificar contra la BD tras 600ms de inactividad
  clearTimeout(_debounceRutEmp)
  _debounceRutEmp = setTimeout(verificarRutEmpresa, 600)
}
// Estado de verificación del RUT usuario contra la BD
const rutUsrVerificando = ref(false)
let _debounceRutUsr = null

async function verificarRutUsuario() {
  const r = validarRut(usuario.value.rut)
  if (!r.valido) return   // solo verificar si el formato es válido
  rutUsrVerificando.value = true
  try {
    const res = await fetch(`/api/verificar-rut/?rut=${encodeURIComponent(usuario.value.rut)}&tipo=usuario`)
    if (res.ok) {
      const data = await res.json()
      if (!data.disponible) {
        errUsr.value = { ...errUsr.value, rut: data.mensaje || 'Este RUT ya está registrado.' }
      }
    }
  } catch {} finally {
    rutUsrVerificando.value = false
  }
}

function onRutUsrInput(e) {
  const v = formatRut(e.target.value)
  usuario.value.rut = v
  e.target.value    = v
  errUsr.value.rut  = ''
  // Verificar contra la BD tras 600ms de inactividad
  clearTimeout(_debounceRutUsr)
  _debounceRutUsr = setTimeout(verificarRutUsuario, 600)
}

function validarPaso2() {
  const e = {}
  const nomEmpR = validarNombre(empresa.value.nombre, 2, 30)
  if (!nomEmpR.valido) e.nombre = nomEmpR.error
  if (empresa.value.rut) {
    const r = validarRut(empresa.value.rut)
    if (!r.valido) e.rut = r.error
  }
  if (empresa.value.email) {
    const r = validarEmail(empresa.value.email)
    if (!r.valido) e.email = r.error
  }
  if (empresa.value.telefono) {
    const r = validarTelefono(empresa.value.telefono)
    if (!r.valido) e.telefono = r.error
  }
  errEmp.value = e
  return Object.keys(e).length === 0
}

// ── Datos usuario ─────────────────────────────────────────────────────────────
const usuario = ref({ nombre: '', apellido_paterno: '', apellido_materno: '', telefono: '', rut: '', email: '', password: '' })
const errUsr  = ref({})
const verPwd  = ref(false)

const nivelPwd = computed(() => {
  if (!usuario.value.password) return null
  return validarPassword(usuario.value.password).nivel || null
})

// Normaliza un RUT igual que el backend: sin puntos, minúscula, sin espacios
function _normRut(rut) {
  return (rut || '').replace(/\./g, '').trim().toLowerCase()
}

function validarPaso3() {
  const e = {}
  const nomR = validarNombre(usuario.value.nombre, 2, 30)
  if (!nomR.valido) e.nombre = nomR.error
  const apPatR = validarNombre(usuario.value.apellido_paterno, 2, 30)
  if (!apPatR.valido) e.apellido_paterno = apPatR.error
  const apMatR = validarNombre(usuario.value.apellido_materno, 2, 30)
  if (!apMatR.valido) e.apellido_materno = apMatR.error
  const telR = validarTelefono(usuario.value.telefono)
  if (!telR.valido) e.telefono = telR.error
  if (usuario.value.rut) {
    const r = validarRut(usuario.value.rut)
    if (!r.valido) e.rut = r.error
    // El RUT del admin no puede ser el mismo que el de la empresa
    else if (empresa.value.rut && _normRut(usuario.value.rut) === _normRut(empresa.value.rut)) {
      e.rut = 'El RUT del administrador no puede ser el mismo que el de la empresa.'
    }
  }
  const re = validarEmail(usuario.value.email)
  if (!re.valido) e.email = re.error
  const rp = validarPassword(usuario.value.password)
  if (!rp.valido) e.password = rp.error
  errUsr.value = e
  return Object.keys(e).length === 0
}

// ── Términos ──────────────────────────────────────────────────────────────────
const aceptaTerminos = ref(false)

// ── Precio formateado ─────────────────────────────────────────────────────────
function precio(plan) {
  const p = plan.precio_mensual
  if (!p) return 'A consultar'
  return new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(Number(p))
}

// ── Navegación entre pasos ────────────────────────────────────────────────────
function seleccionarPlan(plan) {
  planSeleccionado.value = plan
  paso.value = 2
}

async function siguientePaso2() {
  if (!validarPaso2()) return
  // Verificación final contra la BD antes de avanzar
  clearTimeout(_debounceRutEmp)
  if (empresa.value.rut) await verificarRutEmpresa()
  if (errEmp.value.rut) return
  paso.value = 3
}

async function siguientePaso3() {
  if (!validarPaso3()) return
  // Verificación final contra la BD antes de avanzar
  clearTimeout(_debounceRutUsr)
  if (usuario.value.rut) await verificarRutUsuario()
  if (errUsr.value.rut) return
  paso.value = 4
}

// ── Envío final ───────────────────────────────────────────────────────────────
async function pagar() {
  if (!aceptaTerminos.value) {
    errorGral.value = 'Debes aceptar los términos y condiciones para continuar.'
    return
  }
  errorGral.value = ''
  enviando.value  = true

  try {
    // 1. Auto-registro → devuelve JWT
    const regRes = await fetch('/api/auto-registro/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        empresa: { ...empresa.value },
        usuario: { ...usuario.value },
        plan_id: planSeleccionado.value.id,
        ciclo:   ciclo,
      }),
    })
    const regData = await regRes.json()

    if (!regRes.ok) {
      enviando.value = false
      const msg = regData.error || 'Error al crear la cuenta. Revisa los datos e intenta nuevamente.'
      // Redirigir al paso del campo que falló y marcarlo
      if (regData.campo === 'empresa_rut') {
        errEmp.value = { ...errEmp.value, rut: msg }
        paso.value = 2
      } else if (regData.campo === 'usuario_rut') {
        errUsr.value = { ...errUsr.value, rut: msg }
        paso.value = 3
      } else if (regData.campo === 'usuario_email') {
        errUsr.value = { ...errUsr.value, email: msg }
        paso.value = 3
      } else {
        errorGral.value = msg
      }
      return
    }

    // Guardar sesión temporal para el pago
    localStorage.setItem('access_token',  regData.access)
    localStorage.setItem('refresh_token', regData.refresh)
    localStorage.setItem('usuario',       JSON.stringify(regData.user))
    sessionStorage.setItem('plan_modulos',  JSON.stringify(regData.user.plan_modulos  || []))
    sessionStorage.setItem('plan_nombre',   regData.user.plan_nombre  || '')
    sessionStorage.setItem('plan_permisos', JSON.stringify(regData.user.plan_permisos || []))

    // 2. Iniciar pago con el JWT recién obtenido
    const pagoRes = await fetch('/api/pago/iniciar/', {
      method:  'POST',
      headers: {
        'Content-Type':  'application/json',
        'Authorization': `Bearer ${regData.access}`,
      },
      body: JSON.stringify({
        plan_id: planSeleccionado.value.id,
        ciclo:   ciclo,
      }),
    })
    const pagoData = await pagoRes.json()

    if (!pagoRes.ok) {
      errorGral.value = pagoData.error || 'Error al iniciar el pago. Intenta nuevamente.'
      enviando.value  = false
      return
    }

    // 3. Redirigir a Transbank
    if (pagoData.url && pagoData.token) {
      const form = document.createElement('form')
      form.method = 'POST'
      form.action = pagoData.url
      const input = document.createElement('input')
      input.type  = 'hidden'
      input.name  = 'token_ws'
      input.value = pagoData.token
      form.appendChild(input)
      document.body.appendChild(form)
      form.submit()
    } else {
      errorGral.value = 'Respuesta inesperada del servidor de pago.'
      enviando.value  = false
    }

  } catch {
    errorGral.value = 'Sin conexión con el servidor. Verifica tu red e intenta nuevamente.'
    enviando.value  = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 pt-20">
    <div class="max-w-3xl mx-auto px-4 py-12">

      <!-- Barra de progreso -->
      <div class="mb-10">
        <div class="flex items-center justify-between mb-3">
          <span class="text-sm font-medium text-gray-500">
            Paso {{ paso }} de 4
          </span>
          <button @click="router.push('/')" class="text-sm text-gray-400 hover:text-gray-600 transition-colors">
            ← Volver al inicio
          </button>
        </div>
        <div class="h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            class="h-full bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full transition-all duration-500"
            :style="`width: ${(paso / 4) * 100}%`"
          />
        </div>
        <div class="flex justify-between mt-2">
          <span
            v-for="(label, i) in ['Plan', 'Empresa', 'Administrador', 'Pago']"
            :key="i"
            class="text-xs transition-colors"
            :class="i + 1 <= paso ? 'text-indigo-600 font-semibold' : 'text-gray-400'"
          >{{ label }}</span>
        </div>
      </div>

      <!-- ── PASO 1: Elegir plan ─────────────────────────────────────── -->
      <div v-if="paso === 1">
        <h2 class="text-2xl font-extrabold text-gray-900 mb-1">Elige tu plan</h2>
        <p class="text-gray-500 mb-6 text-sm">Selecciona el plan que mejor se adapte a tu empresa.</p>

        <div v-if="cargandoPlanes" class="grid gap-4">
          <div v-for="i in 3" :key="i" class="h-32 rounded-2xl bg-white border border-gray-100 animate-pulse"/>
        </div>

        <div v-else class="grid gap-4">
          <button
            v-for="plan in planes" :key="plan.id"
            @click="seleccionarPlan(plan)"
            class="w-full text-left p-5 rounded-2xl bg-white border-2 transition-all hover:border-indigo-400 hover:shadow-md"
            :class="planSeleccionado?.id === plan.id ? 'border-indigo-500 shadow-lg shadow-indigo-100' : 'border-gray-100'"
          >
            <div class="flex items-center justify-between">
              <div>
                <p class="font-bold text-gray-900">{{ plan.nombre_display }}</p>
                <p class="text-sm text-gray-500 mt-0.5">{{ plan.max_vehiculos }} vehículos · {{ plan.max_conductores }} conductores</p>
              </div>
              <div class="text-right">
                <p class="text-2xl font-extrabold text-gray-900">{{ precio(plan) }}</p>
                <p class="text-xs text-gray-400">/mes</p>
              </div>
            </div>
          </button>
        </div>
      </div>

      <!-- ── PASO 2: Datos empresa ──────────────────────────────────── -->
      <div v-else-if="paso === 2">
        <h2 class="text-2xl font-extrabold text-gray-900 mb-1">Datos de tu empresa</h2>
        <p class="text-gray-500 mb-6 text-sm">Información de la empresa que administrará la flota.</p>

        <div class="bg-white rounded-2xl border border-gray-100 p-6 space-y-4">

          <!-- Datos básicos -->
          <p class="text-xs font-bold text-gray-400 uppercase tracking-widest border-b border-gray-100 pb-2">Datos básicos</p>

          <div class="grid sm:grid-cols-2 gap-4">
            <div class="field sm:col-span-2">
              <label class="field-label">Nombre de la empresa <span class="text-red-500">*</span></label>
              <input v-model="empresa.nombre" type="text" placeholder="Ej: Transportes del Norte S.A." class="field-input" :class="{'field-input-error': errEmp.nombre}" @input="errEmp.nombre=''" autocomplete="off" maxlength="30" />
              <p v-if="errEmp.nombre" class="field-error">{{ errEmp.nombre }}</p>
            </div>

            <div class="field">
              <label class="field-label">RUT de la empresa <span class="text-red-500">*</span></label>
              <div class="relative">
                <input :value="empresa.rut" @input="onRutEmpInput" type="text" placeholder="Ej: 76.123.456-7" class="field-input" :class="{'field-input-error': errEmp.rut}" autocomplete="off" maxlength="12" />
                <span v-if="rutEmpVerificando" class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 border-2 border-gray-300 border-t-indigo-500 rounded-full animate-spin"/>
              </div>
              <p v-if="errEmp.rut" class="field-error">{{ errEmp.rut }}</p>
            </div>
          </div>

          <!-- Contacto -->
          <p class="text-xs font-bold text-gray-400 uppercase tracking-widest border-b border-gray-100 pb-2 pt-2">Contacto</p>

          <div class="grid sm:grid-cols-2 gap-4">
            <div class="field">
              <label class="field-label">Email de contacto</label>
              <input v-model="empresa.email" type="email" placeholder="contacto@empresa.cl" class="field-input" :class="{'field-input-error': errEmp.email}" @input="errEmp.email=''" autocomplete="off" maxlength="50" />
              <p v-if="errEmp.email" class="field-error">{{ errEmp.email }}</p>
            </div>
            <div class="field">
              <label class="field-label">Teléfono</label>
              <InputTelefono v-model="empresa.telefono" :error="!!errEmp.telefono" @update:modelValue="errEmp.telefono=''" />
              <p v-if="errEmp.telefono" class="field-error">{{ errEmp.telefono }}</p>
            </div>
          </div>

          <!-- Ubicación -->
          <p class="text-xs font-bold text-gray-400 uppercase tracking-widest border-b border-gray-100 pb-2 pt-2">Ubicación</p>

          <div class="field">
            <label class="field-label">Dirección</label>
            <input v-model="empresa.direccion" type="text" placeholder="Av. Providencia 1234, Of. 5" class="field-input" autocomplete="off" maxlength="40" />
          </div>

          <div class="grid sm:grid-cols-2 gap-4">
            <div class="field">
              <label class="field-label">Región</label>
              <select v-model="empresa.region" class="field-input">
                <option value="">— Sin especificar —</option>
                <option v-for="r in REGIONES" :key="r.value" :value="r.value">{{ r.label }}</option>
              </select>
            </div>
            <div class="field">
              <label class="field-label">País</label>
              <input v-model="empresa.pais" type="text" placeholder="Chile" class="field-input" autocomplete="off" maxlength="100" />
            </div>
          </div>

          <div class="grid sm:grid-cols-2 gap-4">
            <div class="field">
              <label class="field-label">Ciudad</label>
              <select
                v-model="empresa.ciudad"
                class="field-input"
                :disabled="!empresa.region"
              >
                <option value="">{{ empresa.region ? '— Selecciona ciudad —' : '— Elige región primero —' }}</option>
                <option v-for="c in comunasDisponibles" :key="c" :value="c">{{ c }}</option>
              </select>
            </div>
            <div class="field">
              <label class="field-label">Comuna</label>
              <select
                v-model="empresa.comuna"
                class="field-input"
                :disabled="!empresa.region"
                @change="onComunaChange"
              >
                <option value="">{{ empresa.region ? '— Selecciona comuna —' : '— Elige región primero —' }}</option>
                <option v-for="c in comunasDisponibles" :key="c" :value="c">{{ c }}</option>
              </select>
            </div>
          </div>
        </div>

        <div class="flex gap-3 mt-6">
          <button @click="paso = 1" class="btn-secondary">← Atrás</button>
          <button @click="siguientePaso2" class="btn-primary flex-1">Continuar →</button>
        </div>
      </div>

      <!-- ── PASO 3: Datos administrador ────────────────────────────── -->
      <div v-else-if="paso === 3">
        <h2 class="text-2xl font-extrabold text-gray-900 mb-1">Cuenta de administrador</h2>
        <p class="text-gray-500 mb-6 text-sm">Esta cuenta tendrá acceso completo al panel de tu empresa.</p>

        <div class="bg-white rounded-2xl border border-gray-100 p-6 space-y-4">

          <div class="grid sm:grid-cols-2 gap-4">
            <div class="field">
              <label class="field-label">Nombre <span class="text-red-500">*</span></label>
              <input v-model="usuario.nombre" type="text" placeholder="Ej: Juan" class="field-input" :class="{'field-input-error': errUsr.nombre}" @input="usuario.nombre = soloTexto(usuario.nombre); errUsr.nombre=''" maxlength="30" />
              <p v-if="errUsr.nombre" class="field-error">{{ errUsr.nombre }}</p>
            </div>
            <div class="field">
              <label class="field-label">Apellido paterno <span class="text-red-500">*</span></label>
              <input v-model="usuario.apellido_paterno" type="text" placeholder="Ej: Pérez" class="field-input" :class="{'field-input-error': errUsr.apellido_paterno}" @input="usuario.apellido_paterno = soloTexto(usuario.apellido_paterno); errUsr.apellido_paterno=''" maxlength="30" />
              <p v-if="errUsr.apellido_paterno" class="field-error">{{ errUsr.apellido_paterno }}</p>
            </div>
          </div>

          <div class="grid sm:grid-cols-2 gap-4">
            <div class="field">
              <label class="field-label">Apellido materno <span class="text-red-500">*</span></label>
              <input v-model="usuario.apellido_materno" type="text" placeholder="Ej: González" class="field-input" :class="{'field-input-error': errUsr.apellido_materno}" @input="usuario.apellido_materno = soloTexto(usuario.apellido_materno); errUsr.apellido_materno=''" maxlength="30" />
              <p v-if="errUsr.apellido_materno" class="field-error">{{ errUsr.apellido_materno }}</p>
            </div>
            <div class="field">
              <label class="field-label">Teléfono <span class="text-red-500">*</span></label>
              <InputTelefono v-model="usuario.telefono" :error="!!errUsr.telefono" @update:modelValue="errUsr.telefono=''" />
              <p v-if="errUsr.telefono" class="field-error">{{ errUsr.telefono }}</p>
            </div>
          </div>

          <div class="field">
            <label class="field-label">RUT del administrador</label>
            <div class="relative">
              <input :value="usuario.rut" @input="onRutUsrInput" type="text" placeholder="9.876.543-2" class="field-input" :class="{'field-input-error': errUsr.rut}" maxlength="12" />
              <span v-if="rutUsrVerificando" class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 border-2 border-gray-300 border-t-indigo-500 rounded-full animate-spin"/>
            </div>
            <p v-if="errUsr.rut" class="field-error">{{ errUsr.rut }}</p>
          </div>

          <div class="field">
            <label class="field-label">Correo electrónico <span class="text-red-500">*</span></label>
            <input v-model="usuario.email" type="email" placeholder="admin@empresa.cl" class="field-input" :class="{'field-input-error': errUsr.email}" @input="errUsr.email=''" maxlength="50" />
            <p v-if="errUsr.email" class="field-error">{{ errUsr.email }}</p>
          </div>

          <div class="field">
            <label class="field-label">Contraseña <span class="text-red-500">*</span></label>
            <div class="relative">
              <input
                v-model="usuario.password"
                :type="verPwd ? 'text' : 'password'"
                placeholder="Mín. 8 caracteres, 1 mayúscula, 1 número"
                class="field-input pr-10"
                :class="{'field-input-error': errUsr.password}"
                @input="errUsr.password=''"
              />
              <button type="button" @click="verPwd = !verPwd" class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                  <path v-if="!verPwd" stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"/>
                  <path v-if="!verPwd" stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path v-else stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88"/>
                </svg>
              </button>
            </div>
            <!-- Indicador de fortaleza -->
            <div v-if="usuario.password && nivelPwd" class="flex items-center gap-2 mt-1.5">
              <div class="flex-1 h-1 bg-gray-200 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all"
                  :class="nivelPwd === 'fuerte' ? 'w-full bg-emerald-500' : nivelPwd === 'media' ? 'w-2/3 bg-amber-500' : 'w-1/3 bg-red-500'"
                />
              </div>
              <span class="text-xs font-medium" :class="nivelPwd === 'fuerte' ? 'text-emerald-600' : nivelPwd === 'media' ? 'text-amber-600' : 'text-red-500'">
                {{ nivelPwd === 'fuerte' ? 'Fuerte' : nivelPwd === 'media' ? 'Media' : 'Débil' }}
              </span>
            </div>
            <p v-if="errUsr.password" class="field-error">{{ errUsr.password }}</p>
          </div>
        </div>

        <div class="flex gap-3 mt-6">
          <button @click="paso = 2" class="btn-secondary">← Atrás</button>
          <button @click="siguientePaso3" class="btn-primary flex-1">Revisar y pagar →</button>
        </div>
      </div>

      <!-- ── PASO 4: Revisión y pago ─────────────────────────────────── -->
      <div v-else-if="paso === 4">
        <h2 class="text-2xl font-extrabold text-gray-900 mb-1">Revisa y paga</h2>
        <p class="text-gray-500 mb-6 text-sm">Confirma los datos antes de proceder al pago.</p>

        <div class="bg-white rounded-2xl border border-gray-100 p-6 space-y-5 mb-5">

          <!-- Resumen del plan -->
          <div>
            <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Plan elegido</p>
            <div class="flex items-center justify-between p-4 rounded-xl bg-indigo-50 border border-indigo-100">
              <div>
                <p class="font-bold text-gray-900">{{ planSeleccionado?.nombre_display }}</p>
                <p class="text-sm text-gray-500">Facturación mensual</p>
              </div>
              <div class="text-right">
                <p class="text-xl font-extrabold text-indigo-700">{{ precio(planSeleccionado) }}</p>
                <p class="text-xs text-gray-400">/mes</p>
              </div>
            </div>
          </div>

          <!-- Resumen empresa -->
          <div>
            <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Empresa</p>
            <div class="space-y-1 text-sm text-gray-700">
              <div class="flex justify-between"><span class="text-gray-500">Nombre</span> <span class="font-medium">{{ empresa.nombre }}</span></div>
              <div v-if="empresa.rut" class="flex justify-between"><span class="text-gray-500">RUT</span> <span class="font-medium">{{ empresa.rut }}</span></div>
              <div v-if="empresa.email" class="flex justify-between"><span class="text-gray-500">Email</span> <span class="font-medium">{{ empresa.email }}</span></div>
            </div>
          </div>

          <!-- Resumen admin -->
          <div>
            <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Administrador</p>
            <div class="space-y-1 text-sm text-gray-700">
              <div class="flex justify-between"><span class="text-gray-500">Nombre</span> <span class="font-medium">{{ [usuario.nombre, usuario.apellido_paterno, usuario.apellido_materno].filter(Boolean).join(' ') }}</span></div>
              <div class="flex justify-between"><span class="text-gray-500">Email</span> <span class="font-medium">{{ usuario.email }}</span></div>
              <div v-if="usuario.telefono" class="flex justify-between"><span class="text-gray-500">Teléfono</span> <span class="font-medium">{{ usuario.telefono }}</span></div>
            </div>
          </div>
        </div>

        <!-- Términos -->
        <label class="flex items-start gap-3 cursor-pointer mb-5">
          <input v-model="aceptaTerminos" type="checkbox" class="mt-0.5 w-4 h-4 accent-indigo-600" />
          <span class="text-sm text-gray-600">
            Acepto los
            <a href="/terminos" target="_blank" class="text-indigo-600 underline hover:text-indigo-700">términos y condiciones</a>
            del servicio.
          </span>
        </label>

        <!-- Error general -->
        <div v-if="errorGral" class="mb-4 p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-start gap-2">
          <svg class="w-4 h-4 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
          </svg>
          {{ errorGral }}
        </div>

        <!-- Nota de seguridad -->
        <div class="flex items-center gap-2 text-xs text-gray-400 mb-5">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"/>
          </svg>
          Pago seguro con Transbank Webpay Plus. Tus datos están encriptados.
        </div>

        <div class="flex gap-3">
          <button @click="paso = 3" class="btn-secondary" :disabled="enviando">← Atrás</button>
          <button @click="pagar" class="btn-primary flex-1 flex items-center justify-center gap-2" :disabled="enviando">
            <span v-if="enviando" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"/>
            {{ enviando ? 'Procesando...' : 'Ir a pagar con Transbank' }}
          </button>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.field         { display: flex; flex-direction: column; gap: 0.3rem; }
.field-label   { font-size: 0.8125rem; font-weight: 600; color: #374151; }
.field-input   {
  padding: 0.625rem 0.75rem;
  border: 1.5px solid #E5E7EB;
  border-radius: 10px;
  font-size: 0.875rem;
  color: #111827;
  background: #fff;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
  width: 100%;
}
.field-input:focus        { border-color: #6366F1; box-shadow: 0 0 0 3px rgba(99,102,241,0.12); }
.field-input-error        { border-color: #EF4444 !important; }
.field-error              { font-size: 0.75rem; color: #EF4444; margin-top: 0.15rem; }

.btn-primary {
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s, transform 0.1s;
}
.btn-primary:hover:not(:disabled)  { opacity: 0.92; }
.btn-primary:active:not(:disabled) { transform: scale(0.98); }
.btn-primary:disabled              { opacity: 0.55; cursor: not-allowed; }

.btn-secondary {
  padding: 0.75rem 1.25rem;
  background: #fff;
  color: #374151;
  border: 1.5px solid #E5E7EB;
  border-radius: 12px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.btn-secondary:hover:not(:disabled) { border-color: #9CA3AF; background: #F9FAFB; }
.btn-secondary:disabled             { opacity: 0.55; cursor: not-allowed; }
</style>
