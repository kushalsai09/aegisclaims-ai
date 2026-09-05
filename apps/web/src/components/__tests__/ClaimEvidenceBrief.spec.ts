import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ClaimEvidenceBrief from "@/components/ClaimEvidenceBrief.vue";

const { api } = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("@/services/api", async () => {
  const actual =
    await vi.importActual<typeof import("@/services/api")>("@/services/api");
  return { ...actual, api };
});

const brief = {
  id: "brief-1",
  claim_id: "claim-1",
  workflow_id: "workflow-1",
  task: "Brief evidence",
  status: "conflicting_evidence",
  claim_summary: "Claim evidence requires review.",
  evidence_summary: "Only authorized evidence was summarized.",
  applicable_policy_summary: "Applicable policy edition: 2026-SYN-A.",
  missing_information: ["estimate"],
  conflicts: ["Sources disagree on loss date."],
  ambiguities: ["Cause allocation remains unresolved."],
  safety_flags: ["untrusted_document_instructions_present"],
  citations: [
    {
      id: "CIT-1",
      document_name: "Notice.pdf",
      page_number: 1,
      source_url: "/documents/1?page=1",
    },
  ],
  human_review_required: true,
  limitations: ["Not a claim decision."],
  authority_notice:
    "AI-assisted evidence brief. Decision remains with the authorized reviewer.",
  stale: false,
  validation_state: "valid",
  evidence_fingerprint: "abc",
  applicable_policy_edition: "2026-SYN-A",
  provider: "local_deterministic",
  model_identifier: "claim_evidence_brief",
  configuration_version: "v1",
  prompt_template_version: "v1",
  retrieval_configuration: "v1",
  response_schema_version: "v1",
  latency_ms: 1,
  input_tokens: 10,
  output_tokens: 20,
  retry_count: 0,
  correlation_id: "correlation-1",
  created_at: "2026-08-26T12:00:00Z",
};

function mounted() {
  return mount(ClaimEvidenceBrief, {
    props: { claimId: "claim-1" },
    global: {
      stubs: { RouterLink: { template: "<a><slot /></a>" } },
    },
  });
}

describe("ClaimEvidenceBrief", () => {
  beforeEach(() => api.mockReset());

  it("renders citations, all safety states, and human-control language", async () => {
    api.mockResolvedValueOnce(brief);
    const wrapper = mounted();
    await flushPromises();
    for (const text of [
      "AI-assisted evidence brief",
      "Decision remains",
      "Missing information",
      "Conflicts",
      "Ambiguities",
      "Safety warning",
      "CIT-1",
      "Limitations",
    ])
      expect(wrapper.text()).toContain(text);
  });

  it("renders stale evidence and supports regeneration", async () => {
    api.mockResolvedValueOnce({
      ...brief,
      stale: true,
      validation_state: "stale",
    });
    const wrapper = mounted();
    await flushPromises();
    expect(wrapper.text()).toContain("Evidence changed after generation");
    api.mockResolvedValueOnce({ ...brief, stale: false });
    await wrapper.get(".secondary-button").trigger("click");
    await flushPromises();
    expect(api).toHaveBeenLastCalledWith(
      "/claims/claim-1/briefs",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("renders empty generation and a recoverable generation error", async () => {
    api.mockResolvedValueOnce(null);
    const wrapper = mounted();
    await flushPromises();
    expect(wrapper.text()).toContain("Generate evidence brief");
    api.mockRejectedValueOnce(new Error("provider offline"));
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(wrapper.text()).toContain("Evidence brief unavailable");
    expect(wrapper.text()).toContain("Retry");
  });
});
