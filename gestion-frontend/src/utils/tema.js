export const PRESETS_COLOR = [
  { key: 'violet',  label: 'Violeta',   from: '#4F46E5', to: '#7C3AED', accent: '#7C3AED' },
  { key: 'blue',    label: 'Azul',      from: '#1D4ED8', to: '#2563EB', accent: '#2563EB' },
  { key: 'sky',     label: 'Celeste',   from: '#0369A1', to: '#0EA5E9', accent: '#0EA5E9' },
  { key: 'emerald', label: 'Esmeralda', from: '#047857', to: '#059669', accent: '#059669' },
  { key: 'rose',    label: 'Rosa',      from: '#BE123C', to: '#E11D48', accent: '#E11D48' },
  { key: 'orange',  label: 'Naranja',   from: '#C2410C', to: '#EA580C', accent: '#EA580C' },
  { key: 'amber',   label: 'Ámbar',     from: '#B45309', to: '#D97706', accent: '#D97706' },
  { key: 'slate',   label: 'Pizarra',   from: '#1E293B', to: '#475569', accent: '#6366F1' },
]

export const FUENTES = [
  { key: 'inter',    label: 'Inter',    family: "'Inter', system-ui, sans-serif",           url: null },
  { key: 'roboto',   label: 'Roboto',   family: "'Roboto', sans-serif",                     url: 'Roboto:wght@400;500;600;700' },
  { key: 'poppins',  label: 'Poppins',  family: "'Poppins', sans-serif",                    url: 'Poppins:wght@400;500;600;700' },
  { key: 'dm-sans',  label: 'DM Sans',  family: "'DM Sans', sans-serif",                    url: 'DM+Sans:wght@400;500;600;700' },
  { key: 'nunito',   label: 'Nunito',   family: "'Nunito', sans-serif",                     url: 'Nunito:wght@400;500;600;700' },
  { key: 'geist',    label: 'Geist',    family: "'Geist', system-ui, sans-serif",            url: 'Geist:wght@400;500;600;700' },
]

const KEY_COLOR   = 'tema_color'
const KEY_CUSTOM  = 'tema_custom'
const KEY_DENSITY = 'tema_density'
const KEY_RADIUS  = 'tema_radius'
const KEY_FONT    = 'tema_font'

const DEFAULT_COLOR   = 'violet'
const DEFAULT_DENSITY = 'normal'
const DEFAULT_RADIUS  = 'normal'
const DEFAULT_FONT    = 'inter'

// ── Derivar paleta completa desde un color acento ──────────────────────────
// Tailwind 4 compila bg-indigo-600 como var(--color-indigo-600),
// así que sobrescribir estas variables afecta a TODOS los componentes.
function _derivarPaleta(accent) {
  const r = document.documentElement
  const mix = (pct, base = 'white') => `color-mix(in oklch, ${accent} ${pct}%, ${base})`

  ;['indigo', 'violet'].forEach(scale => {
    r.style.setProperty(`--color-${scale}-50`,  mix(8))
    r.style.setProperty(`--color-${scale}-100`, mix(15))
    r.style.setProperty(`--color-${scale}-200`, mix(30))
    r.style.setProperty(`--color-${scale}-300`, mix(50))
    r.style.setProperty(`--color-${scale}-400`, mix(70))
    r.style.setProperty(`--color-${scale}-500`, mix(85))
    r.style.setProperty(`--color-${scale}-600`, accent)
    r.style.setProperty(`--color-${scale}-700`, mix(85, 'black'))
    r.style.setProperty(`--color-${scale}-800`, mix(70, 'black'))
    r.style.setProperty(`--color-${scale}-900`, mix(50, 'black'))
    r.style.setProperty(`--color-${scale}-950`, mix(35, 'black'))
  })
}

function _aplicarColores(from, to, accent) {
  const r = document.documentElement
  r.style.setProperty('--sidebar-from', from)
  r.style.setProperty('--sidebar-to',   to)
  r.style.setProperty('--color-accent', accent)
  _derivarPaleta(accent)
}

function _aplicarPreset(key) {
  const preset = PRESETS_COLOR.find(p => p.key === key) || PRESETS_COLOR[0]
  _aplicarColores(preset.from, preset.to, preset.accent)
}

// ── Cargar fuente de Google Fonts dinámicamente ────────────────────────────
function _cargarFuente(fuente) {
  if (!fuente.url) return
  const id = `gfont-${fuente.key}`
  if (document.getElementById(id)) return
  const link = Object.assign(document.createElement('link'), {
    id,
    rel:  'stylesheet',
    href: `https://fonts.googleapis.com/css2?family=${fuente.url}&display=swap`,
  })
  document.head.appendChild(link)
}

function _aplicarFamilia(family) {
  document.documentElement.style.setProperty('--font-family', family)
}

// ── API pública ────────────────────────────────────────────────────────────
export function useTema() {

  const colorActual    = () => localStorage.getItem(KEY_COLOR)   || DEFAULT_COLOR
  const customActual   = () => JSON.parse(localStorage.getItem(KEY_CUSTOM) || 'null')
  const densidadActual = () => localStorage.getItem(KEY_DENSITY) || DEFAULT_DENSITY
  const radioActual    = () => localStorage.getItem(KEY_RADIUS)  || DEFAULT_RADIUS
  const fuenteActual   = () => localStorage.getItem(KEY_FONT)    || DEFAULT_FONT

  // ── Aplicar todo al arrancar ────
  const aplicar = () => {
    const key = colorActual()
    if (key === 'custom') {
      const c = customActual()
      if (c) _aplicarColores(c.from, c.to, c.accent)
      else   _aplicarPreset(DEFAULT_COLOR)
    } else {
      _aplicarPreset(key)
    }
  }

  const aplicarDensidad = () =>
    document.documentElement.setAttribute('data-density', densidadActual())

  const aplicarRadio = () =>
    document.documentElement.setAttribute('data-radius', radioActual())

  const aplicarFuente = () => {
    const key    = fuenteActual()
    const fuente = FUENTES.find(f => f.key === key) || FUENTES[0]
    _cargarFuente(fuente)
    _aplicarFamilia(fuente.family)
  }

  // ── Cambiar ────
  const cambiar = (key) => {
    localStorage.setItem(KEY_COLOR, key)
    _aplicarPreset(key)
  }

  const cambiarCustom = ({ from, to, accent }) => {
    localStorage.setItem(KEY_COLOR,  'custom')
    localStorage.setItem(KEY_CUSTOM, JSON.stringify({ from, to, accent }))
    _aplicarColores(from, to, accent)
  }

  const cambiarDensidad = (nivel) => {
    localStorage.setItem(KEY_DENSITY, nivel)
    document.documentElement.setAttribute('data-density', nivel)
  }

  const cambiarRadio = (nivel) => {
    localStorage.setItem(KEY_RADIUS, nivel)
    document.documentElement.setAttribute('data-radius', nivel)
  }

  const cambiarFuente = (key) => {
    localStorage.setItem(KEY_FONT, key)
    const fuente = FUENTES.find(f => f.key === key) || FUENTES[0]
    _cargarFuente(fuente)
    _aplicarFamilia(fuente.family)
  }

  // Expone _aplicarColores para que los gráficos lean el acento actual
  const accentActual = () =>
    getComputedStyle(document.documentElement).getPropertyValue('--color-accent').trim() || '#7C3AED'

  return {
    PRESETS_COLOR, FUENTES,
    colorActual, customActual, densidadActual, radioActual, fuenteActual, accentActual,
    aplicar, aplicarDensidad, aplicarRadio, aplicarFuente,
    cambiar, cambiarCustom, cambiarDensidad, cambiarRadio, cambiarFuente,
  }
}
