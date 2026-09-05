# Phase 5 Governed Model Assistance

Phase 5 adds a bounded Claim Evidence Brief after application-controlled authorization and Phase 3 retrieval. The model provider receives a task, applicable policy edition, and retrieved evidence labeled with opaque citation handles. Uploaded text is always untrusted data and cannot become an instruction or capability.

`ModelProvider` is an application port. The verified adapter is `DeterministicBriefProvider`; no external provider or credential is configured. A real adapter must implement the same structured request/result contract and may not bypass retrieval, validation, or audit persistence.

Responses are parsed by a strict Pydantic schema with unknown fields forbidden. The application rejects malformed output, prohibited consequential language, unknown citation handles, and wrong-policy citations. Only application-resolved citation metadata reaches the stored brief or UI.

The prompt body is not persisted. Invocation records contain provider/model/configuration identifiers, template/schema/retrieval versions, prompt hash, evidence fingerprint, authorized citation IDs, latency, optional token usage, retry count, outcome, validation failures, actor, workflow, and correlation IDs.

Briefs optionally reference the latest Phase 4 workflow. Workflow and review authority remain deterministic. Existing review requirements are carried into the brief, and a changed document fingerprint marks the brief stale.

The model has no tools, shell, filesystem, SQL, HTTP, browser, credentials, write authority, or external-action capability.
