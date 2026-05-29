<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiFetch } from '../../utils/api.js'
import { useToast } from '../../utils/useToast.js'
import ConfirmModal from '../../components/ConfirmModal.vue'

const toast   = useToast()
const planes  = ref([])
const empresas = ref([])
const cargando = ref(false)

// ── KPIs ──────────────────────────────────────────────────────────────────
const kpis = computed(() => {
  const total      = planes.value.length
  const conPlan    = empresas.value.filter(e => e.plan_id).length
  const sinPlan    = empresas.value.filter(e => !e.plan_id && e.estado === 'activa').length
  const conteos    = {}
  for (const p of planes.value) conteos[p.id] = p.empresas_activas
  const masUsado   = planes.value.slice().sort((a, b) => (conteos[b.id] || 0) - (conteos[a.id] || 0))[0]
  return { total, conPlan, sinPlan, masUsado: masUsado?.nombre_display ?? '—' }
})

const empresasSinPlan = computed(() =>
  empresas.value.filter(e => !e.plan_id && e.estado === 'activa')
)

// ── Módulos disponibles ────────────────────────────────────────────────────
const MODULOS = [
  { cat: 'Core', items: [
    { key: 'dashboard',           label: 'Dashboard' },
    { key: 'flotas',              label: 'Flotas' },
    { key: 'vehiculos',           label: 'Vehículos' },
    { key: 'conductores',         label: 'Conductores' },
    { key: 'mantencion_correctiva', label: 'Mantención Correctiva' },
  ]},
  { cat: 'Avanzado', items: [
    { key: 'mantencion_predictiva',  label: 'Mantención Predictiva' },
    { key: 'documentos',             label: 'Documentos' },
    { key: 'notificaciones_avanzadas', label: 'Notificaciones Avanzadas' },
  ]},
  { cat: 'Premium', items: [
    { key: 'gps',       label: 'GPS / Telemetría' },
    { key: 'geofencing', label: 'Geofencing' },
    { key: 'reportes',  label: 'Reportes' },
    { key: 'exportacion', label: 'Exportación' },
    { key: 'api_access', label: 'Acceso API' },
  ]},
]

// ── Modal plan ─────────────────────────────────────────────────────────────
const modalPlan      = ref(false)
const editandoPlan   = ref(null)
const todosPermisos  = ref([])
const permisosPlan   = ref([])
const cargandoPermisos = ref(false)

const formPlan = ref({
  nombre: 'basico', descripcion: '',
  precio_mensual: '',
  max_flotas: 2, max_vehiculos: 10,
  max_conductores: 15, max_usuarios: 3,
  modulos: [], activo: true, orden: 0,
})

// Permisos agrupados por categoría (igual que GestionPermisos)
const permisosAgrupados = computed(() => {
  const grupos = {}
  for (const p of todosPermisos.value) {
    if (!grupos[p.categoria]) grupos[p.categoria] = []
    grupos[p.categoria].push(p)
  }
  return grupos
})

const categoriaCompleta = (permisosCat) =>
  permisosCat.every(p => permisosPlan.value.includes(p.codigo))

const categoriaIndeterminate = (permisosCat) => {
  const alguno = permisosCat.some(p => permisosPlan.value.includes(p.codigo))
  return alguno && !categoriaCompleta(permisosCat)
}

const toggleCategoria = (permisosCat) => {
  const codigos = permisosCat.map(p => p.codigo)
  if (categoriaCompleta(permisosCat)) {
    permisosPlan.value = permisosPlan.value.filter(c => !codigos.includes(c))
  } else {
    const nuevos = codigos.filter(c => !permisosPlan.value.includes(c))
    permisosPlan.value = [...permisosPlan.value, ...nuevos]
  }
}

const abrirModalCrear = async () => {
  editandoPlan.value = null
  formPlan.value = {
    nombre: '', descripcion: '',
    precio_mensual: '',
    max_flotas: 2, max_vehiculos: 10,
    max_conductores: 15, max_usuarios: 3,
    modulos: [], activo: true, orden: 0,
  }
  permisosPlan.value  = []
  todosPermisos.value = []
  modalPlan.value     = true
  cargandoPermisos.value = true
  const res = await apiFetch('/api/permisos/')
  if (res.ok) todosPermisos.value = await res.json()
  cargandoPermisos.value = false
}

const abrirModalEditar = async (plan) => {
  editandoPlan.value = plan
  formPlan.value = {
    nombre:          plan.nombre,
    descripcion:     plan.descripcion || '',
    precio_mensual:  plan.precio_mensual ?? '',
    max_flotas:      plan.max_flotas,
    max_vehiculos:   plan.max_vehiculos,
    max_conductores: plan.max_conductores,
    max_usuarios:    plan.max_usuarios,
    modulos:         [...(plan.modulos || [])],
    activo:          plan.activo,
    orden:           plan.orden,
  }
  permisosPlan.value  = []
  todosPermisos.value = []
  modalPlan.value     = true
  cargandoPermisos.value = true
  const res = await apiFetch(`/api/configuracion/planes/${plan.id}/permisos/`)
  if (res.ok) {
    const data = await res.json()
    permisosPlan.value  = [...(data.permisos_plan  || [])]
    todosPermisos.value = data.todos_permisos || []
  }
  cargandoPermisos.value = false
}

const toggleModulo = (key) => {
  const idx = formPlan.value.modulos.indexOf(key)
  if (idx === -1) formPlan.value.modulos.push(key)
  else formPlan.value.modulos.splice(idx, 1)
}

const guardandoPlan = ref(false)
const guardarPlan = async () => {
  const f = formPlan.value
  if (!f.nombre.trim()) {
    toast.error('El nombre del plan es obligatorio.')
    return
  }
  if (f.nombre.trim().length > 30) {
    toast.error('El nombre no puede superar los 30 caracteres.')
    return
  }
  if ((f.descripcion || '').length > 100) {
    toast.error('La descripción no puede superar los 100 caracteres.')
    return
  }
  if (f.orden === '' || f.orden === null || Number(f.orden) < 0) {
    toast.error('El orden de visualización no puede ser negativo.')
    return
  }
  const numericos = {
    'Precio mensual':    f.precio_mensual,
    'Máx. flotas':       f.max_flotas,
    'Máx. vehículos':    f.max_vehiculos,
    'Máx. conductores':  f.max_conductores,
    'Máx. usuarios':     f.max_usuarios,
  }
  for (const [label, val] of Object.entries(numericos)) {
    if (val !== '' && val !== null && Number(val) < 0) {
      toast.error(`${label} no puede ser un número negativo.`)
      return
    }
  }
  guardandoPlan.value = true
  try {
    const body = {
      ...formPlan.value,
      precio_mensual: formPlan.value.precio_mensual === '' ? null : Number(formPlan.value.precio_mensual),
    }
    const url    = editandoPlan.value ? `/api/configuracion/planes/${editandoPlan.value.id}/` : '/api/configuracion/planes/'
    const method = editandoPlan.value ? 'PUT' : 'POST'
    const res    = await apiFetch(url, { method, body })
    if (!res.ok) {
      const err = await res.json()
      toast.error(err.error || JSON.stringify(err))
      guardandoPlan.value = false
      return
    }

    const planGuardado = await res.json()
    const planId = planGuardado.id || editandoPlan.value?.id

    // Guardar permisos del plan
    await apiFetch(`/api/configuracion/planes/${planId}/permisos/`, {
      method: 'PUT',
      body:   { permisos: permisosPlan.value },
    })

    toast.success(editandoPlan.value ? 'Plan actualizado.' : 'Plan creado.')
    modalPlan.value = false
    await cargarPlanes()
  } catch { toast.error('Error al guardar.') }
  guardandoPlan.value = false
}

const confirmPlan = ref({ visible: false, plan: null, accion: 'desactivar' })

const pedirToggle = (plan) => {
  confirmPlan.value = { visible: true, plan, accion: plan.activo ? 'desactivar' : 'activar' }
}
const cancelarToggle = () => {
  confirmPlan.value = { visible: false, plan: null, accion: 'desactivar' }
}
const confirmarToggle = async () => {
  const { plan } = confirmPlan.value
  cancelarToggle()
  const res = await apiFetch(`/api/configuracion/planes/${plan.id}/`, {
    method: 'PUT',
    body:   { activo: !plan.activo },
  })
  if (res.ok) {
    toast.success(plan.activo ? 'Plan desactivado.' : 'Plan activado.')
    await cargarPlanes()
  } else {
    const err = await res.json()
    toast.error(err.error || 'No se pudo actualizar el plan.')
  }
}

// ── Carga de datos ─────────────────────────────────────────────────────────
const cargarPlanes = async () => {
  const res = await apiFetch('/api/configuracion/planes/')
  if (res.ok) planes.value = await res.json()
}

const cargarEmpresas = async () => {
  const res = await apiFetch('/api/empresas/')
  if (res.ok) {
    const data = await res.json()
    empresas.value = Array.isArray(data) ? data : data.results || []
  }
}

onMounted(async () => {
  cargando.value = true
  await Promise.all([cargarPlanes(), cargarEmpresas()])
  cargando.value = false
})

// ── Precio display ─────────────────────────────────────────────────────────
const precioDisplay = (plan) => {
  if (plan.precio_mensual) {
    return `$${Number(plan.precio_mensual).toLocaleString('es-CL')}/mes`
  }
  return 'A convenir'
}

const colorPlan = (nombre) => ({
  basico:     'border-blue-200 from-blue-50',
  pro:        'border-indigo-300 from-indigo-50',
  enterprise: 'border-purple-300 from-purple-50',
})[nombre] || 'border-gray-200 from-gray-50'

const badgePlan = (nombre) => ({
  basico:     'bg-blue-100 text-blue-700',
  pro:        'bg-indigo-100 text-indigo-700',
  enterprise: 'bg-purple-100 text-purple-700',
})[nombre] || 'bg-gray-100 text-gray-700'
</script>

<template>

  <ConfirmModal
    v-if="confirmPlan.visible"
    :titulo="confirmPlan.accion === 'desactivar' ? 'Desactivar plan' : 'Activar plan'"
    :mensaje="confirmPlan.accion === 'desactivar'
      ? `¿Desactivar &quot;${confirmPlan.plan?.nombre_display}&quot;? Las empresas que ya lo tienen lo conservan; solo dejará de ofrecerse a nuevos clientes.`
      : `¿Activar &quot;${confirmPlan.plan?.nombre_display}&quot;? Volverá a ofrecerse a nuevos clientes.`"
    :label-ok="confirmPlan.accion === 'desactivar' ? 'Desactivar' : 'Activar'"
    :peligroso="confirmPlan.accion === 'desactivar'"
    @confirmar="confirmarToggle"
    @cancelar="cancelarToggle"
  />

  <div class="page p-6 max-w-7xl mx-auto">

    <!-- Encabezado -->
    <div class="mb-6 flex justify-between items-start">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Planes de Suscripción</h1>
        <p class="text-sm text-gray-500 mt-1">Gestiona los planes y asígnalos a empresas.</p>
      </div>
      <button @click="abrirModalCrear"
        class="px-4 py-2 bg-indigo-600 text-white text-sm font-semibold rounded-lg hover:bg-indigo-700 transition-colors">
        + Nuevo plan
      </button>
    </div>

    <!-- KPIs -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div class="bg-white rounded-xl border border-gray-200 p-4">
        <p class="text-xs text-gray-500 font-medium">Total planes</p>
        <p class="text-2xl font-bold text-gray-900 mt-1">{{ kpis.total }}</p>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-4">
        <p class="text-xs text-gray-500 font-medium">Empresas con plan</p>
        <p class="text-2xl font-bold text-gray-900 mt-1">{{ kpis.conPlan }}</p>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-4">
        <p class="text-xs text-gray-500 font-medium">Plan más usado</p>
        <p class="text-lg font-bold text-indigo-600 mt-1">{{ kpis.masUsado }}</p>
      </div>
      <div class="bg-white rounded-xl border border-gray-200 p-4">
        <p class="text-xs text-gray-500 font-medium">Sin plan</p>
        <p class="text-2xl font-bold mt-1" :class="kpis.sinPlan > 0 ? 'text-orange-500' : 'text-gray-900'">
          {{ kpis.sinPlan }}
        </p>
      </div>
    </div>

    <!-- Loader -->
    <div v-if="cargando" class="flex justify-center py-16">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
    </div>

    <!-- Cards de planes -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-10">
      <div v-for="plan in planes" :key="plan.id"
        :class="['bg-gradient-to-b border rounded-2xl overflow-hidden transition-shadow hover:shadow-md', colorPlan(plan.nombre)]">

        <!-- Header del card -->
        <div class="px-5 pt-5 pb-4">
          <div class="flex justify-between items-start mb-3">
            <span :class="['text-xs font-semibold px-2.5 py-1 rounded-full', badgePlan(plan.nombre)]">
              {{ plan.nombre_display }}
            </span>
            <span v-if="!plan.activo" class="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
              Inactivo
            </span>
          </div>

          <p class="text-2xl font-bold text-gray-900">{{ precioDisplay(plan) }}</p>
          <p class="text-xs text-gray-500 mt-1.5">{{ plan.descripcion }}</p>
        </div>

        <!-- Límites -->
        <div class="px-5 py-3 border-t border-white/60 space-y-1.5">
          <div class="flex justify-between text-sm">
            <span class="text-gray-600">Flotas</span>
            <span class="font-semibold text-gray-900">
              {{ plan.max_flotas >= 9999 ? 'Ilimitado' : plan.max_flotas }}
            </span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-gray-600">Vehículos</span>
            <span class="font-semibold text-gray-900">
              {{ plan.max_vehiculos >= 9999 ? 'Ilimitado' : plan.max_vehiculos }}
            </span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-gray-600">Conductores</span>
            <span class="font-semibold text-gray-900">
              {{ plan.max_conductores >= 9999 ? 'Ilimitado' : plan.max_conductores }}
            </span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-gray-600">Usuarios admin</span>
            <span class="font-semibold text-gray-900">
              {{ plan.max_usuarios >= 9999 ? 'Ilimitado' : plan.max_usuarios }}
            </span>
          </div>
        </div>

        <!-- Módulos -->
        <div class="px-5 py-3 border-t border-white/60">
          <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Módulos</p>
          <div class="flex flex-wrap gap-1.5">
            <span v-for="mod in (plan.modulos || [])" :key="mod"
              class="text-xs px-2 py-0.5 bg-white/70 border border-white/80 text-gray-700 rounded-full">
              {{ mod.replace(/_/g, ' ') }}
            </span>
            <span v-if="!(plan.modulos || []).length" class="text-xs text-gray-400">Sin módulos</span>
          </div>
        </div>

        <!-- Footer -->
        <div class="px-5 py-3 border-t border-white/60 bg-white/40 flex justify-between items-center">
          <span class="text-xs text-gray-500">
            {{ plan.empresas_activas }} empresa{{ plan.empresas_activas !== 1 ? 's' : '' }}
          </span>
          <div class="flex gap-2">
            <button @click="abrirModalEditar(plan)"
              class="text-xs px-2.5 py-1 border border-gray-300 bg-white text-gray-700 rounded-md font-medium hover:bg-gray-50 transition-colors">
              Editar
            </button>
            <button @click="pedirToggle(plan)"
              :class="['text-xs px-2.5 py-1 border rounded-md font-medium transition-colors',
                plan.activo
                  ? 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100'
                  : 'border-green-200 bg-green-50 text-green-700 hover:bg-green-100']">
              {{ plan.activo ? 'Desactivar' : 'Activar' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Empresas sin plan -->
    <div v-if="!cargando && empresasSinPlan.length" class="bg-white rounded-2xl border border-orange-200 overflow-hidden">
      <div class="px-6 py-4 border-b border-orange-100 bg-orange-50/50 flex items-center gap-2">
        <svg class="w-4 h-4 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
        </svg>
        <h3 class="font-semibold text-orange-800 text-sm">Empresas sin plan ({{ empresasSinPlan.length }})</h3>
      </div>
      <div class="divide-y divide-gray-100">
        <div v-for="empresa in empresasSinPlan" :key="empresa.id"
          class="px-6 py-3">
          <span class="text-sm font-medium text-gray-800">{{ empresa.nombre }}</span>
        </div>
      </div>
    </div>

  </div>

  <!-- ── Modal crear / editar plan ─────────────────────────────────────── -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modalPlan" class="overlay" @click.self="modalPlan = false">
        <div class="modal-lg">
          <div class="modal-header">
            <h2 class="modal-title">{{ editandoPlan ? 'Editar plan' : 'Nuevo plan' }}</h2>
            <button @click="modalPlan = false" class="close-btn">✕</button>
          </div>
          <div class="modal-body">
            <div class="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label class="field-label">Nombre del plan</label>
                <input v-model="formPlan.nombre" type="text" class="field-input"
                  placeholder="Ej: Premium" maxlength="30" />
              </div>
              <div>
                <label class="field-label">Orden de visualización</label>
                <input v-model.number="formPlan.orden" type="number" class="field-input" min="0"/>
              </div>
            </div>

            <div class="mb-4">
              <label class="field-label">Descripción</label>
              <textarea v-model="formPlan.descripcion" class="field-input" rows="2"
                maxlength="100" placeholder="Descripción del plan..."></textarea>
            </div>

            <div class="mb-4">
              <div>
                <label class="field-label">Precio mensual (CLP, sin puntos)</label>
                <input v-model="formPlan.precio_mensual" type="number" class="field-input"
                  min="0" placeholder="Ej: 49000"/>
              </div>
            </div>

            <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
              <div>
                <label class="field-label">Máx. flotas</label>
                <input v-model.number="formPlan.max_flotas" type="number" class="field-input" min="1"/>
              </div>
              <div>
                <label class="field-label">Máx. vehículos</label>
                <input v-model.number="formPlan.max_vehiculos" type="number" class="field-input" min="1"/>
              </div>
              <div>
                <label class="field-label">Máx. conductores</label>
                <input v-model.number="formPlan.max_conductores" type="number" class="field-input" min="1"/>
              </div>
              <div>
                <label class="field-label">Máx. usuarios admin</label>
                <input v-model.number="formPlan.max_usuarios" type="number" class="field-input" min="1"/>
              </div>
            </div>

            <!-- Permisos granulares -->
            <div class="mt-5">
              <div class="flex items-center justify-between mb-2">
                <label class="field-label mb-0">Permisos incluidos</label>
                <div class="flex gap-2">
                  <button type="button" class="perm-btn-all"
                    @click="permisosPlan = todosPermisos.map(p => p.codigo)">
                    Todos
                  </button>
                  <button type="button" class="perm-btn-all perm-btn-none"
                    @click="permisosPlan = []">
                    Ninguno
                  </button>
                </div>
              </div>

              <div v-if="cargandoPermisos" class="perm-loading">Cargando permisos...</div>
              <div v-else class="perm-grid">
                <div v-for="(permisosCat, cat) in permisosAgrupados" :key="cat" class="perm-cat-card">
                  <div class="perm-cat-header">
                    <label class="perm-cat-label">
                      <input
                        type="checkbox"
                        :checked="categoriaCompleta(permisosCat)"
                        :indeterminate="categoriaIndeterminate(permisosCat)"
                        @change="toggleCategoria(permisosCat)"
                        class="perm-check"
                      />
                      <span class="perm-cat-nombre">{{ cat }}</span>
                    </label>
                    <span :class="['perm-cat-count', { completo: categoriaCompleta(permisosCat) }]">
                      {{ permisosCat.filter(p => permisosPlan.includes(p.codigo)).length }}/{{ permisosCat.length }}
                    </span>
                  </div>
                  <div class="perm-lista">
                    <label v-for="p in permisosCat" :key="p.codigo" class="perm-item">
                      <input type="checkbox" :value="p.codigo" v-model="permisosPlan" class="perm-check"/>
                      <span class="perm-nombre">{{ p.nombre }}</span>
                    </label>
                  </div>
                </div>
                <p v-if="!todosPermisos.length" class="perm-vacio">Sin permisos disponibles.</p>
              </div>
            </div>

            <div class="flex items-center gap-2 mt-4">
              <input type="checkbox" v-model="formPlan.activo" id="activo-check" class="rounded border-gray-300 text-indigo-600"/>
              <label for="activo-check" class="text-sm text-gray-700">Plan activo</label>
            </div>
          </div>
          <div class="modal-footer">
            <button @click="modalPlan = false" class="btn-cancel">Cancelar</button>
            <button @click="guardarPlan" :disabled="guardandoPlan" class="btn-save">
              {{ guardandoPlan ? 'Guardando...' : (editandoPlan ? 'Guardar cambios' : 'Crear plan') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

</template>

<style scoped>
.overlay {
  position: fixed; inset: 0; z-index: 8000;
  background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
  padding: 1.5rem; overflow-y: auto;
}
.modal-lg {
  background: #fff; border-radius: 16px;
  width: 100%; max-width: 640px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
  max-height: 90vh; display: flex; flex-direction: column;
}
.modal-sm {
  background: #fff; border-radius: 16px;
  width: 100%; max-width: 420px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 1.25rem 1.5rem; border-bottom: 1px solid #F3F4F6; flex-shrink: 0;
}
.modal-title { font-size: 1.0625rem; font-weight: 700; color: #111827; }
.close-btn {
  background: none; border: none; cursor: pointer;
  color: #9CA3AF; font-size: 1rem; padding: 0.25rem;
  transition: color 0.15s;
}
.close-btn:hover { color: #374151; }
.modal-body { padding: 1.5rem; overflow-y: auto; flex: 1; min-height: 0; }
.modal-footer {
  display: flex; justify-content: flex-end; gap: 0.75rem;
  padding: 1rem 1.5rem; border-top: 1px solid #F3F4F6; flex-shrink: 0;
}
.field-label { display: block; font-size: 0.8125rem; font-weight: 600; color: #374151; margin-bottom: 0.375rem; }
.field-input {
  width: 100%; padding: 0.5rem 0.75rem;
  border: 1.5px solid #E5E7EB; border-radius: 8px;
  font-size: 0.875rem; color: #111827; background: #fff;
  transition: border-color 0.15s, box-shadow 0.15s; outline: none; font-family: inherit;
}
.field-input:focus { border-color: #6366F1; box-shadow: 0 0 0 3px rgba(99,102,241,0.12); }
select.field-input { appearance: none; cursor: pointer; }
textarea.field-input { resize: vertical; min-height: 60px; }
.btn-cancel {
  padding: 0.55rem 1.25rem; border: 1.5px solid #E5E7EB;
  background: #fff; color: #374151; border-radius: 8px;
  font-size: 0.875rem; font-weight: 500; cursor: pointer; transition: background 0.15s;
}
.btn-cancel:hover { background: #F9FAFB; }
.btn-save {
  padding: 0.55rem 1.5rem;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff; border: none; border-radius: 8px;
  font-size: 0.875rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s;
}
.btn-save:disabled { opacity: 0.65; cursor: not-allowed; }
.btn-save:not(:disabled):hover { opacity: 0.9; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ── Permisos dentro del modal ── */
.perm-loading { font-size: 0.8125rem; color: #9CA3AF; padding: 0.75rem 0; }
.perm-vacio   { font-size: 0.8125rem; color: #9CA3AF; padding: 0.5rem 0; grid-column: 1/-1; }

.perm-btn-all {
  font-size: 0.6875rem; font-weight: 600; padding: 0.2rem 0.625rem;
  border-radius: 6px; border: 1px solid #C4B5FD;
  background: #EEF2FF; color: #4338CA;
  cursor: pointer; font-family: inherit; transition: background 0.15s;
}
.perm-btn-all:hover { background: #DDD6FE; }
.perm-btn-none { background: #F9FAFB; border-color: #E5E7EB; color: #6B7280; }
.perm-btn-none:hover { background: #F3F4F6; }

.perm-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(175px, 1fr));
  gap: 0.625rem;
}
.perm-cat-card {
  border: 1px solid #E5E7EB; border-radius: 10px; overflow: hidden;
}
.perm-cat-header {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.5rem 0.625rem; background: #F9FAFB;
  border-bottom: 1px solid #F3F4F6;
}
.perm-cat-label {
  display: flex; align-items: center; gap: 0.375rem;
  flex: 1; cursor: pointer; min-width: 0;
}
.perm-check { cursor: pointer; accent-color: #7C3AED; flex-shrink: 0; }
.perm-cat-nombre {
  font-size: 0.75rem; font-weight: 600; color: #374151;
  text-transform: capitalize; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.perm-cat-count {
  font-size: 0.625rem; font-weight: 600; padding: 0.1rem 0.35rem;
  border-radius: 100px; background: #F3F4F6; color: #6B7280; flex-shrink: 0;
}
.perm-cat-count.completo { background: #EEF2FF; color: #4338CA; }
.perm-lista { padding: 0.4rem 0.625rem; display: flex; flex-direction: column; gap: 0.2rem; }
.perm-item {
  display: flex; align-items: center; gap: 0.375rem;
  font-size: 0.75rem; color: #374151; cursor: pointer;
}
.perm-nombre { line-height: 1.4; }
</style>
