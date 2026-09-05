<script setup lang="ts">
import { nextTick, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import ErrorState from "@/components/ErrorState.vue";
import LoadingState from "@/components/LoadingState.vue";
import { api, ApiError, documentOriginal } from "@/services/api";
import type { DocumentDetail } from "@/types";

const route = useRoute();
const router = useRouter();
const detail = ref<DocumentDetail | null>(null);
const loading = ref(true);
const error = ref<ApiError | null>(null);
const openingOriginal = ref(false);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    detail.value = await api<DocumentDetail>(
      `/documents/${String(route.params.id)}`,
    );
    await nextTick();
    if (route.hash)
      document.querySelector(route.hash)?.scrollIntoView({ block: "center" });
  } catch (caught) {
    error.value =
      caught instanceof ApiError
        ? caught
        : new ApiError("Unexpected document error", 500);
  } finally {
    loading.value = false;
  }
}

async function openOriginal() {
  openingOriginal.value = true;
  try {
    const blob = await documentOriginal(
      `/documents/${String(route.params.id)}/original`,
    );
    const objectUrl = URL.createObjectURL(blob);
    window.open(objectUrl, "_blank", "noopener,noreferrer");
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
  } catch (caught) {
    error.value =
      caught instanceof ApiError
        ? caught
        : new ApiError("Could not open the original", 500);
  } finally {
    openingOriginal.value = false;
  }
}

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

onMounted(load);
</script>

<template>
  <div class="page-shell page-shell--wide document-detail-page">
    <LoadingState v-if="loading" />
    <ErrorState
      v-else-if="error"
      :message="error.message"
      :correlation-id="error.correlationId"
      @retry="load"
    />
    <template v-else-if="detail">
      <header class="page-header document-header">
        <div>
          <button
            type="button"
            class="breadcrumb breadcrumb-button"
            @click="router.back()"
          >
            ← Claim workspace
          </button>
          <span class="eyebrow">SOURCE DOCUMENT</span>
          <h1>{{ detail.document.name }}</h1>
          <p>
            {{ detail.document.document_type.replaceAll("_", " ") }} ·
            {{ detail.document.page_count }}
            {{ detail.document.page_count === 1 ? "page" : "pages" }}
          </p>
        </div>
        <div class="document-header-actions">
          <span class="status-chip status-chip--success">{{
            detail.document.processing_status
          }}</span>
          <button
            class="primary-button"
            :disabled="openingOriginal"
            @click="openOriginal"
          >
            {{ openingOriginal ? "Opening…" : "Open original" }}
          </button>
        </div>
      </header>

      <nav class="workspace-nav" aria-label="Document sections">
        <a href="#extracted-pages-title">Extracted text</a>
        <a href="#facts-title">Structured facts</a>
        <a href="#history-title">Processing history</a>
      </nav>

      <div
        v-if="detail.document.injection_risk"
        class="security-notice"
        role="note"
      >
        <strong>Untrusted-content indicator detected</strong>
        Document text remains evidence data only. It cannot grant permissions or
        issue system or tool instructions.
      </div>

      <div v-if="detail.error_detail" class="inline-error" role="alert">
        <strong>{{ detail.error_code?.replaceAll("_", " ") }}</strong>
        {{ detail.error_detail }}
      </div>

      <section class="document-metadata-grid" aria-label="Document metadata">
        <article class="metric-card">
          <span>Uploaded by</span
          ><strong>{{ detail.document.uploaded_by ?? "System" }}</strong>
          <small>{{ formatTimestamp(detail.document.uploaded_at) }}</small>
        </article>
        <article class="metric-card">
          <span>Extraction</span
          ><strong>{{ detail.document.extraction_status }}</strong>
          <small>Source text available</small>
        </article>
        <article class="metric-card">
          <span>Size</span
          ><strong
            >{{ Math.ceil(detail.document.size_bytes / 1024) }} KB</strong
          >
          <small>{{ detail.document.page_count }} page source</small>
        </article>
      </section>

      <section v-if="detail.conflicts.length" class="surface conflict-section">
        <div class="surface-header">
          <div>
            <span class="eyebrow">CONFLICT DETECTED</span>
            <h2>Source facts disagree</h2>
          </div>
          <span class="status-chip status-chip--amber">Review required</span>
        </div>
        <div
          v-for="conflict in detail.conflicts"
          :key="conflict.id"
          class="conflict-comparison"
        >
          <strong>{{ conflict.fact_type.replaceAll("_", " ") }}</strong>
          <div>
            <span
              ><small
                >{{ conflict.left_document_name }} · page
                {{ conflict.left.page_number }}</small
              >{{ conflict.left.normalized_value }}</span
            >
            <span class="conflict-symbol" aria-label="does not equal">≠</span>
            <span
              ><small
                >{{ conflict.right_document_name }} · page
                {{ conflict.right.page_number }}</small
              >{{ conflict.right.normalized_value }}</span
            >
          </div>
        </div>
      </section>

      <div class="document-detail-grid">
        <section
          class="surface extracted-pages"
          aria-labelledby="extracted-pages-title"
        >
          <div class="surface-header">
            <div>
              <span class="eyebrow">PAGE PROVENANCE</span>
              <h2 id="extracted-pages-title">Extracted text</h2>
            </div>
            <span>
              {{ detail.pages.length }}
              {{ detail.pages.length === 1 ? "page" : "pages" }}
            </span>
          </div>
          <article
            v-for="page in detail.pages"
            :id="`page-${page.page_number}`"
            :key="page.page_number"
            class="extracted-page"
            :class="{
              'extracted-page--cited':
                String(route.query?.page) === String(page.page_number),
            }"
            tabindex="-1"
          >
            <header>
              <strong>Page {{ page.page_number }}</strong>
              <small>Source page text</small>
            </header>
            <pre>{{ page.text }}</pre>
          </article>
          <div v-if="!detail.pages.length" class="compact-empty">
            No extracted pages are available.
          </div>
        </section>

        <aside class="document-side-stack">
          <section class="surface facts-panel">
            <div class="surface-header">
              <div>
                <span class="eyebrow">STRUCTURED DATA</span>
                <h2 id="facts-title">Structured facts</h2>
              </div>
            </div>
            <dl v-if="detail.facts.length" class="fact-list">
              <div v-for="fact in detail.facts" :key="fact.id">
                <dt>{{ fact.fact_type.replaceAll("_", " ") }}</dt>
                <dd>{{ fact.normalized_value }}</dd>
                <small>Page {{ fact.page_number }}</small>
                <code aria-label="Source text">{{ fact.raw_source_span }}</code>
              </div>
            </dl>
            <div v-else class="compact-empty">
              No supported structured facts were found.
            </div>
          </section>

          <section class="surface history-panel">
            <div class="surface-header">
              <div>
                <span class="eyebrow">AUDITABLE PIPELINE</span>
                <h2 id="history-title">Processing history</h2>
              </div>
            </div>
            <ol class="processing-history">
              <li
                v-for="event in detail.processing_history"
                :key="`${event.status}-${event.created_at}`"
              >
                <span aria-hidden="true"></span>
                <div>
                  <strong>{{ event.status }}</strong>
                  <p>{{ event.detail }}</p>
                  <small>{{ formatTimestamp(event.created_at) }}</small>
                </div>
              </li>
            </ol>
          </section>
          <details class="technical-details document-technical">
            <summary>Technical provenance</summary>
            <dl>
              <div>
                <dt>Media type</dt>
                <dd>{{ detail.document.detected_mime_type }}</dd>
              </div>
              <div>
                <dt>Checksum</dt>
                <dd>{{ detail.document.checksum_sha256 }}</dd>
              </div>
            </dl>
          </details>
        </aside>
      </div>
    </template>
  </div>
</template>
