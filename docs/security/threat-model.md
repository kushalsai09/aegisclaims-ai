# Threat Model

## Method and assets

This model uses STRIDE-style categories plus AI-specific misuse. Protected assets include identity tokens, claim/policy documents, structured facts, policy applicability, model prompts/outputs, workflow checkpoints, human decisions, rules, evaluation datasets, audit events, secrets, infrastructure state, and deployment artifacts.

## Actors

- Authorized employee making an error or exceeding purpose.
- Malicious or compromised employee account.
- Attacker submitting a crafted document or request.
- Compromised dependency, container, model/provider, or CI credential.
- Faulty application/model behavior without malicious intent.

## Primary threats and mitigations

| ID | Threat | Boundary/impact | Prevent/detect/respond |
|---|---|---|---|
| T-01 | Tenant or claim ID enumeration | API/data disclosure | Resource-first authorization, non-enumerating responses, tenant-qualified keys, audit/anomaly alerts |
| T-02 | Role/assignment forgery | Browser/API privilege escalation | Validate OIDC; server-side user/assignment lookup; ignore client tenant/role; negative tests |
| T-03 | Prompt injection in evidence | Retrieval/model/tool misuse | Untrusted-data framing, tool allowlists, schema validation, security classifiers, adversarial tests |
| T-04 | Indirect exfiltration through model | Model boundary disclosure | Minimum evidence, provider policy, egress restrictions, output scanning, no secrets in prompt |
| T-05 | Wrong policy edition retrieved | Integrity and consequential error | Hard metadata filters, applicability validator, citation status, mandatory ambiguity review |
| T-06 | Hallucinated or mismatched citation | Employee deception | Referential/span validation, assertion-to-citation schema, abstain/escalate, golden tests |
| T-07 | Malicious file/polyglot/archive bomb | Upload/parser availability or execution | Magic-byte allowlist, limits, quarantine, scan, sandbox, no active-content rendering |
| T-08 | Duplicate queue event/tool call | State corruption | Idempotency keys, unique constraints, outbox, optimistic concurrency, reconciliation |
| T-09 | Review replay or stale approval | Invalid consequential action | Snapshot-bound task, nonce/version, expiry, reauthorization, append-only decision |
| T-10 | Audit deletion or tampering | Repudiation | Restricted append API, hash chain, immutable archive option, access alarms |
| T-11 | Sensitive telemetry | Secondary data leak | Attribute allowlists, redaction, content references, access tiers, retention |
| T-12 | Dependency/build compromise | Runtime compromise | Lockfiles, SBOM, scanning, signed images, isolated CI, OIDC, protected promotion |
| T-13 | Denial of wallet/service | Model/search cost and availability | Rate/token/concurrency budgets, queue backpressure, timeouts, circuit breakers, budgets/alerts |
| T-14 | Model/provider change | Silent quality/safety regression | Pin model policy/version where possible, canary, evaluation gates, response metadata |
| T-15 | SQL/vector filter omission | Cross-scope retrieval | Typed retrieval request, mandatory predicates, RLS defense in depth, property tests |
| T-16 | XSS through generated/document text | Browser compromise | Encode/sanitize, limited markdown, CSP, isolated safe viewer, no raw HTML |
| T-17 | SSRF through URL/tool/parser | Internal network access | No arbitrary URL tools, allowlisted endpoints, egress proxy/policy, metadata endpoint protection |
| T-18 | Golden-set leakage/overfitting | Misleading evaluation | Holdout sets, scenario families, mutation tests, provenance and access control |

## Abuse cases

Adversarial fixtures attempt to override instructions, claim supervisor authority, request secrets, forge citation IDs, smuggle tool arguments, reference another tenant, cause excessive token use, hide text in OCR noise, and request prohibited decisions. Each case declares expected block/abstain/escalate behavior and required audit signal.

## Risk treatment

Threats are recorded with owner, likelihood, impact, controls, evidence, residual risk, and review date. Critical authorization, consequential-action, and document-execution risks block release until treated. Accepted residual risk requires an explicit ADR or risk acceptance; it cannot be buried in a test waiver.

## Validation cadence

Review at architecture changes, new model/tool/document type, new external integration, and at least before each portfolio release. Run automated abuse tests continuously and manual threat-model/tabletop exercises before production enablement.
