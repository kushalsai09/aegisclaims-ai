<script setup lang="ts">
import { onMounted, ref } from "vue";
import ErrorState from "@/components/ErrorState.vue";
import LoadingState from "@/components/LoadingState.vue";
import { api, ApiError } from "@/services/api";
import type { OperationsSummary } from "@/types";

const summary = ref<OperationsSummary | null>(null);
const loading = ref(true);
const error = ref<ApiError | null>(null);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    summary.value = await api<OperationsSummary>("/operations/summary");
  } catch (caught) {
    error.value =
      caught instanceof ApiError
        ? caught
        : new ApiError("Unexpected operations error", 500);
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="page-shell">
    <header class="page-header">
      <div>
        <span class="eyebrow">PLATFORM OPERATIONS</span>
        <h1>Operations</h1>
        <p>
          Service inventory and human-control workload for authorized oversight.
        </p>
      </div>
      <span class="status-chip status-chip--success">Services available</span>
    </header>
    <LoadingState v-if="loading" />
    <ErrorState
      v-else-if="error"
      :message="error.message"
      :correlation-id="error.correlationId"
      @retry="load"
    />
    <template v-else>
      <section
        class="metric-grid metric-grid--four"
        aria-label="System inventory"
      >
        <article class="metric-card">
          <span>Claims</span><strong>{{ summary?.claim_count }}</strong
          ><small>Authorized portfolio</small>
        </article>
        <article class="metric-card">
          <span>Documents</span><strong>{{ summary?.document_count }}</strong
          ><small>Source records</small>
        </article>
        <article class="metric-card">
          <span>Workflow runs</span
          ><strong>{{ summary?.workflow_count }}</strong
          ><small>Recorded executions</small>
        </article>
        <article class="metric-card">
          <span>Review tasks</span><strong>{{ summary?.review_count }}</strong
          ><small>Review workload records</small>
        </article>
      </section>
      <section class="surface operations-status">
        <div>
          <span class="eyebrow">OPERATING CONTROLS</span>
          <h2>Human authority is enforced</h2>
          <p>
            Model assistance and evidence workflows cannot approve or deny
            claims, issue payments, or perform external communications.
          </p>
        </div>
        <div class="control-list" aria-label="Operating controls">
          <span><strong>Session security</strong> Server managed</span>
          <span><strong>Evidence validation</strong> Required</span>
          <span><strong>Human review</strong> Active</span>
        </div>
      </section>
    </template>
  </div>
</template>
