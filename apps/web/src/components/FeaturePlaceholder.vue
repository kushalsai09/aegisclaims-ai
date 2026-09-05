<script setup lang="ts">
defineProps<{ title: string; description: string }>();
</script>

<template>
  <section class="feature-placeholder" :aria-label="title">
    <div class="feature-icon" aria-hidden="true">◇</div>
    <div>
      <div class="feature-heading">
        <h3>{{ title }}</h3>
        <span class="status-chip status-chip--neutral">Not implemented</span>
      </div>
      <p>{{ description }}</p>
    </div>
  </section>
</template>
