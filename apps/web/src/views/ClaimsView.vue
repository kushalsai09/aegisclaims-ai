<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import ErrorState from "@/components/ErrorState.vue";
import LoadingState from "@/components/LoadingState.vue";
import { api, ApiError } from "@/services/api";
import type { ClaimSummary } from "@/types";

const claims = ref<ClaimSummary[]>([]);
const loading = ref(true);
const error = ref<ApiError | null>(null);
const query = ref("");
const workflow = ref("all");
const sort = ref("updated");

const visibleClaims = computed(() => {
  const search = query.value.trim().toLowerCase();
  return [...claims.value]
    .filter(
      (claim) =>
        workflow.value === "all" || claim.workflow_status === workflow.value,
    )
    .filter(
      (claim) =>
        !search ||
        [
          claim.claim_number,
          claim.property_address,
          claim.loss_type,
          claim.policy_number,
          claim.assigned_to ?? "",
        ].some((value) => value.toLowerCase().includes(search)),
    )
    .sort((left, right) =>
      sort.value === "loss_date"
        ? right.loss_date.localeCompare(left.loss_date)
        : sort.value === "claim_number"
          ? left.claim_number.localeCompare(right.claim_number)
          : right.updated_at.localeCompare(left.updated_at),
    );
});

async function load() {
  loading.value = true;
  error.value = null;
  try {
    claims.value = await api<ClaimSummary[]>("/claims");
  } catch (caught) {
    error.value =
      caught instanceof ApiError
        ? caught
        : new ApiError("Claims could not be loaded.", 500);
  } finally {
    loading.value = false;
  }
}
function label(value: string) {
  return value.replaceAll("_", " ");
}
function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
    new Date(value),
  );
}
onMounted(load);
</script>

<template>
  <div class="page-shell page-shell--wide">
    <header class="page-header">
      <div>
        <span class="eyebrow">CLAIM INVENTORY</span>
        <h1>Claims</h1>
        <p>Find and open claims available to your role and assignment.</p>
      </div>
    </header>
    <LoadingState v-if="loading" />
    <ErrorState
      v-else-if="error"
      :message="error.message"
      :correlation-id="error.correlationId"
      @retry="load"
    />
    <template v-else>
      <section class="filter-bar" aria-label="Claim filters">
        <label class="search-field"
          ><span class="sr-only">Search claims</span
          ><input
            v-model="query"
            type="search"
            placeholder="Search claim, address, policy, or assignee"
        /></label>
        <label
          ><span>Workflow</span
          ><select v-model="workflow">
            <option value="all">All workflow states</option>
            <option value="completed">Completed</option>
            <option value="awaiting_human_review">Awaiting human review</option>
            <option value="not_started">Not started</option>
          </select></label
        >
        <label
          ><span>Sort</span
          ><select v-model="sort">
            <option value="updated">Recently updated</option>
            <option value="loss_date">Loss date</option>
            <option value="claim_number">Claim number</option>
          </select></label
        >
      </section>
      <section class="data-surface" aria-labelledby="claims-results-title">
        <div class="table-toolbar">
          <div>
            <h2 id="claims-results-title">Claim results</h2>
            <p aria-live="polite">
              {{ visibleClaims.length }} of {{ claims.length }} claims
            </p>
          </div>
        </div>
        <div
          v-if="visibleClaims.length"
          class="claims-table enterprise-table"
          role="table"
          aria-label="Claims"
        >
          <div class="claims-row claims-row--header" role="row">
            <span role="columnheader">Claim</span
            ><span role="columnheader">Loss</span
            ><span role="columnheader">Assignment</span
            ><span role="columnheader">Status</span
            ><span role="columnheader">Updated</span><span></span>
          </div>
          <RouterLink
            v-for="claim in visibleClaims"
            :key="claim.id"
            :to="`/claims/${claim.id}`"
            class="claims-row"
            role="row"
          >
            <span role="cell"
              ><strong>{{ claim.claim_number }}</strong
              ><small>{{ claim.property_address }}</small></span
            >
            <span role="cell"
              ><strong>{{ claim.loss_type }}</strong
              ><small
                >{{ formatDate(claim.loss_date) }} ·
                {{ claim.policy_number }}</small
              ></span
            >
            <span role="cell"
              ><strong>{{ claim.assigned_to ?? "Unassigned" }}</strong></span
            >
            <span role="cell"
              ><span class="status-chip status-chip--success">{{
                label(claim.status)
              }}</span
              ><small>{{ label(claim.workflow_status) }}</small></span
            >
            <span role="cell">{{ formatDate(claim.updated_at) }}</span
            ><span class="row-action" aria-hidden="true">Open →</span>
          </RouterLink>
        </div>
        <div v-else class="empty-state">
          <h2>No claims match these filters</h2>
          <p>Clear or adjust the search and workflow filter.</p>
          <button
            class="secondary-button"
            @click="
              query = '';
              workflow = 'all';
            "
          >
            Clear filters
          </button>
        </div>
      </section>
    </template>
  </div>
</template>
