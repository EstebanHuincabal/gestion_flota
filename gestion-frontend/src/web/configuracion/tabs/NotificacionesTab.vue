<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../../../utils/api.js'
import { useToast } from '../../../utils/useToast.js'

const toast = useToast()

const categorias = [
  { key: 'mantencion', label: 'Mantenimiento',         desc: 'Alertas de mantenimiento predictivo por vencer o vencidas' },
  { key: 'documentos', label: 'Documentos',            desc: 'Documentos de vehículos y conductores próximos a vencer' },
  { key: 'seguridad',  label: 'Seguridad',             desc: 'Cambios de contraseña, bloqueos y modificaciones de permisos' },
  { key: 'actividad',  label: 'Actividad operacional', desc: 'Asignaciones de conductor, nuevos vehículos y más' },
]

const prefs    = ref({ inapp: [], email: [], push_token: '' })
const guardando = ref(false)

const toggle = (canal, categoria) => {
  const lista = prefs.value[canal]
  const idx   = lista.indexOf(categoria)
  if (idx === -1) lista.push(categoria)
  else lista.splice(idx, 1)
}

const guardar = async () => {
  guardando.value = true
  const res = await apiFetch('/api/notificaciones/preferencias/', { method: 'PUT', body: prefs.value })
  if (res.ok) {
    prefs.value = await res.json()
    toast.success('Preferencias de notificación guardadas.')
  } else {
    toast.error('Error al guardar las preferencias.')
  }
  guardando.value = false
}

onMounted(async () => {
  const res = await apiFetch('/api/notificaciones/preferencias/')
  if (res.ok) prefs.value = await res.json()
})
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h2 class="card-title">Preferencias de notificación</h2>
      <p class="card-desc">Elige cómo y cuándo quieres recibir notificaciones del sistema</p>
    </div>
    <div class="card-body">
      <table class="table">
        <thead>
          <tr>
            <th class="th th-left">Evento</th>
            <th class="th th-center">In-App</th>
            <th class="th th-center">Email</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="cat in categorias" :key="cat.key" class="tr">
            <td class="td">
              <p class="cat-label">{{ cat.label }}</p>
              <p class="cat-desc">{{ cat.desc }}</p>
            </td>
            <td class="td td-center">
              <input
                type="checkbox"
                :checked="prefs.inapp.includes(cat.key)"
                @change="toggle('inapp', cat.key)"
                class="checkbox"
              />
            </td>
            <td class="td td-center">
              <input
                type="checkbox"
                :checked="prefs.email.includes(cat.key)"
                @change="toggle('email', cat.key)"
                class="checkbox"
              />
            </td>
          </tr>
        </tbody>
      </table>
      <div class="footer">
        <button class="btn-primary" @click="guardar" :disabled="guardando">
          {{ guardando ? 'Guardando...' : 'Guardar preferencias' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.card {
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  overflow: hidden;
}
.card-header {
  padding: 1.25rem 1.5rem 1rem;
  border-bottom: 1px solid #F3F4F6;
}
.card-title { font-size: 1rem; font-weight: 600; color: #111827; margin: 0 0 0.25rem; }
.card-desc { font-size: 0.8125rem; color: #6B7280; margin: 0; }
.card-body { padding: 0; }

.table { width: 100%; border-collapse: collapse; }
.th {
  padding: 0.75rem 1.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: #F9FAFB;
  border-bottom: 1px solid #E5E7EB;
}
.th-left { text-align: left; }
.th-center { text-align: center; }

.tr { border-bottom: 1px solid #F3F4F6; }
.tr:last-child { border-bottom: none; }

.td { padding: 1rem 1.5rem; }
.td-center { text-align: center; }

.cat-label { font-size: 0.875rem; font-weight: 500; color: #111827; margin: 0 0 0.125rem; }
.cat-desc { font-size: 0.75rem; color: #9CA3AF; margin: 0; }

.checkbox {
  width: 16px; height: 16px;
  accent-color: var(--color-accent, #4F46E5);
  cursor: pointer;
}

.footer {
  padding: 1rem 1.5rem;
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid #F3F4F6;
}
.btn-primary {
  padding: 0.5rem 1.25rem;
  background: var(--color-accent, #4F46E5);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.15s;
}
.btn-primary:hover { opacity: 0.88; }
.btn-primary:disabled { opacity: 0.55; cursor: not-allowed; }
</style>
