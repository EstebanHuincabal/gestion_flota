<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../../utils/api.js'
import ConfirmModal from '../../components/ConfirmModal.vue'
import { useToast } from '../../utils/useToast.js'
const router = useRouter()
const usuarios = ref([])
const empresas = ref([])
const cargando = ref(true)
const error    = ref('')
const toast = useToast()
const confirm      = ref({ visible: false, usuario: null, accion: 'desactivar' })
const confirmReset = ref({ visible: false, usuario: null })
const claveModal   = ref({ visible: false, usuario: null, clave: '', copiada: false })

const filtros = ref({ q: '', empresa_id: '', rol: '', estado: '' })
const historialModal = ref({ visible: false, items: [], usuario: null })

const yo = computed(() => JSON.parse(localStorage.getItem('usuario') || '{}'))

const ROL_LABEL = { SUPERADMIN: 'Super Admin', ADMIN: 'Administrador', CONDUCTOR: 'Conductor' }
const ROL_CLASS = { SUPERADMIN: 'badge-superadmin', ADMIN: 'badge-admin', CONDUCTOR: 'badge-conductor' }

const cargarEmpresas = async () => {
  if (yo.value.rol !== 'SUPERADMIN') return
  try {
    const res = await apiFetch('/api/empresas/')
    if (res.ok) empresas.value = await res.json()
  } catch (e) {}
}

const cargar = async () => {
  cargando.value = true
  error.value = ''
  try {
    const params = new URLSearchParams()
    if (filtros.value.q) params.append('q', filtros.value.q)
    if (filtros.value.empresa_id) params.append('empresa_id', filtros.value.empresa_id)
    if (filtros.value.rol) params.append('rol', filtros.value.rol)
    if (filtros.value.estado) params.append('estado', filtros.value.estado)

    const res = await apiFetch(`/api/usuarios/?${params.toString()}`)
    if (!res.ok) throw new Error('Error al cargar usuarios')
    usuarios.value = await res.json()
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

const resetPassword = (u) => {
  confirmReset.value = { visible: true, usuario: u }
}

const confirmarReset = async () => {
  const u = confirmReset.value.usuario
  confirmReset.value = { visible: false, usuario: null }
  try {
    const res = await apiFetch(`/api/usuarios/${u.id}/reset-password/`, { method: 'POST' })
    if (!res.ok) throw new Error('Error al resetear clave')
    const data = await res.json()
    // Mostrar modal con la clave para que el admin pueda copiarla
    claveModal.value = { visible: true, usuario: u, clave: data.clave_temp, copiada: false }
    if (!data.email_enviado) toast.agregar(data.message, 'warning')
  } catch (e) {
    toast.agregar(e.message, 'error')
  }
}

const copiarClave = async () => {
  try {
    await navigator.clipboard.writeText(claveModal.value.clave)
    claveModal.value.copiada = true
    setTimeout(() => { claveModal.value.copiada = false }, 2000)
  } catch {
    toast.agregar('No se pudo copiar. Selecciona el texto manualmente.', 'warning')
  }
}

const toggleBlock = async (u) => {
  try {
    const res = await apiFetch(`/api/usuarios/${u.id}/toggle-block/`, { method: 'POST' })
    if (!res.ok) throw new Error('Error al cambiar bloqueo')
    const data = await res.json()
    toast.agregar(data.message, 'success')
    await cargar()
  } catch (e) {
    toast.agregar(e.message, 'error')
  }
}

const verHistorial = async (u) => {
  historialModal.value.usuario = u
  historialModal.value.visible = true
  historialModal.value.items = []
  try {
    const res = await apiFetch(`/api/usuarios/${u.id}/historial/`)
    if (res.ok) historialModal.value.items = await res.json()
  } catch (e) {}
}

const pedirConfirmacion = (usuario, accion) => {
  confirm.value = { visible: true, usuario, accion }
}

const cancelar = () => {
  confirm.value = { visible: false, usuario: null, accion: 'desactivar' }
}

const confirmarAccion = async () => {
  const { usuario, accion } = confirm.value
  cancelar()
  try {
    if (accion === 'desactivar') {
      const res = await apiFetch(`/api/usuarios/${usuario.id}/`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Error al desactivar')
      toast.agregar(`"${usuario.nombre}" fue desactivado.`, 'success')
    } else {
      const res = await apiFetch(`/api/usuarios/${usuario.id}/`, {
        method: 'PUT',
        body: { is_active: true },
      })
      if (!res.ok) throw new Error('Error al activar')
      toast.agregar(`"${usuario.nombre}" fue activado.`, 'success')
    }
    await cargar()
  } catch (e) {
    toast.agregar(e.message, 'error')
  }
}

// Recargar la lista cuando llegue una notificación de seguridad por WS
// (ej: usuario bloqueado automáticamente por intentos fallidos)
const onWsNotificacion = (e) => {
  if (e.detail?.tipo === 'seguridad') cargar()
}

onMounted(() => {
  cargar()
  cargarEmpresas()
  window.addEventListener('ws:notificacion', onWsNotificacion)
})

onUnmounted(() => {
  window.removeEventListener('ws:notificacion', onWsNotificacion)
})
</script>

<template>

  <ConfirmModal
    v-if="confirm.visible"
    :titulo="confirm.accion === 'desactivar' ? 'Desactivar usuario' : 'Activar usuario'"
    :mensaje="confirm.accion === 'desactivar'
      ? `¿Desactivar a &quot;${confirm.usuario?.nombre}&quot;? No podrá iniciar sesión.`
      : `¿Activar a &quot;${confirm.usuario?.nombre}&quot;? Recuperará acceso al sistema.`"
    :label-ok="confirm.accion === 'desactivar' ? 'Desactivar' : 'Activar'"
    :peligroso="confirm.accion === 'desactivar'"
    @confirmar="confirmarAccion"
    @cancelar="cancelar"
  />

  <ConfirmModal
    v-if="confirmReset.visible"
    titulo="Restablecer contraseña"
    :mensaje="`Se generará una contraseña temporal y se enviará al correo de &quot;${confirmReset.usuario?.nombre}&quot; (${confirmReset.usuario?.email || 'sin email registrado'}).`"
    label-ok="Restablecer"
    :peligroso="false"
    @confirmar="confirmarReset"
    @cancelar="confirmReset.visible = false"
  />

  <!-- Modal contraseña temporal -->
  <Teleport to="body">
    <div v-if="claveModal.visible" class="clave-overlay" @click.self="claveModal.visible = false">
      <div class="clave-modal">
        <div class="clave-icon">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
              d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/>
          </svg>
        </div>
        <h3 class="clave-titulo">Contraseña restablecida</h3>
        <p class="clave-desc">
          Contraseña temporal para <strong>{{ claveModal.usuario?.nombre }}</strong>:
        </p>
        <div class="clave-box">
          <span class="clave-texto">{{ claveModal.clave }}</span>
        </div>
        <p class="clave-hint">Sin espacios, respeta mayúsculas y minúsculas</p>
        <div class="clave-acciones">
          <button class="btn-copiar" @click="copiarClave">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:15px;height:15px;margin-right:6px">
              <path v-if="claveModal.copiada" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
              <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
            </svg>
            {{ claveModal.copiada ? '¡Copiada!' : 'Copiar clave' }}
          </button>
          <button class="btn-cerrar-clave" @click="claveModal.visible = false">Cerrar</button>
        </div>
        <p v-if="claveModal.usuario?.email" class="clave-email-hint">
          También se envió al correo: {{ claveModal.usuario.email }}
        </p>
      </div>
    </div>
  </Teleport>

  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Usuarios</h1>
        <p class="page-subtitle">Gestiona los usuarios del sistema</p>
      </div>
      <button class="btn-primary" @click="router.push('/usuarios/nuevo')">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        Nuevo Usuario
      </button>
    </div>

    <!-- Barra de Filtros -->
    <div class="filters-card card mb-6 p-5 flex flex-wrap gap-4 items-end">
      <div class="flex-1 min-w-[240px]">
        <label class="block text-xs font-bold text-gray-400 uppercase mb-1.5 tracking-wider">Búsqueda rápida</label>
        <div class="relative">
          <input v-model="filtros.q" @input="cargar" type="text" placeholder="Nombre, email o RUT..." class="filter-input w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition-all">
          <svg class="absolute left-3 top-2.5 h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
        </div>
      </div>
      
      <div v-if="yo.rol === 'SUPERADMIN'" class="w-52">
        <label class="block text-xs font-bold text-gray-400 uppercase mb-1.5 tracking-wider">Empresa</label>
        <select v-model="filtros.empresa_id" @change="cargar" class="filter-input w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition-all">
          <option value="">Todas las empresas</option>
          <option v-for="e in empresas" :key="e.id" :value="e.id">{{ e.nombre }}</option>
        </select>
      </div>

      <div class="w-44">
        <label class="block text-xs font-bold text-gray-400 uppercase mb-1.5 tracking-wider">Rol</label>
        <select v-model="filtros.rol" @change="cargar" class="filter-input w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition-all">
          <option value="">Todos los roles</option>
          <option value="ADMIN">Administrador</option>
          <option value="CONDUCTOR">Conductor</option>
        </select>
      </div>

      <div class="w-44">
        <label class="block text-xs font-bold text-gray-400 uppercase mb-1.5 tracking-wider">Estado de cuenta</label>
        <select v-model="filtros.estado" @change="cargar" class="filter-input w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition-all">
          <option value="">Todos los estados</option>
          <option value="activo">Solo Activos</option>
          <option value="bloqueado">Solo Bloqueados</option>
        </select>
      </div>

      <button @click="filtros = { q: '', empresa_id: '', rol: '', estado: '' }; cargar()" class="px-4 py-2 text-sm font-medium text-gray-500 hover:text-indigo-600 transition-colors">
        Limpiar
      </button>
    </div>

    <div v-if="error" class="alert-error">{{ error }}</div>

    <div v-if="cargando" class="loading">
      <div class="spinner"/>
      <span>Cargando usuarios...</span>
    </div>

    <div v-else class="card overflow-hidden">
      <table class="tabla">
        <thead>
          <tr>
            <th>Nombre</th>
            <th>Email</th>
            <th>RUT</th>
            <th>Rol</th>
            <th>Empresa</th>
            <th>Estado</th>
            <th class="text-right">Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="usuarios.length === 0">
            <td colspan="7" class="empty-row">No hay usuarios registrados que coincidan con los filtros.</td>
          </tr>
          <tr v-for="u in usuarios" :key="u.id" :class="{ inactivo: !u.is_active || u.is_blocked }">
            <td class="td-nombre">
              <div class="flex items-center gap-2">
                {{ u.nombre }}
                <span v-if="u.is_blocked" title="Usuario bloqueado por intentos fallidos" class="text-red-500">
                  <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd"/></svg>
                </span>
              </div>
            </td>
            <td class="td-email">{{ u.email }}</td>
            <td class="td-mono">{{ u.rut }}</td>
            <td>
              <span :class="['badge', ROL_CLASS[u.rol] || 'badge-default']">
                {{ ROL_LABEL[u.rol] || u.rol }}
              </span>
            </td>
            <td class="td-empresa">{{ u.empresa || '—' }}</td>
            <td>
              <div class="flex flex-col gap-1">
                <span :class="['badge', u.is_active ? 'badge-activo' : 'badge-inactivo']">
                  {{ u.is_active ? 'Activo' : 'Inactivo' }}
                </span>
                <span v-if="u.is_blocked" class="text-[10px] font-bold text-red-600 uppercase tracking-tighter">Bloqueado</span>
              </div>
            </td>
            <td class="td-acciones">
              <button class="btn-accion btn-historial" @click="verHistorial(u)" title="Ver Historial de Acceso">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
              </button>
              <button class="btn-accion btn-reset" @click="resetPassword(u)" title="Enviar contraseña temporal por correo">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/></svg>
              </button>
              <button v-if="yo.rol === 'SUPERADMIN' && u.rol !== 'SUPERADMIN'" 
                :class="['btn-accion', u.is_blocked ? 'btn-unblock' : 'btn-block']"
                @click="toggleBlock(u)" 
                :title="u.is_blocked ? 'Desbloquear Usuario' : 'Bloquear Usuario'"
              >
                <svg v-if="u.is_blocked" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z"/></svg>
                <svg v-else fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
              </button>
              <button class="btn-accion btn-editar" @click="router.push(`/usuarios/${u.id}/editar`)" title="Editar">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                </svg>
              </button>
              <button v-if="u.is_active" class="btn-accion btn-desactivar"
                @click="pedirConfirmacion(u, 'desactivar')" title="Desactivar">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                    d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/>
                </svg>
              </button>
              <button v-else class="btn-accion btn-activar"
                @click="pedirConfirmacion(u, 'activar')" title="Activar">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal Historial -->
    <div v-if="historialModal.visible" class="modal-overlay" @click.self="historialModal.visible = false">
      <div class="modal-content max-w-2xl w-full">
        <div class="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50 rounded-t-2xl">
          <div>
            <h2 class="text-xl font-bold text-gray-900">Historial de Acceso</h2>
            <p class="text-sm text-gray-500">{{ historialModal.usuario?.nombre }} ({{ historialModal.usuario?.email }})</p>
          </div>
          <button @click="historialModal.visible = false" class="text-gray-400 hover:text-gray-600">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
        
        <div class="p-6 max-h-[60vh] overflow-y-auto">
          <table v-if="historialModal.items.length > 0" class="w-full text-sm">
            <thead>
              <tr class="text-left text-gray-400 uppercase text-[10px] tracking-widest border-b border-gray-100 pb-2">
                <th class="pb-3 font-semibold">Fecha y Hora</th>
                <th class="pb-3 font-semibold">Resultado</th>
                <th class="pb-3 font-semibold">Dirección IP</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50">
              <tr v-for="(h, idx) in historialModal.items" :key="idx" class="hover:bg-gray-50 transition-colors">
                <td class="py-3 text-gray-600">{{ new Date(h.fecha).toLocaleString('es-CL') }}</td>
                <td class="py-3">
                  <span :class="['px-2 py-0.5 rounded-full text-[10px] font-bold uppercase', h.exito ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700']">
                    {{ h.exito ? 'Exitoso' : 'Fallido' }}
                  </span>
                </td>
                <td class="py-3 text-gray-400 font-mono text-xs">{{ h.ip || '—' }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="text-center py-12 text-gray-500">
            No hay registros de acceso para este usuario.
          </div>
        </div>

        <div class="p-4 border-t border-gray-100 flex justify-end">
          <button @click="historialModal.visible = false" class="px-6 py-2 bg-gray-900 text-white rounded-lg text-sm font-semibold hover:bg-gray-800 transition">Cerrar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }

.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; }

.page-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  margin-bottom: 1.75rem; gap: 1rem;
}
.page-title  { font-size: 1.5rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }

/* Filtros */
.filter-input { transition: all 0.2s; background-color: #F9FAFB; }
.filter-input:focus { background-color: #fff; border-color: #6366F1; box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1); }

.btn-primary {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.6rem 1.25rem;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff; font-size: 0.875rem; font-weight: 600;
  border: none; border-radius: 10px; cursor: pointer;
  transition: opacity 0.2s, transform 0.1s; font-family: inherit; white-space: nowrap;
}
.btn-primary:hover { opacity: 0.9; transform: translateY(-1px); }
.btn-primary svg { width: 16px; height: 16px; }

.alert-error {
  background: #FEF2F2; border: 1px solid #FECACA; color: #DC2626;
  padding: 0.75rem 1rem; border-radius: 10px; font-size: 0.875rem; margin-bottom: 1.5rem;
}

.loading { display: flex; align-items: center; gap: 0.75rem; color: #6B7280; font-size: 0.875rem; padding: 2rem 0; }
.spinner {
  width: 22px; height: 22px; border: 2.5px solid #E5E7EB;
  border-top-color: #7C3AED; border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }

.tabla { width: 100%; border-collapse: collapse; }
.tabla thead { background: #F9FAFB; border-bottom: 1px solid #E5E7EB; }
.tabla th {
  padding: 0.75rem 1.1rem; text-align: left;
  font-size: 0.75rem; font-weight: 600; color: #6B7280;
  text-transform: uppercase; letter-spacing: 0.05em;
}
.tabla td { padding: 0.85rem 1.1rem; font-size: 0.875rem; color: #374151; border-bottom: 1px solid #F3F4F6; }
.tabla tr:last-child td { border-bottom: none; }
.tabla tr.inactivo td { opacity: 0.45; }

.td-nombre { font-weight: 600; color: #111827; }
.td-email  { color: #6B7280; font-size: 0.8125rem; }
.td-mono   { font-family: 'Courier New', monospace; font-size: 0.8125rem; }
.td-empresa { color: #6B7280; }

.empty-row { text-align: center; color: #9CA3AF; padding: 3rem !important; }

.badge {
  display: inline-flex; align-items: center;
  padding: 0.2rem 0.625rem; border-radius: 999px;
  font-size: 0.75rem; font-weight: 600;
}
.badge-superadmin { background: #EDE9FE; color: #5B21B6; }
.badge-admin      { background: #EEF2FF; color: #4338CA; }
.badge-conductor  { background: #F0FDF4; color: #15803D; }
.badge-activo     { background: #ECFDF5; color: #059669; }
.badge-inactivo   { background: #F3F4F6; color: #9CA3AF; }
.badge-default    { background: #F3F4F6; color: #6B7280; }

.td-acciones { display: flex; gap: 0.4rem; align-items: center; justify-content: flex-end; }
.btn-accion {
  width: 32px; height: 32px; border: 1px solid #E5E7EB; border-radius: 8px;
  background: #fff; display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: border-color 0.15s, background 0.15s, color 0.15s;
  color: #94A3B8;
}
.btn-accion svg { width: 16px; height: 16px; }

.btn-historial:hover { border-color: #64748B; color: #475569; background: #F8FAFC; }
.btn-reset:hover { border-color: #F59E0B; color: #D97706; background: #FFFBEB; }
.btn-unblock:hover { border-color: #10B981; color: #059669; background: #ECFDF5; }
.btn-block:hover { border-color: #EF4444; color: #DC2626; background: #FEF2F2; }
.btn-editar     { color: #4F46E5; }
.btn-editar:hover { border-color: #4F46E5; background: #EEF2FF; }
.btn-desactivar { color: #DC2626; }
.btn-desactivar:hover { border-color: #DC2626; background: #FEF2F2; }
.btn-activar    { color: #059669; }
.btn-activar:hover { border-color: #059669; background: #ECFDF5; }

/* Modales */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center;
  z-index: 1000; padding: 1rem;
}
.modal-content {
  background: #fff; border-radius: 20px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  animation: modal-in 0.3s ease-out;
}
@keyframes modal-in { from { transform: scale(0.95); opacity: 0; } to { transform: scale(1); opacity: 1; } }

/* ── Modal contraseña temporal ────────────────────────────── */
.clave-overlay {
  position: fixed; inset: 0; background: rgba(15,23,42,0.45);
  backdrop-filter: blur(4px); display: flex; align-items: center;
  justify-content: center; z-index: 1100; padding: 1rem;
  animation: fade-in 0.15s ease;
}
.clave-modal {
  background: #fff; border-radius: 18px; padding: 2rem;
  width: 100%; max-width: 380px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
  display: flex; flex-direction: column; align-items: center;
  text-align: center; animation: slide-up 0.2s ease;
}
.clave-icon {
  width: 52px; height: 52px; border-radius: 50%;
  background: #EEF2FF; color: #4F46E5;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 1rem;
}
.clave-icon svg { width: 24px; height: 24px; }
.clave-titulo { font-size: 1.0625rem; font-weight: 700; color: #111827; margin: 0 0 0.4rem; }
.clave-desc   { font-size: 0.875rem; color: #6B7280; margin: 0 0 1rem; }
.clave-box {
  background: #F0F4FF; border: 2px dashed #A5B4FC;
  border-radius: 10px; padding: 14px 24px; margin-bottom: 6px; width: 100%;
}
.clave-texto {
  font-family: 'Courier New', Courier, monospace;
  font-size: 1.75rem; font-weight: 700; color: #4F46E5;
  letter-spacing: 0; word-break: break-all;
}
.clave-hint  { font-size: 0.75rem; color: #9CA3AF; margin: 0 0 1.25rem; }
.clave-email-hint { font-size: 0.75rem; color: #9CA3AF; margin: 0.75rem 0 0; }
.clave-acciones { display: flex; gap: 0.75rem; width: 100%; }
.btn-copiar {
  flex: 1; display: flex; align-items: center; justify-content: center;
  padding: 0.65rem 1rem; border-radius: 10px; font-size: 0.875rem;
  font-weight: 600; cursor: pointer; font-family: inherit; border: none;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff; transition: opacity 0.15s;
}
.btn-copiar:hover { opacity: 0.9; }
.btn-cerrar-clave {
  flex: 1; padding: 0.65rem 1rem; border-radius: 10px; font-size: 0.875rem;
  font-weight: 600; cursor: pointer; font-family: inherit;
  background: #F3F4F6; color: #374151; border: 1.5px solid #E5E7EB;
  transition: background 0.15s;
}
.btn-cerrar-clave:hover { background: #E5E7EB; }
@keyframes fade-in  { from { opacity: 0; } to { opacity: 1; } }
@keyframes slide-up { from { opacity: 0; transform: translateY(12px) scale(0.97); } to { opacity: 1; transform: translateY(0) scale(1); } }

@media (max-width: 1024px) {
  .page { padding: 1rem; }
  .page-header { flex-direction: column; align-items: stretch; gap: 0.625rem; }
  .page-title { font-size: 1.25rem; }
  .header-actions { flex-direction: column; align-items: stretch; }
  .btn-primary { justify-content: center; }
  /* Scroll horizontal con thumb visible */
  .tabla-wrap, .tabla-card, .sc-table-wrap, .card, .table-wrap {
    overflow-x: scroll !important;  /* scroll (no auto) → track siempre visible */
    overflow-y: hidden !important;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
    scrollbar-color: #A78BFA #EDE9FE;
  }
  .tabla-wrap::-webkit-scrollbar,
  .tabla-card::-webkit-scrollbar,
  .sc-table-wrap::-webkit-scrollbar,
  .card::-webkit-scrollbar,
  .table-wrap::-webkit-scrollbar { height: 8px; }
  .tabla-wrap::-webkit-scrollbar-track,
  .tabla-card::-webkit-scrollbar-track,
  .sc-table-wrap::-webkit-scrollbar-track,
  .card::-webkit-scrollbar-track,
  .table-wrap::-webkit-scrollbar-track { background: #EDE9FE; border-radius: 999px; }
  .tabla-wrap::-webkit-scrollbar-thumb,
  .tabla-card::-webkit-scrollbar-thumb,
  .sc-table-wrap::-webkit-scrollbar-thumb,
  .card::-webkit-scrollbar-thumb,
  .table-wrap::-webkit-scrollbar-thumb { background: #7C3AED; border-radius: 999px; min-width: 40px; }
  .tabla-wrap::-webkit-scrollbar-thumb:hover,
  .tabla-card::-webkit-scrollbar-thumb:hover,
  .sc-table-wrap::-webkit-scrollbar-thumb:hover,
  .card::-webkit-scrollbar-thumb:hover,
  .table-wrap::-webkit-scrollbar-thumb:hover { background: #6D28D9; }
  .tabla-wrap table, .tabla-card table, .sc-table-wrap table,
  .card table, .table-wrap table,
  .tabla, .table, .tabla-flotas, .tabla-vehiculos { min-width: 520px; }

}
</style>
