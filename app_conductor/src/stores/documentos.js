import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiFetch } from '@/services/api.js'

// Documentos del conductor
export const TIPOS_CONDUCTOR = [
  { value: 'licencia', label: 'Licencia de conducir', icono: 'ti-id', color: '#1D4ED8', colorSuave: '#EFF6FF' },
]

// Documentos del vehículo
export const TIPOS_VEHICULO = [
  { value: 'permiso_circulacion', label: 'Permiso de circulación', icono: 'ti-license',      color: '#059669', colorSuave: '#ECFDF5' },
  { value: 'revision_tecnica',    label: 'Revisión técnica',       icono: 'ti-tool',          color: '#D97706', colorSuave: '#FFFBEB' },
  { value: 'seguro_soap',         label: 'Seguro SOAP',            icono: 'ti-shield-check',  color: '#7C3AED', colorSuave: '#F5F3FF' },
]

const TODOS_TIPOS = [...TIPOS_CONDUCTOR, ...TIPOS_VEHICULO]

export const useDocumentosStore = defineStore('documentos', () => {
  const documentos = ref([])
  const cargando   = ref(false)
  const enviando   = ref(false)
  const error      = ref(null)

  // El doc más reciente de cada tipo
  const docPorTipo = computed(() => {
    const map = {}
    for (const t of TODOS_TIPOS) {
      const docs = documentos.value
        .filter(d => d.tipo === t.value)
        .sort((a, b) => b.id - a.id)
      map[t.value] = docs[0] || null
    }
    return map
  })

  async function cargarDocumentos() {
    cargando.value = true
    error.value    = null
    try {
      const data = await apiFetch('/api/empresa/documentos/')
      // Tolerar tanto { documentos: [...] } como array directo
      if (Array.isArray(data)) {
        documentos.value = data
      } else if (Array.isArray(data?.documentos)) {
        documentos.value = data.documentos
      } else {
        documentos.value = []
      }
    } catch (e) {
      error.value = e?.message || 'Error al cargar documentos'
    } finally {
      cargando.value = false
    }
  }

  async function subirDocumento(formData) {
    enviando.value = true
    error.value    = null
    try {
      const doc = await apiFetch('/api/empresa/documentos/', {
        method: 'POST',
        body: formData,
      })
      documentos.value.unshift(doc)
      return { success: true, doc }
    } catch (e) {
      error.value = e?.message || 'Error al subir el documento'
      return { success: false, error: error.value }
    } finally {
      enviando.value = false
    }
  }

  return {
    documentos,
    cargando,
    enviando,
    error,
    docPorTipo,
    cargarDocumentos,
    subirDocumento,
  }
})
