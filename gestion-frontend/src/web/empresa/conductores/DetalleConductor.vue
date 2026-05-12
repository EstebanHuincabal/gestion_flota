<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiFetchEmpresa, useEmpresaNav } from '../../../utils/empresaActiva.js'
import { tienePermiso } from '../../../utils/permisos.js'
import AppToast from '../../../components/AppToast.vue'
import ConfirmModal from '../../../components/ConfirmModal.vue'

const route  = useRoute()
const router = useRouter()
const { ruta } = useEmpresaNav()

const conductor = ref(null)
const cargando  = ref(true)
const error     = ref(false)
const toast     = ref(null)

const activeTab = ref('general') // general, documentos, historial
const vehiculos = ref([])
const modalAsignar = ref(false)
const vehiculoSeleccionado = ref(null)
const guardandoAsignacion = ref(false)

const cargarVehiculosLibres = async () => {
  const res = await apiFetchEmpresa('/api/empresa/vehiculos/')
  if (res.ok) {
    const todos = await res.json()
    vehiculos.value = todos.filter(v => v.activo)
  }
}

const cargarDetalle = async () => {
  cargando.value = true
  error.value = false
  try {
    const res = await apiFetchEmpresa(`/api/empresa/conductores/${route.params.id}/`)
    if (res.ok) {
      conductor.value = await res.json()
    } else {
      error.value = true
    }
  } catch (e) {
    error.value = true
  } finally {
    cargando.value = false
  }
}

const alertasDocumentos = computed(() => {
    if (!conductor.value) return []
    const alertas = []
    
    // Revisar documentos del conductor
    if (conductor.value.documentos_conductor) {
        for (const doc of conductor.value.documentos_conductor) {
            if (doc.estado === 'vencido') alertas.push({ tipo: 'error', mensaje: `Documento de conductor vencido: ${doc.tipo_display}` })
            else if (doc.estado === 'por_vencer') alertas.push({ tipo: 'warning', mensaje: `Documento de conductor por vencer: ${doc.tipo_display}` })
        }
    }
    
    // Revisar documentos del vehiculo
    if (conductor.value.vehiculo_detalle?.documentos) {
        for (const doc of conductor.value.vehiculo_detalle.documentos) {
            if (doc.estado === 'vencido') alertas.push({ tipo: 'error', mensaje: `Documento de vehículo vencido: ${doc.tipo_display} (${conductor.value.vehiculo_detalle.patente})` })
            else if (doc.estado === 'por_vencer') alertas.push({ tipo: 'warning', mensaje: `Documento de vehículo por vencer: ${doc.tipo_display} (${conductor.value.vehiculo_detalle.patente})` })
        }
    }
    return alertas
})

// Acciones Rápidas
const irEditar = () => {
    if (!tienePermiso('conductores.editar')) {
        toast.value?.agregar('No tienes permiso para editar.', 'error')
        return
    }
    router.push(ruta(`/conductores/${conductor.value.id}/editar`))
}

const abrirAsignacion = () => {
    if (!tienePermiso('conductores.asignar')) {
        toast.value?.agregar('No tienes permiso para asignar vehículos.', 'error')
        return
    }
    cargarVehiculosLibres()
    vehiculoSeleccionado.value = conductor.value.vehiculo?.id || null
    modalAsignar.value = true
}

const guardarAsignacion = async () => {
  guardandoAsignacion.value = true
  try {
      if (!vehiculoSeleccionado.value) {
        const resDes = await apiFetchEmpresa(`/api/empresa/conductores/${conductor.value.id}/desasignar/`, { method: 'POST' })
        if (resDes.ok) {
            toast.value?.agregar('Vehículo desasignado', 'success')
            await cargarDetalle()
        }
      } else {
        const resAsig = await apiFetchEmpresa(`/api/empresa/conductores/${conductor.value.id}/asignar/`, {
            method: 'POST',
            body: { vehiculo_id: vehiculoSeleccionado.value }
        })
        const data = await resAsig.json()
        if (resAsig.ok) {
            toast.value?.agregar('Vehículo asignado', 'success')
            await cargarDetalle()
        } else {
            toast.value?.agregar(data.error || 'Error al asignar', 'error')
        }
      }
      modalAsignar.value = false
  } finally {
      guardandoAsignacion.value = false
  }
}

const volver = () => {
  router.push(ruta('/conductores'))
}

const estadoClase = (estado) => {
  if (estado === 'vigente' || estado === 'realizada') return 'badge-success'
  if (estado === 'por_vencer' || estado === 'pendiente') return 'badge-warning'
  if (estado === 'vencido') return 'badge-danger'
  return 'badge-secondary'
}

const formatFecha = (fecha) => {
  if (!fecha) return '—'
  const partes = fecha.split('-')
  if (partes.length === 3) return `${partes[2]}/${partes[1]}/${partes[0]}`
  
  try {
      const d = new Date(fecha)
      if (isNaN(d.getTime())) return fecha
      return new Intl.DateTimeFormat('es-CL').format(d)
  } catch {
      return fecha
  }
}

const formatDateTime = (datetime) => {
    if (!datetime) return '—'
    try {
        const d = new Date(datetime)
        if (isNaN(d.getTime())) return datetime
        return new Intl.DateTimeFormat('es-CL', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        }).format(d)
    } catch {
        return datetime
    }
}

onMounted(cargarDetalle)
</script>

<template>
  <div class="page">
    <AppToast ref="toast"/>

    <div class="page-header">
      <div class="title-wrap">
        <button class="btn-back" @click="volver">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
          </svg>
        </button>
        <div>
          <h1 class="page-title">Detalle del Conductor</h1>
          <p class="page-subtitle" v-if="conductor">{{ conductor.nombre }}</p>
        </div>
      </div>
    </div>

    <!-- Alertas de Documentos -->
    <div v-if="alertasDocumentos.length > 0" class="alerts-container">
        <div v-for="(alerta, index) in alertasDocumentos" :key="index" :class="['alert-box', `alert-${alerta.tipo}`]">
            <svg v-if="alerta.tipo === 'error'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
            <svg v-else fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <span>{{ alerta.mensaje }}</span>
        </div>
    </div>

    <div v-if="cargando" class="loading">
      <div class="spinner"/> <span>Cargando información...</span>
    </div>

    <div v-else-if="error || !conductor" class="empty">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
      </svg>
      <p>Error al cargar el conductor o no existe.</p>
      <button class="btn-primary" @click="volver">Volver</button>
    </div>

    <div v-else class="content-wrapper">
      
      <!-- Panel Lateral (Perfil Resumen) -->
      <aside class="sidebar-profile">
        <div class="card profile-card">
          <div class="avatar-lg">{{ (conductor.nombre || 'C')[0].toUpperCase() }}</div>
          <h2 class="profile-name">{{ conductor.nombre }}</h2>
          <p class="profile-role">Conductor en <strong>{{ conductor.empresa_nombre }}</strong></p>
          <span :class="['badge', conductor.is_active ? 'badge-success' : 'badge-danger']">
            {{ conductor.is_active ? 'Activo' : 'Inactivo' }}
          </span>

          <div class="profile-actions mt-4">
              <button class="btn-secondary w-full" @click="irEditar">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" class="icon-sm"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                  Editar Conductor
              </button>
          </div>

          <div class="profile-details">
            <div class="detail-item" v-if="conductor.empresa_admin">
              <span class="detail-label">Admin Empresa</span>
              <span class="detail-value">{{ conductor.empresa_admin.nombre || conductor.empresa_admin.email }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">RUT</span>
              <span class="detail-value mono">{{ conductor.rut || '—' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Email</span>
              <span class="detail-value">{{ conductor.email }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Teléfono</span>
              <span class="detail-value">{{ conductor.telefono || '—' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Licencia</span>
              <span class="detail-value">{{ conductor.licencia || '—' }}</span>
            </div>
          </div>
        </div>

        <!-- Tarjeta de Vehículo Actual -->
        <div class="card vehicle-card">
          <div class="flex-between">
              <h3>Vehículo Asignado</h3>
              <button class="btn-link" @click="abrirAsignacion">{{ conductor.vehiculo_detalle ? 'Cambiar' : 'Asignar' }}</button>
          </div>
          <template v-if="conductor.vehiculo_detalle">
            <div class="vehicle-info">
              <div class="patente-box">{{ conductor.vehiculo_detalle.patente }}</div>
              <p class="vehicle-desc">{{ conductor.vehiculo_detalle.descripcion }}</p>
              <div class="vehicle-meta">
                <span>{{ conductor.vehiculo_detalle.anio }}</span> •
                <span>{{ conductor.vehiculo_detalle.tipo_combustible }}</span> •
                <span>{{ conductor.vehiculo_detalle.km_actuales }} km</span>
              </div>
              <div class="vehicle-meta mt-1" v-if="conductor.vehiculo_detalle.empresa_nombre">
                <span class="detail-label">Empresa propietaria:</span>
                <span class="font-semibold">{{ conductor.vehiculo_detalle.empresa_nombre }}</span>
              </div>
            </div>
            
            <button class="btn-outline-danger w-full mt-4" @click="guardarAsignacion(null)">
                Desasignar Vehículo
            </button>
          </template>
          <template v-else>
            <div class="empty-sm">
               <p>Sin vehículo asignado actualmente</p>
            </div>
          </template>
        </div>
      </aside>

      <!-- Panel Principal (Pestañas) -->
      <main class="main-content">
        <div class="tabs">
          <button :class="['tab-btn', { active: activeTab === 'general' }]" @click="activeTab = 'general'">
            Información General
          </button>
          <button :class="['tab-btn', { active: activeTab === 'documentos' }]" @click="activeTab = 'documentos'">
            Documentos
          </button>
          <button :class="['tab-btn', { active: activeTab === 'historial' }]" @click="activeTab = 'historial'">
            Historial
          </button>
        </div>

        <div class="tab-content card">
          
          <!-- Pestaña: General (puede incluir estadísticas rápidas o más info en el futuro) -->
          <div v-if="activeTab === 'general'" class="tab-pane">
            <h3 class="section-title">Resumen</h3>
            <p class="text-muted">El conductor se encuentra registrado en el sistema. Utiliza las pestañas superiores para ver su documentación y el historial de asignaciones y mantenciones del vehículo asociado.</p>
            
            <div class="stats-grid">
               <div class="stat-box">
                  <span class="stat-label">Documentos Conductor</span>
                  <span class="stat-value">{{ conductor.documentos_conductor?.length || 0 }}</span>
               </div>
               <div class="stat-box" v-if="conductor.vehiculo_detalle">
                  <span class="stat-label">Documentos Vehículo</span>
                  <span class="stat-value">{{ conductor.vehiculo_detalle.documentos?.length || 0 }}</span>
               </div>
               <div class="stat-box">
                  <span class="stat-label">Asignaciones Pasadas</span>
                  <span class="stat-value">{{ conductor.historial_asignaciones?.length || 0 }}</span>
               </div>
            </div>
          </div>

          <!-- Pestaña: Documentos -->
          <div v-if="activeTab === 'documentos'" class="tab-pane">
            <h3 class="section-title">Documentación del Conductor</h3>
            <div class="table-responsive">
              <table class="table" v-if="conductor.documentos_conductor && conductor.documentos_conductor.length">
                <thead>
                  <tr>
                    <th>Tipo</th>
                    <th>Número</th>
                    <th>Vencimiento</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="doc in conductor.documentos_conductor" :key="doc.id">
                    <td>{{ doc.tipo_display }}</td>
                    <td>{{ doc.numero || '—' }}</td>
                    <td>{{ formatFecha(doc.fecha_vencimiento) }}</td>
                    <td><span :class="['badge', estadoClase(doc.estado)]">{{ doc.estado }}</span></td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="text-muted empty-state">No hay documentos registrados para el conductor.</p>
            </div>

            <template v-if="conductor.vehiculo_detalle">
              <h3 class="section-title mt-4">Documentación del Vehículo ({{ conductor.vehiculo_detalle.patente }})</h3>
              <div class="table-responsive">
                <table class="table" v-if="conductor.vehiculo_detalle.documentos && conductor.vehiculo_detalle.documentos.length">
                  <thead>
                    <tr>
                      <th>Tipo</th>
                      <th>Vencimiento</th>
                      <th>Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="doc in conductor.vehiculo_detalle.documentos" :key="doc.id">
                      <td>{{ doc.tipo_display }}</td>
                      <td>{{ formatFecha(doc.fecha_vencimiento) }}</td>
                      <td><span :class="['badge', estadoClase(doc.estado)]">{{ doc.estado }}</span></td>
                    </tr>
                  </tbody>
                </table>
                <p v-else class="text-muted empty-state">No hay documentos registrados para este vehículo.</p>
              </div>
            </template>
          </div>

          <!-- Pestaña: Historial -->
          <div v-if="activeTab === 'historial'" class="tab-pane">
            <h3 class="section-title">Historial de Asignaciones</h3>
            <div class="table-responsive">
              <table class="table" v-if="conductor.historial_asignaciones && conductor.historial_asignaciones.length">
                <thead>
                  <tr>
                    <th>Vehículo</th>
                    <th>Desde</th>
                    <th>Hasta</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="asig in conductor.historial_asignaciones" :key="asig.id">
                    <td><strong>{{ asig.vehiculo_patente }}</strong> <br/> <span class="text-xs text-muted">{{ asig.vehiculo_descripcion }}</span></td>
                    <td>{{ formatDateTime(asig.desde) }}</td>
                    <td>{{ formatDateTime(asig.hasta) }}</td>
                    <td>
                      <span v-if="asig.activo" class="badge badge-success">Actual</span>
                      <span v-else class="badge badge-secondary">Finalizada</span>
                    </td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="text-muted empty-state">No hay historial de asignaciones.</p>
            </div>

            <template v-if="conductor.vehiculo_detalle">
              <h3 class="section-title mt-4">Mantenciones del Vehículo Actual ({{ conductor.vehiculo_detalle.patente }})</h3>
              <div class="table-responsive">
                <table class="table" v-if="conductor.vehiculo_detalle.mantenciones && conductor.vehiculo_detalle.mantenciones.length">
                  <thead>
                    <tr>
                      <th>Tipo</th>
                      <th>Programada</th>
                      <th>Realizada</th>
                      <th>Costo</th>
                      <th>Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="mant in conductor.vehiculo_detalle.mantenciones" :key="mant.id">
                      <td>{{ mant.tipo_mantencion }}</td>
                      <td>{{ formatFecha(mant.fecha_programada) }}</td>
                      <td>{{ formatFecha(mant.fecha_realizada) }}</td>
                      <td>${{ Number(mant.costo).toLocaleString('es-CL') }}</td>
                      <td><span :class="['badge', estadoClase(mant.estado)]">{{ mant.estado }}</span></td>
                    </tr>
                  </tbody>
                </table>
                <p v-else class="text-muted empty-state">No hay mantenciones registradas para este vehículo.</p>
              </div>
            </template>
          </div>

        </div>
      </main>

    </div>

    <!-- Modal asignar vehículo -->
    <Teleport to="body">
      <div v-if="modalAsignar" class="overlay" @click.self="modalAsignar = false">
        <div class="modal">
          <h2 class="modal-title">Asignar vehículo</h2>
          <p class="modal-sub">{{ conductor?.nombre }}</p>

          <div class="form-group">
            <label class="label">Vehículo</label>
            <select v-model="vehiculoSeleccionado" class="input select">
              <option :value="null">— Sin vehículo —</option>
              <option v-for="v in vehiculos" :key="v.id" :value="v.id">
                {{ v.patente }} · {{ v.marca }} {{ v.modelo }}
              </option>
            </select>
          </div>

          <div class="modal-actions">
            <button class="btn-secondary" @click="modalAsignar = false">Cancelar</button>
            <button class="btn-primary" @click="guardarAsignacion">Guardar</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }
.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; background-color: #F9FAFB; min-height: 100vh; }
.page-header { margin-bottom: 2rem; }
.title-wrap { display: flex; align-items: center; gap: 1rem; }
.btn-back { width: 40px; height: 40px; border-radius: 10px; border: 1px solid #E5E7EB; background: #fff; color: #4B5563; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s; }
.btn-back:hover { background: #F3F4F6; color: #111827; }
.btn-back svg { width: 20px; height: 20px; }
.page-title { font-size: 1.75rem; font-weight: 700; color: #111827; margin: 0; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }

.alerts-container { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1.5rem; }
.alert-box { display: flex; align-items: center; gap: 0.75rem; padding: 1rem 1.25rem; border-radius: 12px; font-size: 0.875rem; font-weight: 500; }
.alert-box svg { width: 20px; height: 20px; flex-shrink: 0; }
.alert-error { background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }
.alert-warning { background: #FFFBEB; color: #92400E; border: 1px solid #FDE68A; }

.loading, .empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1rem; padding: 4rem 0; color: #6B7280; }
.empty svg { width: 64px; height: 64px; color: #9CA3AF; }
.spinner { width: 30px; height: 30px; border: 3px solid #E5E7EB; border-top-color: #7C3AED; border-radius: 50%; animation: spin 0.8s linear infinite; }

.content-wrapper { display: flex; gap: 2rem; align-items: flex-start; flex-wrap: wrap; }

/* Sidebar */
.sidebar-profile { width: 320px; display: flex; flex-direction: column; gap: 1.5rem; flex-shrink: 0; }
.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 16px; padding: 1.5rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }

.profile-card { text-align: center; }
.avatar-lg { width: 80px; height: 80px; margin: 0 auto 1rem; border-radius: 50%; background: linear-gradient(135deg, #4F46E5, #7C3AED); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 2rem; font-weight: 700; box-shadow: 0 4px 10px rgba(124,58,237,0.3); }
.profile-name { font-size: 1.25rem; font-weight: 700; margin: 0 0 0.25rem; color: #111827; }
.profile-role { font-size: 0.875rem; color: #6B7280; margin: 0 0 1rem; }
.profile-actions { display: flex; flex-direction: column; gap: 0.5rem; }
.profile-details { margin-top: 1.5rem; text-align: left; display: flex; flex-direction: column; gap: 0.75rem; border-top: 1px solid #F3F4F6; padding-top: 1.5rem; }
.detail-item { display: flex; justify-content: space-between; align-items: center; font-size: 0.875rem; }
.detail-label { color: #6B7280; font-weight: 500; }
.detail-value { color: #111827; font-weight: 600; text-align: right; }
.mono { font-family: monospace; }

.vehicle-card h3 { font-size: 1rem; margin: 0 0 1rem; color: #111827; font-weight: 600; }
.flex-between { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.flex-between h3 { margin: 0; }
.btn-link { background: none; border: none; color: #4F46E5; font-size: 0.8125rem; font-weight: 600; cursor: pointer; padding: 0; text-decoration: underline; }
.btn-link:hover { color: #3730A3; }
.vehicle-info { display: flex; flex-direction: column; gap: 0.5rem; }
.patente-box { align-self: flex-start; background: #FEF08A; color: #854D0E; font-family: monospace; font-size: 1.125rem; font-weight: 700; padding: 0.25rem 0.75rem; border-radius: 6px; border: 2px solid #EAB308; letter-spacing: 2px; }
.vehicle-desc { font-weight: 600; color: #374151; margin: 0; }
.vehicle-meta { font-size: 0.8125rem; color: #6B7280; display: flex; gap: 0.5rem; }

.empty-sm { text-align: center; color: #9CA3AF; font-size: 0.875rem; padding: 1rem 0; font-style: italic; }

/* Main Content */
.main-content { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1.5rem; }

.tabs { display: flex; gap: 0.5rem; border-bottom: 2px solid #E5E7EB; padding-bottom: 0; }
.tab-btn { background: none; border: none; padding: 0.75rem 1.5rem; font-size: 0.95rem; font-weight: 600; color: #6B7280; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; transition: all 0.2s; }
.tab-btn:hover { color: #374151; }
.tab-btn.active { color: #4F46E5; border-bottom-color: #4F46E5; }

.tab-pane { animation: fadeIn 0.3s ease; }
.section-title { font-size: 1.125rem; font-weight: 600; color: #111827; margin: 0 0 1rem; border-bottom: 1px solid #F3F4F6; padding-bottom: 0.5rem; }
.mt-4 { margin-top: 1rem; }
.w-full { width: 100%; justify-content: center; }

.text-muted { color: #6B7280; font-size: 0.875rem; line-height: 1.5; }
.text-xs { font-size: 0.75rem; }
.empty-state { text-align: center; padding: 2rem 0; background: #F9FAFB; border-radius: 8px; border: 1px dashed #D1D5DB; }

/* Stats Grid */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-top: 1.5rem; }
.stat-box { background: #F9FAFB; padding: 1rem; border-radius: 12px; border: 1px solid #F3F4F6; text-align: center; }
.stat-label { display: block; font-size: 0.8125rem; color: #6B7280; font-weight: 600; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em; }
.stat-value { font-size: 1.75rem; font-weight: 800; color: #4F46E5; }

/* Table */
.table-responsive { overflow-x: auto; }
.table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.table th { background: #F9FAFB; padding: 0.75rem 1rem; text-align: left; font-weight: 600; color: #4B5563; border-bottom: 1px solid #E5E7EB; white-space: nowrap; }
.table td { padding: 0.875rem 1rem; border-bottom: 1px solid #F3F4F6; color: #111827; vertical-align: middle; }
.table tr:last-child td { border-bottom: none; }

/* Badges */
.badge { display: inline-flex; align-items: center; padding: 0.25rem 0.625rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge-success { background: #D1FAE5; color: #065F46; }
.badge-danger  { background: #FEE2E2; color: #991B1B; }
.badge-warning { background: #FEF3C7; color: #92400E; }
.badge-secondary { background: #F3F4F6; color: #4B5563; }

.btn-primary { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: linear-gradient(135deg,#4F46E5,#7C3AED); color: #fff; font-size: 0.875rem; font-weight: 600; border: none; border-radius: 10px; cursor: pointer; transition: opacity 0.2s; }
.btn-primary:hover { opacity: 0.9; }

.btn-secondary { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: #fff; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; font-weight: 600; color: #374151; cursor: pointer; font-family: inherit; transition: border-color 0.15s; }
.btn-secondary:hover { border-color: #9CA3AF; }

.btn-outline-danger { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; background: transparent; border: 1.5px solid #FECACA; color: #DC2626; border-radius: 8px; font-size: 0.8125rem; font-weight: 600; cursor: pointer; transition: all 0.2s; }
.btn-outline-danger:hover { background: #FEF2F2; border-color: #F87171; }

.icon-sm { width: 16px; height: 16px; }

/* Modal */
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #fff; border-radius: 16px; padding: 1.75rem; width: 100%; max-width: 420px; box-shadow: 0 20px 60px rgba(0,0,0,0.15); }
.modal-title { font-size: 1.125rem; font-weight: 700; color: #1E1B4B; margin: 0 0 0.25rem; }
.modal-sub   { font-size: 0.875rem; color: #6B7280; margin: 0 0 1.25rem; }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem; }
.form-group { display: flex; flex-direction: column; gap: 0.375rem; }
.label { font-size: 0.875rem; font-weight: 600; color: #374151; }
.input { padding: 0.65rem 0.875rem; border: 1.5px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; color: #111827; background: #fff; outline: none; transition: border-color 0.15s; font-family: inherit; width: 100%; }
.input:focus { border-color: #7C3AED; box-shadow: 0 0 0 3px rgba(124,58,237,0.1); }

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }

@media (max-width: 768px) {
  .content-wrapper { flex-direction: column; }
  .sidebar-profile { width: 100%; }
}
</style>
