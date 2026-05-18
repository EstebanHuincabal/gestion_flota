<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../../../utils/api.js'
import { useToast } from '../../../utils/useToast.js'

const toast = useToast()

const perfil = ref({ nombre: '', email: '' })
const guardandoPerfil = ref(false)

const pwd = ref({ password_actual: '', password_nueva: '', password_confirmar: '' })
const guardandoPwd = ref(false)

const cargarPerfil = async () => {
  const res = await apiFetch('/api/usuario/perfil/')
  if (res.ok) perfil.value = await res.json()
}

const guardarPerfil = async () => {
  guardandoPerfil.value = true
  const res = await apiFetch('/api/usuario/perfil/', { method: 'PUT', body: perfil.value })
  if (res.ok) {
    const data = await res.json()
    perfil.value.nombre = data.nombre
    perfil.value.email  = data.email
    const u = JSON.parse(localStorage.getItem('usuario') || '{}')
    u.nombre = data.nombre
    u.email  = data.email
    localStorage.setItem('usuario', JSON.stringify(u))
    toast.success('Perfil actualizado correctamente.')
  } else {
    const err = await res.json()
    toast.error(err.error || 'Error al guardar el perfil.')
  }
  guardandoPerfil.value = false
}

const cambiarPassword = async () => {
  guardandoPwd.value = true
  const res = await apiFetch('/api/usuario/cambiar-password/', { method: 'POST', body: pwd.value })
  if (res.ok) {
    toast.success('Contraseña actualizada correctamente.')
    pwd.value = { password_actual: '', password_nueva: '', password_confirmar: '' }
  } else {
    const err = await res.json()
    toast.error(err.error || 'Error al cambiar la contraseña.')
  }
  guardandoPwd.value = false
}

onMounted(cargarPerfil)
</script>

<template>
  <div class="tab-content">
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">Datos personales</h2>
        <p class="card-desc">Actualiza tu nombre y correo electrónico</p>
      </div>
      <div class="card-body">
        <div class="form-group">
          <label class="label">Nombre</label>
          <input v-model="perfil.nombre" type="text" class="input" placeholder="Tu nombre" />
        </div>
        <div class="form-group">
          <label class="label">Correo electrónico</label>
          <input v-model="perfil.email" type="email" class="input" placeholder="tu@email.com" />
        </div>
        <div class="form-footer">
          <button class="btn-primary" @click="guardarPerfil" :disabled="guardandoPerfil">
            {{ guardandoPerfil ? 'Guardando...' : 'Guardar cambios' }}
          </button>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h2 class="card-title">Contraseña</h2>
        <p class="card-desc">Cambia tu contraseña de acceso al sistema</p>
      </div>
      <div class="card-body">
        <div class="form-group">
          <label class="label">Contraseña actual</label>
          <input v-model="pwd.password_actual" type="password" class="input" placeholder="••••••••" />
        </div>
        <div class="form-group">
          <label class="label">Nueva contraseña</label>
          <input v-model="pwd.password_nueva" type="password" class="input" placeholder="••••••••" />
        </div>
        <div class="form-group">
          <label class="label">Confirmar nueva contraseña</label>
          <input v-model="pwd.password_confirmar" type="password" class="input" placeholder="••••••••" />
        </div>
        <div class="form-footer">
          <button class="btn-primary" @click="cambiarPassword" :disabled="guardandoPwd">
            {{ guardandoPwd ? 'Cambiando...' : 'Cambiar contraseña' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tab-content { display: flex; flex-direction: column; gap: 1.25rem; }

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

.card-body { padding: 1.25rem 1.5rem; display: flex; flex-direction: column; gap: 1rem; }

.form-group { display: flex; flex-direction: column; gap: 0.375rem; }
.label { font-size: 0.8125rem; font-weight: 500; color: #374151; }
.input {
  padding: 0.5625rem 0.75rem;
  border: 1px solid #D1D5DB;
  border-radius: 8px;
  font-size: 0.875rem;
  color: #111827;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.input:focus {
  border-color: var(--color-accent, #6366F1);
  box-shadow: 0 0 0 3px rgba(99,102,241,0.12);
}

.form-footer { display: flex; justify-content: flex-end; padding-top: 0.25rem; }

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
