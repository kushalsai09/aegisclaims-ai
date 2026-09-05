<script setup lang="ts">
defineProps<{ message: string; correlationId?: string }>();
defineEmits<{ retry: [] }>();
</script>

<template>
  <div class="error-state" role="alert">
    <strong>We couldn’t load this view.</strong>
    <p>{{ message }}</p>
    <p v-if="correlationId" class="correlation">
      Reference: {{ correlationId }}
    </p>
    <button class="button button--secondary" @click="$emit('retry')">
      Try again
    </button>
  </div>
</template>
