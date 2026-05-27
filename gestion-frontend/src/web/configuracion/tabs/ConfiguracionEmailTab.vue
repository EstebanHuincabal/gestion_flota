<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../../../utils/api.js'
import { useToast } from '../../../utils/useToast.js'

const toast = useToast()

// ── Estado del formulario SMTP ────────────────────────────────────────────────
const form = ref({
  email_host:          'smtp.gmail.com',
  email_port:          587,
  email_host_user:     '',
  email_host_password: '',
  email_use_tls:       true,
  email_use_ssl:       false,
  email_from_name:     'FlotaSystem',
  email_from_address:  '',
  email_activo:        false,
})

// ── Toggles de notificaciones ─────────────────────────────────────────────────
const notif = ref({
  bienvenida:            true,
  pago_aprobado:         true,
  pago_rechazado:        true,
  suscripcion_vence:     true,
  suscripcion_gracia:    true,
  suscripcion_bloqueada: true,
  documento_vence:       true,
  mantencion_vence:      true,
  solicitud_nueva:       true,
  solicitud_resuelta:    true,
  ruta_asignada:         true,
  checklist_fallas:      true,
  reset_password:        true,
  recordatorio_pago:     true,
})

const cargando      = ref(true)
const guardandoSmtp = ref(false)
const guardandoNotif = ref(false)
const mostrarPass   = ref(false)

// Guías SMTP colapsables
const guiaAbierta   = ref(null)

// Modal de test
const modalTest    = ref(false)
const emailTest    = ref('')
const enviandoTest = ref(false)
const resultadoTest = ref(null)

const EVENTOS = [
  { key: 'bienvenida',            label: 'Bienvenida a nuevo usuario' },
  { key: 'pago_aprobado',         label: 'Pago aprobado' },
  { key: 'pago_rechazado',        label: 'Pago rechazado' },
  { key: 'suscripcion_vence',     label: 'Suscripción por vencer' },
  { key: 'suscripcion_gracia',    label: 'Período de gracia' },
  { key: 'suscripcion_bloqueada', label: 'Servicio suspendido' },
  { key: 'documento_vence',       label: 'Documento por vencer / vencido' },
  { key: 'mantencion_vence',      label: 'Mantención pendiente' },
  { key: 'solicitud_nueva',       label: 'Nueva solicitud de conductor' },
  { key: 'solicitud_resuelta',    label: 'Solicitud aprobada / rechazada' },
  { key: 'ruta_asignada',         label: 'Ruta asignada a conductor' },
  { key: 'checklist_fallas',      label: 'Checklist con fallas' },
  { key: 'reset_password',        label: 'Contraseña temporal enviada por admin' },
  { key: 'recordatorio_pago',     label: 'Recordatorio de pago pendiente' },
]

const GUIAS = [
  {
    id: 'gmail',
    titulo: 'Gmail',
    pasos: [
      'Servidor: smtp.gmail.com · Puerto: 587 · TLS activado',
      'Usa una "contraseña de aplicación" (no la contraseña normal de tu cuenta)',
      'Actívala en: Cuenta Google → Seguridad → Verificación en dos pasos → Contraseñas de aplicaciones',
    ],
  },
  {
    id: 'outlook',
    titulo: 'Outlook / Office 365',
    pasos: [
      'Servidor: smtp.office365.com · Puerto: 587 · TLS activado',
      'Usuario y contraseña de tu cuenta Microsoft',
    ],
  },
  {
    id: 'ionos',
    titulo: 'IONOS / 1&1',
    pasos: [
      'Servidor: smtp.ionos.es · Puerto: 587 · TLS activado',
      'Usuario: tu dirección de email completa',
    ],
  },
]

// ── Cargar configuración ──────────────────────────────────────────────────────
const cargar = async () => {
  cargando.value = true
  try {
    const res = await apiFetch('/api/admin/email/')
    if (!res.ok) throw new Error()
    const data = await res.json()
    form.value = {
      email_host:          data.email_host          ?? 'smtp.gmail.com',
      email_port:          data.email_port          ?? 587,
      email_host_user:     data.email_host_user     ?? '',
      email_host_password: data.email_host_password ?? '',
      email_use_tls:       data.email_use_tls       ?? true,
      email_use_ssl:       data.email_use_ssl        ?? false,
      email_from_name:     data.email_from_name     ?? 'FlotaSystem',
      email_from_address:  data.email_from_address  ?? '',
      email_activo:        data.email_activo        ?? false,
    }
    if (data.notificaciones) {
      Object.assign(notif.value, data.notificaciones)
    }
  } catch {
    toast.error('Error al cargar la configuración de email.')
  }
  cargando.value = false
}

// ── Guardar SMTP ──────────────────────────────────────────────────────────────
const guardarSmtp = async () => {
  guardandoSmtp.value = true
  try {
    const res = await apiFetch('/api/admin/email/', {
      method: 'PUT',
      body: { ...form.value },
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error || 'Error al guardar.')
    }
    toast.success('Configuración SMTP guardada.')
  } catch (e) {
    toast.error(e.message || 'Error al guardar.')
  }
  guardandoSmtp.value = false
}

// ── Guardar notificaciones ────────────────────────────────────────────────────
const guardarNotif = async () => {
  guardandoNotif.value = true
  try {
    const res = await apiFetch('/api/admin/email/', {
      method: 'PUT',
      body: { notificaciones: { ...notif.value } },
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.error || 'Error al guardar.')
    }
    toast.success('Preferencias de notificación guardadas.')
  } catch (e) {
    toast.error(e.message || 'Error al guardar.')
  }
  guardandoNotif.value = false
}

// ── Enviar email de prueba ────────────────────────────────────────────────────
const enviarTest = async () => {
  if (!emailTest.value) return
  enviandoTest.value = true
  resultadoTest.value = null
  try {
    const res = await apiFetch('/api/admin/email/test/', {
      method: 'POST',
      body: { email_destino: emailTest.value },
    })
    const data = await res.json().catch(() => ({}))
    if (res.ok) {
      resultadoTest.value = { ok: true, mensaje: data.mensaje }
    } else {
      resultadoTest.value = { ok: false, error: data.error || 'Error al enviar.' }
    }
  } catch (e) {
    resultadoTest.value = { ok: false, error: e.message }
  }
  enviandoTest.value = false
}

const abrirTest = () => {
  emailTest.value = ''
  resultadoTest.value = null
  modalTest.value = true
}

onMounted(cargar)
</script>

<template>
  <div class="email-tab">
    <div v-if="cargando" class="loading">
      <div class="spinner" />
    </div>

    <template v-else>
      <!-- ── Sección 1: Configuración SMTP ── -->
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">Configuración SMTP</h2>
            <p class="card-desc">Servidor de correo saliente para los envíos automáticos</p>
          </div>
          <!-- Toggle activar / desactivar -->
          <label class="toggle-wrap">
            <span class="toggle-label">{{ form.email_activo ? 'Activo' : 'Desactivado' }}</span>
            <button
              class="toggle"
              :class="{ 'toggle--on': form.email_activo }"
              @click="form.email_activo = !form.email_activo"
              type="button"
            >
              <span class="toggle-thumb" />
            </button>
          </label>
        </div>

        <div class="card-body">
          <!-- Guías rápidas -->
          <div class="guias">
            <p class="guias-titulo">Guías de configuración:</p>
            <div v-for="g in GUIAS" :key="g.id" class="guia">
              <button
                class="guia-btn"
                @click="guiaAbierta = guiaAbierta === g.id ? null : g.id"
                type="button"
              >
                <span>{{ g.titulo }}</span>
                <svg
                  class="guia-chevron"
                  :class="{ 'guia-chevron--abierto': guiaAbierta === g.id }"
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              <ul v-if="guiaAbierta === g.id" class="guia-lista">
                <li v-for="(paso, i) in g.pasos" :key="i">{{ paso }}</li>
              </ul>
            </div>
          </div>

          <!-- Formulario SMTP -->
          <div class="form-grid">
            <div class="field">
              <label class="label">Servidor SMTP</label>
              <input v-model="form.email_host" class="input" type="text" placeholder="smtp.gmail.com" />
            </div>
            <div class="field">
              <label class="label">Puerto</label>
              <input v-model.number="form.email_port" class="input" type="number" placeholder="587" />
            </div>
            <div class="field">
              <label class="label">Usuario</label>
              <input v-model="form.email_host_user" class="input" type="email" placeholder="notif@empresa.cl" />
            </div>
            <div class="field">
              <label class="label">Contraseña</label>
              <div class="pass-wrap">
                <input
                  v-model="form.email_host_password"
                  :type="mostrarPass ? 'text' : 'password'"
                  class="input input--pass"
                  placeholder="Contraseña de aplicación"
                />
                <button class="pass-toggle" @click="mostrarPass = !mostrarPass" type="button">
                  <svg v-if="!mostrarPass" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                      d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  <svg v-else fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75"
                      d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                </button>
              </div>
            </div>
            <div class="field">
              <label class="label">Nombre del remitente</label>
              <input v-model="form.email_from_name" class="input" type="text" placeholder="FlotaSystem" />
            </div>
            <div class="field">
              <label class="label">Email del remitente</label>
              <input v-model="form.email_from_address" class="input" type="email" placeholder="notif@empresa.cl" />
            </div>
          </div>

          <!-- TLS / SSL -->
          <div class="tls-row">
            <label class="check-label">
              <input
                type="checkbox"
                v-model="form.email_use_tls"
                @change="form.email_use_tls ? (form.email_use_ssl = false) : null"
                class="check"
              />
              <span>TLS (recomendado)</span>
            </label>
            <label class="check-label">
              <input
                type="checkbox"
                v-model="form.email_use_ssl"
                @change="form.email_use_ssl ? (form.email_use_tls = false) : null"
                class="check"
              />
              <span>SSL (puerto 465)</span>
            </label>
          </div>

          <!-- Botones -->
          <div class="btn-row">
            <button class="btn-secondary" @click="abrirTest" type="button">
              ✉ Enviar email de prueba
            </button>
            <button class="btn-primary" @click="guardarSmtp" :disabled="guardandoSmtp" type="button">
              {{ guardandoSmtp ? 'Guardando…' : 'Guardar configuración' }}
            </button>
          </div>
        </div>
      </div>

      <!-- ── Sección 2: Notificaciones por evento ── -->
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">Notificaciones por evento</h2>
            <p class="card-desc">Activa o desactiva el envío de email para cada evento del sistema</p>
          </div>
        </div>
        <div class="card-body">
          <table class="notif-tabla">
            <thead>
              <tr>
                <th class="notif-th">Evento</th>
                <th class="notif-th notif-th--centro">Email activo</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="ev in EVENTOS" :key="ev.key" class="notif-tr">
                <td class="notif-td">{{ ev.label }}</td>
                <td class="notif-td notif-td--centro">
                  <button
                    class="toggle toggle--sm"
                    :class="{ 'toggle--on': notif[ev.key] }"
                    @click="notif[ev.key] = !notif[ev.key]"
                    type="button"
                  >
                    <span class="toggle-thumb" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>

          <div class="btn-row btn-row--right">
            <button class="btn-primary" @click="guardarNotif" :disabled="guardandoNotif" type="button">
              {{ guardandoNotif ? 'Guardando…' : 'Guardar notificaciones' }}
            </button>
          </div>
        </div>
      </div>
    </template>

    <!-- ── Modal email de prueba ── -->
    <Teleport to="body">
      <div v-if="modalTest" class="modal-overlay" @click.self="modalTest = false">
        <div class="modal">
          <div class="modal-header">
            <h3 class="modal-title">Enviar email de prueba</h3>
            <button class="modal-close" @click="modalTest = false">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="modal-body">
            <p class="modal-desc">
              Se enviará un email de prueba usando la configuración SMTP guardada.
            </p>
            <div class="field">
              <label class="label">Email destino</label>
              <input
                v-model="emailTest"
                class="input"
                type="email"
                placeholder="tu@email.cl"
                @keyup.enter="enviarTest"
              />
            </div>

            <!-- Resultado -->
            <div v-if="resultadoTest" class="resultado" :class="resultadoTest.ok ? 'resultado--ok' : 'resultado--error'">
              <span v-if="resultadoTest.ok">✓ {{ resultadoTest.mensaje }}</span>
              <span v-else>✗ {{ resultadoTest.error }}</span>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" @click="modalTest = false">Cerrar</button>
            <button
              class="btn-primary"
              @click="enviarTest"
              :disabled="enviandoTest || !emailTest"
            >
              {{ enviandoTest ? 'Enviando…' : 'Enviar prueba' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.email-tab { display: flex; flex-direction: column; gap: 1.5rem; }

.loading { display: flex; justify-content: center; padding: 3rem; }
.spinner {
  width: 32px; height: 32px;
  border: 3px solid #E5E7EB;
  border-top-color: var(--color-accent, #4F46E5);
  border-radius: 50%;
  animation: spin 0.75s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Card */
.card { background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; overflow: hidden; }
.card-header {
  padding: 1.25rem 1.5rem 1rem;
  border-bottom: 1px solid #F3F4F6;
  display: flex; align-items: center; justify-content: space-between;
}
.card-title  { font-size: 1rem; font-weight: 600; color: #111827; margin: 0 0 0.2rem; }
.card-desc   { font-size: 0.8125rem; color: #6B7280; margin: 0; }
.card-body   { padding: 1.5rem; display: flex; flex-direction: column; gap: 1.25rem; }

/* Toggle */
.toggle-wrap  { display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0; }
.toggle-label { font-size: 0.8125rem; color: #6B7280; }
.toggle {
  position: relative; width: 40px; height: 22px;
  background: #D1D5DB; border: none; border-radius: 999px;
  cursor: pointer; transition: background 0.2s; flex-shrink: 0;
  padding: 0;
}
.toggle--on { background: var(--color-accent, #4F46E5); }
.toggle--sm { width: 34px; height: 18px; }
.toggle-thumb {
  position: absolute; top: 3px; left: 3px;
  width: 16px; height: 16px;
  background: #fff; border-radius: 50%;
  transition: transform 0.2s;
}
.toggle--sm .toggle-thumb { width: 12px; height: 12px; }
.toggle--on  .toggle-thumb { transform: translateX(18px); }
.toggle--sm.toggle--on .toggle-thumb { transform: translateX(16px); }

/* Guías */
.guias       { background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 8px; padding: 0.875rem; }
.guias-titulo { font-size: 0.8125rem; font-weight: 600; color: #374151; margin: 0 0 0.5rem; }
.guia        { border-top: 1px solid #E5E7EB; }
.guia:first-of-type { border-top: none; }
.guia-btn {
  width: 100%; display: flex; align-items: center; justify-content: space-between;
  background: none; border: none; padding: 0.5rem 0;
  font-size: 0.8125rem; font-weight: 500; color: #374151; cursor: pointer;
}
.guia-chevron { width: 14px; height: 14px; color: #9CA3AF; transition: transform 0.2s; }
.guia-chevron--abierto { transform: rotate(180deg); }
.guia-lista { margin: 0 0 0.5rem; padding-left: 1.25rem; display: flex; flex-direction: column; gap: 0.25rem; }
.guia-lista li { font-size: 0.8rem; color: #6B7280; }

/* Formulario */
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 640px) { .form-grid { grid-template-columns: 1fr; } }
.field  { display: flex; flex-direction: column; gap: 0.375rem; }
.label  { font-size: 0.8125rem; font-weight: 500; color: #374151; }
.input  { padding: 0.5rem 0.75rem; border: 1px solid #D1D5DB; border-radius: 8px; font-size: 0.875rem; color: #111827; outline: none; transition: border-color 0.15s; font-family: inherit; }
.input:focus { border-color: var(--color-accent, #4F46E5); }
.input--pass { flex: 1; border-radius: 8px 0 0 8px; }
.pass-wrap { display: flex; }
.pass-toggle {
  padding: 0 0.75rem; background: #F3F4F6;
  border: 1px solid #D1D5DB; border-left: none;
  border-radius: 0 8px 8px 0; cursor: pointer;
}
.pass-toggle svg { width: 16px; height: 16px; color: #6B7280; }

/* TLS / SSL */
.tls-row { display: flex; gap: 1.5rem; }
.check-label { display: flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; color: #374151; cursor: pointer; }
.check { width: 16px; height: 16px; accent-color: var(--color-accent, #4F46E5); cursor: pointer; }

/* Botones */
.btn-row { display: flex; gap: 0.75rem; justify-content: flex-end; flex-wrap: wrap; }
.btn-row--right { margin-top: 0.5rem; }
.btn-primary {
  padding: 0.5rem 1.25rem;
  background: var(--color-accent, #4F46E5); color: #fff;
  border: none; border-radius: 8px;
  font-size: 0.875rem; font-weight: 500; cursor: pointer; transition: opacity 0.15s;
  font-family: inherit;
}
.btn-primary:hover    { opacity: 0.88; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary {
  padding: 0.5rem 1.25rem;
  background: #fff; color: #374151;
  border: 1px solid #D1D5DB; border-radius: 8px;
  font-size: 0.875rem; font-weight: 500; cursor: pointer; transition: background 0.15s;
  font-family: inherit;
}
.btn-secondary:hover { background: #F9FAFB; }

/* Tabla notificaciones */
.notif-tabla { width: 100%; border-collapse: collapse; }
.notif-th {
  padding: 0.625rem 1rem;
  background: #F9FAFB; border-bottom: 1px solid #E5E7EB;
  font-size: 0.75rem; font-weight: 600; color: #6B7280;
  text-transform: uppercase; letter-spacing: 0.04em; text-align: left;
}
.notif-th--centro { text-align: center; }
.notif-tr { border-bottom: 1px solid #F3F4F6; }
.notif-tr:last-child { border-bottom: none; }
.notif-td { padding: 0.75rem 1rem; font-size: 0.875rem; color: #374151; }
.notif-td--centro { text-align: center; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; z-index: 999;
  background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center; padding: 1rem;
}
.modal {
  background: #fff; border-radius: 16px;
  width: 100%; max-width: 400px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15); overflow: hidden;
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
.modal-desc { font-size: 0.875rem; color: #6B7280; margin: 0; }
.modal-footer {
  display: flex; justify-content: flex-end; gap: 0.75rem;
  padding: 1rem 1.5rem; border-top: 1px solid #F3F4F6;
}
.btn-cancel {
  padding: 0.5rem 1rem;
  background: #fff; color: #374151;
  border: 1px solid #D1D5DB; border-radius: 8px;
  font-size: 0.875rem; font-weight: 500; cursor: pointer; font-family: inherit;
}
.btn-cancel:hover { background: #F9FAFB; }

.resultado {
  padding: 0.75rem 1rem; border-radius: 8px;
  font-size: 0.8125rem; font-weight: 500;
}
.resultado--ok    { background: #E1F5EE; color: #085041; }
.resultado--error { background: #FCEBEB; color: #791F1F; }
</style>
