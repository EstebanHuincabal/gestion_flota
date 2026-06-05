<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiFetch } from '../../../utils/api.js'
import { useToast } from '../../../utils/useToast.js'

const toast = useToast()

const planUso   = ref(null)
const historial = ref([])
const planes    = ref([])
const cargando  = ref(true)

const modalPlan   = ref(null)
const procesando  = ref(false)
const cancelando  = ref(false)

const DIAS_CICLO = 30

const cargar = async () => {
  cargando.value = true
  const [r1, r2, r3] = await Promise.all([
    apiFetch('/api/empresa/plan-uso/'),
    apiFetch('/api/empresa/plan-historial/'),
    apiFetch('/api/configuracion/planes/'),
  ])
  if (r1.ok) planUso.value   = await r1.json()
  if (r2.ok) historial.value = await r2.json()
  if (r3.ok) planes.value    = await r3.json()
  cargando.value = false
}

const colorBarra = (pct) => {
  if (pct >= 90) return '#EF4444'
  if (pct >= 70) return '#F59E0B'
  return '#10B981'
}

const dimLabel = {
  vehiculos: 'Vehículos', conductores: 'Conductores', usuarios: 'Usuarios',
}

function clp(v) { return '$' + Number(v || 0).toLocaleString('es-CL') }

const esPlanActual = (plan) =>
  planUso.value?.plan && planUso.value.plan.id === plan.id

// Tipo de cambio respecto al plan actual: 'actual' | 'upgrade' | 'downgrade' | 'lateral'
function tipoCambio(plan) {
  const actual = planUso.value?.plan
  if (!actual) return 'lateral'
  if (actual.id === plan.id) return 'actual'
  const pa = Number(actual.precio_mensual || 0)
  const pn = Number(plan.precio_mensual || 0)
  if (pn > pa) return 'upgrade'
  if (pn < pa) return 'downgrade'
  return 'lateral'
}

// Estimación de la diferencia prorrateada a cobrar al subir de plan.
function proracionEstimada(plan) {
  const sus    = planUso.value?.suscripcion
  const actual = planUso.value?.plan
  if (!sus || !sus.dias_restantes || sus.dias_restantes <= 0 || !actual) return 0
  const dif = Math.max(0, Number(plan.precio_mensual || 0) - Number(actual.precio_mensual || 0))
  return Math.round(dif * sus.dias_restantes / DIAS_CICLO)
}

const suscripcionVigente = computed(() => planUso.value?.suscripcion?.vigente === true)

const modalTipo      = computed(() => modalPlan.value ? tipoCambio(modalPlan.value) : null)
const modalProracion = computed(() => modalPlan.value ? proracionEstimada(modalPlan.value) : 0)

const abrirModal  = (plan) => { modalPlan.value = plan }
const cerrarModal = () => { modalPlan.value = null }

const confirmarCambio = async () => {
  if (!modalPlan.value) return
  procesando.value = true
  const res  = await apiFetch('/api/empresa/cambiar-plan/', {
    method: 'POST',
    body: { plan_id: modalPlan.value.id },
  })
  const data = await res.json().catch(() => ({}))
  if (res.ok) {
    // Upgrade sin tarjeta guardada → redirigir a Webpay para pagar la diferencia.
    // Webpay Plus exige un POST con token_ws (no un GET): se arma un form y se envía.
    if (data.tipo === 'upgrade_webpay' && data.url && data.token) {
      const form  = document.createElement('form')
      form.method = 'POST'
      form.action = data.url
      const input = document.createElement('input')
      input.type  = 'hidden'
      input.name  = 'token_ws'
      input.value = data.token
      form.appendChild(input)
      document.body.appendChild(form)
      form.submit()
      return
    }
    if (data.tipo === 'upgrade') {
      toast.success(data.cobrado > 0
        ? `Plan mejorado. Se cobró ${clp(data.cobrado)} por los días restantes.`
        : 'Plan mejorado correctamente.')
    } else if (data.tipo === 'downgrade') {
      toast.success(`Cambio programado para el ${data.aplica}.`)
    } else {
      toast.success('Plan actualizado.')
    }
    cerrarModal()
    await cargar()
  } else {
    if (data.codigo === 'SIN_SUSCRIPCION_ACTIVA') {
      toast.error('Tu suscripción no está activa. Actívala en Suscripción y pagos.')
    } else {
      toast.error(data.error || 'No se pudo cambiar el plan.')
    }
  }
  procesando.value = false
}

const cancelarProgramado = async () => {
  cancelando.value = true
  const res = await apiFetch('/api/empresa/cancelar-cambio-plan/', { method: 'POST' })
  if (res.ok) {
    toast.success('Se canceló el cambio de plan programado.')
    await cargar()
  } else {
    const e = await res.json().catch(() => ({}))
    toast.error(e.error || 'No se pudo cancelar el cambio.')
  }
  cancelando.value = false
}

onMounted(cargar)
</script>

<template>
  <div class="tab-content">
    <div v-if="cargando" class="loading">
      <div class="spinner"/>
    </div>

    <template v-else>
      <!-- Sin plan -->
      <div v-if="!planUso || !planUso.plan" class="card">
        <div class="card-body empty">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" class="empty-icon">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/>
          </svg>
          <p class="empty-title">Sin plan asignado</p>
          <p class="empty-desc">Esta empresa no tiene un plan de suscripción activo.</p>
        </div>
      </div>

      <template v-else>
        <!-- Info del plan -->
        <div class="plan-card">
          <div class="plan-badge">Plan activo</div>
          <h2 class="plan-nombre">{{ planUso.plan.nombre_display }}</h2>
          <p v-if="planUso.plan.precio_display" class="plan-precio">{{ planUso.plan.precio_display }}</p>
          <p v-if="planUso.plan.descripcion" class="plan-desc">{{ planUso.plan.descripcion }}</p>
        </div>

        <!-- Banner de cambio de plan programado (downgrade diferido) -->
        <div v-if="planUso.cambio_programado" class="banner-prog">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" class="banner-prog-icon">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <div class="banner-prog-text">
            <strong>Cambio de plan programado</strong>
            <span>
              Cambiarás al plan <b>{{ planUso.cambio_programado.plan_nombre }}</b>
              el <b>{{ planUso.cambio_programado.aplica }}</b>.
              Conservas tu plan actual y sus beneficios hasta esa fecha.
            </span>
          </div>
          <button class="btn-cancelar-prog" @click="cancelarProgramado" :disabled="cancelando">
            {{ cancelando ? 'Cancelando...' : 'Cancelar' }}
          </button>
        </div>

        <!-- Uso de recursos -->
        <div class="card" v-if="planUso.uso">
          <div class="card-header">
            <h2 class="card-title">Uso del plan</h2>
            <p class="card-desc">Recursos utilizados del total disponible</p>
          </div>
          <div class="card-body">
            <div v-for="(dim, key) in planUso.uso" :key="key" class="dim-row">
              <div class="dim-top">
                <span class="dim-label">{{ dimLabel[key] || key }}</span>
                <span class="dim-values">{{ dim.actual }} / {{ dim.limite }}</span>
              </div>
              <div class="barra-track">
                <div class="barra-fill" :style="{ width: dim.pct + '%', background: colorBarra(dim.pct) }"/>
              </div>
              <p class="dim-pct">{{ dim.pct }}%</p>
            </div>
          </div>
        </div>
      </template>

      <!-- Planes disponibles -->
      <div class="card" v-if="planes.length">
        <div class="card-header">
          <h2 class="card-title">Planes disponibles</h2>
          <p class="card-desc">Sube de plan al instante o programa una baja para el fin de tu período</p>
        </div>
        <div class="card-body planes-grid">
          <div
            v-for="plan in planes"
            :key="plan.id"
            :class="['plan-option', { 'plan-actual': esPlanActual(plan) }]"
          >
            <div class="plan-option-top">
              <span v-if="esPlanActual(plan)" class="badge-actual">Tu plan actual</span>
              <h3 class="option-nombre">{{ plan.nombre_display }}</h3>
              <p class="option-precio">{{ plan.precio_display }}</p>
            </div>
            <ul class="option-limites">
              <li>
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                {{ plan.max_vehiculos }} vehículos
              </li>
              <li>
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                {{ plan.max_conductores }} conductores
              </li>
              <li>
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                {{ plan.max_usuarios }} usuarios
              </li>
            </ul>
            <template v-if="!esPlanActual(plan)">
              <button
                v-if="tipoCambio(plan) === 'upgrade'"
                class="btn-solicitar"
                @click="abrirModal(plan)"
              >
                Mejorar a este plan
              </button>
              <button
                v-else
                class="btn-bajar"
                @click="abrirModal(plan)"
              >
                Cambiar a este plan
              </button>
            </template>
            <div v-else class="btn-actual-label">Plan activo</div>
          </div>
        </div>
      </div>

      <!-- Historial -->
      <div class="card" v-if="historial.length">
        <div class="card-header">
          <h2 class="card-title">Historial de cambios de plan</h2>
          <p class="card-desc">Últimas modificaciones al plan de suscripción</p>
        </div>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th class="th">Fecha</th>
                <th class="th">Plan anterior</th>
                <th class="th">Plan nuevo</th>
                <th class="th">Motivo</th>
                <th class="th">Por</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(c, i) in historial" :key="i" class="tr">
                <td class="td td-mono">{{ c.fecha }}</td>
                <td class="td">{{ c.plan_antes }}</td>
                <td class="td td-fw">{{ c.plan_despues }}</td>
                <td class="td td-muted">{{ c.motivo }}</td>
                <td class="td td-muted">{{ c.cambiado_por }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <!-- Modal de confirmación -->
    <Teleport to="body">
      <div v-if="modalPlan" class="modal-overlay" @click.self="cerrarModal">
        <div class="modal">
          <div class="modal-header">
            <h3 class="modal-title">
              {{ modalTipo === 'upgrade' ? 'Mejorar de plan'
                 : modalTipo === 'downgrade' ? 'Cambiar a un plan inferior'
                 : 'Cambiar de plan' }}
            </h3>
            <button class="modal-close" @click="cerrarModal">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>
          <div class="modal-body">
            <p class="modal-text">
              Cambiarás al plan
              <strong>{{ modalPlan.nombre_display }}</strong>
              ({{ modalPlan.precio_display }}).
            </p>

            <!-- UPGRADE: proración -->
            <div v-if="modalTipo === 'upgrade'" class="modal-info modal-info--ok">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" class="info-icon">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M5 13l4 4L19 7"/>
              </svg>
              <p>
                El cambio es <b>inmediato</b>. Se cobrará solo la diferencia prorrateada
                <b v-if="modalProracion > 0">(aprox. {{ clp(modalProracion) }})</b>
                por los {{ planUso?.suscripcion?.dias_restantes }} días que quedan del período
                —con tu tarjeta guardada o, si no tienes, por Webpay.
                El precio completo del nuevo plan recién se cobra en la próxima renovación.
              </p>
            </div>

            <!-- DOWNGRADE: diferido -->
            <div v-else-if="modalTipo === 'downgrade'" class="modal-info modal-info--warn">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" class="info-icon">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <p>
                El cambio se aplicará el <b>{{ planUso?.suscripcion?.fecha_fin }}</b>
                (fin de tu período actual). Hasta entonces conservas tu plan actual y sus beneficios,
                sin perder nada de lo que ya pagaste.
              </p>
            </div>

            <!-- LATERAL -->
            <div v-else class="modal-info">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" class="info-icon">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <p>El cambio se aplica de inmediato. Ambos planes tienen el mismo precio.</p>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" @click="cerrarModal">Cancelar</button>
            <button class="btn-confirm" @click="confirmarCambio" :disabled="procesando">
              {{ procesando ? 'Procesando...'
                 : modalTipo === 'upgrade' ? 'Pagar diferencia y mejorar'
                 : modalTipo === 'downgrade' ? 'Programar cambio'
                 : 'Cambiar plan' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.tab-content { display: flex; flex-direction: column; gap: 1.25rem; }

.loading { display: flex; justify-content: center; padding: 3rem; }
.spinner {
  width: 32px; height: 32px;
  border: 3px solid #E5E7EB;
  border-top-color: var(--color-accent, #4F46E5);
  border-radius: 50%;
  animation: spin 0.75s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.card {
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: var(--radius-card, 12px);
  overflow: hidden;
}
.card-header { padding: 1.25rem 1.5rem 1rem; border-bottom: 1px solid #F3F4F6; }
.card-title  { font-size: 1rem; font-weight: 600; color: #111827; margin: 0 0 0.25rem; }
.card-desc   { font-size: 0.8125rem; color: #6B7280; margin: 0; }
.card-body   { padding: 1.25rem 1.5rem; display: flex; flex-direction: column; gap: 1.25rem; }

.plan-card {
  background: linear-gradient(135deg, var(--sidebar-from, #4F46E5) 0%, var(--sidebar-to, #7C3AED) 100%);
  border-radius: var(--radius-card, 12px);
  padding: 1.5rem;
}
.plan-badge  {
  display: inline-block; padding: 0.25rem 0.625rem;
  background: rgba(255,255,255,0.2); color: #fff;
  font-size: 0.75rem; font-weight: 600; border-radius: 999px; margin-bottom: 0.75rem;
}
.plan-nombre { font-size: 1.5rem; font-weight: 700; color: #fff; margin: 0 0 0.25rem; }
.plan-precio { font-size: 0.875rem; color: rgba(255,255,255,0.75); margin: 0 0 0.25rem; }
.plan-desc   { font-size: 0.8125rem; color: rgba(255,255,255,0.6); margin: 0; }

.empty { display: flex; flex-direction: column; align-items: center; text-align: center; padding: 3rem 1.5rem; }
.empty-icon  { width: 48px; height: 48px; color: #D1D5DB; margin-bottom: 1rem; }
.empty-title { font-size: 1rem; font-weight: 600; color: #374151; margin: 0 0 0.25rem; }
.empty-desc  { font-size: 0.875rem; color: #9CA3AF; margin: 0; }

.dim-row    { display: flex; flex-direction: column; gap: 0.375rem; }
.dim-top    { display: flex; justify-content: space-between; align-items: center; }
.dim-label  { font-size: 0.875rem; font-weight: 500; color: #374151; }
.dim-values { font-size: 0.8125rem; color: #6B7280; }
.dim-pct    { font-size: 0.75rem; color: #9CA3AF; text-align: right; margin: 0; }
.barra-track { height: 8px; background: #F3F4F6; border-radius: 999px; overflow: hidden; }
.barra-fill  { height: 100%; border-radius: 999px; transition: width 0.5s ease; }

/* ── Planes disponibles ── */
.planes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
}
.plan-option {
  border: 2px solid #E5E7EB;
  border-radius: 10px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
  transition: border-color 0.15s;
}
.plan-option:hover       { border-color: #9CA3AF; }
.plan-option.plan-actual { border-color: var(--color-accent, #4F46E5); background: #FAFBFF; }

.plan-option-top { display: flex; flex-direction: column; gap: 0.25rem; }
.badge-actual {
  display: inline-block; padding: 0.2rem 0.5rem;
  background: var(--color-accent, #4F46E5); color: #fff;
  font-size: 0.7rem; font-weight: 600; border-radius: 999px; width: fit-content;
  margin-bottom: 0.25rem;
}
.option-nombre { font-size: 0.9375rem; font-weight: 700; color: #111827; margin: 0; }
.option-precio { font-size: 0.8125rem; color: #6B7280; margin: 0; }

.option-limites { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.375rem; }
.option-limites li {
  display: flex; align-items: center; gap: 0.375rem;
  font-size: 0.8rem; color: #374151;
}
.option-limites svg { width: 14px; height: 14px; color: #10B981; flex-shrink: 0; }

.btn-solicitar {
  margin-top: auto;
  padding: 0.5rem 0.75rem;
  background: var(--color-accent, #4F46E5);
  color: #fff; border: none;
  border-radius: var(--radius-btn, 8px);
  font-size: 0.8125rem; font-weight: 500;
  cursor: pointer; transition: opacity 0.15s;
}
.btn-solicitar:hover { opacity: 0.88; }
.btn-bajar {
  margin-top: auto;
  padding: 0.5rem 0.75rem;
  background: #fff;
  color: #B45309; border: 1.5px solid #FCD34D;
  border-radius: var(--radius-btn, 8px);
  font-size: 0.8125rem; font-weight: 500;
  cursor: pointer; transition: background 0.15s;
}
.btn-bajar:hover { background: #FFFBEB; }
.btn-actual-label {
  margin-top: auto;
  text-align: center; font-size: 0.8125rem;
  color: var(--color-accent, #4F46E5); font-weight: 500;
}

/* ── Banner de cambio programado ── */
.banner-prog {
  display: flex; align-items: center; gap: 0.875rem;
  background: #FFFBEB; border: 1px solid #FDE68A;
  border-radius: var(--radius-card, 12px); padding: 1rem 1.25rem;
}
.banner-prog-icon { width: 24px; height: 24px; color: #D97706; flex-shrink: 0; }
.banner-prog-text { display: flex; flex-direction: column; gap: 0.15rem; flex: 1; min-width: 0; }
.banner-prog-text strong { font-size: 0.875rem; color: #92400E; }
.banner-prog-text span   { font-size: 0.8125rem; color: #B45309; line-height: 1.4; }
.btn-cancelar-prog {
  flex-shrink: 0; padding: 0.45rem 0.875rem;
  background: #fff; border: 1.5px solid #FCD34D; border-radius: var(--radius-btn, 8px);
  font-size: 0.8125rem; font-weight: 600; color: #B45309; cursor: pointer;
  transition: background 0.15s;
}
.btn-cancelar-prog:hover    { background: #FEF3C7; }
.btn-cancelar-prog:disabled { opacity: 0.6; cursor: not-allowed; }

/* Variantes del recuadro informativo del modal */
.modal-info--ok   { background: #ECFDF5; border-color: #A7F3D0; }
.modal-info--ok .info-icon { color: #059669; }
.modal-info--ok p { color: #065F46; }
.modal-info--warn { background: #FFFBEB; border-color: #FDE68A; }
.modal-info--warn .info-icon { color: #D97706; }
.modal-info--warn p { color: #92400E; }

/* ── Historial ── */
.table-wrap { overflow-x: auto; }
.table { width: 100%; border-collapse: collapse; }
.th {
  padding: 0.75rem 1.25rem; text-align: left;
  font-size: 0.75rem; font-weight: 600; color: #6B7280;
  text-transform: uppercase; letter-spacing: 0.05em;
  background: #F9FAFB; border-bottom: 1px solid #E5E7EB; white-space: nowrap;
}
.tr { border-bottom: 1px solid #F3F4F6; }
.tr:last-child { border-bottom: none; }
.td { padding: 0.875rem 1.25rem; font-size: 0.875rem; color: #374151; }
.td-mono { font-family: monospace; font-size: 0.8125rem; white-space: nowrap; }
.td-fw   { font-weight: 500; }
.td-muted { color: #9CA3AF; }

/* ── Modal ── */
.modal-overlay {
  position: fixed; inset: 0; z-index: 999;
  background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center;
  padding: 1rem;
}
.modal {
  background: #fff; border-radius: 16px;
  width: 100%; max-width: 420px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
  overflow: hidden;
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1.25rem 1.5rem; border-bottom: 1px solid #F3F4F6;
}
.modal-title { font-size: 1rem; font-weight: 600; color: #111827; margin: 0; }
.modal-close {
  width: 28px; height: 28px; border: none; background: #F3F4F6;
  border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center;
}
.modal-close svg { width: 15px; height: 15px; color: #6B7280; }
.modal-body { padding: 1.25rem 1.5rem; display: flex; flex-direction: column; gap: 0.875rem; }
.modal-text { font-size: 0.9375rem; color: #374151; margin: 0; line-height: 1.5; }
.modal-info {
  display: flex; gap: 0.625rem; align-items: flex-start;
  background: #F0F9FF; border: 1px solid #BAE6FD;
  border-radius: 8px; padding: 0.875rem;
}
.info-icon { width: 18px; height: 18px; color: #0369A1; flex-shrink: 0; margin-top: 1px; }
.modal-info p { font-size: 0.8125rem; color: #0C4A6E; margin: 0; line-height: 1.5; }
.modal-footer {
  display: flex; justify-content: flex-end; gap: 0.75rem;
  padding: 1rem 1.5rem; border-top: 1px solid #F3F4F6;
}
.btn-cancel {
  padding: 0.5rem 1rem; background: #fff;
  border: 1px solid #D1D5DB; border-radius: var(--radius-btn, 8px);
  font-size: 0.875rem; font-weight: 500; color: #374151; cursor: pointer;
}
.btn-cancel:hover { background: #F9FAFB; }
.btn-confirm {
  padding: 0.5rem 1.25rem;
  background: var(--color-accent, #4F46E5); color: #fff;
  border: none; border-radius: var(--radius-btn, 8px);
  font-size: 0.875rem; font-weight: 500; cursor: pointer; transition: opacity 0.15s;
}
.btn-confirm:hover    { opacity: 0.88; }
.btn-confirm:disabled { opacity: 0.55; cursor: not-allowed; }
</style>
