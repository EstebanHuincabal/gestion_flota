/**
 * services/websocket.js — Cliente WebSocket para la app de conductores.
 *
 * Se conecta al canal exclusivo del conductor `ws/conductor/?token=<JWT>`.
 * Recibe eventos en tiempo real:
 *   - solicitud_actualizada: el admin aprobó o rechazó una solicitud del conductor.
 *
 * Características:
 *   - Singleton (una sola instancia en toda la app).
 *   - Reconexión automática con backoff exponencial (máx. 30 s).
 *   - Se detiene si el token no existe o al llamar a disconnect().
 *   - Obtiene un token fresco de Preferences en cada intento de conexión
 *     (por si fue refrescado por apiFetch mientras tanto).
 */
import { Preferences } from '@capacitor/preferences'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Convierte http(s):// en ws(s)://
function wsUrl(token) {
  const base = BASE_URL.replace(/^http/, 'ws')
  return `${base}/ws/conductor/?token=${token}`
}

class WebSocketService {
  constructor() {
    this._ws             = null
    this._handlers       = new Map()   // tipo → Set<función>
    this._reconnectTimer = null
    this._active         = false
    this._delay          = 1000        // delay inicial de reconexión (ms)
  }

  // ── Conexión ────────────────────────────────────────────────────────────────

  async connect() {
    if (this._active) return   // ya conectado o en proceso
    this._active = true
    this._delay  = 1000
    await this._open()
  }

  async _open() {
    if (!this._active) return

    const { value: token } = await Preferences.get({ key: 'access_token' })
    if (!token) {
      // Sin token: detener completamente — no entrar en bucle de reconexión
      this._active = false
      clearTimeout(this._reconnectTimer)
      return
    }

    // Cerrar socket previo si existe
    if (this._ws) {
      this._ws.onclose = null  // evitar reconexión duplicada
      this._ws.close()
      this._ws = null
    }

    let ws
    try {
      ws = new WebSocket(wsUrl(token))
    } catch {
      // URL inválida u otro error de construcción
      this._scheduleReconnect()
      return
    }
    this._ws = ws

    ws.onopen = () => {
      this._delay = 1000   // reset del backoff al conectar con éxito
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        const handlers = this._handlers.get(data.type)
        if (handlers) handlers.forEach(fn => { try { fn(data) } catch {} })
      } catch {
        // JSON malformado — ignorar
      }
    }

    ws.onclose = () => {
      if (!this._active) return
      this._scheduleReconnect()
    }

    ws.onerror = () => {
      // onerror siempre va seguido de onclose → la reconexión ocurre allí
    }
  }

  _scheduleReconnect() {
    clearTimeout(this._reconnectTimer)
    this._reconnectTimer = setTimeout(async () => {
      if (!this._active) return
      this._delay = Math.min(this._delay * 2, 30_000)
      await this._open()
    }, this._delay)
  }

  // ── Suscripción a eventos ──────────────────────────────────────────────────

  /**
   * Registra un handler para un tipo de evento WebSocket.
   * @param {string}   type     p.ej. 'solicitud_actualizada'
   * @param {Function} handler  función que recibe el objeto del evento
   * @returns {Function}        función para cancelar la suscripción
   */
  on(type, handler) {
    if (!this._handlers.has(type)) this._handlers.set(type, new Set())
    this._handlers.get(type).add(handler)
    return () => this._handlers.get(type)?.delete(handler)
  }

  // ── Desconexión ────────────────────────────────────────────────────────────

  disconnect() {
    this._active = false
    clearTimeout(this._reconnectTimer)
    this._reconnectTimer = null
    if (this._ws) {
      this._ws.onclose = null
      this._ws.close()
      this._ws = null
    }
  }

  // ── Envío de mensajes ──────────────────────────────────────────────────────

  send(data) {
    if (this._ws?.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify(data))
      return true
    }
    return false
  }

  // ── Estado ─────────────────────────────────────────────────────────────────

  get conectado() {
    return this._ws?.readyState === WebSocket.OPEN
  }
}

// Exportar una única instancia para toda la app
export const wsService = new WebSocketService()
