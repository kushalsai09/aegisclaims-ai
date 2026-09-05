<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, ApiError } from "@/services/api";
import type { ClaimEvidenceBrief } from "@/types";

const props = defineProps<{ claimId: string }>();
const brief = ref<ClaimEvidenceBrief | null>(null);
const loading = ref(true);
const generating = ref(false);
const error = ref<ApiError | null>(null);
const task = ref(
  "Prepare a cited evidence brief covering supported facts, gaps, conflicts, and ambiguity.",
);

function key() {
  return `brief-${props.claimId}-${Date.now()}`;
}

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const result = await api<ClaimEvidenceBrief | null>(
      `/claims/${props.claimId}/briefs/latest`,
    );
    brief.value = result && typeof result.status === "string" ? result : null;
  } catch (caught) {
    error.value =
      caught instanceof ApiError
        ? caught
        : new ApiError("Unable to load evidence brief", 500);
  } finally {
    loading.value = false;
  }
}

async function generate() {
  generating.value = true;
  error.value = null;
  try {
    brief.value = await api<ClaimEvidenceBrief>(
      `/claims/${props.claimId}/briefs`,
      {
        method: "POST",
        body: JSON.stringify({ task: task.value, idempotency_key: key() }),
      },
    );
  } catch (caught) {
    error.value =
      caught instanceof ApiError
        ? caught
        : new ApiError("Brief generation failed", 500);
  } finally {
    generating.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section
    id="evidence-brief"
    class="surface brief-panel"
    aria-labelledby="brief-title"
  >
    <header class="surface-header">
      <div>
        <span class="eyebrow">AI-ASSISTED · VALIDATED SOURCES</span>
        <h2 id="brief-title">Evidence brief</h2>
        <p>
          Grounded in authorized retrieval. Decision remains with the authorized
          reviewer.
        </p>
      </div>
      <span
        v-if="brief"
        class="status-chip"
        :class="
          brief.stale || brief.human_review_required
            ? 'status-chip--amber'
            : 'status-chip--success'
        "
        >{{ brief.stale ? "stale" : brief.status.replaceAll("_", " ") }}</span
      >
    </header>
    <div v-if="loading" class="brief-body" aria-live="polite">
      Loading evidence brief…
    </div>
    <div v-else-if="error" class="inline-error" role="alert">
      <strong>Evidence brief unavailable.</strong> {{ error.message }}
      <button type="button" class="text-link" @click="load">Retry</button>
    </div>
    <form v-else-if="!brief" class="workflow-start" @submit.prevent="generate">
      <label for="brief-task">Briefing task</label
      ><textarea
        id="brief-task"
        v-model="task"
        minlength="3"
        maxlength="500"
        required
      />
      <small
        >Document instructions remain untrusted data. Only retrieved citation
        handles are accepted.</small
      >
      <button class="primary-button" type="submit" :disabled="generating">
        {{ generating ? "Generating…" : "Generate evidence brief" }}
      </button>
    </form>
    <div v-else class="brief-body">
      <div v-if="brief.stale" class="security-notice" role="alert">
        <h3>Evidence changed after generation</h3>
        <p>This brief is stale and must not be relied on until regenerated.</p>
      </div>
      <p class="authority-notice">{{ brief.authority_notice }}</p>
      <div class="workflow-facts brief-facts" aria-label="Brief status">
        <div>
          <span>Status</span
          ><strong>{{ brief.status.replaceAll("_", " ") }}</strong>
        </div>
        <div>
          <span>Policy edition</span
          ><strong>{{ brief.applicable_policy_edition }}</strong>
        </div>
        <div>
          <span>Validation</span><strong>{{ brief.validation_state }}</strong>
        </div>
      </div>
      <section>
        <h3>Claim summary</h3>
        <p>{{ brief.claim_summary }}</p>
      </section>
      <section>
        <h3>Evidence summary</h3>
        <p>{{ brief.evidence_summary }}</p>
      </section>
      <section>
        <h3>Applicable policy evidence</h3>
        <p>{{ brief.applicable_policy_summary }}</p>
      </section>
      <section v-if="brief.missing_information.length" class="signal-block">
        <h3>Missing information</h3>
        <ul>
          <li v-for="item in brief.missing_information" :key="item">
            {{ item }}
          </li>
        </ul>
      </section>
      <section
        v-if="brief.conflicts.length"
        class="signal-block signal-block--warning"
      >
        <h3>Conflicts</h3>
        <ul>
          <li v-for="item in brief.conflicts" :key="item">{{ item }}</li>
        </ul>
      </section>
      <section v-if="brief.ambiguities.length" class="signal-block">
        <h3>Ambiguities</h3>
        <ul>
          <li v-for="item in brief.ambiguities" :key="item">{{ item }}</li>
        </ul>
      </section>
      <section
        v-if="brief.safety_flags.length"
        class="security-notice"
        role="alert"
      >
        <h3>Safety warning</h3>
        <p>Untrusted instructions were detected and remained inert evidence.</p>
      </section>
      <section>
        <h3>Sources</h3>
        <p v-if="!brief.citations.length" class="muted">
          No source supported this brief.
        </p>
        <ol v-else class="workflow-citations">
          <li v-for="citation in brief.citations" :key="citation.id">
            <RouterLink :to="citation.source_url"
              ><strong>{{ citation.id }}</strong> ·
              {{ citation.document_name }}, page
              {{ citation.page_number }}</RouterLink
            >
          </li>
        </ol>
      </section>
      <section>
        <h3>Limitations</h3>
        <ul>
          <li v-for="item in brief.limitations" :key="item">{{ item }}</li>
        </ul>
      </section>
      <details class="technical-details">
        <summary>Technical details</summary>
        <dl>
          <div>
            <dt>Provider</dt>
            <dd>{{ brief.provider }}</dd>
          </div>
          <div>
            <dt>Model</dt>
            <dd>{{ brief.model_identifier }}</dd>
          </div>
          <div>
            <dt>Reference</dt>
            <dd>{{ brief.correlation_id }}</dd>
          </div>
        </dl>
      </details>
      <button
        type="button"
        class="secondary-button"
        :disabled="generating"
        @click="generate"
      >
        {{ generating ? "Regenerating…" : "Regenerate from current evidence" }}
      </button>
    </div>
  </section>
</template>
