<script setup lang="ts">
const gates = [
  [
    "Grounding",
    "Citation validity, coverage, wrong-policy and distractor rates",
  ],
  ["Safety", "Injection detection, abstention, and prohibited-action rates"],
  ["Workflow", "Human-review routing, state accuracy, and durable resume"],
  [
    "Isolation",
    "Tenant and assignment boundaries across retrieval and generation",
  ],
];
</script>

<template>
  <div class="page-shell">
    <header class="page-header">
      <div>
        <span class="eyebrow">MODEL GOVERNANCE</span>
        <h1>Evaluation</h1>
        <p>
          Release gates for evidence quality, model safety, and human-control
          behavior.
        </p>
      </div>
      <span class="status-chip status-chip--neutral">Authorized oversight</span>
    </header>
    <section class="surface evaluation-intro">
      <div>
        <span class="eyebrow">CURRENT MODE</span>
        <h2>Deterministic regression suite</h2>
        <p>
          The local environment evaluates repeatable safety and grounding
          behavior. It does not demonstrate production-model quality.
        </p>
      </div>
      <span class="status-chip status-chip--success">CI compatible</span>
    </section>
    <section class="evaluation-grid" aria-label="Evaluation gates">
      <article
        v-for="gate in gates"
        :key="gate[0]"
        class="surface evaluation-card"
      >
        <span class="evaluation-marker" aria-hidden="true"></span>
        <h2>{{ gate[0] }}</h2>
        <p>{{ gate[1] }}</p>
        <span class="evaluation-state">Release-gated</span>
      </article>
    </section>
    <section class="surface boundary-panel">
      <div>
        <span class="eyebrow">LIVE PROVIDER</span>
        <h2>External-model evaluation is separate</h2>
        <p>
          Live-provider evaluation runs only with approved credentials and
          environment access. Deterministic results are never presented as proof
          of production LLM quality.
        </p>
      </div>
    </section>
  </div>
</template>
