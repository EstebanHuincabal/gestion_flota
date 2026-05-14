<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiFetch } from '../../utils/api.js'
import { useToast } from '../../utils/useToast.js'

const router = useRouter()
const route  = useRoute()
const id     = route.params.id

const toast     = useToast()
const cargando  = ref(true)
const guardando = ref(false)
const error     = ref('')
const errores   = ref({})
const empresas  = ref([])
const todosPermisos = ref([])
const permisosSeleccionados = ref([])

const form = ref({ nombre_completo: '', email: '', rol: 'USUARIO', empresa_id: null })

const rolesDisponibles = [
  { value: 'SUPERADMIN', label: 'Super Administrador' },
  { value: 'USUARIO',    label: 'Usuario' },
  { value: 'CONDUCTOR',  label: 'Conductor' },
]

const permisosAgrupados = computed(() => {
  const grupos = {}
  for (const p of todosPermisos.value) {
    if (!grupos[p.categoria]) grupos[p.categoria] = []
    grupos[p.categoria].push(p)
  }
  return grupos
})

const toggleCategoria = (permisosCat) => {
  const codigos = permisosCat.map(p => p.codigo)
  const todosActivos = codigos.every(c => permisosSeleccionados.value.includes(c))
  if (todosActivos) {
    permisosSeleccionados.value = permisosSeleccionados.value.filter(c => !codigos.includes(c))
  } else {
    const nuevos = codigos.filter(c => !permisosSeleccionados.value.includes(c))
    permisosSeleccionados.value = [...permisosSeleccionados.value, ...nuevos]
  }
}

const categoriaCompleta = (permisosCat) =>
  permisosCat.every(p => permisosSeleccionados.value.includes(p.codigo))

const cargar = async () => {
  try {
    const [resU, resE, resP] = await Promise.all([
      apiFetch(`/api/usuarios/${id}/`),
      apiFetch('/api/empresas/'),
      apiFetch('/api/permisos/'),
    ])
    if (!resU.ok) throw new Error('Usuario no encontrado')
    const u = await resU.json()
    form.value.nombre_completo   = u.nombre
    form.value.email             = u.email
    form.value.rol               = u.rol
    form.value.empresa_id        = u.empresa_id
    permisosSeleccionados.value  = u.permisos || []
    if (resE.ok) empresas.value       = (await resE.json()).filter(e => e.estado === 'activa')
    if (resP.ok) todosPermisos.value  = await resP.json()
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

const guardar = async () => {
  error.value   = ''
  errores.value = {}
  guardando.value = true
  try {
    const payload = { ...form.value }
    if (form.value.rol === 'USUARIO') payload.permisos = permisosSeleccionados.value

    const res  = await apiFetch(`/api/usuarios/${id}/`, { method: 'PUT', body: payload })
    const data = await res.json()
    if (!res.ok) {
      if (data.error === 'Sin permisos.') return
      if (typeof data === 'object' && !data.error) errores.value = data
      else error.value = data.error || 'Error al actualizar el usuario'
      return
    }
    toast.success('Usuario actualizado exitosamente')
    router.push('/usuarios')
  } catch {
    error.value = 'Error de conexión con el servidor'
  } finally {
    guardando.value = false
  }
}

onMounted(cargar)
</script>

<template>
  <div class="page">
    <div class="breadcrumb">
      <button class="btn-back" @click="router.push('/usuarios')">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
        </svg>
        Volver a Usuarios
      </button>
    </div>

    <h1 class="page-title">Editar Usuario</h1>
    <p class="page-subtitle">Modifica los datos del usuario</p>

    <div v-if="cargando" class="loading">
      <div class="spinner"/> <span>Cargando datos...</span>
    </div>

    <div v-else class="card">
      <div v-if="error" class="alert-error">{{ error }}</div>

      <form @submit.prevent="guardar" class="form">

        <div class="form-row">
          <div class="form-group">
            <label class="label">Nombre completo</label>
            <input v-model="form.nombre_completo" type="text" class="input"
              :class="{ 'input-error': errores.nombre_completo }"
              placeholder="Nombre completo" required autocomplete="off"/>
            <p v-if="errores.nombre_completo" class="field-error">{{ errores.nombre_completo[0] }}</p>
          </div>

          <div class="form-group">
            <label class="label">Email</label>
            <input v-model="form.email" type="email" class="input"
              :class="{ 'input-error': errores.email }"
              placeholder="usuario@ejemplo.com" required autocomplete="off"/>
            <p v-if="errores.email" class="field-error">{{ errores.email[0] }}</p>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="label">Rol</label>
            <select v-model="form.rol" class="input select"
              :class="{ 'input-error': errores.rol }">
              <option v-for="r in rolesDisponibles" :key="r.value" :value="r.value">
                {{ r.label }}
              </option>
            </select>
            <p v-if="errores.rol" class="field-error">{{ errores.rol[0] }}</p>
          </div>

          <div class="form-group">
            <label class="label">Empresa</label>
            <select v-model="form.empresa_id" class="input select"
              :class="{ 'input-error': errores.empresa_id }" required>
              <option :value="null">— Seleccionar empresa —</option>
              <option v-for="e in empresas" :key="e.id" :value="e.id">{{ e.nombre }}</option>
            </select>
            <p v-if="errores.empresa_id" class="field-error">{{ errores.empresa_id[0] }}</p>
          </div>
        </div>

        <!-- Sección de permisos (solo para USUARIO) -->
        <div v-if="form.rol === 'USUARIO' && todosPermisos.length" class="permisos-seccion">
          <div class="permisos-header">
            <span class="label">Permisos</span>
            <button type="button" class="btn-todos" @click="permisosSeleccionados = todosPermisos.map(p => p.codigo)">Todos</button>
            <button type="button" class="btn-todos btn-ninguno" @click="permisosSeleccionados = []">Ninguno</button>
          </div>
          <div class="permisos-grid">
            <div v-for="(permisosCat, cat) in permisosAgrupados" :key="cat" class="permiso-categoria">
              <label class="categoria-label">
                <input type="checkbox" :checked="categoriaCompleta(permisosCat)"
                  @change="toggleCategoria(permisosCat)" class="check-cat"/>
                <span class="categoria-nombre">{{ cat }}</span>
              </label>
              <div class="permiso-items">
                <label v-for="p in permisosCat" :key="p.codigo" class="permiso-item">
                  <input type="checkbox" :value="p.codigo" v-model="permisosSeleccionados" class="check-item"/>
                  <span>{{ p.nombre }}</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <p v-if="errores.non_field_errors" class="field-error">{{ errores.non_field_errors[0] }}</p>

        <div class="form-actions">
          <button type="button" class="btn-secondary" @click="router.push('/usuarios')" :disabled="guardando">
            Cancelar
          </button>
          <button type="submit" class="btn-primary" :disabled="guardando">
            <span v-if="guardando" class="spinner-inline"/>
            {{ guardando ? 'Guardando...' : 'Guardar Cambios' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }
.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; max-width: 720px; }
.breadcrumb { margin-bottom: 1.5rem; }
.btn-back {
  display: inline-flex; align-items: center; gap: 0.375rem;
  font-size: 0.875rem; font-weight: 500; color: #6B7280;
  background: none; border: none; cursor: pointer; padding: 0;
  font-family: inherit; transition: color 0.15s;
}
.btn-back:hover { color: #4F46E5; }
.btn-back svg { width: 16px; height: 16px; }
.page-title   { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0 0 1.75rem; }
.loading { display: flex; align-items: center; gap: 0.75rem; color: #6B7280; font-size: 0.875rem; padding: 2rem 0; }
.spinner { width: 22px; height: 22px; border: 2.5px solid #E5E7EB; border-top-color: #7C3AED; border-radius: 50%; animation: spin 0.7s linear infinite; }
.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; padding: 1.75rem; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
.alert-error { background: #FEF2F2; border: 1px solid #FECACA; color: #DC2626; padding: 0.75rem 1rem; border-radius: 10px; font-size: 0.875rem; margin-bottom: 1.5rem; }
.form { display: flex; flex-direction: column; gap: 1.25rem; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }
.form-group { display: flex; flex-direction: column; gap: 0.375rem; }
.label { font-size: 0.875rem; font-weight: 600; color: #374151; }
.input {
  padding: 0.65rem 0.875rem; border: 1.5px solid #D1D5DB; border-radius: 10px;
  font-size: 0.875rem; color: #111827; background: #fff; outline: none;
  transition: border-color 0.15s, box-shadow 0.15s; font-family: inherit; width: 100%;
}
.input:focus { border-color: #7C3AED; box-shadow: 0 0 0 3px rgba(124,58,237,0.1); }
.input.input-error { border-color: #EF4444; }
.select { cursor: pointer; }
.field-error { font-size: 0.8125rem; color: #EF4444; margin: 0; }
.form-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 0.5rem; }
.btn-secondary {
  padding: 0.6rem 1.25rem; background: #fff; border: 1.5px solid #D1D5DB;
  border-radius: 10px; font-size: 0.875rem; font-weight: 600; color: #374151;
  cursor: pointer; font-family: inherit; transition: border-color 0.15s;
}
.btn-secondary:hover { border-color: #9CA3AF; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary {
  display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem;
  background: linear-gradient(135deg, #4F46E5, #7C3AED); color: #fff;
  font-size: 0.875rem; font-weight: 600; border: none; border-radius: 10px;
  cursor: pointer; transition: opacity 0.2s; font-family: inherit;
}
.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.spinner-inline { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.35); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.permisos-seccion { border: 1.5px solid #E5E7EB; border-radius: 12px; padding: 1rem 1.25rem; background: #FAFAFA; }
.permisos-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; }
.permisos-header .label { flex: 1; margin: 0; }
.btn-todos {
  font-size: 0.75rem; font-weight: 600; padding: 0.25rem 0.625rem;
  border: 1.5px solid #7C3AED; border-radius: 6px; color: #7C3AED;
  background: #fff; cursor: pointer; font-family: inherit; transition: background 0.15s;
}
.btn-todos:hover { background: #EDE9FE; }
.btn-ninguno { border-color: #9CA3AF; color: #6B7280; }
.btn-ninguno:hover { background: #F3F4F6; }
.permisos-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 1rem; }
.permiso-categoria { background: #fff; border: 1px solid #E5E7EB; border-radius: 10px; padding: 0.75rem 1rem; }
.categoria-label { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; margin-bottom: 0.5rem; }
.categoria-nombre { font-size: 0.8rem; font-weight: 700; color: #374151; text-transform: capitalize; }
.check-cat { accent-color: #7C3AED; width: 14px; height: 14px; cursor: pointer; }
.permiso-items { display: flex; flex-direction: column; gap: 0.35rem; padding-left: 0.25rem; }
.permiso-item { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; }
.permiso-item span { font-size: 0.8125rem; color: #4B5563; }
.check-item { accent-color: #7C3AED; width: 13px; height: 13px; cursor: pointer; }
</style>
