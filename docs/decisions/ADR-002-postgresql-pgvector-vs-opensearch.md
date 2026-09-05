# ADR-002: PostgreSQL/pgvector versus OpenSearch

- **Status:** Accepted
- **Decision date:** 2026-08-26

## Context

The first corpus is modest and needs relational metadata, full-text search, vector search, filtering, and local reproducibility. Running a separate search cluster adds cost and consistency work before scale is known.

## Decision

Use PostgreSQL full-text search plus pgvector and versioned rank fusion. Access it through `RetrievalBackend` and evidence contracts that do not expose SQL details. Keep OpenSearch as a benchmark-driven alternative.

## Alternatives

- **OpenSearch from inception:** richer dedicated search scaling/features, with more operations, AWS coupling, cost, and dual-store consistency.
- **Vector-only database:** simple semantic retrieval but weaker exact terms/filter integration and another store.
- **Managed Bedrock knowledge base only:** faster managed path but less control over evaluation, provenance, and local parity.

## Trade-offs and consequences

PostgreSQL simplifies transactions and development but shares database capacity and may not meet large-scale relevance/concurrency requirements. Index tables remain derived, versioned, and rebuildable. Raw lexical/vector scores are fused as ranks rather than treated as calibrated.

## Success criteria and revisit triggers

Meet declared recall/nDCG, policy-version accuracy, p95 latency, concurrency, and cost on a representative corpus. Benchmark OpenSearch when corpus/traffic targets fail, search operations interfere with transactions, or required ranking/filter features are impractical. Migration requires dual-run parity for citation and authorization contracts.
