/**
 * theme.js — Store de personalización visual (por conductor, por dispositivo)
 *
 * Cada tema define un conjunto de variables CSS que se inyectan en :root.
 * La elección se persiste en @capacitor/preferences (clave 'tema_app').
 * No requiere backend: es completamente local al dispositivo.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { Preferences } from '@capacitor/preferences'

// ── Definición de temas ────────────────────────────────────────────────────────
export const TEMAS = [
  {
    id:         'indigo',
    nombre:     'Índigo',
    descripcion: 'El clásico de la app',
    color:      '#534AB7',
    colorGrad:  ['#534AB7', '#7C3AED'],
    vars: {
      '--color-acento':       '#534AB7',
      '--color-acento-dark':  '#3D3598',
      '--color-acento-light': '#6B63CC',
      '--color-acento-suave': '#EEEDFE',
      '--color-acento-suave2':'#F5F4FF',
      '--gradient-primary':   'linear-gradient(135deg, #534AB7 0%, #7C3AED 100%)',
      '--gradient-hero':      'linear-gradient(160deg, #534AB7 0%, #3D3598 60%, #2D2578 100%)',
      '--gradient-card':      'linear-gradient(135deg, #6B63CC 0%, #534AB7 100%)',
      '--shadow-acento':      '0 4px 20px rgba(83,74,183,0.35)',
    },
  },
  {
    id:         'oceano',
    nombre:     'Océano',
    descripcion: 'Azul profundo',
    color:      '#1D6DB5',
    colorGrad:  ['#1D6DB5', '#0F52A4'],
    vars: {
      '--color-acento':       '#1D6DB5',
      '--color-acento-dark':  '#0F52A4',
      '--color-acento-light': '#2E7EC5',
      '--color-acento-suave': '#EBF4FF',
      '--color-acento-suave2':'#F0F7FF',
      '--gradient-primary':   'linear-gradient(135deg, #1D6DB5 0%, #0F52A4 100%)',
      '--gradient-hero':      'linear-gradient(160deg, #1D6DB5 0%, #0F52A4 60%, #0A3F80 100%)',
      '--gradient-card':      'linear-gradient(135deg, #2E7EC5 0%, #1D6DB5 100%)',
      '--shadow-acento':      '0 4px 20px rgba(29,109,181,0.35)',
    },
  },
  {
    id:         'esmeralda',
    nombre:     'Esmeralda',
    descripcion: 'Verde naturaleza',
    color:      '#059669',
    colorGrad:  ['#10B981', '#047857'],
    vars: {
      '--color-acento':       '#059669',
      '--color-acento-dark':  '#047857',
      '--color-acento-light': '#10B981',
      '--color-acento-suave': '#ECFDF5',
      '--color-acento-suave2':'#F0FDF9',
      '--gradient-primary':   'linear-gradient(135deg, #059669 0%, #047857 100%)',
      '--gradient-hero':      'linear-gradient(160deg, #059669 0%, #047857 60%, #025F47 100%)',
      '--gradient-card':      'linear-gradient(135deg, #10B981 0%, #059669 100%)',
      '--shadow-acento':      '0 4px 20px rgba(5,150,105,0.35)',
    },
  },
  {
    id:         'carmesi',
    nombre:     'Carmesí',
    descripcion: 'Rojo intenso',
    color:      '#DC2626',
    colorGrad:  ['#EF4444', '#B91C1C'],
    vars: {
      '--color-acento':       '#DC2626',
      '--color-acento-dark':  '#B91C1C',
      '--color-acento-light': '#EF4444',
      '--color-acento-suave': '#FEF2F2',
      '--color-acento-suave2':'#FFF5F5',
      '--gradient-primary':   'linear-gradient(135deg, #DC2626 0%, #B91C1C 100%)',
      '--gradient-hero':      'linear-gradient(160deg, #DC2626 0%, #B91C1C 60%, #991B1B 100%)',
      '--gradient-card':      'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
      '--shadow-acento':      '0 4px 20px rgba(220,38,38,0.35)',
    },
  },
  {
    id:         'cobre',
    nombre:     'Cobre',
    descripcion: 'Naranja dorado',
    color:      '#D97706',
    colorGrad:  ['#F59E0B', '#B45309'],
    vars: {
      '--color-acento':       '#D97706',
      '--color-acento-dark':  '#B45309',
      '--color-acento-light': '#F59E0B',
      '--color-acento-suave': '#FEF3C7',
      '--color-acento-suave2':'#FFFBEB',
      '--gradient-primary':   'linear-gradient(135deg, #D97706 0%, #B45309 100%)',
      '--gradient-hero':      'linear-gradient(160deg, #B45309 0%, #92400E 60%, #78350F 100%)',
      '--gradient-card':      'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
      '--shadow-acento':      '0 4px 20px rgba(217,119,6,0.35)',
    },
  },
  {
    id:         'pizarra',
    nombre:     'Pizarra',
    descripcion: 'Gris oscuro elegante',
    color:      '#374151',
    colorGrad:  ['#4B5563', '#1F2937'],
    vars: {
      '--color-acento':       '#374151',
      '--color-acento-dark':  '#1F2937',
      '--color-acento-light': '#4B5563',
      '--color-acento-suave': '#F3F4F6',
      '--color-acento-suave2':'#F9FAFB',
      '--gradient-primary':   'linear-gradient(135deg, #4B5563 0%, #1F2937 100%)',
      '--gradient-hero':      'linear-gradient(160deg, #374151 0%, #1F2937 60%, #111827 100%)',
      '--gradient-card':      'linear-gradient(135deg, #4B5563 0%, #374151 100%)',
      '--shadow-acento':      '0 4px 20px rgba(55,65,81,0.35)',
    },
  },
]

// ── Store ──────────────────────────────────────────────────────────────────────
export const useThemeStore = defineStore('theme', () => {
  const temaActualId = ref('indigo')

  const temaActual = computed(
    () => TEMAS.find(t => t.id === temaActualId.value) ?? TEMAS[0]
  )

  /**
   * Aplica las variables CSS de un tema al elemento raíz del documento.
   * Se llama tanto al cargar como al cambiar el tema.
   */
  function _aplicarVars(vars) {
    const root = document.documentElement
    Object.entries(vars).forEach(([prop, val]) => root.style.setProperty(prop, val))
  }

  function _aplicarTema(id) {
    const tema = TEMAS.find(t => t.id === id) ?? TEMAS[0]
    _aplicarVars(tema.vars)
    temaActualId.value = tema.id
  }

  /**
   * Carga el tema guardado en las preferencias del dispositivo.
   * Si no existe, aplica el tema por defecto (índigo).
   * Llamar en App.vue → onMounted.
   */
  async function cargarTema() {
    try {
      const { value } = await Preferences.get({ key: 'tema_app' })
      _aplicarTema(value || 'indigo')
    } catch {
      _aplicarTema('indigo')
    }
  }

  /**
   * Cambia el tema, lo aplica inmediatamente y lo persiste.
   * @param {string} id — ID del tema (ver TEMAS)
   */
  async function cambiarTema(id) {
    _aplicarTema(id)
    try {
      await Preferences.set({ key: 'tema_app', value: id })
    } catch { /* Capacitor Preferences puede no estar disponible en el navegador */ }
  }

  return {
    temaActualId,
    temaActual,
    TEMAS,
    cargarTema,
    cambiarTema,
  }
})
