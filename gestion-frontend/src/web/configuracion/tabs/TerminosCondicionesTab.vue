<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../../../utils/api.js'

const tabInterna  = ref('terminos') // 'terminos' | 'pagos'
const guardando   = ref(false)
const cargando    = ref(true)
const ok          = ref(false)
const error       = ref('')

// Datos de términos
const terminos   = ref('')
const version    = ref('1.0')
const updatedAt  = ref('')

// Datos de pagos
const diasGracia     = ref(7)
const bloqueoAuto    = ref(true)
const mensajeBloqueo = ref('')
const ambienteTB     = ref('TEST')

async function cargar() {
  cargando.value = true
  try {
    const res  = await apiFetch('/api/admin/terminos/')
    if (!res.ok) return
    const data = await res.json()
    terminos.value      = data.terminos || ''
    version.value       = data.version || '1.0'
    updatedAt.value     = data.updated_at ? new Date(data.updated_at).toLocaleString('es-CL') : ''
    diasGracia.value    = data.dias_gracia ?? 7
    bloqueoAuto.value   = data.bloqueo_auto ?? true
    mensajeBloqueo.value = data.mensaje_bloqueo || ''
    ambienteTB.value    = data.ambiente_tb || 'TEST'
  } catch {}
  finally { cargando.value = false }
}

onMounted(cargar)

async function guardar() {
  guardando.value = true
  ok.value        = false
  error.value     = ''
  try {
    const body = tabInterna.value === 'terminos'
      ? { terminos: terminos.value, version: version.value }
      : { dias_gracia: diasGracia.value, bloqueo_auto: bloqueoAuto.value, mensaje_bloqueo: mensajeBloqueo.value }

    const res = await apiFetch('/api/admin/terminos/', { method: 'PUT', body })
    if (!res.ok) { error.value = 'Error al guardar.'; return }
    ok.value = true
    await cargar()
    setTimeout(() => ok.value = false, 3000)
  } catch {
    error.value = 'Error de conexión.'
  } finally {
    guardando.value = false
  }
}

// Tarjetas de prueba Transbank
const tarjetasPrueba = [
  { numero: '4051 8856 0044 6623', resultado: 'Aprobado',         cvc: '123', exp: 'Cualquier fecha futura' },
  { numero: '4051 8842 3993 7763', resultado: 'Rechazado',        cvc: '123', exp: 'Cualquier fecha futura' },
  { numero: '5186 0595 5959 0568', resultado: 'Aprobado (débito)', cvc: '123', exp: 'Cualquier fecha futura' },
]
</script>

<template>
  <div class="terminos-tab">
    <!-- Tabs internas -->
    <div class="sub-tabs">
      <button :class="['sub-tab', { active: tabInterna === 'terminos' }]" @click="tabInterna = 'terminos'">
        Términos y condiciones
      </button>
      <button :class="['sub-tab', { active: tabInterna === 'pagos' }]" @click="tabInterna = 'pagos'">
        Configuración de pagos
      </button>
    </div>

    <div v-if="cargando" class="cargando">Cargando…</div>

    <!-- TAB TÉRMINOS -->
    <template v-else-if="tabInterna === 'terminos'">
      <div class="campo">
        <label class="campo-label">Versión</label>
        <input v-model="version" class="campo-input campo-sm" placeholder="1.0" />
        <p v-if="updatedAt" class="campo-hint">Última actualización: {{ updatedAt }}</p>
      </div>
      <div class="campo">
        <label class="campo-label">Contenido de los términos</label>
        <textarea v-model="terminos" class="campo-textarea" rows="16" placeholder="Escribe aquí los términos y condiciones…"/>
      </div>
    </template>

    <!-- TAB PAGOS -->
    <template v-else-if="tabInterna === 'pagos'">
      <div class="ambiente-badge" :class="ambienteTB === 'PRODUCTION' ? 'prod' : 'test'">
        Transbank: {{ ambienteTB }}
      </div>

      <div class="campo">
        <label class="campo-label">Días de gracia antes del bloqueo</label>
        <input v-model.number="diasGracia" type="number" min="1" max="60" class="campo-input campo-sm" />
      </div>

      <div class="campo">
        <label class="campo-label toggle-label">
          <span>Bloqueo automático habilitado</span>
          <button
            :class="['toggle-btn', { on: bloqueoAuto }]"
            @click="bloqueoAuto = !bloqueoAuto"
          >
            <span class="toggle-thumb"/>
          </button>
        </label>
        <p class="campo-hint">Cuando está activo, las empresas son suspendidas automáticamente al agotar el período de gracia.</p>
      </div>

      <div class="campo">
        <label class="campo-label">Mensaje de bloqueo</label>
        <textarea v-model="mensajeBloqueo" class="campo-textarea" rows="4" placeholder="Mensaje que verá la empresa bloqueada…"/>
      </div>

      <!-- Tarjetas de prueba -->
      <div v-if="ambienteTB === 'INTEGRATION'" class="tarjetas-section">
        <h3 class="tarjetas-title">Tarjetas de prueba Transbank</h3>
        <p class="tarjetas-sub">RUT de autenticación: <strong>11.111.111-1</strong> — Clave: <strong>123</strong></p>
        <table class="tarjetas-tabla">
          <thead>
            <tr><th>Número</th><th>Resultado</th><th>CVC</th><th>Vencimiento</th></tr>
          </thead>
          <tbody>
            <tr v-for="t in tarjetasPrueba" :key="t.numero">
              <td class="mono">{{ t.numero }}</td>
              <td>
                <span :class="t.resultado.includes('Rechazado') ? 'badge-rechazado' : 'badge-aprobado'">
                  {{ t.resultado }}
                </span>
              </td>
              <td>{{ t.cvc }}</td>
              <td>{{ t.exp }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- Footer -->
    <div v-if="!cargando" class="terminos-footer">
      <div v-if="ok"    class="msg-ok">✓ Guardado correctamente.</div>
      <div v-if="error" class="msg-error">{{ error }}</div>
      <button class="btn-guardar" :disabled="guardando" @click="guardar">
        {{ guardando ? 'Guardando…' : tabInterna === 'terminos' ? 'Guardar y publicar' : 'Guardar configuración' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.terminos-tab { display: flex; flex-direction: column; gap: 1.25rem; }

.sub-tabs { display: flex; gap: 0.5rem; margin-bottom: 0.25rem; }
.sub-tab  {
  padding: 0.4rem 1rem; border-radius: 6px; border: 1px solid #E5E7EB;
  background: #fff; font-size: 0.8125rem; font-weight: 500; color: #374151;
  cursor: pointer; transition: all 0.15s; font-family: inherit;
}
.sub-tab.active { background: #4F46E5; color: #fff; border-color: #4F46E5; }

.cargando { color: #6B7280; font-size: 0.875rem; }

.campo       { display: flex; flex-direction: column; gap: 0.4rem; }
.campo-label { font-size: 0.875rem; font-weight: 600; color: #374151; }
.campo-input {
  padding: 0.5rem 0.75rem; border: 1px solid #E5E7EB; border-radius: 8px;
  font-size: 0.875rem; font-family: inherit;
}
.campo-sm    { max-width: 120px; }
.campo-textarea {
  padding: 0.6rem 0.75rem; border: 1px solid #E5E7EB; border-radius: 8px;
  font-size: 0.8125rem; font-family: monospace; resize: vertical;
}
.campo-hint { font-size: 0.8rem; color: #6B7280; margin: 0; }

.toggle-label { flex-direction: row; align-items: center; justify-content: space-between; }
.toggle-btn   {
  width: 44px; height: 24px; border-radius: 12px; border: none; cursor: pointer;
  background: #D1D5DB; position: relative; transition: background 0.2s;
}
.toggle-btn.on { background: #4F46E5; }
.toggle-thumb  {
  position: absolute; top: 3px; left: 3px;
  width: 18px; height: 18px; border-radius: 50%; background: #fff;
  transition: transform 0.2s;
}
.toggle-btn.on .toggle-thumb { transform: translateX(20px); }

.ambiente-badge {
  display: inline-block; padding: 4px 14px; border-radius: 99px;
  font-size: 0.8rem; font-weight: 700; letter-spacing: 0.05em;
}
.ambiente-badge.test { background: #DBEAFE; color: #1D4ED8; }
.ambiente-badge.prod { background: #D1FAE5; color: #065F46; }

.tarjetas-section { margin-top: 0.5rem; }
.tarjetas-title { font-size: 0.9375rem; font-weight: 600; color: #111827; margin: 0 0 0.25rem; }
.tarjetas-sub   { font-size: 0.8125rem; color: #6B7280; margin: 0 0 0.75rem; }
.tarjetas-tabla { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
.tarjetas-tabla th {
  text-align: left; padding: 0.5rem 0.75rem; background: #F9FAFB;
  color: #374151; font-weight: 600; border-bottom: 1px solid #E5E7EB;
}
.tarjetas-tabla td { padding: 0.5rem 0.75rem; border-bottom: 1px solid #F3F4F6; }
.mono { font-family: monospace; }
.badge-aprobado  { background: #D1FAE5; color: #065F46; font-size: 0.75rem; font-weight: 600; padding: 2px 8px; border-radius: 99px; }
.badge-rechazado { background: #FEE2E2; color: #991B1B; font-size: 0.75rem; font-weight: 600; padding: 2px 8px; border-radius: 99px; }

.terminos-footer { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
.msg-ok    { font-size: 0.875rem; color: #065F46; background: #D1FAE5; padding: 0.4rem 0.875rem; border-radius: 6px; }
.msg-error { font-size: 0.875rem; color: #B91C1C; background: #FEE2E2; padding: 0.4rem 0.875rem; border-radius: 6px; }
.btn-guardar {
  padding: 0.6rem 1.5rem; background: #4F46E5; color: #fff; border: none;
  border-radius: 8px; font-size: 0.875rem; font-weight: 600; cursor: pointer;
  transition: background 0.15s; font-family: inherit;
}
.btn-guardar:hover:not(:disabled) { background: #4338CA; }
.btn-guardar:disabled { opacity: 0.55; cursor: not-allowed; }
</style>
