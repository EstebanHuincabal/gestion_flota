/**
 * services/permisos.js — Utilidades para leer módulos del plan desde Preferences.
 *
 * Los módulos se almacenan en @capacitor/preferences bajo la clave 'plan_modulos'
 * y se guardan al hacer login. NO se leen del store de Pinia — son datos
 * persistentes del dispositivo independientes del ciclo de vida del store.
 */
import { Preferences } from '@capacitor/preferences'

/**
 * Devuelve el array de módulos activos del plan.
 * @returns {Promise<string[]>}
 */
export async function cargarModulos() {
  const { value } = await Preferences.get({ key: 'plan_modulos' })
  return JSON.parse(value || '[]')
}

/**
 * Comprueba si un módulo específico está habilitado en el plan actual.
 * @param {string} modulo
 * @returns {Promise<boolean>}
 */
export async function tieneModulo(modulo) {
  const modulos = await cargarModulos()
  return modulos.includes(modulo)
}

/**
 * Alias de cargarModulos() — nombre más explícito para contextos de importación.
 * @returns {Promise<string[]>}
 */
export async function getModulos() {
  return await cargarModulos()
}
