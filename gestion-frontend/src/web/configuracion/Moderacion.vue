<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { apiFetch } from '../../utils/api.js'
import { useToast } from '../../utils/useToast.js'

const toast = useToast()

const palabras        = ref([])
const cargando        = ref(false)
const busqueda        = ref('')
const nuevaPalabra    = ref('')
const nuevasVariantes = ref('')
const archivoLote     = ref(null)
const nombreArchivo   = ref('')
const textoLote       = ref('')
const guardando       = ref(false)
const guardandoLote   = ref(false)

function seleccionarArchivo(e) {
  const file = e.target.files[0]
  if (!file) return
  nombreArchivo.value = file.name
  const reader = new FileReader()
  reader.onload = ev => { textoLote.value = ev.target.result }
  reader.readAsText(file, 'UTF-8')
}
const confirmEliminar  = ref(null)   // palabra a confirmar eliminación
const palabrasOcultas  = ref(false)

const POR_PAGINA = 15
const pagina     = ref(1)

const palabrasFiltradas = computed(() => {
  if (!busqueda.value) return palabras.value
  const b = busqueda.value.toLowerCase()
  return palabras.value.filter(p =>
    p.palabra.includes(b) || p.variantes.some(v => v.includes(b))
  )
})

const totalPaginas = computed(() => Math.max(1, Math.ceil(palabrasFiltradas.value.length / POR_PAGINA)))

const palabrasPagina = computed(() => {
  const inicio = (pagina.value - 1) * POR_PAGINA
  return palabrasFiltradas.value.slice(inicio, inicio + POR_PAGINA)
})

// Al buscar o recargar, volver a página 1
watch([busqueda, palabras], () => { pagina.value = 1 })

async function cargar() {
  cargando.value = true
  try {
    const res  = await apiFetch('/api/admin/moderacion/palabras/')
    const data = await res.json()
    palabras.value = data.palabras ?? []
  } catch {
    toast.error('Error al cargar el diccionario.')
  } finally {
    cargando.value = false
  }
}

async function agregar() {
  if (!nuevaPalabra.value.trim()) return
  const variantes = nuevasVariantes.value
    .split(',').map(v => v.trim()).filter(Boolean)
  guardando.value = true
  try {
    const res = await apiFetch('/api/admin/moderacion/palabras/agregar/', {
      method: 'POST',
      body: { palabra: nuevaPalabra.value.trim(), variantes },
    })
    if (!res.ok) throw new Error()
    nuevaPalabra.value    = ''
    nuevasVariantes.value = ''
    await cargar()
    toast.success('Palabra agregada al diccionario.')
  } catch {
    toast.error('Error al agregar la palabra.')
  } finally {
    guardando.value = false
  }
}

async function agregarLote() {
  if (!textoLote.value.trim()) return
  guardandoLote.value = true
  try {
    const res  = await apiFetch('/api/admin/moderacion/palabras/lote/', {
      method: 'POST',
      body: { texto: textoLote.value },
    })
    const data = await res.json()
    textoLote.value     = ''
    nombreArchivo.value = ''
    archivoLote.value   = null
    await cargar()
    toast.success(`${data.agregadas} palabra(s) nueva(s) agregada(s).`)
  } catch {
    toast.error('Error al agregar el lote.')
  } finally {
    guardandoLote.value = false
  }
}

async function eliminar(palabra) {
  try {
    const res = await apiFetch('/api/admin/moderacion/palabras/eliminar/', {
      method: 'DELETE',
      body: { palabra },
    })
    if (!res.ok) throw new Error()
    confirmEliminar.value = null
    await cargar()
    toast.success('Palabra eliminada.')
  } catch {
    toast.error('Error al eliminar la palabra.')
  }
}

function descargarPlantilla() {
  const contenido = [
    '# Plantilla de diccionario de moderación',
    '# Una palabra por línea.',
    '# Para agregar variantes usa el formato: palabra:variante1,variante2',
    '#',
    '# Ejemplos:',
    'insulto',
    'ofensa:ofens4,0fensa',
    'agravio:agrav10',
  ].join('\n')
  const blob = new Blob([contenido], { type: 'text/plain;charset=utf-8' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = 'plantilla_moderacion.txt'
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(cargar)
</script>

<template>
  <div class="flex flex-col gap-6">

    <!-- Agregar palabra individual -->
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">Agregar palabra</h2>
      </div>
      <div class="card-body flex flex-col gap-3">
        <div class="flex gap-3">
          <input
            v-model="nuevaPalabra"
            @keyup.enter="agregar"
            placeholder="Escribe la palabra..."
            class="input flex-1"
          />
          <button @click="agregar" :disabled="guardando || !nuevaPalabra.trim()" class="btn-primary shrink-0">
            {{ guardando ? 'Agregando...' : '+ Agregar' }}
          </button>
        </div>
        <input
          v-model="nuevasVariantes"
          placeholder="Variantes (opcional): var1, var2, var3"
          class="input"
        />
      </div>
    </div>

    <!-- Subir por lote (archivo .txt) -->
    <div class="card">
      <div class="card-header">
        <div>
          <h2 class="card-title">Carga masiva desde archivo</h2>
          <p class="card-desc">Archivo .txt — una palabra por línea. Variantes: <code>palabra:var1,var2</code></p>
        </div>
        <button @click="descargarPlantilla" class="btn-download" title="Descargar plantilla .txt">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1M12 4v12m0 0l-4-4m4 4l4-4"/>
          </svg>
          Plantilla
        </button>
      </div>
      <div class="card-body flex flex-col gap-3">
        <!-- Zona de carga -->
        <label class="upload-zone">
          <input
            type="file"
            accept=".txt,text/plain"
            class="sr-only"
            @change="seleccionarArchivo"
          />
          <div v-if="!nombreArchivo" class="flex flex-col items-center gap-1 text-gray-400">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
            <span class="text-sm font-medium">Haz clic para seleccionar un archivo .txt</span>
          </div>
          <div v-else class="flex items-center gap-2 text-indigo-700">
            <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <span class="text-sm font-semibold truncate">{{ nombreArchivo }}</span>
            <span class="text-xs text-gray-400 ml-1">({{ textoLote.split('\n').filter(l => l.trim()).length }} líneas)</span>
          </div>
        </label>

        <div class="flex justify-end">
          <button @click="agregarLote" :disabled="guardandoLote || !textoLote.trim()" class="btn-primary">
            {{ guardandoLote ? 'Procesando...' : '↑ Cargar archivo' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Diccionario actual -->
    <div class="card">
      <div class="card-header">
        <div>
          <h2 class="card-title">Diccionario actual</h2>
          <p class="card-desc">{{ palabras.length }} palabras registradas · mayúsculas y tildes ignoradas</p>
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="palabrasOcultas = !palabrasOcultas"
            class="btn-ocultar"
            :title="palabrasOcultas ? 'Mostrar palabras' : 'Ocultar palabras'"
          >
            <!-- Ojo abierto (mostrar) -->
            <svg v-if="palabrasOcultas" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
            </svg>
            <!-- Ojo tachado (ocultar) -->
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
            </svg>
            {{ palabrasOcultas ? 'Mostrar' : 'Ocultar' }}
          </button>
          <div class="search-wrap">
            <svg class="search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>
            <input v-model="busqueda" placeholder="Buscar..." class="input search-input" />
          </div>
        </div>
      </div>

      <div class="card-body p-0">
        <div v-if="cargando" class="p-8 flex justify-center">
          <div class="spinner"></div>
        </div>

        <div v-else-if="!palabrasFiltradas.length" class="p-8 text-center text-sm text-gray-400">
          {{ busqueda ? 'Sin coincidencias.' : 'El diccionario está vacío. Agrega palabras arriba.' }}
        </div>

        <div v-else class="divide-y divide-gray-50">
          <div
            v-for="item in palabrasPagina"
            :key="item.palabra"
            class="flex items-center gap-3 px-5 py-3 hover:bg-gray-50 transition"
          >
            <span class="font-semibold text-sm w-40 shrink-0" :class="palabrasOcultas ? 'texto-oculto' : 'text-gray-800'">
              {{ palabrasOcultas ? '●'.repeat(Math.min(item.palabra.length, 8)) : item.palabra }}
            </span>
            <span class="text-sm flex-1 truncate" :class="palabrasOcultas ? 'texto-oculto' : 'text-gray-400'">
              {{ palabrasOcultas
                ? (item.variantes.length ? item.variantes.map(v => '●'.repeat(Math.min(v.length, 6))).join(', ') : '—')
                : (item.variantes.length ? item.variantes.join(', ') : '—') }}
            </span>
            <button
              v-if="confirmEliminar !== item.palabra"
              @click="confirmEliminar = item.palabra"
              class="btn-eliminar shrink-0"
              title="Eliminar palabra"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
              </svg>
            </button>
            <div v-else class="flex items-center gap-2 shrink-0">
              <span class="text-xs text-red-600 font-medium">¿Eliminar?</span>
              <button @click="eliminar(item.palabra)" class="text-xs font-semibold text-red-600 hover:underline">Sí</button>
              <button @click="confirmEliminar = null" class="text-xs text-gray-400 hover:underline">No</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Paginación -->
      <div v-if="totalPaginas > 1" class="paginacion">
        <button @click="pagina--" :disabled="pagina === 1" class="btn-page">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
          </svg>
        </button>

        <span class="pag-info">
          Página <strong>{{ pagina }}</strong> de <strong>{{ totalPaginas }}</strong>
          <span class="text-gray-400"> · {{ palabrasFiltradas.length }} palabras</span>
        </span>

        <button @click="pagina++" :disabled="pagina === totalPaginas" class="btn-page">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
          </svg>
        </button>
      </div>

    </div>

  </div>
</template>

<style scoped>
.card         { background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; overflow: hidden; }
.card-header  { padding: 1rem 1.25rem; border-bottom: 1px solid #F3F4F6; display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.card-title   { font-size: 0.9375rem; font-weight: 600; color: #111827; margin: 0 0 0.15rem; }
.card-desc    { font-size: 0.8125rem; color: #6B7280; margin: 0; }
.card-body    { padding: 1.25rem; }
.input        {
  width: 100%; padding: 0.5rem 0.75rem;
  border: 1px solid #D1D5DB; border-radius: 8px;
  font-size: 0.875rem; font-family: inherit; color: #111827;
  outline: none; transition: border-color 0.15s;
}
.input:focus  { border-color: #6366F1; box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }
.btn-primary  {
  padding: 0.5rem 1.1rem; background: #4F46E5; color: #fff;
  border: none; border-radius: 8px; font-size: 0.875rem; font-weight: 500;
  cursor: pointer; font-family: inherit; transition: background 0.15s;
}
.btn-primary:hover:not(:disabled) { background: #4338CA; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.spinner {
  width: 26px; height: 26px;
  border: 3px solid #E5E7EB; border-top-color: #4F46E5;
  border-radius: 50%; animation: spin 0.75s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.btn-eliminar {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 0.375rem; border-radius: 8px; border: none;
  background: #FEF2F2; color: #EF4444; cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.btn-eliminar:hover { background: #FEE2E2; color: #DC2626; }

.search-wrap  { position: relative; width: 208px; flex-shrink: 0; }
.search-icon  {
  position: absolute; left: 0.6rem; top: 50%; transform: translateY(-50%);
  width: 1rem; height: 1rem; color: #9CA3AF; pointer-events: none;
}
.search-input { width: 100% !important; padding-left: 2rem; }

.paginacion {
  display: flex; align-items: center; justify-content: center; gap: 1rem;
  padding: 0.75rem 1.25rem; border-top: 1px solid #F3F4F6;
}
.pag-info { font-size: 0.8125rem; color: #374151; }
.btn-page {
  display: inline-flex; align-items: center; justify-content: center;
  width: 2rem; height: 2rem; border-radius: 8px;
  border: 1px solid #E5E7EB; background: #fff; cursor: pointer;
  color: #374151; transition: background 0.15s, border-color 0.15s;
}
.btn-page:hover:not(:disabled) { background: #F3F4F6; border-color: #D1D5DB; }
.btn-page:disabled { opacity: 0.35; cursor: not-allowed; }

.btn-ocultar {
  display: inline-flex; align-items: center; gap: 0.35rem;
  padding: 0.4rem 0.85rem;
  background: #fff; color: #374151;
  border: 1px solid #D1D5DB; border-radius: 8px;
  font-size: 0.8125rem; font-weight: 500; cursor: pointer;
  font-family: inherit; transition: background 0.15s, border-color 0.15s, color 0.15s;
  white-space: nowrap;
}
.btn-ocultar:hover { background: #F9FAFB; border-color: #9CA3AF; }

.texto-oculto { color: #D1D5DB; letter-spacing: 0.05em; }

.btn-download {
  display: inline-flex; align-items: center; gap: 0.4rem;
  padding: 0.4rem 0.85rem;
  background: #fff; color: #4F46E5;
  border: 1px solid #C7D2FE; border-radius: 8px;
  font-size: 0.8125rem; font-weight: 500; cursor: pointer;
  font-family: inherit; transition: background 0.15s, border-color 0.15s;
  white-space: nowrap;
}
.btn-download:hover { background: #EEF2FF; border-color: #A5B4FC; }
.w-4 { width: 1rem; } .h-4 { height: 1rem; }

.upload-zone {
  display: flex; align-items: center; justify-content: center;
  border: 2px dashed #D1D5DB; border-radius: 10px; padding: 1.5rem 1rem;
  cursor: pointer; transition: border-color 0.15s, background 0.15s;
  min-height: 80px;
}
.upload-zone:hover { border-color: #6366F1; background: #F5F3FF; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); }
code { font-family: monospace; font-size: 0.8rem; background: #F3F4F6; padding: 0.1rem 0.3rem; border-radius: 4px; }
</style>
