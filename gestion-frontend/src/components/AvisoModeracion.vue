<template>
  <Transition name="slide">
    <div
      v-if="aviso"
      class="flex gap-2.5 items-start mt-1.5 px-3.5 py-2.5 rounded-lg border border-amber-200 bg-amber-50"
    >
      <svg class="w-4 h-4 text-amber-600 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>
      </svg>
      <div>
        <p class="text-xs font-semibold text-amber-800 mb-0.5">Lenguaje inapropiado</p>
        <p class="text-xs text-amber-700">{{ aviso }}</p>
        <p v-if="sugerencia" class="text-[11px] text-amber-600 mt-1 italic">{{ sugerencia }}</p>
      </div>
    </div>
  </Transition>
</template>

<script setup>
defineProps({ aviso: String, sugerencia: String })
</script>

<style scoped>
.slide-enter-active, .slide-leave-active { transition: all .18s ease; }
.slide-enter-from, .slide-leave-to       { opacity: 0; transform: translateY(-4px); }
</style>
