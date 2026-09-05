# Prompt-Injection Defense

## Position

Prompt injection cannot be solved by a stronger instruction or detector alone. The secure design assumes a model may follow malicious document text and ensures that model behavior cannot grant access, bypass rules, or execute consequential actions.

## Defense layers

### 1. Minimize authority

Models receive no ambient database, shell, filesystem, network, cloud, or secret access. Available tools are read-oriented typed operations selected by the current graph node. The application, not the model, owns authorization and routing.

### 2. Separate instructions from evidence

System-owned task policy and schemas are immutable versioned inputs. Employee text and retrieved excerpts are identified by source and wrapped as untrusted evidence. Prompts explicitly require treating instructions found inside evidence as quoted content. Delimiters improve behavior but are not a security control by themselves.

### 3. Secure retrieval

Authorization and tenant/policy filters execute before retrieval results reach a model. Injection indicators are stored as metadata and can lower trust, add warnings, or force review, but flagged evidence is not silently discarded when it may be materially relevant.

### 4. Validate tool requests

For every proposed tool call, verify:

- tool is registered for this workflow/node;
- workload and originating employee context permit the action;
- arguments match a strict schema and authorized resource IDs;
- call stays within count, cost, time, and data-classification budgets;
- current workflow state permits it;
- idempotency and audit context exist.

The reference graph offers no model-callable write or consequential tool.

### 5. Validate output

Parse strict structured output; reject extra commands, URLs, active markup, fabricated citation IDs, unauthorized resources, prohibited recommendations, and unsupported assertions. Citation and policy-applicability validation use authoritative stores. A failed validation is never rendered as a normal answer.

### 6. Observe and respond

Record safe detection categories, blocked tool proposals, validation failures, affected document IDs, model/prompt versions, and correlation IDs. Do not log sensitive prompt bodies by default. Repeated patterns create security alerts and may quarantine a document or suspend a workflow pending review.

## Adversarial benchmark

The golden dataset includes direct and indirect instruction overrides, role impersonation, data-exfiltration requests, encoded/obfuscated text, fake system messages, false citation directives, tool argument injection, denial-of-wallet instructions, and benign text likely to cause false positives. Expected behavior is defined at retrieval, generation, tool, output, and escalation layers.

## Residual limitations

Detection has false positives/negatives; delimiters can be ignored; models can transform or echo sensitive text. Therefore permissions, minimization, schemas, and human approval remain authoritative. Adding an autonomous browser, code interpreter, email, payment, or claim-update tool requires a new threat model and explicit approval boundary.

## Phase 3 enforced boundary

The Phase 3 grounded-answer service receives only evidence returned after
server-side tenant, claim-assignment, and action authorization. It has no tools,
network, secrets, or unrestricted document lookup. Injection-risk chunks remain
visible and citable evidence, while instruction-like sentences are excluded
from deterministic answer synthesis. Audit records retain hashes, counts,
versions, states, and correlation identifiers rather than question or document
bodies.
