<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetchEmpresa, useEmpresaNav, getEmpresaActiva } from '../../../utils/empresaActiva.js'
import { tienePermiso } from '../../../utils/permisos.js'
import AppToast from '../../../components/AppToast.vue'
import ConfirmModal from '../../../components/ConfirmModal.vue'

const router = useRouter()
const { ruta } = useEmpresaNav()
const toast = ref(null)

const activeTab = ref('lista') // lista, calendario
const mantenciones = ref([])
const resumen = ref({ costo_mes: 0, costo_total: 0, pendientes: 0, realizadas: 0 })
const cargando = ref(true)

const empresaActiva = getEmpresaActiva()
const esSuperadmin = JSON.parse(localStorage.getItem('usuario') || '{}').rol === 'SUPERADMIN'
const sinEmpresa = computed(() => esSuperadmin && !empresaActiva)

// Modal Nueva/Editar
const modalVisible = ref(false)
const modo = ref('nuevo')
const vehiculosLibres = ref([])
const form = ref({ id: null, vehiculo_id: null, tipo_mantencion: '', fecha_programada: '', kilometraje_programado: '', estado: 'pendiente', fecha_realizada: '', kilometraje_realizado: '', costo: 0 })
const guardando = ref(false)
const errores = ref({})

// Modal Confirmar
const confirmState = ref({ visible: false, accion: null, mantencion: null })

const cargarDatos = async () => {
    if (sinEmpresa.value) return
    cargando.value = true
    try {
        const [resList, resSum, resVeh] = await Promise.all([
            apiFetchEmpresa('/api/empresa/mantenciones/'),
            apiFetchEmpresa('/api/empresa/mantenciones/resumen/'),
            apiFetchEmpresa('/api/empresa/vehiculos/')
        ])
        if (resList.ok) mantenciones.value = await resList.json()
        if (resSum.ok) resumen.value = await resSum.json()
        if (resVeh.ok) vehiculosLibres.value = (await resVeh.json()).filter(v => v.activo)
    } finally {
        cargando.value = false
    }
}

const abrirNuevo = () => {
    if (!tienePermiso('mantenciones.crear')) { toast.value?.agregar('Sin permisos', 'error'); return }
    modo.value = 'nuevo'
    form.value = { id: null, vehiculo_id: null, tipo_mantencion: '', fecha_programada: '', kilometraje_programado: '', estado: 'pendiente', fecha_realizada: '', kilometraje_realizado: '', costo: 0 }
    errores.value = {}
    modalVisible.value = true
}

const abrirEditar = (m) => {
    if (!tienePermiso('mantenciones.editar')) { toast.value?.agregar('Sin permisos', 'error'); return }
    modo.value = 'editar'
    form.value = { ...m }
    errores.value = {}
    modalVisible.value = true
}

const abrirRealizar = (m) => {
    if (!tienePermiso('mantenciones.editar')) { toast.value?.agregar('Sin permisos', 'error'); return }
    modo.value = 'realizar'
    form.value = { ...m, estado: 'realizada', fecha_realizada: new Date().toISOString().split('T')[0] }
    errores.value = {}
    modalVisible.value = true
}

const confirmarEliminar = (m) => {
    if (!tienePermiso('mantenciones.eliminar')) { toast.value?.agregar('Sin permisos', 'error'); return }
    confirmState.value = { visible: true, accion: 'eliminar', mantencion: m }
}

const guardar = async () => {
    guardando.value = true
    errores.value = {}
    try {
        let payload = { ...form.value }
        if (!payload.kilometraje_programado) payload.kilometraje_programado = null
        if (!payload.fecha_programada) payload.fecha_programada = null
        
        let url = '/api/empresa/mantenciones/'
        let method = 'POST'
        if (modo.value === 'editar' || modo.value === 'realizar') {
            url += `${payload.id}/`
            method = 'PUT'
        }
        
        const res = await apiFetchEmpresa(url, { method, body: payload })
        if (res.ok) {
            toast.value?.agregar(modo.value === 'nuevo' ? 'Mantención programada' : 'Mantención actualizada', 'success')
            modalVisible.value = false
            await cargarDatos()
        } else {
            const data = await res.json()
            if (data.error) toast.value?.agregar(data.error, 'error')
            else errores.value = data
        }
    } finally {
        guardando.value = false
    }
}

const eliminar = async () => {
    const id = confirmState.value.mantencion.id
    confirmState.value.visible = false
    const res = await apiFetchEmpresa(`/api/empresa/mantenciones/${id}/`, { method: 'DELETE' })
    if (res.ok) {
        toast.value?.agregar('Mantención eliminada', 'success')
        await cargarDatos()
    }
}

const formatFecha = (f) => f ? new Date(f).toLocaleDateString('es-CL') : '—'

onMounted(cargarDatos)
</script>

<template>
  <div class="page">
    <AppToast ref="toast"/>
    <ConfirmModal v-if="confirmState.visible" titulo="Eliminar mantención" mensaje="¿Seguro que deseas eliminar este registro?" labelOk="Eliminar" peligroso @confirmar="eliminar" @cancelar="confirmState.visible = false"/>

    <!-- Encabezado -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Mantenciones</h1>
        <p class="page-subtitle">Gestiona el mantenimiento y costos de tu flota</p>
      </div>
      <button class="btn-primary" @click="abrirNuevo" :disabled="sinEmpresa">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
        Programar Mantención
      </button>
    </div>

    <!-- Stats -->
    <div class="stats-grid mb-6" v-if="!sinEmpresa && !cargando">
      <div class="stat-card stat-blue">
        <h3>Pendientes</h3>
        <p class="text-2xl">{{ resumen.pendientes }}</p>
      </div>
      <div class="stat-card stat-green">
        <h3>Realizadas</h3>
        <p class="text-2xl">{{ resumen.realizadas }}</p>
      </div>
      <div class="stat-card stat-yellow">
        <h3>Gasto del Mes</h3>
        <p class="text-xl">${{ Number(resumen.costo_mes).toLocaleString('es-CL') }}</p>
      </div>
      <div class="stat-card stat-purple">
        <h3>Gasto Histórico</h3>
        <p class="text-xl">${{ Number(resumen.costo_total).toLocaleString('es-CL') }}</p>
      </div>
    </div>

    <div v-if="sinEmpresa" class="empty">Selecciona una empresa para gestionar mantenciones.</div>
    <div v-else-if="cargando" class="loading"><div class="spinner"/>Cargando...</div>
    
    <div v-else class="card">
        <table class="table">
            <thead>
                <tr>
                    <th>Vehículo</th>
                    <th>Tipo</th>
                    <th>Programada para</th>
                    <th>Estado</th>
                    <th>Realizada el</th>
                    <th>Presupuesto</th>
                    <th>Acciones</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="m in mantenciones" :key="m.id" :class="{'bg-gray-50': m.estado === 'realizada'}">
                    <td><strong>{{ m.vehiculo_patente }}</strong><br><span class="text-xs text-muted">{{ m.vehiculo_descripcion }}</span></td>
                    <td>{{ m.tipo_mantencion }}</td>
                    <td>
                        {{ formatFecha(m.fecha_programada) }}
                        <span v-if="m.kilometraje_programado" class="text-xs text-muted block">{{ m.kilometraje_programado }} km</span>
                    </td>
                    <td>
                        <span :class="['badge', m.estado === 'realizada' ? 'badge-success' : 'badge-warning']">
                            {{ m.estado }}
                        </span>
                    </td>
                    <td>
                        {{ formatFecha(m.fecha_realizada) }}
                        <span v-if="m.kilometraje_realizado" class="text-xs text-muted block">{{ m.kilometraje_realizado }} km</span>
                    </td>
                    <td>${{ Number(m.costo).toLocaleString('es-CL') }}</td>
                    <td>
                        <div class="acciones">
                            <button v-if="m.estado !== 'realizada'" class="btn-icon success" title="Marcar Realizada" @click="abrirRealizar(m)">
                                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                            </button>
                            <button class="btn-icon" title="Editar" @click="abrirEditar(m)">
                                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                            </button>
                            <button class="btn-icon danger" title="Eliminar" @click="confirmarEliminar(m)">
                                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                            </button>
                        </div>
                    </td>
                </tr>
                <tr v-if="!mantenciones.length"><td colspan="7" class="text-center text-muted py-4">No hay mantenciones registradas.</td></tr>
            </tbody>
        </table>
    </div>

    <!-- Modal Formulario -->
    <Teleport to="body">
      <div v-if="modalVisible" class="overlay" @click.self="modalVisible = false">
        <div class="modal">
          <h2 class="modal-title">{{ modo === 'nuevo' ? 'Programar Mantención' : (modo === 'realizar' ? 'Completar Mantención' : 'Editar Mantención') }}</h2>
          
          <form @submit.prevent="guardar" class="form mt-4">
              <div class="form-group" v-if="modo !== 'realizar'">
                  <label class="label">Vehículo</label>
                  <select v-model="form.vehiculo_id" class="input select" required>
                      <option :value="null">-- Seleccionar --</option>
                      <option v-for="v in vehiculosLibres" :key="v.id" :value="v.id">{{ v.patente }} - {{ v.marca }}</option>
                  </select>
                  <p v-if="errores.vehiculo_id" class="field-error">{{ errores.vehiculo_id[0] }}</p>
              </div>

              <div class="form-group" v-if="modo !== 'realizar'">
                  <label class="label">Tipo de Mantención</label>
                  <input v-model="form.tipo_mantencion" class="input" required placeholder="Ej: Cambio de Aceite, Revisión de 10.000km">
              </div>

              <div class="form-row" v-if="modo !== 'realizar'">
                  <div class="form-group">
                      <label class="label">Fecha Programada</label>
                      <input v-model="form.fecha_programada" type="date" class="input">
                  </div>
              </div>

              <template v-if="modo === 'realizar' || form.estado === 'realizada'">
                  <div class="form-row mt-4">
                      <div class="form-group">
                          <label class="label">Fecha Realizada</label>
                          <input v-model="form.fecha_realizada" type="date" class="input" required>
                      </div>
                  </div>
                  <div class="form-group mt-2">
                      <label class="label">Presupuesto ($)</label>
                      <input v-model="form.costo" type="number" class="input" required min="0">
                  </div>
              </template>

              <div class="modal-actions mt-6">
                  <button type="button" class="btn-secondary" @click="modalVisible = false">Cancelar</button>
                  <button type="submit" class="btn-primary" :disabled="guardando">{{ guardando ? 'Guardando...' : 'Guardar' }}</button>
              </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }
.page { padding: 2rem 2.5rem; font-family: 'Inter', system-ui, sans-serif; background: #F9FAFB; min-height: 100vh;}
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem; }
.page-title { font-size: 1.5rem; font-weight: 700; color: #111827; margin: 0 0 0.25rem; }
.page-subtitle { font-size: 0.875rem; color: #6B7280; margin: 0; }

.mb-6 { margin-bottom: 1.5rem; }
.mt-4 { margin-top: 1rem; }
.mt-6 { margin-top: 1.5rem; }
.text-2xl { font-size: 1.5rem; font-weight: 700; }
.text-xl { font-size: 1.25rem; font-weight: 700; }
.text-xs { font-size: 0.75rem; }
.text-muted { color: #6B7280; }
.block { display: block; }
.py-4 { padding-top: 1rem; padding-bottom: 1rem; }
.text-center { text-align: center; }
.bg-gray-50 { background-color: #F9FAFB; }

.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
.stat-card { padding: 1.25rem; border-radius: 12px; color: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
.stat-card h3 { font-size: 0.875rem; font-weight: 600; opacity: 0.9; margin: 0 0 0.5rem; text-transform: uppercase; letter-spacing: 0.05em; }
.stat-card p { margin: 0; }
.stat-blue { background: linear-gradient(135deg, #3B82F6, #2563EB); }
.stat-green { background: linear-gradient(135deg, #10B981, #059669); }
.stat-yellow { background: linear-gradient(135deg, #F59E0B, #D97706); }
.stat-purple { background: linear-gradient(135deg, #8B5CF6, #6D28D9); }

.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.table th { background: #F9FAFB; padding: 0.875rem 1rem; text-align: left; font-weight: 600; color: #4B5563; border-bottom: 1px solid #E5E7EB; }
.table td { padding: 1rem; border-bottom: 1px solid #F3F4F6; color: #111827; vertical-align: middle; }

.badge { display: inline-flex; padding: 0.25rem 0.625rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge-success { background: #D1FAE5; color: #065F46; }
.badge-warning { background: #FEF3C7; color: #92400E; }

.acciones { display: flex; gap: 0.5rem; }
.btn-icon { width: 32px; height: 32px; border-radius: 8px; border: 1px solid #E5E7EB; background: #fff; color: #6B7280; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s; }
.btn-icon svg { width: 16px; height: 16px; }
.btn-icon:hover { border-color: #4F46E5; color: #4F46E5; }
.btn-icon.danger:hover { border-color: #EF4444; color: #EF4444; background: #FEF2F2; }
.btn-icon.success:hover { border-color: #10B981; color: #10B981; background: #D1FAE5; }

.btn-primary { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: linear-gradient(135deg,#4F46E5,#7C3AED); color: #fff; font-size: 0.875rem; font-weight: 600; border: none; border-radius: 10px; cursor: pointer; transition: opacity 0.2s; }
.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary svg { width: 18px; height: 18px; }
.btn-secondary { padding: 0.6rem 1.25rem; background: #fff; border: 1px solid #D1D5DB; border-radius: 10px; font-size: 0.875rem; font-weight: 600; color: #374151; cursor: pointer; }

/* Modal */
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal { background: #fff; border-radius: 16px; padding: 1.5rem; width: 100%; max-width: 450px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); }
.modal-title { font-size: 1.25rem; font-weight: 700; margin: 0; }
.form-group { display: flex; flex-direction: column; gap: 0.375rem; margin-bottom: 1rem; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
.label { font-size: 0.875rem; font-weight: 600; color: #374151; }
.input { padding: 0.625rem 0.875rem; border: 1px solid #D1D5DB; border-radius: 8px; font-size: 0.875rem; outline: none; }
.input:focus { border-color: #4F46E5; box-shadow: 0 0 0 3px rgba(79,70,229,0.1); }
.modal-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }
.field-error { font-size: 0.75rem; color: #EF4444; margin: 0; }

.loading, .empty { display: flex; flex-direction: column; align-items: center; padding: 4rem; color: #6B7280; }
.spinner { width: 30px; height: 30px; border: 3px solid #E5E7EB; border-top-color: #7C3AED; border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 1rem; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>