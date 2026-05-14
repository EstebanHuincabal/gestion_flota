<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../../utils/api.js'
import ConfirmModal from '../../components/ConfirmModal.vue'
import { useToast } from '../../utils/useToast.js'

const router = useRouter()
const empresas = ref([])
const cargando = ref(true)
const error = ref('')

const toast = useToast()
const confirm = ref({ visible: false, empresa: null, accion: 'desactivar' })

const cargarEmpresas = async () => {
  cargando.value = true
  error.value = ''
  try {
    const res = await apiFetch('/api/empresas/')
    if (!res.ok) throw new Error('Error al cargar empresas')
    empresas.value = await res.json()
  } catch (e) {
    error.value = e.message
  } finally {
    cargando.value = false
  }
}

const pedirConfirmacion = (empresa, accion) => {
  confirm.value = { visible: true, empresa, accion }
}

const cancelarConfirmacion = () => {
  confirm.value = { visible: false, empresa: null, accion: 'desactivar' }
}

const confirmarAccion = async () => {
  const { empresa, accion } = confirm.value
  cancelarConfirmacion()
  try {
    if (accion === 'desactivar') {
      const res = await apiFetch(`/api/empresas/${empresa.id}/`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Error al desactivar la empresa')
      toast.agregar(`"${empresa.nombre}" fue desactivada.`, 'success')
    } else {
      const res = await apiFetch(`/api/empresas/${empresa.id}/`, {
        method: 'PUT',
        body: { estado: 'activa' },
      })
      if (!res.ok) throw new Error('Error al activar la empresa')
      toast.agregar(`"${empresa.nombre}" fue activada.`, 'success')
    }
    await cargarEmpresas()
  } catch (e) {
    toast.agregar(e.message, 'error')
  }
}

onMounted(cargarEmpresas)
</script>

<template>

  <ConfirmModal
    v-if="confirm.visible"
    :titulo="confirm.accion === 'desactivar' ? 'Desactivar empresa' : 'Activar empresa'"
    :mensaje="confirm.accion === 'desactivar'
      ? `¿Desactivar &quot;${confirm.empresa?.nombre}&quot;? Dejará de aparecer como activa en el sistema.`
      : `¿Activar &quot;${confirm.empresa?.nombre}&quot;? Volverá a estar disponible en el sistema.`"
    :label-ok="confirm.accion === 'desactivar' ? 'Desactivar' : 'Activar'"
    :peligroso="confirm.accion === 'desactivar'"
    @confirmar="confirmarAccion"
    @cancelar="cancelarConfirmacion"
  />

  <div class="page">
    <!-- Encabezado -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Empresas</h1>
        <p class="page-subtitle">Administra las empresas registradas en el sistema</p>
      </div>
      <button class="btn-primary" @click="router.push('/empresas/nueva')">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        Nueva Empresa
      </button>
    </div>

    <!-- Error -->
    <div v-if="error" class="alert-error">{{ error }}</div>

    <!-- Cargando -->
    <div v-if="cargando" class="loading">
      <div class="spinner"/>
      <span>Cargando empresas...</span>
    </div>

    <!-- Tabla -->
    <div v-else class="card">
      <table class="tabla">
        <thead>
          <tr>
            <th>Nombre</th>
            <th>RUT</th>
            <th>Flotas / Vehículos</th>
            <th>Conductores</th>
            <th>Última Actividad</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="empresas.length === 0">
            <td colspan="7" class="empty-row">No hay empresas registradas.</td>
          </tr>
          <tr v-for="e in empresas" :key="e.id" :class="{ inactiva: e.estado !== 'activa' }">
            <td class="td-nombre">{{ e.nombre }}</td>
            <td class="td-mono">{{ e.rut }}</td>
            <td class="td-metrics">
              <span class="metric" title="Flotas">{{ e.cantidad_flotas || 0 }}</span> / 
              <span class="metric" title="Vehículos">{{ e.cantidad_vehiculos || 0 }}</span>
            </td>
            <td class="td-metrics">
              <span class="metric" title="Conductores">{{ e.cantidad_conductores || 0 }}</span>
            </td>
            <td class="td-fecha">
              {{ e.ultima_actividad ? new Date(e.ultima_actividad).toLocaleDateString('es-CL') : 'Sin registro' }}
            </td>
            <td>
              <span :class="['badge', e.estado === 'activa' ? 'badge-activa' : 'badge-inactiva']">
                {{ e.estado === 'activa' ? 'Activa' : 'Suspendida' }}
              </span>
            </td>
            <td class="td-acciones">
              <button class="btn-accion btn-detalle" @click="router.push(`/empresas/${e.id}`)" title="Ver Detalle">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                    d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </button>
              <button class="btn-accion btn-editar" @click="router.push(`/empresas/${e.id}/editar`)" title="Editar">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                </svg>
              </button>
              <button
                v-if="e.estado === 'activa'"
                class="btn-accion btn-desactivar"
                @click="pedirConfirmacion(e, 'desactivar')"
                title="Desactivar"
              >
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                    d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/>
                </svg>
              </button>
              <button
                v-else
                class="btn-accion btn-activar"
                @click="pedirConfirmacion(e, 'activar')"
                title="Activar"
              >
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
  </div>
</template>

<style scoped>
*{ box-sizing: border-box; }

.page {
  padding: 2rem 2.5rem;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 1.75rem;
  gap: 1rem;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1E1B4B;
  margin: 0 0 0.25rem;
}

.page-subtitle {
  font-size: 0.875rem;
  color: #6B7280;
  margin: 0;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 1.25rem;
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  color: #fff;
  font-size: 0.875rem;
  font-weight: 600;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.1s;
  font-family: inherit;
  white-space: nowrap;
}
.btn-primary:hover { opacity: 0.9; transform: translateY(-1px); }
.btn-primary svg { width: 16px; height: 16px; }

.alert-error {
  background: #FEF2F2;
  border: 1px solid #FECACA;
  color: #DC2626;
  padding: 0.75rem 1rem;
  border-radius: 10px;
  font-size: 0.875rem;
  margin-bottom: 1.5rem;
}

.loading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: #6B7280;
  font-size: 0.875rem;
  padding: 2rem 0;
}
.spinner {
  width: 22px; height: 22px;
  border: 2.5px solid #E5E7EB;
  border-top-color: #7C3AED;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.card {
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

.tabla {
  width: 100%;
  border-collapse: collapse;
}
.tabla thead {
  background: #F9FAFB;
  border-bottom: 1px solid #E5E7EB;
}
.tabla th {
  padding: 0.75rem 1.25rem;
  text-align: left;
  font-size: 0.75rem;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.tabla td {
  padding: 0.875rem 1.25rem;
  font-size: 0.875rem;
  color: #374151;
  border-bottom: 1px solid #F3F4F6;
}
.tabla tr:last-child td { border-bottom: none; }
.tabla tr.inactiva td { opacity: 0.5; }

.td-nombre { font-weight: 600; color: #111827; }
.td-mono { font-family: 'Courier New', monospace; font-size: 0.8125rem; }
.td-fecha { color: #9CA3AF; font-size: 0.8125rem; }
.td-metrics { font-size: 0.8125rem; color: #6B7280; }
.metric { font-weight: 600; color: #111827; font-size: 0.875rem; }

.empty-row {
  text-align: center;
  color: #9CA3AF;
  padding: 3rem !important;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.625rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}
.badge-activa { background: #ECFDF5; color: #059669; }
.badge-inactiva { background: #F3F4F6; color: #9CA3AF; }

.td-acciones { display: flex; gap: 0.5rem; align-items: center; }

.btn-accion {
  width: 32px; height: 32px;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  background: #fff;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.btn-accion svg { width: 15px; height: 15px; }

.btn-detalle { color: #64748B; }
.btn-detalle:hover { border-color: #64748B; background: #F8FAFC; color: #334155; }

.btn-editar { color: #4F46E5; }
.btn-editar:hover { border-color: #4F46E5; background: #EEF2FF; }

.btn-desactivar { color: #DC2626; }
.btn-desactivar:hover { border-color: #DC2626; background: #FEF2F2; }

.btn-activar { color: #059669; }
.btn-activar:hover { border-color: #059669; background: #ECFDF5; }
</style>
