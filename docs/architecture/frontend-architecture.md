# Frontend Information and Technical Architecture

## Experience model

The Vue 3 and TypeScript SPA is an evidence-review workspace, not a conversational shell. Chat-like questions may exist as one tool, but claim state, documents, facts, policy evidence, issues, reviews, and audit history remain first-class navigable objects.

## Information architecture

- **My Work:** assigned claims, recent work, failures requiring attention.
- **Claims:** searchable authorized list with status and review indicators.
- **Claim Workspace:** overview, documents, extracted facts, AI summary, policy evidence, missing information, contradictions, next actions, Support Assessment, review, and history.
- **Review Queue:** reasons, age, risk, assignee, snapshot status, and decision controls.
- **Evaluation & Operations:** authorized quality, latency, cost, error, and review dashboards.
- **Administration:** narrowly scoped configuration/version views; not a generic rule editor in the reference release.

## Claim workspace composition

The persistent header distinguishes authoritative claim fields from generated artifacts and shows freshness. The central workspace uses coordinated panels:

1. claim overview and loss timeline;
2. document inventory with processing state;
3. generated summary and extracted facts;
4. evidence viewer opening exact policy or claim source spans;
5. missing/contradictory/unresolved issue list;
6. rule results and Support Assessment components;
7. proposed next actions with prohibited-boundary notices;
8. human-review state and audit timeline.

Severity never relies on color alone. “AI-generated,” “employee-edited,” “verified,” “unsupported,” and “stale” are explicit labels.

## State and API design

- Server state is fetched/cached through a query library; domain state is not duplicated into a global mutable store without need.
- Local UI state contains layout and unsaved edits only.
- Route guards improve UX but are never authorization controls.
- SSE status updates reconcile through versioned server resources after reconnect.
- Forms submit expected versions and preserve drafts when a conflict occurs.
- Error boundaries show actionable correlation IDs and retry options without exposing internals.

## Review interaction

Approval controls display the exact artifact/evidence snapshot and require a reason appropriate to the decision. Stale review tasks disable action and direct the reviewer to the replacement analysis. Keyboard focus moves to validation summaries and async status is announced through polite live regions. Destructive/cumulative actions require clear confirmation but do not use manipulative UI.

## Security

OIDC authorization code with PKCE is preferred for browser authentication. Tokens are stored according to the selected BFF or secure session design; long-lived secrets never enter the SPA. Content Security Policy, output encoding, safe document rendering, CSRF protection where cookies are used, dependency scanning, and clickjacking protection are required. Model-generated content is rendered as sanitized text/limited markdown, never arbitrary HTML.

## Accessibility and testing

Target WCAG 2.2 AA. Automated axe checks complement keyboard navigation, focus-order, zoom/reflow, reduced-motion, screen-reader, error-identification, table semantics, and contrast tests. Component tests cover state variants; contract tests cover API assumptions; Playwright covers critical claim, evidence, and review journeys.

## Alternatives

Streamlit and Gradio remain suitable for isolated evaluator experiments but not the primary UI: they provide faster prototypes at the expense of granular accessibility, navigation, state, design-system, and enterprise workflow control. Vue is selected for product-quality interaction with the trade-off of a separate frontend toolchain.
