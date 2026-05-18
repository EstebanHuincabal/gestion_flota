<script setup>
import { ref, watch } from 'vue'
import { PRESETS_COLOR, FUENTES, useTema } from '../../../utils/tema.js'

const {
  colorActual, customActual, densidadActual, radioActual, fuenteActual,
  cambiar, cambiarCustom, cambiarDensidad, cambiarRadio, cambiarFuente,
} = useTema()

// ── Color ──────────────────────────────────────────────
const modoColor   = ref(colorActual() === 'custom' ? 'custom' : 'preset')
const presetActivo = ref(colorActual() === 'custom' ? null : colorActual())

const savedCustom = customActual() || { from: '#4F46E5', to: '#7C3AED', accent: '#7C3AED' }
const customFrom   = ref(savedCustom.from)
const customTo     = ref(savedCustom.to)
const customAccent = ref(savedCustom.accent)

const elegirPreset = (key) => {
  presetActivo.value = key
  modoColor.value    = 'preset'
  cambiar(key)
}

const actualizarCustom = () => {
  presetActivo.value = null
  modoColor.value    = 'custom'
  cambiarCustom({ from: customFrom.value, to: customTo.value, accent: customAccent.value })
}

// Aplicar en tiempo real al mover los pickers
watch([customFrom, customTo, customAccent], actualizarCustom)

// ── Densidad ───────────────────────────────────────────
const DENSIDADES = [
  { key: 'compact',  label: 'Compacto', desc: 'Más información en menos espacio' },
  { key: 'normal',   label: 'Normal',   desc: 'Tamaño predeterminado del sistema' },
  { key: 'spacious', label: 'Amplio',   desc: 'Mayor separación y legibilidad' },
]
const densidad = ref(densidadActual())
const elegirDensidad = (key) => {
  densidad.value = key
  cambiarDensidad(key)
}

// ── Radio ──────────────────────────────────────────────
const RADIOS = [
  { key: 'sharp',  label: 'Recto',  ejemplo: '4px'  },
  { key: 'normal', label: 'Normal', ejemplo: '12px' },
  { key: 'soft',   label: 'Suave',  ejemplo: '20px' },
]
const radio = ref(radioActual())
const elegirRadio = (key) => {
  radio.value = key
  cambiarRadio(key)
}

// ── Tipografía ─────────────────────────────────────────
const fuente = ref(fuenteActual())
const elegirFuente = (key) => {
  fuente.value = key
  cambiarFuente(key)
}
</script>

<template>
  <div class="tab-content">

    <!-- ── Sección: Color del sistema ── -->
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">Color del sistema</h2>
        <p class="card-desc">Personaliza el color de la barra lateral y los acentos de la interfaz</p>
      </div>
      <div class="card-body">

        <!-- Toggle modo -->
        <div class="mode-toggle">
          <button :class="['mode-btn', { active: modoColor === 'preset' }]" @click="modoColor = 'preset'">
            Presets
          </button>
          <button :class="['mode-btn', { active: modoColor === 'custom' }]" @click="modoColor = 'custom'">
            Personalizado
          </button>
        </div>

        <!-- Presets -->
        <div v-if="modoColor === 'preset'" class="presets-grid">
          <button
            v-for="p in PRESETS_COLOR"
            :key="p.key"
            :class="['preset-btn', { active: presetActivo === p.key }]"
            @click="elegirPreset(p.key)"
          >
            <span class="preset-swatch" :style="{ background: `linear-gradient(135deg, ${p.from}, ${p.to})` }"/>
            <span class="preset-label">{{ p.label }}</span>
            <span v-if="presetActivo === p.key" class="preset-check">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
              </svg>
            </span>
          </button>
        </div>

        <!-- Color personalizado -->
        <div v-else class="custom-section">
          <div class="custom-pickers">
            <div class="picker-group">
              <label class="picker-label">Color inicio</label>
              <div class="picker-row">
                <input type="color" v-model="customFrom" class="color-input" />
                <span class="color-hex">{{ customFrom }}</span>
              </div>
            </div>
            <div class="picker-group">
              <label class="picker-label">Color fin</label>
              <div class="picker-row">
                <input type="color" v-model="customTo" class="color-input" />
                <span class="color-hex">{{ customTo }}</span>
              </div>
            </div>
            <div class="picker-group">
              <label class="picker-label">Color acento</label>
              <div class="picker-row">
                <input type="color" v-model="customAccent" class="color-input" />
                <span class="color-hex">{{ customAccent }}</span>
              </div>
            </div>
          </div>

          <!-- Preview -->
          <div class="custom-preview">
            <div class="preview-sidebar" :style="{ background: `linear-gradient(160deg, ${customFrom} 0%, ${customTo} 100%)` }">
              <div class="preview-brand"/>
              <div class="preview-item"/>
              <div class="preview-item active" :style="{ background: `rgba(255,255,255,0.18)` }"/>
              <div class="preview-item"/>
              <div class="preview-item"/>
            </div>
            <div class="preview-content">
              <div class="preview-topbar"/>
              <div class="preview-body">
                <div class="preview-card"/>
                <div class="preview-card"/>
                <div class="preview-accent" :style="{ background: customAccent }"/>
              </div>
            </div>
          </div>
          <p class="hint">Los colores se aplican en tiempo real.</p>
        </div>

      </div>
    </div>

    <!-- ── Sección: Densidad ── -->
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">Densidad de la interfaz</h2>
        <p class="card-desc">Ajusta el tamaño general de la interfaz según tu preferencia</p>
      </div>
      <div class="card-body">
        <div class="density-grid">
          <button
            v-for="d in DENSIDADES"
            :key="d.key"
            :class="['density-btn', { active: densidad === d.key }]"
            @click="elegirDensidad(d.key)"
          >
            <div class="density-icon">
              <div v-if="d.key === 'compact'"  class="density-bars compact-bars">
                <div/><div/><div/><div/><div/>
              </div>
              <div v-else-if="d.key === 'normal'" class="density-bars normal-bars">
                <div/><div/><div/><div/>
              </div>
              <div v-else class="density-bars spacious-bars">
                <div/><div/><div/>
              </div>
            </div>
            <span class="density-label">{{ d.label }}</span>
            <span class="density-desc">{{ d.desc }}</span>
            <span v-if="densidad === d.key" class="active-dot" :style="{ background: 'var(--color-accent, #4F46E5)' }"/>
          </button>
        </div>
        <p class="hint">El cambio afecta el tamaño del texto y del espaciado de la interfaz.</p>
      </div>
    </div>

    <!-- ── Sección: Radio de bordes ── -->
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">Radio de bordes</h2>
        <p class="card-desc">Controla qué tan redondeados se ven los elementos del sistema</p>
      </div>
      <div class="card-body">
        <div class="radius-grid">
          <button
            v-for="r in RADIOS"
            :key="r.key"
            :class="['radius-btn', { active: radio === r.key }]"
            @click="elegirRadio(r.key)"
          >
            <div
              class="radius-preview"
              :style="{
                borderRadius: r.ejemplo,
                borderColor: radio === r.key ? 'var(--color-accent, #4F46E5)' : '#D1D5DB',
              }"
            />
            <span class="radius-label">{{ r.label }}</span>
            <span class="radius-val">{{ r.ejemplo }}</span>
          </button>
        </div>
        <p class="hint">El cambio aplica a tarjetas, inputs y botones del sistema.</p>
      </div>
    </div>

    <!-- ── Sección: Tipografía ── -->
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">Tipografía</h2>
        <p class="card-desc">Elige la fuente de texto que se usará en toda la interfaz</p>
      </div>
      <div class="card-body">
        <div class="fonts-grid">
          <button
            v-for="f in FUENTES"
            :key="f.key"
            :class="['font-btn', { active: fuente === f.key }]"
            @click="elegirFuente(f.key)"
            :style="{ fontFamily: f.family }"
          >
            <span class="font-preview">Aa</span>
            <span class="font-nombre">{{ f.label }}</span>
            <span class="font-muestra" :style="{ fontFamily: f.family }">
              El veloz murciélago
            </span>
            <span v-if="fuente === f.key" class="font-check">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
              </svg>
            </span>
          </button>
        </div>
        <p class="hint">Las fuentes externas se cargan desde Google Fonts al seleccionarlas.</p>
      </div>
    </div>

  </div>
</template>

<style scoped>
.tab-content { display: flex; flex-direction: column; gap: 1.25rem; }

/* ── Card base ── */
.card {
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: var(--radius-card, 12px);
  overflow: hidden;
}
.card-header {
  padding: 1.25rem 1.5rem 1rem;
  border-bottom: 1px solid #F3F4F6;
}
.card-title { font-size: 1rem; font-weight: 600; color: #111827; margin: 0 0 0.25rem; }
.card-desc  { font-size: 0.8125rem; color: #6B7280; margin: 0; }
.card-body  { padding: 1.5rem; }
.hint { font-size: 0.75rem; color: #9CA3AF; margin: 0.75rem 0 0; }

/* ── Toggle modo ── */
.mode-toggle {
  display: inline-flex;
  background: #F3F4F6;
  border-radius: 8px;
  padding: 3px;
  margin-bottom: 1.25rem;
}
.mode-btn {
  padding: 0.375rem 1rem;
  border: none;
  border-radius: 6px;
  background: transparent;
  font-size: 0.8125rem;
  font-weight: 500;
  color: #6B7280;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.mode-btn.active { background: #fff; color: #111827; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }

/* ── Presets grid ── */
.presets-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
}
.preset-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 0.5rem;
  border: 2px solid #E5E7EB;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  position: relative;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.preset-btn:hover { border-color: #9CA3AF; }
.preset-btn.active {
  border-color: var(--color-accent, #4F46E5);
  box-shadow: 0 0 0 3px rgba(99,102,241,0.14);
}
.preset-swatch {
  width: 42px; height: 42px; border-radius: 50%;
  box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}
.preset-label { font-size: 0.75rem; font-weight: 500; color: #374151; }
.preset-check {
  position: absolute; top: 6px; right: 6px;
  width: 18px; height: 18px;
  background: var(--color-accent, #4F46E5);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
}
.preset-check svg { width: 10px; height: 10px; stroke: #fff; }

/* ── Custom pickers ── */
.custom-section { display: flex; flex-direction: column; gap: 1.25rem; }
.custom-pickers {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}
.picker-group { display: flex; flex-direction: column; gap: 0.5rem; }
.picker-label { font-size: 0.8125rem; font-weight: 500; color: #374151; }
.picker-row { display: flex; align-items: center; gap: 0.625rem; }
.color-input {
  width: 44px; height: 44px;
  padding: 2px; border: 2px solid #E5E7EB;
  border-radius: 10px; cursor: pointer;
  background: #fff;
}
.color-hex { font-size: 0.8125rem; font-family: monospace; color: #6B7280; }

/* ── Preview de color personalizado ── */
.custom-preview {
  display: flex;
  height: 100px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #E5E7EB;
}
.preview-sidebar {
  width: 52px;
  display: flex; flex-direction: column; gap: 4px;
  padding: 8px 6px;
  flex-shrink: 0;
}
.preview-brand {
  height: 12px; border-radius: 4px;
  background: rgba(255,255,255,0.35); margin-bottom: 4px;
}
.preview-item {
  height: 10px; border-radius: 4px;
  background: rgba(255,255,255,0.2);
}
.preview-item.active { background: rgba(255,255,255,0.45); }
.preview-content {
  flex: 1; display: flex; flex-direction: column;
  background: #F8FAFC;
}
.preview-topbar {
  height: 20px; background: #fff;
  border-bottom: 1px solid #E5E7EB;
}
.preview-body {
  flex: 1; padding: 8px; display: flex; gap: 6px; align-items: center;
}
.preview-card {
  flex: 1; height: 40px; background: #fff;
  border: 1px solid #E5E7EB; border-radius: 6px;
}
.preview-accent {
  width: 32px; height: 26px; border-radius: 6px;
}

/* ── Densidad ── */
.density-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.875rem;
}
.density-btn {
  display: flex; flex-direction: column; align-items: center;
  gap: 0.5rem; padding: 1rem 0.75rem;
  border: 2px solid #E5E7EB; border-radius: 10px;
  background: #fff; cursor: pointer; position: relative;
  transition: border-color 0.15s;
  text-align: center;
}
.density-btn:hover { border-color: #9CA3AF; }
.density-btn.active {
  border-color: var(--color-accent, #4F46E5);
  background: #FAFAFA;
}
.density-icon {
  width: 44px; height: 36px;
  display: flex; flex-direction: column;
  justify-content: center;
}
.density-bars { display: flex; flex-direction: column; gap: 3px; width: 100%; }
.density-bars > div { height: 4px; background: #D1D5DB; border-radius: 2px; }
.density-btn.active .density-bars > div { background: var(--color-accent, #4F46E5); opacity: 0.5; }

.compact-bars  { gap: 2px; }
.compact-bars  > div { height: 3px; }
.normal-bars   > div { height: 4px; }
.spacious-bars { gap: 5px; }
.spacious-bars > div { height: 5px; }

.density-label { font-size: 0.875rem; font-weight: 600; color: #111827; }
.density-desc  { font-size: 0.7rem; color: #9CA3AF; line-height: 1.3; }
.active-dot {
  position: absolute; top: 8px; right: 8px;
  width: 8px; height: 8px; border-radius: 50%;
}

/* ── Radio ── */
.radius-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.875rem;
}
.radius-btn {
  display: flex; flex-direction: column; align-items: center;
  gap: 0.5rem; padding: 1rem 0.75rem;
  border: 2px solid #E5E7EB; border-radius: 10px;
  background: #fff; cursor: pointer;
  transition: border-color 0.15s;
}
.radius-btn:hover { border-color: #9CA3AF; }
.radius-btn.active { border-color: var(--color-accent, #4F46E5); background: #FAFAFA; }

.radius-preview {
  width: 44px; height: 32px;
  border: 2px solid #D1D5DB;
  background: #F3F4F6;
  transition: border-radius 0.2s, border-color 0.15s;
}
.radius-btn.active .radius-preview { background: #EEF2FF; }

.radius-label { font-size: 0.875rem; font-weight: 600; color: #111827; }
.radius-val   { font-size: 0.75rem; color: #9CA3AF; font-family: monospace; }

/* ── Tipografía ── */
.fonts-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.875rem;
}
.font-btn {
  display: flex; flex-direction: column; align-items: center;
  gap: 0.375rem; padding: 1.125rem 0.75rem;
  border: 2px solid #E5E7EB; border-radius: 10px;
  background: #fff; cursor: pointer; position: relative;
  transition: border-color 0.15s;
  text-align: center;
}
.font-btn:hover { border-color: #9CA3AF; }
.font-btn.active {
  border-color: var(--color-accent, #4F46E5);
  background: #FAFAFA;
}
.font-preview {
  font-size: 1.75rem; font-weight: 700;
  color: #111827; line-height: 1;
}
.font-btn.active .font-preview { color: var(--color-accent, #4F46E5); }
.font-nombre {
  font-size: 0.8125rem; font-weight: 600; color: #374151;
}
.font-muestra {
  font-size: 0.75rem; color: #9CA3AF; line-height: 1.4;
}
.font-check {
  position: absolute; top: 8px; right: 8px;
  width: 18px; height: 18px;
  background: var(--color-accent, #4F46E5);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
}
.font-check svg { width: 10px; height: 10px; stroke: #fff; }
</style>
