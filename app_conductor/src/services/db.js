/**
 * db.js — Wrapper de @capacitor-community/sqlite.
 *
 * En dispositivos nativos (Android / iOS) usa SQLite real.
 * En el browser (testing web) cae en modo memoria — los datos
 * no persisten entre recargas pero la app no rompe.
 */
import { Capacitor } from '@capacitor/core'

const isNative = Capacitor.isNativePlatform()

// Fallback en memoria para browser
const _mem = {
  rutas:      new Map(),   // id → { data, estado, actualizado_at }
  pendientes: [],          // [{ id, tipo, payload, creado_at, intentos }]
  nextId:     1,
}

let _db   = null
let _listo = false

// ── Inicialización ────────────────────────────────────────────────────────────

export async function init() {
  if (_listo) return

  if (!isNative) {
    _listo = true
    return
  }

  try {
    const { CapacitorSQLite, SQLiteConnection } = await import('@capacitor-community/sqlite')
    const conn = new SQLiteConnection(CapacitorSQLite)
    _db = await conn.createConnection('conductor_db', false, 'no-encryption', 1, false)
    await _db.open()
    await _db.execute(`
      CREATE TABLE IF NOT EXISTS rutas (
        id           INTEGER PRIMARY KEY,
        data         TEXT    NOT NULL,
        estado       TEXT,
        actualizado_at TEXT
      );
      CREATE TABLE IF NOT EXISTS acciones_pendientes (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo       TEXT NOT NULL,
        payload    TEXT NOT NULL,
        creado_at  TEXT NOT NULL,
        intentos   INTEGER DEFAULT 0
      );
    `)
    _listo = true
  } catch (e) {
    console.warn('[DB] SQLite no disponible, usando modo memoria:', e.message)
    _listo = true
  }
}

// ── Rutas ─────────────────────────────────────────────────────────────────────

export async function getRutas() {
  if (!_db) {
    return [..._mem.rutas.values()].map(r => JSON.parse(r.data))
  }
  const { values } = await _db.query('SELECT data FROM rutas ORDER BY actualizado_at DESC')
  return (values || []).map(r => JSON.parse(r.data))
}

export async function saveRutas(rutas) {
  const ahora = new Date().toISOString()
  if (!_db) {
    rutas.forEach(r => _mem.rutas.set(r.id, {
      data:          JSON.stringify(r),
      estado:        r.estado,
      actualizado_at: ahora,
    }))
    return
  }
  for (const r of rutas) {
    await _db.run(
      'INSERT OR REPLACE INTO rutas (id, data, estado, actualizado_at) VALUES (?, ?, ?, ?)',
      [r.id, JSON.stringify(r), r.estado, ahora],
    )
  }
}

// ── Cola de acciones offline ──────────────────────────────────────────────────

export async function getPendientes() {
  if (!_db) return _mem.pendientes.map(p => ({ ...p, payload: typeof p.payload === 'string' ? JSON.parse(p.payload) : p.payload }))
  const { values } = await _db.query('SELECT * FROM acciones_pendientes ORDER BY id ASC')
  return (values || []).map(r => ({ ...r, payload: JSON.parse(r.payload) }))
}

export async function encolarAccion(tipo, payload) {
  const ahora = new Date().toISOString()
  if (!_db) {
    _mem.pendientes.push({ id: _mem.nextId++, tipo, payload, creado_at: ahora, intentos: 0 })
    return
  }
  await _db.run(
    'INSERT INTO acciones_pendientes (tipo, payload, creado_at) VALUES (?, ?, ?)',
    [tipo, JSON.stringify(payload), ahora],
  )
}

export async function eliminarPendiente(id) {
  if (!_db) {
    const idx = _mem.pendientes.findIndex(p => p.id === id)
    if (idx > -1) _mem.pendientes.splice(idx, 1)
    return
  }
  await _db.run('DELETE FROM acciones_pendientes WHERE id = ?', [id])
}
