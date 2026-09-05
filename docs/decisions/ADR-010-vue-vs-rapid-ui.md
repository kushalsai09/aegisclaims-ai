# ADR-010: Vue versus Streamlit/Gradio for the Primary UI

- **Status:** Accepted
- **Decision date:** 2026-08-26

## Context

The employee experience requires dense evidence navigation, durable async state, accessible review interactions, role-aware routes, a design system, and polished enterprise information architecture. Rapid AI demo frameworks optimize experimentation rather than this interaction model.

## Decision

Use Vue 3 with TypeScript for the primary application. Streamlit or Gradio may be used only for isolated internal experiments/evaluator tools with no production workflow dependency.

## Alternatives

- **Streamlit/Gradio primary:** fast to start but constrained navigation/state/accessibility/design control.
- **React:** equally viable ecosystem; Vue is selected for approachable component composition and explicit project decision, not a claim of universal superiority.
- **Server-rendered templates:** simpler deployment but less suitable for coordinated evidence panels and async updates.

## Trade-offs and consequences

Vue introduces Node tooling, frontend contracts, and dedicated tests. It enables controlled UX, sanitization, accessibility, and component reuse. Backend authorization remains authoritative.

## Success criteria

WCAG 2.2 AA target evidence, keyboard/screen-reader critical journeys, stable SSE reconciliation, no raw generated HTML, typed contract coverage, and successful adjuster/reviewer usability tasks.
