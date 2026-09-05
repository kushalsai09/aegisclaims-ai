<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import ErrorState from "@/components/ErrorState.vue";
import LoadingState from "@/components/LoadingState.vue";
import { api, ApiError } from "@/services/api";
import { authState, hasRole } from "@/services/auth";
import type { ClaimSummary, Dashboard, ReviewTask } from "@/types";

const dashboard = ref<Dashboard | null>(null);
const claims = ref<ClaimSummary[]>([]);
const reviews = ref<ReviewTask[]>([]);
const loading = ref(true);
const error = ref<ApiError | null>(null);
const attentionClaims = computed(() =>
  claims.value.filter(
    (claim) => claim.workflow_status === "awaiting_human_review",
  ),
);
const recentClaims = computed(() =>
  [...claims.value]
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
    .slice(0, 5),
);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const requests: [
      Promise<Dashboard>,
      Promise<ClaimSummary[]>,
      Promise<ReviewTask[]>,
    ] = [
      api<Dashboard>("/dashboard"),
      api<ClaimSummary[]>("/claims"),
      hasRole("supervisor", "admin")
        ? api<ReviewTask[]>("/review-tasks")
        : Promise.resolve([]),
    ];
    [dashboard.value, claims.value, reviews.value] =
      await Promise.all(requests);
  } catch (caught) {
    error.value =
      caught instanceof ApiError
        ? caught
        : new ApiError("Your work could not be loaded.", 500);
  } finally {
    loading.value = false;
  }
}
function label(value: string) {
  return value.replaceAll("_", " ");
}
function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}
onMounted(load);
</script>

<template>
  <div class="page-shell page-shell--wide">
    <header class="page-header">
      <div>
        <span class="eyebrow">MY WORK</span>
        <h1>
          Good morning,
          {{
            authState.session?.user.first_name ||
            authState.session?.user.display_name.split(" ")[0]
          }}
        </h1>
        <p>Prioritized claim and review work available to you.</p>
      </div>
      <span class="status-chip status-chip--success"
        ><span class="status-dot"></span>Services available</span
      >
    </header>
    <LoadingState v-if="loading" />
    <ErrorState
      v-else-if="error"
      :message="error.message"
      :correlation-id="error.correlationId"
      @retry="load"
    />
    <template v-else>
      <section class="work-summary" aria-label="Work summary">
        <RouterLink to="/claims" class="work-stat"
          ><span>Assigned claims</span
          ><strong>{{ dashboard?.assigned_claims }}</strong
          ><small>Open your claim inventory</small></RouterLink
        >
        <RouterLink
          v-if="hasRole('supervisor', 'admin')"
          to="/reviews"
          class="work-stat work-stat--attention"
          ><span>Reviews awaiting action</span
          ><strong>{{ reviews.length }}</strong
          ><small>Open the review queue</small></RouterLink
        >
        <article v-else class="work-stat">
          <span>Claims needing attention</span
          ><strong>{{ attentionClaims.length }}</strong
          ><small>Human review or additional evidence</small>
        </article>
        <article class="work-stat">
          <span>Recently updated</span><strong>{{ recentClaims.length }}</strong
          ><small>Within your authorized portfolio</small>
        </article>
      </section>
      <div class="dashboard-grid">
        <section class="data-surface" aria-labelledby="recent-claims-title">
          <div class="table-toolbar">
            <div>
              <span class="eyebrow">RECENT WORK</span>
              <h2 id="recent-claims-title">Recently updated claims</h2>
            </div>
            <RouterLink to="/claims">View all claims</RouterLink>
          </div>
          <div v-if="recentClaims.length" class="compact-claim-list">
            <RouterLink
              v-for="claim in recentClaims"
              :key="claim.id"
              :to="`/claims/${claim.id}`"
              ><div>
                <strong>{{ claim.claim_number }}</strong
                ><span>{{ claim.loss_type }}</span
                ><small>{{ claim.property_address }}</small>
              </div>
              <div>
                <span
                  class="status-chip"
                  :class="
                    claim.workflow_status === 'awaiting_human_review'
                      ? 'status-chip--amber'
                      : 'status-chip--neutral'
                  "
                  >{{ label(claim.workflow_status) }}</span
                ><small>Updated {{ formatDate(claim.updated_at) }}</small>
              </div></RouterLink
            >
          </div>
          <div v-else class="compact-empty">
            No claims are currently assigned to you.
          </div>
        </section>
        <aside
          class="surface attention-panel"
          aria-labelledby="attention-title"
        >
          <span class="eyebrow">ATTENTION</span>
          <h2 id="attention-title">What needs review</h2>
          <template v-if="attentionClaims.length"
            ><p>
              {{ attentionClaims.length }} claim{{
                attentionClaims.length === 1 ? "" : "s"
              }}
              have evidence or workflow conditions requiring human attention.
            </p>
            <RouterLink class="secondary-button" to="/claims"
              >Review affected claims</RouterLink
            ></template
          ><template v-else
            ><div class="empty-icon" aria-hidden="true">✓</div>
            <p>No assigned claims currently require escalation.</p></template
          >
        </aside>
      </div>
    </template>
  </div>
</template>
