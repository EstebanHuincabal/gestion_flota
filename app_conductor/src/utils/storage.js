/**
 * storage.js — Wrapper de @capacitor/preferences con caché en memoria.
 *
 * @capacitor/preferences es async (usa Keychain en iOS y EncryptedSharedPreferences
 * en Android). Para que api.js pueda leer tokens de forma síncrona usamos un caché
 * en memoria que se rellena una sola vez al arrancar la app (initStorage).
 */
import { Preferences } from '@capacitor/preferences'

// Claves que se precargan al iniciar la app
const CLAVES_SESION = ['access_token', 'refresh_token', 'usuario']

const _cache = {}

/** Llamar UNA VEZ en main.js antes de montar la app */
export async function initStorage() {
  await Promise.all(
    CLAVES_SESION.map(async (k) => {
      const { value } = await Preferences.get({ key: k })
      _cache[k] = value ?? null
    }),
  )
}

/** Lectura síncrona (desde caché) */
export function getItem(key) {
  return _cache[key] ?? null
}

/** Escritura — actualiza caché y almacenamiento nativo */
export async function setItem(key, value) {
  _cache[key] = value
  await Preferences.set({ key, value })
}

/** Eliminación individual */
export async function removeItem(key) {
  _cache[key] = null
  await Preferences.remove({ key })
}

/** Limpia toda la sesión */
export async function clearSession() {
  CLAVES_SESION.forEach((k) => (_cache[k] = null))
  await Promise.all(CLAVES_SESION.map((k) => Preferences.remove({ key: k })))
}
