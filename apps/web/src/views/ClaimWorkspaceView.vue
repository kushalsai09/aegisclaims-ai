<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import ErrorState from "@/components/ErrorState.vue";
import EvidenceSearch from "@/components/EvidenceSearch.vue";
import FeaturePlaceholder from "@/components/FeaturePlaceholder.vue";
import LoadingState from "@/components/LoadingState.vue";
import WorkflowPanel from "@/components/WorkflowPanel.vue";
import ClaimEvidenceBrief from "@/components/ClaimEvidenceBrief.vue";
import { api, ApiError, uploadDocument } from "@/services/api";
import type { ClaimWorkspace, Document } from "@/types";

const route = useRoute();
const workspace = ref<ClaimWorkspace | null>(null);
const loading = ref(true);
const error = ref<ApiError | null>(null);
const uploadError = ref<ApiError | null>(null);
const uploadProgress = ref(0);
const uploadState = ref("");
const uploading = ref(false);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    workspace.value = await api<ClaimWorkspace>(
      `/claims/${String(route.params.id)}`,
    );
  } catch (caught) {
    error.value =
      caught instanceof ApiError
        ? caught
        : new ApiError("Unexpected claim error", 500);
  } finally {
    loading.value = false;
  }
}

onMounted(load);

async function handleUpload(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  uploading.value = true;
  uploadError.value = null;
  uploadProgress.value = 0;
  uploadState.value = `Uploading ${file.name}`;
  try {
    const document = await uploadDocument<Document>(
      String(route.params.id),
      file,
      (progress) => {
        uploadProgress.value = progress;
        uploadState.value =
          progress < 100 ? `Uploading ${file.name}` : "Processing document";
      },
    );
    uploadState.value =
      document.processing_status === "ready"
        ? `${document.name} is ready`
        : `${document.name}: ${document.processing_status}`;
    await load();
  } catch (caught) {
    uploadError.value =
      caught instanceof ApiError
        ? caught
        : new ApiError("Unexpected upload error", 500);
    uploadState.value = "";
  } finally {
    uploading.value = false;
    input.value = "";
  }
}

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
</script>

<template>
  <div class="page-shell page-shell--wide">
    <LoadingState v-if="loading" />
    <ErrorState
      v-else-if="error"
      :message="error.message"
      :correlation-id="error.correlationId"
      @retry="load"
    />
    <template v-else-if="workspace">
      <div class="synthetic-banner" role="note">
        Local environment · Fictional claim data
      </div>
      <header class="page-header claim-header">
        <div>
          <RouterLink to="/claims" class="breadcrumb">← Claims</RouterLink>
          <div class="claim-title-row">
            <h1>{{ workspace.claim.claim_number }}</h1>
            <span class="status-chip status-chip--success">{{
              workspace.claim.status
            }}</span>
          </div>
          <p>
            {{ workspace.claim.loss_type }} · Loss date
            {{ workspace.claim.loss_date }}
          </p>
        </div>
        <div class="workflow-state">
          <span>Workflow status</span
          ><strong>{{
            workspace.workflow?.status.replaceAll("_", " ") ?? "not started"
          }}</strong
          ><small>Human authority remains required</small>
        </div>
      </header>

      <nav class="workspace-nav" aria-label="Claim workspace sections">
        <a href="#overview">Overview</a>
        <a href="#documents-evidence">Documents &amp; evidence</a>
        <a href="#evidence-brief">Evidence brief</a>
        <a href="#review-workflow">Workflow &amp; review</a>
      </nav>

      <section id="overview" class="claim-overview-grid">
        <article class="surface claim-details">
          <div class="surface-header">
            <div>
              <span class="eyebrow">CLAIM OVERVIEW</span>
              <h2>Loss information</h2>
            </div>
          </div>
          <dl class="detail-grid">
            <div>
              <dt>Property</dt>
              <dd>{{ workspace.claim.property_address }}</dd>
            </div>
            <div>
              <dt>Loss type</dt>
              <dd>{{ workspace.claim.loss_type }}</dd>
            </div>
            <div>
              <dt>Claim version</dt>
              <dd>{{ workspace.claim.version }}</dd>
            </div>
            <div class="detail-wide">
              <dt>Reported description</dt>
              <dd>{{ workspace.claim.description }}</dd>
            </div>
          </dl>
        </article>
        <article class="surface policy-card">
          <div class="surface-header">
            <div>
              <span class="eyebrow">POLICY RECORD</span>
              <h2>{{ workspace.policy.product_name }}</h2>
            </div>
          </div>
          <dl class="compact-details">
            <div>
              <dt>Policy</dt>
              <dd>{{ workspace.policy.policy_number }}</dd>
            </div>
            <div>
              <dt>Product</dt>
              <dd>{{ workspace.policy.product_code }}</dd>
            </div>
            <div>
              <dt>Edition</dt>
              <dd>{{ workspace.policy.edition }}</dd>
            </div>
            <div>
              <dt>Effective</dt>
              <dd>
                {{ workspace.policy.effective_from }} –
                {{ workspace.policy.effective_to }}
              </dd>
            </div>
          </dl>
          <span class="synthetic-badge">{{
            workspace.policy.synthetic_label
          }}</span>
        </article>
      </section>

      <section id="documents-evidence" class="surface documents-section">
        <div class="surface-header">
          <div>
            <span class="eyebrow">SOURCE RECORDS</span>
            <h2>Documents &amp; evidence</h2>
          </div>
          <div class="document-actions">
            <span
              >{{ workspace.documents.length }}
              {{ workspace.documents.length === 1 ? "file" : "files" }}</span
            >
            <label class="upload-button" :class="{ disabled: uploading }">
              <input
                type="file"
                accept="application/pdf,text/plain,.pdf,.txt"
                :disabled="uploading"
                @change="handleUpload"
              />
              {{ uploading ? "Processing…" : "Upload document" }}
            </label>
          </div>
        </div>
        <div
          v-if="uploading || uploadState"
          class="upload-state"
          aria-live="polite"
        >
          <div>
            <strong>{{ uploadState }}</strong
            ><span>{{ uploadProgress }}%</span>
          </div>
          <progress :value="uploadProgress" max="100">
            {{ uploadProgress }}%
          </progress>
        </div>
        <div v-if="uploadError" class="inline-error" role="alert">
          <strong>Upload was not accepted.</strong> {{ uploadError.message }}
          <span v-if="uploadError.correlationId"
            >Reference: {{ uploadError.correlationId }}</span
          >
        </div>
        <ul class="document-list">
          <li v-for="document in workspace.documents" :key="document.id">
            <span class="document-icon" aria-hidden="true">PDF</span>
            <RouterLink :to="`/documents/${document.id}`" class="document-link">
              <strong>{{ document.name }}</strong>
              <small>
                {{ document.document_type.replaceAll("_", " ") }} ·
                {{ document.page_count }}
                {{ document.page_count === 1 ? "page" : "pages" }} · uploaded by
                {{ document.uploaded_by ?? "system" }}
              </small>
              <small>{{ formatTimestamp(document.uploaded_at) }}</small>
            </RouterLink>
            <span>
              <span
                class="status-chip"
                :class="
                  document.processing_status === 'ready'
                    ? 'status-chip--success'
                    : document.processing_status === 'failed'
                      ? 'status-chip--amber'
                      : 'status-chip--neutral'
                "
                >{{ document.processing_status }}</span
              >
              <small class="extraction-state">{{
                document.extraction_status
              }}</small>
            </span>
          </li>
        </ul>
      </section>

      <EvidenceSearch :claim-id="workspace.claim.id" />

      <ClaimEvidenceBrief :claim-id="workspace.claim.id" />

      <WorkflowPanel :claim-id="workspace.claim.id" />

      <section
        v-if="workspace.conflicts.length"
        class="surface conflict-section"
        aria-labelledby="conflicts-title"
      >
        <div class="surface-header">
          <div>
            <span class="eyebrow">SOURCE COMPARISON</span>
            <h2 id="conflicts-title">Conflicts detected</h2>
          </div>
          <span class="status-chip status-chip--amber">Human attention</span>
        </div>
        <div
          v-for="conflict in workspace.conflicts"
          :key="conflict.id"
          class="conflict-row"
        >
          <strong>{{ conflict.fact_type.replaceAll("_", " ") }}</strong>
          <span class="conflict-source">
            <small>{{ conflict.left_document_name }}</small>
            {{ conflict.left.normalized_value }}
          </span>
          <span aria-hidden="true">≠</span>
          <span class="conflict-source">
            <small>{{ conflict.right_document_name }}</small>
            {{ conflict.right.normalized_value }}
          </span>
          <small>{{ conflict.detection_method }}</small>
        </div>
      </section>

      <section aria-labelledby="future-intelligence-title">
        <div class="section-heading">
          <div>
            <span class="eyebrow">AUTHORITY BOUNDARY</span>
            <h2 id="future-intelligence-title">Human-only actions</h2>
            <p>
              These consequential actions are intentionally unavailable to
              automation.
            </p>
          </div>
          <span class="status-chip status-chip--amber">Not implemented</span>
        </div>
        <div class="future-grid">
          <FeaturePlaceholder
            v-for="section in workspace.future_sections"
            :key="section.key"
            :title="section.title"
            :description="section.description"
          />
        </div>
      </section>
    </template>
  </div>
</template>
