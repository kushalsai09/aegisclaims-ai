<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api, ApiError } from "@/services/api";
import { hasRole } from "@/services/auth";
import type { ControlledWorkflow, WorkflowHistory } from "@/types";

const props = defineProps<{ claimId: string }>();
const workflow = ref<ControlledWorkflow | null>(null);
const history = ref<WorkflowHistory | null>(null);
const task = ref(
  "Review the claim evidence and identify supported facts, conflicts, and missing information.",
);
const loading = ref(true);
const submitting = ref(false);
const error = ref<ApiError | null>(null);
const reviewReason = ref("");
const reviewer = computed(() => hasRole("supervisor", "admin"));

function key(prefix: string) {
  return `${prefix}-${props.claimId}-${Date.now()}`;
}

async function load() {
  loading.value = true;
  error.value = null;
  try {
    workflow.value = await api<ControlledWorkflow | null>(
      `/claims/${props.claimId}/workflows/latest`,
    );
    if (workflow.value) await loadHistory();
  } catch (caught) {
    error.value =
      caught instanceof ApiError
        ? caught
        : new ApiError("Unable to load workflow", 500);
  } finally {
    loading.value = false;
  }
}

async function loadHistory() {
  if (!workflow.value) return;
  history.value = await api<WorkflowHistory>(
    `/workflows/${workflow.value.id}/history`,
  );
}

async function start() {
  submitting.value = true;
  error.value = null;
  try {
    workflow.value = await api<ControlledWorkflow>(
      `/claims/${props.claimId}/workflows`,
      {
        method: "POST",
        body: JSON.stringify({
          task: task.value,
          idempotency_key: key("workflow"),
        }),
      },
    );
    await loadHistory();
  } catch (caught) {
    error.value =
      caught instanceof ApiError
        ? caught
        : new ApiError("Unable to start workflow", 500);
  } finally {
    submitting.value = false;
  }
}

function beginAnother() {
  workflow.value = null;
  history.value = null;
  error.value = null;
}

async function review(action: string) {
  if (!workflow.value) return;
  submitting.value = true;
  error.value = null;
  try {
    workflow.value = await api<ControlledWorkflow>(
      `/workflows/${workflow.value.id}/review`,
      {
        method: "POST",
        body: JSON.stringify({
          action,
          reason: reviewReason.value,
          expected_checkpoint_version: workflow.value.checkpoint_version,
          idempotency_key: key("review"),
        }),
      },
    );
    reviewReason.value = "";
    await loadHistory();
  } catch (caught) {
    error.value =
      caught instanceof ApiError
        ? caught
        : new ApiError("Unable to submit review", 500);
  } finally {
    submitting.value = false;
  }
}

onMounted(load);

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
</script>

<template>
  <section
    id="review-workflow"
    class="surface workflow-panel"
    aria-labelledby="workflow-title"
  >
    <header class="surface-header">
      <div>
        <span class="eyebrow">WORKFLOW &amp; REVIEW</span>
        <h2 id="workflow-title">Human review</h2>
        <p>
          Organizes cited evidence and proposals. It cannot approve, deny, pay,
          contact, or close.
        </p>
      </div>
      <span
        v-if="workflow"
        class="status-chip"
        :class="
          workflow.human_review_required
            ? 'status-chip--amber'
            : 'status-chip--success'
        "
        aria-live="polite"
      >
        {{ workflow.status.replaceAll("_", " ") }}
      </span>
    </header>

    <div v-if="loading" class="workflow-body" aria-live="polite">
      Loading workflow…
    </div>
    <div v-else-if="error" class="inline-error" role="alert">
      <strong>Workflow action needs attention.</strong> {{ error.message }}
      <button type="button" class="text-link" @click="load">
        Reload current state
      </button>
    </div>
    <form v-else-if="!workflow" class="workflow-start" @submit.prevent="start">
      <label for="workflow-task">Evidence-review task</label>
      <textarea
        id="workflow-task"
        v-model="task"
        minlength="3"
        maxlength="500"
        required
      />
      <small
        >Deterministic local processing only; uploaded content is always treated
        as data.</small
      >
      <button class="primary-button" type="submit" :disabled="submitting">
        {{ submitting ? "Starting…" : "Start controlled workflow" }}
      </button>
    </form>
    <div v-else class="workflow-body">
      <div class="workflow-facts" aria-label="Workflow status">
        <div>
          <span>Current stage</span
          ><strong>{{ workflow.current_stage.replaceAll("_", " ") }}</strong>
        </div>
        <div>
          <span>Policy edition</span
          ><strong>{{ workflow.applicable_policy_edition }}</strong>
        </div>
        <div>
          <span>Approval state</span
          ><strong>{{ workflow.approval_state.replaceAll("_", " ") }}</strong>
        </div>
      </div>
      <button
        v-if="
          workflow.status === 'completed' || workflow.status === 'cancelled'
        "
        type="button"
        class="secondary-button"
        @click="beginAnother"
      >
        Start a new evidence review
      </button>

      <p class="authority-notice">{{ workflow.artifact?.authority_notice }}</p>
      <div v-if="workflow.artifact" class="workflow-artifact">
        <section>
          <h3>Evidence</h3>
          <p v-if="!workflow.artifact.citations.length" class="muted">
            No supporting citation was found.
          </p>
          <ol v-else class="workflow-citations">
            <li
              v-for="citation in workflow.artifact.citations"
              :key="citation.id"
            >
              <RouterLink :to="citation.source_url"
                ><strong>{{ citation.id }}</strong> ·
                {{ citation.document_name }}, page
                {{ citation.page_number }}</RouterLink
              >
            </li>
          </ol>
        </section>
        <section
          v-if="workflow.artifact.conflicting_evidence.length"
          class="signal-block signal-block--warning"
        >
          <h3>Conflicting evidence</h3>
          <p
            v-for="item in workflow.artifact.conflicting_evidence"
            :key="item.fact_type"
          >
            {{ item.left_document_name }}: {{ item.left_value }} ≠
            {{ item.right_document_name }}: {{ item.right_value }}
          </p>
        </section>
        <section
          v-if="workflow.artifact.missing_information.length"
          class="signal-block"
        >
          <h3>Missing information</h3>
          <ul>
            <li
              v-for="item in workflow.artifact.missing_information"
              :key="item"
            >
              {{ item }}
            </li>
          </ul>
        </section>
        <section
          v-if="workflow.artifact.ambiguous_evidence.length"
          class="signal-block"
        >
          <h3>Ambiguity requiring interpretation</h3>
          <ul>
            <li
              v-for="item in workflow.artifact.ambiguous_evidence"
              :key="item"
            >
              {{ item.replaceAll("_", " ") }}
            </li>
          </ul>
        </section>
        <section
          v-if="workflow.artifact.untrusted_content_flags.length"
          class="security-notice"
          role="alert"
        >
          <h3>Untrusted document instructions detected</h3>
          <p>
            Flagged text remained inert evidence and could not grant permissions
            or invoke tools.
          </p>
        </section>
        <section class="proposal-block">
          <span class="eyebrow">SYSTEM-GENERATED PROPOSAL</span>
          <h3>Proposed next steps</h3>
          <ul>
            <li
              v-for="step in workflow.artifact.proposed_next_steps"
              :key="step"
            >
              {{ step }}
            </li>
          </ul>
        </section>
      </div>

      <section
        v-if="workflow.status === 'awaiting_human_review'"
        class="review-gate"
        aria-labelledby="review-gate-title"
      >
        <span class="eyebrow">HUMAN DECISION / ACTION</span>
        <h3 id="review-gate-title">Authorized review required</h3>
        <p>
          {{ workflow.artifact?.human_review_reason?.replaceAll(",", ", ") }}
        </p>
        <template v-if="reviewer">
          <label for="review-reason">Reviewer rationale</label>
          <textarea
            id="review-reason"
            v-model="reviewReason"
            minlength="3"
            maxlength="500"
            required
          />
          <p class="review-consequence">
            Your rationale becomes part of the claim audit record. This action
            addresses the evidence-review workflow only; it does not approve or
            deny the claim.
          </p>
          <div class="review-actions">
            <button
              type="button"
              :disabled="submitting || reviewReason.length < 3"
              @click="review('acknowledge')"
            >
              Acknowledge evidence review
            </button>
            <button
              type="button"
              :disabled="submitting || reviewReason.length < 3"
              @click="review('request_more_information')"
            >
              Request more information
            </button>
            <button
              type="button"
              :disabled="submitting || reviewReason.length < 3"
              @click="review('reject_proposal')"
            >
              Reject proposal
            </button>
          </div>
        </template>
        <p v-else class="muted">
          A supervisor or administrator must complete this review.
        </p>
      </section>

      <section class="workflow-history" aria-labelledby="history-title">
        <h3 id="history-title">Workflow history</h3>
        <ol>
          <li v-for="event in history?.events" :key="event.sequence">
            <span>{{ formatTimestamp(event.created_at) }}</span
            ><strong>{{ event.stage.replaceAll("_", " ") }}</strong
            ><small
              >Checkpoint
              {{ event.details.checkpoint_version ?? event.sequence }}</small
            >
          </li>
        </ol>
      </section>
    </div>
  </section>
</template>
