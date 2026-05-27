<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../../utils/api.js'

const suscripciones = ref([])
const kpis          = ref({})
const cargando      = ref(true)
const error         = ref('')
const filtroEstado  = ref('')
const busqueda      = ref('')

// ── Modal pago manual ────────────────────────────────────────
const modalPago       = ref(null)   // suscripción seleccionada o null
const pagoMonto       = ref('')
const pagoCiclo       = ref('mensual')
const pagoMetodo      = ref('Transferencia bancaria')
const pagoNota        = ref('')
const pagoGuardando   = ref(false)
const pagoError       = ref('')

function abrirModalPago(s) {
  modalPago.value   = s
  pagoMonto.value   = ''
  pagoCiclo.value   = 'mensual'
  pagoMetodo.value  = 'Transferencia bancaria'
  pagoNota.value    = ''
  pagoError.value   = ''
}

function cerrarModalPago() {
  modalPago.value = null
}

async function confirmarPagoManual() {
  if (!pagoMonto.value || Number(pagoMonto.value) <= 0) {
    pagoError.value = 'Ingresa un monto válido.'
    return
  }
  pagoGuardando.value = true
  pagoError.value     = ''
  try {
    const res = await apiFetch(`/api/admin/suscripciones/${modalPago.value.id}/`, {
      method: 'PUT',
      body: {
        accion:  'pago_manual',
        monto:   Number(pagoMonto.value),
        ciclo:   pagoCiclo.value,
        metodo:  pagoMetodo.value,
        nota:    pagoNota.value,
      },
    })
    if (!res.ok) { pagoError.value = 'Error al registrar el pago.'; return }
    cerrarModalPago()
    await cargar()
  } catch {
    pagoError.value = 'Error de conexión.'
  } finally {
    pagoGuardando.value = false
  }
}

async function cargar() {
  cargando.value = true
  error.value    = ''
  try {
    let url = '/api/admin/suscripciones/'
    const params = new URLSearchParams()
    if (filtroEstado.value) params.set('estado', filtroEstado.value)
    if (busqueda.value)     params.set('q', busqueda.value)
    if (params.toString())  url += '?' + params.toString()

    const res  = await apiFetch(url)
    if (!res.ok) { error.value = 'Error al cargar suscripciones.'; return }
    const data = await res.json()
    suscripciones.value = data.suscripciones || []
    kpis.value          = data.kpis || {}
  } catch {
    error.value = 'Error de conexión.'
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)

async function accion(sus, accionNombre, dias = null) {
  const body = { accion: accionNombre }
  if (dias !== null) body.dias = dias
  const res  = await apiFetch(`/api/admin/suscripciones/${sus.id}/`, { method: 'PUT', body })
  if (res.ok) await cargar()
  else alert('Error al ejecutar la acción.')
}

function formatCLP(n) {
  return '$' + parseInt(n).toLocaleString('es-CL')
}

const BADGE = {
  activa:     { label: 'Activa',            cls: 'badge-activa' },
  pendiente:  { label: 'Pendiente de pago', cls: 'badge-pendiente' },
  gracia:     { label: 'En gracia',         cls: 'badge-gracia' },
  suspendida: { label: 'Suspendida',        cls: 'badge-suspendida' },
  cancelada:  { label: 'Cancelada',         cls: 'badge-cancelada' },
}

// ── Comprobante ──────────────────────────────────────────────────────
const comprobanteLoading = ref(null)   // empresa_id cargando

async function descargarComprobante(sus) {
  comprobanteLoading.value = sus.empresa_id
  try {
    const res  = await apiFetch(`/api/pago/historial/?empresa_id=${sus.empresa_id}`)
    if (!res.ok) { alert('No se pudo obtener el historial de pagos.'); return }
    const data = await res.json()
    const pagos = data.pagos || []
    if (!pagos.length) { alert('Esta empresa no tiene pagos aprobados aún.'); return }
    imprimirComprobante(pagos[0], sus.empresa)
  } catch {
    alert('Error de conexión.')
  } finally {
    comprobanteLoading.value = null
  }
}

function imprimirComprobante(p, empresaNombre) {
  const nombre   = p.empresa_nombre || empresaNombre || '—'
  const viaLabel = p.via === 'oneclick' || p.via === 'autocobro'
    ? 'Tarjeta guardada (OneClick)'
    : 'Webpay Plus'

  const html = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Comprobante ${p.orden_compra}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Arial, Helvetica, sans-serif; padding: 48px 40px; max-width: 520px; margin: 0 auto; color: #111827; }
    .logo    { font-size: 1.25rem; font-weight: 800; color: #4F46E5; margin-bottom: 4px; }
    .titulo  { font-size: .875rem; color: #6B7280; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 28px; }
    .badge   { display: inline-block; background: #D1FAE5; color: #065F46; font-size: .8125rem; font-weight: 700; padding: 4px 14px; border-radius: 99px; margin-bottom: 24px; }
    hr       { border: none; border-top: 1px solid #E5E7EB; margin: 18px 0; }
    .fila    { display: flex; justify-content: space-between; padding: 7px 0; font-size: .9rem; }
    .label   { color: #6B7280; }
    .valor   { font-weight: 600; text-align: right; }
    .mono    { font-family: monospace; font-size: .8125rem; color: #6B7280; }
    .total   .label { font-size: 1rem; font-weight: 700; color: #111827; }
    .total   .valor { font-size: 1.25rem; font-weight: 800; color: #4F46E5; }
    .nota    { margin-top: 28px; padding: 12px 16px; background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 6px; font-size: .75rem; color: #9CA3AF; line-height: 1.5; }
    .footer  { margin-top: 36px; font-size: .75rem; color: #D1D5DB; text-align: center; }
    @media print { body { padding: 20px; } }
  </style>
</head>
<body>
  <div class="logo">🚛 Gestión de Flota</div>
  <div class="titulo">Comprobante de pago</div>
  <div class="badge">✓ Pago aprobado</div>
  <div class="fila"><span class="label">N° Orden</span><span class="valor mono">${p.orden_compra}</span></div>
  <div class="fila"><span class="label">Empresa</span><span class="valor">${nombre}${p.empresa_rut ? ' · ' + p.empresa_rut : ''}</span></div>
  <hr>
  <div class="fila"><span class="label">Plan</span><span class="valor">${p.plan}</span></div>
  <div class="fila"><span class="label">Ciclo</span><span class="valor" style="text-transform:capitalize">${p.ciclo}</span></div>
  <div class="fila"><span class="label">Medio de pago</span><span class="valor">${viaLabel}</span></div>
  <div class="fila"><span class="label">Fecha de pago</span><span class="valor">${p.fecha || '—'}</span></div>
  <hr>
  <div class="fila total"><span class="label">Total pagado</span><span class="valor">$${parseInt(p.monto).toLocaleString('es-CL')}</span></div>
  <div class="nota">⚠ Comprobante interno. <strong>No constituye un DTE válido para el SII.</strong></div>
  <div class="footer">Generado el ${new Date().toLocaleDateString('es-CL', {day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'})}</div>
  <script>window.onload=function(){setTimeout(function(){window.print();},400);}<\/script>
</body>
</html>`

  const win = window.open('', '_blank', 'width=620,height=760')
  if (win) { win.document.write(html); win.document.close() }
}
</script>

<template>
  <div class="pagos-page">
    <h1 class="pagos-title">Pagos y Suscripciones</h1>

    <!-- KPIs -->
    <div class="kpis-grid">
      <div class="kpi-card">
        <p class="kpi-label">MRR del mes</p>
        <p class="kpi-val">{{ kpis.mrr ? formatCLP(kpis.mrr) : '$0' }}</p>
      </div>
      <div class="kpi-card">
        <p class="kpi-label">Activas</p>
        <p class="kpi-val kpi-verde">{{ kpis.activas ?? '—' }}</p>
      </div>
      <div class="kpi-card">
        <p class="kpi-label">Sin pago</p>
        <p class="kpi-val kpi-azul">{{ kpis.pendientes ?? '—' }}</p>
      </div>
      <div class="kpi-card">
        <p class="kpi-label">En gracia</p>
        <p class="kpi-val kpi-naranja">{{ kpis.en_gracia ?? '—' }}</p>
      </div>
      <div class="kpi-card">
        <p class="kpi-label">Suspendidas</p>
        <p class="kpi-val kpi-rojo">{{ kpis.suspendidas ?? '—' }}</p>
      </div>
    </div>

    <!-- Filtros -->
    <div class="filtros">
      <input
        v-model="busqueda"
        placeholder="Buscar empresa…"
        class="filtro-input"
        @keydown.enter="cargar"
      />
      <select v-model="filtroEstado" class="filtro-select" @change="cargar">
        <option value="">Todos los estados</option>
        <option value="activa">Activa</option>
        <option value="pendiente">Pendiente de pago</option>
        <option value="gracia">En gracia</option>
        <option value="suspendida">Suspendida</option>
        <option value="cancelada">Cancelada</option>
      </select>
      <button class="btn-buscar" @click="cargar">Buscar</button>
    </div>

    <div v-if="cargando" class="estado-msg">Cargando…</div>
    <div v-else-if="error" class="error-box">{{ error }}</div>

    <div v-else class="tabla-wrap">
      <table class="tabla">
        <thead>
          <tr>
            <th>Empresa</th>
            <th>Plan</th>
            <th>Ciclo</th>
            <th>Estado</th>
            <th>Próximo cobro</th>
            <th>Último pago</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in suscripciones" :key="s.id">
            <td class="empresa-col">{{ s.empresa }}</td>
            <td>{{ s.plan || '—' }}</td>
            <td class="cap">{{ s.ciclo }}</td>
            <td>
              <span :class="['badge', BADGE[s.estado]?.cls]">
                {{ BADGE[s.estado]?.label || s.estado }}
                <template v-if="s.estado === 'gracia' && s.dias_para_vencer !== null">
                  ({{ s.dias_para_vencer }}d)
                </template>
              </span>
            </td>
            <td>{{ s.fecha_fin || '—' }}</td>
            <td>{{ s.ultimo_pago || '—' }}</td>
            <td class="acciones-col">
              <!-- Registrar pago manual: visible para pendiente, gracia y suspendida -->
              <button
                v-if="['pendiente','gracia','suspendida'].includes(s.estado)"
                class="btn-accion btn-pago-manual"
                @click="abrirModalPago(s)"
              >💰 Registrar pago</button>
              <button
                v-if="s.estado === 'gracia'"
                class="btn-accion btn-extender"
                @click="accion(s, 'extender_gracia', 7)"
              >+7 días gracia</button>
              <button
                v-if="s.ultimo_pago"
                class="btn-accion btn-comprobante"
                :disabled="comprobanteLoading === s.empresa_id"
                @click="descargarComprobante(s)"
              >
                {{ comprobanteLoading === s.empresa_id ? '…' : '🧾 Comprobante' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!suscripciones.length" class="estado-msg">Sin resultados.</p>
    </div>
  </div>

  <!-- Modal pago manual -->
  <Teleport to="body">
    <div v-if="modalPago" class="modal-overlay" @click.self="cerrarModalPago">
      <div class="modal-box">
        <div class="modal-header">
          <h3 class="modal-title">Registrar pago manual</h3>
          <button class="modal-close" @click="cerrarModalPago">✕</button>
        </div>
        <p class="modal-empresa">{{ modalPago.empresa }} — {{ modalPago.plan }}</p>

        <div class="modal-body">
          <div class="m-campo">
            <label class="m-label">Monto (CLP)</label>
            <input
              v-model="pagoMonto"
              type="number"
              min="1"
              class="m-input"
              placeholder="Ej: 29990"
              @keydown.enter="confirmarPagoManual"
            />
          </div>

          <div class="m-campo">
            <label class="m-label">Ciclo</label>
            <select v-model="pagoCiclo" class="m-input">
              <option value="mensual">Mensual (30 días)</option>
              <option value="anual">Anual (365 días)</option>
            </select>
          </div>

          <div class="m-campo">
            <label class="m-label">Método de pago</label>
            <select v-model="pagoMetodo" class="m-input">
              <option>Transferencia bancaria</option>
              <option>Efectivo</option>
              <option>Cheque</option>
              <option>Otro</option>
            </select>
          </div>

          <div class="m-campo">
            <label class="m-label">Nota (opcional)</label>
            <input v-model="pagoNota" type="text" class="m-input" placeholder="N° transferencia, referencia…" />
          </div>

          <div v-if="pagoError" class="m-error">{{ pagoError }}</div>
        </div>

        <div class="modal-footer">
          <button class="m-btn-cancel" @click="cerrarModalPago">Cancelar</button>
          <button class="m-btn-ok" :disabled="pagoGuardando" @click="confirmarPagoManual">
            {{ pagoGuardando ? 'Guardando…' : 'Confirmar pago' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.pagos-page  { padding: 2rem 2.5rem; max-width: 1100px; margin: 0 auto; }
.pagos-title { font-size: 1.5rem; font-weight: 700; color: #111827; margin: 0 0 1.5rem; }

.kpis-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
.kpi-card  { background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.25rem; }
.kpi-label { font-size: 0.8125rem; color: #6B7280; margin: 0 0 0.35rem; }
.kpi-val   { font-size: 1.5rem; font-weight: 700; color: #111827; margin: 0; }
.kpi-verde   { color: #059669; }
.kpi-azul    { color: #2563EB; }
.kpi-naranja { color: #D97706; }
.kpi-rojo    { color: #DC2626; }

.filtros { display: flex; gap: 0.75rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
.filtro-input  {
  flex: 1; min-width: 180px; padding: 0.5rem 0.75rem;
  border: 1px solid #E5E7EB; border-radius: 8px; font-size: 0.875rem; font-family: inherit;
}
.filtro-select {
  padding: 0.5rem 0.75rem; border: 1px solid #E5E7EB; border-radius: 8px;
  font-size: 0.875rem; background: #fff; font-family: inherit;
}
.btn-buscar {
  padding: 0.5rem 1.25rem; background: #4F46E5; color: #fff; border: none;
  border-radius: 8px; font-size: 0.875rem; font-weight: 500; cursor: pointer;
  transition: background 0.15s; font-family: inherit;
}
.btn-buscar:hover { background: #4338CA; }

.estado-msg { color: #6B7280; font-size: 0.9rem; padding: 1.5rem 0; }
.error-box  { background: #FEF2F2; border: 1px solid #FECACA; color: #B91C1C; padding: 0.75rem 1rem; border-radius: 8px; font-size: 0.875rem; }

.tabla-wrap { overflow-x: auto; }
.tabla { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.tabla thead th {
  text-align: left; padding: 0.625rem 0.875rem;
  background: #F9FAFB; color: #374151; font-weight: 600;
  border-bottom: 1px solid #E5E7EB; white-space: nowrap;
}
.tabla tbody tr:hover { background: #F9FAFB; }
.tabla tbody td { padding: 0.75rem 0.875rem; border-bottom: 1px solid #F3F4F6; color: #374151; }
.empresa-col { font-weight: 600; }
.cap { text-transform: capitalize; }

.badge          { font-size: 0.75rem; font-weight: 600; padding: 2px 10px; border-radius: 99px; white-space: nowrap; }
.badge-activa    { background: #D1FAE5; color: #065F46; }
.badge-pendiente { background: #DBEAFE; color: #1D4ED8; }
.badge-gracia    { background: #FEF3C7; color: #92400E; }
.badge-suspendida{ background: #FEE2E2; color: #991B1B; }
.badge-cancelada { background: #F3F4F6; color: #6B7280; }

.acciones-col { white-space: nowrap; }
.btn-accion {
  padding: 0.3rem 0.75rem; border-radius: 6px; font-size: 0.8rem; font-weight: 500;
  cursor: pointer; border: 1px solid transparent; font-family: inherit; text-decoration: none;
  display: inline-block; transition: opacity 0.15s;
}
.btn-accion:hover { opacity: 0.85; }
.btn-reactivar    { background: #059669; color: #fff; }
.btn-extender     { background: #D97706; color: #fff; }
.btn-pago-manual  { background: #4F46E5; color: #fff; }
.btn-comprobante  { background: #F3F4F6; color: #374151; border-color: #E5E7EB; }
.btn-comprobante:hover { background: #E5E7EB; }
.btn-comprobante:disabled { opacity: .5; cursor: not-allowed; }

/* Modal pago manual */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.45);
  z-index: 9000; display: flex; align-items: center; justify-content: center;
}
.modal-box {
  background: #fff; border-radius: 14px; width: 100%; max-width: 440px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2); overflow: hidden;
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1.1rem 1.5rem; border-bottom: 1px solid #F3F4F6;
}
.modal-title  { font-size: 1rem; font-weight: 700; color: #111827; margin: 0; }
.modal-close  { background: none; border: none; font-size: 1rem; color: #9CA3AF; cursor: pointer; padding: 0.25rem; }
.modal-close:hover { color: #374151; }
.modal-empresa { font-size: 0.875rem; color: #6B7280; margin: 0; padding: 0.6rem 1.5rem 0; }
.modal-body   { padding: 1rem 1.5rem; display: flex; flex-direction: column; gap: 0.875rem; }
.modal-footer { display: flex; justify-content: flex-end; gap: 0.75rem; padding: 1rem 1.5rem; border-top: 1px solid #F3F4F6; }
.m-campo      { display: flex; flex-direction: column; gap: 0.3rem; }
.m-label      { font-size: 0.8125rem; font-weight: 600; color: #374151; }
.m-input {
  padding: 0.5rem 0.75rem; border: 1px solid #E5E7EB; border-radius: 8px;
  font-size: 0.875rem; font-family: inherit; width: 100%; box-sizing: border-box;
}
.m-input:focus { outline: none; border-color: #4F46E5; box-shadow: 0 0 0 3px rgba(79,70,229,0.1); }
.m-error { font-size: 0.8125rem; color: #B91C1C; background: #FEE2E2; padding: 0.4rem 0.75rem; border-radius: 6px; }
.m-btn-cancel {
  padding: 0.5rem 1.25rem; background: #F3F4F6; color: #374151;
  border: none; border-radius: 8px; font-size: 0.875rem; font-weight: 500; cursor: pointer; font-family: inherit;
}
.m-btn-cancel:hover { background: #E5E7EB; }
.m-btn-ok {
  padding: 0.5rem 1.5rem; background: #4F46E5; color: #fff;
  border: none; border-radius: 8px; font-size: 0.875rem; font-weight: 600; cursor: pointer; font-family: inherit;
  transition: background 0.15s;
}
.m-btn-ok:hover:not(:disabled) { background: #4338CA; }
.m-btn-ok:disabled { opacity: 0.55; cursor: not-allowed; }
</style>
