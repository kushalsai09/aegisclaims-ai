<script setup lang="ts">
import { ref } from "vue";
import { api, ApiError } from "@/services/api";
import type { GroundedAnswer } from "@/types";

const props = defineProps<{ claimId: string }>();
const question = ref("");
const loading = ref(false);
const result = ref<GroundedAnswer | null>(null);
const error = ref<ApiError | null>(null);

async function ask() {
  const normalized = question.value.trim();
  if (normalized.length < 3 || loading.value) return;
  loading.value = true;
  error.value = null;
  result.value = null;
  try {
    result.value = await api<GroundedAnswer>(
      `/claims/${props.claimId}/questions`,
      {
        method: "POST",
        body: JSON.stringify({ question: normalized, limit: 5 }),
      },
    );
  } catch (caught) {
    error.value =
      caught instanceof ApiError
        ? caught
        : new ApiError("Evidence search failed", 500);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <section
    class="surface evidence-search"
    aria-labelledby="evidence-search-title"
  >
    <div class="surface-header evidence-search-header">
      <div>
        <span class="eyebrow">EVIDENCE SEARCH</span>
        <h2 id="evidence-search-title">Search claim documents</h2>
        <p>
          Searches only this authorized claim. Responses are evidence-grounded
          assistance, not claim decisions.
        </p>
      </div>
      <span class="status-chip status-chip--neutral"
        >Human judgment required</span
      >
    </div>
    <form class="evidence-form" @submit.prevent="ask">
      <label for="claim-question">Question about this claim’s documents</label>
      <div>
        <textarea
          id="claim-question"
          v-model="question"
          maxlength="500"
          rows="2"
          placeholder="For example: What reported loss date is supported by the documents?"
          :disabled="loading"
        ></textarea>
        <button
          class="primary-button"
          type="submit"
          :disabled="loading || question.trim().length < 3"
        >
          {{ loading ? "Searching…" : "Find evidence" }}
        </button>
      </div>
      <small>{{ question.length }}/500 characters</small>
    </form>

    <div v-if="loading" class="evidence-loading" role="status">
      Retrieving authorized evidence and validating citations…
    </div>
    <div v-if="error" class="inline-error" role="alert">
      <strong>Evidence search failed.</strong> {{ error.message }}
      <span v-if="error.correlationId"
        >Reference: {{ error.correlationId }}</span
      >
      <button type="button" class="text-button" @click="ask">Try again</button>
    </div>

    <article v-if="result" class="grounded-result" aria-live="polite">
      <header>
        <div>
          <span class="eyebrow">GROUNDED RESULT</span>
          <h3>{{ result.state.replaceAll("_", " ") }}</h3>
        </div>
        <span
          class="status-chip"
          :class="
            result.answerable ? 'status-chip--success' : 'status-chip--amber'
          "
        >
          {{
            result.answerable ? "Evidence available" : "Insufficient evidence"
          }}
        </span>
      </header>
      <p class="grounded-answer">{{ result.answer }}</p>
      <div
        v-if="result.human_review_required"
        class="review-notice"
        role="note"
      >
        Human review is already required for this synthetic scenario.
      </div>
      <div v-if="result.missing_information.length" class="result-signal">
        <strong>Missing information</strong>
        <span>{{
          result.missing_information.join(", ").replaceAll("_", " ")
        }}</span>
      </div>
      <div v-if="result.ambiguity_indicators.length" class="result-signal">
        <strong>Ambiguity</strong>
        <span>{{
          result.ambiguity_indicators.join(", ").replaceAll("_", " ")
        }}</span>
      </div>
      <div
        v-if="result.citations.length"
        class="citation-list"
        aria-label="Source citations"
      >
        <h4>Source evidence</h4>
        <article
          v-for="citation in result.citations"
          :key="citation.id"
          class="citation-card"
        >
          <div>
            <span class="citation-id">{{ citation.id }}</span>
            <RouterLink :to="citation.source_url"
              >{{ citation.document_name }} · page
              {{ citation.page_number }}</RouterLink
            >
          </div>
          <p>{{ citation.excerpt }}</p>
          <small>
            Rank {{ citation.retrieval_rank }} ·
            {{ citation.retrieval_method }} ·
            {{ citation.applicability_status.replaceAll("_", " ") }}
          </small>
          <span v-if="citation.injection_risk" class="untrusted-inline"
            >Untrusted instructions detected — treated as evidence only</span
          >
        </article>
      </div>
      <footer>Policy edition {{ result.applicable_policy_version }}</footer>
    </article>
  </section>
</template>
