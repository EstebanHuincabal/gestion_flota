<script setup>
/**
 * GastosCorrectivos.vue — Gastos correctivos NO presupuestados.
 *
 * Se renderiza como contenido del tab "Correctivos" de FinanzasEmpresa.
 * Recibe el período (mes/año) por props y se autogestiona (carga, modales).
 * Los correctivos nunca se mezclan con el presupuesto normal.
 */
import { ref, computed, watch, onMounted } from 'vue'
import { apiFetchEmpresa, getEmpresaActiva, EMPRESA_TODAS } from '../../utils/empresaActiva.js'
import { useToast } from '../../utils/useToast.js'
import { tienePermiso } from '../../utils/permisos.js'
import ConfirmModal from '../../components/ConfirmModal.vue'
import { usePaginacion } from '../../composables/usePaginacion.js'
import PaginacionTabla from '../../components/PaginacionTabla.vue'
import { useModeracion } from '../../composables/useModeracion.js'
import AvisoModeracion from '../../components/AvisoModeracion.vue'

const props = defineProps({
  mes:  { type: Number, required: true },
  anio: { type: Number, required: true },
})

const toast = useToast()
const { moderar, aviso: avisoMod, sugerencia: sugerenciaMod, limpiar: limpiarMod } = useModeracion()
// Modo "Todas las empresas" (SUPERADMIN): vista de solo lectura agregada. La
// escritura exige una empresa concreta, así que se oculta crear/editar/eliminar.
const esTodas = computed(() => getEmpresaActiva()?.id === EMPRESA_TODAS)
const puedeCrear    = computed(() => tienePermiso('correctivos.crear') && !esTodas.value)
const puedeEditar   = computed(() => tienePermiso('correctivos.editar') && !esTodas.value)
const puedeEliminar = computed(() => tienePermiso('correctivos.eliminar') && !esTodas.value)

// ── Estado ───────────────────────────────────────────────────────────────────
const loading   = ref(false)
const gastos    = ref([])
const resumen   = ref(null)
const vehiculos = ref([])

// Filtros
const filtroVehiculo  = ref('')
const filtroCategoria = ref('')
const filtroPrioridad = ref('')

// ── Catálogos ─────────────────────────────────────────────────────────────────
const CATEGORIAS = [
  { value: 'falla_mecanica',   label: 'Falla mecánica urgente' },
  { value: 'repuesto_urgente', label: 'Repuesto no planificado' },
  { value: 'accidente',        label: 'Daño por accidente' },
  { value: 'electrico',        label: 'Falla eléctrica' },
  { value: 'neumatico',        label: 'Neumático de emergencia' },
  { value: 'otro_correctivo',  label: 'Otro correctivo' },
]
const COLOR_CAT = {
  falla_mecanica:   { bg: '#FEE2E2', text: '#B91C1C' },
  repuesto_urgente: { bg: '#EDE9FE', text: '#6D28D9' },
  accidente:        { bg: '#FCE7E7', text: '#7F1D1D' },
  electrico:        { bg: '#DBEAFE', text: '#1D4ED8' },
  neumatico:        { bg: '#FFEDD5', text: '#C2410C' },
  otro_correctivo:  { bg: '#F3F4F6', text: '#6B7280' },
}
const COLOR_PRIO = {
  alta:  { bg: '#FEE2E2', text: '#B91C1C', label: 'Alta' },
  media: { bg: '#FFEDD5', text: '#C2410C', label: 'Media' },
  baja:  { bg: '#DBEAFE', text: '#1D4ED8', label: 'Baja' },
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function clp(v) { return '$' + Number(v || 0).toLocaleString('es-CL') }
function fmtFecha(iso) {
  if (!iso) return '—'
  return new Date(iso + 'T00:00:00').toLocaleDateString('es-CL', { day: '2-digit', month: '2-digit', year: 'numeric' })
}
function catStyle(c)  { return COLOR_CAT[c]  || COLOR_CAT.otro_correctivo }
function prioStyle(p) { return COLOR_PRIO[p] || { bg: '#F3F4F6', text: '#6B7280', label: p || '—' } }

const impactoPresupuesto = computed(() => {
  const pres = resumen.value?.presupuesto_mensual
  if (!pres?.monto) return null
  const pct = (resumen.value.total_correctivos / pres.monto) * 100
  return Math.round(pct * 10) / 10
})

// Barras de evolución (CSS puro, sin Chart.js).
const maxEvolucion = computed(() => {
  const ev = resumen.value?.evolucion_mensual || []
  return Math.max(1, ...ev.map(m => m.total_correctivo + m.total_normal))
})
function altoBarra(valor, alturaMaxPx = 90) {
  return Math.round((valor / maxEvolucion.value) * alturaMaxPx)
}
// Máximo para las barras "correctivo vs normal" por vehículo.
const maxVehiculo = computed(() => {
  const pv = resumen.value?.por_vehiculo || []
  return Math.max(1, ...pv.flatMap(v => [v.total_correctivo, v.total_normal]))
})

const { pagina: paginaGastos, totalPaginas: totalPaginasGastos, total: totalGastos, paginado: gastosPaginados, irA: irAPaginaGastos } = usePaginacion(gastos, 15)

// ── Carga ───────────────────────────────────────────────────────────────────────
async function cargar() {
  loading.value = true
  try {
    let url = `/api/empresa/gastos/correctivos/?mes=${props.mes}&anio=${props.anio}`
    if (filtroVehiculo.value)  url += `&vehiculo_id=${filtroVehiculo.value}`
    if (filtroCategoria.value) url += `&categoria_correctiva=${filtroCategoria.value}`
    if (filtroPrioridad.value) url += `&prioridad=${filtroPrioridad.value}`
    const res = await apiFetchEmpresa(url)
    if (res.ok) {
      const d = await res.json()
      gastos.value  = d.gastos
      resumen.value = d.resumen
    } else {
      toast.error('Error al cargar los gastos correctivos.')
    }
  } catch {
    toast.error('Error de conexión.')
  } finally {
    loading.value = false
  }
}

async function cargarVehiculos() {
  try {
    const res = await apiFetchEmpresa('/api/empresa/vehiculos/')
    if (res.ok) vehiculos.value = (await res.json()).filter(v => v.activo)
  } catch { /* noop */ }
}

watch(() => [props.mes, props.anio], cargar)
watch([filtroVehiculo, filtroCategoria, filtroPrioridad], cargar)

onMounted(async () => {
  await cargarVehiculos()
  await cargar()
})

// ── Modal registrar / editar ────────────────────────────────────────────────────
const modalOpen  = ref(false)
const editandoId = ref(null)
const guardando  = ref(false)
const form = ref({
  vehiculo_id: '', categoria_correctiva: '', prioridad_correctiva: 'media',
  descripcion: '', monto: '', fecha: new Date().toISOString().slice(0, 10),
  comprobante: null,
})

watch(() => form.value.descripcion, () => {
  if (avisoMod.value) limpiarMod()
})

function abrirCrear() {
  editandoId.value = null
  form.value = {
    vehiculo_id: '', categoria_correctiva: '', prioridad_correctiva: 'media',
    descripcion: '', monto: '', fecha: new Date().toISOString().slice(0, 10), comprobante: null,
  }
  limpiarMod()
  modalOpen.value = true
}

function abrirEditar(g) {
  editandoId.value = g.id
  form.value = {
    vehiculo_id: g.vehiculo_id, categoria_correctiva: g.categoria_correctiva,
    prioridad_correctiva: g.prioridad || 'media', descripcion: g.descripcion,
    monto: g.monto, fecha: g.fecha, comprobante: null,
  }
  detalle.value = null
  limpiarMod()
  modalOpen.value = true
}

function onArchivo(e) {
  const f = e.target.files?.[0]
  if (!f) return
  if (f.size > 10 * 1024 * 1024) { toast.error('El archivo no puede superar 10 MB.'); e.target.value = ''; return }
  form.value.comprobante = f
}

async function guardar() {
  const f = form.value
  if (!f.vehiculo_id)            return toast.error('Selecciona un vehículo.')
  if (!f.categoria_correctiva)  return toast.error('Selecciona la categoría.')
  const descLen = (f.descripcion || '').trim().length
  if (descLen < 10) return toast.error('La descripción debe tener al menos 10 caracteres.')
  if (descLen > 200) return toast.error('La descripción no puede superar los 200 caracteres.')
  if (!(Number(f.monto) > 0))   return toast.error('El monto debe ser mayor a 0.')

  const okMod = await moderar(f.descripcion)
  if (!okMod) return

  guardando.value = true
  try {
    let res
    if (editandoId.value) {
      // Editar: JSON (el comprobante se sube aparte).
      res = await apiFetchEmpresa(`/api/empresa/gastos/correctivos/${editandoId.value}/`, {
        method: 'PUT',
        body: {
          categoria_correctiva: f.categoria_correctiva,
          prioridad_correctiva: f.prioridad_correctiva,
          descripcion: f.descripcion.trim(), monto: Number(f.monto), fecha: f.fecha,
        },
      })
    } else {
      // Crear: multipart si hay comprobante, JSON si no.
      if (f.comprobante) {
        const fd = new FormData()
        fd.append('vehiculo_id', f.vehiculo_id)
        fd.append('categoria_correctiva', f.categoria_correctiva)
        fd.append('prioridad_correctiva', f.prioridad_correctiva)
        fd.append('descripcion', f.descripcion.trim())
        fd.append('monto', Number(f.monto))
        fd.append('fecha', f.fecha)
        fd.append('comprobante', f.comprobante, f.comprobante.name)
        res = await apiFetchEmpresa('/api/empresa/gastos/correctivos/', { method: 'POST', body: fd })
      } else {
        res = await apiFetchEmpresa('/api/empresa/gastos/correctivos/', {
          method: 'POST',
          body: {
            vehiculo_id: f.vehiculo_id, categoria_correctiva: f.categoria_correctiva,
            prioridad_correctiva: f.prioridad_correctiva, descripcion: f.descripcion.trim(),
            monto: Number(f.monto), fecha: f.fecha,
          },
        })
      }
    }
    if (!res.ok) { const e = await res.json().catch(() => ({})); toast.error(e.error || 'Error al guardar.'); return }
    toast.success(editandoId.value ? 'Gasto correctivo actualizado.' : 'Gasto correctivo registrado.')
    modalOpen.value = false
    await cargar()
  } catch {
    toast.error('Error de conexión.')
  } finally {
    guardando.value = false
  }
}

// ── Detalle ───────────────────────────────────────────────────────────────────
const detalle = ref(null)
function abrirDetalle(g) { detalle.value = g }

// ── Eliminar ──────────────────────────────────────────────────────────────────
const confirmId  = ref(null)
const eliminando = ref(false)
async function eliminar() {
  if (!confirmId.value) return
  eliminando.value = true
  try {
    const res = await apiFetchEmpresa(`/api/empresa/gastos/correctivos/${confirmId.value}/`, { method: 'DELETE' })
    if (res.ok) { toast.success('Gasto eliminado.'); detalle.value = null; await cargar() }
    else toast.error('Error al eliminar.')
  } catch {
    toast.error('Error de conexión.')
  } finally {
    eliminando.value = false
    confirmId.value = null
  }
}
</script>

<template>
  <div>
    <div class="cabecera-corr">
      <button v-if="puedeCrear" class="btn-nuevo" @click="abrirCrear">+ Registrar gasto correctivo</button>
    </div>

    <!-- Filtros -->
    <div class="filtros">
      <select v-model="filtroVehiculo" class="sel">
        <option value="">Todos los vehículos</option>
        <option v-for="v in vehiculos" :key="v.id" :value="v.id">{{ v.patente }}</option>
      </select>
      <select v-model="filtroCategoria" class="sel">
        <option value="">Todas las categorías</option>
        <option v-for="c in CATEGORIAS" :key="c.value" :value="c.value">{{ c.label }}</option>
      </select>
      <select v-model="filtroPrioridad" class="sel">
        <option value="">Toda prioridad</option>
        <option value="alta">Alta</option>
        <option value="media">Media</option>
        <option value="baja">Baja</option>
      </select>
    </div>

    <div v-if="loading" class="loading"><div class="spinner"/> Cargando...</div>

    <template v-else-if="resumen">
      <!-- KPIs -->
      <div class="kpis">
        <div class="kpi-card kpi-rojo">
          <i class="ti ti-alert-triangle kpi-ic"/>
          <div><div class="kpi-val">{{ clp(resumen.total_correctivos) }}</div><div class="kpi-lbl">Total correctivos del mes</div></div>
        </div>
        <div class="kpi-card">
          <i class="ti ti-percentage kpi-ic" :style="(impactoPresupuesto ?? 0) > 20 ? 'color:#DC2626' : 'color:#D97706'"/>
          <div>
            <div class="kpi-val" :style="(impactoPresupuesto ?? 0) > 20 ? 'color:#DC2626' : 'color:#D97706'">
              {{ impactoPresupuesto !== null ? impactoPresupuesto + '%' : '—' }}
            </div>
            <div class="kpi-lbl">
              Impacto sobre el presupuesto
              <span v-if="esTodas" class="sin-pres"> (no aplica al ver todas las empresas)</span>
              <span v-else-if="impactoPresupuesto === null" class="sin-pres"> (sin presupuesto definido)</span>
            </div>
          </div>
        </div>
        <div class="kpi-card">
          <i class="ti ti-truck kpi-ic" style="color:#4F46E5"/>
          <div>
            <div class="kpi-val">{{ resumen.vehiculo_mas_afectado?.patente || '—' }}</div>
            <div class="kpi-lbl">{{ resumen.vehiculo_mas_afectado ? clp(resumen.vehiculo_mas_afectado.total) + ' · más afectado' : 'Sin afectados' }}</div>
          </div>
        </div>
      </div>

      <!-- Dos columnas: por vehículo (correctivo vs normal) + por categoría -->
      <div class="cols">
        <div class="card">
          <h3 class="card-title">Correctivo vs normal por vehículo</h3>
          <div class="leyenda"><span><i class="dot" style="background:#9CA3AF"/>Normal</span><span><i class="dot" style="background:#DC2626"/>Correctivo</span></div>
          <div v-if="!resumen.por_vehiculo.length" class="vacio">Sin gastos en el período.</div>
          <div v-for="v in resumen.por_vehiculo" :key="v.vehiculo_id" class="veh-row">
            <div class="veh-info">
              <span class="veh-pat">{{ v.patente }}</span>
              <span v-if="v.modelo" class="veh-modelo">{{ v.modelo }}</span>
            </div>
            <div class="barra-wrap barra-stack">
              <div v-if="v.total_normal" class="barra-seg" :style="`width:${(v.total_normal / maxVehiculo) * 100}%;background:#9CA3AF`" :title="`Normal: ${clp(v.total_normal)}`"/>
              <div v-if="v.total_correctivo" class="barra-seg" :style="`width:${(v.total_correctivo / maxVehiculo) * 100}%;background:#DC2626`" :title="`Correctivo: ${clp(v.total_correctivo)}`"/>
            </div>
            <span class="veh-tot">{{ clp(v.total_correctivo) }}</span>
          </div>
        </div>

        <div class="card">
          <h3 class="card-title">Por categoría</h3>
          <div v-if="!resumen.por_categoria.length" class="vacio">Sin gastos en el período.</div>
          <div v-for="c in resumen.por_categoria" :key="c.categoria" class="cat-row">
            <div class="cat-head">
              <span class="badge" :style="`background:${catStyle(c.categoria).bg};color:${catStyle(c.categoria).text}`">{{ c.label }}</span>
              <span class="cat-monto">{{ clp(c.total) }} · {{ c.pct }}%</span>
            </div>
            <div class="barra-wrap"><div class="barra" :style="`width:${c.pct}%;background:${catStyle(c.categoria).text}`"/></div>
          </div>
        </div>
      </div>

      <!-- Tabla de registros -->
      <div class="card">
        <h3 class="card-title">Registros</h3>
        <div v-if="!gastos.length" class="vacio">No hay gastos correctivos registrados en este período.</div>
        <div v-else class="tabla-wrap">
          <table class="tabla">
            <thead>
              <tr><th v-if="esTodas">Empresa</th><th>Fecha</th><th>Vehículo</th><th>Categoría</th><th>Descripción</th><th>Prioridad</th><th class="r">Monto</th><th>Comp.</th></tr>
            </thead>
            <tbody>
              <tr v-for="g in gastosPaginados" :key="g.id" class="fila" @click="abrirDetalle(g)">
                <td v-if="esTodas" class="mono">{{ g.empresa_nombre || '—' }}</td>
                <td>{{ fmtFecha(g.fecha) }}</td>
                <td>
                  <div class="td-veh">
                    <span class="mono">{{ g.vehiculo_patente || '—' }}</span>
                    <span v-if="g.vehiculo_modelo" class="td-veh-sub">{{ g.vehiculo_modelo }}</span>
                    <span class="td-veh-cond"><i class="ti ti-user"/>{{ g.vehiculo_conductor || 'Sin conductor' }}</span>
                  </div>
                </td>
                <td><span class="badge" :style="`background:${catStyle(g.categoria_correctiva).bg};color:${catStyle(g.categoria_correctiva).text}`">{{ g.categoria_display }}</span></td>
                <td class="desc">{{ g.descripcion }}</td>
                <td><span class="badge" :style="`background:${prioStyle(g.prioridad).bg};color:${prioStyle(g.prioridad).text}`">{{ prioStyle(g.prioridad).label }}</span></td>
                <td class="r" :style="g.monto > 200000 ? 'color:#DC2626;font-weight:700' : 'font-weight:600'">{{ clp(g.monto) }}</td>
                <td><i v-if="g.tiene_comprobante" class="ti ti-paperclip" style="color:#6B7280"/><span v-else class="text-tenue">—</span></td>
              </tr>
            </tbody>
          </table>
          <PaginacionTabla :pagina="paginaGastos" :total-paginas="totalPaginasGastos" :total="totalGastos"
            @update:pagina="irAPaginaGastos" />
        </div>
      </div>

      <!-- Evolución 6 meses (barras apiladas CSS) -->
      <div class="card">
        <h3 class="card-title">Evolución últimos 6 meses</h3>
        <div class="leyenda"><span><i class="dot" style="background:#9CA3AF"/>Normal</span><span><i class="dot" style="background:#DC2626"/>Correctivo</span></div>
        <div class="evol">
          <div v-for="m in resumen.evolucion_mensual" :key="m.mes" class="evol-col">
            <div class="evol-barras">
              <div class="evol-seg" :style="`height:${altoBarra(m.total_correctivo)}px;background:#DC2626`" :title="`Correctivo: ${clp(m.total_correctivo)}`"/>
              <div class="evol-seg" :style="`height:${altoBarra(m.total_normal)}px;background:#9CA3AF`" :title="`Normal: ${clp(m.total_normal)}`"/>
            </div>
            <span class="evol-lbl">{{ m.mes }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- ── Modal registrar / editar ── -->
    <div v-if="modalOpen" class="overlay" @click.self="modalOpen = false">
      <div class="modal">
        <h2 class="modal-title">{{ editandoId ? 'Editar' : 'Registrar' }} gasto correctivo</h2>

        <label class="lbl">Vehículo</label>
        <select v-model="form.vehiculo_id" class="inp" :disabled="!!editandoId">
          <option value="">— Selecciona —</option>
          <option v-for="v in vehiculos" :key="v.id" :value="v.id">{{ v.patente }} · {{ v.marca }} {{ v.modelo }}</option>
        </select>

        <div class="grid2">
          <div>
            <label class="lbl">Categoría</label>
            <select v-model="form.categoria_correctiva" class="inp">
              <option value="">— Selecciona —</option>
              <option v-for="c in CATEGORIAS" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
          <div>
            <label class="lbl">Prioridad</label>
            <select v-model="form.prioridad_correctiva" class="inp">
              <option value="alta">Alta</option>
              <option value="media">Media</option>
              <option value="baja">Baja</option>
            </select>
          </div>
        </div>

        <label class="lbl">
          Descripción
          <span class="cont" :class="{ over: (form.descripcion || '').length > 200 }">{{ (form.descripcion || '').length }}/200</span>
        </label>
        <textarea v-model="form.descripcion" class="inp" rows="3" maxlength="200" placeholder="Entre 10 y 200 caracteres"/>
        <AvisoModeracion :aviso="avisoMod" :sugerencia="sugerenciaMod" />

        <div class="grid2">
          <div>
            <label class="lbl">Monto (CLP)</label>
            <input v-model="form.monto" type="number" min="1" class="inp" placeholder="0"/>
          </div>
          <div>
            <label class="lbl">Fecha</label>
            <input v-model="form.fecha" type="date" class="inp" :max="new Date().toISOString().slice(0,10)"/>
          </div>
        </div>

        <template v-if="!editandoId">
          <label class="lbl">Comprobante <span class="opt">(opcional, PDF o imagen)</span></label>
          <input type="file" accept=".pdf,image/*" class="inp" @change="onArchivo"/>
        </template>

        <div class="modal-acts">
          <button class="btn-sec" @click="modalOpen = false" :disabled="guardando">Cancelar</button>
          <button class="btn-pri" @click="guardar" :disabled="guardando">{{ guardando ? 'Guardando...' : 'Guardar' }}</button>
        </div>
      </div>
    </div>

    <!-- ── Modal detalle ── -->
    <div v-if="detalle" class="overlay" @click.self="detalle = null">
      <div class="modal">
        <h2 class="modal-title">Detalle del gasto correctivo</h2>
        <div v-if="esTodas" class="det-row"><span>Empresa</span><strong>{{ detalle.empresa_nombre || '—' }}</strong></div>
        <div class="det-row"><span>Vehículo</span><strong>{{ detalle.vehiculo_patente || '—' }}</strong></div>
        <div class="det-row"><span>Categoría</span><span class="badge" :style="`background:${catStyle(detalle.categoria_correctiva).bg};color:${catStyle(detalle.categoria_correctiva).text}`">{{ detalle.categoria_display }}</span></div>
        <div class="det-row"><span>Prioridad</span><span class="badge" :style="`background:${prioStyle(detalle.prioridad).bg};color:${prioStyle(detalle.prioridad).text}`">{{ prioStyle(detalle.prioridad).label }}</span></div>
        <div class="det-row"><span>Monto</span><strong>{{ clp(detalle.monto) }}</strong></div>
        <div class="det-row"><span>Fecha</span><strong>{{ fmtFecha(detalle.fecha) }}</strong></div>
        <div class="det-row"><span>Registró</span><strong>{{ detalle.registrado_por || '—' }}</strong></div>
        <p class="det-desc">{{ detalle.descripcion }}</p>
        <a v-if="detalle.comprobante" :href="detalle.comprobante" target="_blank" class="det-comp"><i class="ti ti-download"/> Descargar comprobante</a>

        <div class="modal-acts">
          <button v-if="puedeEliminar" class="btn-del" @click="confirmId = detalle.id">Eliminar</button>
          <button v-if="puedeEditar" class="btn-sec" @click="abrirEditar(detalle)">Editar</button>
          <button class="btn-pri" @click="detalle = null">Cerrar</button>
        </div>
      </div>
    </div>

    <ConfirmModal
      v-if="confirmId"
      titulo="Eliminar gasto correctivo"
      mensaje="¿Seguro? Esta acción no se puede deshacer."
      label-ok="Eliminar" :peligroso="true"
      @confirmar="eliminar" @cancelar="confirmId = null"
    />
  </div>
</template>

<style scoped>
* { box-sizing: border-box; }
.cabecera-corr { display: flex; justify-content: flex-end; margin-bottom: 1rem; }
.btn-nuevo { padding: 0.5rem 0.9rem; background: #E24B4A; color: #fff; border: none; border-radius: 9px; font-size: 0.8125rem; font-weight: 600; cursor: pointer; }

.filtros { display: flex; gap: 0.6rem; margin-bottom: 1rem; flex-wrap: wrap; }
.sel { padding: 0.45rem 0.7rem; border: 1.5px solid #E5E7EB; border-radius: 8px; font-size: 0.8125rem; background: #fff; color: #374151; cursor: pointer; }

.loading { display: flex; align-items: center; gap: 0.6rem; color: #6B7280; padding: 2rem 0; font-size: 0.875rem; }
.spinner { width: 20px; height: 20px; border: 2.5px solid #E5E7EB; border-top-color: #E24B4A; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 0.85rem; margin-bottom: 1.25rem; }
.kpi-card { display: flex; align-items: center; gap: 0.75rem; background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; padding: 0.9rem 1rem; }
.kpi-card.kpi-rojo { border-color: #FECACA; background: #FEF2F2; }
.kpi-ic { font-size: 24px; color: #DC2626; }
.kpi-val { font-size: 1.25rem; font-weight: 800; color: #111827; line-height: 1.1; }
.kpi-lbl { font-size: 0.75rem; color: #6B7280; }
.sin-pres { font-size: 0.65rem; color: #9CA3AF; display: block; }

.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.25rem; }
@media (max-width: 900px) { .cols { grid-template-columns: 1fr; } }
.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 14px; padding: 1.1rem 1.25rem; margin-bottom: 1.25rem; }
.card-title { font-size: 0.9375rem; font-weight: 700; color: #111827; margin: 0 0 0.75rem; }
.vacio { font-size: 0.8125rem; color: #9CA3AF; padding: 0.5rem 0; }
.leyenda { display: flex; gap: 1rem; font-size: 0.75rem; color: #6B7280; margin-bottom: 0.6rem; }
.leyenda span { display: inline-flex; align-items: center; gap: 0.3rem; }
.dot { width: 9px; height: 9px; border-radius: 2px; display: inline-block; }

.veh-row { display: grid; grid-template-columns: 130px 1fr 90px; align-items: center; gap: 0.6rem; margin-bottom: 0.65rem; }
.veh-info { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.veh-pat { font-family: ui-monospace, monospace; font-size: 0.75rem; font-weight: 700; color: #1E1B4B; }
.veh-modelo { font-size: 0.6875rem; color: #6B7280; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.veh-cond { font-size: 0.6875rem; color: #9CA3AF; display: flex; align-items: center; gap: 0.2rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.veh-cond i { font-size: 11px; }
.veh-barras { display: flex; flex-direction: column; gap: 2px; }
.veh-tot { font-size: 0.75rem; font-weight: 600; color: #DC2626; text-align: right; }
.barra-wrap { background: #F3F4F6; border-radius: 999px; height: 8px; overflow: hidden; }
/* Barra única con segmentos normal+correctivo en la misma línea */
.barra-stack { display: flex; }
.barra-seg { height: 100%; transition: width 0.3s; }
.barra { height: 100%; border-radius: 999px; transition: width 0.3s; }

.cat-row { margin-bottom: 0.7rem; }
.cat-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem; }
.cat-monto { font-size: 0.75rem; color: #6B7280; }
.badge { display: inline-block; padding: 0.15rem 0.55rem; border-radius: 999px; font-size: 0.7rem; font-weight: 600; white-space: nowrap; }

.tabla-wrap { overflow-x: auto; }
.tabla { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
.tabla th { text-align: left; padding: 0.5rem 0.6rem; font-size: 0.7rem; font-weight: 600; color: #6B7280; text-transform: uppercase; border-bottom: 1px solid #E5E7EB; }
.tabla th.r { text-align: right; }
.tabla td { padding: 0.55rem 0.6rem; border-bottom: 1px solid #F3F4F6; color: #374151; }
.tabla td.r { text-align: right; }
.fila { cursor: pointer; }
.fila:hover { background: #FEF2F2; }
.mono { font-family: ui-monospace, monospace; font-weight: 600; }
.td-veh { display: flex; flex-direction: column; gap: 1px; }
.td-veh-sub  { font-size: 0.6875rem; color: #6B7280; }
.td-veh-cond { font-size: 0.6875rem; color: #9CA3AF; display: flex; align-items: center; gap: 0.2rem; }
.td-veh-cond i { font-size: 11px; }
.desc { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.text-tenue { color: #D1D5DB; }

.evol { display: flex; align-items: flex-end; justify-content: space-around; height: 130px; gap: 0.5rem; }
.evol-col { display: flex; flex-direction: column; align-items: center; gap: 0.4rem; flex: 1; }
.evol-barras { display: flex; flex-direction: column-reverse; justify-content: flex-start; height: 95px; width: 28px; }
.evol-seg { width: 100%; border-radius: 2px 2px 0 0; }
.evol-lbl { font-size: 0.65rem; color: #9CA3AF; }

.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; padding: 1rem; z-index: 60; }
.modal { background: #fff; border-radius: 16px; padding: 1.5rem; width: 100%; max-width: 460px; max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 50px rgba(0,0,0,0.2); }
.modal-title { font-size: 1.05rem; font-weight: 700; color: #1E1B4B; margin: 0 0 1rem; }
.lbl { display: block; font-size: 0.8125rem; font-weight: 600; color: #374151; margin: 0.6rem 0 0.3rem; }
.cont { float: right; font-weight: 400; color: #9CA3AF; }
.cont.over { color: #DC2626; }
.opt { font-weight: 400; color: #9CA3AF; }
.inp { width: 100%; padding: 0.55rem 0.75rem; border: 1.5px solid #D1D5DB; border-radius: 9px; font-size: 0.875rem; color: #111827; background: #fff; outline: none; font-family: inherit; }
.inp:focus { border-color: #E24B4A; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.modal-acts { display: flex; justify-content: flex-end; gap: 0.6rem; margin-top: 1.25rem; }
.btn-pri { padding: 0.55rem 1.1rem; background: #E24B4A; color: #fff; border: none; border-radius: 9px; font-size: 0.8125rem; font-weight: 600; cursor: pointer; }
.btn-pri:disabled { opacity: 0.6; }
.btn-sec { padding: 0.55rem 1.1rem; background: #fff; border: 1.5px solid #D1D5DB; border-radius: 9px; font-size: 0.8125rem; font-weight: 600; color: #374151; cursor: pointer; }
.btn-del { padding: 0.55rem 1.1rem; background: #FEF2F2; border: 1.5px solid #FECACA; border-radius: 9px; font-size: 0.8125rem; font-weight: 600; color: #DC2626; cursor: pointer; margin-right: auto; }
.det-row { display: flex; justify-content: space-between; align-items: center; padding: 0.45rem 0; border-bottom: 1px solid #F3F4F6; font-size: 0.875rem; color: #6B7280; }
.det-row strong { color: #111827; }
.det-desc { font-size: 0.875rem; color: #374151; background: #F9FAFB; border-radius: 9px; padding: 0.7rem; margin: 0.75rem 0; overflow-wrap: anywhere; white-space: pre-wrap; }
.det-comp { display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.8125rem; color: #4F46E5; text-decoration: none; font-weight: 600; }
</style>
