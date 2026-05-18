<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const rut = ref('')
const password = ref('')
const error = ref('')
const isLoading = ref(false)
const showPassword = ref(false)

const formatRut = (value) => {
  let cleaned = value.replace(/[^0-9kK]/g, '')
  if (cleaned.length < 2) return cleaned
  let body = cleaned.slice(0, -1)
  let dv = cleaned.slice(-1).toUpperCase()
  let formatted = body.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${formatted}-${dv}`
}

const onRutInput = (e) => {
  rut.value = formatRut(e.target.value)
}

const validateRut = (rutFull) => {
  if (!rutFull) return false
  const tmp = rutFull.replace(/\./g, '').split('-')
  if (tmp.length !== 2) return false
  let rutBody = tmp[0]
  let dv = tmp[1].toLowerCase()
  let M = 0, S = 1
  for (; rutBody; rutBody = Math.floor(rutBody / 10)) {
    S = (S + rutBody % 10 * (9 - M++ % 6)) % 11
  }
  const dvCalc = S ? S - 1 + '' : 'k'
  return dvCalc === dv
}

const handleLogin = async () => {
  error.value = ''
  if (!rut.value || !password.value) {
    error.value = 'Por favor complete todos los campos.'
    return
  }
  if (!validateRut(rut.value)) {
    error.value = 'El RUT ingresado no es válido.'
    return
  }
  isLoading.value = true
  try {
    const response = await fetch('/api/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ rut: rut.value, password: password.value })
    })
    const data = await response.json()
    if (response.ok) {
      localStorage.setItem('access_token',  data.access)
      localStorage.setItem('refresh_token', data.refresh)
      localStorage.setItem('usuario', JSON.stringify(data.user))
      if (Array.isArray(data.user.plan_modulos)) {
        sessionStorage.setItem('plan_modulos', JSON.stringify(data.user.plan_modulos))
      }
      sessionStorage.setItem('plan_nombre',   data.user.plan_nombre   || '')
      sessionStorage.setItem('plan_permisos', JSON.stringify(data.user.plan_permisos || []))
      const destino = data.user.rol === 'SUPERADMIN' ? '/dashboard' : (data.user.rol === 'USUARIO' ? '/empresa/dashboard' : '/login')
      router.push(destino)
    } else {
      error.value = data.error || 'Credenciales incorrectas.'
    }
  } catch (err) {
    console.error('Error de conexión:', err)
    error.value = 'Error de conexión con el servidor.'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="login-root">

    <!-- ── Panel izquierdo (branding) ── -->
    <aside class="brand-panel">
      <!-- Orbes de luz de fondo -->
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>

      <!-- Contenido central del panel -->
      <div class="brand-content">
        <div class="brand-icon-wrap">
          <svg class="brand-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0" />
          </svg>
        </div>

        <h2 class="brand-title">Gestión de Flota</h2>
        <p class="brand-subtitle">Sistema multiempresa para el control y monitoreo integral de tu flota vehicular.</p>

        <!-- Feature pills -->
        <ul class="feature-list">
          <li class="feature-item">
            <span class="feature-dot"></span>
            Monitoreo en tiempo real
          </li>
          <li class="feature-item">
            <span class="feature-dot"></span>
            Gestión de mantenimiento
          </li>
          <li class="feature-item">
            <span class="feature-dot"></span>
            Alertas automáticas
          </li>
          <li class="feature-item">
            <span class="feature-dot"></span>
            Dashboard e indicadores
          </li>
        </ul>
      </div>

      <!-- Badge inferior -->
      <div class="brand-badge">
        <span class="badge-dot"></span>
        Sistema seguro y multiempresa
      </div>
    </aside>

    <!-- ── Panel derecho (formulario) ── -->
    <main class="form-panel">
      <!-- Orbes sutiles en el fondo del panel -->
      <div class="form-orb form-orb-top"></div>
      <div class="form-orb form-orb-bottom"></div>

      <div class="form-container">
        <!-- Cabecera -->
        <div class="form-header">
          <div class="form-logo">
            <svg class="form-logo-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1" />
            </svg>
          </div>
          <h1 class="form-title">Bienvenido</h1>
          <p class="form-subtitle">Ingresa tus credenciales para acceder al sistema</p>
        </div>

        <!-- Card con glass effect -->
        <div class="form-card">
          <form @submit.prevent="handleLogin" class="form-body">

            <!-- Campo RUT -->
            <div class="field">
              <label class="field-label">RUT Administrador</label>
              <div class="input-wrap">
                <span class="input-icon">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2" />
                  </svg>
                </span>
                <input
                  type="text"
                  v-model="rut"
                  @input="onRutInput"
                  placeholder="12.345.678-9"
                  maxlength="12"
                  class="field-input"
                  :disabled="isLoading"
                />
              </div>
            </div>

            <!-- Campo Contraseña -->
            <div class="field">
              <div class="field-row">
                <label class="field-label">Contraseña</label>
                <a href="#" class="forgot-link">¿Olvidaste tu contraseña?</a>
              </div>
              <div class="input-wrap">
                <span class="input-icon">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </span>
                <input
                  :type="showPassword ? 'text' : 'password'"
                  v-model="password"
                  placeholder="••••••••"
                  class="field-input"
                  :disabled="isLoading"
                />
                <button
                  type="button"
                  class="toggle-eye"
                  @click="showPassword = !showPassword"
                  :disabled="isLoading"
                  tabindex="-1"
                >
                  <!-- Ojo abierto -->
                  <svg v-if="!showPassword" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  <!-- Ojo cerrado -->
                  <svg v-else fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- Mensaje de error -->
            <transition name="fade-slide">
              <div v-if="error" class="error-box">
                <svg class="error-icon" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                    clip-rule="evenodd" />
                </svg>
                {{ error }}
              </div>
            </transition>

            <!-- Botón principal -->
            <button type="submit" class="submit-btn" :disabled="isLoading">
              <span v-if="isLoading" class="spinner"></span>
              <svg v-else class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
              </svg>
              {{ isLoading ? 'Iniciando sesión...' : 'Ingresar al Sistema' }}
            </button>
          </form>
        </div>

        <!-- Pie del formulario -->
        <p class="form-footer">
          ¿No tienes acceso?
          <a href="#" class="footer-link">Contacta a soporte</a>
        </p>
      </div>
    </main>

  </div>
</template>

<style scoped>
/* ─────────────────────────────────────────
   Root layout
───────────────────────────────────────── */
.login-root {
  display: flex;
  min-height: 100vh;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  background: #F8FAFC;
}

/* ─────────────────────────────────────────
   Brand panel (left)
───────────────────────────────────────── */
.brand-panel {
  display: none;
  position: relative;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-start;
  width: 42%;
  min-height: 100vh;
  padding: 3rem;
  background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
  overflow: hidden;
}

@media (min-width: 1024px) {
  .brand-panel { display: flex; }
}

/* Orbes de fondo del panel */
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  pointer-events: none;
}
.orb-1 {
  width: 340px; height: 340px;
  top: -80px; left: -80px;
  background: rgba(255, 255, 255, 0.08);
}
.orb-2 {
  width: 260px; height: 260px;
  bottom: 80px; right: -60px;
  background: rgba(255, 255, 255, 0.06);
}
.orb-3 {
  width: 180px; height: 180px;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(255, 255, 255, 0.04);
}

.brand-content {
  position: relative;
  z-index: 1;
  margin-top: 2rem;
}

.brand-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 20px;
  margin-bottom: 2rem;
  backdrop-filter: blur(8px);
}
.brand-icon {
  width: 36px;
  height: 36px;
  color: #fff;
}

.brand-title {
  font-size: 2rem;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.5px;
  margin: 0 0 0.75rem;
}
.brand-subtitle {
  font-size: 0.95rem;
  color: rgba(255, 255, 255, 0.72);
  line-height: 1.6;
  max-width: 320px;
  margin: 0 0 2.5rem;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}
.feature-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.85);
  font-weight: 500;
}
.feature-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.6);
  flex-shrink: 0;
}

.brand-badge {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 100px;
  font-size: 0.8rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(8px);
}
.badge-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 0 3px rgba(52, 211, 153, 0.3);
}

/* ─────────────────────────────────────────
   Form panel (right)
───────────────────────────────────────── */
.form-panel {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2.5rem 1.5rem;
  background: #F8FAFC;
  overflow: hidden;
}

.form-orb {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
}
.form-orb-top {
  width: 320px; height: 320px;
  top: -120px; right: -80px;
  background: rgba(79, 70, 229, 0.06);
  filter: blur(60px);
}
.form-orb-bottom {
  width: 280px; height: 280px;
  bottom: -100px; left: -60px;
  background: rgba(124, 58, 237, 0.06);
  filter: blur(60px);
}

.form-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
}

/* Header del formulario */
.form-header {
  text-align: center;
  margin-bottom: 2rem;
}

.form-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(79, 70, 229, 0.3);
  margin-bottom: 1.25rem;
}
.form-logo-icon {
  width: 28px;
  height: 28px;
  color: #fff;
}

/* Solo visible en móvil */
@media (min-width: 1024px) {
  .form-logo { display: none; }
}

.form-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: #0F172A;
  letter-spacing: -0.4px;
  margin: 0 0 0.4rem;
}
.form-subtitle {
  font-size: 0.875rem;
  color: #64748B;
  margin: 0;
}

/* Card */
.form-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid #E2E8F0;
  border-radius: 20px;
  box-shadow:
    0 1px 3px rgba(0, 0, 0, 0.04),
    0 10px 40px rgba(79, 70, 229, 0.08);
  padding: 2rem;
}

.form-body {
  display: flex;
  flex-direction: column;
  gap: 1.4rem;
}

/* Campos */
.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.field-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #0F172A;
  letter-spacing: 0.01em;
}
.field-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.forgot-link {
  font-size: 0.75rem;
  font-weight: 500;
  color: #4F46E5;
  text-decoration: none;
  transition: color 0.2s;
}
.forgot-link:hover { color: #7C3AED; }

.input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}
.input-icon {
  position: absolute;
  left: 0.875rem;
  display: flex;
  align-items: center;
  pointer-events: none;
}
.input-icon svg {
  width: 17px;
  height: 17px;
  color: #94A3B8;
}

.field-input {
  width: 100%;
  padding: 0.75rem 2.75rem 0.75rem 2.625rem;
  background: #fff;
  border: 1.5px solid #E2E8F0;
  border-radius: 10px;
  font-size: 0.9rem;
  color: #0F172A;
  transition: border-color 0.2s, box-shadow 0.2s;
  outline: none;
}
.field-input::placeholder { color: #94A3B8; }
.field-input:focus {
  border-color: #4F46E5;
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.12);
}
.field-input:disabled {
  background: #F8FAFC;
  color: #94A3B8;
  cursor: not-allowed;
}

.toggle-eye {
  position: absolute;
  right: 0.875rem;
  display: flex;
  align-items: center;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: #94A3B8;
  transition: color 0.2s;
}
.toggle-eye:hover { color: #4F46E5; }
.toggle-eye svg { width: 17px; height: 17px; }

/* Error */
.error-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #FFF1F2;
  border: 1px solid #FECDD3;
  color: #E11D48;
  padding: 0.75rem 1rem;
  border-radius: 10px;
  font-size: 0.84rem;
  font-weight: 500;
}
.error-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

/* Botón */
.submit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.625rem;
  width: 100%;
  padding: 0.8rem 1.5rem;
  background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.15s, box-shadow 0.2s;
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.35);
}
.submit-btn:hover:not(:disabled) {
  opacity: 0.92;
  box-shadow: 0 6px 20px rgba(79, 70, 229, 0.45);
}
.submit-btn:active:not(:disabled) {
  transform: scale(0.985);
}
.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.btn-icon {
  width: 18px;
  height: 18px;
}

/* Spinner */
.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Footer */
.form-footer {
  text-align: center;
  margin-top: 1.5rem;
  font-size: 0.84rem;
  color: #64748B;
}
.footer-link {
  font-weight: 600;
  color: #4F46E5;
  text-decoration: none;
  margin-left: 0.25rem;
  transition: color 0.2s;
}
.footer-link:hover { color: #7C3AED; }

/* Transición del mensaje de error */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.25s, transform 0.25s;
}
.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
