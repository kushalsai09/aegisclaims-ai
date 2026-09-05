<script setup lang="ts">
import { onMounted, ref } from "vue";
import ErrorState from "@/components/ErrorState.vue";
import LoadingState from "@/components/LoadingState.vue";
import { api, ApiError } from "@/services/api";
import type { ReviewTask } from "@/types";

const tasks = ref<ReviewTask[]>([]);
const loading = ref(true);
const error = ref<ApiError | null>(null);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    tasks.value = await api<ReviewTask[]>("/review-tasks");
  } catch (caught) {
    error.value =
      caught instanceof ApiError
        ? caught
        : new ApiError("Unexpected review error", 500);
  } finally {
    loading.value = false;
  }
}

onMounted(load);

function label(value: string) {
  return value.replaceAll("_", " ").replaceAll(",", " · ");
}

function reviewReason(value: string) {
  const normalized = value.replace("SYNTHETIC DEMONSTRATION RULE — ", "");
  if (normalized.toLowerCase() === "this scenario requires human review.") {
    return "Policy or evidence conditions require authorized review.";
  }
  return label(normalized);
}

function age(value: string) {
  const milliseconds = Math.max(0, Date.now() - new Date(value).getTime());
  const minutes = Math.floor(milliseconds / 60000);
  if (minutes < 60) return `${minutes}m old`;
  const hours = Math.floor(minutes / 60);
  return hours < 24 ? `${hours}h old` : `${Math.floor(hours / 24)}d old`;
}
</script>

<template>
  <div class="page-shell">
    <header class="page-header">
      <div>
        <span class="eyebrow">HUMAN OVERSIGHT</span>
        <h1>Review queue</h1>
        <p>Prioritized evidence reviews requiring authorized action.</p>
      </div>
      <span class="status-chip status-chip--success">Human control active</span>
    </header>
    <LoadingState v-if="loading" />
    <ErrorState
      v-else-if="error"
      :message="error.message"
      :correlation-id="error.correlationId"
      @retry="load"
    />
    <section v-else-if="!tasks.length" class="surface empty-state">
      <div class="empty-icon" aria-hidden="true">✓</div>
      <h2>No review tasks</h2>
      <p>
        No controlled workflows currently require an authorized human response.
      </p>
    </section>
    <section
      v-else
      class="data-surface review-list"
      aria-label="Open review tasks"
    >
      <div class="review-row review-row--header" aria-hidden="true">
        <span>Claim and reason</span><span>Evidence flags</span
        ><span>Workflow</span><span>Age / owner</span><span></span>
      </div>
      <RouterLink
        v-for="task in tasks"
        :key="task.id"
        :to="`/claims/${task.claim_id}#workflow-title`"
        class="review-row"
      >
        <div>
          <span class="eyebrow">{{
            task.claim_number ?? "Authorized claim"
          }}</span>
          <strong>{{ reviewReason(task.reason) }}</strong>
        </div>
        <div class="review-flags">
          <span
            v-for="flag in task.safety_flags"
            :key="flag"
            class="status-chip status-chip--amber"
            >{{ label(flag) }}</span
          >
        </div>
        <span class="status-chip status-chip--neutral">{{
          label(task.workflow_status ?? task.status)
        }}</span>
        <div class="review-owner">
          <strong>{{ age(task.created_at) }}</strong
          ><small>{{ task.assigned_to ?? "Unassigned" }}</small>
        </div>
        <span class="row-action" aria-hidden="true">Review →</span>
      </RouterLink>
    </section>
  </div>
</template>
