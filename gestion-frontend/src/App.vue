<script setup>
import { RouterView } from 'vue-router'
import PermisoToast from './components/PermisoToast.vue'
</script>

<template>
  <RouterView />
  <PermisoToast />
</template>

<style>
body {
  margin: 0;
  padding: 0;
}
</style>
