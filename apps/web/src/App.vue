<script setup lang="ts">
import { RouterView } from "vue-router";
import AppShell from "@/components/AppShell.vue";
import { authState } from "@/services/auth";
</script>

<template>
  <div v-if="!authState.initialized" class="app-boot" role="status">
    Loading secure workspace…
  </div>
  <AppShell v-else-if="authState.session"><RouterView /></AppShell>
  <RouterView v-else />
</template>
