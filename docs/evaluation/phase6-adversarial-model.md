# Phase 6 Adversarial Model Evaluation

Run `scripts/phase6-evaluate.sh`. The deterministic CI suite covers direct and indirect injection, fake system/assistant/tool messages, invented policy and citations, wrong editions, distractors, unsupported conclusions, hidden-prompt and secret requests, approval/denial/payment/fraud instructions, long input, and malformed evidence.

It reports schema validity, citation validity, safety detection, abstention, human-review routing, and prohibited-action rate. These results prove repeatable application controls only. They do not establish live-model quality. Live-provider tests are separately environment-gated and require explicit AWS credentials, model ID, and region.
