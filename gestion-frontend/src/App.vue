<script setup>
import { RouterView } from 'vue-router'
import PermisoToast  from './components/PermisoToast.vue'
import AppToast      from './components/AppToast.vue'
import ErrorBoundary from './components/ErrorBoundary.vue'
</script>

<template>
  <ErrorBoundary>
    <RouterView />
  </ErrorBoundary>
  <PermisoToast />
  <AppToast />
</template>

<style>
body {
  margin: 0;
  padding: 0;
}
</style>
