# AI Architecture

## AI responsibility

Models help interpret language, normalize extracted content, synthesize evidence, and draft employee-facing text. They do not own authorization, policy-version selection, required-field truth, business thresholds, workflow permissions, citation validity, or consequential decisions.

## Capability allocation

| Capability | Primary method | Why | Guardrail and metric |
|---|---|---|---|
| File safety and metadata | Deterministic | Security and integrity are not language tasks | Allowlist/scan/checksum pass rate |
| Document classification | Heuristic or small model baseline, then structured LLM if needed | Language variation may require ML | Golden macro-F1, abstention, cost |
| Fact extraction | Parser plus schema-constrained model | Unstructured documents need language understanding | Field precision/recall and provenance validity |
| Policy applicability | Deterministic identity/effective-date logic | Version correctness must be reproducible | 100% version-rule tests |
| Evidence retrieval | Hybrid IR, optional reranker | Ground responses in authorized corpus | recall@k, nDCG@k, latency |
| Summary and rationale | Schema-constrained generation over evidence | Human-readable synthesis adds value | groundedness, citation validity, completeness |
| Missing items | Deterministic requirements plus extracted facts | Requirements are explicit | exact-match and reviewer agreement |
| Contradictions | Deterministic comparisons plus bounded semantic comparison | Some statements require normalization | precision/recall by conflict type |
| Escalation | Deterministic policy over signals | Safety boundary must be inspectable | escalation recall/precision by reason |

## Gateway contracts

`ModelGateway` accepts a task identifier, validated message template inputs, output schema, allowed capabilities, model policy, budgets, idempotency key, and trace context. It returns parsed output, provider/model identifiers, usage, latency, stop reason, safety results, and raw-response reference where retention permits.

`EmbeddingGateway` accepts normalized texts, embedding purpose, model policy, dimensions, batch budget, content hashes, and trace context. It returns vectors plus provider/model/dimension metadata. Embeddings are versioned and re-indexable.

Providers declare capabilities such as structured output, tool calling, streaming, token limits, regional availability, and usage reporting. Business code selects a task policy, not a provider model ID.

Required implementations:

- Deterministic mock provider for CI and offline development.
- Bedrock provider for production candidates.
- Optional local provider adapter behind the same contract.

## Prompt and output lifecycle

- Prompts are immutable versioned artifacts with owner, task, input schema, output schema, model constraints, examples, prohibited behavior, and evaluation baseline.
- Runtime interpolation accepts typed values; untrusted content is clearly delimited and cannot modify system-owned policy.
- Outputs are parsed into strict Pydantic schemas. Unknown fields, invalid citations, excessive lengths, and disallowed actions fail validation.
- A bounded repair attempt may correct syntax only. It cannot invent evidence; repeated failure creates an explicit workflow error or human review.
- Release metadata binds graph, prompt, model policy, retrieval, rule, schema, and dataset versions.

## Support Assessment

The assessment is a structured object, not a probability:

- evidence coverage by required question/fact;
- retrieval results and benchmark-derived quality context;
- required-field completeness;
- citation existence, authorization, span, and entailment checks;
- contradiction state and unresolved material conflicts;
- deterministic rule outcomes;
- policy identity/version/effective-date status;
- applicable evaluation warnings;
- workflow risk category;
- escalation required plus reason codes.

The LLM may summarize these results for readability but cannot set or override them. Thresholds are versioned **SYNTHETIC DEMONSTRATION RULES** until replaced by approved production policy.

## Failure behavior

Provider timeout, quota exhaustion, schema failure, unavailable evidence, or safety filtering never becomes a normal completed answer. The graph records the failure class, preserves retryability, avoids duplicate calls using idempotency records where feasible, and either degrades to deterministic partial results or escalates.

## Evaluation and release

Every task has a deterministic or human-labelled benchmark before optimization. Candidate models are compared on quality, abstention, safety, latency, and cost. LLM-as-judge is never the sole gate, cannot see the candidate identity, uses a versioned rubric, and is calibrated against human labels.
