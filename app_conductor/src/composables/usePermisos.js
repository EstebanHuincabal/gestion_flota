/**
 * composables/usePermisos.js — Módulos del plan con estado singleton y polling.
 *
 * El estado (modulos, planNombre) es COMPARTIDO entre todos los componentes
 * que llaman a usePermisos(). Así un solo intervalo de 30 s actualiza el
 * BottomNav, ListaRutas, Ajustes, etc. al mismo tiempo sin duplicar fetches.
 *
 * Ciclo de actualización:
 *  1. Al inicializar → carga caché local (Preferences) y hace fetch al servidor
 *  2. appStateChange → refresca cada vez que la app vuelve al primer plano
 *  3. setInterval 30 s → detecta cambios mientras la app está abierta
 *
 * resetearPermisos() se llama desde auth.js en logout para limpiar el estado.
 */
import { ref } from 'vue'
import { Preferences } from '@capacitor/preferences'
import { App } from '@capacitor/app'
import { apiFetch } from '@/services/api.js'

// ── Estado singleton (module-level) ──────────────────────────────────────────
const modulos    = ref([])
const planNombre = ref('')
const cargando   = ref(true)

let _inicializado    = false
let _appListener     = null
let _intervalId      = null

// ── Lógica de refresco ────────────────────────────────────────────────────────
async function _refrescar() {
  try {
    const data          = await apiFetch('/api/conductor/mi-plan/')
    const nuevosModulos = data.plan_modulos || []
    const nuevoNombre   = data.plan_nombre  || ''

    const mismos = JSON.stringify([...nuevosModulos].sort()) ===
                   JSON.stringify([...modulos.value].sort())

    if (!mismos || nuevoNombre !== planNombre.value) {
      modulos.value    = nuevosModulos
      planNombre.value = nuevoNombre
      await Preferences.set({ key: 'plan_modulos', value: JSON.stringify(nuevosModulos) })
      await Preferences.set({ key: 'plan_nombre',  value: nuevoNombre })
    }
  } catch {
    // Sin conexión → conservar caché
  }
}

async function _inicializar() {
  if (_inicializado) return
  _inicializado = true

  // 1. Caché local (rápido, para que BottomNav no haga flash)
  const { value: m } = await Preferences.get({ key: 'plan_modulos' })
  const { value: p } = await Preferences.get({ key: 'plan_nombre' })
  modulos.value    = JSON.parse(m || '[]')
  planNombre.value = p || ''

  // 2. Fetch servidor — cargando se apaga DESPUÉS para que las vistas
  //    vean datos frescos antes de decidir qué mostrar.
  await _refrescar()
  cargando.value = false

  // 3. Refresco al volver al primer plano
  try {
    _appListener = await App.addListener('appStateChange', ({ isActive }) => {
      if (isActive) _refrescar()
    })
  } catch {
    // En entorno web el plugin App puede no estar disponible; el intervalo basta
  }

  // 4. Polling cada 8 segundos
  _intervalId = setInterval(_refrescar, 8_000)
}

// ── Función de reset (llamar en logout) ───────────────────────────────────────
export async function resetearPermisos() {
  clearInterval(_intervalId)
  _appListener?.remove()
  _intervalId   = null
  _appListener  = null
  _inicializado = false
  modulos.value    = []
  planNombre.value = ''
  cargando.value   = true
}

// ── Composable público ────────────────────────────────────────────────────────
export function usePermisos() {
  // Inicializar solo una vez; llamadas posteriores reutilizan el estado
  _inicializar()

  function tieneModulo(modulo) {
    return modulos.value.includes(modulo)
  }

  return { modulos, planNombre, tieneModulo, cargando }
}
