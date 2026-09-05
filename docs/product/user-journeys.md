# User Journeys

## 1. Adjuster opens a supported claim

1. The adjuster authenticates and opens an assigned claim.
2. The API checks tenant, role, assignment, and document authorization.
3. The workspace displays authoritative structured data immediately and marks generated sections as pending or stale.
4. The adjuster starts analysis. The service snapshots input versions and invokes the claims graph idempotently.
5. The graph assembles documents, extracts/loads facts, retrieves the effective policy edition, validates citations, runs demonstration rules, and creates a Support Assessment.
6. The UI streams status events, then shows the cited summary, relevant policy evidence, missing items, contradictions, rule results, and proposed next actions.
7. If no mandatory trigger fires, the adjuster accepts or edits the artifact and records feedback. Acceptance means “useful decision support,” not claim approval.

## 2. Missing or contradictory evidence

1. Required evidence is absent or two sources disagree on a material fact.
2. The graph records structured issue objects with source references and severity.
3. A **SYNTHETIC DEMONSTRATION RULE** determines whether the issue mandates review.
4. The UI avoids resolving the conflict speculatively and presents the competing evidence side by side.
5. The adjuster may request an allowed missing item or submit the case for supervisor review; external communication remains a draft until approved.

## 3. Wrong policy version

1. Retrieval finds semantically relevant language from an edition outside the claim's effective period.
2. Effective-date and policy-identity filters reject it as governing evidence.
3. If no uniquely applicable edition remains, policy-version status becomes ambiguous and the workflow interrupts for review.
4. The reviewer sees editions considered, applicable dates, rejection reasons, and no fabricated interpretation.

## 4. Prompt-injection document

1. A document contains text instructing the model to ignore rules or call a tool.
2. The ingestion pipeline flags injection-like content while retaining it as evidence.
3. Retrieval labels all excerpts as untrusted quoted material.
4. The model gateway provides system-owned instructions and a fixed output schema; document text cannot grant permissions.
5. Tool calls are checked independently against workflow state and actor authorization. A blocked attempt creates a security event and may trigger review.

## 5. Unsupported employee question

1. The employee asks a question not supported by authorized claim and policy evidence.
2. Retrieval returns inadequate coverage or citation validation fails.
3. The response states that the available evidence does not support an answer, lists what was searched, and suggests an allowed next step.
4. The system neither fills the gap from model memory nor invents a confidence score.

## 6. Supervisor resolves an interrupted workflow

1. An idempotent review task enters the supervisor queue with reason codes and a frozen evidence snapshot.
2. The supervisor examines evidence, rules, unresolved issues, and audit history.
3. The supervisor approves the proposed artifact, edits it, rejects it, or returns it for more evidence, providing a required reason.
4. LangGraph resumes from the persisted interrupt only when the review task and snapshot versions match.
5. The final state and every action are appended to the audit timeline.

## 7. Operations reviewer investigates regression

1. A quality gate or online metric signals declining citation validity or increased unsupported-answer rate.
2. The reviewer filters by dataset, model, prompt, graph, and retrieval configuration versions.
3. Authorized samples expose inputs, evidence, outputs, evaluators, and traces with sensitive fields minimized.
4. A candidate fix is evaluated offline against the frozen golden set before controlled deployment.
