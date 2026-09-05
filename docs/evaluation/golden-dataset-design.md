# Golden Dataset Design

## Dataset contract

The golden dataset is 100% fictional and reproducible. Each case is a directory or manifest entry containing a seeded synthetic claim, applicable policy and edition, documents, expected document classes, expected extracted facts with provenance, retrieval queries and relevance judgments, rule outcomes, expected issues, allowed answer concepts, prohibited claims, expected Support Assessment signals, expected graph path, and expected review outcome.

Every dataset release is immutable, content-hashed, schema-versioned, licensed/attributed as generated project material, and split into development, regression, and withheld challenge sets.

## Required scenario families

| Scenario | Core variation | Expected behavior |
|---|---|---|
| Supported | Complete consistent evidence and applicable edition | Cited artifact; no mandatory issue unless action itself is consequential |
| Missing document | Critical synthetic requirement absent | Explicit missing item and mandatory review when configured |
| Conflicting evidence | Material dates/amounts/descriptions disagree | Preserve both sources; unresolved contradiction; review |
| Ambiguous language | Two plausible fictional policy readings | Abstain from coverage conclusion; show provisions; review |
| Wrong policy version | Relevant older/newer edition is a hard negative | Reject non-governing edition; ambiguity if governing text unavailable |
| OCR/noisy | Character swaps, layout loss, stamps, broken tables | Extraction quality flag, robust retrieval or explicit insufficiency |
| Distractor | Semantically similar irrelevant documents | Exclude/downrank and cite governing evidence only |
| Prompt injection | Evidence includes malicious instructions | Treat as evidence; no unauthorized action; security signal |
| Unanswerable | Corpus lacks support | Explicit abstention, no model-memory answer |
| Mandatory review | One or more configured high-risk triggers | Persist interrupt and require authorized decision |

## Fictional consistency

The HarborView HomeSecure HO-SYN-01 generator maintains a policy graph: product edition, effective interval, base provisions, endorsements, covered-property definitions, duties/evidence lists, and synthetic thresholds. Claim loss dates choose a uniquely applicable edition unless the scenario intentionally creates ambiguity.

Any threshold or duty used to drive workflow behavior is marked **SYNTHETIC DEMONSTRATION RULE** in its source definition and expected result. The dataset makes no statement about real insurance practice or law.

## Relevance annotation

Retrieval queries have graded relevance at section/chunk level: governing/direct, supporting/context, distractor, and invalid-version. Annotators record allowed alternate spans because chunk boundaries can change. Policy applicability and authorization are independent labels: semantic relevance cannot make an invalid edition acceptable.

## Generation annotation

Expected outputs are structured propositions rather than one canonical paragraph. Each proposition includes required/optional status, supporting source spans, allowed paraphrases, uncertainty, and prohibited inference. This avoids rewarding superficial text similarity.

## Generation and QA process

1. Define case graph and expected outcomes before generating prose.
2. Render documents from controlled templates with seeded variation.
3. Inject noise/adversarial content only in declared transforms.
4. Run schema, date, cross-reference, identifier, and provenance validators.
5. Scan for real PII patterns and copied proprietary text.
6. Human-review a representative subset and every safety-critical case.
7. Freeze manifest and hashes; never silently edit a released case.

## Leakage and expansion

Templates and development cases can be visible to implementers; withheld challenge cases should vary names, wording, ordering, noise, and distractors. Failure discoveries become minimal regression cases plus related mutations. Report performance by template family to detect memorization.
