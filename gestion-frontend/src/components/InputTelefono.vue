<script setup>
/**
 * InputTelefono.vue — Input de teléfono chileno con prefijo "+56 9" fijo.
 *
 * El usuario solo ingresa los 8 dígitos finales.
 * Emite el número completo como "+56 9 XXXXXXXX" vía v-model.
 * Solo acepta dígitos en el campo editable.
 */
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  error:      { type: Boolean, default: false },
  disabled:   { type: Boolean, default: false },
  inputClass: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])

/** Extrae solo los 8 dígitos del número completo guardado */
function extraerDigitos(tel) {
  if (!tel) return ''
  const soloDigitos = tel.replace(/\D/g, '')   // "56941141540" o "941141540"
  if (soloDigitos.startsWith('569')) return soloDigitos.slice(3)
  if (soloDigitos.startsWith('56'))  return soloDigitos.slice(2).replace(/^9/, '')
  if (soloDigitos.startsWith('9'))   return soloDigitos.slice(1)
  return soloDigitos.slice(0, 8)
}

const digitos = ref(extraerDigitos(props.modelValue))

// Sincronizar si el valor cambia desde afuera (ej: carga de datos al editar)
watch(() => props.modelValue, (val) => {
  const nuevos = extraerDigitos(val)
  if (nuevos !== digitos.value) digitos.value = nuevos
})

function onInput(e) {
  // Solo dígitos, máximo 8
  digitos.value = e.target.value.replace(/\D/g, '').slice(0, 8)
  e.target.value = digitos.value
  emit('update:modelValue', digitos.value ? `+56 9 ${digitos.value}` : '')
}
</script>

<template>
  <div
    class="tel-input-wrap"
    :class="{ 'tel-input-error': error, 'tel-input-disabled': disabled }"
  >
    <span class="tel-prefix">+56 9</span>
    <input
      type="tel"
      inputmode="numeric"
      :value="digitos"
      :disabled="disabled"
      maxlength="8"
      placeholder="XXXXXXXX"
      autocomplete="tel"
      class="tel-digits"
      @input="onInput"
    />
  </div>
</template>

<style scoped>
.tel-input-wrap {
  display: flex;
  align-items: center;
  border: 1.5px solid #D1D5DB;
  border-radius: 10px;
  background: #fff;
  overflow: hidden;
  transition: border-color 0.15s, box-shadow 0.15s;
  width: 100%;
}
.tel-input-wrap:focus-within {
  border-color: #6366F1;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.12);
}
.tel-input-wrap.tel-input-error {
  border-color: #EF4444;
}
.tel-input-wrap.tel-input-disabled {
  background: #F9FAFB;
  opacity: 0.6;
}

.tel-prefix {
  padding: 0 0.625rem 0 0.875rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #6366F1;
  white-space: nowrap;
  user-select: none;
  border-right: 1.5px solid #E5E7EB;
  line-height: 1;
  /* Match the input height */
  align-self: stretch;
  display: flex;
  align-items: center;
}

.tel-digits {
  flex: 1;
  padding: 0.625rem 0.75rem;
  font-size: 0.875rem;
  color: #111827;
  background: transparent;
  border: none;
  outline: none;
  font-family: inherit;
  min-width: 0;
}
.tel-digits::placeholder {
  color: #9CA3AF;
  letter-spacing: 0.05em;
}
</style>
