<script setup>
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { Preferences } from '@capacitor/preferences'

/** Cargar tema guardado y aplicar variables CSS al :root */
onMounted(async () => {
  try {
    const { value: acento } = await Preferences.get({ key: 'color_acento' })
    if (acento) {
      document.documentElement.style.setProperty('--color-acento', acento)
    }
  } catch {
    // Sin tema guardado — se usa el valor por defecto del CSS
  }
})
</script>

<template>
  <RouterView />
</template>
