<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiFetch } from '../../utils/api.js'

const router = useRouter()
const route  = useRoute()

// ── estado general ──────────────────────────────────────────────────
const cargando      = ref(true)
const procesando    = ref(false)
const redirigiendo  = ref(false)
const error         = ref('')
const exito         = ref('')   // mensaje de éxito tras cobro automático

// ── datos del plan y suscripción ────────────────────────────────────
const plan        = ref(null)
const suscripcion = ref(null)
const ciclo       = 'mensual'   // solo facturación mensual

// ── tarjeta guardada ────────────────────────────────────────────────
const tarjeta       = ref(null)   // { card_type, last_4, created_at } o null
const inscribiendo  = ref(false)
const eliminando    = ref(false)
const confirmarElim = ref(false)

onMounted(async () => {
  // Mensaje tras retorno de OneClick
  const ins = route.query.inscripcion
  if (ins === 'ok')             exito.value = '✅ Tarjeta guardada correctamente. Se usará para cobros automáticos.'
  if (ins === 'rechazada')      error.value = 'La inscripción de tarjeta fue rechazada por Transbank.'
  if (ins === 'error')          error.value = 'Ocurrió un error al guardar la tarjeta. Intenta nuevamente.'
  if (ins === 'sin_token')      error.value = 'Inscripción cancelada o sin token.'
  if (ins === 'error_empresa')  error.value = 'No se pudo identificar la empresa en la inscripción.'

  try {
    const [resPlan, resSus, resTarjeta] = await Promise.all([
      apiFetch('/api/empresa/plan-uso/'),
      apiFetch('/api/empresa/suscripcion/'),
      apiFetch('/api/empresa/tarjeta/'),
    ])

    if (resPlan.ok) {
      const d = await resPlan.json()
      plan.value = d.plan || null
    }
    if (resSus.ok) {
      const d = await resSus.json()
      suscripcion.value = d.suscripcion || null
    }
    if (resTarjeta.ok) {
      const d = await resTarjeta.json()
      tarjeta.value = d.tarjeta || null
    }
  } catch {}
  finally { cargando.value = false }
})

// ── computados de estado ────────────────────────────────────────────
const diasRestantes = computed(() => suscripcion.value?.dias_para_vencer ?? null)

const puedeNovoPago = computed(() => {
  const sus = suscripcion.value
  if (!sus) return true
  if (sus.estado === 'activa') {
    const d = sus.dias_para_vencer
    return d === null || d <= 7
  }
  return true  // trial, gracia, suspendida, cancelada → puede pagar
})

const proxFechaStr = computed(() => {
  if (!suscripcion.value?.fecha_fin_periodo) return null
  return suscripcion.value.fecha_fin_periodo
})

const diasHastaRenovacion = computed(() => {
  const d = diasRestantes.value
  if (d === null) return null
  return d - 7   // días que faltan para poder pagar manualmente
})

// ── computados de precio ────────────────────────────────────────────
const precio = computed(() => {
  if (!plan.value) return null
  const v = plan.value.precio_mensual
  return v ? parseInt(v) : null
})
const precioFormato = computed(() => precio.value ? formatCLP(precio.value) : null)

const badgeSuscripcion = computed(() => {
  const e = suscripcion.value?.estado
  const map = {
    trial:      { label: 'Trial',              cls: 'badge-trial' },
    activa:     { label: 'Activa',             cls: 'badge-activa' },
    gracia:     { label: 'Período de gracia',  cls: 'badge-gracia' },
    suspendida: { label: 'Suspendida',         cls: 'badge-suspendida' },
    cancelada:  { label: 'Cancelada',          cls: 'badge-cancelada' },
  }
  return map[e] || null
})

function formatCLP(n) {
  return '$' + n.toLocaleString('es-CL')
}

// ── Pago con nueva tarjeta (Webpay Plus) ────────────────────────────
async function pagarConWebpay() {
  if (!plan.value || !precio.value) return
  procesando.value = true
  error.value = ''
  try {
    const res  = await apiFetch('/api/pago/iniciar/', {
      method: 'POST',
      body: { plan_id: plan.value.id, ciclo: ciclo, usar_tarjeta: false },
    })
    const data = await res.json()
    if (!res.ok) {
      error.value = data.error || 'Error al iniciar el pago.'
      return
    }
    if (!data.url || !data.token) {
      error.value = 'Transbank no devolvió datos válidos.'
      return
    }
    redirigiendo.value = true
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
  } catch {
    error.value = 'Error de conexión. Intenta nuevamente.'
  } finally {
    if (!redirigiendo.value) procesando.value = false
  }
}

// ── Pago con tarjeta guardada (OneClick) ────────────────────────────
async function pagarConTarjeta() {
  if (!plan.value || !precio.value || !tarjeta.value) return
  procesando.value = true
  error.value = ''
  exito.value = ''
  try {
    const res  = await apiFetch('/api/pago/iniciar/', {
      method: 'POST',
      body: { plan_id: plan.value.id, ciclo: ciclo, usar_tarjeta: true },
    })
    const data = await res.json()
    if (!res.ok) {
      error.value = data.error || 'El cobro fue rechazado.'
      return
    }
    // Pago exitoso sin redirección
    exito.value = `✅ Pago de ${formatCLP(data.monto)} procesado con tu tarjeta guardada. Próximo cobro: ${data.nueva_fecha_fin}.`
    // Recargar datos
    const resSus = await apiFetch('/api/empresa/suscripcion/')
    if (resSus.ok) {
      const d = await resSus.json()
      suscripcion.value = d.suscripcion || null
    }
  } catch {
    error.value = 'Error de conexión. Intenta nuevamente.'
  } finally {
    procesando.value = false
  }
}

// ── Inscribir tarjeta (OneClick) ─────────────────────────────────────
async function inscribirTarjeta() {
  inscribiendo.value = true
  error.value = ''
  try {
    const res  = await apiFetch('/api/empresa/tarjeta/inscribir/', { method: 'POST', body: {} })
    const data = await res.json()
    if (!res.ok) {
      error.value = data.error || 'Error al iniciar inscripción.'
      return
    }
    // Redirigir a OneClick con form POST
    const form  = document.createElement('form')
    form.method = 'POST'
    form.action = data.url
    const input = document.createElement('input')
    input.type  = 'hidden'
    input.name  = 'TBK_TOKEN'
    input.value = data.token
    form.appendChild(input)
    document.body.appendChild(form)
    form.submit()
  } catch {
    error.value = 'Error de conexión. Intenta nuevamente.'
    inscribiendo.value = false
  }
}

// ── Eliminar tarjeta ────────────────────────────────────────────────
async function eliminarTarjeta() {
  eliminando.value = true
  error.value = ''
  try {
    const res = await apiFetch('/api/empresa/tarjeta/eliminar/', { method: 'DELETE' })
    if (res.ok) {
      tarjeta.value    = null
      confirmarElim.value = false
      exito.value = 'Tarjeta eliminada correctamente.'
    } else {
      const d = await res.json()
      error.value = d.error || 'Error al eliminar la tarjeta.'
    }
  } catch {
    error.value = 'Error de conexión.'
  } finally {
    eliminando.value = false
  }
}
</script>

<template>
  <div class="pago-page">

    <!-- Encabezado -->
    <div class="pago-header">
      <div>
        <h1 class="pago-title">Suscripción y Pagos</h1>
        <p class="pago-sub">Gestiona el plan y los pagos de tu empresa</p>
      </div>
      <button class="btn-historial" @click="router.push('/empresa/pagos')">
        Ver historial de pagos
      </button>
    </div>

    <!-- Cargando -->
    <div v-if="cargando" class="estado-msg">Cargando información…</div>

    <!-- Sin plan -->
    <div v-else-if="!plan" class="sin-plan">
      <div class="sin-plan-icon">📋</div>
      <h2>Sin plan asignado</h2>
      <p>Tu cuenta aún no tiene un plan. Contacta al administrador del sistema.</p>
    </div>

    <template v-else>

      <!-- ── Tarjeta del plan ─────────────────────────────────────── -->
      <div class="plan-card">
        <div class="plan-card-header">
          <div>
            <p class="plan-etiqueta">Tu plan actual</p>
            <h2 class="plan-nombre">{{ plan.nombre_display || plan.nombre }}</h2>
            <p v-if="plan.descripcion" class="plan-desc">{{ plan.descripcion }}</p>
          </div>
          <div class="plan-right">
            <span v-if="badgeSuscripcion" :class="['badge', badgeSuscripcion.cls]">
              {{ badgeSuscripcion.label }}
            </span>
            <div v-if="proxFechaStr" class="plan-vence">
              Vence el {{ proxFechaStr }}
              <span v-if="diasRestantes !== null" class="dias-tag"
                    :class="{ 'dias-urgente': diasRestantes <= 7, 'dias-ok': diasRestantes > 7 }">
                {{ diasRestantes > 0 ? `${diasRestantes} días` : 'Vencida' }}
              </span>
            </div>
          </div>
        </div>
        <div class="plan-limites">
          <div class="limite-item">
            <span class="limite-val">{{ plan.max_vehiculos }}</span>
            <span class="limite-lbl">Vehículos</span>
          </div>
          <div class="limite-sep"/>
          <div class="limite-item">
            <span class="limite-val">{{ plan.max_conductores }}</span>
            <span class="limite-lbl">Conductores</span>
          </div>
          <div class="limite-sep"/>
          <div class="limite-item">
            <span class="limite-val">{{ plan.max_usuarios }}</span>
            <span class="limite-lbl">Usuarios</span>
          </div>
        </div>
      </div>

      <!-- ── Mensajes ─────────────────────────────────────────────── -->
      <div v-if="error" class="error-box">{{ error }}</div>
      <div v-if="exito" class="exito-box">{{ exito }}</div>

      <!-- ── Sección tarjeta guardada ────────────────────────────── -->
      <div class="seccion">
        <h3 class="seccion-title">Cobro automático</h3>

        <!-- Tarjeta existente -->
        <div v-if="tarjeta" class="tarjeta-card">
          <div class="tarjeta-info">
            <div class="tarjeta-icono">💳</div>
            <div>
              <p class="tarjeta-tipo">{{ tarjeta.card_type || 'Tarjeta' }} terminada en <strong>****{{ tarjeta.last_4 }}</strong></p>
              <p class="tarjeta-fecha">Inscrita el {{ tarjeta.created_at }}</p>
              <p class="tarjeta-aviso">
                <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                Se cobrará automáticamente 3 días antes del vencimiento.
              </p>
            </div>
          </div>
          <div class="tarjeta-acciones">
            <button v-if="!confirmarElim" class="btn-eliminar-tarjeta" @click="confirmarElim = true">
              Eliminar tarjeta
            </button>
            <template v-else>
              <span class="confirmar-txt">¿Eliminar?</span>
              <button class="btn-confirmar-si" :disabled="eliminando" @click="eliminarTarjeta">
                {{ eliminando ? 'Eliminando…' : 'Sí, eliminar' }}
              </button>
              <button class="btn-confirmar-no" @click="confirmarElim = false">Cancelar</button>
            </template>
          </div>
        </div>

        <!-- Sin tarjeta -->
        <div v-else class="sin-tarjeta">
          <div class="sin-tarjeta-texto">
            <p class="sin-tarjeta-titulo">Sin tarjeta para cobro automático</p>
            <p class="sin-tarjeta-desc">
              Guarda una tarjeta y el sistema cobrará automáticamente 3 días antes del vencimiento,
              sin que necesites hacer nada.
            </p>
          </div>
          <button class="btn-inscribir" :disabled="inscribiendo" @click="inscribirTarjeta">
            <span v-if="inscribiendo">Conectando…</span>
            <span v-else>
              <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="vertical-align:-2px;margin-right:4px">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
              </svg>
              Guardar tarjeta con OneClick
            </span>
          </button>
        </div>
      </div>

      <!-- ── Bloqueo: suscripción activa con tiempo restante ─────── -->
      <div v-if="!puedeNovoPago" class="bloqueo-box">
        <div class="bloqueo-icon">✅</div>
        <div>
          <p class="bloqueo-titulo">Tu suscripción está activa</p>
          <p class="bloqueo-desc">
            Próximo pago el <strong>{{ proxFechaStr }}</strong>
            (en <strong>{{ diasRestantes }} días</strong>).
          </p>
          <p v-if="diasHastaRenovacion > 0" class="bloqueo-desc">
            Podrás renovar manualmente a partir de <strong>7 días antes</strong> del vencimiento
            (en {{ diasHastaRenovacion }} días).
          </p>
          <p v-if="tarjeta" class="bloqueo-auto-nota">
            💳 Se cobrará automáticamente con tu tarjeta <strong>{{ tarjeta.card_type }} ****{{ tarjeta.last_4 }}</strong>.
          </p>
        </div>
      </div>

      <!-- ── Formulario de pago (solo cuando se puede pagar) ──────── -->
      <template v-else>

        <!-- Resumen del cobro -->
        <div v-if="precioFormato" class="resumen-cobro">
          <div class="resumen-row">
            <span>Plan {{ plan.nombre_display || plan.nombre }}</span>
            <span>{{ precioFormato }}</span>
          </div>
          <div class="resumen-row resumen-ciclo">
            <span>Ciclo</span>
            <span class="cap">{{ ciclo }}</span>
          </div>
          <div class="resumen-divider"/>
          <div class="resumen-row resumen-total">
            <span>Total a pagar</span>
            <span>{{ precioFormato }}</span>
          </div>
        </div>
        <div v-else class="aviso-sin-precio">
          El plan no tiene precio para el ciclo seleccionado. Contacta al administrador.
        </div>

        <!-- Botones de pago -->
        <div v-if="precioFormato" class="pago-footer">

          <!-- Opción 1: tarjeta guardada (OneClick) -->
          <button
            v-if="tarjeta"
            class="btn-pagar btn-tarjeta-guardada"
            :disabled="procesando || redirigiendo"
            @click="pagarConTarjeta"
          >
            <span v-if="procesando">Procesando cobro…</span>
            <span v-else>
              💳 Pagar {{ precioFormato }} con tarjeta guardada
              <small class="btn-sub">({{ tarjeta.card_type }} ****{{ tarjeta.last_4 }})</small>
            </span>
          </button>

          <!-- Opción 2: Webpay Plus (nueva tarjeta) -->
          <button
            :class="['btn-pagar', tarjeta ? 'btn-webpay-secundario' : '']"
            :disabled="procesando || redirigiendo"
            @click="pagarConWebpay"
          >
            <span v-if="redirigiendo">Redirigiendo a Transbank…</span>
            <span v-else-if="procesando">Procesando…</span>
            <span v-else>
              {{ tarjeta ? 'Pagar con otra tarjeta (Webpay)' : `Pagar ${precioFormato} con Webpay` }}
            </span>
          </button>

          <p class="transbank-note">
            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
            </svg>
            Pago seguro mediante Webpay de Transbank
          </p>
        </div>

      </template>

    </template>

    <!-- Overlay redirección -->
    <div v-if="redirigiendo" class="redirect-overlay">
      <div class="redirect-box">
        <div class="spinner"/>
        <p>Redirigiendo a Webpay de Transbank…</p>
      </div>
    </div>

  </div>
</template>

<style scoped>
.pago-page  { padding: 2rem 2.5rem; max-width: 720px; margin: 0 auto; }

/* Encabezado */
.pago-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 1.75rem; flex-wrap: wrap; gap: 1rem;
}
.pago-title { font-size: 1.5rem; font-weight: 700; color: #111827; margin: 0 0 0.2rem; }
.pago-sub   { font-size: 0.875rem; color: #6B7280; margin: 0; }
.btn-historial {
  padding: 0.45rem 1rem; background: #fff; border: 1px solid #E5E7EB;
  border-radius: 8px; font-size: 0.8125rem; color: #374151; cursor: pointer;
  font-family: inherit; white-space: nowrap;
}
.btn-historial:hover { background: #F9FAFB; }

/* Sin plan */
.sin-plan { text-align: center; padding: 3rem 1rem; }
.sin-plan-icon { font-size: 3rem; margin-bottom: 1rem; }
.sin-plan h2   { font-size: 1.25rem; font-weight: 700; color: #111827; margin: 0 0 0.5rem; }
.sin-plan p    { font-size: 0.875rem; color: #6B7280; max-width: 360px; margin: 0 auto; line-height: 1.5; }

.estado-msg { color: #6B7280; font-size: 0.875rem; padding: 2rem 0; }

/* Plan card */
.plan-card {
  background: #fff; border: 1px solid #E5E7EB; border-radius: 14px;
  padding: 1.5rem; margin-bottom: 1.5rem;
}
.plan-card-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 1rem; margin-bottom: 1.25rem; flex-wrap: wrap;
}
.plan-etiqueta { font-size: 0.75rem; font-weight: 600; color: #6B7280; text-transform: uppercase; letter-spacing: .06em; margin: 0 0 .25rem; }
.plan-nombre   { font-size: 1.375rem; font-weight: 800; color: #111827; margin: 0 0 .3rem; text-transform: capitalize; }
.plan-desc     { font-size: .8125rem; color: #6B7280; margin: 0; }
.plan-right    { display: flex; flex-direction: column; align-items: flex-end; gap: .4rem; }
.plan-vence    { font-size: .8rem; color: #6B7280; display: flex; align-items: center; gap: .4rem; flex-wrap: wrap; }
.dias-tag      { font-size: .75rem; font-weight: 600; padding: 2px 8px; border-radius: 99px; }
.dias-urgente  { background: #FEE2E2; color: #991B1B; }
.dias-ok       { background: #D1FAE5; color: #065F46; }
.plan-limites  { display: flex; gap: 0; border-top: 1px solid #F3F4F6; padding-top: 1rem; }
.limite-item   { flex: 1; text-align: center; }
.limite-val    { display: block; font-size: 1.25rem; font-weight: 700; color: #4F46E5; }
.limite-lbl    { display: block; font-size: .75rem; color: #6B7280; margin-top: 2px; }
.limite-sep    { width: 1px; background: #F3F4F6; margin: 0 .5rem; }

/* Badges */
.badge            { font-size: .75rem; font-weight: 600; padding: 3px 10px; border-radius: 99px; white-space: nowrap; }
.badge-trial      { background: #DBEAFE; color: #1D4ED8; }
.badge-activa     { background: #D1FAE5; color: #065F46; }
.badge-gracia     { background: #FEF3C7; color: #92400E; }
.badge-suspendida { background: #FEE2E2; color: #991B1B; }
.badge-cancelada  { background: #F3F4F6; color: #6B7280; }

/* Mensajes */
.error-box {
  background: #FEF2F2; border: 1px solid #FECACA; color: #B91C1C;
  padding: .75rem 1rem; border-radius: 8px; margin-bottom: 1rem; font-size: .875rem;
}
.exito-box {
  background: #F0FDF4; border: 1px solid #86EFAC; color: #166534;
  padding: .75rem 1rem; border-radius: 8px; margin-bottom: 1rem; font-size: .875rem;
}

/* Sección */
.seccion       { margin-bottom: 1.5rem; }
.seccion-title { font-size: .9375rem; font-weight: 600; color: #374151; margin: 0 0 .75rem; }

/* Tarjeta guardada */
.tarjeta-card {
  background: #F0FDF4; border: 1px solid #86EFAC; border-radius: 12px;
  padding: 1rem 1.25rem; display: flex; align-items: flex-start;
  justify-content: space-between; gap: 1rem; flex-wrap: wrap;
}
.tarjeta-info { display: flex; align-items: flex-start; gap: .75rem; }
.tarjeta-icono { font-size: 1.75rem; flex-shrink: 0; margin-top: 2px; }
.tarjeta-tipo  { font-size: .9375rem; font-weight: 600; color: #166534; margin: 0 0 .2rem; }
.tarjeta-fecha { font-size: .8rem; color: #4B5563; margin: 0 0 .3rem; }
.tarjeta-aviso { font-size: .8rem; color: #4B5563; margin: 0; display: flex; align-items: center; gap: .3rem; }
.tarjeta-acciones { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }
.btn-eliminar-tarjeta {
  padding: .35rem .8rem; border: 1px solid #FCA5A5; border-radius: 6px;
  background: #fff; color: #B91C1C; font-size: .8rem; cursor: pointer; font-family: inherit;
}
.btn-eliminar-tarjeta:hover { background: #FEF2F2; }
.confirmar-txt  { font-size: .8rem; color: #374151; }
.btn-confirmar-si {
  padding: .35rem .75rem; border: none; border-radius: 6px;
  background: #DC2626; color: #fff; font-size: .8rem; cursor: pointer; font-family: inherit;
}
.btn-confirmar-si:disabled { opacity: .6; cursor: not-allowed; }
.btn-confirmar-no {
  padding: .35rem .75rem; border: 1px solid #E5E7EB; border-radius: 6px;
  background: #fff; color: #374151; font-size: .8rem; cursor: pointer; font-family: inherit;
}

/* Sin tarjeta */
.sin-tarjeta {
  background: #F9FAFB; border: 1px dashed #D1D5DB; border-radius: 12px;
  padding: 1.25rem; display: flex; align-items: center;
  justify-content: space-between; gap: 1rem; flex-wrap: wrap;
}
.sin-tarjeta-titulo { font-size: .9375rem; font-weight: 600; color: #374151; margin: 0 0 .25rem; }
.sin-tarjeta-desc   { font-size: .8125rem; color: #6B7280; margin: 0; line-height: 1.4; max-width: 360px; }
.btn-inscribir {
  padding: .6rem 1.25rem; background: #4F46E5; color: #fff; border: none;
  border-radius: 8px; font-size: .875rem; font-weight: 600; cursor: pointer;
  font-family: inherit; white-space: nowrap; flex-shrink: 0; transition: background .15s;
}
.btn-inscribir:hover:not(:disabled) { background: #4338CA; }
.btn-inscribir:disabled { opacity: .5; cursor: not-allowed; }

/* Bloqueo */
.bloqueo-box {
  background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 12px;
  padding: 1.25rem 1.5rem; display: flex; gap: 1rem;
  align-items: flex-start; margin-bottom: 1.5rem;
}
.bloqueo-icon  { font-size: 1.5rem; flex-shrink: 0; }
.bloqueo-titulo { font-size: 1rem; font-weight: 700; color: #065F46; margin: 0 0 .3rem; }
.bloqueo-desc   { font-size: .875rem; color: #374151; margin: 0 0 .3rem; }
.bloqueo-auto-nota { font-size: .8rem; color: #065F46; margin: .5rem 0 0; }

/* Ciclo tabs */
.ciclo-tabs { display: flex; gap: .75rem; flex-wrap: wrap; }
.ciclo-btn  {
  flex: 1; min-width: 200px; display: flex; align-items: center; justify-content: space-between;
  padding: 1rem 1.25rem; border-radius: 12px; border: 2px solid #E5E7EB;
  background: #fff; cursor: pointer; font-family: inherit; text-align: left;
}
.ciclo-btn:hover  { border-color: #A5B4FC; }
.ciclo-btn.active { border-color: #4F46E5; background: #EEF2FF; }
.ciclo-btn-inner  { display: flex; flex-direction: column; gap: .2rem; }
.ciclo-nombre     { font-size: .9375rem; font-weight: 600; color: #111827; display: flex; align-items: center; gap: .4rem; }
.ciclo-precio     { font-size: .8125rem; color: #6B7280; }
.sin-precio       { color: #9CA3AF; font-style: italic; }
.ciclo-check      {
  width: 22px; height: 22px; border-radius: 50%; background: #4F46E5; color: #fff;
  font-size: .75rem; display: flex; align-items: center; justify-content: center;
  font-weight: 700; flex-shrink: 0;
}
.ahorro-badge {
  background: #D1FAE5; color: #065F46; font-size: .7rem; font-weight: 600;
  padding: 1px 7px; border-radius: 99px;
}

/* Resumen */
.resumen-cobro {
  background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 12px;
  padding: 1.25rem; margin-bottom: 1.5rem;
}
.resumen-row     { display: flex; justify-content: space-between; font-size: .875rem; color: #374151; padding: .3rem 0; }
.resumen-divider { height: 1px; background: #E5E7EB; margin: .5rem 0; }
.resumen-total   { font-weight: 700; font-size: 1rem; color: #111827; }
.cap             { text-transform: capitalize; }
.aviso-sin-precio {
  background: #FFFBEB; border: 1px solid #FDE68A; color: #92400E;
  padding: .75rem 1rem; border-radius: 8px; font-size: .875rem; margin-bottom: 1.5rem;
}

/* Footer de pago */
.pago-footer { display: flex; flex-direction: column; gap: .75rem; }
.btn-pagar {
  padding: .875rem 2rem; background: #4F46E5; color: #fff; border: none;
  border-radius: 10px; font-size: 1rem; font-weight: 600; cursor: pointer;
  font-family: inherit; width: 100%; transition: background .15s; text-align: center;
}
.btn-pagar:hover:not(:disabled) { background: #4338CA; }
.btn-pagar:disabled { opacity: .5; cursor: not-allowed; }
.btn-tarjeta-guardada { background: #059669; }
.btn-tarjeta-guardada:hover:not(:disabled) { background: #047857; }
.btn-webpay-secundario {
  background: #fff; color: #374151; border: 1px solid #D1D5DB; font-size: .9375rem;
}
.btn-webpay-secundario:hover:not(:disabled) { background: #F9FAFB; }
.btn-sub { display: block; font-size: .8rem; font-weight: 400; opacity: .85; margin-top: 2px; }
.transbank-note {
  display: flex; align-items: center; gap: .4rem;
  font-size: .8rem; color: #9CA3AF; justify-content: center;
}

/* Overlay */
.redirect-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.45);
  display: flex; align-items: center; justify-content: center; z-index: 9999;
}
.redirect-box {
  background: #fff; border-radius: 12px; padding: 2.5rem 3rem;
  text-align: center; display: flex; flex-direction: column; align-items: center; gap: 1rem;
}
.redirect-box p { font-size: .9375rem; color: #374151; margin: 0; }
.spinner {
  width: 36px; height: 36px; border: 3px solid #E5E7EB;
  border-top-color: #4F46E5; border-radius: 50%; animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
