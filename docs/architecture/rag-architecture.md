# RAG Architecture

## Phase 3 implementation

Phase 3 implements the retrieval and grounded-answer foundation without
LangGraph, agents, consequential tools, or claim recommendations. The active
host/CI path consists of:

- page-bounded deterministic character windows (`700` characters with `100`
  characters of overlap), versioned as
  `page_window_chars_700_overlap_100_v1`;
- stable chunk identifiers derived from document ID, page checksum, chunker
  version, ordinal, offsets, and chunk-text checksum;
- immutable source checksum, page checksum, exact page-local source offsets,
  document type, policy edition, extraction provenance, and injection-risk
  metadata on every chunk;
- deterministic 64-dimensional signed-token-hash embeddings, versioned as
  `signed_token_hash_64_v1`, used only for offline/local reproducibility;
- portable SQL candidate storage and claim/tenant predicates, lexical and
  vector ranking, applicability filtering, and reciprocal-rank fusion
  `hybrid_rrf_k60_v1`;
- stable citations that resolve to the existing authorized document-detail
  page and cited page;
- an extractive deterministic grounded-answer provider with explicit
  answerable, insufficient-evidence, conflicting-evidence, and
  ambiguous-evidence states.

The same source and configuration reproduce identical chunks. A unique index
manifest prevents duplicate indexing, and changed source or embedding versions
create distinguishable index versions. Failed embeddings leave an explicit
failed index state that can be retried safely.

The portable SQL vector implementation is the executable host/CI baseline.
The existing PostgreSQL/pgvector infrastructure remains the production
direction behind `EmbeddingProvider` and `VectorIndex` ports. Phase 3 live
validation covered the PostgreSQL migration, pgvector `0.8.6` extension, and
retrieval tables; pgvector-native similarity search remains a future adapter.

Retrieved document text is always untrusted evidence. The generator receives
only authorized evidence returned for the requested claim, has no tools or
ambient data access, removes instruction-like evidence sentences from answer
synthesis, and can cite only supplied stable chunk identifiers.

## Objectives

The retrieval-augmented generation system must retrieve authorized, governing, provenance-preserving evidence and make insufficient support visible. The Phase 3 implementation uses a portable SQL index with deterministic lexical/vector ranking. PostgreSQL/pgvector is the production-oriented next adapter; backend-neutral contracts also permit later OpenSearch benchmarking.

See [document ingestion](../diagrams/03-document-ingestion.mmd) and [RAG pipeline](../diagrams/04-rag-pipeline.mmd).

## Ingestion

1. Authorize and register upload intent.
2. Validate type, size, filename, magic bytes, and checksum; quarantine the object.
3. Invoke a malware-scan interface and reject or isolate failures.
4. Extract normalized text and layout/page coordinates. OCR is an adapter, not assumed successful.
5. Classify document type with score/evidence and an abstain state.
6. Normalize text without erasing source offsets; detect language and prompt-injection indicators.
7. Split by structural boundaries, then token-aware windows with limited overlap. Never combine tenants, documents, or policy editions in a chunk.
8. Attach metadata and provenance, compute content hashes, embed, and update keyword/vector indexes atomically through versioned status.
9. Run ingestion quality checks and publish completion or explicit partial/failure status.

## Canonical chunk metadata

Every chunk includes `tenant_id`, `document_id`, `document_version_id`, `claim_id` when applicable, `policy_id`, `policy_edition_id`, `endorsement_ids`, `document_type`, `effective_from`, `effective_to`, `page`, `section_path`, source offsets/bounding boxes, `content_hash`, `extractor_version`, `chunker_version`, `embedding_model`, `embedding_version`, access labels, and injection-risk indicators.

## Query and ranking

1. Authorize the actor and resolve allowed resource scopes before retrieval.
2. Build a typed retrieval request: question, claim/policy identity, loss date, requested evidence types, and `k` budgets.
3. Apply hard metadata filters for tenant, access, policy identity, and effective date before evidence can be selected.
4. Run full-text and vector searches independently.
5. Fuse ranked lists using a versioned method such as reciprocal-rank fusion; do not compare raw backend scores as if calibrated.
6. Optionally rerank the bounded candidate set if offline benefit exceeds added latency/cost.
7. Diversify duplicates while preserving controlling policy sections and claim-specific sources.
8. Return evidence objects with scores by stage, provenance, applicable-version status, and selection reasons.

## Evidence and citations

A citation is valid only if its document/version is authorized, existed in the workflow input snapshot, the quoted span maps to stored normalized text and original coordinates, and policy applicability checks pass when presented as governing policy. Semantic entailment can be an additional evaluator but cannot replace referential validation.

Generated assertions are linked to citation IDs in structured output. Unsupported assertions are removed, labelled unresolved, or trigger abstention/review. The UI opens the exact page/section and distinguishes claim evidence from policy evidence.

## Retrieval quality

Golden queries include expected relevant chunks or sections, allowed alternates, hard negatives, governing editions, and unanswerable cases. Track recall@k, precision@k where annotation supports it, MRR/nDCG, policy-version accuracy, metadata-filter violations, duplicate rate, latency, and downstream citation support. Thresholds are stratified by scenario rather than hidden in one mean.

## Index lifecycle

Indexes are derived projections. A versioned index manifest records corpus snapshot, extractor, chunker, embedding, keyword configuration, fusion, and reranker. Build a new index version, evaluate it, then atomically activate it. Preserve the version used by each workflow. Deletion/retention events propagate to all index versions and are verified by reconciliation.

## OpenSearch adoption trigger

OpenSearch is considered when representative benchmarks show PostgreSQL cannot meet documented corpus, concurrency, relevance, filter, or operational-isolation targets. Migration occurs behind `RetrievalBackend`, with a dual-run evaluation and no change to evidence/citation contracts.
